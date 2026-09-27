from src.agents.base_agent import BaseAgent
from src.schemas import Finding, FileDiff


class RefactorSuggesterAgent(BaseAgent):
    name = "refactor_suggester"
    system_prompt = (
        "You are a senior software engineer suggesting REFACTORS to improve readability, "
        "reduce duplication, and improve structure -- without changing behavior. "
        "Do not repeat bug reports; focus only on code quality / maintainability improvements.\n\n"
        "Respond with ONLY a JSON array, no prose, no markdown fences. Each item:\n"
        '{"line": <int, 0 if general>, "severity": "low"|"medium"|"high", '
        '"issue": "<what could be improved>", "suggestion": "<concrete refactor, include a short code snippet if useful>"}\n'
        "If nothing meaningful to refactor, respond with []."
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
                severity=item.get("severity", "low"),
                issue=item.get("issue", ""),
                suggestion=item.get("suggestion", ""),
                category="refactor",
            )
            for item in items
        ]
