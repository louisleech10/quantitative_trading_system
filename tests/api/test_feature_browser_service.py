from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pytest

from api.services.feature_browser_service import FeatureBrowserService
from momentum.Analysis.coverage_analyzer import CoverageAnalyzer
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.factories import create_feature_reader


def _write_symbol_feature_h5(path: Path, data: np.ndarray, feature_names: list[str]) -> None:
    with h5py.File(path, "w") as h5_file:
        group = h5_file.create_group("data")
        group.create_dataset("features", data=data)
        group.create_dataset(
            "feature_names",
            data=np.array(feature_names, dtype=object),
            dtype=h5py.string_dtype(encoding="utf-8"),
        )


@pytest.fixture(scope="module")
def service() -> FeatureBrowserService:
    return FeatureBrowserService()


def test_get_coverage_matrix(service: FeatureBrowserService, tmp_path: Path) -> None:
    feature_base = tmp_path / "features"
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

    payload = service.get_coverage_matrix(
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="12h",
        feature_names=["feature_a", "feature_b"],
        feature_base_path=str(feature_base),
    )

    assert payload["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert payload["features"] == ["feature_a", "feature_b"]
    assert np.isclose(payload["matrix"]["feature_a"]["BTCUSDT"], 0.0)
    assert np.isclose(payload["matrix"]["feature_b"]["BTCUSDT"], 0.5)
    assert payload["summary"]["worst_symbol"] == "BTCUSDT"


def test_coverage_matrix_requires_two_symbols(service: FeatureBrowserService) -> None:
    with pytest.raises(ValueError):
        service.get_coverage_matrix(symbols=["BTCUSDT"], timeframe="12h")


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


@pytest.fixture(scope="module")
def analyzer() -> CoverageAnalyzer:
    return CoverageAnalyzer(feature_reader_factory=create_feature_reader)


def test_v2_layout_loads(analyzer: CoverageAnalyzer, tmp_path: Path) -> None:
    feature_base = tmp_path / "features"
    _write_v2_raw_fixture(
        feature_base,
        symbol="BTCUSDT",
        timeframe="12h",
        config_hash="cfg_v2_a",
        raw_groups={
            "group_alpha": pd.DataFrame(
                {
                    "feature_a": np.array([1.0, 2.0], dtype=np.float32),
                    "feature_b": np.array([3.0, 4.0], dtype=np.float32),
                }
            )
        },
    )

    frame = analyzer._load_symbol_features("BTCUSDT", "12h", str(feature_base))
    assert frame is not None
    assert not frame.empty
    assert set(frame.columns) == {"feature_a", "feature_b"}


def test_group_coverage_from_manifest(analyzer: CoverageAnalyzer, tmp_path: Path) -> None:
    feature_base = tmp_path / "features"
    rows = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)

    _write_v2_raw_fixture(
        feature_base,
        symbol="BTCUSDT",
        timeframe="12h",
        config_hash="cfg_grp",
        raw_groups={"group_alpha": pd.DataFrame({"feature_a": rows})},
    )
    _write_v2_raw_fixture(
        feature_base,
        symbol="ETHUSDT",
        timeframe="12h",
        config_hash="cfg_grp",
        raw_groups={
            "group_alpha": pd.DataFrame(
                {"feature_a": np.array([1.0, np.nan, 3.0, np.nan], dtype=np.float32)}
            )
        },
    )

    payload = analyzer.compute_group_coverage_matrix(
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="12h",
        feature_base_path=str(feature_base),
    )

    assert payload["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert "group_alpha" in payload["groups"]
    assert np.isclose(payload["matrix"]["group_alpha"]["BTCUSDT"], 1.0)
    assert np.isclose(payload["matrix"]["group_alpha"]["ETHUSDT"], 0.5)
    assert payload["divergence"]["group_alpha"] > 0.0
    assert payload["groups"][0] == "group_alpha"


def test_group_drilldown_per_feature(analyzer: CoverageAnalyzer, tmp_path: Path) -> None:
    feature_base = tmp_path / "features"
    rows = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)

    _write_v2_raw_fixture(
        feature_base,
        symbol="BTCUSDT",
        timeframe="12h",
        config_hash="cfg_drill",
        raw_groups={
            "group_alpha": pd.DataFrame(
                {
                    "feature_a": rows,
                    "feature_b": np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32),
                }
            )
        },
    )
    _write_v2_raw_fixture(
        feature_base,
        symbol="ETHUSDT",
        timeframe="12h",
        config_hash="cfg_drill",
        raw_groups={
            "group_alpha": pd.DataFrame(
                {
                    "feature_a": np.array([1.0, np.nan, 3.0, np.nan], dtype=np.float32),
                    "feature_b": np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32),
                }
            )
        },
    )

    payload = analyzer.compute_group_feature_coverage(
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="12h",
        group_name="group_alpha",
        feature_base_path=str(feature_base),
        top_n=100,
    )

    assert set(payload["features"]) <= {"feature_a", "feature_b"}
    assert np.isclose(payload["matrix"]["feature_a"]["BTCUSDT"], 1.0)
    assert np.isclose(payload["matrix"]["feature_a"]["ETHUSDT"], 0.5)
    divergences = [payload["divergence"][name] for name in payload["features"]]
    assert divergences == sorted(divergences, reverse=True)


def test_group_drilldown_unknown_group(analyzer: CoverageAnalyzer, tmp_path: Path) -> None:
    feature_base = tmp_path / "features"
    _write_v2_raw_fixture(
        feature_base,
        symbol="BTCUSDT",
        timeframe="12h",
        config_hash="cfg_missing",
        raw_groups={"group_alpha": pd.DataFrame({"feature_a": np.array([1.0, 2.0], dtype=np.float32)})},
    )
    _write_v2_raw_fixture(
        feature_base,
        symbol="ETHUSDT",
        timeframe="12h",
        config_hash="cfg_missing",
        raw_groups={"group_alpha": pd.DataFrame({"feature_a": np.array([1.0, 2.0], dtype=np.float32)})},
    )

    with pytest.raises(ValueError, match="group not found"):
        analyzer.compute_group_feature_coverage(
            symbols=["BTCUSDT", "ETHUSDT"],
            timeframe="12h",
            group_name="group_missing",
            feature_base_path=str(feature_base),
        )


def test_get_group_coverage_service(service: FeatureBrowserService, tmp_path: Path) -> None:
    feature_base = tmp_path / "features"
    _write_v2_raw_fixture(
        feature_base,
        symbol="BTCUSDT",
        timeframe="12h",
        config_hash="cfg_svc",
        raw_groups={"group_alpha": pd.DataFrame({"feature_a": np.array([1.0, 2.0], dtype=np.float32)})},
    )
    _write_v2_raw_fixture(
        feature_base,
        symbol="ETHUSDT",
        timeframe="12h",
        config_hash="cfg_svc",
        raw_groups={
            "group_alpha": pd.DataFrame(
                {"feature_a": np.array([1.0, np.nan], dtype=np.float32)}
            )
        },
    )

    payload = service.get_group_coverage(
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="12h",
        feature_base_path=str(feature_base),
    )
    assert payload["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert "group_alpha" in payload["matrix"]
