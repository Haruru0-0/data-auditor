# data-auditor: design

Status: draft for Ahmad's approval. Nothing is built yet.

## Intent and why

Portfolio project 4. A command-line tool that scans ordinary tabular files (CSV, Parquet) and reports what is wrong with them, then publishes the findings as a report anyone can open. It is the second repo after forecast-tracker, and it should look like it came from the same author: small, tested, honest numbers, a static page.

The point of the project is to show careful engineering on a problem every data team has, not to out-feature Great Expectations or pandera. Scale (billions of rows) is a later step; v1 targets ordinary files that fit on a laptop, but is built on DuckDB so scaling up later does not mean a rewrite.

## Goals

- Point it at a file or folder, get a clear list of data problems with counts, examples and severity.
- Checks in v1:
  1. Missing values per column (count, percent).
  2. Duplicate rows, and duplicate values in columns that look like keys.
  3. Type problems: numbers or dates stored as text, mixed types in one column.
  4. Outliers in numeric columns (a robust rule, not mean and standard deviation).
  5. Schema drift: compare two versions of the same file (columns added, removed, retyped).
- Three outputs from one run: a terminal summary, a JSON report, a self-contained HTML report page (React + Vite single-file build with the audit JSON embedded; system fonts, light and dark, no external requests).
- Exit code reflects findings, so it can fail a CI job.
- README numbers come from generated results on public demo datasets, never typed by hand.

## Non-goals

- No streaming, no billion-row runs, no scheduled daily job in v1.
- No fixing or rewriting of the user's data. It only reads.
- No custom-rules config file in v1 (planned as v2).
- No database sources, no web UI beyond the static report.

## Anti-goals

- A tool that cries wolf. If most columns get flagged on normal data, it has failed even if it technically works. Thresholds must be conservative and every finding must show the evidence.
- Silent skipping. A file it cannot read is reported as a problem, never ignored.
- Modifying or overwriting input files or earlier saved reports.

## Constraints

- Python 3.12, package in `src/dataauditor`, tests in `tests/`, test-first.
- DuckDB for reading and aggregating (my call, for the later scale-up).
- Pinned dependencies; no network access at audit time.
- Commits are made as Ahmad: no `Co-Authored-By` and no "Generated with Claude" lines. Never push without his explicit yes. (Same rules as forecast-tracker.)
- Saved reports are never overwritten; each run writes a new timestamped file.
- Report page: React + Vite single-file build, audit JSON embedded; system fonts only, no external requests (no external scripts, fonts or `url(`).

## Decisions Ahmad made

- Build project 4, the data-quality auditor, after project 1.
- First version works on normal (ordinary-sized) data.
- Lives in its own new repo.
- Outputs: terminal, JSON and static page, with a CLI. He approved the playback of the checks list above.

## My calls (change any of these)

- Name: `data-auditor`, package `dataauditor`.
- Outlier rule: median and MAD (robust z-score), flagged only past a high cutoff.
- Key-like column: a column whose name ends in `id` or `key`, or whose values are all distinct. Duplicates in it are reported as high severity.
- Severity levels: info, warning, error. Exit code 1 only if there is at least one error.
- Demo datasets: two or three small public datasets committed or fetched by a script, chosen when planning.
- HTML report reuses forecast-tracker's visual style rather than inventing a new one.

## Left to the builder

- Module layout and exact function names.
- Exact thresholds, as long as they are conservative and documented.
- How to sample large files, if needed.
- Which demo datasets to use.

## Open questions

None blocking. Licence and public author identity are the same open items as forecast-tracker.
