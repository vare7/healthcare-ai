# Healthcare AI Assistant

Fully local, privacy-first AI assistant for healthcare staff to query data in plain English. No SQL knowledge required.

- **Data never leaves your infrastructure** — Ollama runs locally; no cloud APIs.
- **Read-only DB** — LLM receives schema only; generated SQL is validated and executed read-only.
- **Rich UI** — Streamlit renders tables, KPI cards, and charts based on result type.
- **Smart caching** — In-memory + ChromaDB semantic cache for fast repeated/similar queries.
- **Audit log** — Every query logged (no PII) for compliance.

## Run full stack in Docker (app + MySQL + Ollama)

Bring up the app, MySQL, and Ollama with one command:

```bash
docker compose up -d
```

- **App**: http://localhost:8501 (Streamlit UI). The app container uses `mysql` and `ollama` as hostnames.
- **MySQL**: port 3306, seed DB `healthcare_db`, user `readonly_user` / `readonly_pass`. Wait ~30 s for first-time init.
- **Ollama**: port 11434. No models are included in the image.

**Pull Ollama models** (first time only; run after containers are up):

```bash
docker exec -it healthcare-ai-ollama ollama pull llama3.2
docker exec -it healthcare-ai-ollama ollama pull nomic-embed-text
```

Or use `scripts\pull-ollama-models.bat` (Windows) / `bash scripts/pull-ollama-models.sh` (Linux/macOS). Models persist in the `ollama_data` volume.

Stop everything: `docker compose down`.

**Faster rebuilds:** The Dockerfile uses BuildKit’s pip cache mount so dependency installs are cached between builds. Use `docker compose build` (BuildKit is default in Docker Desktop); code-only changes then rebuild in seconds.

---

## Run only MySQL + Ollama (app on host)

If you prefer to run the app on your machine and only use Docker for MySQL and Ollama, comment out or remove the `app` service in `docker-compose.yml`, then run `docker compose up -d`. Use `.env` with `MYSQL_HOST=localhost`, `OLLAMA_BASE_URL=http://localhost:11434`, and run `streamlit run streamlit_app.py` from the project root.

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
5. For **full mode**: With MySQL + Ollama running (e.g. `docker compose up -d` and models pulled via `scripts\pull-ollama-models.bat`), run: `streamlit run streamlit_app.py`

## Tech stack

- **UI:** Streamlit
- **Backend:** Python, LangChain, Ollama (local LLM + embeddings)
- **DB:** MySQL (read-only)
- **Cache:** In-memory + ChromaDB
