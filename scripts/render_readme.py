"""Fill the generated numbers block in README.md from a real run on the demo data.

Run: python scripts/render_readme.py [--readme README.md] [--results results.json]
It writes the demo data to a temporary folder, audits it, matches the findings
to the injected faults, then replaces only the text between the numbers markers.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_demo_data  # noqa: E402

START = "<!-- numbers:start -->"
END = "<!-- numbers:end -->"

# The one matching table. A fault name is "<kind>" or "<kind>:<column>". It counts
# as found when the same file has a finding of the mapped check, severity warning
# or error, on that column (column None when the fault has no column).
FAULT_TO_CHECK = {
    "null_column": "missing",
    "dup_key": "duplicates",
    "dup_rows": "duplicates",
    "text_numbers": "types",
    "outlier": "outliers",
    "schema_dropped": "schema",
    "schema_retyped": "schema",
    "text_placeholder": "missing-marker",
    "constant": "constant",
    "padded_case": "whitespace",
    "impossible": "impossible",
    "header_unnamed": "header",
    "header_duplicate": "header",
    "mixed_dates": "format",
    "bad_email": "format",
    "typo": "typo",
    "empty_rows": "skew",
    "date_order": "date-order",
}


def _split(fault: str) -> tuple[str, str | None]:
    kind, _, column = fault.partition(":")
    return FAULT_TO_CHECK[kind], column or None


def fault_matches(fault: str, finding) -> bool:
    check, column = _split(fault)
    return (
        finding.severity in ("warning", "error")
        and finding.check == check
        and finding.column == column
    )


def evaluate(reports, faults: dict[str, list[str]]) -> dict[str, int]:
    """Count files, injected faults, faults found and warning/error findings no fault explains."""
    by_file = {Path(r.path).name: r for r in reports}
    found = false_positives = 0
    for name, report in by_file.items():
        names = faults.get(name, [])
        found += sum(any(fault_matches(f, x) for x in report.findings) for f in names)
        false_positives += sum(
            x.severity in ("warning", "error") and not any(fault_matches(f, x) for f in names)
            for x in report.findings
        )
    return {
        "files_audited": len(by_file),
        "faults_injected": sum(len(v) for v in faults.values()),
        "faults_found": found,
        "false_positives": false_positives,
    }


def run_demo(seed: int = 7) -> dict[str, int]:
    from dataauditor.audit import audit_path

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        faults = make_demo_data.make_demo(root, seed)
        reports = audit_path(root / "current", baseline=root / "baseline")
        return evaluate(reports, faults)


def _block(results: dict, nl: str) -> str:
    injected = results["faults_injected"]
    found = results["faults_found"]
    # Floor to one decimal so 199/200 never reads as 100%; whole numbers print without ".0".
    recall = "n/a"
    if injected:
        tenths = found * 1000 // injected
        recall = f"{tenths // 10}%" if tenths % 10 == 0 else f"{tenths / 10:.1f}%"
    lines = [
        "| Measure | Value |",
        "| --- | --- |",
        f"| Files audited | {results['files_audited']} |",
        f"| Faults injected | {injected} |",
        f"| Faults found | {found} |",
        f"| Recall | {recall} |",
        f"| False positives | {results['false_positives']} |",
    ]
    return nl.join(lines)


def render_numbers(results_json: Path, readme: Path) -> None:
    results = json.loads(Path(results_json).read_text(encoding="utf-8"))
    text = Path(readme).read_bytes().decode("utf-8")
    for marker in (START, END):
        count = text.count(marker)
        if count == 0:
            raise ValueError(f"marker not found in {readme}: {marker}")
        if count > 1:
            raise ValueError(f"marker appears {count} times in {readme}: {marker}")
    start = text.index(START)
    end = text.index(END)
    if end < start:
        raise ValueError(f"markers are in the wrong order in {readme}: {END} comes before {START}")
    after_start = start + len(START)
    nl = "\r\n" if text.startswith("\r\n", after_start) else "\n"
    new = text[:after_start] + nl + _block(results, nl) + nl + text[end:]
    Path(readme).write_bytes(new.encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenerate the numbers block in the README.")
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    parser.add_argument("--results", type=Path, default=None, help="also keep the results JSON here")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)
    results = run_demo(args.seed)
    with tempfile.TemporaryDirectory() as tmp:
        path = args.results or Path(tmp) / "results.json"
        path.write_text(json.dumps(results, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        render_numbers(path, args.readme)
    print(json.dumps(results, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
