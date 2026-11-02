# Gotchas

- The mirror script in jalter needs a GitHub repo with an `origin` remote and a GitLab token; it commits and pushes, so it only runs after Ahmad says yes to pushing.
- `DRY_RUN=1 bash ../dev-tools/mirror-to-gitlab.sh data-auditor` is safe and changes nothing.
- In forecast-tracker, use the repo's `.venv` Python, not the system one. This repo has `.venv`; run tests with `.venv/Scripts/python.exe -m pytest -q` (system Python has no pytest).
- Key-like column detection in `check_duplicates` is name-based, so names such as `paid` or `grid` count as keys and repeated values give an error (ruled behaviour, a known false-positive risk).
- DuckDB `TRY_CAST(... AS DOUBLE)` accepts `nan`, `inf` and `infinity`, so those strings count as numeric in `check_types`.
- The built report page must contain `__AUDIT_DATA__` exactly once (the Python side replaces it); the app matches it with a regex so its own source does not add a second copy. `web/check-build.mjs` asserts this.
- The shadcn components import `cn` from the npm package `cn` (maintainer shadcn, published 2026-11-02, integrity pinned in `web/package-lock.json`); swap in `clsx` + `tailwind-merge` in `web/src/lib/utils.ts` if that is ever a concern.
- `.mcp.json` runs `shadcn@latest` unpinned.
- The built file contains one `url(` string that is a Framer Motion JS literal, not CSS; `check-build.mjs` and `tests/test_page.py` allow exactly that one.
- React's bundle keeps inert strings (`https://react.dev/errors/` and five W3C namespace URIs). `check-build.mjs` allow-lists exactly those; they are never fetched, and any other `http(s)` fails the build.
- On a Windows console the CLI prints non-ASCII characters as `?` (stdout falls back to replacement); the HTML and JSON files keep the real text as UTF-8.
- README numbers are generated: run `python scripts/render_readme.py` (it audits the synthetic demo data), never edit the block between the `numbers` markers by hand.
- The CI web job diffs `src/dataauditor/static/report.html` against a fresh build (`--ignore-cr-at-eol`); it has only been verified locally on Windows, so drop or normalise that step if the first Linux run differs.
- DuckDB 1.5.6 reads a 0-byte CSV as one phantom column `column0` with 0 rows, so `open_table` checks file size first and raises `UnreadableFile`.
