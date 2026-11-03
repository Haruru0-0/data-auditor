import duckdb

from dataauditor.checks._names import name_tokens
from dataauditor.findings import Finding
from dataauditor.load import Table, quote_ident

# A name is key-like when "id" or "key" is a separate word at its end: the whole name,
# after a separator (_ - space .), or after a camelCase boundary (userId, APIKey).
# A plain suffix such as paid, valid, grid or monkey does not count.
def _is_key_like(name: str) -> bool:
    tokens = name_tokens(name)
    return bool(tokens) and tokens[-1] in ("id", "key")


def check_duplicates(con: duckdb.DuckDBPyConnection, table: Table) -> list[Finding]:
    if table.rows == 0 or not table.columns:
        return []
    view = quote_ident(table.name)
    names = list(table.columns)
    findings = []

    all_cols = ", ".join(quote_ident(n) for n in names)
    distinct_rows = con.execute(
        f"SELECT count(*) FROM (SELECT 1 FROM {view} GROUP BY {all_cols})"
    ).fetchone()[0]
    extra_rows = table.rows - distinct_rows
    if extra_rows > 0:
        findings.append(
            Finding(
                check="duplicates",
                severity="warning",
                column=None,
                message=f"{extra_rows} duplicate row(s) identical across all columns",
                count=extra_rows,
            )
        )

    for name in names:
        if not _is_key_like(name):
            continue
        q = quote_ident(name)
        extra = con.execute(
            f"SELECT count({q}) - count(DISTINCT {q}) FROM {view}"
        ).fetchone()[0]
        if extra > 0:
            findings.append(
                Finding(
                    check="duplicates",
                    severity="error",
                    column=name,
                    message=f"{extra} repeated value(s) in key-like column",
                    count=extra,
                )
            )
    return findings
