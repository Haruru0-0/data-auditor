# Roadmap

## v1 (ordinary-sized CSV and Parquet files)
- Missing values, duplicate rows and keys, type problems, outliers, schema drift.
- Terminal and JSON outputs from the CLI, plus an upload web app (React + Vite page, FastAPI backend); exit code 1 on any error-level finding.

## v1.1 (proposed, not yet agreed)
- A separate `clean` step that writes a new cleaned file plus a change log, never touching the input.

## Later
- Custom-rules config file, scale to large datasets (GH Archive was the example), scheduled daily run.

See [[decisions]].
