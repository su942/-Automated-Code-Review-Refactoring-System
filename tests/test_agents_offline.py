"""
Runs the full multi-agent pipeline on the bundled sample_repo/buggy_calculator.py
without needing a real GitHub PR. Still calls the real Groq API (free -- needs
GROQ_API_KEY set) and the real pylint/bandit binaries.

This is what to run for your lab demo screenshots.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.orchestrator import Orchestrator
from src.schemas import FileDiff


def main():
    if not Config.GROQ_API_KEY:
        print("ERROR: set GROQ_API_KEY in your .env before running this "
              "(free key at https://console.groq.com/keys).")
        sys.exit(1)

    # This is a local/offline demo against a fake repo -- never attempt to
    # post a comment to GitHub here, no matter what .env says.
    Config.POST_TO_GITHUB = False

    sample_path = os.path.join(os.path.dirname(__file__), "sample_repo", "buggy_calculator.py")
    with open(sample_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Treat the whole file as the "diff" for this offline demo
    file_diff = FileDiff(
        filename="buggy_calculator.py",
        patch=content,
        full_content=content,
    )

    orchestrator = Orchestrator(repo="local/offline-demo", pr_number=0)
    orchestrator.load_files_locally([file_diff])
    report_path = orchestrator.run()

    print("\n--- REPORT PREVIEW ---\n")
    with open(report_path, "r", encoding="utf-8") as f:
        print(f.read())


if __name__ == "__main__":
    main()
