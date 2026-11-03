from dataauditor.checks.constant import check_constant
from dataauditor.load import open_table


def _run(con, csv, text):
    return check_constant(con, open_table(con, csv("t.csv", text)))


def test_text_constant_column(con, csv):
    findings = _run(con, csv, "a,b\n1,x\n2,x\n3,x\n")
    assert len(findings) == 1
    f = findings[0]
    assert (f.check, f.severity, f.column, f.count) == ("constant", "warning", "b", 3)
    assert f.message == 'every value is the same ("x")'


def test_numeric_constant_column(con, csv):
    findings = _run(con, csv, "a,b\n5,x\n5,y\n")
    assert [(f.column, f.count, f.message) for f in findings] == [("a", 2, 'every value is the same ("5")')]


def test_varied_columns_are_clean(con, csv):
    assert _run(con, csv, "a,b\n1,x\n2,y\n3,x\n") == []


def test_nulls_are_ignored_when_counting(con, csv):
    findings = _run(con, csv, "a,b\n1,x\n2,\n3,x\n")
    assert [(f.column, f.count) for f in findings] == [("b", 2)]


def test_single_non_null_value_is_skipped(con, csv):
    assert _run(con, csv, "a,b\n1,x\n2,\n3,\n") == []


def test_all_null_column_is_skipped(con, csv):
    assert _run(con, csv, "a,b\n1,\n2,\n3,\n") == []


def test_long_value_is_truncated_to_40_chars(con, csv):
    findings = _run(con, csv, "a,b\n1," + "x" * 60 + "\n2," + "x" * 60 + "\n")
    assert findings[0].message == f'every value is the same ("{"x" * 40}")'


def test_quoted_and_spaced_column_names(con, csv):
    findings = _run(con, csv, 'né,"we""ird name"\n1,x\n2,x\n')
    assert [f.column for f in findings] == ['we"ird name']


def test_header_only_is_empty(con, csv):
    assert _run(con, csv, "a,b\n") == []
