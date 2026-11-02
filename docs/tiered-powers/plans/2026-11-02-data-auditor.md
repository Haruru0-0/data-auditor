# data-auditor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use tiered-powers:subagent-driven-development (recommended) or tiered-powers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A command-line tool that audits CSV and Parquet files for data-quality problems and writes a terminal summary, a JSON report and a static HTML page.

**Architecture:** DuckDB loads each file as a view; each check is a pure function `(con, table) -> list[Finding]`; an audit runner collects findings per file; report writers turn them into JSON and HTML; a thin CLI wires it together and sets the exit code.

**Tech Stack:** Python 3.12, DuckDB, pytest. No other runtime dependencies.

**Spec:** `docs/tiered-powers/specs/2026-11-02-data-auditor-design.md`

## Global Constraints

- Python 3.12; package in `src/dataauditor`; tests in `tests/`; test-first.
- DuckDB reads and aggregates; the tool never modifies an input file.
- Commits are made as Ahmad: no `Co-Authored-By` and no "Generated with Claude" lines. Never push; the controller asks Ahmad first.
- README numbers come from generated results, never typed by hand.
- Saved reports are never overwritten (exclusive create, new timestamped name).
- Static page: system fonts only; no external scripts, fonts, `http` links or `url(`; light and dark via `prefers-color-scheme`.
- Severity values are exactly `info`, `warning`, `error`. Exit code is 1 only if any finding is `error`.
- Thresholds are conservative: a clean, normal file must produce no `warning` or `error`.

## Review Focus

- Header-only CSV (zero rows): no crash, no divide-by-zero, no findings (Tasks 1, 2).
- Empty (0-byte) or corrupt file: reported as an `error` finding with check `read`; other files in the folder still audited (Tasks 1, 7).
- Constant numeric column (MAD is 0): no outlier findings and no crash (Task 5).
- Column that is entirely null: exactly one `error` from `missing`, and no extra noise from the type check (Tasks 2, 4).
- UTF-8 BOM, non-ASCII column names and duplicate column names load and report without error (Task 1).

---

### Task 1: Scaffold, loader and Finding model

**Files:**
- Create: `pyproject.toml`, `src/dataauditor/__init__.py`, `src/dataauditor/findings.py`, `src/dataauditor/load.py`, `tests/conftest.py`, `tests/test_load.py`

**Tier:** sonnet — prose steps, DuckDB behaviour to confirm

**Interfaces:**
- Produces:
  - `findings.Finding` frozen dataclass: `check: str`, `severity: str`, `column: str | None`, `message: str`, `count: int`, `examples: tuple[str, ...] = ()`.
  - `load.UnreadableFile(Exception)`.
  - `load.Table` dataclass: `path: Path`, `name: str` (DuckDB view name), `rows: int`, `columns: dict[str, str]` (name to DuckDB type, in file order).
  - `load.open_table(con: duckdb.DuckDBPyConnection, path: Path) -> Table`, supports `.csv` and `.parquet`; any DuckDB read failure or unsupported extension raises `UnreadableFile`.
  - `tests/conftest.py` fixtures: `con` (fresh in-memory DuckDB) and `csv(name, text) -> Path` (writes under `tmp_path`, UTF-8).

- [ ] **Step 1: Write failing tests in `tests/test_load.py`**
  - `test_csv_rows_columns_and_types`: `"id,name\n1,x\n2,y\n"` gives `rows == 2`, `list(columns) == ["id","name"]`, `columns["id"] == "BIGINT"`.
  - `test_header_only_csv_has_zero_rows`: `"a,b\n"` gives `rows == 0` and two columns.
  - `test_empty_file_raises_unreadable`: 0-byte csv raises `UnreadableFile`.
  - `test_bom_and_non_ascii_header`: `"﻿id,naïve\n1,2\n"` gives columns `["id","naïve"]`.
  - `test_duplicate_column_names_load`: `"a,a\n1,2\n"` gives two columns.
  - `test_parquet_roundtrip`: create with `con.execute("COPY (SELECT 1 AS x) TO ... (FORMAT parquet)")`, `open_table` returns `rows == 1`.
  - `test_unsupported_extension_raises_unreadable`.
- [ ] **Step 2: Run `pytest tests/test_load.py -q`; expect FAIL (import error).**
- [ ] **Step 3: Create `pyproject.toml`** (project `dataauditor`, `requires-python >=3.12`, deps `duckdb>=1.1,<2`, dev extra `pytest>=8,<9`, script `dataauditor = "dataauditor.cli:main"`, src layout, pytest `testpaths = ["tests"]`). Create the venv: `python -m venv .venv` then `.venv/Scripts/python.exe -m pip install -e ".[dev]"`.
- [ ] **Step 4: Implement `findings.py` and `load.py`** per the Interfaces. `open_table` creates a uniquely named view over `read_csv`/`read_parquet`, reads `DESCRIBE` for columns and `count(*)` for rows.
- [ ] **Step 5: Run `.venv/Scripts/python.exe -m pytest -q`; expect all PASS.**
- [ ] **Step 6: Commit** `feat: scaffold package, loader and Finding model`.

### Task 2: Missing-values check

**Files:**
- Create: `src/dataauditor/checks/__init__.py`, `src/dataauditor/checks/missing.py`, `tests/test_check_missing.py`

**Tier:** sonnet — SQL aggregate plus thresholds

**Interfaces:**
- Consumes: `Table`, `Finding`.
- Produces: `checks.missing.check_missing(con, table: Table) -> list[Finding]`, check name `"missing"`.

Rules (pinned): null fraction >= 0.05 gives `warning`; column 100% null (with rows > 0) gives one `error` instead of the warning; 0 rows gives `[]`. `count` is the null count; message contains the percentage.

- [ ] **Step 1: Write failing tests:** 20 rows with 1 null in `b` gives one `warning` for `b` and none for `a`; 100 rows with 1 null gives `[]`; all-null column gives exactly one `error`; header-only file gives `[]`.
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Implement `check_missing`** with one aggregate query over all columns (quote identifiers).
- [ ] **Step 4: Run; expect PASS.**
- [ ] **Step 5: Commit** `feat: missing-values check`.

### Task 3: Duplicates check

**Files:**
- Create: `src/dataauditor/checks/duplicates.py`, `tests/test_check_duplicates.py`

**Tier:** sonnet

**Interfaces:**
- Consumes: `Table`, `Finding`.
- Produces: `checks.duplicates.check_duplicates(con, table: Table) -> list[Finding]`, check name `"duplicates"`.

Rules (pinned): extra copies of identical full rows give one `warning` (`column=None`, `count` = number of extra copies). A column whose lowercase name ends in `id` or `key` with repeated non-null values gives an `error` (`count` = extra occurrences). Duplicates in other columns are not flagged.

- [ ] **Step 1: Write failing tests:** `"a,b\n1,x\n1,x\n2,y\n"` gives one row-duplicate warning with count 1; `user_id` values 1,1,2 gives one `error` for `user_id` with count 1; repeated values in a plain `city` column give no finding; zero-row file gives `[]`; nulls in a key column are not counted as duplicates.
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Implement `check_duplicates`.**
- [ ] **Step 4: Run; expect PASS.**
- [ ] **Step 5: Commit** `feat: duplicates check`.

### Task 4: Type-problems check

**Files:**
- Create: `src/dataauditor/checks/types.py`, `tests/test_check_types.py`

**Tier:** sonnet

**Interfaces:**
- Consumes: `Table`, `Finding`.
- Produces: `checks.types.check_types(con, table: Table) -> list[Finding]`, check name `"types"`.

Rules (pinned), for `VARCHAR` columns only, over non-null values: if the share castable with `TRY_CAST(... AS DOUBLE)` is >= 0.95 and < 1, `warning` "numbers stored as text" with `count` = non-numeric values and up to 3 `examples`; same for `DATE` ("dates stored as text"); if the numeric share is between 0.05 and 0.95, `warning` "mixed types". A column with no non-null values gives nothing. Correctly typed columns and pure text give nothing.

- [ ] **Step 1: Write failing tests:** 97 numeric strings plus 3 `n/a` gives one warning, count 3, examples contain `n/a`; 50/50 numbers and words gives a "mixed" warning; pure text gives `[]`; a column typed `BIGINT` gives `[]`; all-null column gives `[]`; 97 ISO dates plus 3 junk values gives a dates-as-text warning.
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Implement `check_types`.**
- [ ] **Step 4: Run; expect PASS.**
- [ ] **Step 5: Commit** `feat: type-problems check`.

### Task 5: Outliers check

**Files:**
- Create: `src/dataauditor/checks/outliers.py`, `tests/test_check_outliers.py`

**Tier:** sonnet

**Interfaces:**
- Consumes: `Table`, `Finding`.
- Produces: `checks.outliers.check_outliers(con, table: Table) -> list[Finding]`, check name `"outliers"`.

Rules (pinned): numeric columns only (integer, float, decimal types); needs >= 20 non-null values; robust z = `0.6745 * (x - median) / MAD`; values with `abs(z) > 6` are outliers; MAD of 0 gives no finding. One `warning` per column with `count` and up to 3 `examples`.

- [ ] **Step 1: Write failing tests:** 50 values around 10 plus one 10000 gives one warning, count 1, `"10000"` in examples; values 1..50 give `[]`; a constant column of 30 values gives `[]` without error; 19 values including a huge one gives `[]`; a text column is ignored.
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Implement `check_outliers`** using DuckDB `median` for the median and the median of absolute deviations.
- [ ] **Step 4: Run; expect PASS.**
- [ ] **Step 5: Commit** `feat: outliers check`.

### Task 6: Schema drift

**Files:**
- Create: `src/dataauditor/checks/schema.py`, `tests/test_check_schema.py`

**Tier:** sonnet

**Interfaces:**
- Consumes: two `Table` values (baseline and current), `Finding`.
- Produces: `checks.schema.compare_schemas(old: Table, new: Table) -> list[Finding]`, check name `"schema"`.

Rules (pinned): column in `old` but not `new` gives `error`; column only in `new` gives `info`; same name with a different type gives `warning`; identical schemas give `[]`. Compare by name, not position.

- [ ] **Step 1: Write failing tests** for removed, added, retyped, reordered-only (gives `[]`) and identical.
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Implement `compare_schemas`** (pure, no `con` needed).
- [ ] **Step 4: Run; expect PASS.**
- [ ] **Step 5: Commit** `feat: schema drift comparison`.

### Task 7: Audit runner and JSON report

**Files:**
- Create: `src/dataauditor/audit.py`, `src/dataauditor/report.py`, `tests/test_audit.py`, `tests/test_report.py`

**Tier:** sonnet

**Interfaces:**
- Consumes: all checks, `open_table`, `compare_schemas`.
- Produces:
  - `audit.FileReport` dataclass: `path: str`, `rows: int`, `columns: dict[str, str]`, `findings: list[Finding]`.
  - `audit.audit_path(path: Path, baseline: Path | None = None) -> list[FileReport]`: a file gives one report; a folder gives one per `.csv`/`.parquet` file (sorted by name, other files ignored). An unreadable file gives a `FileReport` with `rows=0`, no columns and one `error` Finding with check `"read"`; the rest still run. With `baseline`, a file is compared to the same-named file in the baseline folder (or to the baseline file itself when both are files); a missing baseline counterpart gives an `info` finding check `"schema"`.
  - `report.exit_code(reports: list[FileReport]) -> int` (1 if any `error`, else 0).
  - `report.to_json(reports, generated_at: datetime) -> str` (sorted keys, indent 2, ISO UTC time).
  - `report.write_json(reports, out_dir: Path, now: datetime) -> Path` writes `audit-YYYYmmddTHHMMSSZ.json` with exclusive create; raises `FileExistsError` rather than overwrite.

- [ ] **Step 1: Write failing tests:** folder with one clean file, one corrupt file and one `.txt` gives two reports with the corrupt one carrying a `read` error; clean file gives no warning or error; baseline with a dropped column yields a schema `error`; `exit_code` is 1 for an error and 0 for only warnings; `to_json` round-trips through `json.loads` with the expected keys; second `write_json` with the same `now` raises `FileExistsError` and the first file is unchanged; empty folder gives `[]`.
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Implement `audit.py` and `report.py`** per Interfaces; open one in-memory connection per `audit_path` call.
- [ ] **Step 4: Run the full suite; expect PASS.**
- [ ] **Step 5: Commit** `feat: audit runner and JSON report`.

### Task 8: Static HTML page

**Files:**
- Create: `src/dataauditor/page.py`, `tests/test_page.py`

**Tier:** sonnet — escaping matters, markup is user-influenced

**Interfaces:**
- Consumes: `FileReport`, `Finding`.
- Produces: `page.render_html(reports: list[FileReport], generated_at: datetime) -> str`, one self-contained document.

Rules: header with totals by severity, one card per file with a findings table (severity, check, column, message, count, examples), severity shown by label and symbol not colour alone; inline CSS in the same token style as forecast-tracker (system fonts, light and dark); empty list shows "No files audited". Every value from a file (names, examples) is HTML-escaped.

- [ ] **Step 1: Write failing tests:** file name and counts appear; a column named `<script>alert(1)</script>` appears escaped and the raw tag does not; output contains `prefers-color-scheme` and none of `http://`, `https://`, `url(`, `@font-face`, `<script`; empty list contains "No files audited".
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Implement `render_html`** with `html.escape` on all dynamic text.
- [ ] **Step 4: Run; expect PASS.**
- [ ] **Step 5: Commit** `feat: static HTML report page`.

### Task 9: Command-line interface

**Files:**
- Create: `src/dataauditor/cli.py`, `src/dataauditor/__main__.py`, `tests/test_cli.py`

**Tier:** sonnet

**Interfaces:**
- Consumes: `audit_path`, `write_json`, `render_html`, `exit_code`.
- Produces: `cli.main(argv: list[str] | None = None, now: datetime | None = None) -> int`. Usage: `dataauditor audit PATH [--baseline PATH] [--out DIR]` (default out `reports`). Prints a per-file summary (counts by severity, one line per finding); writes the JSON and an HTML file with the same timestamp stem. Returns 0 clean or warnings only, 1 if any `error`, 2 for usage problems (path missing, no CSV/Parquet files found, output file already exists). `__main__.py` calls `sys.exit(main())`.

- [ ] **Step 1: Write failing tests:** clean file returns 0 and writes `.json` and `.html`; a file with a null-only column returns 1; nonexistent path returns 2; empty folder returns 2 with a clear message; calling twice with the same `now` returns 2 and leaves the first outputs untouched; input file bytes are unchanged after the run.
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Implement `cli.py`** with `argparse`.
- [ ] **Step 4: Run the full suite; expect PASS.**
- [ ] **Step 5: Commit** `feat: command-line interface`.

### Task 10: Demo data, generated README numbers and CI

**Files:**
- Create: `scripts/make_demo_data.py`, `scripts/render_readme.py`, `README.md`, `.github/workflows/ci.yml`, `tests/test_demo.py`, `tests/test_readme.py`

**Tier:** sonnet

**Interfaces:**
- Consumes: `audit_path`.
- Produces: `scripts/make_demo_data.py` with `make_demo(out_dir: Path, seed: int = 7) -> dict[str, list[str]]` writing deterministic synthetic CSVs with known injected faults and returning, per file, the list of injected fault names (for example `"null_column:notes"`, `"dup_key:order_id"`, `"text_numbers:price"`, `"outlier:amount"`). `scripts/render_readme.py` with `render_numbers(results_json: Path, readme: Path) -> None` replacing only the text between `<!-- numbers:start -->` and `<!-- numbers:end -->`.

Synthetic data is my ruling instead of downloading public datasets: it needs no network or licence and lets the README state "found N of N injected faults" from a generated result.

- [ ] **Step 1: Write failing tests:** two `make_demo` runs with the same seed produce byte-identical files; auditing the demo finds every injected fault (recall 1.0) and the clean demo file has no `warning` or `error`; `render_numbers` leaves everything outside the markers byte-identical and fails clearly if a marker is missing.
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Implement both scripts;** the README numbers block shows files audited, faults injected, faults found and the false-positive count, all read from the audit's JSON output.
- [ ] **Step 4: Write `README.md`** (what it is, install, usage, the generated numbers block with markers, limits) and `ci.yml` (checkout, Python 3.12, install `.[dev]`, `pytest`). No hand-typed numbers.
- [ ] **Step 5: Run the full suite; expect PASS.**
- [ ] **Step 6: Commit** `feat: demo data, generated README numbers and CI`.
