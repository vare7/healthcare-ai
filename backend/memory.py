"""Conversation memory: format recent turns into a context string for the LLM."""
from typing import Any

MAX_HISTORY_TURNS = 5


def format_history(turns: list[dict[str, Any]], max_turns: int = MAX_HISTORY_TURNS) -> str:
    """
    Convert the most recent turns into a compact string the LLM can use
    to resolve follow-up questions like "now show that by month".

    Each turn is a dict with at least:
        question (str), sql (str), result_type (str)

    Returns empty string when there's no usable history.
    """
    if not turns:
        return ""

    recent = turns[-max_turns:]
    lines: list[str] = []
    for t in recent:
        q = t.get("question", "")
        sql = t.get("sql", "")
        rt = t.get("result_type", "")
        if q and sql:
            lines.append(f"Q: {q}\nSQL: {sql}\nResult type: {rt}")

    if not lines:
        return ""
    return "\n\n".join(lines)
