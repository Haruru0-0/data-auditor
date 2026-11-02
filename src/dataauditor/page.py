from datetime import datetime, timezone
from html import escape

from dataauditor.audit import FileReport

_SYMBOLS = {"error": "✖", "warning": "▲", "info": "ℹ"}

_CSS = """
:root {
  --bg: #f6f7f9; --card: #ffffff; --text: #1b1f24; --muted: #5b6470;
  --border: #d5dae1; --error: #b42318; --warning: #8a5a00; --info: #1d5fa8;
  --radius: 8px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #14171b; --card: #1d2228; --text: #e6e9ed; --muted: #9aa4b0;
    --border: #343b44; --error: #ff8a80; --warning: #ffc965; --info: #82b4f0;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 16px; background: var(--bg); color: var(--text);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif; line-height: 1.5;
}
main { max-width: 72rem; margin: 0 auto; }
h1 { margin: 0 0 4px; font-size: 1.6rem; }
h2 { margin: 0 0 4px; font-size: 1.1rem; }
.mono, code { font-family: ui-monospace, Consolas, monospace; }
.meta { color: var(--muted); margin: 0 0 12px; }
.totals { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 20px; padding: 0; list-style: none; }
.totals li { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 6px 12px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; margin: 0 0 16px; }
.wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; min-width: 40rem; }
th, td { text-align: left; vertical-align: top; padding: 6px 8px; border-bottom: 1px solid var(--border); }
th { color: var(--muted); font-weight: 600; font-size: 0.85rem; }
.sev { font-weight: 600; white-space: nowrap; }
.sev-error { color: var(--error); }
.sev-warning { color: var(--warning); }
.sev-info { color: var(--info); }
""".strip()


def _utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def _sev(severity: str) -> str:
    symbol = _SYMBOLS.get(severity, "•")
    cls = severity if severity in _SYMBOLS else "info"
    return f'<span class="sev sev-{cls}">{symbol} {_e(severity)}</span>'


def _card(report: FileReport) -> str:
    parts = [
        '<section class="card">',
        f'<h2 class="mono">{_e(report.path)}</h2>',
        f'<p class="meta">{int(report.rows)} rows · {len(report.columns)} columns</p>',
    ]
    if not report.findings:
        parts.append("<p>No problems found</p>")
    else:
        parts.append('<div class="wrap"><table><thead><tr>'
                     "<th>Severity</th><th>Check</th><th>Column</th>"
                     "<th>Message</th><th>Count</th><th>Examples</th>"
                     "</tr></thead><tbody>")
        for f in report.findings:
            column = _e(f.column) if f.column is not None else ""
            examples = ", ".join(f'<code class="mono">{_e(x)}</code>' for x in f.examples)
            parts.append(
                f"<tr><td>{_sev(f.severity)}</td><td>{_e(f.check)}</td>"
                f"<td>{column}</td><td>{_e(f.message)}</td>"
                f"<td>{int(f.count)}</td><td>{examples}</td></tr>"
            )
        parts.append("</tbody></table></div>")
    parts.append("</section>")
    return "\n".join(parts)


def render_html(reports: list[FileReport], generated_at: datetime) -> str:
    totals = {"info": 0, "warning": 0, "error": 0}
    for r in reports:
        for f in r.findings:
            totals[f.severity] = totals.get(f.severity, 0) + 1
    stamp = _utc(generated_at).strftime("%Y-%m-%dT%H:%M:%SZ")
    total_items = "".join(
        f"<li>{_sev(s)}: {int(totals[s])}</li>" for s in ("error", "warning", "info")
    )
    body = "\n".join(_card(r) for r in reports) if reports else "<p>No files audited</p>"
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Data audit</title>\n"
        f"<style>\n{_CSS}\n</style>\n"
        "</head>\n<body>\n<main>\n"
        "<header>\n<h1>Data audit</h1>\n"
        f'<p class="meta">Generated {_e(stamp)}</p>\n'
        f'<ul class="totals">{total_items}</ul>\n</header>\n'
        f"{body}\n"
        "</main>\n</body>\n</html>\n"
    )
