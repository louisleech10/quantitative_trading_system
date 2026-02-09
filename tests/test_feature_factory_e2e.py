"""Feature Factory end-to-end tests."""

from __future__ import annotations

import numpy as np
import pytest

from momentum.factories import create_feature_factory, create_kline_storage_manager
from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner


def _load_data(symbol: str, timeframe: str):
    storage = create_kline_storage_manager()
    try:
        df = storage.read_klines(symbol, timeframe)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    return df


def _require_data(symbol: str, timeframe: str) -> None:
    if _load_data(symbol, timeframe) is None:
        pytest.skip(f"missing data for {symbol}/{timeframe}")


def _has_timeframes(symbol: str, timeframes: list[str]) -> bool:
    return all(_load_data(symbol, tf) is not None for tf in timeframes)


def test_standard_preset_btcusdt():
    _require_data("BTCUSDT", "12h")
    factory = create_feature_factory()
    result = factory.generate_features(
        "BTCUSDT",
        "12h",
        config_override={"preset": "standard"},
    )
    assert result.feature_count > 0
    assert result.features_df.shape[0] > 100
    assert not np.isinf(result.features_df.to_numpy()).any()


def test_minimal_preset():
    _require_data("BTCUSDT", "12h")
    factory = create_feature_factory()
    result = factory.generate_features(
        "BTCUSDT",
        "12h",
        config_override={"preset": "minimal"},
    )
    assert result.feature_count > 0
    assert result.feature_count < 500


def test_multi_data_source():
    _require_data("BTCUSDT", "12h")
    factory = create_feature_factory()
    override = {
        "data_sources": {"enabled_sources": ["close", "volume", "taker_ratio"]},
        "atomic_indicators": {"trend": {"enabled": True}},
    }
    result = factory.generate_features("BTCUSDT", "12h", config_override=override)
    columns = set(result.features_df.columns)
    assert any(col.startswith("close_") for col in columns)
    assert any(col.startswith("volume_") for col in columns)


def test_multi_timeframe_alignment():
    symbol = "BTCUSDT"
    timeframes = ["1h", "4h", "12h"]
    if not _has_timeframes(symbol, timeframes):
        pytest.skip("missing multi-timeframe data")

    factory = create_feature_factory()
    config = ConfigManager().get_merged_config(
        {"timeframes": {"primary": "12h", "training": timeframes}}
    )
    generator = MultiTFGenerator(factory, config)
    aligned = generator.generate_multi_tf(symbol)
    assert not aligned.empty
    assert any("_1h_" in col for col in aligned.columns) or any(
        col.startswith("close_1h_") for col in aligned.columns
    )


def test_user_override_rsi_period():
    _require_data("BTCUSDT", "12h")
    factory = create_feature_factory()
    override = {
        "atomic_indicators": {
            "momentum": {
                "enabled": True,
                "indicators": [{"name": "RSI", "periods": [7]}],
            }
        }
    }
    result = factory.generate_features("BTCUSDT", "12h", config_override=override)
    assert any("RSI_7" in col for col in result.features_df.columns)


def test_no_future_leak_alignment_check():
    _require_data("BTCUSDT", "12h")
    storage = create_kline_storage_manager()
    primary = storage.read_klines("BTCUSDT", "12h")
    primary_ts = primary["timestamp"] if "timestamp" in primary.columns else primary.index

    aligner = TimeframeAligner()
    aligned = TimeframeAligner.align_to_primary(
        primary.drop(columns=["timestamp"]) if "timestamp" in primary.columns else primary,
        "12h",
        primary_ts,
        "12h",
    )
    assert TimeframeAligner.validate_no_future_leak(aligned, primary_ts)


def test_naming_convention_basic():
    _require_data("BTCUSDT", "12h")
    factory = create_feature_factory()
    result = factory.generate_features("BTCUSDT", "12h", config_override={"preset": "minimal"})
    for name in result.features_df.columns:
        assert name
        assert " " not in name
        if name.startswith("meta_") or name.startswith("label_"):
            continue
        parts = name.split("_")
        assert len(parts) >= 3
        assert all(part for part in parts)


def test_metadata_completeness():
    _require_data("BTCUSDT", "12h")
    factory = create_feature_factory()
    result = factory.generate_features("BTCUSDT", "12h", config_override={"preset": "minimal"})
    metadata = result.metadata
    assert metadata["feature_count"] == result.feature_count
    assert len(metadata["feature_names"]) == result.feature_count
    assert "layer_counts" in metadata
    assert "config_hash" in metadata
    assert "generation_time" in metadata
