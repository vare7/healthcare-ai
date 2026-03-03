"""Text-to-SQL using LangChain + Ollama. LLM receives only schema string (no row data)."""
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from backend.schema import get_schema_string
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL


SYSTEM_PROMPT = """You are a read-only SQL assistant for a healthcare database.
Rules:
- Output only a single valid SELECT statement. No other text.
- Do not use INSERT, UPDATE, DELETE, DROP, ALTER, or any other write operations.
- You have access only to the following schema. Use only these tables and columns.

Schema:
{schema}
"""

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
    return (
        {"schema": RunnablePassthrough(), "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )


_chain = None


def get_chain():
    global _chain
    if _chain is None:
        _chain = _build_chain()
    return _chain


def generate_sql(question: str, schema_string: str | None = None) -> str:
    """
    Generate a single SELECT statement from a natural language question.
    Uses schema_string if provided; otherwise fetches from DB (read-only introspection).
    """
    if schema_string is None:
        schema_string = get_schema_string()
    chain = get_chain()
    # Chain expects two inputs; we pass same question for both slots and override schema in prompt
    # Actually our prompt has {schema} and {question} - so we need to invoke with dict
    result = chain.invoke({"schema": schema_string, "question": question})
    # Extract only the SQL (in case LLM adds markdown or explanation)
    sql = _extract_sql(result)
    return sql


def _extract_sql(text: str) -> str:
    """Try to extract a single SELECT statement from LLM output (e.g. remove markdown)."""
    text = text.strip()
    # Remove markdown code block if present
    if "```" in text:
        parts = text.split("```")
        for p in parts:
            p = p.strip()
            if p.upper().startswith("SELECT"):
                return p
    # Use as-is if it looks like SQL
    if text.upper().startswith("SELECT"):
        return text
    return text
