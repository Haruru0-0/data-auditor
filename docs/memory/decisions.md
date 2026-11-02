# Decisions

Made by Ahmad:
- Project 4 is a data-quality auditor, built after forecast-tracker.
- First version targets normal-sized data, in a new folder and a new repo.
- Auditor first; cleaning is a possible later addition.
- Mirror the GitHub repo to GitLab the way jalter does (`dev-tools/mirror-to-gitlab.sh`).

- Stay on Python for everything (audit now, cleaning later); Rust was considered and dropped for v1 (decided 2026-11-02).
- The report page is React + Vite, replacing the pure-Python page (2026-11-02). Ruled by Claude on how: single-file build committed at `src/dataauditor/static/report.html` so CLI users need no Node; audit JSON embedded in a script block; no external requests. Costs: the page needs JavaScript, and CI needs Node.
- Ahmad also wants shadcn/ui and Framer Motion for the page's animation, and the shadcn MCP server and registries set up for the repo (2026-11-02). Built in Task 8c; `.mcp.json` has the shadcn server, registries stay at the default.

- Open for Ahmad: commits are authored as `Haru <ahmad.w.kanaan@proton.me>` (the git config) while CLAUDE.md says "as Ahmad"; and the `cn` npm package (published the day it was adopted) could be swapped for `clsx` + `tailwind-merge`.

Made by Claude (marked as calls in the design doc, open to change):
- Name `data-auditor`, package `dataauditor`.
- Outliers use median and MAD; exit code 1 only on error-level findings.

Process rules carried over from forecast-tracker: commits as Ahmad without co-author or generated-with lines, never push without his explicit yes.

See [[architecture]].
