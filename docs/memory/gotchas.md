# Gotchas

- The mirror script in jalter needs a GitHub repo with an `origin` remote and a GitLab token; it commits and pushes, so it only runs after Ahmad says yes to pushing.
- `DRY_RUN=1 bash ../dev-tools/mirror-to-gitlab.sh data-auditor` is safe and changes nothing.
- In forecast-tracker, use the repo's `.venv` Python, not the system one. Check the same here once a venv exists (inferred).
