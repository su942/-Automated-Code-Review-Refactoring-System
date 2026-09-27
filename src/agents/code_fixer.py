"""
Code Fixer agent: given the original file content and all findings from the
other agents, produces a fully corrected version of the file with every issue
addressed. Returns the improved source code as a string.
"""
from src.agents.base_agent import BaseAgent
from src.schemas import FileDiff, Finding


class CodeFixerAgent(BaseAgent):
    name = "code_fixer"
    system_prompt = (
        "You are a senior software engineer tasked with fixing a Python source file. "
        "You will be given the original file content and a list of findings (bugs, "
        "security issues, style problems, and refactor suggestions) from a code review.\n\n"
        "Your job: rewrite the ENTIRE file with ALL findings fixed. Rules:\n"
        "- Output ONLY the corrected Python source code, nothing else.\n"
        "- Do NOT include any explanation, comments about what changed, or markdown fences.\n"
        "- Preserve the original logic and structure where no fix is needed.\n"
        "- Apply every finding: fix bugs, resolve security issues, rename to PEP-8 "
        "conventions, add docstrings, use safe patterns (parameterized queries, "
        "subprocess instead of os.system, etc.).\n"
        "- The output must be valid, runnable Python."
    )

    def run(self, file_diff: FileDiff, findings: list[Finding]) -> str:
        """
        Returns the improved file content as a string.
        Does not produce Finding objects — its output is code, not findings.
        """
        findings_summary = "\n".join(
            f"  Line {f.line} [{f.severity}] {f.category}: {f.issue} → {f.suggestion}"
            for f in findings
        )

        user_prompt = (
            f"File: {file_diff.filename}\n\n"
            f"=== ORIGINAL SOURCE CODE ===\n{file_diff.full_content}\n\n"
            f"=== FINDINGS TO FIX ===\n{findings_summary}\n\n"
            "Now output the complete corrected file:"
        )

        return self._call_llm(user_prompt)
