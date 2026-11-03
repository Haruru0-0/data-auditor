# data-auditor

Command-line tool that scans CSV and Parquet files and reports data-quality problems. Design: `docs/tiered-powers/specs/2026-11-02-data-auditor-design.md`.

## Conventions

- Python 3.12, package in `src/dataauditor`, tests in `tests/`, test-first.
- DuckDB reads and aggregates the data. The tool only reads inputs; it never modifies them.
- Commits are made as Ahmad: no `Co-Authored-By` and no "Generated with Claude" lines. Never push without his explicit yes.
- README numbers come from generated results, never typed by hand.
- Saved reports are never overwritten; each run writes a new timestamped file.
- Web app (standard Vite react-ts layout in `web/`: `src/App.tsx` is the upload page, `src/AuditReport.tsx` the results view): upload a CSV/Parquet file to the FastAPI backend (`src/dataauditor/server.py`, max 50 MB, temp file deleted, original name only reported).
- Web UI: React + Vite (`web/`) with shadcn/ui (Tailwind) components and Framer Motion for animation, `prefers-reduced-motion` respected; never use `dangerouslySetInnerHTML`; shadcn MCP is configured in `.mcp.json`.

## Commands

- Install: `python -m venv .venv`, then `.venv/Scripts/python.exe -m pip install -e ".[dev]"`
- Test: `.venv/Scripts/python.exe -m pytest -q`
- Web: in `web/`, `npm ci`, `npm test`, `npm run build` (typechecks, then builds `web/dist`), `npm run lint`, `npm run dev` (hot reload; needs the API running)
- Web app: `uvicorn dataauditor.server:app --port 8000` serves `/api/audit` and `web/dist`

## Memory / Code map

- Read `docs/memory/index.md` at session start; save durable decisions there as Markdown.
- `graphify-out/GRAPH_REPORT.md` summarizes code structure once there is code; refresh with `graphify update .`.
