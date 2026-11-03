from dataauditor.checks.dateorder import check_date_order
from dataauditor.load import open_table


def _run(con, csv, text):
    return check_date_order(con, open_table(con, csv("t.csv", text)))


def test_end_before_start(con, csv):
    text = "start_date,end_date\n2024-01-01,2024-02-01\n2024-03-01,2024-02-01\n"
    (f,) = _run(con, csv, text)
    assert (f.check, f.severity, f.column, f.count) == ("date-order", "warning", "end_date", 1)
    assert f.message == '1 row(s) where "end_date" is before "start_date"'
    assert f.examples == ("2024-03-01 > 2024-02-01",)


def test_camel_case_pair(con, csv):
    text = "startDate,endDate\n2024-03-01,2024-02-01\n"
    (f,) = _run(con, csv, text)
    assert f.column == "endDate"


def test_other_word_pairs(con, csv):
    cases = [
        ("date_from", "date_to"),
        ("created_at", "updated_at"),
        ("begin_day", "end_day"),
        ("open_date", "close_date"),
        ("opened", "closed"),
        ("created", "deleted"),
        ("birth_date", "death_date"),
    ]
    for earlier, later in cases:
        (f,) = _run(con, csv, f"{earlier},{later}\n2024-03-01,2024-02-01\n")
        assert f.column == later, (earlier, later)


def test_equal_dates_and_correct_order_are_clean(con, csv):
    text = "start_date,end_date\n2024-01-01,2024-01-01\n2024-01-01,2024-05-01\n"
    assert _run(con, csv, text) == []


def test_non_pair_does_not_match(con, csv):
    # different stems: start_date / end_time and start_date / end_day
    assert _run(con, csv, "start_date,end_time\n2024-03-01,2024-02-01\n") == []
    assert _run(con, csv, "start_date,end_day\n2024-03-01,2024-02-01\n") == []


def test_reversed_word_roles_are_not_a_pair(con, csv):
    text = "end_date,finish_date\n2024-03-01,2024-02-01\n"
    assert _run(con, csv, text) == []


def test_null_values_are_skipped(con, csv):
    text = "start_date,end_date\n2024-03-01,\n,2024-02-01\n2024-03-01,2024-02-01\n"
    (f,) = _run(con, csv, text)
    assert f.count == 1


def test_timestamp_columns(con, csv):
    text = "created_at,updated_at\n2024-03-01 10:00:00,2024-03-01 09:00:00\n"
    (f,) = _run(con, csv, text)
    assert f.column == "updated_at" and f.count == 1


def test_non_date_columns_are_ignored(con, csv):
    assert _run(con, csv, "start,end\n5,3\n") == []
    assert _run(con, csv, "start_date,end_date\nsoon,later\n") == []


def test_examples_limited_to_three(con, csv):
    text = "start_date,end_date\n" + "".join(f"2024-03-0{i},2024-02-01\n" for i in range(1, 6))
    (f,) = _run(con, csv, text)
    assert f.count == 5 and len(f.examples) == 3


def test_quoted_and_spaced_column_names(con, csv):
    text = '"we""ird start","we""ird end"\n2024-03-01,2024-02-01\n'
    (f,) = _run(con, csv, text)
    assert f.column == 'we"ird end'


def test_header_only_is_empty(con, csv):
    assert _run(con, csv, "start_date,end_date\n") == []
