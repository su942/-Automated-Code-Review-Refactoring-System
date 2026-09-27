from src.agents.base_agent import BaseAgent
from src.schemas import Finding, FileDiff
from src.static_tools import run_bandit


class SecurityAuditorAgent(BaseAgent):
    name = "security_auditor"
    system_prompt = (
        "You are a security-focused code reviewer. You are given raw bandit findings plus "
        "the code. Explain each real risk in plain language and give a concrete fix. Also "
        "flag anything bandit missed but is clearly a security issue (hardcoded secrets, "
        "SQL built via string concatenation, eval/exec on untrusted input, disabled TLS "
        "verification).\n\n"
        "Respond with ONLY a JSON array, no prose, no markdown fences. Each item:\n"
        '{"line": <int>, "severity": "low"|"medium"|"high"|"critical", "issue": "<short description>", '
        '"suggestion": "<how to fix>"}\n'
        "If there is nothing worth flagging, respond with []."
    )

    def run(self, file_diff: FileDiff, extra_context: dict = None) -> list[Finding]:
        bandit_results = run_bandit(file_diff.filename, file_diff.full_content)
        if extra_context is not None:
            extra_context["bandit"] = bandit_results

        user_prompt = (
            f"File: {file_diff.filename}\n\n"
            f"Raw bandit findings (JSON): {bandit_results}\n\n"
            f"Full file content:\n{file_diff.full_content[:6000]}"
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
                category="security",
            )
            for item in items
        ]
