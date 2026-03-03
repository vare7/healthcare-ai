"""Data-driven SQL post-generation guards loaded from config/sql_guards.yaml.

Each guard checks the user question and the generated SQL.  When the question
matches AND the SQL looks wrong (per the rule), the SQL is replaced with a
deterministic fallback.  See config/sql_guards.yaml for the rule format.
"""
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_GUARDS_PATH = Path(__file__).resolve().parent.parent / "config" / "sql_guards.yaml"
_guards: list[dict[str, Any]] | None = None


def _load_guards() -> list[dict[str, Any]]:
    global _guards
    if _guards is not None:
        return _guards
    if not _GUARDS_PATH.exists():
        logger.warning("SQL guards file not found: %s", _GUARDS_PATH)
        _guards = []
        return _guards
    with open(_GUARDS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    _guards = data.get("guards") or [] if data else []
    logger.info("Loaded %d SQL guard(s) from %s", len(_guards), _GUARDS_PATH)
    return _guards


def _question_matches(question: str, match: dict) -> bool:
    """True when the question satisfies the question_match block."""
    q = question.lower()
    any_of = match.get("any_of", [])
    if any_of and not any(phrase in q for phrase in any_of):
        return False
    also_any_of = match.get("also_any_of", [])
    if also_any_of and not any(phrase in q for phrase in also_any_of):
        return False
    return True


def _sql_is_bad(sql: str, bad_when: dict) -> bool:
    """True when the SQL violates the sql_bad_when conditions."""
    sql_upper = sql.upper()
    all_present = bad_when.get("all_present", [])
    if all_present and not all(kw.upper() in sql_upper for kw in all_present):
        return False
    any_missing = bad_when.get("any_missing", [])
    if any_missing and not any(kw.upper() not in sql_upper for kw in any_missing):
        return False
    return True


def _pick_fallback(question: str, fallbacks: list[dict]) -> str | None:
    """Return the first matching fallback SQL, or None."""
    q = question.lower()
    for entry in fallbacks:
        when = entry.get("when", "*")
        if when == "*" or when.lower() in q:
            return entry.get("sql")
    return None


def apply_guards(question: str, sql: str) -> str:
    """Run all guards against (question, sql).  Returns corrected SQL or original."""
    for guard in _load_guards():
        qm = guard.get("question_match", {})
        if not _question_matches(question, qm):
            continue
        bad = guard.get("sql_bad_when", {})
        if not _sql_is_bad(sql, bad):
            continue
        fallbacks = guard.get("fallback_sql", [])
        replacement = _pick_fallback(question, fallbacks)
        if replacement:
            logger.info(
                "Guard '%s' triggered — replacing SQL.\n  Original: %s\n  Replacement: %s",
                guard.get("name", "unnamed"), sql, replacement,
            )
            return replacement
    return sql
