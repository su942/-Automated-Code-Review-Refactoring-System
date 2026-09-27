"""
Aggregator agent: does NOT call the LLM for every finding (that would be
wasteful and non-deterministic for something that's really just merging +
formatting). Instead it deterministically ranks/dedupes findings in code,
then makes ONE LLM call to write a short natural-language executive summary
on top. This is a deliberate design choice worth mentioning in your report's
"Observations" section (pure-LLM aggregation was less consistent).
"""
from collections import defaultdict
from src.agents.base_agent import BaseAgent
from src.schemas import Finding, PipelineState

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class AggregatorAgent(BaseAgent):
    name = "aggregator"
    system_prompt = (
        "You are a lead engineer writing a concise executive summary of a code review. "
        "Given a list of findings (JSON), write a 4-6 sentence plain-language summary: "
        "overall code health, the most urgent 1-2 issues, and one encouraging note about "
        "what looked good. No markdown headers, just plain prose."
    )

    def _dedupe(self, findings: list[Finding]) -> list[Finding]:
        seen = set()
        deduped = []
        for f in findings:
            key = (f.file, f.line, f.issue.strip().lower()[:60])
            if key not in seen:
                seen.add(key)
                deduped.append(f)
        return deduped

    def build_report(self, state: PipelineState) -> str:
        findings = self._dedupe(state.findings)
        findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 4), f.file, f.line))

        by_file = defaultdict(list)
        for f in findings:
            by_file[f.file].append(f)

        # one LLM call for the executive summary, grounded in the actual findings
        summary_prompt = str([f.to_dict() for f in findings[:40]])
        try:
            summary = self._call_llm(summary_prompt)
        except Exception as e:
            summary = f"(summary generation failed: {e})"

        lines = [
            f"# Automated Code Review Report",
            f"**Repo:** {state.repo}  |  **PR:** #{state.pr_number}",
            "",
            "## Executive Summary",
            summary.strip(),
            "",
            f"## Findings ({len(findings)} total across {len(by_file)} files)",
        ]

        for filename, file_findings in by_file.items():
            lines.append(f"\n### `{filename}`")
            lines.append("| Line | Category | Severity | Agent | Issue | Suggestion |")
            lines.append("|---|---|---|---|---|---|")
            for f in file_findings:
                lines.append(
                    f"| {f.line} | {f.category} | {f.severity} | {f.agent} | "
                    f"{f.issue.replace('|', '/')} | {f.suggestion.replace('|', '/')} |"
                )

        report = "\n".join(lines)
        state.final_report_markdown = report
        return report
