import pytest

from dataauditor.load import UnreadableFile, open_table


def test_csv_rows_columns_and_types(con, csv):
    table = open_table(con, csv("t.csv", "id,name\n1,x\n2,y\n"))
    assert table.rows == 2
    assert list(table.columns) == ["id", "name"]
    assert table.columns["id"] == "BIGINT"


def test_header_only_csv_has_zero_rows(con, csv):
    table = open_table(con, csv("t.csv", "a,b\n"))
    assert table.rows == 0
    assert len(table.columns) == 2


def test_empty_file_raises_unreadable(con, csv):
    with pytest.raises(UnreadableFile):
        open_table(con, csv("t.csv", ""))


def test_bom_and_non_ascii_header(con, csv):
    table = open_table(con, csv("t.csv", "﻿id,naïve\n1,2\n"))
    assert list(table.columns) == ["id", "naïve"]


def test_duplicate_column_names_load(con, csv):
    table = open_table(con, csv("t.csv", "a,a\n1,2\n"))
    assert len(table.columns) == 2


def test_parquet_roundtrip(con, tmp_path):
    path = tmp_path / "t.parquet"
    con.execute(f"COPY (SELECT 1 AS x) TO '{path.as_posix()}' (FORMAT parquet)")
    table = open_table(con, path)
    assert table.rows == 1
    assert list(table.columns) == ["x"]


def test_unsupported_extension_raises_unreadable(con, tmp_path):
    path = tmp_path / "t.txt"
    path.write_text("a\n1\n")
    with pytest.raises(UnreadableFile):
        open_table(con, path)


def test_corrupt_parquet_raises_unreadable(con, tmp_path):
    path = tmp_path / "bad.parquet"
    path.write_bytes(b"not parquet")
    with pytest.raises(UnreadableFile):
        open_table(con, path)


def test_path_with_quote_and_space_and_unique_names(con, tmp_path):
    path = tmp_path / "it's a file.csv"
    path.write_text("a\n1\n", encoding="utf-8")
    first = open_table(con, path)
    second = open_table(con, path)
    assert first.name != second.name
    assert second.rows == 1


def test_late_format_change_does_not_break_the_file(con, csv):
    # DuckDB sniffs types from the first rows by default; a date column whose
    # format changes after that sample must load as text, not fail later.
    rows = ["id,d"] + [f"{i},2024-01-{i % 28 + 1:02d}" for i in range(25000)]
    rows += ["25000,05/01/2024", "25001,2024-02-10"]
    table = open_table(con, csv("late.csv", "\n".join(rows) + "\n"))
    assert table.columns["d"] == "VARCHAR"
    assert con.execute(f'SELECT count(d) FROM "{table.name}"').fetchone()[0] == 25002


@pytest.mark.parametrize("other", ["05/01/2024", "05.01.2024", "05-01-2024"])
def test_mixed_date_formats_load_as_text_and_keep_other_types(con, csv, other):
    rows = ["id,d"] + [f"{i},2024-01-{i % 28 + 1:02d}" for i in range(10)] + [f"10,{other}"]
    table = open_table(con, csv("mixed.csv", "\n".join(rows) + "\n"))
    assert table.columns["d"] == "VARCHAR"
    assert table.columns["id"] == "BIGINT"
    assert con.execute(f'SELECT count(d) FROM "{table.name}"').fetchone()[0] == 11


def test_columns_named_t_d_e_with_late_failures_load_as_text(con, csv):
    # A column called "t" must not break loading, and d and e (ISO dates until
    # the last row) fall back to text while t stays numeric.
    rows = ["t,d,e"] + [f"{i},2024-01-{i % 28 + 1:02d},2024-02-{i % 28 + 1:02d}" for i in range(49)]
    rows.append("50,01/02/2024,01/03/2024")
    table = open_table(con, csv("tde.csv", "\n".join(rows) + "\n"))
    assert table.columns == {"t": "BIGINT", "d": "VARCHAR", "e": "VARCHAR"}
    assert table.rows == 50


def test_csv_is_materialized_but_parquet_stays_a_view(con, csv, tmp_path):
    t = open_table(con, csv("a.csv", "a\n1\n"))
    kinds = dict(con.execute("SELECT table_name, table_type FROM information_schema.tables").fetchall())
    assert kinds[t.name] == "LOCAL TEMPORARY"
    path = tmp_path / "p.parquet"
    con.execute(f"COPY (SELECT 1 AS x) TO '{path.as_posix()}' (FORMAT parquet)")
    p = open_table(con, path)
    kinds = dict(con.execute("SELECT table_name, table_type FROM information_schema.tables").fetchall())
    assert kinds[p.name] == "VIEW"
