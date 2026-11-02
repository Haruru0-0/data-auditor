from dataauditor.checks.duplicates import check_duplicates
from dataauditor.load import open_table


def _run(con, csv, text):
    return check_duplicates(con, open_table(con, csv("t.csv", text)))


def test_duplicate_rows_warning(con, csv):
    findings = _run(con, csv, "a,b\n1,x\n1,x\n2,y\n")
    assert len(findings) == 1
    f = findings[0]
    assert (f.check, f.severity, f.column, f.count) == ("duplicates", "warning", None, 1)


def test_duplicate_rows_count_extra_copies(con, csv):
    findings = _run(con, csv, "a,b\n1,x\n1,x\n1,x\n2,y\n2,y\n")
    assert len(findings) == 1
    assert findings[0].count == 3


def test_null_rows_count_as_equal(con, csv):
    findings = _run(con, csv, "a,b\n1,\n1,\n")
    assert [(f.column, f.count) for f in findings] == [(None, 1)]


def test_key_column_error(con, csv):
    findings = _run(con, csv, "user_id,n\n1,a\n1,b\n2,c\n")
    assert len(findings) == 1
    f = findings[0]
    assert (f.check, f.severity, f.column, f.count) == ("duplicates", "error", "user_id", 1)


def test_key_suffix_is_case_insensitive(con, csv):
    findings = _run(con, csv, "APIKey,n\nk,a\nk,b\n")
    assert [(f.severity, f.column, f.count) for f in findings] == [("error", "APIKey", 1)]


def test_plain_column_not_flagged(con, csv):
    assert _run(con, csv, "city,n\nParis,1\nParis,2\nRome,3\n") == []


def test_zero_rows_is_empty(con, csv):
    assert _run(con, csv, "user_id,b\n") == []


def test_nulls_in_key_column_not_duplicates(con, csv):
    assert _run(con, csv, "user_id,n\n,a\n,b\n1,c\n") == []


def test_non_ascii_and_quoted_names(con, csv):
    findings = _run(con, csv, 'né_id,"we""ird"\n1,a\n1,b\n')
    assert [(f.column, f.count) for f in findings] == [("né_id", 1)]


import pytest

from dataauditor.checks.duplicates import _is_key_like


@pytest.mark.parametrize(
    "name", ["id", "ID", "Key", "user_id", "order-key", "userId", "APIKey", "customer id", "a.id", "userID"]
)
def test_key_like_names(name):
    assert _is_key_like(name)


@pytest.mark.parametrize(
    "name", ["paid", "valid", "is_valid", "void", "grid", "android", "monkey", "hockey", "bid", "identity"]
)
def test_not_key_like_names(name):
    assert not _is_key_like(name)


def test_paid_column_with_repeats_gives_no_finding(con, csv):
    assert _run(con, csv, "paid,n\nyes,a\nyes,b\nno,c\n") == []
