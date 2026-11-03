from dataauditor.checks.typos import check_typos
from dataauditor.load import open_table


def _run(con, csv, text):
    return check_typos(con, open_table(con, csv("t.csv", text)))


def _col(values, header="country"):
    return header + "\n" + "".join(f"{v}\n" for v in values)


def test_typo_of_a_frequent_value(con, csv):
    values = ["Lebanon"] * 18 + ["Lebnon", "Norway"]
    (f,) = _run(con, csv, _col(values))
    assert (f.check, f.severity, f.column, f.count) == ("typo", "warning", "country", 1)
    assert f.message == '1 value(s) look like typos (e.g. "Lebnon" -> "Lebanon")'
    assert f.examples == ('"Lebnon" -> "Lebanon"',)


def test_twenty_row_boundary(con, csv):
    assert len(_run(con, csv, _col(["Lebanon"] * 18 + ["Lebnon", "Norway"]))) == 1
    assert _run(con, csv, _col(["Lebanon"] * 17 + ["Lebnon", "Norway"])) == []


def test_ten_times_rule(con, csv):
    # 2 * 10 > 18: not rare enough compared to "Lebanon"
    assert _run(con, csv, _col(["Lebanon"] * 18 + ["Lebnon"] * 2)) == []
    # 2 * 10 <= 20 and 2 <= max(2, 2% of 22)
    (f,) = _run(con, csv, _col(["Lebanon"] * 20 + ["Lebnon"] * 2))
    assert f.count == 2


def test_two_percent_boundary(con, csv):
    # 200 non-null rows: allowed up to max(2, 4) = 4 rows
    assert len(_run(con, csv, _col(["Lebanon"] * 196 + ["Lebnon"] * 4))) == 1
    assert _run(con, csv, _col(["Lebanon"] * 195 + ["Lebnon"] * 5)) == []


def test_minimum_length_four(con, csv):
    assert _run(con, csv, _col(["Iran"] * 20 + ["Ira"])) == []
    assert len(_run(con, csv, _col(["Iran"] * 20 + ["Irna"]))) == 1


def test_substitutions_are_not_typos(con, csv):
    for common, rare in [("Omar", "Omer"), ("Maria", "Mario"), ("A1234", "A1235"), ("2020", "2021")]:
        assert _run(con, csv, _col([common] * 25 + [rare])) == [], (common, rare)


def test_values_with_digits_are_skipped(con, csv):
    # an insertion, but both values carry digits
    assert _run(con, csv, _col(["Item12"] * 25 + ["Item2"])) == []
    assert _run(con, csv, _col(["Lebanon"] * 25 + ["Lebanon1"])) == []


def test_adjacent_transposition_is_a_typo(con, csv):
    (f,) = _run(con, csv, _col(["Beirut"] * 25 + ["Beriut"]))
    assert f.examples == ('"Beriut" -> "Beirut"',)


def test_non_adjacent_swap_is_not_a_typo(con, csv):
    assert _run(con, csv, _col(["Beirut"] * 25 + ["Tebiur"])) == []


def test_case_difference_is_not_a_typo(con, csv):
    assert _run(con, csv, _col(["Lebanon"] * 25 + ["lebanon"])) == []


def test_most_frequent_target_wins(con, csv):
    values = ["Lebanon"] * 40 + ["Lebnonn"] * 30 + ["Lebnon"]
    (f,) = _run(con, csv, _col(values))
    assert f.examples == ('"Lebnon" -> "Lebanon"',)


def test_distinct_count_gate(con, csv):
    # 50 distinct values (one of them the typo) is allowed, 51 is skipped
    fillers = [f"zzq{i:02d}x" for i in range(48)]
    assert len(_run(con, csv, _col(["Lebanon"] * 200 + ["Lebnon"] + fillers))) == 1
    assert _run(con, csv, _col(["Lebanon"] * 200 + ["Lebnon"] + fillers + ["extra1"])) == []


def test_single_distinct_value_is_skipped(con, csv):
    assert _run(con, csv, _col(["Lebanon"] * 30)) == []


def test_examples_limited_to_three_and_count_is_rows(con, csv):
    big = [("Lebanon", 400), ("Norway", 400), ("Finland", 400), ("Germany", 400)]
    typos = [("Lebnon", 2), ("Norwy", 2), ("Finlnd", 2), ("Germny", 2)]
    values = [v for v, n in big + typos for _ in range(n)]
    (f,) = _run(con, csv, _col(values))
    assert f.count == 8 and len(f.examples) == 3
    assert f.message.startswith("8 value(s) look like typos")


def test_values_are_trimmed(con, csv):
    values = ["Lebanon"] * 18 + [" Lebnon ", "Norway"]
    (f,) = _run(con, csv, _col(values))
    assert f.examples == ('"Lebnon" -> "Lebanon"',)


def test_non_varchar_columns_are_skipped(con, csv):
    assert _run(con, csv, _col([1000] * 20 + [1001, 1002], header="n")) == []


def test_quoted_and_spaced_column_names(con, csv):
    values = ["Lebanon"] * 18 + ["Lebnon", "Norway"]
    (f,) = _run(con, csv, _col(values, header='we"ird name'))
    assert f.column == 'we"ird name'


def test_header_only_is_empty(con, csv):
    assert _run(con, csv, "a,b\n") == []
