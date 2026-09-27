# Automated Code Review & Refactoring System Using Multi-Agent AI

---

## Cover Page

| Field | Details |
|---|---|
| Problem Statement Title | Automated Code Review & Refactoring System |
| Domain | Agentic AI / Software Engineering Automation |
| Problem Statement Number | Lab-I |
| Course Name | CE509 – Agentic AI |
| GitHub | https://github.com/su942/-Automated-Code-Review-Refactoring-System |

---

## 1. Objective

The objective of this lab is to design and implement a multi-agent AI system that automatically reviews GitHub Pull Requests. The system uses specialized LLM-powered agents, each responsible for a distinct aspect of code quality: bug detection, refactoring suggestions, style checking, and security auditing. A coordinator agent aggregates all findings into a structured Markdown report, and a code fixer agent generates an improved version of the reviewed file. The system also integrates real static analysis tools (pylint, bandit) to ground the LLM findings in deterministic results, reducing hallucinations. The overall goal is to demonstrate how autonomous, collaborating agents can replace or assist human code reviewers in a traceable and reproducible way.

---

## 2. Work Done

### Problem Understanding

Manual code review is time-consuming and inconsistent. Different reviewers notice different types of issues depending on their expertise. The goal was to build a system where each area of concern (bugs, style, security, refactoring) is handled by a dedicated LLM agent, and all findings are combined into one actionable report — similar to how a team of specialists would review code.

### Task Decomposition

The review task was split into the following sequential steps:

1. Fetch the PR diff from GitHub API (Orchestrator)
2. For each changed file, run 4 independent review agents:
   - Bug Detector
   - Refactor Suggester
   - Style Checker (grounded by pylint)
   - Security Auditor (grounded by bandit)
3. Aggregate all findings, deduplicate, rank by severity (Aggregator)
4. Rewrite the file with all issues fixed (Code Fixer)
5. Save the report and optionally post it as a PR comment

### Agent Roles and Responsibilities

| Agent | Responsibility | Input | Output |
|---|---|---|---|
| Orchestrator | Fetches PR diff, dispatches agents, manages state | GitHub repo + PR number | FileDiff objects |
| Bug Detector | Finds logic errors, unhandled exceptions, off-by-one bugs | Diff + full file | Finding[] |
| Refactor Suggester | Identifies readability and structure improvements | Diff + full file | Finding[] |
| Style Checker | Reports naming, formatting, and convention violations | pylint output + code | Finding[] |
| Security Auditor | Flags injection risks, hardcoded secrets, unsafe calls | bandit output + code | Finding[] |
| Aggregator | Deduplicates, sorts by severity, writes executive summary | All Finding[] | Markdown report |
| Code Fixer | Rewrites the entire file with all findings resolved | Full file + Finding[] | Corrected source file |

### Communication Design

- **Pattern:** Hub-and-spoke. The Orchestrator is the central coordinator; worker agents never communicate with each other directly. This makes the system easy to log and debug.
- **Shared State:** A single `PipelineState` object is passed through the entire pipeline. Each agent appends its `Finding` objects to it. The Code Fixer reads them all at the end.
- **Message Schema:** All agents emit findings in a standard JSON format:
  ```json
  {
    "agent": "bug_detector",
    "file": "buggy_calculator.py",
    "line": 6,
    "severity": "high",
    "issue": "division by zero unhandled",
    "suggestion": "check if b == 0 before dividing",
    "category": "bug"
  }
  ```
- **Traceability:** Every LLM prompt and response is logged to `logs/trace_<repo>_<pr>.jsonl` as a JSONL file, providing a complete audit trail.

### Tools Used

| Tool | Purpose |
|---|---|
| Groq API (openai/gpt-oss-20b) | LLM backend for all 6 agents |
| PyGithub | Fetch PR diffs and post review comments |
| pylint | Static style/lint analysis fed to Style Checker |
| bandit | Static security analysis fed to Security Auditor |
| python-dotenv | Load API keys and config from .env |
| GitHub Actions | Auto-trigger the review pipeline on PR open/update |

### Architecture / Workflow Diagram

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
                   │   Code Fixer     │
                   └────────┬─────────┘
                             ▼
                   fixed/<filename>.py
```

---

## 3. Results / Output

### System Running – Terminal Output

```
[orchestrator] reviewing 1 file(s) across 4 agents...
  -> buggy_calculator.py
     [bug_detector] 2 finding(s)
     [refactor_suggester] 5 finding(s)
     [style_checker] 10 finding(s)
     [security_auditor] 3 finding(s)
     [code_fixer] improved code generated
[orchestrator] report written to reports/report_su942_..._1.md
[orchestrator] improved code written to fixed/buggy_calculator.py
[trace] full agent trace written to logs/trace_su942_..._1.jsonl
```

### Sample Input – buggy_calculator.py

```python
import os

API_KEY = "sk-test-1234567890abcdef"  # BUG(security): hardcoded secret

def divide(a, b):
    return a / b  # BUG(logic): no check for b == 0

def get_user(users, index):
    return users[index]  # BUG(logic): no bounds checking

def run_query(user_input):
    query = "SELECT * FROM users WHERE name = '" + user_input + "'"  # SQL injection
    return query

def calculate_total(items):
    total = 0
    for i in range(len(items)):
        total = total + items[i]['price']
    return total

class shoppingCart:                      # style: should be PascalCase
    def __init__(self):
        self.Items = []                  # style: should be snake_case

    def addItem(self, item):             # style: should be snake_case
        self.Items.append(item)
        os.system("echo added " + item['name'])  # BUG(security): command injection
```

### Sample Output – Report (Findings Table)

| Line | Category | Severity | Agent | Issue | Suggestion |
|---|---|---|---|---|---|
| 3 | security | high | security_auditor | Hardcoded secret API key | Load from environment variable using os.getenv('API_KEY') |
| 5 | bug | high | bug_detector | Division by zero unhandled | Check if b == 0 before dividing |
| 8 | bug | high | bug_detector | Index out of bounds unhandled | Validate index against len(users) |
| 26 | style | high | style_checker | Class name "shoppingCart" not PascalCase | Rename to ShoppingCart |
| 27 | security | high | security_auditor | Command injection via os.system | Use subprocess.run() or remove the shell call |
| 12 | security | medium | security_auditor | SQL injection via string concatenation | Use parameterized queries |
| 6 | style | medium | style_checker | Missing function docstring | Add docstring to divide() |
| 20 | refactor | medium | refactor_suggester | Inefficient index-based loop | Use: for item in items: total += item['price'] |

Total: 20 findings across 1 file (2 bugs, 5 refactors, 10 style, 3 security)

### Agent Interaction Trace (Sample from logs/trace_*.jsonl)

Bug Detector prompt sent to LLM:
```
System: You are a senior software engineer reviewing a pull request diff for
BUGS ONLY: logic errors, off-by-one errors, null/None handling...

User: File: buggy_calculator.py
Diff: [full file content]
```

Bug Detector response:
```json
[
  {"line": 5, "severity": "high", "issue": "division by zero unhandled",
   "suggestion": "check if b == 0 before dividing, raise ValueError or return None"},
  {"line": 8, "severity": "high", "issue": "index out of bounds unhandled",
   "suggestion": "validate index against len(users), raise IndexError or return None"}
]
```

Security Auditor used bandit's static output as grounding context before calling the LLM:
```json
[
  {"line": 15, "severity": "MEDIUM", "message": "Possible SQL injection vector
   through string-based query construction.", "test_id": "B608"},
  {"line": 32, "severity": "HIGH", "message": "Starting a process with a shell,
   possible injection detected.", "test_id": "B605"}
]
```

### Evaluation Summary

| Agent | Findings | True Positives | Notes |
|---|---|---|---|
| Bug Detector | 2 | 2 | Correctly caught division-by-zero and index OOB |
| Refactor Suggester | 5 | 5 | All valid improvements |
| Style Checker | 10 | 10 | Grounded in pylint, all verified |
| Security Auditor | 3 | 3 | Bandit caught 2; LLM added hardcoded key |
| Code Fixer | 1 file | — | Generated valid, fixed Python file |

### GitHub Repository

https://github.com/su942/-Automated-Code-Review-Refactoring-System

---

## 4. Observations & Learning

### What Worked Well

- The hybrid approach (pylint/bandit + LLM) worked very well for style and security. Grounding the LLM with deterministic tool output made findings more accurate and consistent.
- The shared `PipelineState` schema was an effective way to pass findings between agents — all agents spoke the same JSON format, so the aggregator required no special handling per agent.
- The Code Fixer agent produced clean, runnable Python that addressed all flagged issues in a single pass.
- The JSONL trace file made it easy to inspect exactly what prompt was sent to each agent and what it returned, which is useful for debugging and for the lab report.

### Challenges Faced and How They Were Solved

- **Model deprecation:** The initially configured model (`llama-3.1-8b-instant`) was unavailable on the account. After checking the Groq API's live model list, the model was switched to `openai/gpt-oss-20b`, which was confirmed available and working.
- **GitHub token permissions:** When attempting to post the review as a PR comment, the token returned a 403 error. This was resolved by setting `POST_TO_GITHUB=false` for offline testing and noting that the token needs `repo` scope (or Issues: Read & Write for fine-grained tokens) for live use.
- **README corruption:** An early strReplace edit to the README left the file in a corrupted state with duplicated and interleaved content. This was resolved by doing a full clean rewrite of the file.

### Key Learning Points

- Multi-agent systems benefit greatly from a standardized shared schema — it decouples agents from each other and lets you add or remove agents without rewriting the coordinator.
- LLMs are better at explaining and prioritizing real issues than at discovering them from scratch. Feeding static tool output as context dramatically improves precision.
- Hub-and-spoke orchestration is easier to trace and debug than peer-to-peer agent communication — every interaction has exactly one sender and one receiver.
- Agent prompts need to be very specific about output format (JSON only, no prose, no markdown fences) to ensure reliable parsing downstream.

---

## 5. Conclusion

This lab successfully demonstrated a working multi-agent AI system for automated code review. Six specialized agents — Bug Detector, Refactor Suggester, Style Checker, Security Auditor, Aggregator, and Code Fixer — collaboratively reviewed a Python file and produced 20 actionable findings along with a corrected version of the file. The hybrid design (LLM + static tools) proved effective at reducing hallucinations while maintaining the flexibility of natural language explanations. The system runs both locally for offline testing and against real GitHub Pull Requests, with optional auto-triggering via GitHub Actions. The architecture is modular and extensible — new agents or languages can be added without changing the core orchestration logic.

---

## 6. References

1. Groq API Documentation – https://console.groq.com/docs/models
2. PyGithub Documentation – https://pygithub.readthedocs.io
3. Pylint Documentation – https://pylint.readthedocs.io
4. Bandit Documentation – https://bandit.readthedocs.io
5. OpenAI Chat Completions API – https://platform.openai.com/docs/api-reference/chat
6. GitHub Actions Documentation – https://docs.github.com/en/actions

---

## Appendix

### 1. Important Prompts

**Bug Detector System Prompt:**
```
You are a senior software engineer reviewing a pull request diff for BUGS ONLY:
logic errors, off-by-one errors, null/None handling, unhandled exceptions,
incorrect conditionals, and race conditions. Ignore style and security issues.

Respond with ONLY a JSON array, no prose, no markdown fences. Each item:
{"line": <int>, "severity": "low"|"medium"|"high"|"critical",
 "issue": "<short description>", "suggestion": "<how to fix>"}
If there are no bugs, respond with [].
```

**Code Fixer System Prompt:**
```
You are a senior software engineer tasked with fixing a Python source file.
You will be given the original file content and a list of findings (bugs,
security issues, style problems, and refactor suggestions) from a code review.

Your job: rewrite the ENTIRE file with ALL findings fixed. Rules:
- Output ONLY the corrected Python source code, nothing else.
- Do NOT include any explanation, comments about what changed, or markdown fences.
- Apply every finding: fix bugs, resolve security issues, rename to PEP-8
  conventions, add docstrings, use safe patterns.
- The output must be valid, runnable Python.
```

**Aggregator System Prompt:**
```
You are a lead engineer writing a concise executive summary of a code review.
Given a list of findings (JSON), write a 4-6 sentence plain-language summary:
overall code health, the most urgent 1-2 issues, and one encouraging note about
what looked good. No markdown headers, just plain prose.
```

### 2. Selected Code Snippets

**PipelineState schema (src/schemas.py):**
```python
@dataclass
class PipelineState:
    repo: str
    pr_number: int
    files: List[FileDiff] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    static_tool_output: Dict[str, Any] = field(default_factory=dict)
    final_report_markdown: str = ""
    fixed_files: Dict[str, str] = field(default_factory=dict)
```

**Orchestrator dispatch loop (src/orchestrator.py):**
```python
for file_diff in self.state.files:
    for agent in self.worker_agents:
        findings = agent.run(file_diff)
        self.state.add_findings(findings)

    file_findings = [f for f in self.state.findings if f.file == file_diff.filename]
    if file_findings and file_diff.full_content:
        fixed_code = self.code_fixer.run(file_diff, file_findings)
        self.state.fixed_files[file_diff.filename] = fixed_code
```

**GitHub Actions trigger (.github/workflows/code-review.yml):**
```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  agent-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run multi-agent review
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          POST_TO_GITHUB: "true"
        run: python main.py --repo ${{ github.repository }} --pr ${{ github.event.pull_request.number }}
```
