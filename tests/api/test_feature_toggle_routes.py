from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from api.models.feature_toggle_models import (
    BatchToggleResponse,
    FeatureToggleDTO,
    FeatureToggleListResponse,
    FeatureToggleResponse,
    FeatureToggleSummary,
)
from api.routes import feature_toggles


class _StubFeatureToggleService:
    def list_toggles(self, difficulty=None):
        summary = FeatureToggleSummary(
            total=23,
            enabled=12,
            by_difficulty={
                "L1": {"total": 4, "enabled": 4},
                "L2": {"total": 10, "enabled": 8},
                "L3": {"total": 9, "enabled": 0},
            },
            estimated_total_seconds=360,
        )
        return FeatureToggleListResponse(
            toggles=[
                FeatureToggleDTO(
                    feature_id="F-001",
                    name="模型訓練",
                    description="核心",
                    difficulty="L1",
                    is_enabled=True,
                    is_locked=True,
                    engine_types=["lightgbm", "xgboost"],
                    dependencies=[],
                    phase="3",
                    module="core",
                    estimated_time="< 5s",
                    tags=[],
                )
            ],
            summary=summary,
            presets=["essential-only", "recommended", "full"],
        )

    def update_toggle(self, feature_id, enabled):
        if feature_id == "UNKNOWN":
            raise ValueError("未知功能 ID")
        return FeatureToggleResponse(
            toggle=FeatureToggleDTO(
                feature_id=feature_id,
                name="模型訓練",
                description="核心",
                difficulty="L1",
                is_enabled=enabled,
                is_locked=False,
                engine_types=["lightgbm", "xgboost"],
                dependencies=[],
                phase="3",
                module="core",
                estimated_time="< 5s",
                tags=[],
            ),
            cascaded=["F-002"] if not enabled else [],
            summary=self.list_toggles().summary,
        )

    def batch_update(self, updates):
        return BatchToggleResponse(
            updated=updates,
            cascaded=["F-008"],
            summary=self.list_toggles().summary,
        )

    def apply_preset(self, preset_name):
        if preset_name == "unknown":
            raise ValueError("未知 preset")
        return self.list_toggles()


def test_get_feature_toggles(monkeypatch):
    monkeypatch.setattr(feature_toggles, "get_feature_toggle_service", lambda: _StubFeatureToggleService())
    client = TestClient(app)

    response = client.get("/api/v1/feature-toggles")
    assert response.status_code == 200
    assert response.json()["summary"]["total"] == 23


def test_update_feature_toggle(monkeypatch):
    monkeypatch.setattr(feature_toggles, "get_feature_toggle_service", lambda: _StubFeatureToggleService())
    client = TestClient(app)

    response = client.put("/api/v1/feature-toggles/F-005", json={"enabled": False})
    assert response.status_code == 200
    assert response.json()["toggle"]["is_enabled"] is False


def test_batch_update_feature_toggles(monkeypatch):
    monkeypatch.setattr(feature_toggles, "get_feature_toggle_service", lambda: _StubFeatureToggleService())
    client = TestClient(app)

    response = client.put(
        "/api/v1/feature-toggles/batch",
        json={"updates": {"F-005": False, "F-007": True}},
    )
    assert response.status_code == 200
    assert response.json()["updated"]["F-005"] is False


def test_apply_preset(monkeypatch):
    monkeypatch.setattr(feature_toggles, "get_feature_toggle_service", lambda: _StubFeatureToggleService())
    client = TestClient(app)

    response = client.post("/api/v1/feature-toggles/presets/recommended")
    assert response.status_code == 200
    assert "toggles" in response.json()


def test_unknown_feature_returns_400(monkeypatch):
    monkeypatch.setattr(feature_toggles, "get_feature_toggle_service", lambda: _StubFeatureToggleService())
    client = TestClient(app)

    response = client.put("/api/v1/feature-toggles/UNKNOWN", json={"enabled": True})
    assert response.status_code == 400


def test_unknown_preset_returns_400(monkeypatch):
    monkeypatch.setattr(feature_toggles, "get_feature_toggle_service", lambda: _StubFeatureToggleService())
    client = TestClient(app)

    response = client.post("/api/v1/feature-toggles/presets/unknown")
    assert response.status_code == 400


def test_request_validation_returns_422(monkeypatch):
    monkeypatch.setattr(feature_toggles, "get_feature_toggle_service", lambda: _StubFeatureToggleService())
    client = TestClient(app)

    response = client.put("/api/v1/feature-toggles/F-005", json={})
    assert response.status_code == 422
