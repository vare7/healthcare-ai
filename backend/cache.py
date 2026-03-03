"""In-memory cache (by normalized SQL) + ChromaDB semantic cache (by question embedding).

Flow (order matters):
1. Chroma — check by question embedding BEFORE calling the LLM.
   Only hits for cosine similarity >= threshold AND entry within TTL.
   Purpose: skip the expensive LLM call for nearly-identical questions.
2. LLM — generate SQL from the question.
3. In-memory — check by normalized SQL to skip a redundant DB round-trip
   when the LLM produces SQL we already executed recently.
4. Execute — run the SQL and fill both cache layers.
"""
import logging
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

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory SQL cache: normalized_sql -> { response, cached_at }
# ---------------------------------------------------------------------------
_sql_cache: dict[str, dict[str, Any]] = {}


def _make_cache_key(sql: str) -> str:
    return normalize_sql(sql)


def _is_expired(cached_at: float) -> bool:
    return (time.time() - cached_at) > CACHE_TTL_SECONDS


def get_from_sql_cache(normalized_sql: str) -> dict[str, Any] | None:
    """Return cached response if present and not expired."""
    key = _make_cache_key(normalized_sql)
    entry = _sql_cache.get(key)
    if not entry or _is_expired(entry.get("cached_at", 0)):
        return None
    return {**entry["response"], "from_cache": True}


def set_sql_cache(normalized_sql: str, response: dict[str, Any]) -> None:
    key = _make_cache_key(normalized_sql)
    _sql_cache[key] = {"response": response, "cached_at": time.time()}


# ---------------------------------------------------------------------------
# ChromaDB semantic cache
# Uses cosine distance (0 = identical, 2 = opposite).
# "query_cache_v2" so any old L2 collection ("query_cache") is abandoned.
# ---------------------------------------------------------------------------
_chroma_client = None
_chroma_collection = None
_embedding_fn = None

_CHROMA_COLLECTION_NAME = "query_cache_v2"


def _get_embedding(text: str) -> list[float]:
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
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_PATH)
        _chroma_collection = _chroma_client.get_or_create_collection(
            name=_CHROMA_COLLECTION_NAME,
            metadata={"description": "Semantic cache for natural language queries"},
            configuration={"hnsw": {"space": "cosine"}},
        )
    return _chroma_collection


def get_from_chroma_cache(question: str) -> dict[str, Any] | None:
    """
    Return a cached response only when ALL of these hold:
    - A stored question has cosine similarity >= CHROMA_SIMILARITY_THRESHOLD
    - The Chroma entry has not exceeded CACHE_TTL_SECONDS
    - The stored SQL can be re-executed (or is still in the in-memory SQL cache)
    """
    try:
        coll = _get_chroma()
        if coll.count() == 0:
            return None

        embedding = _get_embedding(question)
        results = coll.query(
            query_embeddings=[embedding],
            n_results=1,
            include=["metadatas", "documents", "distances"],
        )

        if not results["ids"] or not results["ids"][0]:
            return None

        distances = results.get("distances", [[]])
        if not distances or not distances[0]:
            return None
        dist = distances[0][0]

        # cosine distance = 1 - similarity; threshold 0.95 → max distance 0.05
        max_dist = 1.0 - CHROMA_SIMILARITY_THRESHOLD
        if dist > max_dist:
            matched_q = (results.get("documents") or [[""]])[0][0]
            logger.debug(
                "Chroma MISS: dist=%.4f > max=%.4f  question=%r  nearest=%r",
                dist, max_dist, question, matched_q,
            )
            return None

        meta = (results.get("metadatas") or [[]])[0]
        if not meta:
            return None
        meta = meta[0]

        # TTL check on the Chroma entry itself
        try:
            cached_at = float(meta.get("cached_at", 0))
        except (TypeError, ValueError):
            cached_at = 0
        if _is_expired(cached_at):
            logger.debug("Chroma hit EXPIRED (cached_at=%.0f)", cached_at)
            return None

        normalized_sql = meta.get("normalized_sql")
        if not normalized_sql:
            return None

        matched_q = (results.get("documents") or [[""]])[0][0]
        logger.debug(
            "Chroma HIT: dist=%.4f  question=%r  matched=%r  sql=%s",
            dist, question, matched_q, normalized_sql,
        )

        # Reuse in-memory result if still warm
        cached = get_from_sql_cache(normalized_sql)
        if cached:
            return cached

        # Otherwise re-execute the SQL
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
        logger.exception("Chroma cache lookup failed")
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
        logger.exception("Failed to write Chroma cache")


# ---------------------------------------------------------------------------
# Demo mode
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def query_with_cache(question: str, session_id: str = "") -> dict[str, Any]:
    """
    1. Chroma  — skip LLM for nearly-identical questions.
    2. LLM    — generate SQL.
    3. SQL cache — skip execution for same SQL.
    4. Execute — run query and fill both caches.
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

    # ── Step 1: Semantic cache (BEFORE the LLM call) ──────────────────────
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

    # ── Step 2: Generate SQL via LLM ──────────────────────────────────────
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

    # ── Step 3: SQL-level dedup (skip execution, NOT the LLM) ─────────────
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
        # Also store this question in Chroma so next time we skip the LLM too.
        set_chroma_cache(question, normalized, cached)
        return cached

    # ── Step 4: Execute and fill both caches ──────────────────────────────
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
