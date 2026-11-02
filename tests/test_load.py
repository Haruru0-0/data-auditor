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
