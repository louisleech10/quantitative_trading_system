from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pytest

from api.services.feature_browser_service import FeatureBrowserService


def _write_sample_feature_h5(path: Path, rows: int = 300, cols: int = 16) -> None:
    rng = np.random.default_rng(42)
    data = rng.normal(size=(rows, cols)).astype(np.float64)
    data[:, 0] = np.linspace(0.0, 2.0, rows)
    data[:, 1] = np.sin(np.linspace(0, 10, rows))
    data[::9, 2] = np.nan
    names = np.array([f"feature_{idx}" for idx in range(cols)], dtype=object)
    timestamps = np.arange(rows, dtype=np.int64)

    with h5py.File(path, "w") as h5_file:
        group = h5_file.create_group("data")
        group.create_dataset("features", data=data)
        group.create_dataset("feature_names", data=names, dtype=h5py.string_dtype(encoding="utf-8"))
        group.create_dataset("timestamps", data=timestamps)


@pytest.fixture(scope="module")
def sample_h5(tmp_path_factory: pytest.TempPathFactory) -> str:
    file_path = tmp_path_factory.mktemp("feature_browser_service") / "sample_features.h5"
    _write_sample_feature_h5(file_path)
    return str(file_path)


@pytest.fixture(scope="module")
def service() -> FeatureBrowserService:
    return FeatureBrowserService()


def test_get_overview(service: FeatureBrowserService, sample_h5: str) -> None:
    payload = service.get_overview(sample_h5)
    assert payload["total_features"] == 16
    assert len(payload["items"]) == 16


def test_get_ic_dashboard(service: FeatureBrowserService, sample_h5: str) -> None:
    payload = service.get_ic_dashboard(sample_h5, top_k=10)
    assert "available" in payload
    assert "entries" in payload


def test_get_rolling_ic(service: FeatureBrowserService, sample_h5: str) -> None:
    payload = service.get_rolling_ic(sample_h5, "feature_1", window=40)
    assert payload["feature_name"] == "feature_1"
    assert "points" in payload


def test_get_quality_scorecard(service: FeatureBrowserService, sample_h5: str) -> None:
    payload = service.get_quality_scorecard(sample_h5, top_k=50)
    assert "items" in payload
    assert "funnel" in payload


def test_get_correlation_matrix_truncation(service: FeatureBrowserService, sample_h5: str) -> None:
    payload = service.get_correlation_matrix(sample_h5, method="spearman", max_features=5)
    assert payload["original_feature_count"] >= 5
    assert len(payload["features"]) == 5


def test_get_vif(service: FeatureBrowserService, sample_h5: str) -> None:
    payload = service.get_vif(sample_h5, max_features=10)
    assert len(payload["items"]) > 0


def test_get_drift_monitor(service: FeatureBrowserService, sample_h5: str) -> None:
    payload = service.get_drift_monitor(sample_h5, max_features=20)
    assert "items" in payload


def test_get_shap_summary(service: FeatureBrowserService, sample_h5: str) -> None:
    payload = service.get_shap_summary(sample_h5, top_k=8)
    assert payload["available"] in {True, False}
    assert "items" in payload


def test_get_importance_comparison(service: FeatureBrowserService, sample_h5: str) -> None:
    payload = service.get_importance_comparison(sample_h5, top_k=10)
    assert len(payload["items"]) <= 10


def test_missing_file_raises(service: FeatureBrowserService) -> None:
    with pytest.raises(FileNotFoundError):
        service.get_overview("/tmp/does_not_exist.h5")
