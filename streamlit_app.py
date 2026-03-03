"""Streamlit UI: plain-English query -> dynamic table / KPI / chart render."""
import sys
from datetime import date, datetime
from numbers import Number
from pathlib import Path

# Ensure project root is on path when running streamlit run streamlit_app.py
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import plotly.express as px

from backend.cache import query_with_cache
from config.settings import DEMO_MODE


def _format_metric_value(value):
    """Return a Streamlit-safe metric value for numeric/date/text KPIs."""
    if value is None:
        return "N/A"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Number):
        return value
    return str(value)


st.set_page_config(page_title="Healthcare AI Assistant", layout="wide")
st.title("Healthcare AI Assistant")
st.caption("Ask questions in plain English. Data stays local and read-only.")
if DEMO_MODE:
    st.info("Demo mode: using mock data (no MySQL/Ollama). Set DEMO_MODE=0 and configure .env for real data.")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(id(st.session_state))
session_id = st.session_state.session_id

question = st.text_input("Your question", placeholder="e.g. How many patients were admitted last week?")
if not question:
    st.stop()
with st.spinner("Generating query..."):
    result = query_with_cache(question, session_id=session_id)

if result.get("error"):
    st.error(result["error"])
    if result.get("sql"):
        with st.expander("Generated SQL"):
            st.code(result["sql"], language="sql")
    st.stop()

# From cache badge
if result.get("from_cache"):
    st.success("Served from cache")

# Optional: View SQL
if result.get("sql"):
    with st.expander("View generated SQL"):
        st.code(result["sql"], language="sql")

data = result.get("data", [])
result_type = result.get("result_type", "table")
chart_config = result.get("chart_config", {})
row_count = result.get("row_count", 0)

if not data:
    st.info("No rows returned.")
    st.stop()

df = pd.DataFrame(data)

if result_type == "kpi":
    label = df.columns[0]
    value = _format_metric_value(df.iloc[0, 0])
    st.metric(label=label, value=value)
elif result_type == "bar_chart":
    x_col = chart_config.get("x_column", df.columns[0])
    y_col = chart_config.get("y_column", df.columns[1])
    title = chart_config.get("title", f"{y_col} by {x_col}")
    fig = px.bar(df, x=x_col, y=y_col, title=title)
    st.plotly_chart(fig, use_container_width=True)
elif result_type == "line_chart":
    x_col = chart_config.get("x_column", df.columns[0])
    y_col = chart_config.get("y_column", df.columns[1])
    title = chart_config.get("title", f"{y_col} over {x_col}")
    fig = px.line(df, x=x_col, y=y_col, title=title)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.dataframe(df, use_container_width=True)

st.caption(f"Rows: {row_count}")
