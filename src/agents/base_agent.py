"""
Base class for all LLM-backed agents. Handles the Groq API call (free tier,
OpenAI-compatible chat completions), JSON-only parsing, and trace logging so
each concrete agent only needs to define its system prompt and how to turn
the response into Finding objects.
"""
import json
import re
from groq import Groq
from src.config import Config
from src.logger import TraceLogger


class BaseAgent:
    name = "base_agent"
    system_prompt = "You are a helpful assistant."

    def __init__(self, trace_logger: TraceLogger, client: Groq = None):
        self.trace_logger = trace_logger
        self.client = client or Groq(api_key=Config.GROQ_API_KEY)

    def _call_llm(self, user_prompt: str) -> str:
        self.trace_logger.log(self.name, "prompt", {"system": self.system_prompt,
                                                      "user": user_prompt})
        response = self.client.chat.completions.create(
            model=Config.GROQ_MODEL,
            max_tokens=Config.MAX_TOKENS,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = response.choices[0].message.content or ""
        self.trace_logger.log(self.name, "response", {"text": text})
        return text

    @staticmethod
    def _extract_json(text: str):
        """Strip markdown code fences if present, then parse JSON."""
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # last-resort: find the first [...] or {...} block
            match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            raise

    def run(self, file_diff, extra_context: dict = None):
        raise NotImplementedError
