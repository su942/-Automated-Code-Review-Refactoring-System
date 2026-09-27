# Automated Code Review & Refactoring System (Multi-Agent)

A multi-agent system where specialized LLM agents collaboratively review a GitHub
Pull Request: detecting bugs, suggesting refactors, checking style, flagging security
issues, and generating an improved version of every reviewed file. Findings are merged
by an Aggregator agent into one Markdown report and optionally posted back to the PR
as a comment.

## Architecture

```
                    ┌─────────────────────┐
                    │   Orchestrator      │
                    └──────────┬──────────┘
                               │ fetches PR diff (GitHub API)
                               ▼
        ┌──────────────────────────────────────────────┐
        │           dispatch per changed file           │
        └──────────────────────────────────────────────┘
        │            │            │            │
        ▼            ▼            ▼            ▼
   ┌─────────┐  ┌──────────┐ ┌──────────┐ ┌───────────┐
   │  Bug    │  │ Refactor │ │  Style   │ │ Security  │
   │Detector │  │Suggester │ │ Checker  │ │ Auditor   │
   └────┬────┘  └────┬─────┘ └────┬─────┘ └─────┬─────┘
        └────────────┴──────┬──────┴──────────────┘
                             ▼
                   ┌──────────────────┐
                   │   Aggregator     │
                   └────────┬─────────┘
                             ▼
                report.md / PR comment
                             │
                             ▼
                   ┌──────────────────┐
                   │   Code Fixer     │  ← improved source saved to fixed/
                   └──────────────────┘
```

See `docs/architecture.md` for the full design write-up.

## Agents

### BugDetectorAgent (`src/agents/bug_detector.py`)
Scans the diff and full file content for logic errors, off-by-one mistakes, unhandled
exceptions, null/None mishandling, and incorrect conditionals. Returns a JSON array of
findings with line number, severity, issue description, and suggested fix.

### RefactorSuggesterAgent (`src/agents/refactor_suggester.py`)
Identifies opportunities to improve code quality and maintainability without changing
behaviour — duplicate logic, overly complex expressions, non-idiomatic patterns, naming
inconsistencies, and structure improvements. Includes short code snippets in suggestions
where useful.

### StyleCheckerAgent (`src/agents/style_checker.py`)
Runs `pylint` on the file first (via `src/static_tools.py`), then feeds those real
findings to the LLM to explain and prioritise them. This hybrid approach prevents the
model from hallucinating style issues. Covers PEP-8 naming, docstrings, import order,
and formatting.

### SecurityAuditorAgent (`src/agents/security_auditor.py`)
Runs `bandit` on the file first, then feeds those findings to the LLM alongside the
source code. Also catches issues bandit misses: hardcoded secrets, SQL built via string
concatenation, `eval`/`exec` on untrusted input, and disabled TLS verification.

### AggregatorAgent (`src/agents/aggregator.py`)
Deterministically deduplicates and sorts all findings by severity, then makes a single
LLM call to write a 4-6 sentence plain-language executive summary. Outputs the final
Markdown report combining the summary and a per-file findings table.

### CodeFixerAgent (`src/agents/code_fixer.py`)
After all findings are collected for a file, this agent rewrites the entire file with
every issue resolved — bugs fixed, security vulnerabilities patched, style cleaned up,
and refactors applied. Outputs valid, runnable Python saved to `fixed/<filename>`.

## Supporting modules

| Module | Purpose |
|---|---|
| `src/config.py` | Loads env vars from `.env`; strips stray quotes; provides `validate_for_live_run()` |
| `src/schemas.py` | `Finding`, `FileDiff`, `PipelineState` dataclasses — the shared communication schema |
| `src/orchestrator.py` | Hub-and-spoke dispatcher: runs all agents per file, calls aggregator, saves outputs |
| `src/github_client.py` | Fetches PR diffs and full file content via PyGithub; posts review comment |
| `src/static_tools.py` | Runs `pylint` and `bandit` in a temp file; returns structured JSON results |
| `src/logger.py` | Writes every agent prompt/response as a JSONL trace to `logs/` |
| `main.py` | CLI entry point (`--repo owner/repo --pr 42`) |

## Repo layout

```
code-review-agents/
├── README.md
├── requirements.txt
├── .env.example
├── main.py
├── src/
│   ├── config.py
│   ├── schemas.py
│   ├── logger.py
│   ├── github_client.py
│   ├── static_tools.py
│   ├── orchestrator.py
│   └── agents/
│       ├── base_agent.py
│       ├── bug_detector.py
│       ├── refactor_suggester.py
│       ├── style_checker.py
│       ├── security_auditor.py
│       ├── aggregator.py
│       └── code_fixer.py
├── tests/
│   ├── sample_repo/
│   │   └── buggy_calculator.py
│   └── test_agents_offline.py
├── fixed/                         # improved source files (generated at runtime)
├── reports/                       # markdown review reports (generated at runtime)
├── logs/                          # JSONL agent traces (generated at runtime)
├── .github/workflows/code-review.yml
└── docs/
    └── architecture.md
```

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=your_key           # free at console.groq.com/keys
GITHUB_TOKEN=your_pat           # needs repo scope to post PR comments
GROQ_MODEL=openai/gpt-oss-20b  # or openai/gpt-oss-120b for higher quality
POST_TO_GITHUB=false            # set true to post report as a PR comment
```

## Usage

**Run against a real GitHub PR:**
```bash
python main.py --repo owner/repo --pr 42
```

**Run offline on the bundled sample (no GitHub account needed):**
```bash
python tests/test_agents_offline.py
```

## Output

| Path | Contents |
|---|---|
| `reports/report_<repo>_<pr>.md` | Full review report with executive summary and findings table |
| `fixed/<filename>` | Improved version of each reviewed file with all issues resolved |
| `logs/trace_<repo>_<pr>.jsonl` | Complete JSONL trace of every agent prompt and response |

## Design notes

- **Orchestration pattern**: hub-and-spoke (orchestrator → 5 worker agents → aggregator → code fixer), not peer-to-peer. Simpler to log and debug.
- **Hybrid grounding**: Style and Security agents receive real `pylint`/`bandit` output as context before the LLM call, so findings are grounded in deterministic analysis rather than model guesses.
- **Shared state**: a single `PipelineState` object is passed through the whole pipeline. Each agent appends findings; the code fixer reads them all at the end.
- **Code generation**: `CodeFixerAgent` runs after all four reviewer agents finish for a file, so it has the full picture before rewriting.
