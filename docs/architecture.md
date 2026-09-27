# Architecture & Design Notes

## 1. Task Decomposition

The PR review problem is split by *concern*, not by file:

1. Fetch PR diff (Orchestrator)
2. For each changed file, run 4 independent analyses in parallel-conceptually
   (sequential in this implementation for simplicity/logging, but each agent
   is stateless per file and could be parallelized with `asyncio` or threads):
   - Bug detection
   - Refactor suggestions
   - Style checking (grounded by pylint)
   - Security auditing (grounded by bandit)
3. Aggregate all findings into one report (Aggregator)
4. Post back to GitHub (optional)

## 2. Agent Roles & Responsibilities

| Agent | Responsibility | Input | Output |
|---|---|---|---|
| Orchestrator | Fetch PR diff, dispatch to workers, manage shared state | PR URL/number | List of `FileDiff` |
| Bug Detector | Logic errors, unhandled exceptions, edge cases | Diff + full file | `Finding[]` |
| Refactor Suggester | Readability/structure improvements | Diff + full file | `Finding[]` |
| Style Checker | Naming, formatting, convention violations | pylint output + code | `Finding[]` |
| Security Auditor | Injection risks, secrets, unsafe calls | bandit output + code | `Finding[]` |
| Aggregator | Dedupe, rank by severity, write executive summary | All `Finding[]` | Markdown report |

## 3. Communication Design

- **Pattern:** hub-and-spoke. The Orchestrator is the only agent that talks to
  every other agent; workers never talk to each other directly. This keeps
  the system easy to trace/debug/log — every message has one sender, one
  receiver.
- **Shared state object:** `PipelineState` (see `src/schemas.py`) is passed
  through the whole run and accumulates `Finding` objects. This is the
  system's "blackboard."
- **Message schema:** every agent, regardless of role, emits a list of
  `Finding` JSON objects with the same shape:
  ```json
  {"agent": "security_auditor", "file": "auth.py", "line": 42,
   "severity": "high", "issue": "...", "suggestion": "...", "category": "security"}
  ```
  Standardizing this schema is what lets the Aggregator merge findings from
  four differently-prompted agents without special-casing each one.
- **Traceability:** every LLM prompt and response is logged to
  `logs/trace_<repo>_<pr>.jsonl`, giving a full audit trail of the
  "conversation" between the orchestrator and each agent.

## 4. Why hybrid (LLM + static tools)?

Pure LLM-based bug/security detection tends to hallucinate issues that
aren't real, and misses issues a deterministic tool would catch instantly
(e.g., bandit reliably flags `eval()`, hardcoded passwords, insecure hashes).
By feeding `pylint`/`bandit` JSON output into the Style/Security agents as
context, the LLM's job shifts from "invent issues" to "explain, prioritize,
and contextualize real issues" — which is both more accurate and easier to
evaluate (precision/recall against known static-tool ground truth).

## 5. Tools Used

| Tool | Purpose |
|---|---|
| Groq API (Llama 3.3 70B, free tier) | All four review agents + aggregator summary |
| PyGithub | Fetch PR diffs, post review comment |
| pylint | Deterministic style/lint grounding |
| bandit | Deterministic security grounding |
| GitHub Actions | Auto-trigger review on PR open/update |

## 6. Known Limitations / Future Work

- Workers run sequentially per file; could parallelize with `asyncio.gather`
  for latency, at the cost of harder-to-read logs.
- Only Python is grounded with static tools; other languages fall back to
  pure LLM judgment for style/security.
- Line numbers from the LLM (bug/refactor agents) are best-effort, not
  guaranteed accurate against the diff hunk headers — a stretch goal is to
  parse unified diff `@@` headers and pass exact line ranges to the prompt.
