from dataauditor.checks.markers import check_missing_markers
from dataauditor.load import open_table


def _run(con, csv, text):
    return check_missing_markers(con, open_table(con, csv("t.csv", text)))


def _col(values):
    return "c\n" + "".join(f"{v}\n" for v in values)


def test_flagged_at_exactly_one_percent(con, csv):
    findings = _run(con, csv, _col(["word"] * 99 + ["N/A"]))
    assert len(findings) == 1
    f = findings[0]
    assert (f.check, f.severity, f.column, f.count) == ("missing-marker", "warning", "c", 1)


def test_nothing_below_one_percent(con, csv):
    assert _run(con, csv, _col(["word"] * 100 + ["N/A"])) == []


def test_message_and_examples(con, csv):
    values = ["N/A"] * 3 + ["null"] * 2 + ["-", "none"] + ["word"] * 10
    f = _run(con, csv, _col(values))[0]
    assert f.count == 7
    assert f.message == '7 value(s) look like missing data (e.g. "N/A", "null", "-")'
    assert f.examples == ("N/A", "null", "-")


def test_case_insensitive_after_trim(con, csv):
    f = _run(con, csv, _col(["word", "word", '" NULL "', "Nil", "#N/A", "--", "?", "missing", "NaN"]))[0]
    assert f.count == 7


def test_na_is_not_a_marker(con, csv):
    assert _run(con, csv, _col(["NA", "NA", "word"])) == []


def test_empty_cells_are_not_counted_and_not_in_denominator(con, csv):
    f = _run(con, csv, _col(["word"] * 99 + ["N/A"] + [""] * 50))[0]
    assert f.count == 1


def test_entirely_markers_still_reported(con, csv):
    f = _run(con, csv, _col(["N/A", "null", "N/A"]))[0]
    assert (f.severity, f.count) == ("warning", 3)


def test_numeric_columns_are_skipped(con, csv):
    assert _run(con, csv, _col([1, 2, 3])) == []


def test_clean_text(con, csv):
    assert _run(con, csv, _col(["a", "b", "c"])) == []


def test_quoted_and_spaced_column_names(con, csv):
    findings = _run(con, csv, 'né,"we""ird name"\nx,N/A\ny,b\n')
    assert [f.column for f in findings] == ['we"ird name']


def test_header_only_is_empty(con, csv):
    assert _run(con, csv, "a,b\n") == []
