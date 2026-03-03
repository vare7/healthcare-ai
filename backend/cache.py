"""In-memory cache (by normalized SQL) + ChromaDB semantic cache (by question embedding)."""
import time
import uuid
from typing import Any

from backend.sql_executor import normalize_sql
from backend.text_to_sql import generate_sql
from backend.query import run_query
from backend.audit import log_query as audit_log
from config.settings import (
    CACHE_TTL_SECONDS,
    CHROMA_PERSIST_PATH,
    CHROMA_SIMILARITY_THRESHOLD,
    OLLAMA_BASE_URL,
    OLLAMA_EMBEDDING_MODEL,
    DEMO_MODE,
)


# In-memory: normalized_sql -> { response_dict, cached_at }
_sql_cache: dict[str, dict[str, Any]] = {}


def _make_cache_key(sql: str) -> str:
    return normalize_sql(sql)


def _is_expired(entry: dict) -> bool:
    cached_at = entry.get("cached_at", 0)
    return (time.time() - cached_at) > CACHE_TTL_SECONDS


def get_from_sql_cache(normalized_sql: str) -> dict[str, Any] | None:
    """Return cached response if present and not expired."""
    key = _make_cache_key(normalized_sql)
    entry = _sql_cache.get(key)
    if not entry or _is_expired(entry):
        return None
    out = {**entry["response"], "from_cache": True}
    return out


def set_sql_cache(normalized_sql: str, response: dict[str, Any]) -> None:
    key = _make_cache_key(normalized_sql)
    _sql_cache[key] = {"response": response, "cached_at": time.time()}


# ChromaDB semantic cache
_chroma_client = None
_chroma_collection = None
_embedding_fn = None


def _get_embedding(text: str) -> list[float]:
    """Use Ollama to embed text."""
    from langchain_ollama import OllamaEmbeddings
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = OllamaEmbeddings(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_EMBEDDING_MODEL,
        )
    return _embedding_fn.embed_query(text)


def _get_chroma():
    global _chroma_client, _chroma_collection
    if _chroma_client is None:
        import chromadb
        from chromadb.config import Settings
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_PATH)
        _chroma_collection = _chroma_client.get_or_create_collection(
            name="query_cache",
            metadata={"description": "Semantic cache for natural language queries"},
        )
    return _chroma_collection


def get_from_chroma_cache(question: str) -> dict[str, Any] | None:
    """
    If a semantically similar question is in Chroma, return its cached response.
    We store normalized_sql in metadata and fetch full response from sql_cache (or re-execute if missing).
    """
    try:
        coll = _get_chroma()
        embedding = _get_embedding(question)
        results = coll.query(
            query_embeddings=[embedding],
            n_results=1,
            include=["metadatas", "documents"],
        )
        if not results["ids"] or not results["ids"][0]:
            return None
        # Chroma returns distance (lower = more similar). We use similarity threshold.
        # For cosine, distance can be 0-2; we want high similarity so distance < (1 - threshold) * 2 or similar.
        # Chroma's default metric is L2; we might need to check distances[0][0]
        distances = results.get("distances", [[]])
        if distances and distances[0]:
            dist = distances[0][0]
            # L2: smaller is more similar. Accept if distance below threshold (e.g. 0.5)
            max_dist = max(0.01, 1.0 - CHROMA_SIMILARITY_THRESHOLD)
            if dist > max_dist:
                return None
        metadatas = results.get("metadatas", [[]])
        if not metadatas or not metadatas[0]:
            return None
        meta = metadatas[0][0]
        normalized_sql = meta.get("normalized_sql")
        if not normalized_sql:
            return None
        # Try to get full response from sql cache (same process, so it might be there)
        cached = get_from_sql_cache(normalized_sql)
        if cached:
            return cached
        # Re-execute that SQL to get fresh result (e.g. after restart)
        from backend.sql_executor import execute_select
        from backend.result_metadata import get_result_metadata
        rows, row_count, err = execute_select(normalized_sql)
        if err:
            return None
        result_type, chart_config = get_result_metadata(rows)
        response = {
            "data": rows,
            "result_type": result_type,
            "chart_config": chart_config,
            "from_cache": True,
            "row_count": row_count,
            "sql": normalized_sql,
            "error": "",
        }
        set_sql_cache(normalized_sql, response)
        return response
    except Exception:
        return None


def set_chroma_cache(question: str, normalized_sql: str, response: dict[str, Any]) -> None:
    try:
        coll = _get_chroma()
        embedding = _get_embedding(question)
        coll.add(
            ids=[str(uuid.uuid4())],
            embeddings=[embedding],
            documents=[question],
            metadatas=[{
                "normalized_sql": normalized_sql,
                "result_type": response.get("result_type", "table"),
                "row_count": str(response.get("row_count", 0)),
                "cached_at": str(time.time()),
            }],
        )
    except Exception:
        pass


def _demo_response(question: str) -> dict[str, Any]:
    """Return mock response for demo mode (no MySQL/Ollama)."""
    q = question.lower()
    if "count" in q or "how many" in q or "total" in q:
        return {
            "data": [{"total": 42}],
            "result_type": "kpi",
            "chart_config": {},
            "from_cache": False,
            "row_count": 1,
            "sql": "SELECT 42 AS total",
            "error": "",
        }
    if "chart" in q or "by department" in q or "by month" in q:
        return {
            "data": [
                {"department": "Cardiology", "admissions": 120},
                {"department": "ER", "admissions": 340},
                {"department": "Surgery", "admissions": 85},
            ],
            "result_type": "bar_chart",
            "chart_config": {"x_column": "department", "y_column": "admissions", "title": "Admissions by department"},
            "from_cache": False,
            "row_count": 3,
            "sql": "SELECT department, COUNT(*) AS admissions FROM visits GROUP BY department",
            "error": "",
        }
    # default: table
    return {
        "data": [
            {"id": 1, "patient_id": "P001", "date": "2025-01-15", "status": "Completed"},
            {"id": 2, "patient_id": "P002", "date": "2025-01-16", "status": "Scheduled"},
        ],
        "result_type": "table",
        "chart_config": {},
        "from_cache": False,
        "row_count": 2,
        "sql": "SELECT id, patient_id, date, status FROM appointments LIMIT 10",
        "error": "",
    }


def query_with_cache(question: str, session_id: str = "") -> dict[str, Any]:
    """
    Generate SQL, check in-memory cache by SQL, then Chroma by question; on miss execute and fill caches.
    Audits every request (cache hit or miss).
    """
    start = time.time()

    if DEMO_MODE:
        resp = _demo_response(question)
        duration_ms = (time.time() - start) * 1000
        audit_log(
            session_id=session_id,
            question=question,
            generated_sql=resp.get("sql", ""),
            result_type=resp.get("result_type", "table"),
            row_count=resp.get("row_count", 0),
            from_cache=False,
            duration_ms=duration_ms,
            error="",
        )
        return resp

    # 1) Generate SQL
    try:
        sql = generate_sql(question)
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        audit_log(
            session_id=session_id,
            question=question,
            generated_sql="",
            result_type="table",
            row_count=0,
            from_cache=False,
            duration_ms=duration_ms,
            error=str(e),
        )
        return {
            "data": [],
            "result_type": "table",
            "chart_config": {},
            "from_cache": False,
            "row_count": 0,
            "sql": "",
            "error": str(e),
        }
    normalized = normalize_sql(sql)

    # 2) In-memory by SQL
    cached = get_from_sql_cache(normalized)
    if cached:
        duration_ms = (time.time() - start) * 1000
        audit_log(
            session_id=session_id,
            question=question,
            generated_sql=normalized,
            result_type=cached.get("result_type", "table"),
            row_count=cached.get("row_count", 0),
            from_cache=True,
            duration_ms=duration_ms,
            error="",
        )
        return cached

    # 3) Chroma by question
    cached = get_from_chroma_cache(question)
    if cached:
        duration_ms = (time.time() - start) * 1000
        audit_log(
            session_id=session_id,
            question=question,
            generated_sql=cached.get("sql", ""),
            result_type=cached.get("result_type", "table"),
            row_count=cached.get("row_count", 0),
            from_cache=True,
            duration_ms=duration_ms,
            error="",
        )
        return cached

    # 4) Execute and cache
    response = run_query(question, sql=sql)
    duration_ms = (time.time() - start) * 1000
    audit_log(
        session_id=session_id,
        question=question,
        generated_sql=response.get("sql", ""),
        result_type=response.get("result_type", "table"),
        row_count=response.get("row_count", 0),
        from_cache=False,
        duration_ms=duration_ms,
        error=response.get("error", ""),
    )
    if response.get("error"):
        return response
    set_sql_cache(normalized, response)
    set_chroma_cache(question, normalized, response)
    return response
