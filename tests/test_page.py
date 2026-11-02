import json
import re
from datetime import datetime, timezone

import pytest

from dataauditor import page
from dataauditor.audit import FileReport
from dataauditor.findings import Finding
from dataauditor.report import to_json

NOW = datetime(2026, 11, 2, 9, 30, 5, tzinfo=timezone.utc)
BLOCK = re.compile(r'<script id="audit-data" type="application/json">(.*?)</script>', re.S)


def clean():
    return [FileReport("data/a.csv", 3, {"x": "BIGINT"},
                       [Finding("missing", "error", "x", "3 missing", 3, ("e1",))])]


def with_message(msg, **kw):
    return [FileReport(kw.get("path", "a.csv"), 1, {"x": "BIGINT"},
                       [Finding("missing", "error", "x", msg, 1, ("e",))])]


def embedded(html):
    return json.loads(BLOCK.search(html).group(1))


def test_embeds_path_and_json_round_trips():
    html = page.render_html(clean(), NOW)
    assert "data/a.csv" in html
    assert embedded(html) == json.loads(to_json(clean(), NOW))


def test_hostile_strings_are_neutralised():
    reports = [FileReport(
        "<img src=x onerror=alert(1)>.csv", 1, {"<img src=x onerror=alert(1)>": "BIGINT"},
        [Finding("<b>chk", "<b>sev", "<img src=x onerror=alert(1)>",
                 "</script><script>alert(1)</script>", 1, ("<!-- <script>",))])]
    # severity is only counted in totals, so keep to_json happy
    html = page.render_html(reports, NOW)
    empty = page.render_html([], NOW)
    for raw in ["<img src=x", "<b>chk", "<b>sev", "<!-- <script>", "alert(1)</script>",
                "</script><script>"]:
        assert raw not in html
    assert html.count("</script>") == empty.count("</script>")
    assert embedded(html) == json.loads(to_json(reports, NOW))
    f = embedded(html)["files"][0]
    assert f["findings"][0]["message"] == "</script><script>alert(1)</script>"
    assert f["findings"][0]["examples"] == ["<!-- <script>"]
    assert f["findings"][0]["check"] == "<b>chk"
    assert f["findings"][0]["severity"] == "<b>sev"


def test_line_separators_round_trip():
    msg = "a" + chr(0x2028) + "b" + chr(0x2029) + "c"
    html = page.render_html(with_message(msg), NOW)
    assert chr(0x2028) not in html and chr(0x2029) not in html
    assert embedded(html)["files"][0]["findings"][0]["message"] == msg


def test_backslash_sequences_are_literal():
    bs = chr(92)
    msg = bs + "g<0> and " + bs + "1 and " + bs + bs + " and " + bs + "u0041"
    html = page.render_html(with_message(msg), NOW)
    assert embedded(html)["files"][0]["findings"][0]["message"] == msg


def test_empty_list():
    html = page.render_html([], NOW)
    assert '"files": []' in html
    assert embedded(html)["files"] == []


def test_deterministic():
    assert page.render_html(clean(), NOW) == page.render_html(clean(), NOW)


@pytest.mark.parametrize("template", ["<html>no placeholder</html>",
                                      "__AUDIT_DATA__ and __AUDIT_DATA__"])
def test_placeholder_must_appear_exactly_once(monkeypatch, template):
    monkeypatch.setattr(page, "_load_template", lambda: template)
    with pytest.raises(RuntimeError):
        page.render_html([], NOW)


ALLOWED = [
    "https://react.dev/errors/",
    "http://www.w3.org/1999/xhtml",
    "http://www.w3.org/1998/Math/MathML",
    "http://www.w3.org/2000/svg",
    "http://www.w3.org/1999/xlink",
    "http://www.w3.org/XML/1998/namespace",
]


URL_ALLOWED = "startsWith(`url(`)"


def test_clean_render_is_self_contained():
    html = page.render_html(clean(), NOW)
    for bad in ["<link", "@import", "@font-face"]:
        assert bad not in html
    # framer-motion's JS source has one string literal "url(" (a startsWith test); every copy of exactly that literal is stripped
    assert "url(" not in html.replace(URL_ALLOWED, "")
    markup = re.sub(r"<(script|style)\b([^>]*)>.*?</\1>", r"<\1\2></\1>", html, flags=re.S)
    for attr in (r"\ssrc\s*=", r"\shref\s*="):
        assert not re.search(attr, markup, re.I)
    rest = html
    for ok in ALLOWED:
        rest = rest.replace(ok, "")
    assert "http://" not in rest and "https://" not in rest


def test_template_found_via_package_resource(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert '"files"' in page.render_html(clean(), NOW)
