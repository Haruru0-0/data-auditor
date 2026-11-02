import json
from datetime import datetime, timezone
from pathlib import Path

from dataauditor.audit import FileReport


def exit_code(reports: list[FileReport]) -> int:
    return int(any(f.severity == "error" for r in reports for f in r.findings))


def _utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def to_json(reports: list[FileReport], generated_at: datetime) -> str:
    totals = {"info": 0, "warning": 0, "error": 0}
    files = []
    for r in reports:
        for f in r.findings:
            totals[f.severity] = totals.get(f.severity, 0) + 1
        files.append({
            "path": r.path,
            "rows": r.rows,
            "columns": dict(r.columns),
            "findings": [
                {
                    "check": f.check,
                    "severity": f.severity,
                    "column": f.column,
                    "message": f.message,
                    "count": f.count,
                    "examples": list(f.examples),
                }
                for f in r.findings
            ],
        })
    doc = {
        "generated_at": _utc(generated_at).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": files,
        "totals": totals,
    }
    return json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False)


def write_json(reports: list[FileReport], out_dir: Path, now: datetime) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"audit-{_utc(now).strftime('%Y%m%dT%H%M%SZ')}.json"
    text = to_json(reports, now)
    with open(path, "x", encoding="utf-8") as fh:
        fh.write(text)
    return path
