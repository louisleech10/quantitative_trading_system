from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def _write_sample_feature_h5(path: Path, rows: int = 320, cols: int = 12) -> None:
    rng = np.random.default_rng(42)
    data = rng.normal(size=(rows, cols)).astype(np.float64)
    data[:, 0] = np.linspace(0.0, 1.0, rows)
    data[::11, 3] = np.nan
    names = np.array([f"feature_{idx}" for idx in range(cols)], dtype=object)
    timestamps = np.arange(rows, dtype=np.int64)

    with h5py.File(path, "w") as h5_file:
        group = h5_file.create_group("data")
        group.create_dataset("features", data=data)
        group.create_dataset("feature_names", data=names, dtype=h5py.string_dtype(encoding="utf-8"))
        group.create_dataset("timestamps", data=timestamps)


@pytest.fixture(scope="module")
def sample_h5(tmp_path_factory: pytest.TempPathFactory) -> str:
    file_path = tmp_path_factory.mktemp("feature_browser_v2") / "sample_features.h5"
    _write_sample_feature_h5(file_path)
    return str(file_path)


def test_overview_endpoint_200(sample_h5: str) -> None:
    response = client.get("/api/v1/feature-browser/overview", params={"features_path": sample_h5})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_features"] == 12


def test_distribution_endpoint_200(sample_h5: str) -> None:
    response = client.get(
        "/api/v1/feature-browser/distribution/feature_0",
        params={"features_path": sample_h5, "bins": 40},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["feature_name"] == "feature_0"


def test_ic_dashboard_endpoint_200(sample_h5: str) -> None:
    response = client.get("/api/v1/feature-browser/ic-dashboard", params={"features_path": sample_h5})
    assert response.status_code == 200
    payload = response.json()
    assert "available" in payload
    assert "entries" in payload


def test_rolling_ic_endpoint_200(sample_h5: str) -> None:
    response = client.get(
        "/api/v1/feature-browser/rolling-ic/feature_1",
        params={"features_path": sample_h5, "window": 40},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["feature_name"] == "feature_1"


def test_quality_scorecard_endpoint_200(sample_h5: str) -> None:
    response = client.get(
        "/api/v1/feature-browser/quality-scorecard",
        params={"features_path": sample_h5},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert "funnel" in payload


def test_correlation_matrix_endpoint_200(sample_h5: str) -> None:
    response = client.get(
        "/api/v1/feature-browser/correlation-matrix",
        params={"features_path": sample_h5, "max_features": 20},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "matrix" in payload
    assert "features" in payload


def test_vif_endpoint_200(sample_h5: str) -> None:
    response = client.get("/api/v1/feature-browser/vif", params={"features_path": sample_h5})
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload


def test_drift_monitor_endpoint_200(sample_h5: str) -> None:
    response = client.get("/api/v1/feature-browser/drift-monitor", params={"features_path": sample_h5})
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload


def test_shap_summary_endpoint_200(sample_h5: str) -> None:
    response = client.get("/api/v1/feature-browser/shap-summary", params={"features_path": sample_h5})
    assert response.status_code == 200
    payload = response.json()
    assert "available" in payload
    assert "items" in payload


def test_importance_comparison_endpoint_200(sample_h5: str) -> None:
    response = client.get("/api/v1/feature-browser/importance-comparison", params={"features_path": sample_h5})
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload


def test_overview_missing_path_404() -> None:
    response = client.get("/api/v1/feature-browser/overview", params={"features_path": "/tmp/does_not_exist.h5"})
    assert response.status_code == 404


def test_distribution_unknown_feature_404(sample_h5: str) -> None:
    response = client.get(
        "/api/v1/feature-browser/distribution/not_exists",
        params={"features_path": sample_h5},
    )
    assert response.status_code == 404
