"""Application settings from environment."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _get(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _get_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


def _get_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, str(default)))
    except ValueError:
        return default


# MySQL (read-only)
MYSQL_HOST = _get("MYSQL_HOST", "localhost")
MYSQL_PORT = _get_int("MYSQL_PORT", 3306)
MYSQL_USER = _get("MYSQL_USER", "readonly_user")
MYSQL_PASSWORD = _get("MYSQL_PASSWORD", "")
MYSQL_DATABASE = _get("MYSQL_DATABASE", "healthcare_db")

# Ollama
OLLAMA_BASE_URL = _get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = _get("OLLAMA_MODEL", "llama3.2")
OLLAMA_EMBEDDING_MODEL = _get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

# Cache
CACHE_TTL_SECONDS = _get_int("CACHE_TTL_SECONDS", 300)
CHROMA_PERSIST_PATH = _get("CHROMA_PERSIST_PATH", "./chroma_data")
CHROMA_SIMILARITY_THRESHOLD = _get_float("CHROMA_SIMILARITY_THRESHOLD", 0.95)

# Audit
AUDIT_LOG_PATH = _get("AUDIT_LOG_PATH", "./audit_log.jsonl")

# Limits
MAX_QUERY_ROWS = _get_int("MAX_QUERY_ROWS", 500)

# Demo mode: use mock responses (no MySQL/Ollama required)
DEMO_MODE = os.environ.get("DEMO_MODE", "").strip().lower() in ("1", "true", "yes")
