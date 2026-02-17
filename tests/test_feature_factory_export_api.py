"""Feature Factory export API tests (Phase 3.2)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.feature_factory import router as feature_factory_router
from api.services.feature_factory_service import feature_factory_service


app = FastAPI()
app.include_router(feature_factory_router)
client = TestClient(app)


def test_export_csv_stream_success(monkeypatch):
    """CSV 串流端點：成功回傳 + headers。"""

    def fake_export_csv_stream(task_id, columns, max_rows, include_metadata_header):
        assert task_id == "task-123"
        assert columns == ["a", "b"]
        assert max_rows == 10
        assert include_metadata_header is True

        def generator():
            yield "# task_id: task-123\n"
            yield "timestamp,a,b\n"
            yield "2026-01-01,1,2\n"

        return {
            "generator": generator(),
            "filename": "BTCUSDT_12h_features_task-123.csv",
            "feature_count": 2,
            "row_count": 1,
        }

    monkeypatch.setattr(feature_factory_service, "export_csv_stream", fake_export_csv_stream)

    response = client.get(
        "/api/v1/features/export/task-123/csv",
        params={
            "columns": "a,b",
            "max_rows": 10,
            "include_metadata_header": True,
        },
    )

    assert response.status_code == 200
    assert "attachment; filename=BTCUSDT_12h_features_task-123.csv" in response.headers.get(
        "content-disposition", ""
    )
    assert response.headers.get("x-export-task-id") == "task-123"
    assert "timestamp,a,b" in response.text


def test_export_csv_not_found(monkeypatch):
    """CSV 串流端點：task_id 不存在回傳 404。"""

    def fake_export_csv_stream(*args, **kwargs):
        raise FileNotFoundError("Result not found")

    monkeypatch.setattr(feature_factory_service, "export_csv_stream", fake_export_csv_stream)

    response = client.get("/api/v1/features/export/missing/csv")
    assert response.status_code == 404


def test_export_csv_invalid_columns(monkeypatch):
    """CSV 串流端點：無效欄位回傳 400。"""

    def fake_export_csv_stream(*args, **kwargs):
        raise ValueError("Invalid columns")

    monkeypatch.setattr(feature_factory_service, "export_csv_stream", fake_export_csv_stream)

    response = client.get("/api/v1/features/export/task-1/csv", params={"columns": "bad_col"})
    assert response.status_code == 400


def test_export_json_success(monkeypatch):
    """JSON 匯出端點：回傳符合主結構。"""

    def fake_export_json_report(**kwargs):
        return {
            "version": "1.0",
            "type": "feature_factory_report",
            "metadata": {"task_id": "task-1"},
            "feature_catalog": {"by_category": {}, "by_level": {}, "by_layer": {}},
            "statistics": {"summary": {}, "per_feature": []},
            "sample_data": {"columns": [], "rows": []},
            "quality_alerts": [],
            "correlation_hotspots": [],
        }

    monkeypatch.setattr(feature_factory_service, "export_json_report", fake_export_json_report)

    response = client.get("/api/v1/features/export/task-1/json")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "feature_factory_report"
    assert "feature_catalog" in data
    assert "statistics" in data


def test_export_markdown_success(monkeypatch):
    """Markdown 匯出端點：Content-Type 為 text/markdown。"""

    def fake_export_markdown_report(**kwargs):
        return "# Report\n\nHello"

    monkeypatch.setattr(feature_factory_service, "export_markdown_report", fake_export_markdown_report)

    response = client.get("/api/v1/features/export/task-1/markdown")
    assert response.status_code == 200
    assert "text/markdown" in response.headers.get("content-type", "")
    assert "# Report" in response.text
