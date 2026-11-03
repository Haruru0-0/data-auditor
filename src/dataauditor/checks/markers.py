import duckdb

from dataauditor.findings import Finding
from dataauditor.load import Table, quote_ident, quote_str

# Not "na": it is a real country/language code.
MARKERS = ("n/a", "#n/a", "null", "none", "nan", "nil", "-", "--", "?", "missing")
MIN_FRACTION = 0.01
MAX_EXAMPLES = 3


def check_missing_markers(con: duckdb.DuckDBPyConnection, table: Table) -> list[Finding]:
    if table.rows == 0 or not table.columns:
        return []
    view = quote_ident(table.name)
    marker_list = ", ".join(quote_str(m) for m in MARKERS)
    findings = []
    for name, col_type in table.columns.items():
        if col_type.upper() != "VARCHAR":
            continue
        q = quote_ident(name)
        is_marker = f"lower(trim({q})) IN ({marker_list})"
        non_null, count = con.execute(
            f"SELECT count({q}), count(*) FILTER (WHERE {is_marker}) FROM {view}"
        ).fetchone()
        # Integer form of count / non_null >= 0.01, so exactly 1% is not lost to rounding.
        if count < 1 or count * 100 < non_null:
            continue
        spellings = con.execute(
            f"SELECT trim({q}) AS s FROM {view} WHERE {is_marker} "
            f"GROUP BY s ORDER BY count(*) DESC, s LIMIT {MAX_EXAMPLES}"
        ).fetchall()
        shown = tuple(s for (s,) in spellings)
        listed = ", ".join(f'"{s}"' for s in shown)
        findings.append(
            Finding(
                check="missing-marker",
                severity="warning",
                column=name,
                message=f"{count} value(s) look like missing data (e.g. {listed})",
                count=count,
                examples=shown,
            )
        )
    return findings
