#!/usr/bin/env bash
# Pull required Ollama models into the healthcare-ai-ollama container.
# Run after: docker compose up -d
set -e
echo "Pulling llama3.2 (LLM for text-to-SQL)..."
docker exec healthcare-ai-ollama ollama pull llama3.2
echo "Pulling nomic-embed-text (embeddings for semantic cache)..."
docker exec healthcare-ai-ollama ollama pull nomic-embed-text
echo "Done. You can now run the app: streamlit run streamlit_app.py"
