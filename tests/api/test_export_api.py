import json
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


client = TestClient(app)

pytestmark = [
    pytest.mark.ic_persist_redirect,
    pytest.mark.usefixtures("ic_persist_redirect"),
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


def _write_features_h5(path: Path, features: np.ndarray, timestamps: np.ndarray, names: list[str]) -> None:
    with h5py.File(path, "w") as file:
        group = file.create_group("data")
        group.create_dataset("features", data=features, compression="gzip")
        group.create_dataset("timestamps", data=timestamps, compression="gzip")
        str_dtype = h5py.string_dtype(encoding="utf-8")
        group.create_dataset("feature_names", data=np.array(names, dtype=object), dtype=str_dtype)


def _write_labels_h5(path: Path, labels: np.ndarray, timestamps: np.ndarray, names: list[str]) -> None:
    with h5py.File(path, "w") as file:
        group = file.create_group("data")
        group.create_dataset("labels", data=labels, compression="gzip")
        group.create_dataset("timestamps", data=timestamps, compression="gzip")
        str_dtype = h5py.string_dtype(encoding="utf-8")
        group.create_dataset("label_names", data=np.array(names, dtype=object), dtype=str_dtype)


def _write_meta_json(path: Path, feature_names: list[str]) -> None:
    payload = {
        "symbol": "TESTUSDT",
        "timeframe": "12h",
        "case_id": "ic_export_test",
    }
    for name in feature_names:
        payload[name] = {
            "name": name,
            "category": "test",
            "layer": 1,
            "data_source": "close",
        }
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


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
    tmp_path_factory: pytest.TempPathFactory,
    redirect_patch_set,
    redirect_root_session: Path,
) -> dict:
    redirect_ctx = redirect_patch_set.activate(redirect_root_session, owner="export_task")
    try:
        temp_dir = tmp_path_factory.mktemp("ic_export")
        features_path = temp_dir / "features.h5"
        labels_path = temp_dir / "labels.h5"
        meta_path = temp_dir / "meta.json"

        rng = np.random.default_rng(7)
        n_samples = 180
        n_features = 8
        features = rng.normal(size=(n_samples, n_features)).astype(np.float32)
        labels = rng.normal(size=(n_samples, 1)).astype(np.float32)
        timestamps = np.arange(n_samples, dtype=np.int64)
        feature_names = [f"feature_{i}" for i in range(n_features)]

        _write_features_h5(features_path, features, timestamps, feature_names)
        _write_labels_h5(labels_path, labels, timestamps, ["label"])
        _write_meta_json(meta_path, feature_names)

        analyze_payload = {
            "features_path": str(features_path),
            "labels_path": str(labels_path),
            "meta_path": str(meta_path),
            "config_override": {
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

        analyze_response = client.post("/api/v1/ic/analyze", json=analyze_payload)
        assert analyze_response.status_code == 200
        task_id = analyze_response.json()["task_id"]
        _wait_for_task(task_id)

        with ic_analysis_service._lock:
            task_info = ic_analysis_service._tasks.get(task_id)
            if task_info is not None:
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
                "features", data=np.array([[1.0, 2.0]], dtype=np.float32)
            )

        return {"task_id": task_id, "module": "factor_returns"}
    finally:
        assert not redirect_ctx.spy.violations
        redirect_patch_set.deactivate(redirect_ctx)


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
