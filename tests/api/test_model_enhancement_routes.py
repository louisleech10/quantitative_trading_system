from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from api.models.model_enhancement import FullEnhancementResponse, ModelEnhancementResponse
from api.routes import model_enhancement


class _StubService:
    async def execute_calibration(self, request):
        return ModelEnhancementResponse(
            task_id="task-cal",
            status="running",
            module="calibration",
            created_at="2026-02-18T00:00:00",
        )

    async def execute_walk_forward(self, request):
        return ModelEnhancementResponse(
            task_id="task-wf",
            status="running",
            module="walk_forward",
            created_at="2026-02-18T00:00:00",
        )

    async def execute_sample_weights(self, request):
        return ModelEnhancementResponse(
            task_id="task-sw",
            status="running",
            module="sample_weight",
            created_at="2026-02-18T00:00:00",
        )

    async def execute_adversarial(self, request):
        return ModelEnhancementResponse(
            task_id="task-av",
            status="running",
            module="adversarial",
            created_at="2026-02-18T00:00:00",
        )

    async def execute_cpcv(self, request):
        return ModelEnhancementResponse(
            task_id="task-cpcv",
            status="running",
            module="cpcv",
            created_at="2026-02-18T00:00:00",
        )

    async def execute_learning_curve(self, request):
        return ModelEnhancementResponse(
            task_id="task-lc",
            status="running",
            module="learning_curve",
            created_at="2026-02-18T00:00:00",
        )

    async def execute_full_enhancement(self, request):
        return FullEnhancementResponse(
            task_id="task-full",
            status="completed",
            modules={
                "calibration": ModelEnhancementResponse(
                    task_id="task-cal",
                    status="completed",
                    module="calibration",
                    created_at="2026-02-18T00:00:00",
                )
            },
            total_execution_time_seconds=1.5,
        )

    def get_task_status(self, task_id: str):
        if task_id == "missing":
            return None
        return ModelEnhancementResponse(
            task_id=task_id,
            status="completed",
            module="calibration",
            created_at="2026-02-18T00:00:00",
        )


def test_model_enhancement_routes(monkeypatch):
    monkeypatch.setattr(model_enhancement, "get_model_enhancement_service", lambda: _StubService())
    client = TestClient(app)

    base_payload = {"model_task_id": "task-1"}

    assert client.post("/api/v1/model-enhancement/calibrate", json=base_payload).status_code == 200
    assert client.post("/api/v1/model-enhancement/walk-forward", json=base_payload).status_code == 200
    assert client.post("/api/v1/model-enhancement/sample-weights", json=base_payload).status_code == 200
    assert client.post("/api/v1/model-enhancement/adversarial-validate", json=base_payload).status_code == 200
    assert client.post("/api/v1/model-enhancement/cpcv", json=base_payload).status_code == 200
    assert client.post("/api/v1/model-enhancement/learning-curve", json=base_payload).status_code == 200
    assert client.post("/api/v1/model-enhancement/full-enhancement", json=base_payload).status_code == 200
    assert client.get("/api/v1/model-enhancement/task/task-cal").status_code == 200


def test_model_enhancement_task_not_found(monkeypatch):
    monkeypatch.setattr(model_enhancement, "get_model_enhancement_service", lambda: _StubService())
    client = TestClient(app)

    response = client.get("/api/v1/model-enhancement/task/missing")
    assert response.status_code == 404


def test_model_enhancement_request_validation(monkeypatch):
    monkeypatch.setattr(model_enhancement, "get_model_enhancement_service", lambda: _StubService())
    client = TestClient(app)

    invalid = client.post(
        "/api/v1/model-enhancement/calibrate",
        json={"model_task_id": "task-1", "method": "invalid", "cv": 1},
    )
    assert invalid.status_code == 422
