"""IC analysis API tests."""

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


client = TestClient(app)

pytestmark = [
    pytest.mark.ic_persist_redirect,
    pytest.mark.usefixtures("ic_persist_redirect"),
]


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
        "case_id": "ic_api_test",
    }
    for name in feature_names:
        payload[name] = {
            "name": name,
            "category": "test",
            "layer": 1,
            "data_source": "close",
        }
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


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


def _build_ic_analysis_task(tmp_path_factory: pytest.TempPathFactory) -> dict:
    temp_dir = tmp_path_factory.mktemp("ic_api")
    features_path = temp_dir / "features.h5"
    labels_path = temp_dir / "labels.h5"
    meta_path = temp_dir / "meta.json"

    rng = np.random.default_rng(42)
    n_samples = 120
    n_features = 6
    features = rng.normal(size=(n_samples, n_features)).astype(np.float32)
    labels = rng.normal(size=(n_samples, 1)).astype(np.float32)
    timestamps = np.arange(n_samples, dtype=np.int64)
    feature_names = [f"feature_{i}" for i in range(n_features)]

    _write_features_h5(features_path, features, timestamps, feature_names)
    _write_labels_h5(labels_path, labels, timestamps, ["label"])
    _write_meta_json(meta_path, feature_names)

    request_data = {
        "features_path": str(features_path),
        "labels_path": str(labels_path),
        "meta_path": str(meta_path),
        "config_override": {
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

    response = client.post("/api/v1/ic/analyze", json=request_data)
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    _wait_for_task(task_id)

    return {"task_id": task_id, "feature_names": feature_names}


@pytest.fixture(scope="session")
def ic_analysis_task(
    tmp_path_factory: pytest.TempPathFactory,
    redirect_patch_set,
    redirect_root_session: Path,
) -> dict:
    ctx = redirect_patch_set.activate(redirect_root_session, owner="ic_analysis_task")
    try:
        return _build_ic_analysis_task(tmp_path_factory)
    finally:
        assert not ctx.spy.violations
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


def test_ic_export_csv(ic_analysis_task: dict) -> None:
    task_id = ic_analysis_task["task_id"]
    response = client.get(f"/api/v1/ic/export-csv/{task_id}")
    assert response.status_code == 200


def test_ic_export_hdf5(ic_analysis_task: dict) -> None:
    task_id = ic_analysis_task["task_id"]
    response = client.get(f"/api/v1/ic/export/{task_id}")
    assert response.status_code == 200
