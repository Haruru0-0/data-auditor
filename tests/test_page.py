import re
from datetime import datetime, timezone

from dataauditor.audit import FileReport
from dataauditor.findings import Finding
from dataauditor.page import render_html

NOW = datetime(2026, 11, 2, 9, 30, 5, tzinfo=timezone.utc)

FORBIDDEN = ["http://", "https://", "url(", "@font-face", "<script", "@import",
             "onerror=", "onload=", "onclick="]


def clean_reports():
    return [
        FileReport("data/sales.csv", 120, {"id": "BIGINT", "name": "VARCHAR"}, [
            Finding("missing", "error", "id", "3 missing values", 3, ("row 4",)),
            Finding("outliers", "warning", "name", "odd values", 2, ("x", "y")),
            Finding("types", "info", None, "note", 1),
        ]),
        FileReport("data/clean.csv", 5, {"a": "BIGINT"}, []),
    ]


def test_names_and_counts_appear():
    out = render_html(clean_reports(), NOW)
    assert "data/sales.csv" in out
    assert "120" in out
    assert "Data audit" in out
    assert "2026-11-02T09:30:05Z" in out
    assert "No problems found" in out
    for label in ("error", "warning", "info"):
        assert label in out


def test_severity_has_symbol_and_label():
    out = render_html(clean_reports(), NOW)
    assert "✖ error" in out and "▲ warning" in out and "ℹ info" in out


def test_document_shape():
    out = render_html(clean_reports(), NOW)
    assert out.lstrip().lower().startswith("<!doctype html>")
    assert '<html lang="en">' in out
    assert '<meta charset="utf-8">' in out
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in out
    assert "<title>" in out
    assert "prefers-color-scheme" in out
    assert "overflow-x: auto" in out


def test_no_forbidden_markup_for_clean_data():
    out = render_html(clean_reports(), NOW)
    for bad in FORBIDDEN:
        assert bad not in out, bad
    assert not re.search(r"<link\b", out)


def test_empty_list():
    out = render_html([], NOW)
    assert "No files audited" in out
    for bad in FORBIDDEN:
        assert bad not in out, bad


def test_hostile_data_is_escaped():
    reports = [FileReport(
        "<b>evil</b>.csv", 1, {"<script>alert(1)</script>": "<i>T</i>"},
        [Finding("missing", "error", "<script>alert(1)</script>",
                 '"><img src=x onerror=alert(1)>', 1, ("url(http://evil)",))],
    )]
    out = render_html(reports, NOW)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in out
    assert "&quot;&gt;&lt;img src=x onerror=alert(1)&gt;" in out
    assert "&lt;b&gt;evil&lt;/b&gt;.csv" in out
    assert "<script" not in out
    assert "<img" not in out
    assert "<b>evil" not in out
    assert '"><img' not in out
    assert "<i>T" not in out


def test_deterministic():
    assert render_html(clean_reports(), NOW) == render_html(clean_reports(), NOW)
