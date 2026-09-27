# Automated Code Review & Refactoring System (Multi-Agent)

A multi-agent system where specialized LLM agents collaboratively review a GitHub
Pull Request: detecting bugs, suggesting refactors, checking style, and flagging
security issues. Findings are merged by an Aggregator agent into one Markdown
report and (optionally) posted back to the PR as a comment.

## Architecture

```
                    ┌─────────────────────┐
                    │   Orchestrator      │
                    └──────────┬──────────┘
                               │ fetches PR diff (GitHub API)
                               ▼
        ┌──────────────────────────────────────────┐
        │           dispatch per changed file         │
        └──────────────────────────────────────────┘
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
```

See `docs/architecture.md` for the full design write-up (agent roles,
communication schema, tool choices) — this doubles as content for your
CE509 lab report's "Work Done" section.

## Repo layout

```
code-review-agents/
├── README.md
├── requirements.txt
├── .env.example
├── main.py                        # CLI entry point
├── src/
│   ├── config.py                  # env/config loading
│   ├── schemas.py                 # shared JSON message schema (dataclasses)
│   ├── logger.py                  # structured JSONL logging of every agent call
│   ├── github_client.py           # fetch PR diff, post PR comment
│   ├── static_tools.py            # wraps pylint / bandit for grounded findings
│   ├── orchestrator.py            # dispatches work to agents, builds shared state
│   └── agents/
│       ├── base_agent.py          # shared LLM-calling logic
│       ├── bug_detector.py
│       ├── refactor_suggester.py
│       ├── style_checker.py
│       ├── security_auditor.py
│       └── aggregator.py
├── tests/
│   ├── sample_repo/               # small file with injected bugs, for local testing
│   │   └── buggy_calculator.py
│   └── test_agents_offline.py     # runs the pipeline on a local diff, no GitHub needed
├── .github/workflows/code-review.yml   # GitHub Action: auto-run on PR open
└── docs/
    └── architecture.md
```

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY (free, from console.groq.com/keys) and GITHUB_TOKEN
```

## Usage

**Run on a real GitHub PR:**
```bash
python main.py --repo owner/repo --pr 42
```

**Run fully offline on the bundled sample (no GitHub/API calls needed for a dry run of the pipeline shape):**
```bash
python tests/test_agents_offline.py
```

Output: `reports/report_<repo>_<pr>.md` plus a full JSONL trace of every
agent's prompt/response in `logs/trace_<repo>_<pr>.jsonl` (this trace file is
exactly what you paste into the "Sample conversation traces" part of your
report).

## Design notes

- **Orchestration pattern**: hub-and-spoke (orchestrator → 4 worker agents →
  aggregator), not peer-to-peer. Simpler to log and debug, which matters for
  a lab report where you need to show traceable agent communication.
- **Hybrid grounding**: the Style and Security agents are given real
  `pylint`/`bandit` output as context, not just raw code, so the LLM explains
  and prioritizes deterministic findings rather than hallucinating them.
- **Shared state**: a single `PipelineState` object (see `src/schemas.py`) is
  passed through the pipeline and each agent appends its findings to it —
  this is your "communication design."
