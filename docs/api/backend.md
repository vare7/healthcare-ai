# Backend API Reference

The backend exposes a small set of functions intended to be called by the UI or other Python code.

## `backend.query.run_query`

```python
from backend.query import run_query

result = run_query("How many patients were admitted last week?")
```

**Parameters**

- `question: str` – natural-language question.
- `sql: str | None` – optional SQL override. If provided, the generated SQL step is skipped.

**Returns** a dict with the standard response shape:

```python
{
    "data": list[dict],           # rows as dicts
    "result_type": "table" | "kpi" | "bar_chart" | "line_chart",
    "chart_config": dict,         # keys like x_column, y_column, title
    "from_cache": bool,
    "row_count": int,
    "sql": str,                   # normalized SQL
    "error": str,                 # non-empty on failure
}
```

## `backend.cache.query_with_cache`

```python
from backend.cache import query_with_cache

result = query_with_cache(
    "Show visits by department in the last 30 days",
    session_id="demo-session-1",
    history="...",  # formatted by backend.memory
)
```

**Parameters**

- `question: str` – natural-language question.
- `session_id: str` – identifier for the current UI session.
- `history: str` – compact representation of recent turns, produced by `backend.memory.format_history`.

**Behavior**

1. Checks ChromaDB semantic cache for similar questions.
2. If miss, calls `run_query()` which:
   - Generates SQL (`backend.text_to_sql.generate_sql`).
   - Validates and executes it (`backend.sql_executor`).
   - Infers result type and chart config (`backend.result_metadata`).
3. Fills both semantic and SQL caches.
4. Logs an audit entry via `backend.audit`.

Returns the same response dict shape as `run_query`.

