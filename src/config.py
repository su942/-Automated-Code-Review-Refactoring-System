"""Central config loaded from environment variables (.env)."""
import os
from dotenv import load_dotenv

load_dotenv()


def _clean(value: str) -> str:
    """Strip accidental quotes/whitespace so a stray edit in .env can't
    silently break the API key or model name."""
    return value.strip().strip('"').strip("'").strip()


class Config:
    GROQ_API_KEY = _clean(os.getenv("GROQ_API_KEY", ""))
    GITHUB_TOKEN = _clean(os.getenv("GITHUB_TOKEN", ""))
    GROQ_MODEL = _clean(os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"))
    POST_TO_GITHUB = os.getenv("POST_TO_GITHUB", "false").lower() == "true"
    MAX_TOKENS = 2000

    @classmethod
    def validate_for_live_run(cls):
        missing = []
        if not cls.GROQ_API_KEY:
            missing.append("GROQ_API_KEY")
        if not cls.GITHUB_TOKEN:
            missing.append("GITHUB_TOKEN")
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Copy .env.example to .env and fill them in."
            )
