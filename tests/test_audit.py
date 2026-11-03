import pytest

from dataauditor.findings import Finding

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


def test_check_failure_becomes_read_error_and_others_still_audited(tmp_path, monkeypatch):
    import duckdb

    import dataauditor.audit as audit_mod

    (tmp_path / "a.csv").write_text(CLEAN, encoding="utf-8")
    (tmp_path / "b.csv").write_text(CLEAN, encoding="utf-8")
    (tmp_path / "c.csv").write_text(CLEAN, encoding="utf-8")
    real = audit_mod.check_missing

    def flaky(con, table):
        if table.path.name == "b.csv":
            raise duckdb.Error("damaged page")
        return real(con, table)

    monkeypatch.setattr(audit_mod, "check_missing", flaky)
    a, b, c = audit_path(tmp_path)
    assert b.rows == 0 and b.columns == {}
    assert len(b.findings) == 1
    f = b.findings[0]
    assert (f.check, f.severity, f.column, f.count) == ("read", "error", None, 1)
    assert "damaged page" in f.message
    for ok in (a, c):
        assert ok.rows == 20
        assert [x for x in ok.findings if x.severity in ("warning", "error")] == []


def test_oserror_in_check_is_read_error(tmp_path, monkeypatch):
    import dataauditor.audit as audit_mod

    (tmp_path / "a.csv").write_text(CLEAN, encoding="utf-8")

    def boom(con, table):
        raise OSError("file vanished")

    monkeypatch.setattr(audit_mod, "check_outliers", boom)
    (r,) = audit_path(tmp_path)
    assert [(f.check, f.severity) for f in r.findings] == [("read", "error")]


def test_new_checks_run_through_audit_path(csv):
    rows = [
        f"{i},{'Beirut' if i % 4 else 'beirut'},{-5 if i == 3 else 20 + i},{'N/A' if i < 3 else 'ok' + str(i)},y,{i}"
        for i in range(1, 21)
    ]
    text = "id,city,age,note,flag,id\n" + "\n".join(rows) + "\n"
    found = {f.check for f in audit_path(csv("n.csv", text))[0].findings}
    assert {"constant", "whitespace", "missing-marker", "impossible", "header"} <= found


def test_heuristic_checks_run_through_audit_path(csv):
    rows = []
    for i in range(1, 120):
        rows.append(
            ",".join(
                [
                    str(i),
                    "2024-01-05" if i % 5 else "05/01/2024",
                    "bad" if i == 2 else "a@b.com",
                    "Lebnon" if i == 3 else "Norway" if i == 4 else "Lebanon",
                    "no" if i == 7 else "yes",
                    "2024-01-01",
                    "2023-01-01" if i == 5 else "2024-02-01",
                ]
            )
        )
    rows.append("120,,,,,,")  # mostly empty
    text = "id,seen,email,city,flag,start_date,end_date\n" + "\n".join(rows) + "\n"
    found = {(f.check, f.column) for f in audit_path(csv("h.csv", text))[0].findings}
    assert {
        ("format", "seen"),  # mixed date formats
        ("format", "email"),  # invalid email
        ("typo", "city"),
        ("skew", "flag"),  # dominant value
        ("skew", None),  # mostly-empty row
        ("date-order", "end_date"),
    } <= found


def test_report_has_profile_and_score(csv):
    [r] = audit_path(csv("p.csv", "id,name\n1,a\n2,b\n3,\n"))
    assert list(r.profile) == ["id", "name"]
    assert r.profile["id"]["max"] == 3
    assert r.profile["name"]["missing"] == 1
    from dataauditor.score import quality_score
    assert r.score == quality_score(r.findings)


def test_unreadable_file_has_empty_profile_and_zero_score(tmp_path):
    (tmp_path / "bad.csv").write_bytes(b"")
    [r] = audit_path(tmp_path / "bad.csv")
    assert r.profile == {} and r.score == 0


def test_profile_failure_becomes_read_error(csv, monkeypatch):
    import duckdb
    import dataauditor.audit as audit_mod

    def boom(con, table):
        raise duckdb.Error("profile broke")

    monkeypatch.setattr(audit_mod, "profile_columns", boom)
    [r] = audit_path(csv("x.csv", "a\n1\n"))
    assert r.findings[-1].check == "read" and r.profile == {} and r.score == 0


def test_filereport_constructor_without_profile_still_works():
    assert FileReport("a.csv", 0, {}, []).profile == {}


def test_read_error_keeps_first_line_and_is_capped(tmp_path, monkeypatch):
    import duckdb

    import dataauditor.audit as audit_mod

    (tmp_path / "a.csv").write_text(CLEAN, encoding="utf-8")
    long_line = "first line " + "x" * 500

    def boom(con, table):
        raise duckdb.Error(long_line + "\nSELECT secret FROM C:\tmp\file.csv\nsniffer dump")

    monkeypatch.setattr(audit_mod, "check_missing", boom)
    (r,) = audit_path(tmp_path)
    msg = r.findings[0].message
    assert msg.startswith("first line ") and len(msg) <= 300
    assert "SELECT" not in msg and "sniffer" not in msg


def _types_text(column):
    return Finding("types", "warning", column, "numbers stored as text: 1 of 9 non-null values do not fit", 1)


def test_drop_explained_types_only_with_format_or_marker_on_same_column():
    from dataauditor.audit import drop_explained_types

    mixed = Finding("types", "warning", "m", "mixed types: 50.0% of values look numeric, the rest are text", 4)
    findings = [
        _types_text("d"), Finding("format", "warning", "d", "dates in 2 different formats", 2),
        _types_text("n"), Finding("missing-marker", "warning", "n", "1 value(s) look like missing data", 1),
        _types_text("plain"),
        _types_text("other"), Finding("format", "warning", "elsewhere", "x", 1),
        mixed, Finding("format", "warning", "m", "x", 1),
    ]
    kept = drop_explained_types(findings)
    assert [(f.check, f.column) for f in kept] == [
        ("format", "d"), ("missing-marker", "n"), ("types", "plain"), ("types", "other"),
        ("format", "elsewhere"), ("types", "m"), ("format", "m"),
    ]


def test_mixed_dates_report_only_format(csv):
    rows = ["id,d"] + [f"{i},2024-01-{i % 28 + 1:02d}" for i in range(12)] + [f"{i},05/01/2024" for i in range(12, 20)]
    [r] = audit_path(csv("md.csv", "\n".join(rows) + "\n"))
    assert [f.check for f in r.findings if f.column == "d"] == ["format"]


def test_numeric_text_with_marker_reports_only_marker(csv):
    rows = ["id,v"] + [f"{i},{i}" for i in range(80)] + ["80,n/a", "81,n/a"]
    [r] = audit_path(csv("nm.csv", "\n".join(rows) + "\n"))
    assert [f.check for f in r.findings if f.column == "v"] == ["missing-marker"]


def test_plain_numbers_as_text_keep_the_types_finding(csv):
    rows = ["id,v"] + [f"{i},{i}" for i in range(80)] + ["80,abc", "81,def"]
    [r] = audit_path(csv("pt.csv", "\n".join(rows) + "\n"))
    assert "types" in [f.check for f in r.findings if f.column == "v"]
