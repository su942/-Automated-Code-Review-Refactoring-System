# Architecture & Design Notes

## 1. Task Decomposition

The PR review problem is split by *concern*, not by file:

1. Fetch PR diff (Orchestrator)
2. For each changed file, run 4 independent analyses (sequential in this
   implementation for simplicity/logging, but each agent is stateless per
   file and could be parallelized with `asyncio` or threads):
   - Bug detection
   - Refactor suggestions
   - Style checking (grounded by pylint)
   - Security auditing (grounded by bandit)
3. Aggregate all findings into one report (Aggregator)
4. Generate improved source code with all issues fixed (Code Fixer)
5. Post report back to GitHub (optional)

## 2. Agent Roles & Responsibilities

| Agent | Responsibility | Input | Output |
|---|---|---|---|
| Orchestrator | Fetch PR diff, dispatch to workers, manage shared state | PR URL/number | List of `FileDiff` |
| Bug Detector | Logic errors, unhandled exceptions, edge cases | Diff + full file | `Finding[]` |
| Refactor Suggester | Readability/structure improvements | Diff + full file | `Finding[]` |
| Style Checker | Naming, formatting, convention violations | pylint output + code | `Finding[]` |
| Security Auditor | Injection risks, secrets, unsafe calls | bandit output + code | `Finding[]` |
| Aggregator | Dedupe, rank by severity, write executive summary | All `Finding[]` | Markdown report |
| Code Fixer | Rewrite file with all findings resolved | Full file + all `Finding[]` | Corrected source file |

## 3. Communication Design

- **Pattern:** hub-and-spoke. The Orchestrator is the only agent that talks to
  every other agent; workers never talk to each other directly. This keeps
  the system easy to trace/debug/log — every message has one sender, one
  receiver.
- **Shared state object:** `PipelineState` (see `src/schemas.py`) is passed
  through the whole run and accumulates `Finding` objects and `fixed_files`.
  This is the system's "blackboard."
- **Message schema:** every review agent emits a list of `Finding` JSON
  objects with the same shape:
  ```json
  {"agent": "security_auditor", "file": "auth.py", "line": 42,
   "severity": "high", "issue": "...", "suggestion": "...", "category": "security"}
  ```
  Standardizing this schema is what lets the Aggregator and Code Fixer
  consume findings from four differently-prompted agents without
  special-casing each one.
- **Code Fixer input:** after all four review agents finish for a file, the
  Code Fixer receives the original source code plus the full flat list of
  findings and rewrites the entire file in one LLM call.
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
| Groq API (`openai/gpt-oss-20b`) | All review agents + aggregator summary + code fixer |
| PyGithub | Fetch PR diffs, post review comment |
| pylint | Deterministic style/lint grounding for Style Checker |
| bandit | Deterministic security grounding for Security Auditor |
| GitHub Actions | Auto-trigger review on PR open/update |

## 6. Output Artifacts

| Artifact | Location | Description |
|---|---|---|
| Review report | `reports/report_<repo>_<pr>.md` | Executive summary + per-file findings table |
| Improved code | `fixed/<filename>` | Full rewrite of each reviewed file with all issues resolved |
| Agent trace | `logs/trace_<repo>_<pr>.jsonl` | JSONL log of every prompt and LLM response |

## 7. Known Limitations / Future Work

- Workers run sequentially per file; could parallelize with `asyncio.gather`
  for lower latency, at the cost of harder-to-read logs.
- Only Python is grounded with static tools; other languages fall back to
  pure LLM judgment for style/security.
- Line numbers from the LLM (bug/refactor agents) are best-effort — a stretch
  goal is to parse unified diff `@@` headers and pass exact line ranges to
  the prompt for higher accuracy.
- The Code Fixer rewrites the whole file in one shot; for very large files
  a chunked approach would be needed to stay within model context limits.
