# Config Reference

Configuration is centralized in `config/settings.py` and is primarily driven by environment variables (usually set via `.env`).

Key variables include:

- `MYSQL_HOST` – hostname of the MySQL server (e.g., `localhost` or `mysql` in Docker).
- `MYSQL_PORT` – MySQL port (default `3306`).
- `MYSQL_USER` – database username (e.g., `readonly_user`).
- `MYSQL_PASSWORD` – database password.
- `MYSQL_DATABASE` – schema name (default `healthcare_db`).
- `OLLAMA_BASE_URL` – base URL for the Ollama server (e.g., `http://localhost:11434`).
- `OLLAMA_MODEL` – model name for text-to-SQL (default `llama3.2`).
- `OLLAMA_EMBEDDING_MODEL` – model name for embeddings (default `nomic-embed-text`).
- `CACHE_TTL_SECONDS` – TTL for cache entries (default `300` seconds).
- `CHROMA_PERSIST_PATH` – path where ChromaDB stores its data (e.g., `./chroma_data`).
- `CHROMA_SIMILARITY_THRESHOLD` – cosine similarity threshold for semantic cache hits (default `0.95`).
- `AUDIT_LOG_PATH` – path to the JSONL audit log file.
- `MAX_QUERY_ROWS` – maximum number of rows returned from a query (default `500`).
- `DEMO_MODE` – when set to `"1"`, bypasses MySQL and Ollama and uses mock responses.

Refer to `config/settings.py` for the authoritative list and default values.

