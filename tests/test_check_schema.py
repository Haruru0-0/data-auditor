from pathlib import Path

from dataauditor.checks.schema import compare_schemas
from dataauditor.load import Table


def make(columns):
    return Table(Path("a.csv"), "t", 0, columns)


def test_identical_gives_nothing():
    cols = {"a": "BIGINT", "b": "VARCHAR"}
    assert compare_schemas(make(cols), make(dict(cols))) == []


def test_reordered_only_gives_nothing():
    old = make({"a": "BIGINT", "b": "VARCHAR"})
    new = make({"b": "VARCHAR", "a": "BIGINT"})
    assert compare_schemas(old, new) == []


def test_removed_column_is_error():
    findings = compare_schemas(make({"a": "BIGINT", "b": "VARCHAR"}), make({"a": "BIGINT"}))
    assert len(findings) == 1
    f = findings[0]
    assert (f.check, f.severity, f.column, f.count) == ("schema", "error", "b", 1)


def test_added_column_is_info():
    findings = compare_schemas(make({"a": "BIGINT"}), make({"a": "BIGINT", "c": "DATE"}))
    assert len(findings) == 1
    f = findings[0]
    assert (f.check, f.severity, f.column, f.count) == ("schema", "info", "c", 1)


def test_retyped_column_is_warning_naming_both_types():
    findings = compare_schemas(make({"a": "BIGINT"}), make({"a": "VARCHAR"}))
    assert len(findings) == 1
    f = findings[0]
    assert (f.check, f.severity, f.column, f.count) == ("schema", "warning", "a", 1)
    assert "BIGINT" in f.message and "VARCHAR" in f.message


def test_order_removed_retyped_added():
    old = make({"r": "BIGINT", "t": "BIGINT", "k": "DATE"})
    new = make({"n": "DATE", "t": "VARCHAR", "k": "DATE"})
    got = [(f.severity, f.column) for f in compare_schemas(old, new)]
    assert got == [("error", "r"), ("warning", "t"), ("info", "n")]
