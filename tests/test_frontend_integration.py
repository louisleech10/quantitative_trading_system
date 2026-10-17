"""
前端整合測試 - Phase 3-6 Frontend Integration（TestClient 版，不需 run_api.py）

測試項目:
1. Trial Comparison API (/api/v1/optimization/trials/compare)
2. ML Pipeline Creation API (/api/v1/ml-pipeline/create) 單一／多指標
3. ML Pipeline List/Detail APIs

以 FastAPI TestClient 在行程內呼叫路由；Optuna study 與 MLPipelineConfig 以替身隔離，
pipeline 落盤目錄指向 tmp_path。原版為打 localhost:8000 之 print 腳本（無任何斷言）。
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import ml_pipeline as ml_route
from api.routes import optimization as opt_route

TEST_STUDY_NAME = "momentum_optimization_001"


class _FakeFEC:
    def __init__(self, indicators):
        self.indicators = indicators
        self.all_feature_names = [f"{i.indicator_type}_f" for i in indicators]


class _FakePipelineConfig:
    def __init__(self, kwargs, indicators):
        self.kwargs = kwargs
        self.feature_engineering_config = _FakeFEC(indicators)

    def to_dict(self):
        return {
            "study_name": self.kwargs["study_name"],
            "trial_number": self.kwargs["trial_number"],
            "strategy_type": self.kwargs["strategy_type"],
            "user_notes": self.kwargs["user_notes"],
            "selected_by": self.kwargs["selected_by"],
            "use_xgboost_tuning": self.kwargs["use_xgboost_tuning"],
            "feature_engineering_config": {
                "all_feature_names": self.feature_engineering_config.all_feature_names
            },
        }


class _FakeMLPipelineConfig:
    calls: list = []

    @classmethod
    def from_user_selection(cls, **kwargs):
        cls.calls.append(kwargs)
        indicators = kwargs.get("indicators")
        if indicators is None:
            # 單一指標模式：繼承 trial 參數（替身給一個固定指標）
            indicators = [
                SimpleNamespace(
                    indicator_type="ema_three_line",
                    data_source="close",
                    params={"short_period": 5},
                )
            ]
        return _FakePipelineConfig(kwargs, indicators)


@pytest.fixture
def client(tmp_path, monkeypatch):
    _FakeMLPipelineConfig.calls = []
    monkeypatch.setattr(ml_route, "MLPipelineConfig", _FakeMLPipelineConfig)
    monkeypatch.setattr(ml_route, "PIPELINE_STORAGE_PATH", tmp_path)
    return TestClient(app)


def _single_payload(trial_number: int = 5) -> dict:
    return {
        "study_name": TEST_STUDY_NAME,
        "trial_number": trial_number,
        "strategy_type": "ema_three_line",
        "pipeline_name": f"EMA Test Pipeline (Trial {trial_number})",
        "user_notes": "這是一個測試用的 Pipeline，用於驗證單一指標模式是否正常運作。",
        "selected_by": "test_script",
        "use_xgboost_tuning": True,
        "indicators": None,
    }


def test_trial_comparison(monkeypatch):
    """Trial 比較端點：回應欄位由 compare_trials 結果逐欄映射；壞輸入回 400；study 不存在回 404。"""
    seen = {}

    def _fake_compare(study_name, trial_numbers):
        seen["study_name"] = study_name
        seen["trial_numbers"] = trial_numbers
        trials = [
            SimpleNamespace(
                number=n,
                value=0.1 * n,
                state="COMPLETE",
                duration_seconds=1.5,
                params={"short_period": n},
                user_attrs={},
            )
            for n in trial_numbers
        ]
        return SimpleNamespace(
            best_trial_number=10,
            best_value=1.0,
            value_mean=0.42,
            value_std=0.3,
            value_min=0.1,
            value_max=1.0,
            trials=trials,
            recommendation="選 trial 10",
        )

    monkeypatch.setattr(opt_route, "compare_trials", _fake_compare)
    client = TestClient(app)

    resp = client.get(
        "/api/v1/optimization/trials/compare",
        params={"study_name": TEST_STUDY_NAME, "trial_numbers": "1,2,3,5,10"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert seen == {"study_name": TEST_STUDY_NAME, "trial_numbers": [1, 2, 3, 5, 10]}
    data = body["data"]
    assert data["best_trial_number"] == 10
    assert data["best_value"] == 1.0
    assert data["value_mean"] == 0.42
    assert data["value_std"] == 0.3
    assert data["recommendation"] == "選 trial 10"
    assert [t["number"] for t in data["trials"]] == [1, 2, 3, 5, 10]
    assert data["trials"][1]["params"] == {"short_period": 2}

    # study 不存在 ⇒ 404
    def _raise_fnf(study_name, trial_numbers):
        raise FileNotFoundError("no such study")

    monkeypatch.setattr(opt_route, "compare_trials", _raise_fnf)
    missing = client.get(
        "/api/v1/optimization/trials/compare",
        params={"study_name": "nope", "trial_numbers": "1,2"},
    )
    assert missing.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason="生產缺陷：compare_optimization_trials 內 raise HTTPException(400) 被外層 except Exception 吞成 500（optimization.py:437-520）；見 白話說明/還沒做的事.md",
)
@pytest.mark.parametrize("trial_numbers", ["a,b", "1"])
def test_trial_comparison_bad_input_is_400(trial_numbers):
    """非整數、少於 2 個 trial 應回 400（用戶輸入錯誤）。"""
    resp = TestClient(app).get(
        "/api/v1/optimization/trials/compare",
        params={"study_name": TEST_STUDY_NAME, "trial_numbers": trial_numbers},
    )
    assert resp.status_code == 400


def test_create_single_indicator_pipeline(client, tmp_path):
    """單一指標（indicators=None）走 single_indicator 模式，且 trial 參數原樣交給 MLPipelineConfig 並落盤。"""
    resp = client.post("/api/v1/ml-pipeline/create", json=_single_payload(5))
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    summary = data["pipeline_summary"]
    assert summary["mode"] == "single_indicator"
    assert summary["trial_number"] == 5
    assert summary["study_name"] == TEST_STUDY_NAME
    assert summary["feature_count"] == 1
    assert len(summary["indicators"]) == 1
    assert data["pipeline_id"].startswith(f"pipeline_{TEST_STUDY_NAME}_trial5_")

    assert len(_FakeMLPipelineConfig.calls) == 1
    kw = _FakeMLPipelineConfig.calls[0]
    assert kw["trial_number"] == 5
    assert kw["use_xgboost_tuning"] is True
    assert "indicators" not in kw

    saved = tmp_path / f"{data['pipeline_id']}.json"
    assert saved.exists()
    assert json.loads(saved.read_text(encoding="utf-8"))["trial_number"] == 5


def test_create_multi_indicator_pipeline(client, tmp_path):
    """多指標（EMA+RSI+MACD）走 multi_indicator 模式：請求之指標型別／來源／參數逐項轉成 IndicatorConfig。"""
    payload = _single_payload(5)
    payload["use_xgboost_tuning"] = False
    payload["indicators"] = [
        {
            "indicator_type": "ema_three_line",
            "params": {"short_period": 5, "mid_period": 20, "long_period": 60, "volume_threshold": 1000000},
            "data_source": "close",
        },
        {"indicator_type": "rsi", "params": {"period": 14, "overbought": 70, "oversold": 30}, "data_source": "close"},
        {"indicator_type": "macd", "params": {"fast_period": 12, "slow_period": 26, "signal_period": 9}, "data_source": "close"},
    ]
    resp = client.post("/api/v1/ml-pipeline/create", json=payload)
    assert resp.status_code == 200
    summary = resp.json()["pipeline_summary"]
    assert summary["mode"] == "multi_indicator"
    assert summary["use_xgboost_tuning"] is False
    assert [i["type"] for i in summary["indicators"]] == ["ema_three_line", "rsi", "macd"]
    assert [i["data_source"] for i in summary["indicators"]] == ["close", "close", "close"]
    assert summary["indicators"][1]["params"] == {"period": 14, "overbought": 70, "oversold": 30}
    assert summary["feature_count"] == 3

    kw = _FakeMLPipelineConfig.calls[0]
    assert [c.indicator_type for c in kw["indicators"]] == ["ema_three_line", "rsi", "macd"]


def test_get_pipeline_detail(client, tmp_path):
    """建立後以 pipeline_id 查詳情：內容等於落盤 JSON；不存在回 404。"""
    created = client.post("/api/v1/ml-pipeline/create", json=_single_payload(7)).json()
    pipeline_id = created["pipeline_id"]

    resp = client.get(f"/api/v1/ml-pipeline/{pipeline_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["trial_number"] == 7
    assert body["data"] == json.loads((tmp_path / f"{pipeline_id}.json").read_text(encoding="utf-8"))

    assert client.get("/api/v1/ml-pipeline/pipeline_does_not_exist").status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason="生產缺陷：GET /ml-pipeline/list 被先註冊之 /{pipeline_id} 遮蔽（回 404 'list' not found）；見 白話說明/還沒做的事.md",
)
def test_list_pipelines(client):
    """列表端點：建兩筆後 total=2 且摘要含 pipeline_id／trial_number／feature_count。"""
    client.post("/api/v1/ml-pipeline/create", json=_single_payload(1))
    client.post("/api/v1/ml-pipeline/create", json=_single_payload(2))

    resp = client.get("/api/v1/ml-pipeline/list", params={"limit": 10, "offset": 0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert sorted(p["trial_number"] for p in body["data"]) == [1, 2]
    assert all(p["feature_count"] == 1 for p in body["data"])
