"""Introspect MySQL schema (read-only) and return a string for the LLM. No row data."""
import pymysql
from typing import Optional

from config.settings import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
)


def get_connection():
    """Return a read-only MySQL connection."""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        cursorclass=pymysql.cursors.DictCursor,
        charset="utf8mb4",
    )


def get_schema_string(database: Optional[str] = None) -> str:
    """
    Query information_schema for the given database and return a concise
    schema string (tables, columns, types). No row data.
    """
    db = database or MYSQL_DATABASE
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_KEY
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME, ORDINAL_POSITION
                """,
                (db,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    # Group by table
    tables: dict[str, list[dict]] = {}
    for r in rows:
        t = r["TABLE_NAME"]
        if t not in tables:
            tables[t] = []
        tables[t].append(
            {
                "name": r["COLUMN_NAME"],
                "type": r["DATA_TYPE"],
                "key": r["COLUMN_KEY"] or "",
            }
        )

    parts = []
    for table_name in sorted(tables.keys()):
        cols = tables[table_name]
        col_strs = [f"{c['name']} ({c['type']})" for c in cols]
        parts.append(f"Table {table_name}: {', '.join(col_strs)}")
    return "; ".join(parts)
