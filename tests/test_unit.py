"""
Unit tests that run WITHOUT Docker, MySQL, or Ollama.

Covers:
    - backend/sql_guards.py   (guard matching, fallback selection, apply_guards)
    - backend/result_metadata.py   (result_type inference + override)
    - backend/sql_executor.py   (validate_read_only, normalize_sql)
    - backend/text_to_sql.py   (_extract_sql, _fix_bare_alias_joins)

Run from repo root:
    python -m pytest tests/test_unit.py -v
"""
import os
import sys
import types
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

# Stub out heavy optional deps so we can import the modules under test
# without installing LangChain / Ollama / Streamlit.
for mod_name in (
    "langchain_ollama",
    "langchain_core",
    "langchain_core.prompts",
    "langchain_core.output_parsers",
    "langchain_core.runnables",
):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)

# Provide the specific names that text_to_sql.py imports at module level.
sys.modules["langchain_ollama"].ChatOllama = MagicMock()
sys.modules["langchain_core.prompts"].ChatPromptTemplate = MagicMock()
sys.modules["langchain_core.output_parsers"].StrOutputParser = MagicMock()
sys.modules["langchain_core.runnables"].RunnablePassthrough = MagicMock()


# ---------------------------------------------------------------------------
# sql_guards.py
# ---------------------------------------------------------------------------
from backend.sql_guards import (
    _question_matches,
    _sql_is_bad,
    _pick_fallback,
    apply_guards,
    _load_guards,
    _guards,
)


class TestQuestionMatches:
    """_question_matches: phrase-presence logic."""

    def test_any_of_hit(self):
        match = {"any_of": ["admitted", "admission"]}
        assert _question_matches("How many were admitted?", match)

    def test_any_of_miss(self):
        match = {"any_of": ["admitted", "admission"]}
        assert not _question_matches("List all departments", match)

    def test_also_any_of_both_hit(self):
        match = {"any_of": ["admitted"], "also_any_of": ["last week", "last month"]}
        assert _question_matches("patients admitted last week", match)

    def test_also_any_of_miss(self):
        match = {"any_of": ["admitted"], "also_any_of": ["last week", "last month"]}
        assert not _question_matches("patients admitted in 2023", match)

    def test_empty_match_always_true(self):
        assert _question_matches("anything at all", {})

    def test_case_insensitive(self):
        match = {"any_of": ["admitted"]}
        assert _question_matches("ADMITTED LAST WEEK", match)


class TestSqlIsBad:
    """_sql_is_bad: keyword presence/absence checks against generated SQL."""

    def test_all_present_all_found(self):
        bad_when = {"all_present": ["APPOINTMENTS", "VISITS", "JOIN", "COUNT"]}
        sql = "SELECT COUNT(*) FROM visits v JOIN appointments a ON v.patient_id = a.patient_id"
        assert _sql_is_bad(sql, bad_when)

    def test_all_present_one_missing(self):
        bad_when = {"all_present": ["APPOINTMENTS", "VISITS", "JOIN", "COUNT"]}
        sql = "SELECT COUNT(*) FROM visits WHERE visit_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
        assert not _sql_is_bad(sql, bad_when)

    def test_any_missing_one_absent(self):
        bad_when = {"any_missing": ["VISIT_DATE", "DATE_SUB"]}
        sql = "SELECT COUNT(*) FROM visits"
        assert _sql_is_bad(sql, bad_when)

    def test_any_missing_all_present(self):
        bad_when = {"any_missing": ["VISIT_DATE", "DATE_SUB"]}
        sql = "SELECT COUNT(*) FROM visits WHERE VISIT_DATE >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
        assert not _sql_is_bad(sql, bad_when)

    def test_combined_conditions(self):
        bad_when = {
            "all_present": ["APPOINTMENTS", "JOIN"],
            "any_missing": ["DATE_SUB"],
        }
        sql = "SELECT * FROM visits JOIN appointments ON 1=1"
        assert _sql_is_bad(sql, bad_when)

    def test_empty_bad_when_always_true(self):
        assert _sql_is_bad("SELECT 1", {})


class TestPickFallback:
    """_pick_fallback: ordered fallback selection by question phrase."""

    def test_exact_match(self):
        fallbacks = [
            {"when": "last month", "sql": "SQL_MONTH"},
            {"when": "*", "sql": "SQL_DEFAULT"},
        ]
        assert _pick_fallback("admitted last month", fallbacks) == "SQL_MONTH"

    def test_wildcard_default(self):
        fallbacks = [
            {"when": "last month", "sql": "SQL_MONTH"},
            {"when": "*", "sql": "SQL_DEFAULT"},
        ]
        assert _pick_fallback("admitted last week", fallbacks) == "SQL_DEFAULT"

    def test_first_match_wins(self):
        fallbacks = [
            {"when": "last", "sql": "SQL_FIRST"},
            {"when": "last week", "sql": "SQL_SECOND"},
        ]
        assert _pick_fallback("admitted last week", fallbacks) == "SQL_FIRST"

    def test_no_match_returns_none(self):
        fallbacks = [{"when": "last month", "sql": "SQL_MONTH"}]
        assert _pick_fallback("admitted yesterday", fallbacks) is None

    def test_empty_list(self):
        assert _pick_fallback("anything", []) is None


class TestApplyGuards:
    """apply_guards: end-to-end with the real YAML file."""

    def test_bad_sql_is_replaced(self):
        bad = (
            "SELECT COUNT(DISTINCT v.patient_id) FROM visits v "
            "JOIN appointments a ON v.patient_id = a.patient_id "
            "WHERE a.status = 'completed'"
        )
        result = apply_guards("How many patients were admitted last week?", bad)
        assert "DATE_SUB" in result
        assert "appointments" not in result.lower()

    def test_good_sql_unchanged(self):
        good = (
            "SELECT COUNT(DISTINCT patient_id) FROM visits "
            "WHERE visit_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
        )
        assert apply_guards("How many patients were admitted last week?", good) == good

    def test_unrelated_question_unchanged(self):
        sql = "SELECT * FROM departments"
        assert apply_guards("List all departments", sql) == sql

    def test_monthly_variant(self):
        bad = (
            "SELECT COUNT(*) FROM visits v JOIN appointments a "
            "ON v.patient_id = a.patient_id"
        )
        result = apply_guards("How many patients were admitted last month?", bad)
        assert "INTERVAL 30 DAY" in result

    def test_yesterday_variant(self):
        bad = (
            "SELECT COUNT(*) FROM visits v JOIN appointments a "
            "ON v.patient_id = a.patient_id"
        )
        result = apply_guards("How many patients were admitted yesterday?", bad)
        assert "INTERVAL 1 DAY" in result

    def test_no_guards_file(self):
        """When the YAML file doesn't exist, SQL passes through unchanged."""
        import backend.sql_guards as mod
        original = mod._guards
        mod._guards = None  # force reload
        with patch.object(mod, "_GUARDS_PATH", Path("/nonexistent/guards.yaml")):
            result = mod.apply_guards("admitted last week?", "SELECT 1")
            assert result == "SELECT 1"
        mod._guards = original  # restore


# ---------------------------------------------------------------------------
# result_metadata.py
# ---------------------------------------------------------------------------
from backend.result_metadata import (
    get_result_metadata,
    VALID_RESULT_TYPES,
    _infer_result_type,
)
import pandas as pd


class TestInferResultType:
    """_infer_result_type heuristic tests."""

    def test_empty_df_is_table(self):
        assert _infer_result_type(pd.DataFrame()) == "table"

    def test_single_cell_is_kpi(self):
        df = pd.DataFrame({"count": [42]})
        assert _infer_result_type(df) == "kpi"

    def test_one_row_multi_col_is_table(self):
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        assert _infer_result_type(df) == "table"

    def test_cat_num_is_bar(self):
        df = pd.DataFrame({"department": ["Cardiology", "Neurology"], "count": [10, 20]})
        assert _infer_result_type(df) == "bar_chart"

    def test_two_numeric_is_bar(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        assert _infer_result_type(df) == "bar_chart"

    def test_date_num_is_line(self):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2025-01-01", "2025-01-02"]),
            "value": [10, 20],
        })
        assert _infer_result_type(df) == "line_chart"

    def test_two_string_cols_is_table(self):
        df = pd.DataFrame({"name": ["Alice", "Bob"], "dept": ["A", "B"]})
        assert _infer_result_type(df) == "table"

    def test_multi_col_cat_num_is_bar(self):
        df = pd.DataFrame({
            "dept": ["A", "B"],
            "count": [10, 20],
            "extra": ["x", "y"],
        })
        assert _infer_result_type(df) == "bar_chart"


class TestGetResultMetadata:
    """get_result_metadata: end-to-end with override support."""

    def test_empty_rows(self):
        rtype, config = get_result_metadata([])
        assert rtype == "table"
        assert config == {}

    def test_kpi_inferred(self):
        rtype, config = get_result_metadata([{"total": 42}])
        assert rtype == "kpi"
        assert config == {}

    def test_bar_chart_has_config(self):
        rows = [{"dept": "A", "count": 10}, {"dept": "B", "count": 20}]
        rtype, config = get_result_metadata(rows)
        assert rtype == "bar_chart"
        assert "x_column" in config
        assert "y_column" in config

    def test_override_to_table(self):
        rows = [{"total": 42}]
        rtype, _ = get_result_metadata(rows, result_type_override="table")
        assert rtype == "table"

    def test_override_to_bar_chart(self):
        rows = [{"total": 42}]
        rtype, _ = get_result_metadata(rows, result_type_override="bar_chart")
        assert rtype == "bar_chart"

    def test_invalid_override_ignored(self):
        rows = [{"total": 42}]
        rtype, _ = get_result_metadata(rows, result_type_override="pie_chart")
        assert rtype == "kpi"  # falls back to inference

    def test_none_override_ignored(self):
        rows = [{"total": 42}]
        rtype, _ = get_result_metadata(rows, result_type_override=None)
        assert rtype == "kpi"

    def test_valid_result_types_constant(self):
        assert "table" in VALID_RESULT_TYPES
        assert "kpi" in VALID_RESULT_TYPES
        assert "bar_chart" in VALID_RESULT_TYPES
        assert "line_chart" in VALID_RESULT_TYPES


# ---------------------------------------------------------------------------
# sql_executor.py  (validate_read_only and normalize_sql only — no DB calls)
# ---------------------------------------------------------------------------
from backend.sql_executor import validate_read_only, normalize_sql


class TestNormalizeSql:
    """normalize_sql: comment stripping and whitespace."""

    def test_strips_inline_comment(self):
        assert normalize_sql("SELECT 1 -- comment") == "SELECT 1"

    def test_strips_hash_comment(self):
        assert normalize_sql("SELECT 1 # comment") == "SELECT 1"

    def test_strips_block_comment(self):
        assert normalize_sql("SELECT /* nope */ 1") == "SELECT 1"

    def test_normalizes_whitespace(self):
        assert normalize_sql("SELECT   1\n  FROM\ttable") == "SELECT 1 FROM table"

    def test_empty_string(self):
        assert normalize_sql("") == ""


class TestValidateReadOnly:
    """validate_read_only: accept SELECT, reject everything else."""

    def test_simple_select_ok(self):
        ok, err = validate_read_only("SELECT * FROM patients")
        assert ok
        assert err == ""

    def test_select_with_trailing_semicolon_ok(self):
        ok, err = validate_read_only("SELECT 1;")
        assert ok

    def test_insert_rejected(self):
        ok, err = validate_read_only("INSERT INTO patients VALUES (1, 'a')")
        assert not ok
        assert "SELECT" in err

    def test_update_rejected(self):
        ok, err = validate_read_only("UPDATE patients SET first_name='x'")
        assert not ok

    def test_delete_rejected(self):
        ok, err = validate_read_only("DELETE FROM patients")
        assert not ok

    def test_drop_rejected(self):
        ok, err = validate_read_only("DROP TABLE patients")
        assert not ok

    def test_select_with_delete_keyword_rejected(self):
        ok, err = validate_read_only("SELECT * FROM patients; DELETE FROM patients")
        assert not ok
        assert "single" in err.lower() or "forbidden" in err.lower()

    def test_multi_statement_rejected(self):
        ok, err = validate_read_only("SELECT 1; SELECT 2")
        assert not ok
        assert "single" in err.lower()

    def test_truncate_rejected(self):
        ok, err = validate_read_only("TRUNCATE TABLE patients")
        assert not ok

    def test_alter_rejected(self):
        ok, err = validate_read_only("ALTER TABLE patients ADD COLUMN age INT")
        assert not ok

    def test_create_rejected(self):
        ok, err = validate_read_only("CREATE TABLE evil (id INT)")
        assert not ok

    def test_select_with_subquery_ok(self):
        ok, err = validate_read_only(
            "SELECT * FROM patients WHERE id IN (SELECT patient_id FROM visits)"
        )
        assert ok

    def test_select_with_comments_ok(self):
        ok, err = validate_read_only("SELECT 1 -- just a test")
        assert ok

    def test_case_insensitive_rejection(self):
        ok, err = validate_read_only("insert into patients values (1)")
        assert not ok


# ---------------------------------------------------------------------------
# text_to_sql.py  (_extract_sql and _fix_bare_alias_joins — no LLM needed)
# ---------------------------------------------------------------------------
from backend.text_to_sql import _extract_sql, _fix_bare_alias_joins


class TestExtractSql:
    """_extract_sql: markdown stripping and SQL extraction."""

    def test_plain_select(self):
        assert _extract_sql("SELECT 1") == "SELECT 1"

    def test_strips_markdown_fences(self):
        text = "```sql\nSELECT * FROM patients\n```"
        result = _extract_sql(text)
        assert result.startswith("SELECT")
        assert "```" not in result

    def test_strips_plain_fences(self):
        text = "```\nSELECT 1\n```"
        result = _extract_sql(text)
        assert result == "SELECT 1"

    def test_multiple_fences_picks_select(self):
        text = "Here is the query:\n```sql\nSELECT 1\n```\nDone."
        result = _extract_sql(text)
        assert result == "SELECT 1"

    def test_leading_whitespace(self):
        assert _extract_sql("  SELECT 1  ").startswith("SELECT")

    def test_non_sql_passthrough(self):
        text = "I don't know how to answer that."
        assert _extract_sql(text) == text

    def test_lowercase_select_in_fence(self):
        text = "```\nselect 1\n```"
        result = _extract_sql(text)
        assert result == "select 1"

    def test_fence_with_lang_tag(self):
        text = "```sql\nSELECT * FROM visits\n```"
        result = _extract_sql(text)
        assert "visits" in result.lower()
        assert "```" not in result


class TestFixBareAliasJoins:
    """_fix_bare_alias_joins: rewrite alias-only JOINs to full table names."""

    def test_join_d_becomes_departments(self):
        sql = "SELECT * FROM visits v JOIN d ON v.department_id = d.id"
        fixed = _fix_bare_alias_joins(sql)
        assert "JOIN departments d ON" in fixed

    def test_join_p_becomes_patients(self):
        sql = "SELECT * FROM visits v JOIN p ON v.patient_id = p.id"
        fixed = _fix_bare_alias_joins(sql)
        assert "JOIN patients p ON" in fixed

    def test_join_a_becomes_appointments(self):
        sql = "SELECT * FROM visits v JOIN a ON v.patient_id = a.patient_id"
        fixed = _fix_bare_alias_joins(sql)
        assert "JOIN appointments a ON" in fixed

    def test_join_dept_becomes_departments(self):
        sql = "SELECT * FROM visits v JOIN dept ON v.department_id = dept.id"
        fixed = _fix_bare_alias_joins(sql)
        assert "JOIN departments dept ON" in fixed

    def test_correct_join_unchanged(self):
        sql = "SELECT * FROM visits v JOIN departments d ON v.department_id = d.id"
        assert _fix_bare_alias_joins(sql) == sql

    def test_multiple_bare_aliases(self):
        sql = "SELECT * FROM visits v JOIN d ON v.department_id = d.id JOIN p ON v.patient_id = p.id"
        fixed = _fix_bare_alias_joins(sql)
        assert "JOIN departments d ON" in fixed
        assert "JOIN patients p ON" in fixed

    def test_case_insensitive(self):
        sql = "SELECT * FROM visits v join D on v.department_id = D.id"
        fixed = _fix_bare_alias_joins(sql)
        assert "departments" in fixed.lower()

    def test_no_false_positive_on_table_name(self):
        """Should NOT mangle 'JOIN visits v ON' (table name, not bare alias)."""
        sql = "SELECT * FROM patients JOIN visits v ON patients.id = v.patient_id"
        assert _fix_bare_alias_joins(sql) == sql
