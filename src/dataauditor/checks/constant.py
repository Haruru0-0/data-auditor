import duckdb

from dataauditor.findings import Finding
from dataauditor.load import Table, quote_ident

MAX_SHOWN = 40


def check_constant(con: duckdb.DuckDBPyConnection, table: Table) -> list[Finding]:
    if table.rows == 0 or not table.columns:
        return []
    names = list(table.columns)
    selects = ", ".join(
        f"count({quote_ident(n)}), count(DISTINCT {quote_ident(n)}), "
        f"any_value({quote_ident(n)})::VARCHAR"
        for n in names
    )
    row = con.execute(f"SELECT {selects} FROM {quote_ident(table.name)}").fetchone()
    findings = []
    for i, name in enumerate(names):
        non_null, distinct, sample = row[3 * i : 3 * i + 3]
        # Fewer than 2 non-null values: nothing to compare (all-null is the missing check's job).
        if non_null < 2 or distinct != 1:
            continue
        findings.append(
            Finding(
                check="constant",
                severity="warning",
                column=name,
                message=f'every value is the same ("{sample[:MAX_SHOWN]}")',
                count=non_null,
            )
        )
    return findings
