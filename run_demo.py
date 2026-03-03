"""Run Streamlit in demo mode (no MySQL/Ollama)."""
import os
import sys

os.environ["DEMO_MODE"] = "1"

# Run streamlit
from streamlit.web import cli as stcli

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "streamlit_app.py", "--server.headless", "true", "--server.port", "8502"]
    sys.exit(stcli.main())
