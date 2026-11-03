import re
from collections import Counter

import duckdb

from dataauditor.findings import Finding
from dataauditor.load import Table, quote_str

_UNNAMED = re.compile(r"^Unnamed: \d+$", re.IGNORECASE)
_NO_HEADER_NAME = re.compile(r"^column\d+$")


def _raw_header(con: duckdb.DuckDBPyConnection, table: Table) -> list[str | None] | None:
    try:
        row = con.execute(
            f"SELECT * FROM read_csv({quote_str(table.path.as_posix())}, header=false, all_varchar=true) LIMIT 1"
        ).fetchone()
    except duckdb.Error:
        return None
    return list(row) if row else None


def check_headers(con: duckdb.DuckDBPyConnection, table: Table) -> list[Finding]:
    if table.rows == 0 or not table.columns or table.path.suffix.lower() != ".csv":
        return []
    names = list(table.columns)
    # DuckDB names the columns column0, column1... when it found no header row at all.
    # Known limitation: a header of only blank cells, or literally named column0, column1, is skipped too.
    if all(_NO_HEADER_NAME.match(n) for n in names):
        return []
    raw = _raw_header(con, table)
    if raw is None or len(raw) != len(names):
        return []

    findings = []
    blank = [c for c in raw if c is None or c.strip() == ""]
    if blank:
        findings.append(
            Finding("header", "warning", None, f"{len(blank)} blank column name(s) in the header", len(blank))
        )

    trimmed = [c.strip() for c in raw if c is not None and c.strip() != ""]
    for name, n in Counter(trimmed).items():
        if n > 1:
            findings.append(
                Finding("header", "warning", name, f"column name appears {n} times in the header", n)
            )

    unnamed = [c for c in trimmed if _UNNAMED.match(c)]
    if unnamed:
        findings.append(
            Finding(
                "header",
                "warning",
                None,
                f'{len(unnamed)} column(s) named like "Unnamed: 0" (an exported index)',
                len(unnamed),
            )
        )

    for c in raw:
        if c is not None and c.strip() != "" and c != c.strip():
            findings.append(
                Finding("header", "warning", c.strip(), "column name has leading or trailing spaces", 1)
            )
    return findings
