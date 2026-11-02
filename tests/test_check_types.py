from dataauditor.checks.types import check_types
from dataauditor.load import open_table


def _run(con, csv, text, col_type="VARCHAR", col="b"):
    table = open_table(con, csv("t.csv", text))
    assert table.columns[col] == col_type
    return check_types(con, table)


def _csv(values):
    return "a,b\n" + "\n".join(f"{i},{v}" for i, v in enumerate(values)) + "\n"


def test_numbers_stored_as_text(con, csv):
    values = [str(i) for i in range(97)] + ["n/a"] * 3
    findings = _run(con, csv, _csv(values))
    assert len(findings) == 1
    f = findings[0]
    assert (f.check, f.severity, f.column, f.count) == ("types", "warning", "b", 3)
    assert "numbers stored as text" in f.message
    assert "n/a" in f.examples


def test_dates_stored_as_text(con, csv):
    values = [f"2024-01-{(i % 28) + 1:02d}" for i in range(97)] + ["junk", "oops", "??"]
    findings = _run(con, csv, _csv(values))
    assert len(findings) == 1
    f = findings[0]
    assert (f.severity, f.count) == ("warning", 3)
    assert "dates stored as text" in f.message
    assert set(f.examples) == {"junk", "oops", "??"}


def test_mixed_types(con, csv):
    values = [str(i) for i in range(50)] + [f"word{i}" for i in range(50)]
    findings = _run(con, csv, _csv(values))
    assert len(findings) == 1
    assert findings[0].severity == "warning"
    assert "mixed types" in findings[0].message


def test_pure_text_is_clean(con, csv):
    assert _run(con, csv, _csv([f"word{i}" for i in range(100)])) == []


def test_bigint_column_is_clean(con, csv):
    assert _run(con, csv, _csv(range(100)), col_type="BIGINT") == []


def test_all_null_column_is_clean(con, csv):
    table = open_table(con, csv("t.csv", "a,b\n1,\n2,\n3,\n"))
    assert check_types(con, table) == []


def test_examples_capped_at_three(con, csv):
    values = [str(i) for i in range(90)] + [f"bad{i}" for i in range(5)] * 2
    findings = _run(con, csv, _csv(values))
    assert findings[0].count == 10
    assert len(findings[0].examples) == 3
