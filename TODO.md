# Pending Actions

Tracked improvements identified from the architecture review. Check off items as they are completed and tested.

---

## Completed

- [x] **Add result_type override mechanism** -- "Display as" selectbox in Streamlit UI lets users switch between Table/KPI/Bar/Line without re-querying the backend. (`result_metadata.py`, `streamlit_app.py`)
- [x] **Make SQL guards data-driven** -- Replaced hardcoded `_is_wrong_admissions_sql` / `_sql_for_admitted_last_week` with YAML-driven guard engine. New rules are added to `config/sql_guards.yaml` with zero Python changes. (`backend/sql_guards.py`, `config/sql_guards.yaml`)
- [x] **Fix bare-alias JOIN bug** -- Post-generation `_fix_bare_alias_joins` rewrites `JOIN d ON` to `JOIN departments d ON`. Prompt updated with explicit rule and "admissions by department" few-shot example. (`backend/text_to_sql.py`)
- [x] **Add ARCHITECTURE.md** -- Full repo walkthrough with data flow diagram, layer breakdown, tradeoffs, and tech stack table.
- [x] **Fix semantic cache serving wrong results** -- Rewrote `cache.py`: Chroma checked BEFORE the LLM (was backwards), switched to cosine metric (was L2), added TTL to Chroma entries, new collection name (`query_cache_v2`) to abandon stale L2 data. Gibberish and unrelated questions no longer get false cache hits.
- [x] **Enrich schema with foreign keys** -- `schema.py` now introspects `information_schema.KEY_COLUMN_USAGE` and includes FK refs (e.g. `department_id (int) [references departments(id)]`) so the LLM knows how to join tables.
- [x] **Improve text-to-SQL prompt** -- Added domain semantics (admitted = visits, department names only in departments.name), two few-shot examples, and a safety-net override for "admitted last week" queries. (`backend/text_to_sql.py`)
- [x] **Add department_id to appointments** -- `01-init.sql` updated; migration script added for existing volumes (`docker/mysql/migrate-appointments-department.sql`).
- [x] **Fix Dockerfile BuildKit dependency** -- Replaced `RUN --mount=type=cache` with plain `pip install --no-cache-dir`.
- [x] **Add integration test suites** -- `tests/test_cache_behavior.py` (cache correctness) and `tests/test_sql_generation.py` (SQL quality + safety).

## Pending

- [ ] **Add active cache invalidation** -- Both cache tiers (in-memory + ChromaDB) rely on TTL-only expiration (default 300s). Consider invalidating on schema changes or periodic DB checksums so stale data doesn't linger.
- [ ] **Add authentication / RBAC** -- Streamlit has no built-in auth. For multi-user production, add session-based login or integrate with an identity provider (e.g. Streamlit's `st.experimental_user`, or an OAuth proxy).
- [x] **Add conversation history** -- Chat-style UI with `st.chat_message`; `backend/memory.py` formats last N turns into LLM context; follow-ups like "now show that by month" resolve against prior questions/SQL. Sidebar shows turn count and clear button.
- [ ] **Expand chart types** -- Only bar and line charts are supported. Add pie charts, stacked bars, and multi-series line charts. Extend `result_metadata.py` inference and `streamlit_app.py` rendering.
- [x] **Add unit tests that don't require Docker** -- `tests/test_unit.py` (74 tests, <1s) covers `sql_guards.py`, `result_metadata.py`, `sql_executor.validate_read_only`/`normalize_sql`, and `_extract_sql`/`_fix_bare_alias_joins`. Heavy deps stubbed with MagicMock. Also fixed a bug in `_extract_sql` that failed to strip ` ```sql ` language tags from markdown fences.
- [ ] **Extend SQL guard vocabulary** -- Current YAML guards support `all_present` / `any_missing` keyword checks. Consider adding regex pattern support or negative lookbehind for more expressive rules as the schema grows.
