from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

existing_api = sys.modules.get("api")
existing_api_file = getattr(existing_api, "__file__", "") if existing_api is not None else ""
if existing_api is not None and (not existing_api_file or not existing_api_file.startswith(str(PROJECT_ROOT))):
    sys.modules.pop("api", None)
    for module_name in list(sys.modules.keys()):
        if module_name.startswith("api."):
            sys.modules.pop(module_name, None)

from fastapi.testclient import TestClient

from api.main import app
from api.routes import pattern_analysis


class _StubModelTaskService:
    def __init__(self, task_payload):
        self._task_payload = task_payload

    async def start_training_task(self, engine, config, data_source, validation, run_comparison):
        return "task-test-001"

    def get_task_status(self, task_id):
        return self._task_payload


def test_model_train_invalid_engine_returns_422():
    client = TestClient(app)

    response = client.post(
        "/api/v1/pattern-analysis/model/train",
        json={
            "engine": "unknown",
            "features_source": "dummy_case",
        },
    )

    assert response.status_code == 422


def test_model_train_start_and_get_performance(monkeypatch):
    stub_service = _StubModelTaskService(
        {
            "task_id": "task-test-001",
            "status": "completed",
            "result": {
                "engine": "lightgbm",
                "performance": {
                    "engine_type": "lightgbm",
                    "in_sample_train_auc": 0.81,
                    "cv_auc_mean": 0.79,
                    "cv_auc_std": 0.02,
                    "precision": 0.7,
                    "recall": 0.6,
                    "f1_score": 0.64,
                    "overfitting_score": 0.02,
                },
                "feature_importance": [{"feature_name": "f1", "importance": 0.5, "rank": 1}],
            },
        }
    )
    monkeypatch.setattr(pattern_analysis, "model_task_service", stub_service)

    client = TestClient(app)

    start_response = client.post(
        "/api/v1/pattern-analysis/model/train",
        json={
            "engine": "lightgbm",
            "features_source": "dummy_case",
            "config": {"n_estimators": 10},
            "run_comparison": False,
        },
    )
    assert start_response.status_code == 200
    assert start_response.json()["task_id"] == "task-test-001"

    performance_response = client.get("/api/v1/pattern-analysis/model/task-test-001/performance")
    assert performance_response.status_code == 200
    assert performance_response.json()["engine_type"] == "lightgbm"


def test_model_comparison_and_lightgbm_results(monkeypatch):
    stub_service = _StubModelTaskService(
        {
            "task_id": "task-test-001",
            "status": "completed",
            "result": {
                "engine": "lightgbm",
                "performance": {
                    "engine_type": "lightgbm",
                    "in_sample_train_auc": 0.81,
                    "cv_auc_mean": 0.79,
                    "cv_auc_std": 0.02,
                    "precision": 0.7,
                    "recall": 0.6,
                    "f1_score": 0.64,
                    "overfitting_score": 0.02,
                },
                "feature_importance": [{"feature_name": "f1", "importance": 0.5, "rank": 1}],
                "comparison": {
                    "engine_performances": {
                        "lightgbm": {
                            "engine_type": "lightgbm",
                            "in_sample_train_auc": 0.81,
                            "cv_auc_mean": 0.79,
                            "cv_auc_std": 0.02,
                            "precision": 0.7,
                            "recall": 0.6,
                            "f1_score": 0.64,
                            "overfitting_score": 0.02,
                        },
                        "xgboost": {
                            "engine_type": "xgboost",
                            "in_sample_train_auc": 0.8,
                            "cv_auc_mean": 0.78,
                            "cv_auc_std": 0.02,
                            "precision": 0.69,
                            "recall": 0.59,
                            "f1_score": 0.63,
                            "overfitting_score": 0.02,
                        },
                    },
                    "consensus_rate": 0.9,
                    "feature_rank_correlation": 0.7,
                    "recommended_engine": "lightgbm",
                    "recommendation_reason": "AUC 較高",
                },
            },
        }
    )
    monkeypatch.setattr(pattern_analysis, "model_task_service", stub_service)

    client = TestClient(app)

    comparison_response = client.get("/api/v1/pattern-analysis/model/task-test-001/comparison")
    assert comparison_response.status_code == 200
    assert comparison_response.json()["recommended_engine"] == "lightgbm"

    lightgbm_response = client.get("/api/v1/pattern-analysis/lightgbm/task-test-001/results")
    assert lightgbm_response.status_code == 200
    assert lightgbm_response.json()["task_id"] == "task-test-001"


def test_xgboost_existing_endpoint_still_registered():
    client = TestClient(app)

    response = client.post("/api/v1/pattern-analysis/xgboost/start", json={})

    assert response.status_code != 404
