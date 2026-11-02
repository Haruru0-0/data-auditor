# data-auditor

A command-line tool that scans CSV and Parquet files and reports data-quality problems. DuckDB reads and aggregates the data. The tool only reads your files; it never modifies them.

## Checks

- Missing values per column (count and percent).
- Duplicate rows, and repeated values in columns that look like keys.
- Type problems: numbers or dates stored as text, mixed types in one column.
- Outliers in numeric columns, using median and MAD (a robust z-score) with a high cutoff.
- Schema drift: columns added, removed or retyped compared with a baseline version of the file.

Thresholds are conservative on purpose, and every finding shows its evidence (counts and examples).

## Requirements and install

Python 3.12.

```
python -m venv .venv
.venv/Scripts/activate        # on macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```
dataauditor audit PATH [--baseline PATH] [--out DIR]
```

`PATH` is a CSV or Parquet file, or a folder of them. `--baseline` is the earlier version of the file (or a folder with files of the same names) for the schema drift check. `--out` is the folder for saved reports.

Exit codes: 0 when there is no error-level finding, 1 when there is at least one, 2 when the command could not run (for example a path that does not exist).

Each run produces:

- a terminal summary,
- a timestamped JSON report (`audit-<stamp>.json`),
- a self-contained HTML report page (`audit-<stamp>.html`).

Saved reports are never overwritten; each run writes new files.

## Demo results

The numbers below come from running `python scripts/render_readme.py`, which writes synthetic CSV files with known injected faults (including a clean file and a baseline copy of each file), audits them, and counts how many injected faults were found. Rerun it and commit the result after changing a check.

<!-- numbers:start -->
| Measure | Value |
| --- | --- |
| Files audited | 7 |
| Faults injected | 7 |
| Faults found | 7 |
| Recall | 100% |
| False positives | 0 |
<!-- numbers:end -->

A fault counts as found when the matching check reports a warning or error on the same file and column. A false positive is a warning or error that no injected fault explains. The matching table is in `scripts/render_readme.py`. The data is synthetic and small, so this shows that the checks work as designed, not how they behave on your data.

## Report page

The HTML report is built with React, Vite, shadcn/ui and Framer Motion into one committed file, `src/dataauditor/static/report.html`. The audit JSON is embedded in it and the page makes no network requests (system fonts, no external scripts). To rebuild it after changing the page source:

```
cd web && npm ci && npm run build
```

## Tests

```
pytest
cd web && npm test
```

## Limits

- Built for ordinary-sized files that fit on a laptop; no streaming or sampling.
- The heuristics are conservative, so small problems can go unreported.
- Key detection is name-based: a column is key-like when its name ends in `id` or `key`.
- Schema drift needs a baseline to compare against.
- It reports problems only; cleaning or fixing data is not built yet.
