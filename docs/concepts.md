# Concepts

## Text-to-SQL with schema-only context

The assistant converts plain-English questions into SQL using:

- `backend/text_to_sql.py` – LangChain + Ollama to generate a single `SELECT` statement.
- `backend/schema.py` – runtime introspection of `information_schema` to build a schema string that includes tables, columns, and foreign keys.

Only **schema** (table/column structure) is sent to the LLM – never row data. This keeps PHI out of the model context while still allowing the LLM to reason about relationships.

## Two-tier caching

Caching lives in `backend/cache.py` and has two layers:

- **ChromaDB semantic cache** (checked before the LLM call):
  - Embeds the question with `nomic-embed-text`.
  - Performs cosine similarity search over previous questions.
  - If a similar question is found (similarity ≥ threshold, within TTL), the cached result is returned without calling the LLM or database.
- **In-memory SQL cache** (checked after SQL generation):
  - Keyed by normalized SQL.
  - If the same SQL appears again, results are served from memory without hitting MySQL.

Together these significantly reduce latency and load for repeated or rephrased questions.

## Read-only safety

SQL safety is enforced in two places:

- `backend/sql_executor.py`:
  - `validate_read_only()` rejects anything that is not a single `SELECT`.
  - Blocks `INSERT`, `UPDATE`, `DELETE`, `DROP`, and similar statements via pattern checks.
- MySQL user:
  - The app connects as a read-only user defined in `docker/mysql/02-readonly-user.sql` with **SELECT-only** grants on `healthcare_db`.

Even if a prompt injection tricks the LLM into emitting dangerous SQL, it is blocked before execution and again at the DB permissions layer.

## Result type inference

`backend/result_metadata.py` inspects the shape and column types of the query result to infer:

- **KPI** – 1 row × 1 column.
- **Bar chart** – categorical + numeric columns (e.g., department + count).
- **Line chart** – date/time + numeric columns (e.g., day + admissions).
- **Table** – everything else.

The UI uses this `result_type` and a `chart_config` (x/y columns, title) to render with Streamlit + Plotly. Users can override the visualization type in the UI without re-running the query.

## Audit logging

Every query (cached or fresh) is logged by `backend/audit.py` to a JSONL file:

- Includes timestamp, `session_id`, truncated question text, SQL, `result_type`, row count, duration, and error (if any).
- **Never logs PII** (no patient names, IDs, or row data).

This supports basic compliance/audit requirements without adding external infrastructure.

