# Gotchas

- The mirror script in jalter needs a GitHub repo with an `origin` remote and a GitLab token; it commits and pushes, so it only runs after Ahmad says yes to pushing.
- `DRY_RUN=1 bash ../dev-tools/mirror-to-gitlab.sh data-auditor` is safe and changes nothing.
- In forecast-tracker, use the repo's `.venv` Python, not the system one. This repo has `.venv`; run tests with `.venv/Scripts/python.exe -m pytest -q` (system Python has no pytest).
- DuckDB 1.5.6 reads a 0-byte CSV as one phantom column `column0` with 0 rows, so `open_table` checks file size first and raises `UnreadableFile`.
