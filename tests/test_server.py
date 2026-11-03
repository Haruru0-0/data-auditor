import json

import pytest
from fastapi.testclient import TestClient

from dataauditor.server import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def _upload(client, name, content, ctype="text/csv"):
    return client.post("/api/audit", files={"file": (name, content, ctype)})


def test_csv_upload_returns_the_audit_json(client):
    csv = "id,score\n" + "".join(f"{i},{i}\n" for i in range(1, 11)) + "11,\n12,\n"
    response = _upload(client, "data.csv", csv)
    assert response.status_code == 200
    body = response.json()
    entry = body["files"][0]
    assert entry["path"] == "data.csv"
    assert entry["rows"] == 12
    assert any(f["check"] == "missing" for f in entry["findings"])
    assert isinstance(entry["score"], int) and 0 <= entry["score"] <= 100
    assert entry["profile"]["id"]["max"] == 12
    assert set(body["totals"]) == {"error", "warning", "info"}


def test_reported_name_is_the_base_name_only(client):
    response = _upload(client, "../../etc/evil.csv", "a\n1\n")
    assert response.status_code == 200
    assert response.json()["files"][0]["path"] == "evil.csv"


def test_name_with_glob_characters_is_read_correctly(client):
    response = _upload(client, "sales[2024]*.csv", "a,b\n1,2\n")
    entry = response.json()["files"][0]
    assert entry["path"] == "sales[2024]*.csv"
    assert entry["rows"] == 1
    assert not any(f["check"] == "read" for f in entry["findings"])


def test_empty_file_is_a_read_error_not_a_server_error(client):
    response = _upload(client, "empty.csv", "")
    assert response.status_code == 200
    findings = response.json()["files"][0]["findings"]
    assert findings[0]["check"] == "read" and findings[0]["severity"] == "error"


def test_unsupported_extension_is_rejected(client):
    response = _upload(client, "notes.txt", "hello", "text/plain")
    assert response.status_code == 400
    assert ".csv" in response.json()["detail"]


def test_oversized_upload_is_rejected():
    small = TestClient(create_app(max_bytes=10))
    response = _upload(small, "big.csv", "a,b\n" + "1,2\n" * 50)
    assert response.status_code == 413


def test_missing_file_field_is_a_validation_error(client):
    assert client.post("/api/audit").status_code == 422


def test_parquet_upload_works(client, tmp_path, con):
    path = tmp_path / "t.parquet"
    con.execute(f"COPY (SELECT 1 AS x, 'a' AS y) TO '{path.as_posix()}' (FORMAT parquet)")
    response = _upload(client, "t.parquet", path.read_bytes(), "application/octet-stream")
    assert response.status_code == 200
    assert response.json()["files"][0]["rows"] == 1


def test_serves_the_built_web_app_when_given_a_directory(tmp_path):
    (tmp_path / "index.html").write_text("<html>app</html>", encoding="utf-8")
    served = TestClient(create_app(web_dir=tmp_path))
    assert "app" in served.get("/").text
    assert served.get("/api/health").json() == {"status": "ok"}
