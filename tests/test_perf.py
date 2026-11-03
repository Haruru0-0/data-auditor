import time

import pytest

from dataauditor.audit import audit_path


@pytest.mark.slow
def test_wide_csv_runs_every_check_in_time(tmp_path):
    # CSV is read once into a table; the checks must not re-parse the file per query.
    cols = [f"c{i}" for i in range(20)]
    lines = [",".join(["id"] + cols)]
    for r in range(60000):
        lines.append(",".join([str(r)] + [str((r * (i + 3)) % 997) if i % 2 else f"v{(r + i) % 50}" for i in range(20)]))
    (tmp_path / "wide.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    start = time.perf_counter()
    [report] = audit_path(tmp_path / "wide.csv")
    elapsed = time.perf_counter() - start
    assert not any(f.check == "read" for f in report.findings)
    assert report.rows == 60000 and len(report.profile) == 21
    assert elapsed < 60, f"audit took {elapsed:.1f}s"
