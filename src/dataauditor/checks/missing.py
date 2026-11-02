import duckdb

from dataauditor.findings import Finding
from dataauditor.load import Table, quote_ident

WARN_FRACTION = 0.05


def check_missing(con: duckdb.DuckDBPyConnection, table: Table) -> list[Finding]:
    if table.rows == 0 or not table.columns:
        return []
    names = list(table.columns)
    selects = ", ".join(f"count(*) - count({quote_ident(n)})" for n in names)
    nulls = con.execute(f"SELECT {selects} FROM {quote_ident(table.name)}").fetchone()
    findings = []
    for name, null_count in zip(names, nulls):
        if null_count == 0:
            continue
        fraction = null_count / table.rows
        if fraction < WARN_FRACTION:
            continue
        severity = "error" if null_count == table.rows else "warning"
        findings.append(
            Finding(
                check="missing",
                severity=severity,
                column=name,
                message=f"{fraction * 100:.1f}% missing ({null_count} of {table.rows} rows)",
                count=null_count,
            )
        )
    return findings
