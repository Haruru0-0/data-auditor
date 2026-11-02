import json
from datetime import datetime, timezone

import pytest

from dataauditor.audit import FileReport
from dataauditor.findings import Finding
from dataauditor.report import exit_code, to_json, write_json

NOW = datetime(2026, 11, 2, 9, 30, 5, tzinfo=timezone.utc)


def rep(*severities):
    return [FileReport("a.csv", 3, {"x": "BIGINT"},
                       [Finding("missing", s, "x", "msg", 1, ("e",)) for s in severities])]


def test_exit_code():
    assert exit_code(rep("error", "warning")) == 1
    assert exit_code(rep("warning", "info")) == 0
    assert exit_code([]) == 0


def test_to_json_round_trip():
    data = json.loads(to_json(rep("error", "warning", "warning"), NOW))
    assert data["generated_at"] == "2026-11-02T09:30:05Z"
    assert data["totals"] == {"info": 0, "warning": 2, "error": 1}
    f = data["files"][0]
    assert (f["path"], f["rows"], f["columns"]) == ("a.csv", 3, {"x": "BIGINT"})
    assert f["findings"][0] == {"check": "missing", "severity": "error", "column": "x",
                                "message": "msg", "count": 1, "examples": ["e"]}


def test_to_json_naive_treated_as_utc_and_sorted():
    text = to_json([], datetime(2026, 1, 2, 3, 4, 5))
    assert json.loads(text)["generated_at"] == "2026-01-02T03:04:05Z"
    assert text.index('"files"') < text.index('"generated_at"') < text.index('"totals"')


def test_write_json_creates_dir_and_never_overwrites(tmp_path):
    out = tmp_path / "new" / "reports"
    p = write_json(rep("info"), out, NOW)
    assert p.name == "audit-20261102T093005Z.json"
    first = p.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_json(rep("error"), out, NOW)
    assert p.read_text(encoding="utf-8") == first
