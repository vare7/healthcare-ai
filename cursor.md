# Healthcare AI Assistant — Project Context

Use this file to keep context across sessions. Reference it with `@cursor.md` when starting a new chat.

## What this project is

Fully **local, privacy-first** AI assistant for healthcare staff: plain-English questions → SQL → results. No data leaves the machine (Ollama + MySQL + ChromaDB all local). Read-only DB; LLM sees **schema only**, never patient data. Audit log on every query for compliance.

## Tech stack

| Layer        | Technology |
|-------------|------------|
| UI          | Streamlit |
| Backend     | Python, LangChain, LangChain-Ollama |
| DB          | MySQL (read-only user) |
| LLM/Embeddings | Ollama (local) |
| Cache       | In-memory (by normalized SQL) + ChromaDB (semantic by question) |
| Config      | `python-dotenv`, `config/settings.py` |

## Architecture (3 layers)

1. **Text-to-SQL** — `backend/text_to_sql.py` uses LangChain + ChatOllama. LLM gets schema string (with FK relationships) from `backend/schema.py`; outputs a single SELECT. Prompt includes domain semantics and few-shot examples. `backend/sql_guards.py` applies YAML-driven post-generation fixes. `backend/sql_executor.py` validates (SELECT only, no forbidden keywords) and executes.
2. **Rich UI** — `streamlit_app.py` is a chat interface (`st.chat_message` / `st.chat_input`). Conversation history stored in `st.session_state`; `backend/memory.py` formats last N turns for the LLM so follow-ups like "now show that by month" work. Response has `result_type` (`table` \| `kpi` \| `bar_chart` \| `line_chart`) and `chart_config`. Users can override `result_type` via a selectbox.
3. **Caching** — `backend/cache.py`: ChromaDB semantic cache by question embedding (cosine, checked BEFORE LLM) → generate SQL → in-memory cache by normalized SQL → on miss: execute, then fill both caches. Both layers respect `CACHE_TTL_SECONDS`. Audit in `backend/audit.py` (JSONL, no PII).

## Key files

- **Entrypoints:** `streamlit_app.py` (main UI), `run_demo.py` (demo mode, port 8502)
- **Config:** `config/settings.py` (env), `.env.example`. `DEMO_MODE` = mock responses without MySQL/Ollama.
- **Orchestration:** `backend/query.py` — `run_query(question, sql=None)` (text-to-SQL → execute → result_metadata). `backend/cache.py` — `query_with_cache(question, session_id, history)` wraps that with cache + audit.
- **Memory:** `backend/memory.py` — `format_history(turns)` formats last N Q/SQL/result_type turns into a compact context string for the LLM prompt.
- **Schema/DB:** `backend/schema.py` — `get_schema_string()` (read-only introspection, includes FK relationships). `backend/sql_executor.py` — `normalize_sql`, `validate_read_only`, `execute_select`.
- **SQL guards:** `backend/sql_guards.py` + `config/sql_guards.yaml` — YAML-driven post-generation SQL fixes (no Python changes needed for new rules).
- **Result shaping:** `backend/result_metadata.py` — `get_result_metadata(rows)` → `(result_type, chart_config)` from row shape.
- **Audit:** `backend/audit.py` — `log_query(...)` appends to `AUDIT_LOG_PATH` (JSONL).

## Response shape (backend → UI)

```python
{
    "data": list[dict],           # rows
    "result_type": "table" | "kpi" | "bar_chart" | "line_chart",
    "chart_config": {"x_column", "y_column", "title"},
    "from_cache": bool,
    "row_count": int,
    "sql": str,                   # normalized
    "error": str,                 # non-empty on failure
}
```

## Conventions

- Run from repo root; `sys.path` includes root (e.g. `streamlit_app.py` inserts `ROOT`).
- Imports: `from backend.xyz import ...`, `from config.settings import ...`.
- No PII in audit logs (question text, SQL, result_type, row_count, duration only).
- Demo mode: set `DEMO_MODE=1` or run `python run_demo.py`; no MySQL/Ollama required.

## Quick run

- **Demo:** `python run_demo.py` or `run_demo.bat` → http://localhost:8502
- **Full:** Copy `.env.example` → `.env`, set MySQL + Ollama, `ollama pull llama3.2` and `nomic-embed-text`, then `streamlit run streamlit_app.py`
