# Guide: Demo Preparation (Engineering Audience)

This guide summarizes how to prepare for an engineering-focused demo that highlights natural-language-to-SQL and results.

## 1. Environment & data prep

- **Start full stack**
  - From repo root: `docker compose up -d`
  - Verify:
    - App: `http://localhost:8501`
    - MySQL: `docker ps` shows the MySQL container.
    - Ollama: `curl http://localhost:11434/api/tags` returns JSON.
- **Pull Ollama models (first time only)**
  - `docker exec -it healthcare-ai-ollama ollama pull llama3.2`
  - `docker exec -it healthcare-ai-ollama ollama pull nomic-embed-text`
- **Verify database seed data**
  - `mysql -h 127.0.0.1 -P 3306 -u readonly_user -p`
  - `USE healthcare_db;`
  - `SELECT COUNT(*) FROM patients;`
  - `SELECT COUNT(*) FROM visits;`
- **Pre-warm caches**
  - In the UI, ask 3–5 representative questions so ChromaDB and SQL caches are populated.

## 2. Core demo flows

- **Admissions KPI**
  - Question: “How many patients were admitted last week?”
  - Show:
    - KPI card.
    - Generated SQL (using `visits`).
    - `from_cache=False` on first run, `True` on repeat.
- **Visits by department (bar chart)**
  - Question: “Show the number of visits by department in the last 30 days.”
  - Show:
    - Bar chart (department vs. count).
    - GROUP BY SQL.
    - Manual “Display as” override to a table.
- **Daily trend (line chart)**
  - Question: “Show a line chart of daily visits over the last 60 days.”
  - Show:
    - Line chart (date vs. count).
    - How result type is inferred.
- **Safety**
  - Question: “Delete all patients.”
  - Show:
    - Error / safe handling.
    - Explain read-only validation and DB grants.

## 3. Failure / edge cases to be ready for

- **Models not pulled**
  - Symptom: LLM call fails.
  - Recovery: run the `ollama pull` commands above, retry query.
- **MySQL not ready**
  - Symptom: connection or table errors.
  - Recovery: check `docker ps` and `docker logs` for MySQL, wait for init, reseed if needed.
- **Slow first query**
  - Explain cold start (models, embeddings, DB) vs. fast cached queries.

