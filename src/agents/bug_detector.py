from src.agents.base_agent import BaseAgent
from src.schemas import Finding, FileDiff


class BugDetectorAgent(BaseAgent):
    name = "bug_detector"
    system_prompt = (
        "You are a senior software engineer reviewing a pull request diff for BUGS ONLY: "
        "logic errors, off-by-one errors, null/None handling, unhandled exceptions, "
        "incorrect conditionals, and race conditions. Ignore style and security issues.\n\n"
        "Respond with ONLY a JSON array, no prose, no markdown fences. Each item:\n"
        '{"line": <int, best guess, 0 if unknown>, "severity": "low"|"medium"|"high"|"critical", '
        '"issue": "<short description>", "suggestion": "<how to fix>"}\n'
        "If there are no bugs, respond with []."
    )

    def run(self, file_diff: FileDiff, extra_context: dict = None) -> list[Finding]:
        user_prompt = (
            f"File: {file_diff.filename}\n\n"
            f"Diff:\n{file_diff.patch}\n\n"
            f"Full file content (for context):\n{file_diff.full_content[:6000]}"
        )
        raw = self._call_llm(user_prompt)
        try:
            items = self._extract_json(raw)
        except Exception:
            items = []

        return [
            Finding(
                agent=self.name,
                file=file_diff.filename,
                line=item.get("line", 0),
                severity=item.get("severity", "medium"),
                issue=item.get("issue", ""),
                suggestion=item.get("suggestion", ""),
                category="bug",
            )
            for item in items
        ]
