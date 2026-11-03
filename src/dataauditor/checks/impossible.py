import duckdb

from dataauditor.checks._names import is_numeric_type, is_temporal_type, name_tokens
from dataauditor.findings import Finding
from dataauditor.load import Table, quote_ident

# Not balance or amount: those can legitimately be negative.
NON_NEGATIVE = {"age", "quantity", "qty", "price", "salary", "count"}
PERCENT = {"percent", "percentage", "pct"}
BIRTH = {"birth", "birthday", "dob", "born"}
# An age column measured in units or grouped into bands legitimately exceeds 120.
NOT_A_YEAR_AGE = {
    "day", "days", "month", "months", "week", "weeks", "hour", "hours", "minute", "minutes",
    "second", "seconds", "group", "bucket", "band", "range", "limit", "threshold",
}
# A change, difference or net amount can legitimately be negative (price_change).
SIGNED = {"delta", "change", "diff", "difference", "adjustment", "variance", "net"}
MAX_AGE = 120
MAX_EXAMPLES = 3
MAX_SHOWN = 40


def _count_and_examples(con, view: str, q: str, condition: str) -> tuple[int, tuple[str, ...]]:
    count = con.execute(f"SELECT count(*) FROM {view} WHERE {condition}").fetchone()[0]
    if not count:
        return 0, ()
    shown = con.execute(
        f"SELECT DISTINCT {q} FROM {view} WHERE {condition} ORDER BY {q} LIMIT {MAX_EXAMPLES}"
    ).fetchall()
    return count, tuple(str(v)[:MAX_SHOWN] for (v,) in shown)


def check_impossible(con: duckdb.DuckDBPyConnection, table: Table) -> list[Finding]:
    if table.rows == 0 or not table.columns:
        return []
    view = quote_ident(table.name)
    findings = []

    def report(name: str, message: str, count: int, examples: tuple[str, ...]) -> None:
        findings.append(Finding("impossible", "warning", name, message, count, examples))

    for name, col_type in table.columns.items():
        tokens = set(name_tokens(name))
        q = quote_ident(name)
        if is_numeric_type(col_type):
            # NaN sorts above every number in DuckDB, so it would pass "> 120" and "> 100".
            not_nan = f" AND NOT isnan({q})" if col_type.upper() in ("FLOAT", "DOUBLE", "REAL") else ""
            if tokens & NON_NEGATIVE and not tokens & SIGNED:
                count, examples = _count_and_examples(con, view, q, f"{q} < 0")
                if count:
                    report(name, f"{count} negative value(s) in a column that should not be negative", count, examples)
            if "age" in tokens and not tokens & NOT_A_YEAR_AGE:
                count, examples = _count_and_examples(con, view, q, f"{q} > {MAX_AGE}{not_nan}")
                if count:
                    report(name, f"{count} value(s) above {MAX_AGE} in an age column", count, examples)
            if tokens & PERCENT:
                count, examples = _count_and_examples(con, view, q, f"({q} < 0 OR {q} > 100){not_nan}")
                if count:
                    report(name, f"{count} value(s) outside 0-100 in a percentage column", count, examples)
        elif is_temporal_type(col_type) and tokens & BIRTH:
            count, examples = _count_and_examples(con, view, q, f"{q} > current_date")
            if count:
                report(name, f"{count} date(s) in the future in a birth-date column", count, examples)
            count, examples = _count_and_examples(con, view, q, f"{q} < DATE '1900-01-01'")
            if count:
                report(name, f"{count} date(s) before 1900 in a birth-date column", count, examples)
    return findings
