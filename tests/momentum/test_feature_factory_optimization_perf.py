from __future__ import annotations

import time
from functools import lru_cache

import numpy as np
import pandas as pd
import pytest

from momentum.factories import create_feature_factory, create_kline_storage_manager
from momentum.FeatureEngineering.atomic.entropy_indicators import EntropyIndicatorEngine
from momentum.FeatureEngineering.atomic.microstructure_indicators import MicrostructureIndicatorEngine
from momentum.FeatureEngineering.atomic.tail_risk_indicators import TailRiskIndicatorEngine
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


TEST_KLINE_CACHE_DIR = "data_cache/feature_klines"


@lru_cache(maxsize=1)
def _resolve_perf_target(min_rows: int = 300) -> tuple[str, str]:
    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    candidates = [
        ("BTCUSDT", "12h"),
        ("ETHUSDT", "1h"),
        ("ETHUSDT", "12h"),
    ]

    for symbol, timeframe in candidates:
        data = storage.read_klines(symbol, timeframe, validate_continuity=False)
        if data is not None and len(data) >= min_rows:
            return symbol, timeframe

    pytest.skip(f"No kline dataset with >= {min_rows} rows for perf tests")


def _load_ohlcv_300():
    symbol, timeframe = _resolve_perf_target(300)
    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    data = storage.read_klines(symbol, timeframe, validate_continuity=False)
    return data.head(300).copy()


def _base_pipeline_override() -> dict:
    return {
        "atomic_indicators": {
            "trend": {"enabled": True},
            "momentum": {"enabled": True},
            "volatility": {"enabled": False},
            "volume": {"enabled": False},
            "cycle": {"enabled": False},
            "pattern": {"enabled": True},
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


def test_microstructure_performance() -> None:
    data = _load_ohlcv_300()
    engine = MicrostructureIndicatorEngine(
        {
            "windows": [5, 13, 21, 55],
            "cs_spread_smooth": [5, 13, 21],
            "kyle_lambda_windows": [13, 21, 55],
            "vpin_n_buckets": [30, 50],
            "vpin_zscore_windows": [21, 55],
        },
        ["close"],
    )

    start = time.time()
    out = engine.compute_all(data)
    elapsed = time.time() - start

    assert out.shape[1] == 25
    assert elapsed < 1.0


def test_entropy_performance() -> None:
    data = _load_ohlcv_300()
    engine = EntropyIndicatorEngine(
        {
            "windows": [55, 100],
            "n_bins": 10,
            "apen_m": 2,
            "apen_r_ratio": 0.2,
            "shannon_windows": [21, 55, 100],
            "hurst_windows": [55, 100, 200],
            "fractal_kmax": 10,
            "perm_m": 3,
            "perm_windows": [21, 55, 100],
            "apply_to": ["close_return"],
            "use_numba": True,
        },
        ["close"],
    )

    start = time.time()
    out = engine.compute_all(data)
    elapsed = time.time() - start

    assert out.shape[1] == 15
    assert elapsed < 8.0


def test_tail_risk_performance() -> None:
    data = _load_ohlcv_300()
    engine = TailRiskIndicatorEngine(
        {
            "windows": [21, 55, 100],
            "cvar_alphas": [0.01, 0.05],
            "rv_windows": [13, 21, 55],
            "mdd_windows": [21, 55, 100],
        },
        ["close"],
    )

    start = time.time()
    out = engine.compute_all(data)
    elapsed = time.time() - start

    assert out.shape[1] == 26
    assert elapsed < 1.2


def test_preprocessing_performance() -> None:
    np.random.seed(42)
    features = np.random.normal(0, 1, (300, 1000))
    columns = [f"f{i}" for i in range(1000)]

    df = pd.DataFrame(features, columns=columns)
    preprocessor = FeaturePreprocessor(
        {
            "mode": "append",
            "winsorization": {
                "enabled": True,
                "method": "quantile",
                "quantile_range": [0.01, 0.99],
                "apply_to": "all",
            },
            "adf_differencing": {"enabled": False},
            "fractional_differencing": {"enabled": False},
            "rank_transform": {"enabled": True, "window": 50, "apply_to": "all"},
            "gaussian_normalize": {"enabled": False},
            "adaptive_zscore": {"enabled": True, "windows": [50], "epsilon": 1e-8, "apply_to": "all"},
        }
    )

    start = time.time()
    out = preprocessor.transform(df)
    elapsed = time.time() - start

    assert not out.empty
    assert elapsed < 30.0


def test_full_pipeline_overhead() -> None:
    # Performance benchmark should focus on feature pipeline overhead, not data continuity policy.
    factory = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    symbol, timeframe = _resolve_perf_target(300)

    shared_preprocessing = {
        "enabled": True,
        "mode": "append",
        "winsorization": {"enabled": True, "apply_to": "all"},
        "adf_differencing": {"enabled": False},
        "fractional_differencing": {"enabled": False},
        "rank_transform": {"enabled": True, "window": 55, "apply_to": "all"},
        "gaussian_normalize": {"enabled": False},
        "adaptive_zscore": {"enabled": False},
    }

    base_override = _base_pipeline_override()
    base_override["preprocessing"] = shared_preprocessing

    start_base = time.time()
    base_result = factory.generate_features(
        symbol,
        timeframe,
        config_override=base_override,
        force_regenerate=True,
        persist=False,
    )
    base_elapsed = time.time() - start_base

    new_override = _base_pipeline_override()
    new_override["atomic_indicators"]["microstructure"] = {
        "enabled": True,
        "windows": [21],
        "cs_spread_smooth": [21],
        "kyle_lambda_windows": [21],
        "vpin_n_buckets": [30],
        "vpin_zscore_windows": [21],
    }
    new_override["atomic_indicators"]["entropy"] = {
        "enabled": True,
        "windows": [55],
        "n_bins": 10,
        "apen_m": 2,
        "apen_r_ratio": 0.2,
        "shannon_windows": [21],
        "hurst_windows": [55],
        "fractal_kmax": 10,
        "perm_m": 3,
        "perm_windows": [21],
        "apply_to": ["close_return"],
        "use_numba": True,
    }
    new_override["atomic_indicators"]["tail_risk"] = {
        "enabled": True,
        "windows": [21],
        "cvar_alphas": [0.05],
        "rv_windows": [21],
        "mdd_windows": [21],
    }
    new_override["preprocessing"] = shared_preprocessing

    # Warm-up heavy paths (e.g., numba/engine initialization) to reduce one-time noise.
    factory.generate_features(
        symbol,
        timeframe,
        config_override=new_override,
        force_regenerate=True,
        persist=False,
    )

    start_new = time.time()
    new_result = factory.generate_features(
        symbol,
        timeframe,
        config_override=new_override,
        force_regenerate=True,
        persist=False,
    )
    new_elapsed = time.time() - start_new

    assert base_result.feature_count > 0
    assert new_result.feature_count > base_result.feature_count
    new_columns = (
        list(new_result.features_df.columns)
        if not new_result.features_df.empty
        else new_result.metadata.get("feature_names", [])
    )
    assert any(col.startswith("ms_") for col in new_columns)
    assert any(col.startswith("ent_") for col in new_columns)
    assert any(col.startswith("tr_") for col in new_columns)

    base_time_per_feature = base_elapsed / max(base_result.feature_count, 1)
    new_time_per_feature = new_elapsed / max(new_result.feature_count, 1)
    overhead_ratio = (new_time_per_feature - base_time_per_feature) / max(base_time_per_feature, 1e-6)
    # Keep a broad ratio guard plus absolute wall-time guard to reduce environment flakiness.
    assert overhead_ratio < 5.0
    assert new_elapsed < 60.0