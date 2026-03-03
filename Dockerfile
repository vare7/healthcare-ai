# syntax=docker/dockerfile:1
# Healthcare AI Assistant - Streamlit app
# Build with BuildKit for faster rebuilds: DOCKER_BUILDKIT=1 docker compose build
FROM python:3.12-slim

WORKDIR /app

# Install dependencies (cache mount reuses pip download cache between builds)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy application code
COPY config/ config/
COPY backend/ backend/
COPY streamlit_app.py .

# Run Streamlit (bind to 0.0.0.0 so Docker can forward the port)
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
