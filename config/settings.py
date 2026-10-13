
"""Centralized application configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root, regardless of the current working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _get_int(name: str, default: int) -> int:
    """Read an integer environment variable with a helpful error."""
    value = os.getenv(name, str(default))
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc


APP_ENV = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# LLM provider configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL", "http://localhost:11434"
)

# Vector database configuration
VECTOR_DB_PROVIDER = os.getenv("VECTOR_DB_PROVIDER", "chroma").strip().lower()
CHROMA_PERSIST_DIRECTORY = os.getenv(
    "CHROMA_PERSIST_DIRECTORY", "./data/chroma"
)

# External data sources
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "")
FINANCIAL_API_KEY = os.getenv("FINANCIAL_API_KEY", "")
WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY", "")

# Agent configuration
MAX_TOOL_CALLS = _get_int("MAX_TOOL_CALLS", 20)
TOOL_TIMEOUT_SECONDS = _get_int("TOOL_TIMEOUT_SECONDS", 30)
MAX_RETRIES = _get_int("MAX_RETRIES", 3)

SUPPORTED_LLM_PROVIDERS = {
    "openai",
    "anthropic",
    "groq",
    "gemini",
    "openrouter",
    "ollama",
}


def validate_settings(require_api_key: bool = False) -> None:
    """Validate supported providers and optional API-key requirements."""
    if LLM_PROVIDER not in SUPPORTED_LLM_PROVIDERS:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: {LLM_PROVIDER!r}. "
            f"Choose one of: {', '.join(sorted(SUPPORTED_LLM_PROVIDERS))}."
        )

    if VECTOR_DB_PROVIDER not in {"chroma", "pinecone", "weaviate", "qdrant"}:
        raise ValueError(
            "VECTOR_DB_PROVIDER must be chroma, pinecone, weaviate, or qdrant."
        )

    if MAX_TOOL_CALLS < 1:
        raise ValueError("MAX_TOOL_CALLS must be at least 1.")
    if TOOL_TIMEOUT_SECONDS < 1:
        raise ValueError("TOOL_TIMEOUT_SECONDS must be at least 1.")
    if MAX_RETRIES < 0:
        raise ValueError("MAX_RETRIES cannot be negative.")

    if require_api_key:
        api_keys = {
            "openai": OPENAI_API_KEY,
            "anthropic": ANTHROPIC_API_KEY,
            "groq": GROQ_API_KEY,
            "gemini": GEMINI_API_KEY,
            "openrouter": OPENROUTER_API_KEY,
        }

        # Ollama runs locally and normally does not require an API key.
        if LLM_PROVIDER != "ollama" and not api_keys[LLM_PROVIDER]:
            raise ValueError(
                f"Set the API key for the selected provider: {LLM_PROVIDER}."
            )

