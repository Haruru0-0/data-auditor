import duckdb

from dataauditor.findings import Finding
from dataauditor.load import Table, quote_ident

MAX_SHOWN = 40
MAX_EXAMPLES = 3


def _short(text: str) -> str:
    return text[:MAX_SHOWN]


def check_whitespace(con: duckdb.DuckDBPyConnection, table: Table) -> list[Finding]:
    if table.rows == 0 or not table.columns:
        return []
    view = quote_ident(table.name)
    findings = []
    for name, col_type in table.columns.items():
        if col_type.upper() != "VARCHAR":
            continue
        q = quote_ident(name)

        padded = con.execute(f"SELECT count(*) FROM {view} WHERE {q} <> trim({q})").fetchone()[0]
        if padded:
            shown = con.execute(
                f"SELECT DISTINCT {q} FROM {view} WHERE {q} <> trim({q}) ORDER BY {q} LIMIT {MAX_EXAMPLES}"
            ).fetchall()
            findings.append(
                Finding(
                    check="whitespace",
                    severity="warning",
                    column=name,
                    message=f"{padded} value(s) have leading or trailing spaces",
                    count=padded,
                    examples=tuple(repr(_short(v)) for (v,) in shown),
                )
            )

        # Forms of one normalised value, most frequent first; rn > 1 are the minority forms.
        forms = f"""
            WITH f AS (SELECT {q} AS v, count(*) AS c FROM {view} WHERE trim({q}) <> '' GROUP BY {q}),
            g AS (
                SELECT v, c,
                    row_number() OVER w AS rn,
                    first_value(v) OVER w AS top,
                    count(*) OVER (PARTITION BY lower(trim(v))) AS n_forms
                FROM f
                WINDOW w AS (PARTITION BY lower(trim(v)) ORDER BY c DESC, v)
            )
            SELECT v, c, top FROM g WHERE n_forms > 1 AND rn > 1 ORDER BY c DESC, v
        """
        minority = con.execute(forms).fetchall()
        if minority:
            pairs = [f'"{_short(top)}" / "{_short(v)}"' for v, _c, top in minority[:MAX_EXAMPLES]]
            total = sum(c for _v, c, _top in minority)
            findings.append(
                Finding(
                    check="whitespace",
                    severity="warning",
                    column=name,
                    message=(
                        f"{total} value(s) appear in more than one case or spacing (e.g. {pairs[0]})"
                    ),
                    count=total,
                    examples=tuple(pairs),
                )
            )
    return findings
