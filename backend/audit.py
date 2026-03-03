"""Audit log for every query: timestamp, session_id, question, sql, result_type, row_count, from_cache, duration_ms. No PII."""
import json
import time
from pathlib import Path

from config.settings import AUDIT_LOG_PATH


def log_query(
    session_id: str,
    question: str,
    generated_sql: str,
    result_type: str,
    row_count: int,
    from_cache: bool,
    duration_ms: float,
    error: str = "",
) -> None:
    """Append one audit record to the log file (JSONL)."""
    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "session_id": session_id,
        "question_text": question[:500],
        "generated_sql": generated_sql[:2000],
        "result_type": result_type,
        "row_count": row_count,
        "from_cache": from_cache,
        "duration_ms": round(duration_ms, 2),
        "error": error[:200] if error else "",
    }
    path = Path(AUDIT_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
