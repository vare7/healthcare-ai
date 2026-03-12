# Guide: Docker Stack (App + MySQL + Ollama)

## 1. Start the full stack

From the project root:

```bash
docker compose up -d        # Docker Desktop / newer CLI
# or, on some setups:
docker-compose up -d
```

This brings up three services:

- `app` – Streamlit UI (port 8501).
- `mysql` – MySQL 8.0 with seeded `healthcare_db`.
- `ollama` – Ollama server for `llama3.2` and `nomic-embed-text`.

## 2. Pull Ollama models

Models are not baked into the image and must be pulled once:

```bash
docker exec -it healthcare-ai-ollama ollama pull llama3.2
docker exec -it healthcare-ai-ollama ollama pull nomic-embed-text
```

On Windows you can run:

```bash
scripts\pull-ollama-models.bat
```

Models are stored in the `ollama_data` volume and persist across container restarts.

## 3. Verify database seed data

The MySQL container runs seed scripts from `docker/mysql/`:

- `01-init.sql` – creates schema and initial small seed.
- `03-seed-100.sql` – truncates and inserts richer seed data.

You can verify counts:

```bash
mysql -h 127.0.0.1 -P 3306 -u readonly_user -p
USE healthcare_db;
SHOW TABLES;
SELECT COUNT(*) FROM patients;
SELECT COUNT(*) FROM appointments;
SELECT COUNT(*) FROM visits;
```

## 4. Reseed data (non-destructive to Ollama)

To reload the richer seed data without affecting Ollama models:

```bash
docker exec -i healthcare-ai-mysql mysql -uroot -prootpass healthcare_db < docker/mysql/03-seed-100.sql
```

This script truncates and repopulates the core tables, but only touches the `healthcare_db` schema.

## 5. Stop the stack

```bash
docker compose down        # or: docker-compose down
```

This stops containers but leaves volumes (including `ollama_data`) intact.

