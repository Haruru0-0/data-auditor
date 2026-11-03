import duckdb

from dataauditor.checks._names import is_numeric_type
from dataauditor.findings import Finding
from dataauditor.load import Table, quote_ident

MIN_VALUES = 20
Z_LIMIT = 6
Z_SCALE = 0.6745
MAX_EXAMPLES = 3

def _fmt(value: float) -> str:
    return str(int(value)) if value.is_integer() else str(value)


def check_outliers(con: duckdb.DuckDBPyConnection, table: Table) -> list[Finding]:
    if table.rows == 0 or not table.columns:
        return []
    view = quote_ident(table.name)
    findings = []
    for name, col_type in table.columns.items():
        if not is_numeric_type(col_type):
            continue
        col = quote_ident(name)
        base = (
            f"WITH vals AS (SELECT CAST({col} AS DOUBLE) AS x FROM {view} "
            f"WHERE {col} IS NOT NULL AND isfinite(CAST({col} AS DOUBLE))), "
            f"med AS (SELECT median(x) AS m, count(*) AS n FROM vals), "
            f"mad AS (SELECT median(abs(x - m)) AS d FROM vals, med), "
            f"z AS (SELECT x, {Z_SCALE} * (x - m) / d AS z FROM vals, med, mad "
            f"WHERE d > 0 AND n >= {MIN_VALUES}) "
        )
        count = con.execute(base + f"SELECT count(*) FROM z WHERE abs(z) > {Z_LIMIT}").fetchone()[0]
        if count == 0:
            continue
        rows = con.execute(
            base
            + f"SELECT x FROM z WHERE abs(z) > {Z_LIMIT} ORDER BY abs(z) DESC, x LIMIT {MAX_EXAMPLES}"
        ).fetchall()
        findings.append(
            Finding(
                check="outliers",
                severity="warning",
                column=name,
                message=f"{count} outlier value(s) far from the typical range (robust z-score above {Z_LIMIT})",
                count=count,
                examples=tuple(_fmt(r[0]) for r in rows),
            )
        )
    return findings
