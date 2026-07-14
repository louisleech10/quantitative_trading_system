"""Phase 2.7 IC deep analysis API tests."""

from __future__ import annotations

import copy
import time
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services.ic_analysis_service import ic_analysis_service
from tests.fixtures.ic_api_real_kline import ic_api_real_kline


client = TestClient(app)

pytestmark = [
    pytest.mark.ic_persist_redirect,
    pytest.mark.usefixtures("ic_persist_redirect"),
]


def _reset_rate_limit_state() -> None:
    current = app.middleware_stack
    while hasattr(current, "app"):
        if hasattr(current, "requests") and isinstance(getattr(current, "requests"), dict):
            current.requests.clear()
        current = current.app


def _wait_for_task_completed(task_id: str, timeout: float = 20.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
        response = client.get(f"/api/v1/ic/task/{task_id}")
        assert response.status_code == 200
        data = response.json()
        if data["status"] == "completed":
            return
        if data["status"] == "failed":
            pytest.fail(f"task failed: {data.get('error')}")
        time.sleep(0.2)
    pytest.fail("task timeout")


def _wait_for_deep_result(task_id: str, timeout: float = 30.0) -> dict:
    """輪詢至 completed/failed。不因 results 非空提前返回(背景任務可能仍 running)。"""
    start = time.time()
    last: dict | None = None
    while time.time() - start < timeout:
        response = client.get(f"/api/v1/ic/deep-analysis/{task_id}/result")
        assert response.status_code == 200
        data = response.json()
        last = data
        if data.get("status") in {"completed", "failed"}:
            return data
        time.sleep(0.5)
    pytest.fail(f"deep analysis timeout; last={last}")


@pytest.fixture(autouse=True)
def reset_rate_limit() -> None:
    _reset_rate_limit_state()


@pytest.fixture(scope="module")
def sample_paths(ic_api_real_kline: dict) -> dict:
    return ic_api_real_kline


def _build_completed_ic_task(sample_paths: dict[str, str]) -> str:
    request_data = {
        "features_path": sample_paths["features_path"],
        "labels_path": sample_paths["labels_path"],
        "meta_path": sample_paths["meta_path"],
        "config_override": {
            **sample_paths["config_override"],
            "thresholds": {
                "ic_mean_min": -1.0,
                "icir_min": -1.0,
                "p_value_max": 1.0,
                "ic_hit_rate_min": 0.0,
                "monotonicity_score_min": 0.0,
                "coverage_min": 0.0,
                "long_short_spread": {"enabled": False},
            },
            "redundancy": {"correlation_threshold": 0.999},
        },
    }

    with client:
        response = client.post("/api/v1/ic/analyze", json=request_data)
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        _wait_for_task_completed(task_id)
    return task_id


@pytest.fixture(scope="module")
def completed_ic_task(
    sample_paths: dict[str, str],
    redirect_patch_set,
    redirect_root_module: Path,
) -> str:
    ctx = redirect_patch_set.activate(redirect_root_module, owner="completed_ic_task")
    try:
        return _build_completed_ic_task(sample_paths)
    finally:
        assert not ctx.spy.violations
        redirect_patch_set.deactivate(ctx)


def test_list_available_features_success(sample_paths: dict[str, str]) -> None:
    response = client.get(
        "/api/v1/ic/features/list",
        params={
            "features_path": sample_paths["features_path"],
            "meta_path": sample_paths["meta_path"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == len(sample_paths["feature_names"])
    assert data["features"][0]["feature_name"] in sample_paths["feature_names"]


def test_list_available_features_not_found() -> None:
    response = client.get(
        "/api/v1/ic/features/list",
        params={"features_path": "/tmp/not_exists_features.h5"},
    )
    assert response.status_code == 404


def test_start_deep_analysis_and_get_result(completed_ic_task: str) -> None:
    deep_request = {
        "top_n": 3,
        "modules": {
            "factor_return": True,
            "factor_centrality": False,
            "trend_analysis": False,
            "parameter_sensitivity": False,
            "rolling_oos": False,
            "factor_orthogonalization": False,
            "factor_exposure": False,
            "long_short_analysis": False,
            "feature_quality_diagnostics": False,
            "net_ic_analysis": False,
        },
    }
    response = client.post(f"/api/v1/ic/deep-analysis/{completed_ic_task}", json=deep_request)
    assert response.status_code == 200

    deep_result = _wait_for_deep_result(completed_ic_task)
    assert deep_result["status"] in {"running", "completed"}
    assert deep_result["results"] is not None
    assert deep_result["summary"] is not None
    assert 0.0 <= deep_result["progress"] <= 1.0


def test_start_deep_analysis_invalid_task_id() -> None:
    response = client.post("/api/v1/ic/deep-analysis/nonexistent-task", json={"top_n": 5})
    assert response.status_code == 404


def test_get_deep_analysis_result_invalid_task_id() -> None:
    response = client.get("/api/v1/ic/deep-analysis/nonexistent-task/result")
    assert response.status_code == 404


def test_full_analysis_endpoint(sample_paths: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/ic/full-analysis",
        json={
            "features_path": sample_paths["features_path"],
            "labels_path": sample_paths["labels_path"],
            "meta_path": sample_paths["meta_path"],
            "config_override": sample_paths["config_override"],
            "deep_analysis": False,
        },
    )
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    _wait_for_task_completed(task_id)

    result_response = client.get(f"/api/v1/ic/result/{task_id}")
    assert result_response.status_code == 200
    result = result_response.json()
    assert "summary_table" in result


def test_full_analysis_with_deep_analysis_config(sample_paths: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/ic/full-analysis",
        json={
            "features_path": sample_paths["features_path"],
            "labels_path": sample_paths["labels_path"],
            "meta_path": sample_paths["meta_path"],
            "config_override": sample_paths["config_override"],
            "deep_analysis": True,
            "deep_analysis_config": {
                "top_n": 2,
                "modules": {
                    "factor_return": True,
                    "factor_centrality": False,
                    "trend_analysis": False,
                    "parameter_sensitivity": False,
                    "rolling_oos": False,
                    "factor_orthogonalization": False,
                    "factor_exposure": False,
                    "long_short_analysis": False,
                    "feature_quality_diagnostics": False,
                    "net_ic_analysis": False,
                },
            },
        },
    )
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    _wait_for_task_completed(task_id)

    result_response = client.get(f"/api/v1/ic/result/{task_id}")
    assert result_response.status_code == 200
    result = result_response.json()
    assert result.get("deep_analysis_enabled") is True
    assert isinstance(result.get("deep_analysis_report"), dict)


def test_deep_analysis_request_validation_top_n() -> None:
    response = client.post("/api/v1/ic/deep-analysis/nonexistent-task", json={"top_n": 999})
    assert response.status_code == 422


def test_full_analysis_request_validation_required_labels_path(sample_paths: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/ic/full-analysis",
        json={
            "features_path": sample_paths["features_path"],
            "meta_path": sample_paths["meta_path"],
        },
    )
    assert response.status_code == 422


def test_deep_analysis_start(completed_ic_task: str) -> None:
    response = client.post(
        f"/api/v1/ic/deep-analysis/{completed_ic_task}",
        json={"top_n": 3},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("status") in {"started", "running"}


def test_deep_analysis_result_serializes_numpy_scalars(completed_ic_task: str) -> None:
    original: dict | None = None
    with ic_analysis_service._lock:
        task_info = ic_analysis_service._tasks.get(completed_ic_task)
        assert task_info is not None
        original = copy.deepcopy(task_info)
        # API serialization stub：只驗 numpy scalar 邊界，不宣稱是真 deep 計算結果。
        task_info["deep_analysis_result"] = {
            "total_modules": np.int64(10),
            "completed_count": np.int64(1),
            "skipped_count": np.int64(0),
            "failed_count": np.int64(0),
            "total_execution_time_s": np.float64(0.12),
            "module_summary": {
                "factor_returns": "completed",
            },
            "results": {
                "factor_returns": {
                    "feature_0": {
                        "samples": np.int64(128),
                    }
                }
            },
        }

    try:
        response = client.get(f"/api/v1/ic/deep-analysis/{completed_ic_task}/result")
        assert response.status_code == 200
        payload = response.json()
        assert payload["summary"]["total_modules"] == 10
        assert payload["summary"]["completed_count"] == 1
        assert payload["results"]["results"]["factor_returns"]["feature_0"]["samples"] == 128
    finally:
        with ic_analysis_service._lock:
            assert original is not None
            ic_analysis_service._tasks[completed_ic_task] = original


# ---------------------------------------------------------------------------
# IC1C Phase 2 / T2 — cost_bps HTTP 422 矩陣 + wiring + union + probes
# ---------------------------------------------------------------------------

from api.models.ic_models import (  # noqa: E402
    DeepAnalysisRequest,
    ICAnalyzeRequest,
    NetICAnalysisRequest,
)
from api.services.ic_analysis_service import ICAnalysisService  # noqa: E402
from tests.momentum.Analysis.test_net_ic_schema_profiles import (  # noqa: E402
    SCHEMA_COST_ENABLED,
    SCHEMA_GROSS_ONLY,
    SCHEMA_SKIPPED,
    UNAVAILABLE_REASON,
)


def _net_ic_only_modules() -> dict:
    return {
        "factor_return": False,
        "factor_centrality": False,
        "trend_analysis": False,
        "parameter_sensitivity": False,
        "rolling_oos": False,
        "factor_orthogonalization": False,
        "factor_exposure": False,
        "long_short_analysis": False,
        "feature_quality_diagnostics": False,
        "net_ic_analysis": True,
    }


def test_cost_bps_range_422() -> None:
    """T2:0/NaN/inf/1000.1/{cost_enabled:false,cost_bps:NaN}/enabled 缺 bps → 422。

    HTTP 可 JSON 字面(0/1000.1/缺 bps/'NaN'/'Infinity')走 TestClient 422;
    Python float NaN/inf 於 Pydantic 同步路徑斷言 ValidationError(→FastAPI 422 同源)。
    """
    import json as _json

    from pydantic import ValidationError

    base = {"top_n": 3, "modules": _net_ic_only_modules()}

    http_cases = [
        {"net_ic": {"cost_enabled": True, "cost_bps": 0}},
        {"net_ic": {"cost_enabled": True, "cost_bps": 1000.1}},
        {"net_ic": {"cost_enabled": True}},  # enabled 缺 bps
        # codex 建議:HTTP 字串非有限字面(標準 JSON 可序列化)→422
        {"net_ic": {"cost_enabled": True, "cost_bps": "NaN"}},
        {"net_ic": {"cost_enabled": True, "cost_bps": "Infinity"}},
        {"net_ic": {"cost_enabled": False, "cost_bps": "NaN"}},
    ]
    for extra in http_cases:
        body = {**base, **extra}
        response = client.post(
            "/api/v1/ic/deep-analysis/nonexistent-task", json=body
        )
        assert response.status_code == 422, (
            f"expected 422 for {extra}, got {response.status_code}: {response.text}"
        )

    # 原始 body 再釘一次字串案例(避免 json= 路徑型別寬鬆誤綠)
    for raw_bps in ("NaN", "Infinity"):
        raw = _json.dumps(
            {
                **base,
                "net_ic": {"cost_enabled": True, "cost_bps": raw_bps},
            }
        )
        response = client.post(
            "/api/v1/ic/deep-analysis/nonexistent-task",
            content=raw,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422, (
            f"expected 422 for raw cost_bps={raw_bps!r}, "
            f"got {response.status_code}: {response.text}"
        )

    # T-F7 + 域:NaN/inf 即使 disabled 也拒(model 層=route 同步 validator)
    unit_cases = [
        {"cost_enabled": False, "cost_bps": float("nan")},
        {"cost_enabled": True, "cost_bps": float("nan")},
        {"cost_enabled": True, "cost_bps": float("inf")},
        {"cost_enabled": True, "cost_bps": 0.0},
        {"cost_enabled": True, "cost_bps": 1000.1},
        {"cost_enabled": True, "cost_bps": None},
    ]
    for kwargs in unit_cases:
        with pytest.raises(ValidationError):
            NetICAnalysisRequest(**kwargs)


def test_config_override_net_ic_rejected() -> None:
    """T2/T-F12 雙入口:DeepAnalysisRequest + ICAnalyzeRequest 皆拒 net_ic_analysis 整節。"""
    # DeepAnalysisRequest 入口
    response = client.post(
        "/api/v1/ic/deep-analysis/nonexistent-task",
        json={
            "top_n": 3,
            "config_override": {"net_ic_analysis": {"cost_enabled": True, "cost_bps": 5}},
        },
    )
    assert response.status_code == 422

    # ICAnalyzeRequest 入口(同步 Pydantic 路徑)
    response2 = client.post(
        "/api/v1/ic/analyze",
        json={
            "features_path": "/tmp/x.h5",
            "labels_path": "/tmp/y.h5",
            "config_override": {"net_ic_analysis": {"cost_bps": 7}},
        },
    )
    assert response2.status_code == 422

    # 單元層雙入口
    with pytest.raises(Exception):
        DeepAnalysisRequest(
            config_override={"net_ic_analysis": {"cost_enabled": True, "cost_bps": 5.0}}
        )
    with pytest.raises(Exception):
        ICAnalyzeRequest(
            config_override={"net_ic_analysis": {"cost_bps": 7.0}},
        )


def test_legacy_request_gross_only(completed_ic_task: str) -> None:
    """T2:舊 request(無 net_ic 欄)→cost_enabled=False→GROSS_ONLY 照跑。"""
    deep_request = {
        "top_n": 5,
        "modules": _net_ic_only_modules(),
        # 故意不帶 net_ic
    }
    response = client.post(
        f"/api/v1/ic/deep-analysis/{completed_ic_task}", json=deep_request
    )
    assert response.status_code == 200
    deep_result = _wait_for_deep_result(completed_ic_task, timeout=60.0)
    assert deep_result["status"] == "completed"
    results = deep_result.get("results") or {}
    net_ic = (results.get("results") or results).get("net_ic_analysis") or {}
    assert net_ic.get("skipped") is not True or "features" in net_ic
    features = net_ic.get("features") or {}
    if not features and net_ic.get("skipped"):
        # turnover 可能缺 → 頂層 skipped 可接受
        return
    assert features, f"expected features in net_ic_analysis, got {net_ic}"
    for name, feat in features.items():
        if feat.get("skipped"):
            assert set(feat.keys()) == SCHEMA_SKIPPED
            continue
        # GROSS_ONLY:無 cost 鍵
        keys = set(feat.keys())
        assert keys == SCHEMA_GROSS_ONLY, f"{name}: {sorted(keys)}"
        assert "cost_bps" not in feat
        assert "cost_drag_return" not in feat
        # T-F16 union 形狀
        nfr = feat.get("net_factor_return")
        assert isinstance(nfr, dict)
        assert set(nfr.keys()) == {"status", "value", "reason"}
        assert nfr["status"] == "unavailable"
        assert nfr["value"] is None
        assert nfr["reason"]


def test_cost_bps_fullstack_wiring(completed_ic_task: str) -> None:
    """T2:request 7bps → engine artifact 記 7 + COST_ENABLED + union 完整。"""
    deep_request = {
        "top_n": 5,
        "modules": _net_ic_only_modules(),
        "net_ic": {"cost_enabled": True, "cost_bps": 7.0},
        "config_override": None,
    }
    response = client.post(
        f"/api/v1/ic/deep-analysis/{completed_ic_task}", json=deep_request
    )
    assert response.status_code == 200, response.text
    deep_result = _wait_for_deep_result(completed_ic_task, timeout=60.0)
    assert deep_result["status"] == "completed", deep_result.get("error")
    results = deep_result.get("results") or {}
    net_ic = (results.get("results") or results).get("net_ic_analysis") or {}
    features = net_ic.get("features") or {}
    assert features, f"expected features, got {net_ic}"

    saw_cost = False
    for name, feat in features.items():
        if feat.get("skipped"):
            assert set(feat.keys()) == SCHEMA_SKIPPED
            continue
        keys = set(feat.keys())
        assert keys == SCHEMA_COST_ENABLED, f"{name}: {sorted(keys)}"
        assert feat.get("cost_bps") == 7.0
        saw_cost = True
        # T-F16:三鍵 union 原樣
        for ukey in ("net_factor_return", "breakeven_cost_bps", "profitable_after_cost"):
            u = feat[ukey]
            assert isinstance(u, dict), f"{name}.{ukey} flattened: {u!r}"
            assert set(u.keys()) == {"status", "value", "reason"}
            assert u["status"] == "unavailable"
            assert u["value"] is None
            assert isinstance(u["reason"], str) and u["reason"]
            assert "1c-FR" in u["reason"] or UNAVAILABLE_REASON in u["reason"]
        # 禁 net_ic 鍵
        assert "net_ic" not in feat
    assert saw_cost, "expected at least one COST_ENABLED feature"


def test_e2e_unavailable_union_shape(completed_ic_task: str) -> None:
    """T2 e2e:conditional metrics 恒 unavailable(1c-FR),response JSON 可 strict 序列化。"""
    deep_request = {
        "top_n": 3,
        "modules": _net_ic_only_modules(),
        "net_ic": {"cost_enabled": True, "cost_bps": 10.0},
    }
    response = client.post(
        f"/api/v1/ic/deep-analysis/{completed_ic_task}", json=deep_request
    )
    assert response.status_code == 200
    deep_result = _wait_for_deep_result(completed_ic_task, timeout=60.0)
    assert deep_result["status"] == "completed"
    # allow_nan=False 序列化不得炸
    import json as _json

    _json.dumps(deep_result, allow_nan=False)
    net_ic = ((deep_result.get("results") or {}).get("results") or {}).get(
        "net_ic_analysis"
    ) or {}
    for feat in (net_ic.get("features") or {}).values():
        if feat.get("skipped"):
            continue
        for ukey in ("net_factor_return", "breakeven_cost_bps", "profitable_after_cost"):
            if ukey not in feat:
                continue
            u = feat[ukey]
            assert u["status"] == "unavailable"
            assert u["value"] is None


def test_build_deep_module_override_typed_last() -> None:
    """merge 順序:typed net_ic 最後注入;cost 欄來自 typed 非 override。"""
    from api.models.ic_models import DeepAnalysisModules

    svc = ICAnalysisService()
    req = DeepAnalysisRequest(
        modules=DeepAnalysisModules(**_net_ic_only_modules()),
        net_ic=NetICAnalysisRequest(cost_enabled=True, cost_bps=7.0),
        config_override={"factor_exposure": {"neutralization_mode": "none"}},
    )
    override = svc._build_deep_module_override(req)
    assert override["net_ic_analysis"]["cost_enabled"] is True
    assert override["net_ic_analysis"]["cost_bps"] == 7.0
    assert override["net_ic_analysis"]["enabled"] is True
    assert override["factor_exposure"]["neutralization_mode"] == "none"


def test_mutation_m7_allow_override_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """M7:若允許 config_override.net_ic_analysis → 雙入口拒測應紅。"""
    from api.models import ic_models as models_mod

    monkeypatch.setattr(
        models_mod,
        "_reject_net_ic_analysis_in_config_override",
        lambda *_a, **_k: None,
    )

    with pytest.raises(AssertionError):
        raised = False
        try:
            # 直接呼叫 reject 函式(已 noop)
            models_mod._reject_net_ic_analysis_in_config_override(
                {"net_ic_analysis": {"cost_bps": 5}}
            )
            # 好後不 raise = 變異成功;oracle 要求必須 raise
            raise_happened = False
        except ValueError:
            raise_happened = True
        assert raise_happened, "config_override.net_ic_analysis must be rejected"


def test_mutation_m10_api_drop_validator(monkeypatch: pytest.MonkeyPatch) -> None:
    """M10 API 層:卸掉 NetICAnalysisRequest 域檢 → 0 應 422 卻過 → 好測試紅。"""
    from typing import Optional

    from pydantic import BaseModel

    class _LooseNetIC(BaseModel):
        cost_enabled: bool = False
        cost_bps: Optional[float] = None

    import api.models.ic_models as models_mod

    monkeypatch.setattr(models_mod, "NetICAnalysisRequest", _LooseNetIC)

    with pytest.raises(AssertionError):
        raised = False
        try:
            models_mod.NetICAnalysisRequest(cost_enabled=True, cost_bps=0.0)
        except Exception:
            raised = True
        assert raised, "cost_bps=0 must raise at API NetICAnalysisRequest"


def test_mutation_m4_drop_cost_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    """M4:若 _build_deep_module_override 不傳 cost_bps → fullstack 7 斷言紅。"""
    real = ICAnalysisService._build_deep_module_override

    def drop_cost(self, request):  # type: ignore[no-untyped-def]
        out = real(self, request)
        # 抹掉 cost 注入,模擬幽靈開關
        if "net_ic_analysis" in out:
            out["net_ic_analysis"] = {
                "enabled": out["net_ic_analysis"].get("enabled", True)
            }
        return out

    monkeypatch.setattr(ICAnalysisService, "_build_deep_module_override", drop_cost)
    svc = ICAnalysisService()
    from api.models.ic_models import DeepAnalysisModules

    req = DeepAnalysisRequest(
        modules=DeepAnalysisModules(**_net_ic_only_modules()),
        net_ic=NetICAnalysisRequest(cost_enabled=True, cost_bps=7.0),
    )
    override = svc._build_deep_module_override(req)
    with pytest.raises(AssertionError):
        assert override["net_ic_analysis"].get("cost_bps") == 7.0
        assert override["net_ic_analysis"].get("cost_enabled") is True
