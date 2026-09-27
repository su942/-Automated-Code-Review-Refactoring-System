"""
Structured logging of every agent prompt/response, written as JSONL.
This file is exactly what to paste into the report's "sample conversation
traces" section (or attach as an appendix).
"""
import json
import os
import time


class TraceLogger:
    def __init__(self, repo: str, pr_number: int, log_dir: str = "logs"):
        os.makedirs(log_dir, exist_ok=True)
        safe_repo = repo.replace("/", "_")
        self.path = os.path.join(log_dir, f"trace_{safe_repo}_{pr_number}.jsonl")

    def log(self, agent: str, event: str, payload: dict):
        record = {
            "timestamp": time.time(),
            "agent": agent,
            "event": event,   # "prompt" | "response" | "tool_call" | "error"
            "payload": payload,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def print_summary(self):
        print(f"[trace] full agent trace written to {self.path}")
