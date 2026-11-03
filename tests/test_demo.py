"""Tests for the synthetic demo data and its audit.

scripts/ is not a package, so the scripts are loaded by file path.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

from dataauditor.audit import audit_path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load(name: str):
    sys.path.insert(0, str(SCRIPTS))  # render_readme imports make_demo_data as a sibling
    try:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


demo = _load("make_demo_data")
render = _load("render_readme")


def _snapshot(folder: Path) -> dict[str, bytes]:
    return {
        p.relative_to(folder).as_posix(): p.read_bytes()
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }


def test_same_seed_gives_identical_bytes(tmp_path):
    a = demo.make_demo(tmp_path / "a", seed=7)
    b = demo.make_demo(tmp_path / "b", seed=7)
    assert a == b
    assert _snapshot(tmp_path / "a") == _snapshot(tmp_path / "b")
    assert _snapshot(tmp_path / "a")


def test_different_seed_changes_data(tmp_path):
    demo.make_demo(tmp_path / "a", seed=7)
    demo.make_demo(tmp_path / "b", seed=8)
    assert _snapshot(tmp_path / "a") != _snapshot(tmp_path / "b")


def test_layout_and_clean_file(tmp_path):
    faults = demo.make_demo(tmp_path)
    assert [] in faults.values()
    for name in faults:
        assert (tmp_path / "current" / name).is_file()
        assert (tmp_path / "baseline" / name).is_file()
    assert not list((tmp_path / "current").glob("*.json"))


@pytest.fixture(scope="module")
def audited(tmp_path_factory):
    root = tmp_path_factory.mktemp("demo")
    faults = demo.make_demo(root)
    reports = audit_path(root / "current", baseline=root / "baseline")
    return root, faults, reports


def test_every_injected_fault_is_found(audited):
    _, faults, reports = audited
    result = render.evaluate(reports, faults)
    assert result["faults_injected"] >= 6
    assert result["faults_found"] == result["faults_injected"]


def test_every_check_family_is_covered(audited):
    _, faults, _ = audited
    kinds = {f.split(":")[0] for fs in faults.values() for f in fs}
    families = {render.FAULT_TO_CHECK[k] for k in kinds}
    assert families == {
        "missing", "duplicates", "types", "outliers", "schema", "constant", "whitespace",
        "missing-marker", "impossible", "header", "format", "typo", "skew", "date-order",
    }


def test_numbers_as_text_fault_is_not_a_missing_marker(audited):
    # The placeholder in the numbers-as-text fault must not be a missing marker, so only
    # `types` explains it; the separate text-placeholder fault covers `missing-marker`.
    _, faults, reports = audited
    assert faults["products.csv"] == ["text_numbers:price"]
    products = next(r for r in reports if Path(r.path).name == "products.csv")
    assert [f for f in products.findings if f.check == "missing-marker"] == []


def test_every_fault_is_found_by_its_own_check(audited):
    _, faults, reports = audited
    by_file = {Path(r.path).name: r for r in reports}
    for name, injected in faults.items():
        for fault in injected:
            assert any(render.fault_matches(fault, f) for f in by_file[name].findings), (name, fault)


def test_clean_file_has_no_warning_or_error(audited):
    _, faults, reports = audited
    clean = [n for n, fs in faults.items() if not fs]
    assert clean
    for report in reports:
        if Path(report.path).name in clean:
            assert [f for f in report.findings if f.severity in ("warning", "error")] == []


def test_no_false_positives(audited):
    _, faults, reports = audited
    assert render.evaluate(reports, faults)["false_positives"] == 0
    assert render.evaluate(reports, faults)["files_audited"] == len(faults)


def test_audit_does_not_modify_inputs(tmp_path):
    demo.make_demo(tmp_path)
    before = _snapshot(tmp_path)
    audit_path(tmp_path / "current", baseline=tmp_path / "baseline")
    assert _snapshot(tmp_path) == before
