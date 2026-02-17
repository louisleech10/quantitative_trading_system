from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def _write_sample_feature_h5(path: Path, rows: int = 240, cols: int = 8) -> None:
    rng = np.random.default_rng(42)
    data = rng.normal(size=(rows, cols)).astype(np.float64)
    data[:, 0] = np.linspace(0.0, 2.0, rows)
    data[::10, 1] = np.nan
    names = np.array([f"feature_{idx}" for idx in range(cols)], dtype=object)
    timestamps = np.arange(rows, dtype=np.int64)

    with h5py.File(path, "w") as h5_file:
        group = h5_file.create_group("data")
        group.create_dataset("features", data=data)
        group.create_dataset("feature_names", data=names, dtype=h5py.string_dtype(encoding="utf-8"))
        group.create_dataset("timestamps", data=timestamps)


@pytest.fixture(scope="module")
def sample_h5(tmp_path_factory: pytest.TempPathFactory) -> str:
    file_path = tmp_path_factory.mktemp("feature_browser") / "sample_features.h5"
    _write_sample_feature_h5(file_path)
    return str(file_path)


def test_catalog_returns_all_features(sample_h5: str) -> None:
    response = client.get("/api/v1/features/catalog", params={"features_path": sample_h5})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 8


def test_catalog_includes_statistics(sample_h5: str) -> None:
    response = client.get("/api/v1/features/catalog", params={"features_path": sample_h5})
    payload = response.json()
    assert "summary" in payload
    assert payload["summary"]["total_features"] == 8


def test_catalog_unknown_path_404() -> None:
    response = client.get("/api/v1/features/catalog", params={"features_path": "/not/exist/sample.h5"})
    assert response.status_code == 404


def test_distribution_50_bins(sample_h5: str) -> None:
    response = client.get(
        "/api/v1/features/feature_0/distribution",
        params={"features_path": sample_h5, "bins": 50},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["bins"] == 50
    assert len(payload["histogram"]) == 50


def test_distribution_statistics_correct(sample_h5: str) -> None:
    response = client.get(
        "/api/v1/features/feature_0/distribution",
        params={"features_path": sample_h5, "bins": 20},
    )
    payload = response.json()
    assert payload["statistics"]["mean"] is not None
    assert payload["statistics"]["std"] is not None


def test_distribution_unknown_feature_404(sample_h5: str) -> None:
    response = client.get(
        "/api/v1/features/unknown/distribution",
        params={"features_path": sample_h5, "bins": 20},
    )
    assert response.status_code == 404


def test_timeseries_single_feature(sample_h5: str) -> None:
    response = client.get(
        "/api/v1/features/time-series",
        params={"features_path": sample_h5, "features": "feature_0"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["features"] == ["feature_0"]
    assert len(payload["points"]) > 0


def test_timeseries_multiple_features(sample_h5: str) -> None:
    response = client.get(
        "/api/v1/features/time-series",
        params={"features_path": sample_h5, "features": "feature_0,feature_2,feature_3"},
    )
    payload = response.json()
    assert payload["features"] == ["feature_0", "feature_2", "feature_3"]


def test_timeseries_sample_rate(sample_h5: str) -> None:
    response = client.get(
        "/api/v1/features/time-series",
        params={"features_path": sample_h5, "features": "feature_0", "sample_rate": 4},
    )
    payload = response.json()
    assert payload["sample_rate"] == 4


def test_correlation_spearman_default(sample_h5: str) -> None:
    response = client.get(
        "/api/v1/features/correlation",
        params={"features_path": sample_h5, "features": "feature_0,feature_1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["method"] == "spearman"
    assert len(payload["matrix"]) == 2


def test_correlation_max_features_limit(sample_h5: str) -> None:
    response = client.get(
        "/api/v1/features/correlation",
        params={"features_path": sample_h5, "max_features": 2},
    )
    payload = response.json()
    assert len(payload["features"]) <= 2


def test_quality_check_runs_adf(sample_h5: str) -> None:
    response = client.post(
        "/api/v1/features/quality-check",
        json={"features_path": sample_h5},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) > 0


def test_quality_check_selected_features(sample_h5: str) -> None:
    response = client.post(
        "/api/v1/features/quality-check",
        json={"features_path": sample_h5, "selected_features": ["feature_0", "feature_2"]},
    )
    payload = response.json()
    assert {item["feature"] for item in payload["results"]} == {"feature_0", "feature_2"}


def test_data_table_pagination(sample_h5: str) -> None:
    response = client.get(
        "/api/v1/features/data-table",
        params={"features_path": sample_h5, "page": 2, "page_size": 100},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 2
    assert len(payload["rows"]) == 100


def test_data_table_column_selection(sample_h5: str) -> None:
    response = client.get(
        "/api/v1/features/data-table",
        params={"features_path": sample_h5, "columns": "feature_0,feature_1", "page_size": 10},
    )
    payload = response.json()
    assert payload["columns"] == ["timestamp", "feature_0", "feature_1"]
    assert len(payload["rows"]) == 10
