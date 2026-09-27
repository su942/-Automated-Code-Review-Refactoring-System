"""
Orchestrator: fetches the PR, dispatches each changed file to all four
worker agents, collects findings into shared PipelineState, then hands off
to the Aggregator. Hub-and-spoke pattern -- see docs/architecture.md.
"""
import os
from src.config import Config
from src.schemas import PipelineState, FileDiff
from src.logger import TraceLogger
from src.github_client import GitHubClient
from src.agents.bug_detector import BugDetectorAgent
from src.agents.refactor_suggester import RefactorSuggesterAgent
from src.agents.style_checker import StyleCheckerAgent
from src.agents.security_auditor import SecurityAuditorAgent
from src.agents.aggregator import AggregatorAgent
from src.agents.code_fixer import CodeFixerAgent


class Orchestrator:
    def __init__(self, repo: str, pr_number: int):
        self.repo = repo
        self.pr_number = pr_number
        self.trace_logger = TraceLogger(repo, pr_number)
        self.state = PipelineState(repo=repo, pr_number=pr_number)

        self.worker_agents = [
            BugDetectorAgent(self.trace_logger),
            RefactorSuggesterAgent(self.trace_logger),
            StyleCheckerAgent(self.trace_logger),
            SecurityAuditorAgent(self.trace_logger),
        ]
        self.aggregator = AggregatorAgent(self.trace_logger)
        self.code_fixer = CodeFixerAgent(self.trace_logger)

    def load_files_from_github(self):
        gh = GitHubClient()
        self.state.files = gh.fetch_pr_diff(self.repo, self.pr_number)

    def load_files_locally(self, file_diffs: list[FileDiff]):
        """For offline testing without hitting the GitHub API."""
        self.state.files = file_diffs

    def run(self) -> str:
        print(f"[orchestrator] reviewing {len(self.state.files)} file(s) "
              f"across {len(self.worker_agents)} agents...")

        for file_diff in self.state.files:
            print(f"  -> {file_diff.filename}")
            for agent in self.worker_agents:
                try:
                    findings = agent.run(file_diff)
                    self.state.add_findings(findings)
                    print(f"     [{agent.name}] {len(findings)} finding(s)")
                except Exception as e:
                    self.trace_logger.log(agent.name, "error", {"error": str(e)})
                    print(f"     [{agent.name}] ERROR: {e}")

            # generate improved code for this file using all findings collected so far
            file_findings = [f for f in self.state.findings if f.file == file_diff.filename]
            if file_findings and file_diff.full_content:
                try:
                    fixed_code = self.code_fixer.run(file_diff, file_findings)
                    self.state.fixed_files[file_diff.filename] = fixed_code
                    print(f"     [code_fixer] improved code generated")

            if file_findings and file_diff.full_content:
                try:
                    fixed_code = self.code_fixer.run(file_diff, file_findings)
                    self.state.fixed_files[file_diff.filename] = fixed_code
                    print(f"     [code_fixer] improved code generated")
                except Exception as e:
                    self.trace_logger.log("code_fixer", "error", {"error": str(e)})
                    print(f"     [code_fixer] ERROR: {e}")

        report = self.aggregator.build_report(self.state)

        os.makedirs("reports", exist_ok=True)
        safe_repo = self.repo.replace("/", "_")
        report_path = f"reports/report_{safe_repo}_{self.pr_number}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"[orchestrator] report written to {report_path}")

        # save improved versions of all fixed files
        if self.state.fixed_files:
            os.makedirs("fixed", exist_ok=True)
            for filename, code in self.state.fixed_files.items():
                safe_name = filename.replace("/", "_")
                fixed_path = f"fixed/{safe_name}"
                with open(fixed_path, "w", encoding="utf-8") as f:
                    f.write(code)
                print(f"[orchestrator] improved code written to {fixed_path}")

        self.trace_logger.print_summary()

        if Config.POST_TO_GITHUB:
            GitHubClient().post_comment(self.repo, self.pr_number, report)

        return report_path
