# Guide: Running Locally (App on Host)

## 1. Create a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# or: source .venv/bin/activate   # Linux/macOS
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Configure environment

Copy the example env file and edit as needed:

```bash
cp .env.example .env
```

Key variables:

- `MYSQL_HOST` – usually `localhost` when using Docker for MySQL.
- `MYSQL_PORT` – default `3306`.
- `MYSQL_USER` / `MYSQL_PASSWORD` – `readonly_user` / `readonly_pass` for the seeded DB.
- `MYSQL_DATABASE` – `healthcare_db`.
- `OLLAMA_BASE_URL` – e.g. `http://localhost:11434`.

## 4. Start MySQL + Ollama (via Docker)

From the project root:

```bash
docker compose up -d
```

Pull required Ollama models once:

```bash
docker exec -it healthcare-ai-ollama ollama pull llama3.2
docker exec -it healthcare-ai-ollama ollama pull nomic-embed-text
```

## 5. Run the Streamlit app

With your virtual environment activated and `.env` configured:

```bash
streamlit run streamlit_app.py
```

Open the browser at `http://localhost:8501` and start asking questions in plain English.

