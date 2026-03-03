"""Text-to-SQL using LangChain + Ollama. LLM receives only schema string (no row data)."""
import re

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from backend.schema import get_schema_string
from backend.sql_guards import apply_guards
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL


SYSTEM_PROMPT = """You are a read-only SQL assistant for a healthcare database.
Rules:
- Output only a single valid SELECT statement. No other text.
- Do not use INSERT, UPDATE, DELETE, DROP, ALTER, or any other write operations.
- You have access only to the following schema. Use only these tables and columns.
- ALWAYS use full table names in FROM and JOIN clauses (e.g. JOIN departments d, not JOIN d). An alias alone is not a table name.

Schema:
{schema}

Semantics:
- "Admitted", "admissions", "encounters" mean the visits table (visit_date = when the visit happened). Use visits.visit_date for time filters like "last week", "last month".
- "Last week" = visits where visit_date is within the past 7 days, e.g. visit_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY).
- "Appointments" = scheduled future or past appointments (appointments table, scheduled_at). Do not use appointments for "how many admitted" unless the question explicitly asks about appointments.
- Department names are ONLY in departments.name. To get a department name from visits or appointments, JOIN on department_id = departments.id.
- Patient names are in patients.first_name and patients.last_name. To get a patient name from visits or appointments, JOIN on patient_id = patients.id.
- "By department" or "per department" means GROUP BY departments.name after JOINing visits to departments.

Examples:
Question: How many patients were admitted last week?
SELECT COUNT(DISTINCT patient_id) FROM visits WHERE visit_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY);

Question: What department did Jane Doe visit?
SELECT DISTINCT d.name FROM visits v JOIN patients p ON v.patient_id = p.id JOIN departments d ON v.department_id = d.id WHERE p.first_name = 'Jane' AND p.last_name = 'Doe';

Question: Show admissions by department
SELECT d.name AS department, COUNT(*) AS admissions FROM visits v JOIN departments d ON v.department_id = d.id GROUP BY d.name;

{history_block}"""

USER_PROMPT = """Question: {question}"""


def _build_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ])
    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=0,
    )
    return prompt | llm | StrOutputParser()


_chain = None


def get_chain():
    global _chain
    if _chain is None:
        _chain = _build_chain()
    return _chain


def _build_history_block(history: str) -> str:
    if not history:
        return ""
    return (
        "Conversation so far (use this to resolve follow-up questions):\n"
        + history
    )


def generate_sql(
    question: str,
    schema_string: str | None = None,
    history: str = "",
) -> str:
    """
    Generate a single SELECT statement from a natural language question.
    Optionally receives formatted conversation history for follow-up resolution.
    """
    if schema_string is None:
        schema_string = get_schema_string()
    chain = get_chain()
    result = chain.invoke({
        "schema": schema_string,
        "question": question,
        "history_block": _build_history_block(history),
    })
    sql = _extract_sql(result)
    sql = apply_guards(question, sql)
    return sql


def _extract_sql(text: str) -> str:
    """Try to extract a single SELECT statement from LLM output (e.g. remove markdown)."""
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        for p in parts:
            p = p.strip()
            # Strip optional language tag (e.g. "sql\n..." -> "SELECT ...")
            if "\n" in p:
                first_line, rest = p.split("\n", 1)
                if not first_line.upper().startswith("SELECT"):
                    p = rest.strip()
            if p.upper().startswith("SELECT"):
                return _fix_bare_alias_joins(p)
    if text.upper().startswith("SELECT"):
        return _fix_bare_alias_joins(text)
    return text


_TABLE_ALIASES: dict[str, str] = {
    "d": "departments",
    "p": "patients",
    "v": "visits",
    "a": "appointments",
    "dept": "departments",
    "pat": "patients",
    "vis": "visits",
    "appt": "appointments",
}


def _fix_bare_alias_joins(sql: str) -> str:
    """Replace ``JOIN d ON`` with ``JOIN departments d ON`` when the LLM uses an alias as a table name."""
    for alias, table in _TABLE_ALIASES.items():
        sql = re.sub(
            rf'\bJOIN\s+{re.escape(alias)}\s+ON\b',
            f'JOIN {table} {alias} ON',
            sql,
            flags=re.IGNORECASE,
        )
    return sql


