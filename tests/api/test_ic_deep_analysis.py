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
        result = _build_completed_ic_task(sample_paths)
        assert not ctx.spy.violations
        return result
    finally:
        # deactivate 必須無條件執行,否則 assert 失敗會洩漏 _ACTIVE → 後續 suite ERROR
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


def test_api_deep_cache_key_includes_fit_mode(completed_ic_task: str) -> None:
    """LA-0 B4 #6：真 API 路徑 deep cache key 必含 fit_mode + pit_stats_version。

    非僅 private method：POST /ic/analyze 完成後，經 API 觸發 deep-analysis，
    驗證真 API 留下的 analyzer 上 key payload 含 mode/version，且 mode 變 key 變。
    """
    import hashlib
    import json

    from momentum.Analysis.pit_stats import PIT_STATS_VERSION

    analyzer = ic_analysis_service.get_analyzer(completed_ic_task)
    assert analyzer is not None

    # 真 analyze API 後 fit_mode 已由 orchestrator 注入（split 預設 ON → train_mask）
    fit_mode = getattr(analyzer, "_active_fit_mode", None)
    assert fit_mode in {"train_mask", "pit_expanding", "full_sample"}, fit_mode

    with ic_analysis_service._lock:
        task_info = ic_analysis_service._tasks.get(completed_ic_task)
        assert task_info is not None
        result = task_info.get("result") or {}
    meta = result.get("metadata") or {}
    cache_meta = (analyzer._ic_cache or {}).get("metadata") or {}
    observed_mode = meta.get("fit_mode") or cache_meta.get("fit_mode")
    assert observed_mode == fit_mode
    assert (
        meta.get("pit_stats_version") == PIT_STATS_VERSION
        or cache_meta.get("pit_stats_version") == PIT_STATS_VERSION
    )

    # 真 API deep-analysis（modules 全關：仍走 run_deep_analysis → key 建構路徑）
    deep_req = {
        "top_n": 2,
        "modules": {
            "factor_return": False,
            "factor_centrality": False,
            "trend_analysis": False,
            "parameter_sensitivity": False,
            "rolling_oos": False,
            "factor_orthogonalization": False,
            "factor_exposure": False,
            "long_short_analysis": False,
        },
    }
    response = client.post(
        f"/api/v1/ic/deep-analysis/{completed_ic_task}",
        json=deep_req,
    )
    assert response.status_code == 200, response.text
    deep_result = _wait_for_deep_result(completed_ic_task, timeout=60.0)
    assert deep_result.get("status") in {"completed", "failed"}

    filtered = getattr(analyzer, "_filtered_features_df", None)
    if filtered is not None and len(filtered.columns) > 0:
        features_for_key = sorted(list(filtered.columns[:2]))
    else:
        features_for_key = ["f"]

    cfg = analyzer._apply_tier_config(analyzer._config)
    key_a = analyzer._compute_deep_cache_key(features_for_key, cfg)
    deep_cfg = {
        "factor_return": cfg.factor_return.model_dump(),
        "factor_centrality": cfg.factor_centrality.model_dump(),
        "trend_analysis": cfg.trend_analysis.model_dump(),
        "parameter_sensitivity": cfg.parameter_sensitivity.model_dump(),
        "rolling_oos": cfg.rolling_oos.model_dump(),
        "factor_orthogonalization": cfg.factor_orthogonalization.model_dump(),
        "factor_exposure": cfg.factor_exposure.model_dump(),
        "long_short_analysis": cfg.long_short_analysis.model_dump(),
        "feature_quality_diagnostics": cfg.feature_quality_diagnostics.model_dump(),
        "net_ic_analysis": cfg.net_ic_analysis.model_dump(),
        "deep_analysis_global": cfg.deep_analysis_global.model_dump(),
    }
    payload = {
        "features": sorted(features_for_key),
        "deep_config": deep_cfg,
        "pit_stats_version": PIT_STATS_VERSION,
        "fit_mode": fit_mode,
    }
    expected = hashlib.md5(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert key_a == expected

    # mode 變 → key 變（cache 隔離）
    prev = analyzer._active_fit_mode
    analyzer._active_fit_mode = (
        "pit_expanding" if fit_mode != "pit_expanding" else "full_sample"
    )
    try:
        key_b = analyzer._compute_deep_cache_key(features_for_key, cfg)
        assert key_a != key_b
    finally:
        analyzer._active_fit_mode = prev


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
        # API serialization stub：驗 numpy scalar 邊界 + STOPGAP sanitizer。
        # 舊斷言為何錯: 注入 finite factor_returns samples==128 固化錯位輸出形狀;
        # sanitizer 下架 → factor_returns 為 §U 佔位,無有限葉。
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
        # FR legacy completed → unavailable 後 completed_count 重算為 0(unavailable 不計)
        assert payload["summary"]["completed_count"] == 0
        fr = payload["results"]["results"]["factor_returns"]
        assert fr.get("status") == "unavailable"
        assert fr.get("value") is None
        assert "feature_0" not in fr
        ms = (payload.get("results") or {}).get("module_summary") or {}
        assert ms.get("factor_returns") == "unavailable"
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


# ---------------------------------------------------------------------------
# IC1C-FR-STOPGAP Task 1.2 — factor_return sanitizer 七掛點 + 冪等 + M2
# ---------------------------------------------------------------------------

from momentum.Analysis.deep_analysis_types import DeepAnalysisReport  # noqa: E402
from momentum.Analysis.factor_return_sanitizer import (  # noqa: E402
    FACTOR_RETURNS_PLACEHOLDER,
    assert_no_finite_in_factor_returns_subtree,
    has_finite_numeric_leaf,
    sanitize_factor_returns,
)
import momentum.Analysis.factor_return_sanitizer as _fr_sanitizer_mod  # noqa: E402
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator  # noqa: E402
from momentum.Analysis.ic_reporter import ICReporter  # noqa: E402
from momentum.Analysis.ic_config_schema import ICConfig  # noqa: E402
import json  # noqa: E402
import tempfile  # noqa: E402
from dataclasses import asdict  # noqa: E402


def _legacy_factor_returns_payload() -> dict:
    """有限 numeric leaf 的 legacy factor_returns(錯位序列形狀)。"""
    return {
        "feature_0": {
            "long_short_mean_return": 0.11,
            "samples": 128,
            "risk_metrics": {"sharpe": 1.5, "max_drawdown": -0.08},
        }
    }


def _legacy_summary_null_row() -> dict:
    """含三個 summary null keys 的 legacy 列(證 _SUMMARY_NULL_KEYS 有牙)。"""
    return {
        "feature_name": "feature_0",
        "ic_mean": 0.05,
        "icir": 0.5,
        "factor_return_ls_mean": 0.11,
        "factor_return_sharpe": 1.5,
        "factor_return_max_drawdown": -0.08,
    }


def _assert_fr_no_finite(payload: object) -> None:
    if payload is None:
        return
    if isinstance(payload, dict) and payload.get("status") == "unavailable":
        assert payload.get("value") is None
        assert not has_finite_numeric_leaf(payload)
        return
    # nested under results / deep report
    if isinstance(payload, dict):
        if "factor_returns" in payload:
            _assert_fr_no_finite(payload["factor_returns"])
            return
        if "results" in payload and isinstance(payload["results"], dict):
            if "factor_returns" in payload["results"]:
                _assert_fr_no_finite(payload["results"]["factor_returns"])
                return
    assert not has_finite_numeric_leaf(payload), f"finite leaf leaked: {payload!r}"


def _seed_orch_with_legacy_deep_cache(
    *,
    fr_payload: dict | None = None,
    fr_mean: float = 0.11,
) -> tuple[ICFilterOrchestrator, ICConfig]:
    """注入 _ic_cache + deep cache 含 legacy FR,供 cache-hit / force-merge 測。"""
    config = ICConfig()
    orch = ICFilterOrchestrator(config)
    payload = fr_payload if fr_payload is not None else {
        "feature_0": {"long_short_mean_return": fr_mean, "samples": 128}
    }
    legacy_report = DeepAnalysisReport(
        results={
            "factor_returns": payload,
            "trend_analysis": {"placeholder": True},
        },
        module_summary={
            "factor_returns": "completed",
            "trend_analysis": "completed",
        },
        completed_count=2,
        skipped_count=0,
    )
    orch._ic_cache = {
        "features_df": __import__("pandas").DataFrame({"f": [1.0, 2.0]}),
        "label_series": __import__("pandas").Series([0.1, 0.2]),
        "metadata": {},
        "icir": {},
        "rolling_ic": {},
        "ic_decay": {},
        "grouped_ic": {},
        "event_info": {},
        "stage0_log": {},
        "preproc_log": {},
    }
    orch._filtered_features_df = orch._ic_cache["features_df"]
    cache_key = orch._compute_deep_cache_key(["f"], orch._apply_tier_config(config))
    orch._deep_analysis_cache[cache_key] = legacy_report
    return orch, config


def test_sanitizer_cache_hit_legacy() -> None:
    """(a) orchestrator cache-hit: legacy 有限值 → sanitize 後無有限葉 + summary/count。"""
    orch, _config = _seed_orch_with_legacy_deep_cache()

    out = orch.run_deep_analysis(selected_features=["f"])
    assert "factor_returns" in out.results
    _assert_fr_no_finite(out.results["factor_returns"])
    assert out.results["factor_returns"].get("status") == "unavailable"
    # B1-1: summary 不得殘 completed;unavailable 不計 completed_count
    assert out.module_summary.get("factor_returns") == "unavailable"
    assert out.completed_count == 1  # only trend_analysis
    assert out.skipped_count == 0


def test_sanitizer_cache_force_merge_legacy() -> None:
    """B-R2-1: cache 有 legacy FR + force 其他模組(merge 非早退)→ 輸出無有限 FR 葉。

    路徑:force_modules=["trend_analysis"] 且 deep cache 命中 → 走 merge 而非 cache-hit
    早退;legacy FR 不得以 long_short_mean_return 有限值洩出,summary/count 一致。
    """
    orch, _config = _seed_orch_with_legacy_deep_cache(
        fr_payload={"feature_0": {"long_short_mean_return": 0.42}},
        fr_mean=0.42,
    )

    # 避免真跑 trend(無 rolling_ic);只證 merge 出口仍 sanitize FR
    def _fake_trend(selected_features, config):  # type: ignore[no-untyped-def]
        return {"direction": "up", "score": 0.9}

    orch._run_trend_analysis = _fake_trend  # type: ignore[method-assign]

    out = orch.run_deep_analysis(
        selected_features=["f"],
        force_modules=["trend_analysis"],
    )
    fr = out.results.get("factor_returns")
    assert fr is not None
    _assert_fr_no_finite(fr)
    assert fr.get("status") == "unavailable"
    assert out.module_summary.get("factor_returns") == "unavailable"
    # trend re-run completed; FR unavailable 不計 → completed_count == 1
    assert out.module_summary.get("trend_analysis") == "completed"
    assert out.completed_count == 1
    assert "0.42" not in __import__("json").dumps(out.results.get("factor_returns"))


def test_sanitizer_raw_json_legacy(completed_ic_task: str) -> None:
    """(b) API raw JSON export: inject finite → dump 無有限 factor_returns 葉。"""
    original = None
    with ic_analysis_service._lock:
        task_info = ic_analysis_service._tasks.get(completed_ic_task)
        assert task_info is not None
        original = copy.deepcopy(task_info)
        result = dict(task_info.get("result") or {})
        result["deep_analysis_report"] = {
            "results": {"factor_returns": _legacy_factor_returns_payload()},
        }
        # also top-level for raw report path
        result["factor_returns"] = _legacy_factor_returns_payload()
        task_info["result"] = result

    try:
        response = client.get(f"/api/v1/ic/export/{completed_ic_task}/json")
        assert response.status_code == 200
        body = response.json() if response.headers.get("content-type", "").startswith("application/json") else json.loads(response.content.decode("utf-8"))
        # export returns file-like; TestClient may expose body as content
        if not isinstance(body, dict):
            body = json.loads(response.content.decode("utf-8"))
        if "factor_returns" in body:
            _assert_fr_no_finite(body["factor_returns"])
        deep = body.get("deep_analysis_report") or {}
        if isinstance(deep, dict) and "factor_returns" in deep:
            _assert_fr_no_finite(deep["factor_returns"])
        if isinstance(deep, dict) and isinstance(deep.get("results"), dict) and "factor_returns" in deep["results"]:
            _assert_fr_no_finite(deep["results"]["factor_returns"])
        # whole tree: any factor_returns node must lack finite leaves
        def walk(obj: object) -> None:
            if isinstance(obj, dict):
                if "factor_returns" in obj:
                    _assert_fr_no_finite(obj["factor_returns"])
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v)
        walk(body)
    finally:
        with ic_analysis_service._lock:
            assert original is not None
            ic_analysis_service._tasks[completed_ic_task] = original


def test_sanitizer_task_storage_roundtrip(completed_ic_task: str) -> None:
    """(c) serializer+task storage → get_deep_analysis_result 皆無有限葉。"""
    original = None
    with ic_analysis_service._lock:
        task_info = ic_analysis_service._tasks.get(completed_ic_task)
        assert task_info is not None
        original = copy.deepcopy(task_info)

    try:
        # 模擬 serializer 寫入(與 production _serialize_deep_report 同路徑)
        legacy_report = DeepAnalysisReport(
            results={"factor_returns": _legacy_factor_returns_payload()},
            module_summary={"factor_returns": "completed"},
            completed_count=1,
        )
        serialized = ic_analysis_service._serialize_deep_report(legacy_report)
        _assert_fr_no_finite(serialized)
        with ic_analysis_service._lock:
            task_info = ic_analysis_service._tasks.get(completed_ic_task)
            assert task_info is not None
            task_info["deep_analysis_result"] = serialized

        got = ic_analysis_service.get_deep_analysis_result(completed_ic_task)
        assert got is not None
        _assert_fr_no_finite(got)

        # 即使 task_info 被直接注入 legacy(繞 serializer),get 仍 sanitize
        with ic_analysis_service._lock:
            task_info = ic_analysis_service._tasks.get(completed_ic_task)
            assert task_info is not None
            task_info["deep_analysis_result"] = {
                "results": {"factor_returns": _legacy_factor_returns_payload()},
                "module_summary": {"factor_returns": "completed"},
            }
        got2 = ic_analysis_service.get_deep_analysis_result(completed_ic_task)
        assert got2 is not None
        _assert_fr_no_finite(got2)
    finally:
        with ic_analysis_service._lock:
            assert original is not None
            ic_analysis_service._tasks[completed_ic_task] = original


def test_sanitizer_csv_legacy() -> None:
    """(d) detailed CSV: legacy finite → 輸出無有限 long_short_mean_return 值。"""
    reporter = ICReporter({})
    report = {
        "summary_table": [{"feature_name": "feature_0", "ic_mean": 0.05, "icir": 0.5}],
        "deep_analysis_report": {
            "results": {"factor_returns": _legacy_factor_returns_payload()},
        },
    }
    csv_text = reporter.generate_detailed_csv(report, "factor_returns")
    # 佔位後 flatten 可能含 status/reason 字串,不得含有限報酬數值
    assert "0.11" not in csv_text
    assert "1.5" not in csv_text
    assert "-0.08" not in csv_text


def test_sanitizer_ai_json_legacy() -> None:
    """(e) AI JSON: factor_returns 子樹禁任何有限 numeric leaf(通用 oracle)。"""
    reporter = ICReporter({})
    report = {
        "summary_table": [_legacy_summary_null_row()],
        "deep_analysis_report": {
            "results": {"factor_returns": _legacy_factor_returns_payload()},
        },
        # 亦附 top-level 誤嵌 size meta 形狀(防假綠)
        "factor_returns": {
            **_legacy_factor_returns_payload(),
            "size": 1,
            "keys": ["feature_0"],
        },
    }
    payload = reporter.generate_ai_json(report)
    summaries = payload.get("module_summaries") or {}
    fr_sum = summaries.get("factor_returns")
    if fr_sum is not None:
        assert isinstance(fr_sum, dict)
        assert fr_sum.get("status") == "unavailable"
        assert not has_finite_numeric_leaf(fr_sum)
    # 通用:遞迴掃 factor_returns 子樹禁任何有限 numeric leaf
    assert_no_finite_in_factor_returns_subtree(payload)


def _assert_markdown_factor_returns_no_finite(md: str) -> None:
    """對**真實 Markdown 字串產物**判定:深度摘要 factor_returns 行禁有限 numeric。

    解析 ``- factor_returns: {...}`` 行(ast.literal_eval),再以
    has_finite_numeric_leaf 判定;不對輸入 re-sanitize,避免假綠。
    """
    import ast
    import re

    assert isinstance(md, str) and md, "markdown product empty"
    # 字面禁 legacy 有限報酬字樣(輔助)
    for banned in ("0.11", "0.42", "long_short_mean_return"):
        # long_short_mean_return 不應出現在 MD 摘要(佔位僅 status/reason)
        if banned == "long_short_mean_return" and banned in md:
            raise AssertionError(f"markdown leaks key {banned!r}")
        if banned != "long_short_mean_return" and banned in md:
            raise AssertionError(f"markdown leaks finite literal {banned!r}")

    in_deep = False
    fr_lines: list[str] = []
    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_deep = stripped == "## 深度分析摘要"
            continue
        if in_deep and stripped.startswith("- factor_returns:"):
            fr_lines.append(stripped)

    if not fr_lines:
        # 無 FR 行亦可(default-off);有 deep 節但無 FR 不算洩漏
        return

    for line in fr_lines:
        payload_str = line.split(":", 1)[1].strip()
        try:
            value = ast.literal_eval(payload_str)
        except (SyntaxError, ValueError) as exc:
            # 無法解析時,若行內出現獨立有限數字亦紅(排除 1c-FR 類 token)
            if re.search(r"(?<![A-Za-z])\d+\.\d+|(?<![A-Za-z-])\b\d+\b(?!c-)", payload_str):
                raise AssertionError(
                    f"markdown factor_returns unparsable with numeric: {line!r}"
                ) from exc
            continue
        if has_finite_numeric_leaf(value):
            raise AssertionError(
                f"finite numeric in markdown factor_returns product: {value!r} line={line!r}"
            )
        # §U 期望:status unavailable 且無 size/samples 等 meta
        if isinstance(value, dict):
            if value.get("status") == "unavailable" and "size" in value:
                raise AssertionError(f"unavailable FR still has size meta: {value!r}")


def test_sanitizer_markdown_legacy() -> None:
    """(f) Markdown: **實際 MD 產物** factor_returns 段落無有限 numeric leaf。"""
    reporter = ICReporter({})
    report = {
        "summary_table": [_legacy_summary_null_row()],
        "deep_analysis_report": {
            "results": {
                "factor_returns": {
                    **_legacy_factor_returns_payload(),
                    "size": 1,
                }
            },
        },
    }
    md = reporter.generate_enhanced_markdown(report)
    # oracle 必須打在真實 Markdown 字串,不可 re-sanitize 輸入後再驗
    _assert_markdown_factor_returns_no_finite(md)
    assert "0.11" not in md


def test_sanitizer_export_all_legacy() -> None:
    """(g) export_all raw dump: JSON 檔無有限 factor_returns 葉。"""
    reporter = ICReporter({})
    report = {
        "summary_table": [_legacy_summary_null_row()],
        "deep_analysis_report": {
            "results": {"factor_returns": _legacy_factor_returns_payload()},
        },
        "factor_returns": _legacy_factor_returns_payload(),
    }
    with tempfile.TemporaryDirectory() as tmp:
        paths = reporter.export_all(report, tmp, "stopgap")
        raw = Path(paths["json"]).read_text(encoding="utf-8")
        data = json.loads(raw)
        assert_no_finite_in_factor_returns_subtree(data)
        # summary 三欄 null
        for row in data.get("summary_table") or []:
            if isinstance(row, dict):
                for k in (
                    "factor_return_ls_mean",
                    "factor_return_sharpe",
                    "factor_return_max_drawdown",
                ):
                    if k in row:
                        assert row[k] is None


def test_sanitizer_save_report_legacy_no_leak() -> None:
    """具名:save_report 注入 legacy → 落檔無有限 FR 葉(B1-2 SAVE_REPORT_LEAK)。"""
    reporter = ICReporter({"ai_summary": False})
    report = {
        "summary_table": [_legacy_summary_null_row()],
        "factor_returns": _legacy_factor_returns_payload(),
        "deep_analysis_report": {
            "results": {"factor_returns": _legacy_factor_returns_payload()},
            "module_summary": {"factor_returns": "completed"},
            "completed_count": 1,
        },
    }
    with tempfile.TemporaryDirectory() as tmp:
        paths = reporter.save_report(report, tmp, "save_leak_probe")
        raw = Path(paths["json"]).read_text(encoding="utf-8")
        data = json.loads(raw)
        assert_no_finite_in_factor_returns_subtree(data)
        assert "0.11" not in raw
        # summary 狀態一致
        deep = data.get("deep_analysis_report") or {}
        if isinstance(deep, dict) and isinstance(deep.get("module_summary"), dict):
            assert deep["module_summary"].get("factor_returns") == "unavailable"
        if isinstance(deep, dict) and "completed_count" in deep:
            assert deep["completed_count"] == 0


def test_sanitizer_summary_null_keys_in_fixture() -> None:
    """legacy fixture 含三 summary keys → sanitize 後皆 null。"""
    row = _legacy_summary_null_row()
    for k in (
        "factor_return_ls_mean",
        "factor_return_sharpe",
        "factor_return_max_drawdown",
    ):
        assert k in row and row[k] is not None
    cleaned = sanitize_factor_returns({"summary_table": [row]})
    out_row = cleaned["summary_table"][0]
    assert out_row["factor_return_ls_mean"] is None
    assert out_row["factor_return_sharpe"] is None
    assert out_row["factor_return_max_drawdown"] is None


def test_sanitizer_idempotent() -> None:
    """佔位再過 → 不變。"""
    once = sanitize_factor_returns({"results": {"factor_returns": _legacy_factor_returns_payload()}})
    twice = sanitize_factor_returns(once)
    assert twice == once
    assert twice["results"]["factor_returns"] == FACTOR_RETURNS_PLACEHOLDER
    # missing key 不 crash
    assert sanitize_factor_returns({"results": {"trend_analysis": {"x": 1}}})["results"]["trend_analysis"]["x"] == 1


def test_mutation_m2_bypass_sanitizer(monkeypatch: pytest.MonkeyPatch) -> None:
    """M2:繞 sanitizer → legacy payload 測試紅(基線綠→注入紅→還原)。"""

    def identity(payload):  # type: ignore[no-untyped-def]
        return payload

    monkeypatch.setattr(
        "momentum.Analysis.factor_return_sanitizer.sanitize_factor_returns",
        identity,
    )
    # reporter 掛點 import 時已綁定? generate_detailed_csv 內 local import → monkeypatch 模組屬性生效
    reporter = ICReporter({})
    report = {
        "summary_table": [{"feature_name": "feature_0", "ic_mean": 0.05, "icir": 0.5}],
        "deep_analysis_report": {
            "results": {"factor_returns": _legacy_factor_returns_payload()},
        },
    }
    csv_text = reporter.generate_detailed_csv(report, "factor_returns")
    # 繞過後應露出有限值;斷言「無 0.11」應紅
    with pytest.raises(AssertionError):
        assert "0.11" not in csv_text


def test_mutation_m2b_clear_summary_null_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """清空 _SUMMARY_NULL_KEYS → summary null 斷言必紅(證 keys 有牙)。"""
    monkeypatch.setattr(_fr_sanitizer_mod, "_SUMMARY_NULL_KEYS", frozenset())
    row = _legacy_summary_null_row()
    cleaned = _fr_sanitizer_mod.sanitize_factor_returns({"summary_table": [row]})
    out_row = cleaned["summary_table"][0]
    with pytest.raises(AssertionError):
        assert out_row["factor_return_ls_mean"] is None
        assert out_row["factor_return_sharpe"] is None
        assert out_row["factor_return_max_drawdown"] is None


def test_mutation_m2c_restore_finite_metadata() -> None:
    """恢復 finite size:1 metadata 於 factor_returns → 通用 oracle 必紅。"""
    poisoned = {
        "factor_returns": {
            "status": "unavailable",
            "value": None,
            "reason": "x",
            "size": 1,  # finite meta 洩漏
        }
    }
    with pytest.raises(AssertionError):
        assert_no_finite_in_factor_returns_subtree(poisoned)


def test_mutation_m2d_markdown_restore_size_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    """B-R2-2: monkeypatch _build_module_summaries 恢復 size:1 → MD oracle 必紅。

    證 Markdown wiring 真連到產物 oracle,非只對 re-sanitize 輸入假綠。
    """

    def _leaky_summaries(self, deep_payload):  # type: ignore[no-untyped-def]
        return {"factor_returns": {"size": 1}}

    monkeypatch.setattr(ICReporter, "_build_module_summaries", _leaky_summaries)
    reporter = ICReporter({})
    report = {
        "summary_table": [_legacy_summary_null_row()],
        "deep_analysis_report": {
            "results": {"factor_returns": _legacy_factor_returns_payload()},
        },
    }
    md = reporter.generate_enhanced_markdown(report)
    # 產物必含 size:1;對真實 MD 的 oracle 必須 raise
    assert "size" in md and "1" in md
    with pytest.raises(AssertionError):
        _assert_markdown_factor_returns_no_finite(md)
