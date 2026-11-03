import duckdb

from dataauditor.findings import Finding
from dataauditor.load import Table, quote_ident

MAX_SHOWN = 40
MAX_EXAMPLES = 3
MIN_ROWS = 100
MIN_COLUMNS = 3


def _dominant(con, view: str, name: str, q: str) -> Finding | None:
    # Top value and the non-null total in one pass; the second row shows the column is not constant.
    rows = con.execute(
        f"""
        SELECT {q}::VARCHAR AS v, count(*) AS c, sum(count(*)) OVER () AS total
        FROM {view} WHERE {q} IS NOT NULL GROUP BY {q} ORDER BY c DESC, v LIMIT 2
        """
    ).fetchall()
    if len(rows) < 2:  # nothing, or constant (the constant check reports that)
        return None
    value, top, total = rows[0]
    total = int(total)
    # Integer form of top / total > 0.99, so exactly 99% is not reported.
    if total < MIN_ROWS or top * 100 <= 99 * total:
        return None
    pct = (top * 1000 // total) / 10  # truncated, so 99.96% never reads as 100.0%
    return Finding(
        check="skew",
        severity="info",
        column=name,
        message=f'{pct:.1f}% of values are "{value[:MAX_SHOWN]}"',
        count=top,
    )


def _mostly_empty_rows(con, table: Table, view: str) -> Finding | None:
    if len(table.columns) < MIN_COLUMNS:
        return None
    terms = []
    for name, col_type in table.columns.items():
        q = quote_ident(name)
        blank = f"{q} IS NULL OR trim({q}) = ''" if col_type.upper() == "VARCHAR" else f"{q} IS NULL"
        terms.append(f"CAST({blank} AS INTEGER)")
    empties = " + ".join(terms)
    rows = con.execute(
        f"""
        WITH r AS (SELECT row_number() OVER () AS rn, ({empties}) AS empty FROM {view})
        SELECT rn, count(*) OVER () FROM r WHERE empty * 100 >= 80 * {len(table.columns)}
        ORDER BY rn LIMIT {MAX_EXAMPLES}
        """
    ).fetchall()
    if not rows:
        return None
    count = rows[0][1]
    return Finding(
        check="skew",
        severity="warning",
        column=None,
        message=f"{count} row(s) are mostly empty (80% or more of columns missing)",
        count=count,
        examples=tuple(str(rn) for rn, _c in rows),
    )


def check_skew(con: duckdb.DuckDBPyConnection, table: Table) -> list[Finding]:
    if table.rows == 0 or not table.columns:
        return []
    view = quote_ident(table.name)
    findings = []
    for name in table.columns:
        found = _dominant(con, view, name, quote_ident(name))
        if found:
            findings.append(found)
    empty_rows = _mostly_empty_rows(con, table, view)
    if empty_rows:
        findings.append(empty_rows)
    return findings
