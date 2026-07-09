from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path

import pandas as pd
import pytest

from momentum.factories import create_feature_factory, create_kline_storage_manager
from momentum.FeatureEngineering.atomic.microstructure_indicators import MicrostructureIndicatorEngine
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.core.contracts import LayerStatus


TEST_KLINE_CACHE_DIR = "data_cache/feature_klines"


def _base_pipeline_override() -> dict:
    return {
        "atomic_indicators": {
            "trend": {"enabled": False},
            "momentum": {"enabled": False},
            "volatility": {"enabled": False},
            "volume": {"enabled": False},
            "cycle": {"enabled": False},
            "pattern": {"enabled": False},
            "statistics": {"enabled": False},
            "microstructure": {"enabled": False},
            "entropy": {"enabled": False},
            "tail_risk": {"enabled": False},
        },
        "operators": {
            "distance": {"enabled": False},
            "cross": {"enabled": False},
            "momentum": {"enabled": False},
            "ratio": {"enabled": False},
            "binary_signal": {"enabled": False},
            "worldquant": {"enabled": False},
        },
        "rolling_aggregation": {"enabled": False},
        "lag_features": {"enabled": False},
        "cross_sectional": {"enabled": False},
        "meta_features": {"enabled": False},
        "preprocessing": {"enabled": False},
    }


@lru_cache(maxsize=1)
def _resolve_test_target() -> tuple[str, str]:
    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    candidates = [
        ("BTCUSDT", "12h"),
        ("ETHUSDT", "12h"),
        ("ETHUSDT", "1h"),
    ]

    for symbol, timeframe in candidates:
        try:
            data = storage.read_klines(symbol, timeframe)
        except ValueError:
            # Skip discontinuous datasets for this E2E path.
            continue

        if data is not None and not data.empty:
            return symbol, timeframe

    pytest.skip("No available kline dataset for feature factory E2E tests")


def _generate(
    config_override: dict,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    persist: bool = False,
):
    work_dir = tmp_path / "cgsa"
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(work_dir))
    monkeypatch.setenv("FFACT_FEATURE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    factory = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR)
    factory._storage = FeatureStorage(str(tmp_path / "features"))
    factory._registry = FeatureRegistry(tmp_path / "registry.json")
    symbol, timeframe = _resolve_test_target()
    result = factory.generate_features(
        symbol=symbol,
        timeframe=timeframe,
        config_override=config_override,
        force_regenerate=True,
        persist=persist,
    )
    manifest = json.loads(Path(result.metadata["manifest_path"]).read_text(encoding="utf-8"))
    return result, factory, manifest


def _manifest_columns(manifest: dict) -> list[str]:
    """從 CGSA source manifest 或 L7 artifact manifest 讀取 schema 欄位。"""
    groups = manifest.get("groups")
    if groups is None:
        groups = manifest["artifacts"]["raw"]["groups"]
    group_values = groups.values() if isinstance(groups, dict) else groups
    return [str(column) for group in group_values for column in group.get("columns", [])]


def test_pipeline_with_microstructure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _base_pipeline_override()
    config["atomic_indicators"]["microstructure"]["enabled"] = True

    _result, _factory, manifest = _generate(config, tmp_path, monkeypatch)
    ms_columns = [col for col in _manifest_columns(manifest) if col.startswith("ms_")]

    assert manifest["schema_version"] == 2
    assert len(ms_columns) > 0


def test_pipeline_with_entropy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _base_pipeline_override()
    config["atomic_indicators"]["entropy"]["enabled"] = True

    _result, _factory, manifest = _generate(config, tmp_path, monkeypatch)
    ent_columns = [col for col in _manifest_columns(manifest) if col.startswith("ent_")]

    assert len(ent_columns) > 0


def test_pipeline_with_tail_risk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _base_pipeline_override()
    config["atomic_indicators"]["tail_risk"]["enabled"] = True

    _result, _factory, manifest = _generate(config, tmp_path, monkeypatch)
    tr_columns = [col for col in _manifest_columns(manifest) if col.startswith("tr_")]

    assert len(tr_columns) > 0


def test_pipeline_with_preprocessing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """L6.5 預處理設計範圍=Winsor+Fracdiff(2026-07-09 使用者定);rank/zscore/gaussian
    config key 被接受但不生效——本測試釘住此邊界:開啟它們不得產生對應欄位。"""
    config = _base_pipeline_override()
    config["atomic_indicators"]["microstructure"]["enabled"] = True
    config["preprocessing"] = {
        "enabled": True,
        "mode": "append",
        "winsorization": {"enabled": True, "apply_to": "all"},
        "adf_differencing": {"enabled": False},
        "fractional_differencing": {"enabled": False},
        "rank_transform": {"enabled": True, "window": 55, "apply_to": "all"},
        "gaussian_normalize": {"enabled": False},
        "adaptive_zscore": {"enabled": True, "windows": [55], "apply_to": "all", "epsilon": 1e-8},
    }

    result, _factory, manifest = _generate(
        config, tmp_path, monkeypatch, persist=True
    )
    columns = _manifest_columns(manifest)

    assert result.feature_count > 0
    assert any(col.startswith("ms_") for col in columns)
    # L6.5 scope guard:rank/gaussian 不屬 L6.5,開了也不得產預處理欄。
    # 注意:zscore 不能用 substring 守衛——ms_vpin_zscore_* 是 microstructure 指標非 L6.5 產物。
    assert not any(col.endswith("_rank") for col in columns)
    assert not any("_gauss" in col for col in columns)


def test_pipeline_all_new_features(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _base_pipeline_override()
    config["atomic_indicators"]["microstructure"]["enabled"] = True
    config["atomic_indicators"]["entropy"]["enabled"] = True
    config["atomic_indicators"]["tail_risk"]["enabled"] = True
    config["preprocessing"] = {
        "enabled": True,
        "mode": "append",
        "winsorization": {"enabled": True, "apply_to": "all"},
        "adf_differencing": {"enabled": False},
        "fractional_differencing": {"enabled": False},
        "rank_transform": {"enabled": True, "window": 55, "apply_to": "all"},
        "gaussian_normalize": {"enabled": False},
        "adaptive_zscore": {"enabled": True, "windows": [55], "apply_to": "all", "epsilon": 1e-8},
    }

    result, _factory, manifest = _generate(
        config, tmp_path, monkeypatch, persist=True
    )
    columns = _manifest_columns(manifest)

    assert result.feature_count > 0
    assert any(col.startswith("ms_") for col in columns)
    assert any(col.startswith("ent_") for col in columns)
    assert any(col.startswith("tr_") for col in columns)
    assert result.hdf5_path
    assert "validation" in result.metadata


def test_pipeline_backward_compatible(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_a = _base_pipeline_override()
    config_b = deepcopy(_base_pipeline_override())

    result_a, _factory_a, manifest_a = _generate(config_a, tmp_path / "a", monkeypatch)
    result_b, _factory_b, manifest_b = _generate(config_b, tmp_path / "b", monkeypatch)

    assert result_a.features_df.shape == result_b.features_df.shape
    assert list(result_a.features_df.columns) == list(result_b.features_df.columns)
    pd.testing.assert_frame_equal(result_a.features_df, result_b.features_df)
    assert _manifest_columns(manifest_a) == _manifest_columns(manifest_b)


def test_pipeline_partial_engine_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _base_pipeline_override()
    config["atomic_indicators"]["microstructure"]["enabled"] = True
    config["atomic_indicators"]["tail_risk"]["enabled"] = True

    def _raise(*_args, **_kwargs):
        raise RuntimeError("forced microstructure failure")

    monkeypatch.setattr(MicrostructureIndicatorEngine, "compute_all", _raise)

    _result, factory, manifest = _generate(config, tmp_path, monkeypatch)
    columns = _manifest_columns(manifest)

    assert any(col.startswith("tr_") for col in columns)
    assert not any(col.startswith("ms_") for col in columns)
    layer1 = factory.layer_results["Layer 1"]
    assert layer1.failed_engines == ("microstructure",)
    assert layer1.status == LayerStatus.engine_partial
