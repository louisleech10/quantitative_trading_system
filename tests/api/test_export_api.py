import copy
import time
from pathlib import Path

import h5py
import numpy as np
import pytest
from binance.client import Client
from fastapi.testclient import TestClient

Client.ping = lambda self: {}

from api.main import app
from api.services.ic_analysis_service import ic_analysis_service
from tests.fixtures.ic_persist_redirect import get_active_redirect_root
from tests.fixtures.ic_api_real_kline import ic_api_real_kline


client = TestClient(app)

pytestmark = [
    pytest.mark.ic_persist_redirect,
]


def _export_fixture_filtered_path(metadata: dict) -> Path:
    symbol = metadata.get("symbol") if metadata else None
    timeframe = metadata.get("timeframe") if metadata else None
    name = (
        f"{symbol}_{timeframe}_filtered.h5"
        if symbol and timeframe
        else "filtered_features.h5"
    )
    active_root = get_active_redirect_root()
    base = active_root / "features" if active_root is not None else Path("data_cache/features")
    return base / name


def _wait_for_task(task_id: str, timeout: float = 20.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
        response = client.get(f"/api/v1/ic/task/{task_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] == "completed":
            return
        if payload["status"] == "failed":
            pytest.fail(f"task failed: {payload.get('error')}")
        time.sleep(0.2)
    pytest.fail("task timeout")


@pytest.fixture(scope="session")
def export_task(
    ic_api_real_kline: dict,
    redirect_patch_set,
    redirect_root_session: Path,
) -> dict:
    """建 task 時短暫 activate;yield 期間不得持有 _ACTIVE(否則後續 suite ERROR)。"""
    analyze_payload = {
        "features_path": ic_api_real_kline["features_path"],
        "labels_path": ic_api_real_kline["labels_path"],
        "meta_path": ic_api_real_kline["meta_path"],
        "config_override": {
            **ic_api_real_kline["config_override"],
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

    redirect_ctx = redirect_patch_set.activate(redirect_root_session, owner="export_task")
    try:
        with client:
            analyze_response = client.post("/api/v1/ic/analyze", json=analyze_payload)
            assert analyze_response.status_code == 200
            task_id = analyze_response.json()["task_id"]
            _wait_for_task(task_id)

        original: dict | None = None
        with ic_analysis_service._lock:
            task_info = ic_analysis_service._tasks.get(task_id)
            if task_info is not None:
                original = copy.deepcopy(task_info)
                # API serialization stub：export seam 所需容器。
                # 舊斷言為何錯: 注入 finite long_short_mean_return 固化錯位 CSV 形狀;
                # STOPGAP sanitizer 下架 → detailed CSV 無有限報酬葉(見 test_export_csv_detailed_factor_return)。
                task_info["deep_analysis_result"] = {
                    "results": {
                        "factor_returns": {
                            "feature_0": {
                                "long_short_mean_return": 0.03,
                                "risk_metrics": {"sharpe": 1.2, "max_drawdown": -0.1},
                            }
                        }
                    }
                }

        result = client.get(f"/api/v1/ic/result/{task_id}")
        assert result.status_code == 200
        metadata = result.json().get("metadata", {})

        filtered_path = _export_fixture_filtered_path(metadata)
        filtered_path.parent.mkdir(parents=True, exist_ok=True)
        with h5py.File(filtered_path, "w") as file:
            group = file.create_group("filtered")
            group.create_dataset(
                "features",
                data=ic_api_real_kline["features"].iloc[:1, :2].to_numpy(dtype=np.float64),
            )
        assert not redirect_ctx.spy.violations
    finally:
        # setup 結束即釋放;session-scoped yield 不得跨測持有 redirect
        redirect_patch_set.deactivate(redirect_ctx)

    try:
        yield {"task_id": task_id, "module": "factor_returns"}
    finally:
        if original is not None:
            with ic_analysis_service._lock:
                ic_analysis_service._tasks[task_id] = original


def test_export_csv_summary_200(export_task: dict) -> None:
    response = client.get(f"/api/v1/ic/export/{export_task['task_id']}/csv_summary")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")


def test_export_csv_detailed_factor_return(export_task: dict) -> None:
    response = client.get(
        f"/api/v1/ic/export/{export_task['task_id']}/csv_detailed?module={export_task['module']}"
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    # IC1C-FR-STOPGAP: CSV 不得洩漏注入的有限 long_short_mean_return(0.03)
    body = response.content.decode("utf-8")
    assert "0.03" not in body


def test_export_ai_json_200(export_task: dict) -> None:
    response = client.get(f"/api/v1/ic/export/{export_task['task_id']}/ai_json")
    assert response.status_code == 200
    payload = response.json()
    assert "interpretation_guide" in payload


def test_export_markdown_200(export_task: dict) -> None:
    response = client.get(f"/api/v1/ic/export/{export_task['task_id']}/markdown")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")


def test_export_hdf5_200(export_task: dict) -> None:
    response = client.get(f"/api/v1/ic/export/{export_task['task_id']}/hdf5")
    assert response.status_code == 200


def test_export_unknown_task_404() -> None:
    response = client.get("/api/v1/ic/export/unknown-task-id/csv_summary")
    assert response.status_code == 404


def test_export_invalid_format_422(export_task: dict) -> None:
    response = client.get(f"/api/v1/ic/export/{export_task['task_id']}/xlsx")
    assert response.status_code == 422


def test_export_csv_detailed_without_module_422(export_task: dict) -> None:
    response = client.get(f"/api/v1/ic/export/{export_task['task_id']}/csv_detailed")
    assert response.status_code == 422
