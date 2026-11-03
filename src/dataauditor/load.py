import itertools
from dataclasses import dataclass
from pathlib import Path

import duckdb

_counter = itertools.count(1)


class UnreadableFile(Exception):
    """The file could not be read as CSV or Parquet."""


@dataclass
class Table:
    path: Path
    name: str  # DuckDB view name
    rows: int
    columns: dict[str, str]  # column name -> DuckDB type, in file order


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def quote_str(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def _read_sql(reader: str, path: Path, options: str) -> str:
    return f"SELECT * FROM {reader}({quote_str(path.as_posix())}{options})"


def _unparsable_columns(con, path: Path, options: str) -> list[str]:
    """Names of non-text columns whose values do not all convert to the sniffed type."""
    probe = f"audit_probe_{next(_counter)}"
    con.execute(f"CREATE VIEW {quote_ident(probe)} AS {_read_sql('read_csv', path, options)}")
    try:
        described = con.execute(f"DESCRIBE {quote_ident(probe)}").fetchall()
        bad = []
        for column, kind in ((row[0], row[1]) for row in described):
            if kind == "VARCHAR":
                continue
            try:
                con.execute(f"SELECT max(hash({quote_ident(column)})) FROM {quote_ident(probe)}").fetchall()
            except duckdb.Error:
                bad.append(column)
        return bad
    finally:
        con.execute(f"DROP VIEW {quote_ident(probe)}")


def _load_csv(con, name: str, path: Path, options: str) -> None:
    """Read the CSV once into a temp table, so the checks do not re-parse the file per query."""
    create = f"CREATE TEMP TABLE {quote_ident(name)} AS "
    try:
        con.execute(create + _read_sql("read_csv", path, options))
    except duckdb.Error:
        # The sniffed type does not fit every value (for example dates in two
        # formats). Keep those columns as text so the checks can see them.
        as_text = _unparsable_columns(con, path, options)
        if not as_text:
            raise
        types = ", ".join(f"{quote_str(c)}: 'VARCHAR'" for c in as_text)
        con.execute(create + _read_sql("read_csv", path, f"{options}, types={{{types}}}"))


def open_table(con: duckdb.DuckDBPyConnection, path: Path) -> Table:
    # sample_size=-1 sniffs types from every row, not just the first ones, so a
    # column whose format changes late (mixed date formats) loads as text.
    # A CSV is materialized once into a temp table; Parquet stays a lazy view.
    reader = {".csv": "read_csv", ".parquet": "read_parquet"}.get(path.suffix.lower())
    options = ", sample_size=-1" if reader == "read_csv" else ""
    if reader is None:
        raise UnreadableFile(f"{path}: unsupported file type '{path.suffix}'")
    try:
        empty = path.stat().st_size == 0
    except OSError as exc:
        raise UnreadableFile(f"{path}: {exc}") from exc
    if empty:  # DuckDB reads a 0-byte CSV as one phantom column with no rows
        raise UnreadableFile(f"{path}: file is empty")
    name = f"audit_table_{next(_counter)}"
    try:
        if reader == "read_csv":
            _load_csv(con, name, path, options)
        else:
            con.execute(f"CREATE VIEW {quote_ident(name)} AS {_read_sql(reader, path, options)}")
        described = con.execute(f"DESCRIBE {quote_ident(name)}").fetchall()
        rows = con.execute(f"SELECT count(*) FROM {quote_ident(name)}").fetchone()[0]
    except duckdb.Error as exc:
        raise UnreadableFile(f"{path}: {exc}") from exc
    return Table(path, name, rows, {row[0]: row[1] for row in described})
