import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from dataauditor.audit import FileReport, audit_path
from dataauditor.page import render_html
from dataauditor.report import exit_code, write_json

SEVERITIES = ("error", "warning", "info")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dataauditor", description="Scan CSV and Parquet files for data-quality problems."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="audit a file or a folder")
    audit.add_argument("path", type=Path, help="CSV/Parquet file or folder")
    audit.add_argument("--baseline", type=Path, default=None,
                       help="earlier file (or folder) to compare the schema against")
    audit.add_argument("--out", type=Path, default=Path("reports"),
                       help="folder for the saved reports (default: reports)")
    return parser


def _safe_stdout() -> None:
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass


def _summary(reports: list[FileReport]) -> list[str]:
    lines: list[str] = []
    for r in reports:
        lines.append(f"{r.path}: {r.rows} rows, {len(r.columns)} columns")
        counts = {s: sum(1 for f in r.findings if f.severity == s) for s in SEVERITIES}
        lines.append("  " + ", ".join(f"{s}: {n}" for s, n in counts.items()))
        for f in r.findings:
            lines.append(f"  {f.severity} {f.check} {f.column or '-'} {f.message}")
    return lines


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    _safe_stdout()
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    if now is None:
        now = datetime.now(timezone.utc).replace(microsecond=0)

    try:
        reports = audit_path(args.path, args.baseline)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not reports:
        print(f"error: no CSV or Parquet files found in {args.path}", file=sys.stderr)
        return 2

    stamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = args.out / f"audit-{stamp}.json"
    html_path = args.out / f"audit-{stamp}.html"
    for p in (json_path, html_path):
        if p.exists():
            print(f"error: output file already exists: {p}", file=sys.stderr)
            return 2

    try:
        written_json = write_json(reports, args.out, now)
        with open(html_path, "x", encoding="utf-8") as fh:
            fh.write(render_html(reports, now))
    except OSError as exc:
        print(f"error: could not write report: {exc}", file=sys.stderr)
        return 2

    for line in _summary(reports):
        print(line)
    print(f"wrote {written_json} and {html_path}")
    return exit_code(reports)
