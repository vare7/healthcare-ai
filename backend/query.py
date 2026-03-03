"""Orchestration: text-to-SQL -> execute -> result metadata. Used by cache layer and UI."""
from typing import Any

from backend.text_to_sql import generate_sql
from backend.sql_executor import execute_select, normalize_sql
from backend.result_metadata import get_result_metadata


def run_query(question: str, sql: str | None = None) -> dict[str, Any]:
    """
    Generate SQL from question (or use provided sql), execute read-only, add result_type and chart_config.
    Returns dict: data, result_type, chart_config, from_cache=False, row_count, sql, error.
    """
    if sql is None:
        try:
            sql = generate_sql(question)
        except Exception as e:
            return {
                "data": [],
                "result_type": "table",
                "chart_config": {},
                "from_cache": False,
                "row_count": 0,
                "sql": "",
                "error": str(e),
            }
    rows, row_count, err = execute_select(sql)
    if err:
        return {
            "data": [],
            "result_type": "table",
            "chart_config": {},
            "from_cache": False,
            "row_count": 0,
            "sql": normalize_sql(sql),
            "error": err,
        }
    result_type, chart_config = get_result_metadata(rows)
    return {
        "data": rows,
        "result_type": result_type,
        "chart_config": chart_config,
        "from_cache": False,
        "row_count": row_count,
        "sql": normalize_sql(sql),
        "error": "",
    }
