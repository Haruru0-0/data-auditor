# Features built

Plan: `docs/tiered-powers/plans/2026-11-02-data-auditor.md` (10 tasks).

- Task 1 done: `pyproject.toml`, `findings.Finding`, `load.open_table` (CSV and Parquet via DuckDB views), `tests/test_load.py`.
- Task 2 done (`f3c6fdd`): `checks/missing.py` `check_missing` (warning at >= 5% null, error when a column is all null, nothing for 0 rows).
- Task 3 done (`373477b`): `checks/duplicates.py` `check_duplicates` (full-row extra copies as a warning; error for repeated non-null values in columns whose lowercase name ends in `id` or `key`).
- Task 4 done (`00a2eb2`): `checks/types.py` `check_types` (VARCHAR columns only: numbers or dates stored as text at >= 95% and < 100% castable, "mixed types" at 5% to 95% numeric). Boundary cases at exactly 0.95 and 0.05 are not tested yet.
- Task 5 committed (`e88ef6d`): `checks/outliers.py` `check_outliers` (numeric columns, >= 20 non-null values, robust z over median and MAD, |z| > 6, MAD 0 gives nothing). Passed task review.
- Task 6 done (`a64db46`): `checks/schema.py` `compare_schemas(old, new)` (pure; removed column error, added info, retyped warning, matched by name).
- Task 7 committed (`1b0511b`): `audit.py` (`audit_path`, `FileReport`) and `report.py` (`to_json`, `write_json` with exclusive create, `exit_code`). Fixed in `65b7879`: a `duckdb.Error` or `OSError` inside any check becomes one `read` error for that file (rows 0, no columns) and the rest of the folder is still audited.
- Task 8 committed (`a0126fb`): `page.py` `render_html` (self-contained page, every dynamic string escaped, system fonts, light and dark). Opus review approved the code; a test gap (examples, check and severity escaping not guarded) is in a fix round.
- 72 tests passing. Tasks 2-7 passed a sonnet task review.

Next: finish Task 8, then Tasks 9-10 ( CLI, demo data and README). SDD progress ledger: `.tiered-powers/sdd/2026-11-02-data-auditor/progress.md` (git-ignored). See [[roadmap]].
