from datetime import datetime, timezone

from dataauditor.cli import main

NOW = datetime(2026, 11, 2, 9, 30, 5, tzinfo=timezone.utc)
STEM = "audit-20261102T093005Z"
CLEAN = "id,name\n1,a\n2,b\n3,c\n4,d\n5,e\n"


def write(tmp_path, name="data.csv", text=CLEAN):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8", newline="")
    return p


def run(args, now=NOW):
    return main([str(a) for a in args], now=now)


def test_clean_file_writes_json_and_html(tmp_path, capsys):
    f = write(tmp_path)
    out = tmp_path / "out"
    assert run(["audit", f, "--out", out]) == 0
    assert (out / f"{STEM}.json").is_file()
    assert (out / f"{STEM}.html").is_file()
    text = capsys.readouterr().out
    assert str(f) in text
    assert f"{STEM}.json" in text and f"{STEM}.html" in text


def test_null_only_column_returns_1_and_summary_counts(tmp_path, capsys):
    f = write(tmp_path, text="id,empty\n1,\n2,\n3,\n")
    assert run(["audit", f, "--out", tmp_path / "out"]) == 1
    text = capsys.readouterr().out
    assert "error" in text and "missing" in text and "empty" in text
    assert "3 rows" in text and "2 columns" in text
    assert "error: 1" in text


def test_missing_path_returns_2_and_writes_nothing(tmp_path, capsys):
    out = tmp_path / "out"
    assert run(["audit", tmp_path / "nope.csv", "--out", out]) == 2
    assert "not found" in capsys.readouterr().err
    assert not out.exists()


def test_empty_folder_returns_2_with_message(tmp_path, capsys):
    folder = tmp_path / "empty"
    folder.mkdir()
    out = tmp_path / "out"
    assert run(["audit", folder, "--out", out]) == 2
    assert "no CSV or Parquet files found" in capsys.readouterr().err
    assert not out.exists()


def test_folder_with_only_txt_returns_2(tmp_path, capsys):
    folder = tmp_path / "d"
    folder.mkdir()
    (folder / "notes.txt").write_text("hi")
    assert run(["audit", folder, "--out", tmp_path / "out"]) == 2
    assert "no CSV or Parquet files found" in capsys.readouterr().err


def test_second_run_same_now_returns_2_and_keeps_outputs(tmp_path, capsys):
    f = write(tmp_path)
    out = tmp_path / "out"
    assert run(["audit", f, "--out", out]) == 0
    j, h = out / f"{STEM}.json", out / f"{STEM}.html"
    before = (j.read_bytes(), h.read_bytes())
    capsys.readouterr()
    assert run(["audit", f, "--out", out]) == 2
    assert "already exists" in capsys.readouterr().err
    assert (j.read_bytes(), h.read_bytes()) == before


def test_existing_html_only_blocks_run_and_no_json_written(tmp_path, capsys):
    f = write(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    h = out / f"{STEM}.html"
    h.write_bytes(b"keep")
    assert run(["audit", f, "--out", out]) == 2
    assert not (out / f"{STEM}.json").exists()
    assert h.read_bytes() == b"keep"


def test_input_bytes_unchanged(tmp_path):
    f = write(tmp_path)
    before = f.read_bytes()
    run(["audit", f, "--out", tmp_path / "out"])
    assert f.read_bytes() == before


def test_baseline_with_dropped_column_returns_1(tmp_path):
    base = write(tmp_path, "base.csv", "id,name\n1,a\n2,b\n")
    cur = write(tmp_path, "cur.csv", "id\n1\n2\n")
    assert run(["audit", cur, "--baseline", base, "--out", tmp_path / "out"]) == 1


def test_missing_baseline_returns_2(tmp_path, capsys):
    f = write(tmp_path)
    assert run(["audit", f, "--baseline", tmp_path / "nope.csv",
                "--out", tmp_path / "out"]) == 2
    assert "baseline not found" in capsys.readouterr().err


def test_folder_with_file_baseline_returns_2(tmp_path, capsys):
    folder = tmp_path / "d"
    folder.mkdir()
    write(folder)
    base = write(tmp_path, "base.csv")
    assert run(["audit", folder, "--baseline", base, "--out", tmp_path / "out"]) == 2
    assert "baseline must be a folder" in capsys.readouterr().err


def test_unknown_command_and_no_args_return_2(capsys):
    assert main(["bogus"], now=NOW) == 2
    assert main([], now=NOW) == 2


def test_help_returns_0(capsys):
    assert main(["--help"], now=NOW) == 0


def test_html_starts_with_doctype_and_names_file(tmp_path):
    f = write(tmp_path)
    out = tmp_path / "out"
    run(["audit", f, "--out", out])
    html = (out / f"{STEM}.html").read_text(encoding="utf-8")
    assert html.lstrip().lower().startswith("<!doctype html")
    assert "data.csv" in html


def test_non_ascii_column_names(tmp_path):
    f = write(tmp_path, text="naïve,日本\n1,2\n3,4\n")
    out = tmp_path / "out"
    run(["audit", f, "--out", out])
    html = (out / f"{STEM}.html").read_bytes().decode("utf-8")
    assert "naïve" in html and "日本" in html
