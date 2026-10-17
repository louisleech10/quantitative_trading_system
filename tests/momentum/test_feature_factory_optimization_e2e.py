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


def _persisted_raw_values(factory, result) -> pd.DataFrame:
    """讀回本次 generate 落盤之 raw 群組全部欄位之值（CGSA 之 features_df 只帶索引、不帶欄）。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    symbol, timeframe = _resolve_test_target()
    reader = FeatureReader(str(factory._storage.base_path))
    config_hash = str(result.metadata["config_hash"])
    manifest = reader.load_manifest_v2(symbol, timeframe, config_hash, allow_partial=True)
    columns = _manifest_columns(manifest)
    return reader.load_columns_v2(
        symbol, timeframe, config_hash, columns, allow_partial=True, attach_row_index=True,
    )


def test_pipeline_backward_compatible(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """新引擎（microstructure／entropy／tail_risk）關閉時，既有引擎之產出**決定性且逐值不變**。

    TESTREG b5 改寫：原比對 `result.features_df`，但 CGSA 之 features_df 只有索引
    （`feature_factory.py` 約 :4006）⇒ 形狀／欄名／值比對恆真。現改為兩次獨立 generate
    （各自 tmp 落盤根）讀回 **raw 落盤值**逐欄位元組比對，並斷言欄集合非空
    （開一個既有引擎 `momentum`，防空集合恆成立）。
    """
    config_a = _base_pipeline_override()
    config_a["atomic_indicators"]["momentum"]["enabled"] = True
    config_b = deepcopy(config_a)

    result_a, factory_a, manifest_a = _generate(config_a, tmp_path / "a", monkeypatch, persist=True)
    result_b, factory_b, manifest_b = _generate(config_b, tmp_path / "b", monkeypatch, persist=True)

    columns_a = _manifest_columns(manifest_a)
    assert columns_a, "既有引擎開啟卻無任何產出欄——比對會空集合恆成立"
    assert columns_a == _manifest_columns(manifest_b)
    assert not any(col.startswith(("ms_", "ent_", "tr_")) for col in columns_a), (
        "新引擎關閉卻產出其欄位"
    )
    assert str(result_a.metadata["config_hash"]) == str(result_b.metadata["config_hash"])

    values_a = _persisted_raw_values(factory_a, result_a)
    values_b = _persisted_raw_values(factory_b, result_b)
    assert len(values_a) > 0 and list(values_a.columns) == list(values_b.columns)
    assert set(columns_a) <= set(values_a.columns), "落盤讀回之欄集合少於 manifest 宣告"
    pd.testing.assert_frame_equal(values_a, values_b, check_exact=True)


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
