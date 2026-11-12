from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.core.background_jobs import BackgroundJobStore
from api.main import app
from api.services.feature_browser_service import feature_browser_service
from momentum.FeatureEngineering.feature_storage import FeatureStorage


client = TestClient(app)


@pytest.fixture(autouse=True)
def _tmp_job_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BackgroundJobStore:
    """ICPERF Task 0.6 L1c：三端點改背景任務；任務紀錄寫於 tmp（不落正式 data_cache）。"""
    store = BackgroundJobStore(tmp_path / "jobs")
    monkeypatch.setattr(feature_browser_service, "job_store", store)
    return store


def _task_result(response: Any) -> Dict[str, Any]:
    """POST 回 task_id ⇒ 等任務終態（Event，無逾時）⇒ 讀結果端點。"""
    task_id = response.json()["task_id"]
    final = feature_browser_service.job_store.wait(task_id)
    assert final["state"] == "completed", final
    result = client.get(f"/api/v1/feature-browser/tasks/{task_id}/result")
    assert result.status_code == 200, result.text[:300]
    return result.json()



def test_coverage_matrix_endpoint_200(tmp_path: Path) -> None:
    feature_base = tmp_path / "feature_matrix"
    feature_base.mkdir()

    _write_v2_raw_fixture(
        feature_base,
        symbol="BTCUSDT",
        timeframe="12h",
        config_hash="cfg_route_matrix",
        raw_groups={
            "group_alpha": pd.DataFrame(
                {
                    "feature_a": np.array([1.0, 2.0], dtype=np.float32),
                    "feature_b": np.array([np.nan, 3.0], dtype=np.float32),
                }
            )
        },
    )
    _write_v2_raw_fixture(
        feature_base,
        symbol="ETHUSDT",
        timeframe="12h",
        config_hash="cfg_route_matrix",
        raw_groups={
            "group_alpha": pd.DataFrame(
                {
                    "feature_a": np.array([1.0, 2.0], dtype=np.float32),
                    "feature_b": np.array([2.0, 3.0], dtype=np.float32),
                }
            )
        },
    )

    response = client.post(
        "/api/v1/feature-browser/coverage-matrix",
        json={
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframe": "12h",
            "feature_names": ["feature_a", "feature_b"],
            "feature_base_path": str(feature_base),
        },
    )

    assert response.status_code == 200
    payload = _task_result(response)
    assert payload["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert "matrix" in payload
    assert "summary" in payload
    assert payload["matrix"]["feature_b"]["BTCUSDT"] == 0.5


def test_coverage_matrix_requires_at_least_two_symbols(tmp_path: Path) -> None:
    feature_base = tmp_path / "feature_matrix_400"
    feature_base.mkdir()


    response = client.post(
        "/api/v1/feature-browser/coverage-matrix",
        json={
            "symbols": ["BTCUSDT"],
            "timeframe": "12h",
            "feature_names": ["feature_a"],
            "feature_base_path": str(feature_base),
        },
    )

    assert response.status_code == 400


def _write_v2_raw_fixture(
    feature_base: Path,
    *,
    symbol: str,
    timeframe: str,
    config_hash: str,
    raw_groups: dict[str, pd.DataFrame],
) -> None:
    storage = FeatureStorage(str(feature_base))
    storage.write_raw(symbol, timeframe, config_hash, raw_groups)


def test_group_coverage_endpoint_200(tmp_path: Path) -> None:
    feature_base = tmp_path / "group_coverage"
    feature_base.mkdir()
    _write_v2_raw_fixture(
        feature_base,
        symbol="BTCUSDT",
        timeframe="12h",
        config_hash="cfg_route",
        raw_groups={"group_alpha": pd.DataFrame({"feature_a": np.array([1.0, 2.0], dtype=np.float32)})},
    )
    _write_v2_raw_fixture(
        feature_base,
        symbol="ETHUSDT",
        timeframe="12h",
        config_hash="cfg_route",
        raw_groups={
            "group_alpha": pd.DataFrame(
                {"feature_a": np.array([1.0, np.nan], dtype=np.float32)}
            )
        },
    )

    response = client.post(
        "/api/v1/feature-browser/group-coverage",
        json={
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframe": "12h",
            "feature_base_path": str(feature_base),
        },
    )

    assert response.status_code == 200
    payload = _task_result(response)
    assert payload["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert "groups" in payload
    assert "matrix" in payload
    assert "divergence" in payload
    assert "summary" in payload


def test_group_feature_coverage_endpoint_200(tmp_path: Path) -> None:
    feature_base = tmp_path / "group_feature_coverage"
    feature_base.mkdir()
    _write_v2_raw_fixture(
        feature_base,
        symbol="BTCUSDT",
        timeframe="12h",
        config_hash="cfg_route_feat",
        raw_groups={"group_alpha": pd.DataFrame({"feature_a": np.array([1.0, 2.0], dtype=np.float32)})},
    )
    _write_v2_raw_fixture(
        feature_base,
        symbol="ETHUSDT",
        timeframe="12h",
        config_hash="cfg_route_feat",
        raw_groups={
            "group_alpha": pd.DataFrame(
                {"feature_a": np.array([1.0, np.nan], dtype=np.float32)}
            )
        },
    )

    response = client.post(
        "/api/v1/feature-browser/group-feature-coverage",
        json={
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframe": "12h",
            "group_name": "group_alpha",
            "feature_base_path": str(feature_base),
        },
    )

    assert response.status_code == 200
    payload = _task_result(response)
    assert payload["group_name"] == "group_alpha"
    assert "features" in payload
    assert "matrix" in payload
    assert payload["symbols"] == ["BTCUSDT", "ETHUSDT"]
