# Healthcare AI Assistant

Fully local, privacy-first AI assistant for healthcare staff to query data in plain English. No SQL knowledge required.

- **Data never leaves your infrastructure** — Ollama runs locally; no cloud APIs.
- **Read-only DB** — LLM receives schema only; generated SQL is validated and executed read-only.
- **Rich UI** — Streamlit renders tables, KPI cards, and charts based on result type.
- **Smart caching** — In-memory + ChromaDB semantic cache for fast repeated/similar queries.
- **Audit log** — Every query logged (no PII) for compliance.

## Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # or: source .venv/bin/activate   # Linux/macOS
   ```
2. Install: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set MySQL (read-only user), Ollama URL, and paths.
4. For **demo mode** (no MySQL/Ollama): `python run_demo.py` or `DEMO_MODE=1 streamlit run streamlit_app.py`
5. For **full mode**: Run Ollama and pull models: `ollama pull llama3.2` and `ollama pull nomic-embed-text`. Then: `streamlit run streamlit_app.py`

## Tech stack

- **UI:** Streamlit
- **Backend:** Python, LangChain, Ollama (local LLM + embeddings)
- **DB:** MySQL (read-only)
- **Cache:** In-memory + ChromaDB
