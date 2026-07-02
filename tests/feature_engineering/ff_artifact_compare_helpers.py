"""P1-FF-5/7 共用測試 helper。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.preprocessing._d_star_cache import (
    DStarCache,
    PreprocessingContext,
    read_d_star_json,
)
from momentum.factories import create_feature_factory


KLINE_CACHE_DIR = "data_cache/feature_klines"
BASELINE_SYMBOL = "BTCUSDT"
OTHER_SYMBOL = "ETHUSDT"
BASELINE_TIMEFRAME = "12h"
FULL_CHAIN_DATA_SOURCES = [
    "close",
    "open",
    "high",
    "low",
    "volume",
    "quote_volume",
    "taker_ratio",
]
FULL_CHAIN_SYNTHETIC_SOURCES = ["typ-price"]
SLOW_L3_WINDOWS = [13, 55]
SLOW_L3_AGGREGATORS = ["mean", "std", "rank", "zscore", "min", "max", "range", "slope"]
SLOW_CUSTOM_LAGS = [1, 3]


def kline_full_window_dates(*klines: pd.DataFrame) -> tuple[str, str]:
    """由真實 kline timestamp 交集推出完整共同日期窗。"""
    if not klines:
        pytest.fail("kline_full_window_dates needs at least one kline frame")
    mins: list[int] = []
    maxes: list[int] = []
    for kline_df in klines:
        if "timestamp" not in kline_df.columns:
            pytest.fail("requires_kline fixture missing timestamp column")
        ts = kline_df["timestamp"].astype(np.int64)
        mins.append(int(ts.min()))
        maxes.append(int(ts.max()))
    start = pd.Timestamp(max(mins), unit="s", tz="UTC")
    end = pd.Timestamp(min(maxes), unit="s", tz="UTC")
    if start >= end:
        pytest.fail(f"kline full-window intersection is empty: {start} >= {end}")
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def kline_window_dates(kline_df: pd.DataFrame, *, days: int) -> tuple[str, str]:
    """由真實 kline timestamp 推出短窗日期。"""
    if "timestamp" not in kline_df.columns:
        pytest.fail("requires_kline fixture missing timestamp column")
    ts = kline_df["timestamp"].astype(np.int64)
    end = pd.Timestamp(int(ts.max()), unit="s", tz="UTC")
    start = end - pd.Timedelta(days=days)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def fast_config_payload(**overrides: object) -> dict[str, object]:
    """短窗 Feature Factory config：不開 L6.5，專注跨 symbol 值隔離。"""
    payload: dict[str, object] = {
        "timeframes": {
            "primary": BASELINE_TIMEFRAME,
            "training": [BASELINE_TIMEFRAME],
            "alignment_mode": "open_minus",
        },
        "data_sources": {"enabled_sources": ["close"], "synthetic_sources": []},
        "atomic_indicators": {
            "trend": {
                "enabled": True,
                "indicators": [
                    {"name": "EMA", "params": {"timeperiod": 8}},
                    {"name": "SMA", "params": {"timeperiod": 13}},
                ],
            },
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
        "operators": {"enabled": False},
        "rolling_aggregation": {"enabled": False},
        "lag_features": {"enabled": False},
        "meta_features": {"enabled": False},
        "cross_sectional": {"enabled": False},
        "preprocessing": {"enabled": False},
        "nan_strategy": {"l7_dead_feature_drop": {"enabled": False}},
    }
    payload.update(overrides)
    return payload


def cross_sectional_config_payload(reference_symbol: str) -> dict[str, object]:
    """短窗 L5 config：固定 reference_symbol，測 reference cache key。"""
    return fast_config_payload(
        cross_sectional={
            "enabled": True,
            "reference_symbol": reference_symbol,
            "features": {
                "relative_price": {"enabled": True},
                "beta": {"enabled": False},
                "idiosyncratic_momentum": {"enabled": False},
            },
        },
    )


def slow_full_chain_config_payload(reference_symbol: str) -> dict[str, object]:
    """Slow tier FF5 config：明確全開（不綁 preset，preset 待盤點移除）全鏈 + L6.5 fracdiff/d*。"""
    from tests.feature_engineering.ff_truncation_mr_helpers import (
        _atomic_indicators_all_enabled,
    )

    return {
        "global": {
            "sequence_length": 100,
            "lag_strategy": "custom",
            "custom_lags": SLOW_CUSTOM_LAGS,
        },
        "atomic_indicators": _atomic_indicators_all_enabled(),
        "timeframes": {
            "primary": BASELINE_TIMEFRAME,
            "training": [BASELINE_TIMEFRAME],
            "alignment_mode": "open_minus",
        },
        "data_sources": {
            "enabled_sources": FULL_CHAIN_DATA_SOURCES,
            "synthetic_sources": FULL_CHAIN_SYNTHETIC_SOURCES,
        },
        "operators": {
            "enabled": True,
            "distance": {"enabled": True},
            "cross": {"enabled": True},
            "ratio": {"enabled": True},
            "momentum": {"enabled": True, "lags": [1, 3]},
            "binary_signal": {"enabled": False, "rules": []},
            "signed_strength": {"enabled": True},
            "worldquant": {
                "enabled": True,
                "windows": [13],
                "operators": {
                    "ts_rank": {"enabled": True},
                    "decay_linear": {"enabled": True},
                    "ts_argmax": {"enabled": False},
                    "ts_argmin": {"enabled": False},
                    "ts_corr": {"enabled": False},
                },
                "transforms": ["sign", "abs"],
            },
        },
        "rolling_aggregation": {
            "enabled": True,
            "windows": SLOW_L3_WINDOWS,
            "aggregators": {name: {"enabled": True} for name in SLOW_L3_AGGREGATORS},
        },
        "lag_features": {"enabled": True, "apply_to": "layer1_and_raw"},
        "cross_sectional": {
            "enabled": True,
            "reference_symbol": reference_symbol,
            "features": {
                "relative_price": {"enabled": True},
                "beta": {"enabled": True},
                "idiosyncratic_momentum": {"enabled": True},
            },
        },
        "meta_features": {
            "enabled": True,
            "trend_consensus": True,
            "momentum_divergence": True,
            "volume_price_divergence": True,
            "volatility_regime": True,
            "interaction": True,
            "time_features": True,
        },
        "preprocessing": {
            "enabled": True,
            "mode": "replace",
            "causal_preprocessing": True,
            "winsorization": {"enabled": True, "window": 55},
            "rank_transform": {"enabled": False},
            "adaptive_zscore": {"enabled": False},
            "gaussian_normalize": {"enabled": False},
            "adf_differencing": {"enabled": True, "sample_size": 256, "max_diff": 1},
            "fractional_differencing": {
                "enabled": True,
                "cache_d_star": True,
                "apply_to": "non_stationary",
                "precision": 0.1,
                "weight_threshold": 1e-4,
            },
        },
        "nan_strategy": {"l7_dead_feature_drop": {"enabled": False}},
    }


def assert_slow_full_chain_config(factory, config_payload: Mapping[str, object]) -> None:
    """配置稽核：slow tier 不得退化為 compact/smoke。"""
    config = factory._resolve_config(dict(config_payload))
    atomic = config.atomic_indicators.model_dump()
    enabled_atomic = [
        key
        for key, value in atomic.items()
        if isinstance(value, dict) and bool(value.get("enabled"))
    ]
    assert len(enabled_atomic) >= 8, enabled_atomic
    assert set(FULL_CHAIN_DATA_SOURCES).issubset(set(config.data_sources.enabled_sources))
    assert list(config.data_sources.synthetic_sources) == FULL_CHAIN_SYNTHETIC_SOURCES
    assert config.operators.enabled is True
    assert config.rolling_aggregation.enabled is True
    assert list(config.rolling_aggregation.windows) == SLOW_L3_WINDOWS
    enabled_aggs = [
        name for name, value in config.rolling_aggregation.aggregators.items() if value.enabled
    ]
    assert enabled_aggs == SLOW_L3_AGGREGATORS
    assert config.lag_features.enabled is True
    assert config.global_settings.lag_strategy == "custom"
    assert list(config.global_settings.custom_lags or []) == SLOW_CUSTOM_LAGS
    assert config.cross_sectional.enabled is True
    assert config.cross_sectional.reference_symbol == OTHER_SYMBOL
    assert all(feature.enabled for feature in config.cross_sectional.features.values())
    assert config.meta_features.enabled is True
    assert config.meta_features.trend_consensus is True
    assert config.meta_features.momentum_divergence is True
    assert config.meta_features.volume_price_divergence is True
    assert config.meta_features.volatility_regime is True
    assert config.meta_features.interaction is True
    assert config.meta_features.time_features is True
    assert config.preprocessing.enabled is True
    assert config.preprocessing.causal_preprocessing is True
    assert config.preprocessing.winsorization.enabled is True
    assert config.preprocessing.adf_differencing.enabled is True
    assert config.preprocessing.fractional_differencing.enabled is True
    assert config.preprocessing.fractional_differencing.cache_d_star is True


def assert_full_chain_runtime(factory, result, *, manifest: Mapping[str, Any] | None = None) -> None:
    """執行稽核：L1-L7 每層實跑完成，不得 empty/disabled/degraded。"""
    assert int(result.feature_count) > 2
    assert result.features_df.shape[1] > 2
    for layer_name in ["Layer 1", "Layer 2", "Layer 3", "Layer 4", "Layer 5", "Layer 6"]:
        layer = factory.layer_results.get(layer_name)
        assert layer is not None, f"missing {layer_name}"
        status = getattr(layer, "status", None)
        status_value = getattr(status, "value", str(status))
        assert status_value == "ok", (
            layer_name,
            status,
            getattr(layer, "reason", None),
            getattr(layer, "failed_engines", None),
        )
        assert int(getattr(layer, "present_engines", 0)) > 0, (
            layer_name,
            getattr(layer, "status", None),
            getattr(layer, "reason", None),
        )
        data = getattr(layer, "data", pd.DataFrame())
        assert data is not None and not data.empty, (
            layer_name,
            getattr(layer, "status", None),
        )
        assert int(data.shape[1]) > 0, (layer_name, data.shape)
    assert getattr(factory, "_preprocessing_applied", None) is True
    effective = getattr(factory, "_effective_preprocessing_config", None) or {}
    fracdiff = effective.get("fractional_differencing") or {}
    assert effective.get("enabled") is True
    assert fracdiff.get("enabled") is True
    assert fracdiff.get("cache_d_star") is True
    output_manifest = manifest or runtime_output_manifest(result)
    assert int(output_manifest.get("feature_count", output_manifest.get("total_features", result.feature_count))) > 0
    assert str(output_manifest.get("run_status", output_manifest.get("quality_status", "complete"))) in {
        "complete",
        "ok",
    }


def make_factory(tmp_path: Path):
    """建立隔離 storage 的 FeatureFactory。"""
    factory = create_feature_factory(
        cache_dir=KLINE_CACHE_DIR,
        validate_continuity=False,
    )
    factory._storage = FeatureStorage(str(tmp_path / "features"))
    return factory


def run_symbol_frame(
    factory,
    *,
    symbol: str,
    start_date: str,
    end_date: str,
    config_payload: Mapping[str, object] | None = None,
    persist: bool = False,
) -> pd.DataFrame:
    """跑單一 symbol 並回傳 feature DataFrame。"""
    return run_symbol_result(
        factory,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        config_payload=config_payload,
        persist=persist,
    ).features_df


def run_symbol_result(
    factory,
    *,
    symbol: str,
    start_date: str,
    end_date: str,
    config_payload: Mapping[str, object] | None = None,
    persist: bool = False,
):
    """跑單一 symbol 並回傳完整 FeatureGenerationResult。"""
    result = factory.generate_features(
        symbol,
        BASELINE_TIMEFRAME,
        config_override=dict(config_payload or fast_config_payload()),
        force_regenerate=True,
        start_date=start_date,
        end_date=end_date,
        persist=persist,
    )
    return result


def canonical_frame_digest(frame: pd.DataFrame) -> str:
    """DataFrame canonical hash：欄序/index/NaN mask/值 bytes。"""
    digest = hashlib.sha256()
    digest.update("\0".join(str(column) for column in frame.columns).encode("utf-8"))
    digest.update(str(frame.index.dtype).encode("utf-8"))
    digest.update(pd.util.hash_pandas_object(frame.index, index=True).to_numpy().tobytes())
    for column in frame.columns:
        values = np.asarray(frame[column].to_numpy(copy=False))
        mask = pd.isna(values).astype(np.uint8)
        digest.update(str(column).encode("utf-8"))
        digest.update(str(values.dtype).encode("utf-8"))
        digest.update(np.packbits(mask, bitorder="little").tobytes())
        finite_values = values[~mask.astype(bool)]
        digest.update(np.ascontiguousarray(finite_values).view(np.uint8).tobytes())
    return digest.hexdigest()


def representative_columns(frame: pd.DataFrame, *, limit: int = 20) -> list[str]:
    """穩定抽樣最多 20 欄，避免只比整表 hash。"""
    numeric = [
        str(column)
        for column in frame.select_dtypes(include=[np.number]).columns
        if frame[column].notna().any()
    ]
    if len(numeric) <= limit:
        return numeric
    positions = np.linspace(0, len(numeric) - 1, limit, dtype=int)
    return [numeric[int(pos)] for pos in positions]


def assert_sampled_values_equal(
    expected: pd.DataFrame,
    actual: pd.DataFrame,
    *,
    columns: Iterable[str],
) -> None:
    """代表欄值與 NaN mask 一致。"""
    assert expected.index.equals(actual.index)
    assert list(expected.columns) == list(actual.columns)
    for column in columns:
        left = expected[column].to_numpy()
        right = actual[column].to_numpy()
        left_nan = pd.isna(left)
        right_nan = pd.isna(right)
        assert np.array_equal(left_nan, right_nan), f"NaN mask differs: {column}"
        finite = ~left_nan
        if finite.any():
            np.testing.assert_allclose(
                left[finite].astype(float),
                right[finite].astype(float),
                rtol=0.0,
                atol=0.0,
                err_msg=f"value differs: {column}",
            )


def dstar_context(symbol: str, timeframe: str = BASELINE_TIMEFRAME) -> PreprocessingContext:
    """建立 d-star isolation context。"""
    return PreprocessingContext(
        symbol=symbol,
        timeframe=timeframe,
        config_hash="cfg-p1ff57",
        data_fingerprint=f"fingerprint-{symbol}-{timeframe}",
    )


def write_dstar_payload(cache_dir: Path, symbol: str, column: str) -> Path:
    """建立一份 d-star cache payload 並回傳檔案路徑。"""
    values = np.linspace(1.0, 3.0, 32, dtype=np.float64)
    cache = DStarCache(
        dstar_context(symbol),
        cache_dir,
        adf_threshold=0.05,
        precision=0.1,
        max_lag=20,
        weight_threshold=1e-5,
        sample_size=64,
        causal_preprocessing=True,
        calibration_bars=32,
    )
    cache.set(column, 0.4, col_values=values)
    cache.flush_atomic()
    assert cache.path.is_file()
    return cache.path


def assert_dstar_symbol_isolated(cache_dir: Path) -> None:
    """V5.2/V5.2b：d-star path、語義 map、value_alias source 隔離。"""
    a_path = write_dstar_payload(cache_dir, BASELINE_SYMBOL, "L1_close_self")
    b_path = write_dstar_payload(cache_dir, OTHER_SYMBOL, "L1_close_other")

    assert a_path != b_path
    assert BASELINE_SYMBOL in a_path.name
    assert OTHER_SYMBOL not in a_path.name
    assert read_d_star_json(a_path) == {"L1_close_self": 0.4}
    assert read_d_star_json(b_path) == {"L1_close_other": 0.4}
    assert read_d_star_json(b_path).get("L1_close_self") is None

    payload = __import__("json").loads(a_path.read_text(encoding="utf-8"))
    aliases = payload.get("value_aliases") or {}
    for alias in aliases.values():
        assert OTHER_SYMBOL not in str(alias.get("source_column", ""))


def feature_manifest_path(factory, symbol: str, config_hash: str) -> Path:
    """回傳 runtime 實際 feature_manifest.json 路徑。"""
    return (
        factory._storage.feature_run_dir(symbol, BASELINE_TIMEFRAME, config_hash)
        / FeatureStorage.L7_V2_MANIFEST_NAME
    )


def load_json(path: Path) -> dict[str, Any]:
    """讀取 JSON object。"""
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def runtime_output_manifest(result, *, factory=None, symbol: str | None = None) -> dict[str, Any]:
    """讀 runtime manifest；非 CGSA/HDF5 path 則使用 result metadata 作為輸出 manifest。"""
    metadata = dict(result.metadata or {})
    hdf5_path = Path(str(result.hdf5_path)) if result.hdf5_path else None
    if hdf5_path and hdf5_path.name == FeatureStorage.L7_V2_MANIFEST_NAME and hdf5_path.exists():
        return load_json(hdf5_path)
    if factory is not None and symbol is not None and metadata.get("config_hash"):
        manifest_path = feature_manifest_path(factory, symbol, str(metadata["config_hash"]))
        if manifest_path.exists():
            return load_json(manifest_path)
    return metadata


def manifest_semantic_summary(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """V5.3 語義摘要：忽略 created_at/updated_at/path 等非語義欄。"""
    if "artifacts" in manifest and isinstance(manifest.get("artifacts"), Mapping):
        raw = manifest.get("artifacts", {}).get("raw") or manifest
        raw_metadata = raw.get("metadata") or {}
        groups = raw.get("groups") or {}
        columns_by_group = {
            str(group_id): [str(column) for column in group_meta.get("columns", [])]
            for group_id, group_meta in sorted(groups.items())
            if isinstance(group_meta, Mapping)
        }
        return {
            "symbol": str(raw.get("symbol", raw_metadata.get("symbol", manifest.get("symbol", "")))),
            "row_count": int(raw.get("row_count", manifest.get("row_count", -1))),
            "total_features": int(raw.get("total_features", manifest.get("total_features", -1))),
            "schema_version": str(raw.get("schema_version", manifest.get("schema_version", ""))),
            "feature_schema_hash": str(raw.get("feature_schema_hash", manifest.get("feature_schema_hash", ""))),
            "columns_by_group": columns_by_group,
        }

    feature_names = [str(column) for column in manifest.get("feature_names", [])]
    return {
        "symbol": str(manifest.get("symbol", "")),
        "row_count": int(manifest.get("row_count", manifest.get("output_rows", -1))),
        "total_features": int(manifest.get("feature_count", len(feature_names))),
        "config_hash": str(manifest.get("config_hash", "")),
        "feature_names": feature_names,
        "validation_keys": sorted((manifest.get("validation") or {}).keys()),
    }


def assert_manifest_semantics_equal(expected: Mapping[str, Any], actual: Mapping[str, Any]) -> None:
    """V5.3：manifest 行數、欄集、schema 語義一致。"""
    assert manifest_semantic_summary(expected) == manifest_semantic_summary(actual)


def dstar_payload_summary(cache_dir: Path, symbol: str) -> dict[str, dict[str, float]]:
    """讀取指定 symbol 的 d-star payload 語義 map。"""
    paths = sorted(Path(cache_dir).glob(f"d_star_{symbol}_*.json"))
    if not paths:
        pytest.fail(f"missing d-star cache artifacts for {symbol}: {cache_dir}")
    summary = {path.name: read_d_star_json(path) for path in paths}
    empty = [name for name, payload in summary.items() if not payload]
    if empty:
        pytest.fail(f"empty d-star payloads for {symbol}: {empty}")
    return summary


def assert_dstar_payloads_equal(expected_cache_dir: Path, actual_cache_dir: Path, symbol: str) -> None:
    """V5.2：solo(A) 與 batch A 的 d-star payload 語義一致。"""
    assert dstar_payload_summary(expected_cache_dir, symbol) == dstar_payload_summary(actual_cache_dir, symbol)


def assert_path_excludes_symbol(path_or_payload: object, forbidden_symbol: str) -> None:
    """V5.4：runtime path/metadata 不得含另一個 symbol token。"""
    assert forbidden_symbol not in str(path_or_payload)
