# Healthcare AI Assistant

Fully local, privacy-first AI assistant for healthcare staff to query data in plain English. No SQL knowledge required.

- **Data never leaves your infrastructure** — Ollama runs locally; no cloud APIs.
- **Read-only DB** — LLM receives schema only; generated SQL is validated and executed read-only.
- **Rich UI** — Streamlit renders tables, KPI cards, and charts based on result type.
- **Smart caching** — In-memory + ChromaDB semantic cache for fast repeated/similar queries.
- **Audit log** — Every query logged (no PII) for compliance.

## Documentation & Architecture

- **Quick start** – see `docs/quickstart.md` for Docker and local setup.
- **Concepts** – see `docs/concepts.md` for text-to-SQL, caching, and safety.
- **Guides** – see `docs/guides/` for running locally, Docker stack details, demo prep, and Azure hosting.
- **API** – see `docs/api/` for backend and config reference.
- **Examples** – see `docs/examples/example-questions.md` for curated natural-language queries.
- **Architecture (full stack)** – `docs/architecture.md` (services, containers, components).
- **Architecture (pipeline & data flow)** – `docs/architecture-data-flow.md` (UI → caches → LLM → DB → charts).

