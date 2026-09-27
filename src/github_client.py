"""
Thin wrapper around PyGithub: fetch a PR's changed files + diffs, and
optionally post the aggregated report back as a PR comment.
"""
from github import Github
from src.config import Config
from src.schemas import FileDiff


class GitHubClient:
    def __init__(self, token: str = None):
        self.client = Github(token or Config.GITHUB_TOKEN)

    def fetch_pr_diff(self, repo_name: str, pr_number: int) -> list[FileDiff]:
        """Return one FileDiff per changed file in the PR."""
        repo = self.client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        file_diffs = []
        for f in pr.get_files():
            full_content = ""
            try:
                # fetch full file content at the PR head commit, for extra context
                content_file = repo.get_contents(f.filename, ref=pr.head.sha)
                full_content = content_file.decoded_content.decode("utf-8", errors="ignore")
            except Exception:
                pass  # file may be deleted / binary / too large

            file_diffs.append(
                FileDiff(
                    filename=f.filename,
                    patch=f.patch or "",
                    full_content=full_content,
                )
            )
        return file_diffs

    def post_comment(self, repo_name: str, pr_number: int, body: str):
        repo = self.client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(body)
        print(f"[github] posted review comment to {repo_name}#{pr_number}")
