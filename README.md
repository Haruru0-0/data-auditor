# data-auditor

A command-line tool that scans CSV and Parquet files and reports data-quality problems. DuckDB reads and aggregates the data. The tool only reads your files; it never modifies them.

## Checks

- Missing values per column (count and percent).
- Duplicate rows, and repeated values in columns that look like keys.
- Type problems: numbers or dates stored as text, mixed types in one column.
- Outliers in numeric columns, using median and MAD (a robust z-score) with a high cutoff.
- Schema drift: columns added, removed or retyped compared with a baseline version of the file.
- Constant columns: every value is the same.
- Extra spaces and case variants: values with leading or trailing spaces, or the same value written in more than one case.
- Missing-data markers: text such as `n/a`, `null` or `-` standing in for a missing value.
- Impossible values: negative ages, quantities or prices, ages above 120, percentages outside 0-100, birth dates in the future or before 1900. Columns whose names say they hold a change (`delta`, `change`, `diff`, `difference`, `adjustment`, `variance`, `net`) may be negative.
- Header problems: blank or repeated column names, `Unnamed: 0` index columns, names with extra spaces.
- Format problems: dates written in more than one format in a column, invalid email addresses, phone numbers that are too short or long or contain letters (a trailing extension such as `x12` or `ext 5` is ignored). The email and phone rules apply when the key word is the last word of the column name (`home_email`, `mobile`), not `phone_type`.
- Probable typos: rare spellings one edit away from a much more common value in a column of categories.
- Skew: a column where one value makes up more than 99% of the non-empty values (at least 100 of them), and rows that are mostly empty.
- Date order: an end date before its start date (also created/updated, open/close and similar pairs).

Thresholds are conservative on purpose, and every finding shows its evidence (counts and examples).

## Requirements and install

Python 3.12.

```
python -m venv .venv
.venv\Scripts\Activate.ps1     # PowerShell on Windows
source .venv/bin/activate     # macOS/Linux
pip install -e ".[dev]"
```

## Usage

```
dataauditor audit PATH [--baseline PATH] [--out DIR]
```

`PATH` is a CSV or Parquet file, or a folder of them. Folder scans are non-recursive: only the files directly inside the folder are audited. `--baseline` is the earlier version of the file (or a folder with files of the same names) for the schema drift check. `--out` is the folder for the saved report.

Exit codes: 0 when there is no error-level finding, 1 when there is at least one, 2 when the command could not run (for example a path that does not exist).

Each run produces a terminal summary and a timestamped JSON report (`audit-<stamp>.json`). Saved reports are never overwritten; each run writes a new file.

Every file also gets a quality score from 0 to 100: it starts at 100 and loses 20 per error (at most 60 in total), 7 per warning (at most 35) and 1 per info finding (at most 5); an unreadable file scores 0. It is a rough indicator for comparing runs, not a standard. The report also holds a per-column profile (type, missing count, distinct count, and min, max and mean where they apply), saved in the JSON report and shown in the web results view; the score is also in the CLI summary.

## Demo results

The numbers below come from running `python scripts/render_readme.py`, which writes synthetic CSV files with known injected faults (including a clean file and a baseline copy of each file), audits them, and counts how many injected faults were found. Rerun it and commit the result after changing a check.

<!-- numbers:start -->
| Measure | Value |
| --- | --- |
| Files audited | 11 |
| Faults injected | 18 |
| Faults found | 18 |
| Recall | 100% |
| False positives | 0 |
<!-- numbers:end -->

A fault counts as found when the matching check reports a warning or error on the same file and column. A false positive is a warning or error that no injected fault explains. The matching table is in `scripts/render_readme.py`. The data is synthetic and small, so this shows that the checks work as designed, not how they behave on your data.

## Web app

A normal web page where you upload a CSV or Parquet file and see the audit. The React page (`web/`) posts the file to a small FastAPI backend (`src/dataauditor/server.py`) that runs the same checks as the CLI. Uploads are limited to 50 MB, are written to a temporary folder that is deleted afterwards, and are never kept.

Run it (the web dependencies are in the `web` extra, already included in `dev`):

```
pip install -e ".[web]"
cd web && npm ci && npm run build && cd ..
uvicorn dataauditor.server:app --port 8000
```

Then open http://localhost:8000. For development with hot reload, run the API as above and `npm run dev` in `web/`; Vite proxies `/api` to port 8000. `DATAAUDITOR_WEB_DIR` points the server at a different build folder.

## Tests

```
pytest
cd web && npm test
```

## Limits

- Built for ordinary-sized files that fit on a laptop; no streaming or sampling.
- The heuristics are conservative, so small problems can go unreported.
- Key detection is name-based: a column is key-like when `id` or `key` is the last word of its name: the whole name, after a separator (`_`, `-`, space, `.`), or after a camelCase boundary (`user_id`, `order-key`, `userId`, `APIKey`). Names such as `paid`, `valid` or `monkey` are not key-like.
- Column types are sniffed by DuckDB from every row of a CSV; a column whose values do not fit the sniffed type is loaded as text, so the file still loads (mixed date formats are then reported by the `format` check).
- Impossible values, date order, the email and phone rules and key detection are heuristics based on column names (`age`, `start_date`/`end_date`, `email`, `phone`); a column with a different name is not checked. Key-like columns such as `customer_id` that legitimately repeat in an orders table are still reported as errors.
- The typo check only catches an inserted letter, a deleted letter or two adjacent letters swapped, and ignores values that contain digits.
- Schema drift needs a baseline to compare against.
- It reports problems only; cleaning or fixing data is not built yet.
