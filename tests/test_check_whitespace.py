from dataauditor.checks.whitespace import check_whitespace
from dataauditor.load import open_table


def _run(con, csv, text):
    return check_whitespace(con, open_table(con, csv("t.csv", text)))


def test_leading_and_trailing_spaces(con, csv):
    findings = _run(con, csv, "city\n Beirut\nOslo\nLima \nBerlin\n")
    assert len(findings) == 1
    f = findings[0]
    assert (f.check, f.severity, f.column, f.count) == ("whitespace", "warning", "city", 2)
    assert f.message == "2 value(s) have leading or trailing spaces"
    assert set(f.examples) == {"' Beirut'", "'Lima '"}


def test_case_and_spacing_variants(con, csv):
    text = "city\n" + "Beirut\n" * 3 + "beirut\nBEIRUT \n" + "Oslo\n" * 2
    findings = _run(con, csv, text)
    variants = [f for f in findings if "more than one case" in f.message]
    assert len(variants) == 1
    f = variants[0]
    assert (f.check, f.severity, f.column, f.count) == ("whitespace", "warning", "city", 2)
    assert f.message.startswith("2 value(s) appear in more than one case or spacing (e.g. ")
    assert set(f.examples) == {'"Beirut" / "beirut"', '"Beirut" / "BEIRUT "'}
    assert len(findings) == 2  # the trailing space in "BEIRUT " is reported too


def test_same_form_repeated_is_clean(con, csv):
    assert _run(con, csv, "city\nBeirut\nBeirut\nOslo\n") == []


def test_non_varchar_columns_are_skipped(con, csv):
    assert _run(con, csv, "n\n1\n2\n3\n") == []


def test_examples_are_limited_to_three(con, csv):
    text = "c\n" + "".join(f" v{i}\n" for i in range(6)) + "ok\n"
    f = _run(con, csv, text)[0]
    assert f.count == 6 and len(f.examples) == 3


def test_quoted_and_spaced_column_names(con, csv):
    findings = _run(con, csv, 'né,"we""ird name"\nx, a\ny,b\n')
    assert [f.column for f in findings] == ['we"ird name']


def test_header_only_is_empty(con, csv):
    assert _run(con, csv, "a,b\n") == []


def test_blank_values_do_not_form_variant_groups(con, csv):
    findings = _run(con, csv, 'c\n"  "\n" "\nx\n')
    assert [f.message for f in findings] == ["2 value(s) have leading or trailing spaces"]
