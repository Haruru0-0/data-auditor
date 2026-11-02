# data-auditor

Command-line tool that scans CSV and Parquet files and reports data-quality problems. Design: `docs/tiered-powers/specs/2026-11-02-data-auditor-design.md`.

## Conventions

- Python 3.12, package in `src/dataauditor`, tests in `tests/`, test-first.
- DuckDB reads and aggregates the data. The tool only reads inputs; it never modifies them.
- Commits are made as Ahmad: no `Co-Authored-By` and no "Generated with Claude" lines. Never push without his explicit yes.
- README numbers come from generated results, never typed by hand.
- Saved reports are never overwritten; each run writes a new timestamped file.
- Static page: system fonts only, no external scripts, fonts or `url(`.

## Commands

- Install: `python -m venv .venv`, then `.venv/Scripts/python.exe -m pip install -e ".[dev]"`
- Test: `.venv/Scripts/python.exe -m pytest -q`

## Memory / Code map

- Read `docs/memory/index.md` at session start; save durable decisions there as Markdown.
- `graphify-out/GRAPH_REPORT.md` summarizes code structure once there is code; refresh with `graphify update .`.
