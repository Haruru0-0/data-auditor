import duckdb

from dataauditor.checks._names import is_temporal_type, name_tokens
from dataauditor.findings import Finding
from dataauditor.load import Table, quote_ident

MAX_EXAMPLES = 3
# (earlier word, later word)
WORD_PAIRS = (
    ("start", "end"),
    ("begin", "end"),
    ("from", "to"),
    ("created", "updated"),
    ("open", "close"),
    ("opened", "closed"),
    ("created", "deleted"),
    ("birth", "death"),
)


def _pairs(columns: dict[str, str]) -> list[tuple[str, str]]:
    """(earlier column, later column) pairs whose names differ only by a start/end word."""
    by_tokens: dict[tuple[str, ...], list[str]] = {}
    for name, col_type in columns.items():
        if is_temporal_type(col_type):
            by_tokens.setdefault(tuple(name_tokens(name)), []).append(name)
    pairs = []
    for later_tokens, later_names in by_tokens.items():
        for i, token in enumerate(later_tokens):
            for first, second in WORD_PAIRS:
                if token != second:
                    continue
                earlier_tokens = later_tokens[:i] + (first,) + later_tokens[i + 1 :]
                for earlier in by_tokens.get(earlier_tokens, []):
                    pairs += [(earlier, later) for later in later_names]
    return pairs


def check_date_order(con: duckdb.DuckDBPyConnection, table: Table) -> list[Finding]:
    if table.rows == 0 or not table.columns:
        return []
    view = quote_ident(table.name)
    findings = []
    for earlier, later in _pairs(table.columns):
        e, l = quote_ident(earlier), quote_ident(later)
        bad = f"{e} IS NOT NULL AND {l} IS NOT NULL AND {l} < {e}"
        count = con.execute(f"SELECT count(*) FROM {view} WHERE {bad}").fetchone()[0]
        if not count:
            continue
        shown = con.execute(
            f"SELECT DISTINCT {e}::VARCHAR, {l}::VARCHAR FROM {view} WHERE {bad} "
            f"ORDER BY 1, 2 LIMIT {MAX_EXAMPLES}"
        ).fetchall()
        findings.append(
            Finding(
                check="date-order",
                severity="warning",
                column=later,
                message=f'{count} row(s) where "{later}" is before "{earlier}"',
                count=count,
                examples=tuple(f"{a} > {b}" for a, b in shown),
            )
        )
    return findings
