"""Determine result_type and chart_config from executed query result shape."""
from typing import Any

import pandas as pd


def _is_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)


def _is_datetime_or_date(series: pd.Series) -> bool:
    return pd.api.types.is_datetime64_any_dtype(series) or "date" in str(series.dtype).lower()


def _infer_result_type(df: pd.DataFrame) -> str:
    """Infer result_type from row count and column types."""
    if df.empty:
        return "table"
    nrows, ncols = len(df), len(df.columns)
    if nrows == 1 and ncols == 1:
        return "kpi"
    if nrows == 1 and ncols >= 2:
        # One row, multiple columns: could be KPI (one value) or table
        return "table"
    if ncols == 2:
        # Two columns: categorical + numeric -> bar; date/time + numeric -> line
        c0, c1 = df.iloc[:, 0], df.iloc[:, 1]
        if _is_numeric(c0) and _is_numeric(c1):
            return "bar_chart"
        if _is_datetime_or_date(c0) and _is_numeric(c1):
            return "line_chart"
        if _is_numeric(c0) and _is_datetime_or_date(c1):
            return "line_chart"
        # One cat, one num
        if _is_numeric(c0):
            return "bar_chart"  # cat in col1, num in col0
        if _is_numeric(c1):
            return "bar_chart"
        return "table"
    if ncols >= 2:
        # Try first two cols for chart
        c0, c1 = df.iloc[:, 0], df.iloc[:, 1]
        if _is_numeric(c1) and not _is_numeric(c0):
            return "bar_chart"
        if _is_datetime_or_date(c0) and _is_numeric(c1):
            return "line_chart"
    return "table"


def _infer_chart_config(df: pd.DataFrame, result_type: str) -> dict[str, Any]:
    """Build chart_config (x_column, y_column, title) when result_type is chart."""
    if result_type not in ("bar_chart", "line_chart") or df.empty or len(df.columns) < 2:
        return {}
    x_col = df.columns[0]
    y_col = df.columns[1]
    # If first column is numeric and second is not, swap for bar (categories on x)
    if _is_numeric(df.iloc[:, 0]) and not _is_numeric(df.iloc[:, 1]):
        x_col, y_col = df.columns[1], df.columns[0]
    return {
        "x_column": x_col,
        "y_column": y_col,
        "title": f"{y_col} by {x_col}",
    }


def get_result_metadata(rows: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    """
    Given executed query rows (list of dicts), return (result_type, chart_config).
    result_type is one of: table, kpi, bar_chart, line_chart.
    chart_config has x_column, y_column, title for charts; empty dict otherwise.
    """
    if not rows:
        return "table", {}
    df = pd.DataFrame(rows)
    result_type = _infer_result_type(df)
    chart_config = _infer_chart_config(df, result_type)
    return result_type, chart_config
