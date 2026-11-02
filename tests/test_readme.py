"""Tests for render_numbers. scripts/ is not a package, so it is loaded by file path."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
try:
    _spec = importlib.util.spec_from_file_location("render_readme", SCRIPTS / "render_readme.py")
    render = importlib.util.module_from_spec(_spec)
    sys.modules["render_readme"] = render
    _spec.loader.exec_module(render)
finally:
    sys.path.remove(str(SCRIPTS))

START = "<!-- numbers:start -->"
END = "<!-- numbers:end -->"
BEFORE = "# Title\r\nline with CRLF\r\n\r\nmixed LF line\n"
AFTER = "\ntrailing text\r\nlast line without newline"


def _setup(tmp_path, middle="\nold content\n", before=BEFORE, after=AFTER):
    readme = tmp_path / "README.md"
    readme.write_bytes((before + START + middle + END + after).encode("utf-8"))
    results = tmp_path / "results.json"
    results.write_text(
        json.dumps({"files_audited": 5, "faults_injected": 8, "faults_found": 8, "false_positives": 0}),
        encoding="utf-8",
    )
    return readme, results


def test_outside_markers_is_byte_identical(tmp_path):
    readme, results = _setup(tmp_path)
    render.render_numbers(results, readme)
    data = readme.read_bytes()
    assert data.startswith((BEFORE + START).encode())
    assert data.endswith((END + AFTER).encode())


def test_block_is_replaced_with_numbers(tmp_path):
    readme, results = _setup(tmp_path)
    render.render_numbers(results, readme)
    text = readme.read_bytes().decode()
    block = text.split(START)[1].split(END)[0]
    assert "old content" not in block
    for expected in ("5", "8", "100%"):
        assert expected in block
    assert "false positive" in block.lower()


def test_idempotent(tmp_path):
    readme, results = _setup(tmp_path)
    render.render_numbers(results, readme)
    first = readme.read_bytes()
    render.render_numbers(results, readme)
    assert readme.read_bytes() == first


def test_crlf_inside_block_is_kept(tmp_path):
    readme, results = _setup(tmp_path, middle="\r\nold\r\n")
    render.render_numbers(results, readme)
    block = readme.read_bytes().decode().split(START)[1].split(END)[0]
    assert "\n" not in block.replace("\r\n", "")


@pytest.mark.parametrize("missing", [START, END])
def test_missing_marker_fails_naming_it(tmp_path, missing):
    readme, results = _setup(tmp_path)
    original = readme.read_bytes().replace(missing.encode(), b"")
    readme.write_bytes(original)
    with pytest.raises(ValueError) as err:
        render.render_numbers(results, readme)
    assert missing in str(err.value)
    assert readme.read_bytes() == original


@pytest.mark.parametrize("dup", [START, END])
def test_duplicated_marker_fails(tmp_path, dup):
    readme, results = _setup(tmp_path)
    original = readme.read_bytes() + b"\n" + dup.encode()
    readme.write_bytes(original)
    with pytest.raises(ValueError) as err:
        render.render_numbers(results, readme)
    assert dup in str(err.value)
    assert readme.read_bytes() == original


def test_wrong_order_fails(tmp_path):
    readme, results = _setup(tmp_path)
    readme.write_bytes(f"a\n{END}\nb\n{START}\nc".encode())
    with pytest.raises(ValueError, match="order"):
        render.render_numbers(results, readme)
