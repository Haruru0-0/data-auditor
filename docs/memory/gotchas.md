# Gotchas

- The mirror script in jalter needs a GitHub repo with an `origin` remote and a GitLab token; it commits and pushes, so it only runs after Ahmad says yes to pushing.
- `DRY_RUN=1 bash ../dev-tools/mirror-to-gitlab.sh data-auditor` is safe and changes nothing.
- In forecast-tracker, use the repo's `.venv` Python, not the system one. This repo has `.venv`; run tests with `.venv/Scripts/python.exe -m pytest -q` (system Python has no pytest).
- Key-like column detection in `check_duplicates` is name-based and token-based: `id`, `key`, `user_id`, `order-key`, `userId`, `APIKey` count; `paid`, `valid`, `grid`, `bid`, `identity` do not. Names with no separator or case boundary (`userid`, `USERID`, `ORDERKEY`) are not flagged, so a real key column named that way is missed.
- DuckDB `TRY_CAST(... AS DOUBLE)` accepts `nan`, `inf` and `infinity`, so those strings count as numeric in `check_types`.
- The shadcn components import `cn` from the npm package `cn` (maintainer shadcn, published 2026-11-02, integrity pinned in `web/package-lock.json`); swap in `clsx` + `tailwind-merge` in `web/src/lib/utils.ts` if that is ever a concern.
- `.mcp.json` pins the shadcn server to `shadcn@4.23.0` (same as `web/package.json`).
- On a Windows console the CLI prints non-ASCII characters as `?` (stdout falls back to replacement); the JSON file keeps the real text as UTF-8.
- README numbers are generated: run `python scripts/render_readme.py` (it audits the synthetic demo data), never edit the block between the `numbers` markers by hand.
- Unverified: DuckDB expands glob characters (`[`, `*`, `?`) in file paths, so a file named like `sales[2024].csv` may be read wrongly or give a false `read` error.
- DuckDB 1.5.6 reads a 0-byte CSV as one phantom column `column0` with 0 rows, so `open_table` checks file size first and raises `UnreadableFile`.
- The upload server has no login, rate limiting or CORS setup; add them before hosting it publicly. Uploads are saved as `upload.<ext>` so glob characters in a real file name cannot reach DuckDB (this resolves the glob worry for uploads only; the CLI path is still unverified).
- `npm run dev` in `web/` needs the API running on port 8000 (Vite proxies `/api`).
- `impossible` is name-based: the "age above 120" rule skips names that also carry a unit or grouping word (`account_age_days`, `age_group`), float NaN is never flagged, and `balance`/`amount` are not treated as non-negative. `header` only sees CSV headers DuckDB sniffed as a header; a header of only blank cells, or literally named `column0,column1`, is skipped.
- A CSV is read once into a temp table with `sample_size=-1` (types sniffed from every row); the first version kept a lazy view and re-parsed the whole file on every query (a 100 MB file would have taken about 8 minutes, now about 15 s for 48 MB). Parquet stays a lazy view.
- DuckDB's `count(*)` and `DESCRIBE` do not parse CSV values, so a bad value only fails at query time. If the temp-table load raises, `load._unparsable_columns` probes each non-text column and the load is retried with those columns as VARCHAR. The `typo` check ignores substitutions on purpose (`Omar`/`Omer`, `Maria`/`Mario` are legitimate).
- Name-based rules look at the LAST word of the column name for emails and phones (`phone_type` and `email_domain` are not checked) and skip signed quantities (`price_change`, `stock_count_delta`). A key-like column such as `customer_id` that legitimately repeats in an orders file is still reported as an error (known false positive).
- `audit.drop_explained_types` drops a `types` "stored as text" finding when the same column has a `format` or `missing-marker` finding, so one fault is not counted twice. A `read` error message keeps only the first line (300 characters) so SQL and temp paths do not leak to the web page.
