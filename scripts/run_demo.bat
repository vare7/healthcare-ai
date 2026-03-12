@echo off
rem Canonical Windows helper for running the app in demo mode from a venv.
set DEMO_MODE=1
.venv\Scripts\streamlit run streamlit_app.py --server.port 8502

