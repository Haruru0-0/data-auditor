from dataauditor.checks.missing import check_missing
from dataauditor.load import open_table


def _run(con, csv, text):
    return check_missing(con, open_table(con, csv("t.csv", text)))


def test_warning_at_five_percent(con, csv):
    lines = ["a,b"] + [f"{i},x" for i in range(19)] + ["19,"]
    findings = _run(con, csv, "\n".join(lines) + "\n")
    assert len(findings) == 1
    f = findings[0]
    assert (f.check, f.severity, f.column, f.count) == ("missing", "warning", "b", 1)
    assert "5.0% missing" in f.message


def test_below_threshold_is_clean(con, csv):
    lines = ["a,b"] + [f"{i},x" for i in range(99)] + ["99,"]
    assert _run(con, csv, "\n".join(lines) + "\n") == []


def test_all_null_column_is_single_error(con, csv):
    findings = _run(con, csv, "a,b\n1,\n2,\n3,\n")
    assert len(findings) == 1
    assert findings[0].severity == "error"
    assert findings[0].column == "b"
    assert findings[0].count == 3
    assert "100.0% missing" in findings[0].message


def test_header_only_is_empty(con, csv):
    assert _run(con, csv, "a,b\n") == []


def test_non_ascii_and_quoted_column_names(con, csv):
    text = 'né,"we""ird"\n' + ",\n,\n"
    findings = _run(con, csv, text)
    assert sorted(f.column for f in findings) == ['né', 'we"ird']
