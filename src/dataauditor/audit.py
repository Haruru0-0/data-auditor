from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from dataauditor.checks.constant import check_constant
from dataauditor.checks.duplicates import check_duplicates
from dataauditor.checks.dateorder import check_date_order
from dataauditor.checks.formats import check_formats
from dataauditor.checks.headers import check_headers
from dataauditor.checks.impossible import check_impossible
from dataauditor.checks.markers import check_missing_markers
from dataauditor.checks.missing import check_missing
from dataauditor.checks.outliers import check_outliers
from dataauditor.checks.schema import compare_schemas
from dataauditor.checks.skew import check_skew
from dataauditor.checks.types import check_types
from dataauditor.checks.typos import check_typos
from dataauditor.checks.whitespace import check_whitespace
from dataauditor.findings import Finding
from dataauditor.load import Table, UnreadableFile, open_table
from dataauditor.profile import profile_columns
from dataauditor.score import quality_score

SUPPORTED = {".csv", ".parquet"}


@dataclass
class FileReport:
    path: str
    rows: int
    columns: dict[str, str]
    findings: list[Finding]
    profile: dict = field(default_factory=dict)

    @property
    def score(self) -> int:
        return quality_score(self.findings)


READ_ERROR_MAX = 300


def _read_error(exc: Exception) -> Finding:
    """A `read` finding with only the first line of the message (DuckDB's full
    diagnostic can hold SQL, sniffer dumps and temp paths), capped in length."""
    lines = str(exc).strip().splitlines()
    return Finding("read", "error", None, (lines[0] if lines else type(exc).__name__)[:READ_ERROR_MAX], 1)


def drop_explained_types(findings: list[Finding]) -> list[Finding]:
    """Drop a "stored as text" `types` finding when the same column also has a `format`
    or `missing-marker` finding, which already explains why it is text."""
    explained = {f.column for f in findings if f.check in ("format", "missing-marker")}
    return [
        f for f in findings
        if not (f.check == "types" and "stored as text" in f.message and f.column in explained)
    ]


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
        return FileReport(str(path), 0, {}, [_read_error(exc)])
    findings: list[Finding] = []
    try:
        findings += check_missing(con, table)
        findings += check_duplicates(con, table)
        findings += check_types(con, table)
        findings += check_outliers(con, table)
        findings += check_constant(con, table)
        findings += check_whitespace(con, table)
        findings += check_missing_markers(con, table)
        findings += check_impossible(con, table)
        findings += check_headers(con, table)
        findings += check_formats(con, table)
        findings += check_typos(con, table)
        findings += check_skew(con, table)
        findings += check_date_order(con, table)
        if use_baseline:
            findings += _schema_findings(con, table, baseline)
        findings = drop_explained_types(findings)
        profile = profile_columns(con, table)
    except (duckdb.Error, OSError) as exc:
        return FileReport(str(path), 0, {}, [_read_error(exc)])
    return FileReport(str(path), table.rows, table.columns, findings, profile)


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
