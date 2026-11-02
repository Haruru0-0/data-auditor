# Architecture

Status: loader and Finding model built; checks, runner, reports and CLI are still planned (see the design doc).

- Python 3.12 package `src/dataauditor`, tests in `tests/`.
- `load.open_table` creates a uniquely named DuckDB view over `read_csv`/`read_parquet` and returns a `Table` (rows, columns in file order). Failures and unsupported types raise `UnreadableFile`.
- `findings.Finding` is a frozen dataclass; checks will return lists of it.
- One audit run will produce a terminal summary, a JSON report and a static HTML page.
- Reports are written as new timestamped files, never overwritten.

See [[decisions]] and [[roadmap]].
