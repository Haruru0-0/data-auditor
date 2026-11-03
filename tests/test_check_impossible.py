import pytest

from dataauditor.checks.impossible import check_impossible
from dataauditor.load import open_table


def _run(con, csv, text):
    return check_impossible(con, open_table(con, csv("t.csv", text)))


def test_negative_age(con, csv):
    findings = _run(con, csv, "age\n5\n-3\n40\n")
    assert len(findings) == 1
    f = findings[0]
    assert (f.check, f.severity, f.column, f.count) == ("impossible", "warning", "age", 1)
    assert f.message == "1 negative value(s) in a column that should not be negative"
    assert f.examples == ("-3",)


def test_age_above_120(con, csv):
    findings = _run(con, csv, "age\n130\n20\n121\n120\n")
    assert len(findings) == 1
    assert findings[0].message == "2 value(s) above 120 in an age column"
    assert findings[0].count == 2


def test_negative_and_too_old_are_separate_findings(con, csv):
    findings = _run(con, csv, "age\n-1\n150\n30\n")
    assert len(findings) == 2
    assert sorted(f.count for f in findings) == [1, 1]


@pytest.mark.parametrize("name", ["quantity", "qty", "price", "salary", "count", "userAge", "Unit_Price", "order qty"])
def test_negative_check_name_tokens(con, csv, name):
    findings = _run(con, csv, f'"{name}"\n1\n-2\n')
    assert [(f.column, f.count) for f in findings] == [(name, 1)]


def test_decimal_price(con, csv):
    findings = _run(con, csv, "price\n-1.5\n2.5\n")
    assert [f.count for f in findings] == [1]


@pytest.mark.parametrize("name", ["paid", "page", "usage", "balance", "amount", "ages", "image"])
def test_other_names_are_not_checked(con, csv, name):
    assert _run(con, csv, f"{name}\n-1\n-200\n") == []


def test_varchar_age_column_is_not_checked(con, csv):
    assert _run(con, csv, "age\nx\n-3\n") == []


def test_percentage(con, csv):
    findings = _run(con, csv, "completion_pct\n50\n101\n-1\n100\n0\n")
    assert len(findings) == 1
    f = findings[0]
    assert f.message == "2 value(s) outside 0-100 in a percentage column"
    assert f.count == 2


def test_percent_and_percentage_tokens(con, csv):
    assert len(_run(con, csv, "percent,discountPercentage\n101,5\n5,-2\n")) == 2


@pytest.mark.parametrize("name", ["date_of_birth", "DOB", "birthday", "born", "birthDate"])
def test_birth_date_columns(con, csv, name):
    findings = _run(con, csv, f"{name}\n1985-01-01\n2999-01-01\n1850-05-05\n")
    assert sorted(f.message for f in findings) == [
        "1 date(s) before 1900 in a birth-date column",
        "1 date(s) in the future in a birth-date column",
    ]
    assert all(f.column == name and f.count == 1 for f in findings)


def test_birth_timestamp_column(con, csv):
    findings = _run(con, csv, "dob\n1985-01-01 10:00:00\n2999-01-01 10:00:00\n")
    assert [f.message for f in findings] == ["1 date(s) in the future in a birth-date column"]


def test_birth_column_stored_as_text_is_skipped(con, csv):
    assert _run(con, csv, "birthday\nsoon\n2999-01-01x\n") == []


def test_clean_data(con, csv):
    assert _run(con, csv, "age,price,pct,dob\n30,2.5,50,1990-01-01\n41,3.5,99,1980-06-01\n") == []


def test_quoted_and_spaced_column_names(con, csv):
    findings = _run(con, csv, 'né,"we""ird age"\n1,-4\n2,5\n')
    assert [f.column for f in findings] == ['we"ird age']


def test_header_only_is_empty(con, csv):
    assert _run(con, csv, "age,price\n") == []


def test_age_with_unit_or_grouping_word_skips_the_above_120_rule(con, csv):
    assert _run(con, csv, "account_age_days\n400\n500\n") == []
    assert _run(con, csv, "ageBucket,age_range\n130,200\n1,2\n") == []
    # the negative rule is unchanged
    assert [f.count for f in _run(con, csv, "account_age_days\n-1\n500\n")] == [1]
    assert len(_run(con, csv, "age\n121\n20\n")) == 1


def test_nan_is_not_flagged(con, csv):
    assert _run(con, csv, "age\nnan\n20\n") == []
    assert _run(con, csv, "pct\nnan\n20.5\n") == []


def test_birth_date_boundaries(con, csv):
    import datetime

    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    findings = _run(con, csv, f"dob\n1899-12-31\n1900-01-01\n{today}\n{tomorrow}\n")
    assert sorted(f.message for f in findings) == [
        "1 date(s) before 1900 in a birth-date column",
        "1 date(s) in the future in a birth-date column",
    ]
    assert all(f.count == 1 for f in findings)
    assert findings[0].examples or findings[1].examples


@pytest.mark.parametrize("name", ["price_change", "stock_count_delta", "net_price", "qty_diff", "count_variance"])
def test_negative_allowed_in_change_like_columns(con, csv, name):
    assert _run(con, csv, f"{name}\n5\n-3\n") == []


def test_negative_price_still_flagged(con, csv):
    assert len(_run(con, csv, "unit_price\n5\n-3\n")) == 1
