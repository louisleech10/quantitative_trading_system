from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from api.routes import export as export_route


class _StubExportService:
    def export_file(self, model_task_id, format, scope):
        if model_task_id == "missing":
            raise ValueError("任務不存在或無可匯出資料")
        content = f"scope={scope.value},format={format.value}".encode("utf-8")
        file_name = f"{model_task_id}_{scope.value}.txt"
        return content, file_name, "text/plain"

    def preview(self, model_task_id, format, scope):
        if model_task_id == "missing":
            raise ValueError("任務不存在或無可匯出資料")
        return f"preview:{scope.value}:{format.value}", f"{model_task_id}_{scope.value}.txt"


def test_export_download_success(monkeypatch):
    monkeypatch.setattr(export_route, "get_export_service", lambda: _StubExportService())
    client = TestClient(app)

    response = client.get("/api/v1/export/task-1", params={"format": "csv", "scope": "full"})

    assert response.status_code == 200
    assert "attachment;" in response.headers.get("content-disposition", "")


def test_export_preview_success(monkeypatch):
    monkeypatch.setattr(export_route, "get_export_service", lambda: _StubExportService())
    client = TestClient(app)

    response = client.get("/api/v1/export/task-1/preview", params={"format": "json", "scope": "performance"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_task_id"] == "task-1"
    assert payload["scope"] == "performance"


def test_export_missing_task_returns_404(monkeypatch):
    monkeypatch.setattr(export_route, "get_export_service", lambda: _StubExportService())
    client = TestClient(app)

    response = client.get("/api/v1/export/missing", params={"format": "json", "scope": "full"})

    assert response.status_code == 404


def test_export_invalid_format_returns_422(monkeypatch):
    monkeypatch.setattr(export_route, "get_export_service", lambda: _StubExportService())
    client = TestClient(app)

    response = client.get("/api/v1/export/task-1", params={"format": "xml", "scope": "full"})

    assert response.status_code == 422


def test_export_invalid_scope_returns_422(monkeypatch):
    monkeypatch.setattr(export_route, "get_export_service", lambda: _StubExportService())
    client = TestClient(app)

    response = client.get("/api/v1/export/task-1", params={"format": "json", "scope": "unknown"})

    assert response.status_code == 422
