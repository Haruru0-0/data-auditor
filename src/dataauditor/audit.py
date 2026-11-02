from dataclasses import dataclass
from pathlib import Path

import duckdb

from dataauditor.checks.duplicates import check_duplicates
from dataauditor.checks.missing import check_missing
from dataauditor.checks.outliers import check_outliers
from dataauditor.checks.schema import compare_schemas
from dataauditor.checks.types import check_types
from dataauditor.findings import Finding
from dataauditor.load import Table, UnreadableFile, open_table

SUPPORTED = {".csv", ".parquet"}


@dataclass
class FileReport:
    path: str
    rows: int
    columns: dict[str, str]
    findings: list[Finding]


def _files_in(folder: Path) -> list[Path]:
    return sorted(
        (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED),
        key=lambda p: p.name,
    )


def _schema_findings(con, table: Table, baseline_file: Path | None) -> list[Finding]:
    if baseline_file is None or not baseline_file.is_file():
        return [Finding("schema", "info", None, "no baseline file to compare against", 1)]
    try:
        old = open_table(con, baseline_file)
    except UnreadableFile as exc:
        return [Finding("schema", "warning", None, f"baseline unreadable: {exc}", 1)]
    return compare_schemas(old, table)


def _audit_file(con, path: Path, baseline: Path | None, use_baseline: bool) -> FileReport:
    try:
        table = open_table(con, path)
    except UnreadableFile as exc:
        return FileReport(str(path), 0, {}, [Finding("read", "error", None, str(exc), 1)])
    findings: list[Finding] = []
    findings += check_missing(con, table)
    findings += check_duplicates(con, table)
    findings += check_types(con, table)
    findings += check_outliers(con, table)
    if use_baseline:
        findings += _schema_findings(con, table, baseline)
    return FileReport(str(path), table.rows, table.columns, findings)


def audit_path(path: Path, baseline: Path | None = None) -> list[FileReport]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"path not found: {path}")
    if baseline is not None:
        baseline = Path(baseline)
        if not baseline.exists():
            raise FileNotFoundError(f"baseline not found: {baseline}")
        if path.is_dir() and baseline.is_file():
            raise ValueError("baseline must be a folder when auditing a folder")
    files = _files_in(path) if path.is_dir() else [path]
    con = duckdb.connect(":memory:")
    try:
        reports = []
        for f in files:
            if baseline is None:
                base = None
            elif baseline.is_dir():
                base = baseline / f.name
            else:
                base = baseline
            reports.append(_audit_file(con, f, base, baseline is not None))
        return reports
    finally:
        con.close()
