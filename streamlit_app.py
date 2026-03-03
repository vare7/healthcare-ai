"""Streamlit UI: chat-style interface for plain-English healthcare queries."""
import sys
from datetime import date, datetime
from numbers import Number
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import plotly.express as px

from backend.cache import query_with_cache
from backend.memory import format_history
from backend.result_metadata import VALID_RESULT_TYPES, get_result_metadata
from config.settings import DEMO_MODE

_DISPLAY_LABELS: dict[str, str] = {
    "table": "Table",
    "kpi": "KPI Card",
    "bar_chart": "Bar Chart",
    "line_chart": "Line Chart",
}


def _format_metric_value(value):
    if value is None:
        return "N/A"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Number):
        return value
    return str(value)


def _render_result(result: dict, question: str):
    """Render a single query result (table / KPI / chart)."""
    if result.get("error"):
        st.error(result["error"])
        if result.get("sql"):
            with st.expander("Generated SQL"):
                st.code(result["sql"], language="sql")
        return

    if result.get("from_cache"):
        st.caption("Served from cache")

    if result.get("sql"):
        with st.expander("View generated SQL"):
            st.code(result["sql"], language="sql")

    data = result.get("data", [])
    if not data:
        st.info("No rows returned.")
        return

    df = pd.DataFrame(data)
    inferred_type = result.get("result_type", "table")
    row_count = result.get("row_count", 0)

    display_options = [_DISPLAY_LABELS.get(t, t) for t in VALID_RESULT_TYPES]
    default_idx = list(VALID_RESULT_TYPES).index(inferred_type) if inferred_type in VALID_RESULT_TYPES else 0

    chosen_label = st.selectbox(
        "Display as",
        display_options,
        index=default_idx,
        key=f"rt_{question}_{id(result)}",
    )
    chosen_type = VALID_RESULT_TYPES[display_options.index(chosen_label)]
    result_type, chart_config = get_result_metadata(data, result_type_override=chosen_type)

    if result_type == "kpi":
        label = df.columns[0]
        value = _format_metric_value(df.iloc[0, 0])
        st.metric(label=label, value=value)
    elif result_type == "bar_chart":
        x_col = chart_config.get("x_column", df.columns[0])
        y_col = chart_config.get("y_column", df.columns[min(1, len(df.columns) - 1)])
        title = chart_config.get("title", f"{y_col} by {x_col}")
        fig = px.bar(df, x=x_col, y=y_col, title=title)
        st.plotly_chart(fig, use_container_width=True)
    elif result_type == "line_chart":
        x_col = chart_config.get("x_column", df.columns[0])
        y_col = chart_config.get("y_column", df.columns[min(1, len(df.columns) - 1)])
        title = chart_config.get("title", f"{y_col} over {x_col}")
        fig = px.line(df, x=x_col, y=y_col, title=title)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(df, use_container_width=True)

    st.caption(f"Rows: {row_count}")


# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(page_title="Healthcare AI Assistant", layout="wide")

# Sticky header that stays visible when chat history scrolls.
st.markdown(
    """
    <style>
    div[data-testid="stAppViewBlockContainer"] > div:first-child {
        position: sticky;
        top: 0;
        z-index: 999;
        background: var(--background-color, white);
        padding-bottom: 0.25rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container():
    st.title("Healthcare AI Assistant")
    st.caption("Ask questions in plain English. Follow-up questions use conversation context.")
    if DEMO_MODE:
        st.info("Demo mode: using mock data (no MySQL/Ollama). Set DEMO_MODE=0 and configure .env for real data.")

# ── Session state ─────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(id(st.session_state))
if "messages" not in st.session_state:
    st.session_state.messages = []
if "turns" not in st.session_state:
    st.session_state.turns = []

session_id = st.session_state.session_id

# ── Render conversation history ───────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            _render_result(msg["result"], msg["question"])

# ── Chat input ────────────────────────────────────────────────────────────
if question := st.chat_input("e.g. How many patients were admitted last week?"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    history_str = format_history(st.session_state.turns)

    with st.chat_message("assistant"):
        with st.spinner("Generating query..."):
            result = query_with_cache(
                question,
                session_id=session_id,
                history=history_str,
            )
        _render_result(result, question)

    st.session_state.messages.append({
        "role": "assistant",
        "content": "",
        "result": result,
        "question": question,
    })

    st.session_state.turns.append({
        "question": question,
        "sql": result.get("sql", ""),
        "result_type": result.get("result_type", "table"),
    })

# ── Sidebar: clear history ────────────────────────────────────────────────
with st.sidebar:
    st.header("Session")
    st.caption(f"Turns: {len(st.session_state.turns)}")
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.session_state.turns = []
        st.rerun()
