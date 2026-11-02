import pytest

from dataauditor.audit import FileReport, audit_path

CLEAN = "id,name,score\n" + "".join(f"{i},name{i},{10 + i % 5}\n" for i in range(1, 21))


def checks_of(report, severity=None):
    return [f for f in report.findings if severity is None or f.severity == severity]


def test_folder_with_clean_corrupt_and_txt(tmp_path):
    (tmp_path / "a_clean.csv").write_text(CLEAN, encoding="utf-8")
    (tmp_path / "b_bad.parquet").write_bytes(b"not parquet")
    (tmp_path / "notes.txt").write_text("hi", encoding="utf-8")
    reports = audit_path(tmp_path)
    assert [r.path.endswith(n) for r, n in zip(reports, ["a_clean.csv", "b_bad.parquet"])] == [True, True]
    assert len(reports) == 2
    clean, bad = reports
    assert isinstance(clean, FileReport)
    assert [f for f in clean.findings if f.severity in ("warning", "error")] == []
    assert bad.rows == 0 and bad.columns == {}
    assert len(bad.findings) == 1
    f = bad.findings[0]
    assert (f.check, f.severity, f.column, f.count) == ("read", "error", None, 1)


def test_suffix_case_insensitive_and_sorted(tmp_path):
    (tmp_path / "b.CSV").write_text(CLEAN, encoding="utf-8")
    (tmp_path / "a.csv").write_text(CLEAN, encoding="utf-8")
    assert [r.path[-5:] for r in audit_path(tmp_path)] == ["a.csv", "b.CSV"]


def test_empty_folder_and_no_matching_files(tmp_path):
    assert audit_path(tmp_path) == []
    (tmp_path / "x.txt").write_text("x", encoding="utf-8")
    assert audit_path(tmp_path) == []


def test_missing_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        audit_path(tmp_path / "nope")


def test_header_only_csv_no_findings(csv):
    reports = audit_path(csv("h.csv", "a,b,c\n"))
    assert reports[0].rows == 0
    assert reports[0].findings == []


def test_all_null_column_single_missing_error(csv):
    text = "id,empty\n" + "".join(f"{i},\n" for i in range(1, 21))
    findings = audit_path(csv("n.csv", text))[0].findings
    errs = [f for f in findings if f.column == "empty"]
    assert [(f.check, f.severity) for f in errs] == [("missing", "error")]
    assert not [f for f in findings if f.check == "types"]


def test_baseline_dropped_column_is_schema_error(tmp_path):
    new, old = tmp_path / "new", tmp_path / "old"
    new.mkdir()
    old.mkdir()
    (new / "t.csv").write_text("id,name\n" + "".join(f"{i},n{i}\n" for i in range(1, 21)), encoding="utf-8")
    (old / "t.csv").write_text("id,name,extra\n" + "".join(f"{i},n{i},{i}\n" for i in range(1, 21)), encoding="utf-8")
    (new / "u.csv").write_text(CLEAN, encoding="utf-8")
    reports = audit_path(new, baseline=old)
    t, u = reports
    assert any(f.check == "schema" and f.severity == "error" for f in t.findings)
    schema_u = [f for f in u.findings if f.check == "schema"]
    assert len(schema_u) == 1 and schema_u[0].severity == "info" and schema_u[0].column is None
    assert "baseline" in schema_u[0].message.lower()


def test_file_vs_file_baseline(csv, tmp_path):
    new = csv("new.csv", "id\n1\n2\n")
    old = tmp_path / "old.csv"
    old.write_text("id,gone\n1,2\n", encoding="utf-8")
    findings = audit_path(new, baseline=old)[0].findings
    assert any(f.check == "schema" and f.severity == "error" for f in findings)


def test_file_with_folder_baseline_and_folder_with_file_baseline(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    (base / "t.csv").write_text("id,gone\n1,2\n", encoding="utf-8")
    f = tmp_path / "t.csv"
    f.write_text("id\n1\n", encoding="utf-8")
    assert any(x.check == "schema" and x.severity == "error" for x in audit_path(f, baseline=base)[0].findings)
    with pytest.raises(ValueError):
        audit_path(tmp_path, baseline=f)


def test_unreadable_baseline_gives_warning(tmp_path):
    new = tmp_path / "t.csv"
    new.write_text("id\n1\n", encoding="utf-8")
    old = tmp_path / "old.parquet"
    old.write_bytes(b"junk")
    schema = [f for f in audit_path(new, baseline=old)[0].findings if f.check == "schema"]
    assert len(schema) == 1 and schema[0].severity == "warning"
    assert "unreadable" in schema[0].message.lower()
