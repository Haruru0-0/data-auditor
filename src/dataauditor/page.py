from datetime import datetime
from importlib import resources

from dataauditor.audit import FileReport
from dataauditor.report import to_json

PLACEHOLDER = "__AUDIT_DATA__"

_ESCAPES = {ch: chr(92) + "u%04x" % ord(ch) for ch in "<>&" + chr(0x2028) + chr(0x2029)}


def _load_template() -> str:
    path = resources.files("dataauditor") / "static" / "report.html"
    return path.read_text(encoding="utf-8")


def _script_safe(text: str) -> str:
    return text.translate(str.maketrans(_ESCAPES))


def render_html(reports: list[FileReport], generated_at: datetime) -> str:
    """Return the report page with the audit JSON embedded. Write it as UTF-8."""
    template = _load_template()
    found = template.count(PLACEHOLDER)
    if found != 1:
        raise RuntimeError(f"report template must contain {PLACEHOLDER} exactly once, found {found}")
    return template.replace(PLACEHOLDER, _script_safe(to_json(reports, generated_at)))
