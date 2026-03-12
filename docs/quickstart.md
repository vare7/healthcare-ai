# Quick Start

## Full stack in Docker (app + MySQL + Ollama)

Bring up the app, MySQL, and Ollama with one command from the repo root:

```bash
docker compose up -d        # Docker Desktop / newer CLI
# or, on some setups:
docker-compose up -d
```

- **App**: `http://localhost:8501` (Streamlit UI). The app container uses `mysql` and `ollama` as hostnames.
- **MySQL**: port 3306, seed DB `healthcare_db`, user `readonly_user` / `readonly_pass`. Wait ~30 seconds for first-time init.
- **Ollama**: port 11434. No models are included in the image.

Pull Ollama models (first time only; run after containers are up):

```bash
docker exec -it healthcare-ai-ollama ollama pull llama3.2
docker exec -it healthcare-ai-ollama ollama pull nomic-embed-text
```

On Windows you can also run:

```bash
scripts\\pull-ollama-models.bat
```

Stop everything:

```bash
docker compose down        # or: docker-compose down
```

## Run app on host (MySQL + Ollama in Docker)

If you prefer to run the app on your machine and only use Docker for MySQL and Ollama:

1. Comment out or remove the `app` service in `docker-compose.yml`.
2. Start infra:

   ```bash
   docker compose up -d        # or: docker-compose up -d
   ```

3. Create `.env` from the example and point it at Docker:

   ```bash
   cp .env.example .env
   # Set:
   # MYSQL_HOST=localhost
   # OLLAMA_BASE_URL=http://localhost:11434
   ```

4. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate  # Windows
   # or: source .venv/bin/activate  # Linux/macOS
   pip install -r requirements.txt
   ```

5. Run the UI from the project root:

   ```bash
   streamlit run streamlit_app.py
   ```

## Demo mode (no MySQL / Ollama)

For a fully local demo that does not require MySQL or Ollama:

- Using the helper script:

  ```bash
  python run_demo.py
  ```

- Or with an environment variable:

  ```bash
  DEMO_MODE=1 streamlit run streamlit_app.py
  ```

In demo mode, responses come from mock data in `backend/cache.py` and no external services are required.

