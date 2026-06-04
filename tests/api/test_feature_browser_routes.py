from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from api.main import app
from momentum.FeatureEngineering.feature_storage import FeatureStorage


client = TestClient(app)


def _write_symbol_feature_h5(path: Path, data: np.ndarray, feature_names: list[str]) -> None:
    with h5py.File(path, "w") as h5_file:
        group = h5_file.create_group("data")
        group.create_dataset("features", data=data)
        group.create_dataset(
            "feature_names",
            data=np.array(feature_names, dtype=object),
            dtype=h5py.string_dtype(encoding="utf-8"),
        )


def test_coverage_matrix_endpoint_200(tmp_path: Path) -> None:
    feature_base = tmp_path / "feature_matrix"
    feature_base.mkdir()

    _write_symbol_feature_h5(
        feature_base / "BTCUSDT_12h_factory.h5",
        np.array([[1.0, np.nan], [2.0, 3.0]], dtype=float),
        ["feature_a", "feature_b"],
    )
    _write_symbol_feature_h5(
        feature_base / "ETHUSDT_12h_factory.h5",
        np.array([[1.0, 2.0], [2.0, 3.0]], dtype=float),
        ["feature_a", "feature_b"],
    )

    response = client.post(
        "/api/v1/feature-browser/coverage-matrix",
        json={
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframe": "12h",
            "feature_names": ["feature_a", "feature_b"],
            "feature_base_path": str(feature_base),
            "timeout_seconds": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert "matrix" in payload
    assert "summary" in payload


def test_coverage_matrix_requires_at_least_two_symbols(tmp_path: Path) -> None:
    feature_base = tmp_path / "feature_matrix_400"
    feature_base.mkdir()

    _write_symbol_feature_h5(
        feature_base / "BTCUSDT_12h_factory.h5",
        np.array([[1.0], [2.0]], dtype=float),
        ["feature_a"],
    )

    response = client.post(
        "/api/v1/feature-browser/coverage-matrix",
        json={
            "symbols": ["BTCUSDT"],
            "timeframe": "12h",
            "feature_names": ["feature_a"],
            "feature_base_path": str(feature_base),
            "timeout_seconds": 10,
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
            "timeout_seconds": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
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
            "top_n": 50,
            "timeout_seconds": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["group_name"] == "group_alpha"
    assert "features" in payload
    assert "matrix" in payload
    assert payload["symbols"] == ["BTCUSDT", "ETHUSDT"]
