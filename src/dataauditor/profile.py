import datetime
import decimal
import math

from dataauditor.checks._names import is_numeric_type, is_temporal_type
from dataauditor.load import Table, quote_ident


def _json_value(value):
    """JSON-safe form of an aggregate result: dates as ISO text, non-finite as None."""
    if value is None:
        return None
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, str):
        return value.replace(" ", "T", 1)  # a time-zone timestamp that was cast to text
    if isinstance(value, decimal.Decimal):
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def profile_columns(con, table: Table) -> dict[str, dict]:
    """Per-column statistics in file order, from one aggregate query over the table."""
    if not table.columns:
        return {}
    parts = []
    for column, col_type in table.columns.items():
        q = quote_ident(column)
        parts.append(f"count(*) - count({q}), count(DISTINCT {q})")
        if is_numeric_type(col_type) or is_temporal_type(col_type):
            # Time-zone types come back as text: Python would need pytz to convert them.
            as_text = "TIME ZONE" in col_type.upper()
            lo, hi = f"min({q})", f"max({q})"
            if as_text:
                lo, hi = f"CAST({lo} AS VARCHAR)", f"CAST({hi} AS VARCHAR)"
            parts.append(f"{lo}, {hi}")
        if is_numeric_type(col_type):
            parts.append(f"avg({q})")
    row = con.execute(f"SELECT {', '.join(parts)} FROM {quote_ident(table.name)}").fetchone()
    values = iter(row)
    result: dict[str, dict] = {}
    for column, col_type in table.columns.items():
        entry = {"type": col_type, "missing": next(values), "distinct": next(values)}
        if is_numeric_type(col_type) or is_temporal_type(col_type):
            entry["min"] = _json_value(next(values))
            entry["max"] = _json_value(next(values))
        if is_numeric_type(col_type):
            mean = _json_value(next(values))
            entry["mean"] = None if mean is None else round(mean, 4)
        result[column] = entry
    return result
