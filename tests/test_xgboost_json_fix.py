"""
XGBoost Batch 任務狀態端點 - JSON 序列化修復驗證（TestClient 版，不需 run_api.py）

回歸情境：批量分析任務結果含 numpy.int64／float64／ndarray／NaN／Inf，
輪詢端點（/pattern-analysis/xgboost/batch/task/{id}、/pattern-analysis/batch/task/{id}）
必須回 200 且 body 為合法 JSON、數值為原生型別（舊 bug：numpy.int64 無法序列化 ⇒ 前端輪詢無限迴圈）。

batch service 以替身取代（不重訓），任務結果直接塞入 numpy 型別。
"""

from __future__ import annotations

import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import pattern_analysis as pa_route

TASK_ID = "task-json-fix"


class _FakeBatchService:
    def __init__(self, task):
        self._task = task

    def get_task_status(self, task_id):
        return self._task if task_id == TASK_ID else None


def _numpy_task():
    return {
        "task_id": TASK_ID,
        "status": "completed",
        "progress": np.float64(100.0),
        "current_step": "done",
        "result": {
            "total_cases": np.int64(120),
            "valid_cases": np.int64(100),
            "positive_cases": np.int64(60),
            "negative_cases": np.int64(40),
            "features_generated": np.int32(35),
            "feature_ids": np.array([1, 2, 3], dtype=np.int64),
            "model_performance": {
                "train_auc_score": np.float64(0.91),
                "cv_auc_mean": np.float32(0.75),
            },
        },
    }


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(pa_route, "get_xgboost_batch_service", lambda: _FakeBatchService(_numpy_task()))
    return TestClient(app)


@pytest.mark.xfail(
    strict=True,
    reason="生產缺陷：convert_numpy_types 對 np.float64 的 NaN/Inf 直接 float() 回傳而未轉 None（json_serializer.py:23-24），端點 500；見 白話說明/還沒做的事.md",
)
@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_batch_xgboost_json_numpy_nan_inf_become_null(monkeypatch, bad):
    """np.float64 的 NaN／Inf（如 CV AUC 算不出）經端點後應為 null，而非 500。"""
    task = _numpy_task()
    task["result"]["model_performance"]["cv_auc_bad"] = np.float64(bad)
    monkeypatch.setattr(pa_route, "get_xgboost_batch_service", lambda: _FakeBatchService(task))
    resp = TestClient(app).get(f"/api/v1/pattern-analysis/xgboost/batch/task/{TASK_ID}")
    assert resp.status_code == 200
    assert resp.json()["result"]["model_performance"]["cv_auc_bad"] is None


@pytest.mark.parametrize(
    "path",
    [
        f"/api/v1/pattern-analysis/xgboost/batch/task/{TASK_ID}",
        f"/api/v1/pattern-analysis/batch/task/{TASK_ID}",
    ],
)
def test_batch_xgboost_json(client, path):
    """含 numpy 型別／NaN／Inf 之任務結果經端點後為合法 JSON 且數值守恆。"""
    resp = client.get(path)
    assert resp.status_code == 200
    # 嚴格 JSON（不允許 NaN／Infinity 字面值）
    body = json.loads(resp.text, parse_constant=lambda c: pytest.fail(f"非法 JSON 常數 {c}"))

    assert body["status"] == "completed"
    assert body["progress"] == 100.0
    result = body["result"]
    assert result["total_cases"] == 120
    assert result["valid_cases"] == 100
    assert result["positive_cases"] == 60
    assert result["negative_cases"] == 40
    assert result["positive_cases"] + result["negative_cases"] == result["valid_cases"]
    assert result["features_generated"] == 35
    assert result["feature_ids"] == [1, 2, 3]
    perf = result["model_performance"]
    assert perf["train_auc_score"] == pytest.approx(0.91)
    assert perf["cv_auc_mean"] == pytest.approx(0.75)


def test_batch_xgboost_task_not_found(client):
    """不存在之任務回 404。"""
    assert client.get("/api/v1/pattern-analysis/xgboost/batch/task/nonexistent").status_code == 404
    assert client.get("/api/v1/pattern-analysis/batch/task/nonexistent").status_code == 404
