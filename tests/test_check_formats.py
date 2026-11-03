from dataauditor.checks.formats import check_formats
from dataauditor.load import open_table


def _run(con, csv, text):
    return check_formats(con, open_table(con, csv("t.csv", text)))


def _col(values, header="d"):
    return header + "\n" + "".join(f"{v}\n" for v in values)


def test_mixed_date_formats(con, csv):
    # pure mix, no extra text: DuckDB loads this one as VARCHAR
    values = ["05/01/2024"] * 8 + ["05.01.2024"] * 2
    (f,) = _run(con, csv, _col(values))
    assert (f.check, f.severity, f.column, f.count) == ("format", "warning", "d", 2)
    assert f.examples == ("05/01/2024", "05.01.2024")


def test_iso_and_slash_dates_with_a_text_value(con, csv):
    # DuckDB sniffs a pure ISO + slash mix as DATE and then fails to load it (loader issue),
    # so the text value keeps the column VARCHAR
    values = ["2024-01-05"] * 7 + ["05/01/2024"] * 2 + ["tbd"]
    (f,) = _run(con, csv, _col(values))
    assert f.count == 3
    assert f.message == "dates in 2 different formats (e.g. 2024-01-05, 05/01/2024)"
    assert f.message == "dates in 2 different formats (e.g. 2024-01-05, 05/01/2024)"
    assert f.examples == ("2024-01-05", "05/01/2024")


def test_one_date_format_is_clean(con, csv):
    # a trailing text value makes the column VARCHAR, but only one pattern matches
    assert _run(con, csv, _col(["2024-01-05"] * 9 + ["soon"])) == []


def test_eighty_percent_boundary(con, csv):
    at = ["2024-01-05"] * 6 + ["05/01/2024"] * 2 + ["soon"] * 2  # 8 of 10 match
    below = ["2024-01-05"] * 5 + ["05/01/2024"] * 2 + ["soon"] * 3  # 7 of 10 match
    assert len(_run(con, csv, _col(at))) == 1
    assert _run(con, csv, _col(below)) == []


def test_count_is_rows_outside_the_most_common_pattern(con, csv):
    values = ["2024-01-05"] * 5 + ["05/01/2024"] * 3 + ["05.01.2024"] * 2
    (f,) = _run(con, csv, _col(values))
    assert f.count == 5
    assert f.message.startswith("dates in 3 different formats (e.g. ")


def test_examples_limited_to_one_per_pattern_and_three(con, csv):
    values = (
        ["2024-01-05"] * 4 + ["2024/01/05"] * 3 + ["5/1/2024"] * 2 + ["5-1-2024"] + ["5.1.2024"]
    )
    (f,) = _run(con, csv, _col(values))
    assert len(f.examples) == 3
    assert f.examples[0] == "2024-01-05"


def test_datetime_is_its_own_pattern_and_values_are_trimmed(con, csv):
    values = ["2024-01-05"] * 4 + [" 2024-01-05 10:30"] + ["2024-01-05T10:30:15"]
    (f,) = _run(con, csv, _col(values))
    assert f.count == 2
    assert f.message.startswith("dates in 2 different formats")


def test_invalid_emails(con, csv):
    text = "email\na@b.com\nnot-an-email\n x@y.org \n@no.com\nname@host\n"
    (f,) = _run(con, csv, text)
    assert (f.check, f.severity, f.column, f.count) == ("format", "warning", "email", 3)
    assert f.message == "3 value(s) are not valid email addresses"
    assert set(f.examples) == {"not-an-email", "@no.com", "name@host"}


def test_email_name_tokens_and_unrelated_names(con, csv):
    text = "Work E-Mail,notes,hotel\nbad,bad,bad\nok@x.io,ok,ok\n"
    findings = _run(con, csv, text)
    assert [f.column for f in findings] == ["Work E-Mail"]


def test_clean_emails_and_blank_values(con, csv):
    assert _run(con, csv, 'email\na@b.com\n"  "\nc@d.org\n') == []


def test_invalid_phones(con, csv):
    text = (
        "phone\n+961 1 234 567\n12345\ncall me\n1234567890123456\n123456\n1234567\n"
        "123456789012345\n"
    )
    (f,) = _run(con, csv, text)
    assert (f.check, f.severity, f.column, f.count) == ("format", "warning", "phone", 4)
    assert f.message == "4 value(s) do not look like phone numbers"
    assert len(f.examples) == 3
    assert set(f.examples) <= {"12345", "call me", "1234567890123456", "123456"}


def test_phone_digit_boundaries(con, csv):
    assert _run(con, csv, "tel\n1234567\n123456789012345\n(555) 123-4567\n") == []
    assert len(_run(con, csv, "tel\n123-456\n")) == 1
    assert len(_run(con, csv, "tel\n1234-5678-9012-3456\n")) == 1


def test_phone_with_letters_is_invalid(con, csv):
    (f,) = _run(con, csv, "Mobile\n1234567x89\n5551234567\n")
    assert f.count == 1


def test_phone_name_tokens(con, csv):
    text = "telephone,mobile_no,photo\nabc,abc,abc\n"
    assert [f.column for f in _run(con, csv, text)] == ["telephone", "mobile_no"]


def test_examples_limited_to_three(con, csv):
    text = "email\n" + "".join(f"bad{i}\n" for i in range(6)) + "a@b.com\n"
    (f,) = _run(con, csv, text)
    assert f.count == 6 and len(f.examples) == 3


def test_non_varchar_columns_are_ignored(con, csv):
    assert _run(con, csv, "phone,email\n12,3\n45,6\n") == []


def test_quoted_and_spaced_column_names(con, csv):
    text = 'contact "main" mail,we"ird date\nbad,2024-01-05\nok@x.io,05/01/2024\n'
    findings = _run(con, csv, text)
    assert sorted(f.column for f in findings) == sorted(['contact "main" mail', 'we"ird date'])


def test_odd_date_column_name(con, csv):
    values = ["05/01/2024"] * 4 + ["05.01.2024"]
    (f,) = _run(con, csv, _col(values, header='we"ird date'))
    assert f.column == 'we"ird date'


def test_mixed_dates_in_parquet(con, tmp_path):
    path = tmp_path / "t.parquet"
    con.execute(
        "COPY (SELECT * FROM (VALUES ('2024-01-05'), ('2024-01-06'), ('05/01/2024')) t(d)) "
        f"TO '{path.as_posix()}' (FORMAT parquet)"
    )
    (f,) = check_formats(con, open_table(con, path))
    assert (f.column, f.count) == ("d", 1)


def test_header_only_is_empty(con, csv):
    assert _run(con, csv, "email,phone\n") == []


def test_email_and_phone_rules_need_the_token_last(con, csv):
    text = "phone_type,mail_status,email_domain,home_email,email_address\nabc,abc,abc,abc,abc\n"
    assert [f.column for f in _run(con, csv, text)] == ["home_email", "email_address"]


def test_phone_extension_is_ignored(con, csv):
    values = ["555.123.4567 x12", "555-123-4567 ext 5", "555-123-4567 EXT. 5", "555-123-4567 X123", "12 x1"]
    (f,) = _run(con, csv, "phone\n" + "".join(f"{v}\n" for v in values))
    assert f.count == 1 and f.examples == ("12 x1",)
