"""
Feature Factory API Tests
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.feature_factory import router as feature_factory_router


app = FastAPI()
app.include_router(feature_factory_router)
client = TestClient(app)


def test_feature_factory_preview():
    """測試 Feature Factory preview 端點"""
    response = client.post("/api/v1/features/preview", json={})
    assert response.status_code == 200
    data = response.json()
    assert "total_features" in data
    assert "estimated_time_seconds" in data
    assert "memory_mb" in data
    assert "breakdown" in data


def test_feature_factory_generate():
    """測試 Feature Factory generate 端點"""
    response = client.post(
        "/api/v1/features/generate",
        json={"symbol": "BTCUSDT", "timeframe": "12h"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "running"


def test_feature_factory_task_not_found():
    """測試不存在的任務查詢"""
    response = client.get("/api/v1/features/task/nonexistent_task")
    assert response.status_code == 404
