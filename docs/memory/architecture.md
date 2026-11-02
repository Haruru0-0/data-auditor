# Architecture

Status: nothing built yet. This is the planned shape from the design doc, not existing code.

- Python 3.12 package `src/dataauditor`, tests in `tests/`.
- DuckDB reads CSV and Parquet and runs the aggregates.
- One audit run produces a terminal summary, a JSON report and a static HTML page.
- Reports are written as new timestamped files, never overwritten.

See [[decisions]] and [[roadmap]].
