from src.agents.base_agent import BaseAgent
from src.schemas import Finding, FileDiff
from src.static_tools import run_pylint


class StyleCheckerAgent(BaseAgent):
    name = "style_checker"
    system_prompt = (
        "You are a code style reviewer. You are given raw pylint output plus the code. "
        "Your job is to select the MOST IMPORTANT style issues (ignore trivial ones like "
        "missing docstrings unless there are many), explain them briefly in plain language, "
        "and suggest a fix. Do not invent issues not present in the pylint output unless "
        "extremely obvious (e.g. inconsistent naming conventions).\n\n"
        "Respond with ONLY a JSON array, no prose, no markdown fences. Each item:\n"
        '{"line": <int>, "severity": "low"|"medium"|"high", "issue": "<short description>", '
        '"suggestion": "<how to fix>"}\n'
        "If there is nothing worth flagging, respond with []."
    )

    def run(self, file_diff: FileDiff, extra_context: dict = None) -> list[Finding]:
        pylint_results = run_pylint(file_diff.filename, file_diff.full_content)
        if extra_context is not None:
            extra_context["pylint"] = pylint_results

        if not pylint_results:
            self.trace_logger.log(self.name, "tool_call", {"tool": "pylint", "result": "no issues / not python"})
            return []

        user_prompt = (
            f"File: {file_diff.filename}\n\n"
            f"Raw pylint findings (JSON):\n{pylint_results}\n\n"
            f"Relevant code:\n{file_diff.full_content[:6000]}"
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
                category="style",
            )
            for item in items
        ]
