"""Phase 2.7 IC deep analysis API tests."""

from __future__ import annotations

import json
import time
from pathlib import Path

import h5py
import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services.ic_analysis_service import ic_analysis_service


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


def _write_features_h5(path: Path, features: np.ndarray, timestamps: np.ndarray, names: list[str]) -> None:
    with h5py.File(path, "w") as h5_file:
        group = h5_file.create_group("data")
        group.create_dataset("features", data=features, compression="gzip")
        group.create_dataset("timestamps", data=timestamps, compression="gzip")
        str_dtype = h5py.string_dtype(encoding="utf-8")
        group.create_dataset("feature_names", data=np.array(names, dtype=object), dtype=str_dtype)


def _write_labels_h5(path: Path, labels: np.ndarray, timestamps: np.ndarray, names: list[str]) -> None:
    with h5py.File(path, "w") as h5_file:
        group = h5_file.create_group("data")
        group.create_dataset("labels", data=labels, compression="gzip")
        group.create_dataset("timestamps", data=timestamps, compression="gzip")
        str_dtype = h5py.string_dtype(encoding="utf-8")
        group.create_dataset("label_names", data=np.array(names, dtype=object), dtype=str_dtype)


def _write_meta_json(path: Path, feature_names: list[str]) -> None:
    payload = {
        "symbol": "TESTUSDT",
        "timeframe": "12h",
        "case_id": "ic_deep_api_test",
    }
    for idx, name in enumerate(feature_names):
        payload[name] = {
            "name": name,
            "category": "momentum" if idx % 2 == 0 else "volatility",
            "layer": 1,
            "data_source": "close",
            "family": "test_family",
        }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
    start = time.time()
    while time.time() - start < timeout:
        response = client.get(f"/api/v1/ic/deep-analysis/{task_id}/result")
        assert response.status_code == 200
        data = response.json()
        if data.get("status") in {"completed", "failed"}:
            return data
        if data.get("results") is not None:
            return data
        time.sleep(0.5)
    pytest.fail("deep analysis timeout")


@pytest.fixture(autouse=True)
def reset_rate_limit() -> None:
    _reset_rate_limit_state()


@pytest.fixture(scope="module")
def sample_paths(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    temp_dir = tmp_path_factory.mktemp("ic_deep_api")
    features_path = temp_dir / "features.h5"
    labels_path = temp_dir / "labels.h5"
    meta_path = temp_dir / "meta.json"

    rng = np.random.default_rng(7)
    n_samples = 140
    n_features = 8
    features = rng.normal(size=(n_samples, n_features)).astype(np.float32)
    labels = rng.normal(size=(n_samples, 1)).astype(np.float32)
    timestamps = np.arange(n_samples, dtype=np.int64)
    feature_names = [f"feature_{i}" for i in range(n_features)]

    _write_features_h5(features_path, features, timestamps, feature_names)
    _write_labels_h5(labels_path, labels, timestamps, ["label"])
    _write_meta_json(meta_path, feature_names)

    return {
        "features_path": str(features_path),
        "labels_path": str(labels_path),
        "meta_path": str(meta_path),
        "feature_names": feature_names,
    }


def _build_completed_ic_task(sample_paths: dict[str, str]) -> str:
    request_data = {
        "features_path": sample_paths["features_path"],
        "labels_path": sample_paths["labels_path"],
        "meta_path": sample_paths["meta_path"],
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


def test_feature_list(sample_paths: dict[str, str]) -> None:
    response = client.get(
        "/api/v1/ic/features/list",
        params={
            "features_path": sample_paths["features_path"],
            "meta_path": sample_paths["meta_path"],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == len(sample_paths["feature_names"])


def test_deep_analysis_start(completed_ic_task: str) -> None:
    response = client.post(
        f"/api/v1/ic/deep-analysis/{completed_ic_task}",
        json={"top_n": 3},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("status") in {"started", "running"}


def test_deep_analysis_result(completed_ic_task: str) -> None:
    start_response = client.post(
        f"/api/v1/ic/deep-analysis/{completed_ic_task}",
        json={"top_n": 3},
    )
    assert start_response.status_code in {200, 400}

    result = _wait_for_deep_result(completed_ic_task)
    assert result.get("results") is not None
    assert result.get("summary") is not None


def test_full_analysis(sample_paths: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/ic/full-analysis",
        json={
            "features_path": sample_paths["features_path"],
            "labels_path": sample_paths["labels_path"],
            "meta_path": sample_paths["meta_path"],
            "deep_analysis": False,
        },
    )
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    _wait_for_task_completed(task_id)

    result_response = client.get(f"/api/v1/ic/result/{task_id}")
    assert result_response.status_code == 200
    assert "summary_table" in result_response.json()


def test_deep_analysis_result_serializes_numpy_scalars(completed_ic_task: str) -> None:
    with ic_analysis_service._lock:
        task_info = ic_analysis_service._tasks.get(completed_ic_task)
        assert task_info is not None
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

    response = client.get(f"/api/v1/ic/deep-analysis/{completed_ic_task}/result")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_modules"] == 10
    assert payload["summary"]["completed_count"] == 1
    assert payload["results"]["results"]["factor_returns"]["feature_0"]["samples"] == 128
