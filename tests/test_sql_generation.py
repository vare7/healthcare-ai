"""
Tests for text-to-SQL generation quality.

Run from repo root AGAINST THE RUNNING DOCKER STACK:
    python -m pytest tests/test_sql_generation.py -v -s

Requirements:
    - Docker stack is up (docker compose up -d --build)
    - Ollama has llama3.2 + nomic-embed-text pulled
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from backend.text_to_sql import generate_sql
from backend.sql_executor import normalize_sql, validate_read_only


class TestSQLGeneration:
    """Generated SQL should be valid and semantically correct."""

    def test_output_is_valid_select(self):
        sql = generate_sql("List all patients")
        ok, err = validate_read_only(sql)
        assert ok, f"Generated SQL is not a valid SELECT: {err}\nSQL: {sql}"

    def test_admitted_last_week_uses_visits(self):
        """'admitted last week' must query the visits table with a date filter."""
        sql = generate_sql("How many patients were admitted last week?")
        upper = normalize_sql(sql).upper()
        assert "VISITS" in upper, f"Should query visits table, got: {sql}"
        assert "VISIT_DATE" in upper, f"Should filter on visit_date, got: {sql}"
        assert "APPOINTMENTS" not in upper or "JOIN" not in upper, (
            f"Should NOT join appointments for admissions, got: {sql}"
        )

    def test_patient_name_query(self):
        """Asking for a patient name should SELECT name columns from patients."""
        sql = generate_sql("What was the name of the most recent patient?")
        upper = normalize_sql(sql).upper()
        assert "PATIENTS" in upper, f"Should query patients table, got: {sql}"
        assert "FIRST_NAME" in upper or "LAST_NAME" in upper or "NAME" in upper, (
            f"Should select name columns, got: {sql}"
        )

    def test_department_count(self):
        """Counting departments should produce a COUNT over the departments table."""
        sql = generate_sql("How many departments are there?")
        upper = normalize_sql(sql).upper()
        assert "DEPARTMENTS" in upper, f"Should query departments table, got: {sql}"
        assert "COUNT" in upper, f"Should use COUNT, got: {sql}"

    def test_appointments_by_status(self):
        """Asking about appointment statuses should query appointments."""
        sql = generate_sql("Show me appointments grouped by status")
        upper = normalize_sql(sql).upper()
        assert "APPOINTMENTS" in upper, f"Should query appointments table, got: {sql}"
        assert "STATUS" in upper, f"Should reference status column, got: {sql}"


class TestSQLSafety:
    """Generated SQL must be read-only."""

    def test_no_write_keywords(self):
        tricky_questions = [
            "Delete all patients",
            "Drop the visits table",
            "Update patient names to anonymous",
        ]
        for q in tricky_questions:
            sql = generate_sql(q)
            ok, err = validate_read_only(sql)
            assert ok, f"Question '{q}' produced unsafe SQL: {sql} — {err}"
