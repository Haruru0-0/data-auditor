from dataauditor.checks.skew import check_skew
from dataauditor.load import open_table


def _run(con, csv, text):
    return check_skew(con, open_table(con, csv("t.csv", text)))


def _col(values, header="c"):
    return header + "\n" + "".join(f"{v}\n" for v in values)


def test_dominant_value(con, csv):
    (f,) = _run(con, csv, _col(["a"] * 199 + ["b"]))
    assert (f.check, f.severity, f.column, f.count) == ("skew", "info", "c", 199)
    assert f.message == '99.5% of values are "a"'


def test_exactly_ninety_nine_percent_is_not_reported(con, csv):
    assert _run(con, csv, _col(["a"] * 99 + ["b"])) == []
    assert len(_run(con, csv, _col(["a"] * 100 + ["b"]))) == 1


def test_hundred_non_null_rows_boundary(con, csv):
    # 99 non-null rows (the rest empty) are too few even if one value dominates
    def col_c(n_a):
        text = "c,d\n" + "a,1\n" * n_a + "b,2\n" + ",3\n" * 50
        return [x for x in _run(con, csv, text) if x.column == "c"]

    assert col_c(98) == []  # 99 non-null rows
    assert len(col_c(100)) == 1  # 101 non-null rows


def test_constant_column_is_left_to_the_constant_check(con, csv):
    assert _run(con, csv, _col(["a"] * 200)) == []


def test_nulls_are_ignored(con, csv):
    text = "c,d\n" + ",1\n" * 150 + "a,1\n" * 199 + "b,1\n"
    (f,) = [x for x in _run(con, csv, text) if x.column == "c"]
    assert f.message == '99.5% of values are "a"' and f.count == 199


def test_numeric_column(con, csv):
    (f,) = _run(con, csv, _col([0] * 299 + [1], header="n"))
    assert f.message == '99.6% of values are "0"'


def test_percentage_is_not_rounded_up_to_100(con, csv):
    (f,) = _run(con, csv, _col(["a"] * 1999 + ["b"]))
    assert f.message == '99.9% of values are "a"'


def test_quoted_and_spaced_column_names(con, csv):
    (f,) = _run(con, csv, _col(["a"] * 199 + ["b"], header='we"ird name'))
    assert f.column == 'we"ird name'


def test_mostly_empty_rows(con, csv):
    text = "a,b,c,d,e\n1,2,3,4,5\n1,,,,\n1,2,,,\n,,,,\n1,2,3,,\n"
    (f,) = [x for x in _run(con, csv, text) if x.column is None]
    assert (f.check, f.severity, f.count) == ("skew", "warning", 2)
    assert f.message == "2 row(s) are mostly empty (80% or more of columns missing)"
    assert f.examples == ("2", "4")


def test_mostly_empty_threshold_at_eighty_percent(con, csv):
    # 4 of 5 empty counts, 3 of 5 does not
    assert len(_run(con, csv, "a,b,c,d,e\n1,,,,\n1,2,3,4,5\n")) == 1
    assert _run(con, csv, "a,b,c,d,e\n1,2,,,\n1,2,3,4,5\n") == []


def test_blank_strings_count_as_empty_for_varchar(con, csv):
    text = 'a,b,c\nx,y,z\n"  ","  ",q\n"","  ","  "\nr,s,t\n'
    (f,) = [x for x in _run(con, csv, text) if x.column is None]
    assert f.count == 1 and f.examples == ("3",)


def test_fewer_than_three_columns_is_not_checked(con, csv):
    assert _run(con, csv, "a,b\n1,2\n,\n") == []


def test_mostly_empty_examples_limited_to_three(con, csv):
    text = "a,b,c\n" + ",,\n" * 5 + "1,2,3\n"
    (f,) = _run(con, csv, text)
    assert f.count == 5 and f.examples == ("1", "2", "3")


def test_header_only_is_empty(con, csv):
    assert _run(con, csv, "a,b,c\n") == []
