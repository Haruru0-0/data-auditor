from dataauditor.checks.headers import check_headers
from dataauditor.load import open_table


def _run(con, csv, text):
    return check_headers(con, open_table(con, csv("t.csv", text)))


def test_blank_header_cells(con, csv):
    findings = _run(con, csv, "a,,c\n1,2,3\n")
    assert len(findings) == 1
    f = findings[0]
    assert (f.check, f.severity, f.column, f.count) == ("header", "warning", None, 1)
    assert f.message == "1 blank column name(s) in the header"


def test_duplicate_names(con, csv):
    findings = _run(con, csv, "id,name,id\n1,x,2\n")
    assert len(findings) == 1
    f = findings[0]
    assert (f.column, f.count) == ("id", 2)
    assert f.message == "column name appears 2 times in the header"


def test_duplicates_are_case_sensitive_after_trim(con, csv):
    assert _run(con, csv, "id,Id\n1,2\n") == []
    findings = _run(con, csv, 'id," id"\n1,2\n')
    assert [(f.column, f.count) for f in findings if "appears" in f.message] == [("id", 2)]


def test_unnamed_index_leftovers(con, csv):
    findings = _run(con, csv, "Unnamed: 0,a\n0,1\n1,2\n")
    assert len(findings) == 1
    assert findings[0].column is None and findings[0].count == 1
    assert findings[0].message == '1 column(s) named like "Unnamed: 0" (an exported index)'


def test_unnamed_is_case_insensitive(con, csv):
    findings = _run(con, csv, "unnamed: 12,Unnamed: 3,a\n0,1,x\n")
    assert [f.count for f in findings] == [2]


def test_whitespace_in_header_cell(con, csv):
    findings = _run(con, csv, " name,age\nx,1\ny,2\n")
    assert len(findings) == 1
    f = findings[0]
    assert (f.column, f.count) == ("name", 1)
    assert f.message == "column name has leading or trailing spaces"


def test_clean_header(con, csv):
    assert _run(con, csv, "id,name\n1,x\n2,y\n") == []


def test_quoted_and_spaced_names(con, csv):
    findings = _run(con, csv, '"we""ird","we""ird",a b\n1,2,3\n')
    assert [(f.column, f.count) for f in findings] == [('we"ird', 2)]


def test_parquet_is_skipped(con, tmp_path):
    path = tmp_path / "t.parquet"
    con.execute(f"COPY (SELECT 1 AS a, 2 AS b) TO '{path.as_posix()}' (FORMAT parquet)")
    assert check_headers(con, open_table(con, path)) == []


def test_file_without_header_is_skipped(con, csv):
    assert _run(con, csv, "1,1\n2,3\n") == []


def test_column_count_mismatch_is_skipped(con, csv):
    table = open_table(con, csv("t.csv", "a,a\n1,2\n"))
    table.columns = {**table.columns, "extra": "VARCHAR"}
    assert check_headers(con, table) == []


def test_unreadable_file_returns_empty(con, csv, tmp_path):
    table = open_table(con, csv("t.csv", "a,a\n1,2\n"))
    table.path = tmp_path / "gone.csv"
    assert check_headers(con, table) == []


def test_header_only_is_empty(con, csv):
    assert _run(con, csv, "a,a\n") == []


def test_all_blank_header_is_skipped_known_limitation(con, csv):
    # DuckDB names such columns column0, column1... which is indistinguishable from "no header".
    assert _run(con, csv, ",,\n1,2,3\n") == []
