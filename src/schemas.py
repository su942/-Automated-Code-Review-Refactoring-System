"""
Shared data structures. Every agent reads/writes these so the whole pipeline
speaks one schema -- this is the "communication design" for the report.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any


@dataclass
class Finding:
    agent: str            # which agent produced this, e.g. "bug_detector"
    file: str              # file path within the repo
    line: int               # best-guess line number (0 if not applicable)
    severity: str          # "low" | "medium" | "high" | "critical"
    issue: str              # short description
    suggestion: str = ""   # proposed fix / refactor
    category: str = ""      # "bug" | "style" | "security" | "refactor"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FileDiff:
    filename: str
    patch: str              # unified diff text for this file
    full_content: str = ""  # full file content after the PR change (if available)


@dataclass
class PipelineState:
    """The single shared object passed through the whole pipeline."""
    repo: str
    pr_number: int
    files: List[FileDiff] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    static_tool_output: Dict[str, Any] = field(default_factory=dict)
    final_report_markdown: str = ""
    fixed_files: Dict[str, str] = field(default_factory=dict)  # filename -> improved code

    def add_findings(self, new_findings: List[Finding]):
        self.findings.extend(new_findings)

    def findings_by_agent(self, agent_name: str) -> List[Finding]:
        return [f for f in self.findings if f.agent == agent_name]
