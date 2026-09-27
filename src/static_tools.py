"""
Runs real static analysis tools (pylint, bandit) on file content and returns
structured results. These are fed into the Style/Security agents as grounding
context so the LLM explains and prioritizes real findings instead of only
guessing from the diff -- this is the "hybrid" part of the design.

Only works on Python files; other languages are skipped gracefully.
"""
import json
import subprocess
import tempfile
import os


def _is_python(filename: str) -> bool:
    return filename.endswith(".py")


def run_pylint(filename: str, content: str) -> list[dict]:
    if not _is_python(filename) or not content.strip():
        return []
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            ["pylint", tmp_path, "--output-format=json", "--disable=all",
             "--enable=C,W,E"],
            capture_output=True, text=True, timeout=30,
        )
        if not result.stdout.strip():
            return []
        raw = json.loads(result.stdout)
        return [
            {
                "line": item.get("line", 0),
                "type": item.get("type"),
                "message": item.get("message"),
                "symbol": item.get("symbol"),
            }
            for item in raw
        ]
    except Exception as e:
        return [{"line": 0, "type": "error", "message": f"pylint failed: {e}", "symbol": ""}]
    finally:
        os.unlink(tmp_path)


def run_bandit(filename: str, content: str) -> list[dict]:
    if not _is_python(filename) or not content.strip():
        return []
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            ["bandit", "-f", "json", tmp_path],
            capture_output=True, text=True, timeout=30,
        )
        if not result.stdout.strip():
            return []
        raw = json.loads(result.stdout)
        return [
            {
                "line": item.get("line_number", 0),
                "severity": item.get("issue_severity"),
                "confidence": item.get("issue_confidence"),
                "message": item.get("issue_text"),
                "test_id": item.get("test_id"),
            }
            for item in raw.get("results", [])
        ]
    except Exception as e:
        return [{"line": 0, "severity": "error", "confidence": "", "message": f"bandit failed: {e}", "test_id": ""}]
    finally:
        os.unlink(tmp_path)
