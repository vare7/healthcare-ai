"""Validate and execute read-only SELECT queries against MySQL."""
import re
import pymysql
from typing import Any

from backend.schema import get_connection
from config.settings import MAX_QUERY_ROWS


# Forbidden patterns (read-only enforcement)
FORBIDDEN_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|LOAD|EXECUTE|CALL)\b",
    re.IGNORECASE,
)


def normalize_sql(sql: str) -> str:
    """Strip comments and normalize whitespace to a single space."""
    # Remove single-line -- and # comments
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"#[^\n]*", " ", sql)
    # Remove multi-line /* */ comments
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    # Normalize whitespace
    sql = " ".join(sql.split())
    return sql.strip()


def validate_read_only(sql: str) -> tuple[bool, str]:
    """
    Ensure the query is a single SELECT and contains no forbidden keywords.
    Returns (ok, error_message).
    """
    normalized = normalize_sql(sql)
    if not normalized.upper().startswith("SELECT"):
        return False, "Only SELECT queries are allowed."
    if FORBIDDEN_PATTERNS.search(normalized):
        return False, "Query contains forbidden keywords (e.g. INSERT, UPDATE, DELETE)."
    # Reject multiple statements
    if ";" in normalized.rstrip(";"):
        return False, "Only a single SELECT statement is allowed."
    return True, ""


def execute_select(sql: str) -> tuple[list[dict[str, Any]], int, str]:
    """
    Validate and execute a SELECT. Returns (rows, row_count, error_message).
    error_message is empty on success. Rows are list of dicts (column -> value).
    """
    ok, err = validate_read_only(sql)
    if not ok:
        return [], 0, err

    normalized = normalize_sql(sql)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(normalized)
            rows = cur.fetchmany(MAX_QUERY_ROWS)
        row_count = len(rows)
        # Convert to list of dicts if cursor returns tuples (DictCursor already returns dicts)
        if rows and isinstance(rows[0], dict):
            return rows, row_count, ""
        # If tuple row, we'd need column names; DictCursor gives dicts
        return rows, row_count, ""
    except pymysql.Error as e:
        return [], 0, str(e)
    finally:
        conn.close()
