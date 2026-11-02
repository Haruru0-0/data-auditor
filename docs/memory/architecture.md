# Architecture

Status: loader, checks, runner, JSON report, React report page and CLI are built; demo data, the README numbers script and CI are built too (Task 10).

- Python 3.12 package `src/dataauditor`, tests in `tests/`.
- `load.open_table` creates a uniquely named DuckDB view over `read_csv`/`read_parquet` and returns a `Table` (rows, columns in file order). Failures and unsupported types raise `UnreadableFile`.
- `findings.Finding` is a frozen dataclass; checks will return lists of it.
- `audit.audit_path` runs the checks per file (a failure in any check becomes a `read` error for that file) and `report` writes the JSON.
- The report page is a React + Vite app in `web/`, built to one committed file at `src/dataauditor/static/report.html`; `page.render_html` embeds the audit JSON into it. It uses shadcn/ui (Tailwind) components and Framer Motion for animation.
- `cli.main` runs one audit and produces a terminal summary, a JSON report and the HTML page, returning the exit code.
- Reports are written as new timestamped files, never overwritten.

See [[decisions]] and [[roadmap]].
