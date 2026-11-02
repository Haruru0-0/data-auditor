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


def open_table(con: duckdb.DuckDBPyConnection, path: Path) -> Table:
    reader = {".csv": "read_csv", ".parquet": "read_parquet"}.get(path.suffix.lower())
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
        con.execute(
            f"CREATE VIEW {quote_ident(name)} AS "
            f"SELECT * FROM {reader}({quote_str(path.as_posix())})"
        )
        described = con.execute(f"DESCRIBE {quote_ident(name)}").fetchall()
        rows = con.execute(f"SELECT count(*) FROM {quote_ident(name)}").fetchone()[0]
    except duckdb.Error as exc:
        raise UnreadableFile(f"{path}: {exc}") from exc
    return Table(path, name, rows, {row[0]: row[1] for row in described})
