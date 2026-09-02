"""IC analysis API tests."""

import time
from pathlib import Path

import pytest
from binance.client import Client
from fastapi.testclient import TestClient

Client.ping = lambda self: {}

from api.main import app
from tests.fixtures.ic_api_real_kline import ic_api_real_kline


client = TestClient(app)

pytestmark = [
    pytest.mark.ic_persist_redirect,
    pytest.mark.usefixtures("ic_persist_redirect"),
]


def _wait_for_task(task_id: str, timeout: float = 15.0) -> None:
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


def _build_ic_analysis_task(real_kline: dict) -> dict:
    request_data = {
        "features_path": real_kline["features_path"],
        "labels_path": real_kline["labels_path"],
        "meta_path": real_kline["meta_path"],
        "config_override": {
            **real_kline["config_override"],
            "ic_train_test_split": False,
            "thresholds": {
                "ic_mean_min": -1.0,
                "icir_min": -1.0,
                "p_value_max": 1.0,
                "ic_hit_rate_min": 0.0,
                "monotonicity_score_min": 0.0,
                "coverage_min": 0.0,
                "long_short_spread": {"enabled": False},
            },
            "redundancy": {"correlation_threshold": 0.99},
        },
    }

    with client:
        response = client.post("/api/v1/ic/analyze", json=request_data)
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        _wait_for_task(task_id)

    return {"task_id": task_id, "feature_names": real_kline["feature_names"]}


@pytest.fixture(scope="session")
def ic_analysis_task(
    ic_api_real_kline: dict,
    redirect_patch_set,
    redirect_root_session: Path,
) -> dict:
    ctx = redirect_patch_set.activate(redirect_root_session, owner="ic_analysis_task")
    try:
        result = _build_ic_analysis_task(ic_api_real_kline)
        assert not ctx.spy.violations
        return result
    finally:
        # deactivate 必須無條件執行,否則 assert 失敗會洩漏 _ACTIVE → 後續 suite ERROR
        redirect_patch_set.deactivate(ctx)


def test_ic_task_status(ic_analysis_task: dict) -> None:
    task_id = ic_analysis_task["task_id"]
    response = client.get(f"/api/v1/ic/task/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"running", "completed", "failed"}
    assert "progress" in data


def test_ic_result(ic_analysis_task: dict) -> None:
    task_id = ic_analysis_task["task_id"]
    response = client.get(f"/api/v1/ic/result/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert "metadata" in data
    assert "summary_table" in data


def test_ic_summary(ic_analysis_task: dict) -> None:
    task_id = ic_analysis_task["task_id"]
    response = client.get(f"/api/v1/ic/summary/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data


def test_ic_top_features(ic_analysis_task: dict) -> None:
    response = client.get("/api/v1/ic/top-features?n=3")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_ic_quantile_and_correlation(ic_analysis_task: dict) -> None:
    task_id = ic_analysis_task["task_id"]
    result = client.get(f"/api/v1/ic/result/{task_id}").json()
    summary_table = result.get("summary_table", [])
    assert summary_table
    feature_name = summary_table[0]["feature_name"]

    response = client.get(f"/api/v1/ic/quantile/{feature_name}")
    assert response.status_code == 200

    response = client.get("/api/v1/ic/correlation")
    assert response.status_code == 200
    data = response.json()
    assert "features" in data
    assert "matrix" in data


def test_ic_grouped(ic_analysis_task: dict) -> None:
    response = client.get("/api/v1/ic/grouped")
    assert response.status_code == 200


def test_ic_config_update() -> None:
    response = client.put("/api/v1/ic/config", json={"thresholds": {"icir_min": 0.1}})
    assert response.status_code == 200
    data = response.json()
    assert "thresholds" in data


def test_ic_refilter(ic_analysis_task: dict) -> None:
    response = client.post("/api/v1/ic/refilter", json={"thresholds": {"icir_min": -1.0}})
    assert response.status_code == 200
    data = response.json()
    assert "summary_table" in data


def test_ic_refilter_nan_inf_are_json_safe(ic_analysis_task: dict, monkeypatch) -> None:
    """G3-D12（UAT B16）：refilter 回 analyzer 原始 dict 含 NaN／inf ⇒ 曾 500「Out of range float values」⇒ 瀏覽器 Failed to fetch。

    refilter 須與 `/result` 走同一出口（非有限值 → null），mutation：改回 `return report` ⇒ 本條紅。
    """
    import math

    from api.routes.ic_analysis import ic_analysis_service

    task_id = ic_analysis_task["task_id"]
    analyzer = ic_analysis_service.get_analyzer(task_id)
    assert analyzer is not None
    real = analyzer.refilter

    def refilter_with_nonfinite(thresholds):
        report = dict(real(thresholds))
        report["_probe"] = {"nan": float("nan"), "inf": float("inf"), "neg_inf": -math.inf, "ok": 1.5}
        return report

    monkeypatch.setattr(analyzer, "refilter", refilter_with_nonfinite)
    response = client.post(f"/api/v1/ic/refilter?task_id={task_id}", json={"thresholds": {"icir_min": -1.0}})
    assert response.status_code == 200, response.text
    data = response.json()
    assert "summary_table" in data
    assert data["_probe"] == {"nan": None, "inf": None, "neg_inf": None, "ok": 1.5}
    # 與 /result 同一出口：兩者對同一 task 之 summary_table 逐字相同
    result = client.get(f"/api/v1/ic/result/{task_id}").json()
    assert result["summary_table"] == data["summary_table"]


def test_ic_export_csv(ic_analysis_task: dict) -> None:
    task_id = ic_analysis_task["task_id"]
    response = client.get(f"/api/v1/ic/export-csv/{task_id}")
    assert response.status_code == 200


def test_ic_export_hdf5(ic_analysis_task: dict) -> None:
    task_id = ic_analysis_task["task_id"]
    response = client.get(f"/api/v1/ic/export/{task_id}")
    assert response.status_code == 200
