import duckdb

from dataauditor.findings import Finding
from dataauditor.load import Table, quote_ident

MAX_SHOWN = 40
MAX_EXAMPLES = 3
MIN_ROWS = 20
MIN_DISTINCT, MAX_DISTINCT = 2, 50
MIN_TYPO_LENGTH = 4


def _short(text: str) -> str:
    return text[:MAX_SHOWN]


# A value is a probable typo of a much more frequent one only when it differs by one inserted or
# deleted character, or by two adjacent characters swapped. Single-character substitutions are
# excluded on purpose: they join distinct real values (Omar/Omer, Maria/Mario, A1234/A1235).
# Values containing digits are skipped for the same reason (codes, years, ids).
def check_typos(con: duckdb.DuckDBPyConnection, table: Table) -> list[Finding]:
    if table.rows == 0 or not table.columns:
        return []
    view = quote_ident(table.name)
    varchars = [n for n, t in table.columns.items() if t.upper() == "VARCHAR"]
    if not varchars:
        return []
    # One pass over the table decides which columns are worth the pairwise comparison.
    gate = ", ".join(
        f"count(CASE WHEN trim({quote_ident(n)}) <> '' THEN 1 END), "
        f"count(DISTINCT nullif(trim({quote_ident(n)}), ''))"
        for n in varchars
    )
    row = con.execute(f"SELECT {gate} FROM {view}").fetchone()
    findings = []
    for i, name in enumerate(varchars):
        non_null, distinct = row[2 * i : 2 * i + 2]
        if non_null < MIN_ROWS or not MIN_DISTINCT <= distinct <= MAX_DISTINCT:
            continue
        q = quote_ident(name)
        pairs = con.execute(
            f"""
            WITH f AS (
                SELECT trim({q}) AS v, count(*) AS c FROM {view}
                WHERE {q} IS NOT NULL AND trim({q}) <> '' GROUP BY 1
            ),
            m AS (
                SELECT a.v AS typo, a.c AS n, b.v AS fix,
                    row_number() OVER (PARTITION BY a.v ORDER BY b.c DESC, b.v) AS rn
                FROM f a JOIN f b
                  ON lower(a.v) <> lower(b.v)
                 AND (
                    (abs(length(a.v) - length(b.v)) = 1
                        AND levenshtein(lower(a.v), lower(b.v)) = 1)
                    OR (length(a.v) = length(b.v)
                        AND list_bool_or(list_transform(range(1, length(a.v)),
                            i -> substr(lower(a.v), 1, i - 1) || substr(lower(a.v), i + 1, 1)
                                 || substr(lower(a.v), i, 1) || substr(lower(a.v), i + 2)
                                 = lower(b.v))))
                 )
                WHERE length(a.v) >= {MIN_TYPO_LENGTH}
                  AND NOT regexp_matches(a.v, '\\d') AND NOT regexp_matches(b.v, '\\d')
                  AND a.c * 10 <= b.c
                  AND a.c <= greatest(2, 0.02 * {non_null})
            )
            SELECT typo, n, fix FROM m WHERE rn = 1 ORDER BY n DESC, typo
            """
        ).fetchall()
        if not pairs:
            continue
        shown = tuple(f'"{_short(t)}" -> "{_short(w)}"' for t, _n, w in pairs[:MAX_EXAMPLES])
        total = sum(n for _t, n, _w in pairs)
        findings.append(
            Finding(
                check="typo",
                severity="warning",
                column=name,
                message=f"{total} value(s) look like typos (e.g. {shown[0]})",
                count=total,
                examples=shown,
            )
        )
    return findings
