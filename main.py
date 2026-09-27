"""
CLI entry point.

Usage:
    python main.py --repo owner/repo --pr 42
"""
import argparse
from src.config import Config
from src.orchestrator import Orchestrator


def main():
    parser = argparse.ArgumentParser(description="Multi-agent GitHub PR code reviewer")
    parser.add_argument("--repo", required=True, help="owner/repo, e.g. octocat/Hello-World")
    parser.add_argument("--pr", required=True, type=int, help="Pull request number")
    args = parser.parse_args()

    Config.validate_for_live_run()

    orchestrator = Orchestrator(repo=args.repo, pr_number=args.pr)
    orchestrator.load_files_from_github()
    orchestrator.run()


if __name__ == "__main__":
    main()
