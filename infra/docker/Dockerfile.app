# Canonical Dockerfile for the Healthcare AI Assistant app image.
#
# The root-level `Dockerfile` remains for backwards compatibility and simply
# mirrors this configuration so existing `docker compose` workflows continue
# to work unchanged.

FROM python:3.12-slim

WORKDIR /app

# Install dependencies (cache mount reuses pip download cache between builds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config/ config/
COPY backend/ backend/
COPY streamlit_app.py .

# Run Streamlit (bind to 0.0.0.0 so Docker can forward the port)
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]

