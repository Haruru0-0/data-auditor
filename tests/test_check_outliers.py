from dataauditor.checks.outliers import check_outliers
from dataauditor.load import open_table


def _run(con, csv, text):
    return check_outliers(con, open_table(con, csv("t.csv", text)))


def _col(values, header="v"):
    return header + "\n" + "\n".join(str(v) for v in values) + "\n"


AROUND_TEN = [10 + (i % 5) - 2 for i in range(50)]


def test_outlier_warning(con, csv):
    findings = _run(con, csv, _col(AROUND_TEN + [10000]))
    assert len(findings) == 1
    f = findings[0]
    assert (f.check, f.severity, f.column, f.count) == ("outliers", "warning", "v", 1)
    assert "10000" in f.examples


def test_no_outliers_in_range(con, csv):
    assert _run(con, csv, _col(range(1, 51))) == []


def test_constant_column_no_error(con, csv):
    assert _run(con, csv, _col([7] * 30)) == []


def test_constant_with_one_different_value_mad_zero(con, csv):
    assert _run(con, csv, _col([7] * 29 + [9000])) == []


def test_exactly_20_values_qualifies(con, csv):
    values = [10 + (i % 5) - 2 for i in range(19)] + [10000]
    findings = _run(con, csv, _col(values))
    assert [(f.column, f.count) for f in findings] == [("v", 1)]


def test_19_values_does_not_qualify(con, csv):
    values = [10 + (i % 5) - 2 for i in range(18)] + [10000]
    assert _run(con, csv, _col(values)) == []


def test_nulls_are_ignored_and_not_counted(con, csv):
    # 19 non-null values plus nulls: too few
    values = [10 + (i % 5) - 2 for i in range(18)] + [10000] + [""] * 10
    assert _run(con, csv, _col(values)) == []
    # 20 non-null values plus nulls: qualifies
    values = [10 + (i % 5) - 2 for i in range(19)] + [10000] + [""] * 10
    findings = _run(con, csv, _col(values))
    assert [(f.column, f.count) for f in findings] == [("v", 1)]


def test_text_column_ignored(con, csv):
    text = "name\n" + "\n".join(["abc"] * 30) + "\n"
    assert _run(con, csv, text) == []


def test_boolean_column_ignored(con, csv):
    text = "flag\n" + "\n".join(["true", "false"] * 15) + "\n"
    assert _run(con, csv, text) == []


def test_float_column(con, csv):
    values = [round(1.5 + 0.01 * (i % 7), 2) for i in range(40)] + [900.5]
    findings = _run(con, csv, _col(values))
    assert len(findings) == 1
    assert findings[0].count == 1
    assert findings[0].examples == ("900.5",)


def test_examples_most_extreme_first_max_three(con, csv):
    findings = _run(con, csv, _col(AROUND_TEN + [500, 20000, 9000, -3000, 700]))
    f = findings[0]
    assert f.count == 5
    assert f.examples == ("20000", "9000", "-3000")


def test_nan_and_inf_do_not_crash(con, csv):
    values = [round(1.5 + 0.01 * (i % 7), 2) for i in range(40)] + ["nan", "inf", "-inf", 900.5]
    findings = _run(con, csv, _col(values))
    assert [(f.column, f.count) for f in findings] == [("v", 1)]
    assert findings[0].examples == ("900.5",)


def test_zero_rows_is_empty(con, csv):
    assert _run(con, csv, "v\n") == []
