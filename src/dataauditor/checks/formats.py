import duckdb

from dataauditor.checks._names import last_word
from dataauditor.findings import Finding
from dataauditor.load import Table, quote_ident, quote_str

MAX_SHOWN = 40
MAX_EXAMPLES = 3
MIN_DATE_SHARE = 0.8

# (label, regex) - the patterns do not overlap, so a value matches at most one.
DATE_PATTERNS = (
    ("YYYY-MM-DD", r"^\d{4}-\d{2}-\d{2}$"),
    ("YYYY/MM/DD", r"^\d{4}/\d{2}/\d{2}$"),
    ("DD/MM/YYYY or MM/DD/YYYY", r"^\d{1,2}/\d{1,2}/\d{4}$"),
    ("DD-MM-YYYY", r"^\d{1,2}-\d{1,2}-\d{4}$"),
    ("DD.MM.YYYY", r"^\d{1,2}\.\d{1,2}\.\d{4}$"),
    ("YYYY-MM-DD HH:MM[:SS]", r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?$"),
)
EMAIL_TOKENS = {"email", "mail"}
PHONE_TOKENS = {"phone", "mobile", "tel", "telephone"}
EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
MIN_DIGITS, MAX_DIGITS = 7, 15
# Words that may follow the key word: mobile_no, email_address.
FILLER = frozenset({"no", "num", "number", "nr", "address", "addr"})
# A trailing extension such as "x12", "ext 5" or "EXT. 5" is not part of the number.
EXTENSION_RE = r"(\s*ext\.?|[\s,;]+x)\s*\d+$"


def _short(text: str) -> str:
    return text[:MAX_SHOWN]


def _date_finding(con, view: str, name: str, q: str) -> Finding | None:
    whens = " ".join(
        f"WHEN regexp_matches(v, {quote_str(rx)}) THEN {quote_str(label)}"
        for label, rx in DATE_PATTERNS
    )
    rows = con.execute(
        f"""
        WITH t AS (SELECT trim({q}) AS v FROM {view} WHERE {q} IS NOT NULL AND trim({q}) <> ''),
        p AS (SELECT v, CASE {whens} END AS pattern FROM t)
        SELECT pattern, count(*), min(v) FROM p GROUP BY pattern ORDER BY count(*) DESC, pattern
        """
    ).fetchall()
    total = sum(n for _p, n, _v in rows)
    matched = [(n, v) for p, n, v in rows if p is not None]
    # Integer form of matched / total >= 0.8, so exactly 80% is not lost to rounding.
    if len(matched) < 2 or sum(n for n, _v in matched) * 10 < total * 8:
        return None
    shown = tuple(_short(v) for _n, v in matched[:MAX_EXAMPLES])
    top_count = matched[0][0]
    return Finding(
        check="format",
        severity="warning",
        column=name,
        message=f"dates in {len(matched)} different formats (e.g. {', '.join(shown[:2])})",
        count=total - top_count,
        examples=shown,
    )


def _count_and_examples(con, view: str, q: str, bad: str) -> tuple[int, tuple[str, ...]]:
    count = con.execute(f"SELECT count(*) FROM {view} WHERE {q} IS NOT NULL AND ({bad})").fetchone()[0]
    shown = con.execute(
        f"SELECT DISTINCT trim({q}) AS s FROM {view} WHERE {q} IS NOT NULL AND ({bad}) "
        f"ORDER BY s LIMIT {MAX_EXAMPLES}"
    ).fetchall()
    return count, tuple(_short(s) for (s,) in shown)


def check_formats(con: duckdb.DuckDBPyConnection, table: Table) -> list[Finding]:
    if table.rows == 0 or not table.columns:
        return []
    view = quote_ident(table.name)
    findings = []
    for name, col_type in table.columns.items():
        if col_type.upper() != "VARCHAR":
            continue
        q = quote_ident(name)
        word = last_word(name, FILLER)

        dates = _date_finding(con, view, name, q)
        if dates:
            findings.append(dates)

        if word in EMAIL_TOKENS:
            bad = f"trim({q}) <> '' AND NOT regexp_matches(trim({q}), {quote_str(EMAIL_RE)})"
            count, examples = _count_and_examples(con, view, q, bad)
            if count:
                findings.append(
                    Finding(
                        "format", "warning", name,
                        f"{count} value(s) are not valid email addresses", count, examples,
                    )
                )

        if word in PHONE_TOKENS:
            number = f"regexp_replace(trim({q}), {quote_str(EXTENSION_RE)}, '', 'i')"
            digits = f"length(regexp_replace({number}, '\\D', '', 'g'))"
            bad = (
                f"trim({q}) <> '' AND ({digits} < {MIN_DIGITS} OR {digits} > {MAX_DIGITS} "
                f"OR regexp_matches({number}, '\\pL'))"
            )
            count, examples = _count_and_examples(con, view, q, bad)
            if count:
                findings.append(
                    Finding(
                        "format", "warning", name,
                        f"{count} value(s) do not look like phone numbers", count, examples,
                    )
                )
    return findings
