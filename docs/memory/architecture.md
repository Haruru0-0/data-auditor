# Architecture

Status: loader, checks, runner, JSON report, CLI and the upload web app are built; demo data, the README numbers script and CI are built too.

- Python 3.12 package `src/dataauditor`, tests in `tests/`.
- `load.open_table` creates a uniquely named DuckDB view over `read_csv`/`read_parquet` and returns a `Table` (rows, columns in file order). Failures and unsupported types raise `UnreadableFile`.
- `findings.Finding` is a frozen dataclass; each check returns a list of them.
- `audit.audit_path` runs the checks per file (a failure in any check becomes a `read` error for that file) and `report` writes the JSON.
- The upload web app is the standard Vite `react-ts` layout in `web/`: `src/App.tsx` is the upload page and posts a file to the FastAPI backend in `server.py`, which runs the same audit and returns the JSON; `src/AuditReport.tsx` is the results view (shadcn/ui, Tailwind, Framer Motion). `npm run build` typechecks and writes `web/dist`, which the server serves.
- `cli.main` runs one audit and produces a terminal summary and a JSON report, returning the exit code.
- Reports are written as new timestamped files, never overwritten.

See [[decisions]] and [[roadmap]].
- Checks run in `audit._audit_file` in this order: missing, duplicates, types, outliers, constant, whitespace, missing-marker, impossible, header, format, typo, skew, date-order, then schema drift when a baseline is given. Name-based rules share `checks/_names.py`.
