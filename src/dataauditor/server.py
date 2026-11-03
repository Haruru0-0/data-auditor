"""Web backend: upload one CSV or Parquet file, get the audit JSON back.

Needs the optional `web` dependencies (pip install -e ".[web]").
"""

import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from dataauditor.audit import SUPPORTED, audit_path
from dataauditor.report import to_json

MAX_BYTES = 50 * 1024 * 1024
_CHUNK = 1024 * 1024
_ENVELOPE = 64 * 1024  # multipart framing allowed on top of the file itself


def create_app(web_dir: Path | None = None, max_bytes: int = MAX_BYTES) -> FastAPI:
    app = FastAPI(title="data-auditor", docs_url=None, redoc_url=None)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/audit")
    def audit_upload(file: UploadFile, request: Request) -> Response:
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > max_bytes + _ENVELOPE:
            raise HTTPException(413, f"file is larger than {max_bytes // (1024 * 1024)} MB")
        # Only the base name is kept; the client never chooses where anything is written.
        name = Path((file.filename or "").replace("\\", "/")).name
        suffix = Path(name).suffix.lower()
        if suffix not in SUPPORTED:
            raise HTTPException(400, "only .csv and .parquet files can be audited")
        with tempfile.TemporaryDirectory(prefix="dataauditor-") as tmp:
            # A fixed safe name on disk: characters such as [ * ? in the real
            # name would be read by DuckDB as a glob pattern.
            target = Path(tmp) / f"upload{suffix}"
            written = 0
            with open(target, "wb") as out:
                while chunk := file.file.read(_CHUNK):
                    written += len(chunk)
                    if written > max_bytes:
                        raise HTTPException(413, f"file is larger than {max_bytes // (1024 * 1024)} MB")
                    out.write(chunk)
            reports = audit_path(target)
        for report in reports:
            report.path = name
        body = to_json(reports, datetime.now(UTC))
        return Response(body, media_type="application/json")

    if web_dir is not None:
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
    return app


def _default_web_dir() -> Path | None:
    chosen = os.environ.get("DATAAUDITOR_WEB_DIR")
    path = Path(chosen) if chosen else Path(__file__).resolve().parents[2] / "web" / "dist"
    return path if (path / "index.html").is_file() else None


app = create_app(_default_web_dir())
