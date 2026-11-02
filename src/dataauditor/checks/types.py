import duckdb

from dataauditor.findings import Finding
from dataauditor.load import Table, quote_ident

HIGH_SHARE = 0.95
LOW_SHARE = 0.05
MAX_EXAMPLES = 3


def _examples(con, view: str, col: str, cast_type: str) -> tuple[str, ...]:
    rows = con.execute(
        f"SELECT DISTINCT {col} FROM {view} "
        f"WHERE {col} IS NOT NULL AND TRY_CAST({col} AS {cast_type}) IS NULL "
        f"ORDER BY {col} LIMIT {MAX_EXAMPLES}"
    ).fetchall()
    return tuple(str(r[0]) for r in rows)


def check_types(con: duckdb.DuckDBPyConnection, table: Table) -> list[Finding]:
    if table.rows == 0 or not table.columns:
        return []
    view = quote_ident(table.name)
    findings = []
    for name, col_type in table.columns.items():
        if col_type != "VARCHAR":
            continue
        col = quote_ident(name)
        total, numeric, dates = con.execute(
            f"SELECT count({col}), count(TRY_CAST({col} AS DOUBLE)), "
            f"count(TRY_CAST({col} AS DATE)) FROM {view}"
        ).fetchone()
        if total == 0:
            continue
        num_share = numeric / total
        date_share = dates / total
        if HIGH_SHARE <= num_share < 1:
            kind, cast_type, bad = "numbers stored as text", "DOUBLE", total - numeric
        elif HIGH_SHARE <= date_share < 1 and num_share < HIGH_SHARE:
            kind, cast_type, bad = "dates stored as text", "DATE", total - dates
        elif LOW_SHARE <= num_share < HIGH_SHARE:
            findings.append(
                Finding(
                    check="types",
                    severity="warning",
                    column=name,
                    message=f"mixed types: {num_share * 100:.1f}% of values look numeric, the rest are text",
                    count=total - numeric,
                    examples=_examples(con, view, col, "DOUBLE"),
                )
            )
            continue
        else:
            continue
        findings.append(
            Finding(
                check="types",
                severity="warning",
                column=name,
                message=f"{kind}: {bad} of {total} non-null values do not fit",
                count=bad,
                examples=_examples(con, view, col, cast_type),
            )
        )
    return findings
