"""Feature Factory 新增指標族（microstructure／entropy／tail_risk）與 L6.5 之效能與輸出驗收。

TESTSEL S3：牆鐘門檻屬效能基準（`perf`，opt-in；結果隨機器負載而變）；輸出欄數、特徵數與欄名前綴屬正確性，
留在非 perf 測試。每項計算於模組 fixture 只做一次，正確性與計時兩條共用其結果（不重複計算）。
"""

from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

from momentum.factories import create_feature_factory, create_kline_storage_manager
from momentum.FeatureEngineering.atomic.entropy_indicators import EntropyIndicatorEngine
from momentum.FeatureEngineering.atomic.microstructure_indicators import MicrostructureIndicatorEngine
from momentum.FeatureEngineering.atomic.tail_risk_indicators import TailRiskIndicatorEngine
from momentum.FeatureEngineering.feature_naming import FEATURE_CATEGORIES, parse_either_form
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


def _timed(fn) -> Dict[str, Any]:
    start = time.time()
    out = fn()
    elapsed = time.time() - start
    return {"out": out, "elapsed": elapsed}


# ---------------------------------------------------------------- 共用計算（每項一次）


@pytest.fixture(scope="module")
def microstructure_run() -> Dict[str, Any]:
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
    return _timed(lambda: engine.compute_all(data))


@pytest.fixture(scope="module")
def entropy_run() -> Dict[str, Any]:
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
    return _timed(lambda: engine.compute_all(data))


@pytest.fixture(scope="module")
def tail_risk_run() -> Dict[str, Any]:
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
    return _timed(lambda: engine.compute_all(data))


@pytest.fixture(scope="module")
def preprocessing_run() -> Dict[str, Any]:
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
    return _timed(lambda: preprocessor.transform(df))


@pytest.fixture(scope="module")
def full_pipeline_run() -> Dict[str, Any]:
    """base 與 new（加三族）各生成一次並計時；new 前先暖機一次（降低 numba／引擎初始化之一次性雜訊）。"""
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
    return {"base_result": base_result, "base_elapsed": base_elapsed,
            "new_result": new_result, "new_elapsed": new_elapsed}


# ---------------------------------------------------------------- 正確性（非 perf）


def test_microstructure_output_columns_count(microstructure_run: Dict[str, Any]) -> None:
    """microstructure 指標族於 300 根真實 K 線之輸出欄數（其餘三條同型：entropy、tail_risk、L6.5）。"""
    out = microstructure_run["out"]
    assert out.shape[1] == 25


def test_entropy_output_columns_count(entropy_run: Dict[str, Any]) -> None:
    out = entropy_run["out"]
    assert out.shape[1] == 15


def test_tail_risk_output_columns_count(tail_risk_run: Dict[str, Any]) -> None:
    out = tail_risk_run["out"]
    assert out.shape[1] == 26


def test_preprocessing_output_nonempty(preprocessing_run: Dict[str, Any]) -> None:
    out = preprocessing_run["out"]
    assert not out.empty


def test_full_pipeline_new_families_emit_columns(full_pipeline_run: Dict[str, Any]) -> None:
    """加入三族後特徵數增加，且 microstructure／entropy／tail-risk 三族（FF-NAME 前之 ms_／ent_／tr_ 前綴族）之欄皆出現
    （CGSA 路徑以 manifest 為欄名真相源）。"""
    base_result, new_result = full_pipeline_run["base_result"], full_pipeline_run["new_result"]
    assert base_result.feature_count > 0
    assert new_result.feature_count > base_result.feature_count
    # CGSA 路徑 features_df 為空且 metadata.feature_names 為空 list;欄名真相源=manifest
    new_columns = list(new_result.features_df.columns)
    if not new_columns:
        manifest_path = new_result.metadata.get("manifest_path")
        assert manifest_path, "manifest_path missing; cannot resolve feature columns"
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
        groups = manifest.get("groups")
        if groups is None:
            groups = manifest["artifacts"]["raw"]["groups"]
        group_values = groups.values() if isinstance(groups, dict) else groups
        new_columns = [
            str(column) for group in group_values for column in group.get("columns", [])
        ]
    # FF-NAME（45b18859、f2440d3b）：`ms_`／`ent_`／`tr_` 前綴族改由 category 段表達（`feature_naming.py`
    # FEATURE_CATEGORIES）⇒ 以產品 parser 解析欄名之 category 段判定三族皆有欄
    categories = {ident.category for ident in map(parse_either_form, new_columns) if ident is not None}
    for family in ("microstructure", "entropy", "tail-risk"):
        assert family in FEATURE_CATEGORIES, family
        assert family in categories, f"{family} 族無輸出欄（解析得 category {sorted(categories)}）"


# ---------------------------------------------------------------- 效能（perf，opt-in）


@pytest.mark.perf
def test_microstructure_performance(microstructure_run: Dict[str, Any]) -> None:
    elapsed = microstructure_run["elapsed"]
    assert elapsed < 1.0


@pytest.mark.perf
def test_entropy_performance(entropy_run: Dict[str, Any]) -> None:
    elapsed = entropy_run["elapsed"]
    assert elapsed < 8.0


@pytest.mark.perf
def test_tail_risk_performance(tail_risk_run: Dict[str, Any]) -> None:
    elapsed = tail_risk_run["elapsed"]
    assert elapsed < 1.2


@pytest.mark.perf
def test_preprocessing_performance(preprocessing_run: Dict[str, Any]) -> None:
    elapsed = preprocessing_run["elapsed"]
    assert elapsed < 30.0


@pytest.mark.perf
def test_full_pipeline_overhead(full_pipeline_run: Dict[str, Any]) -> None:
    base_result, new_result = full_pipeline_run["base_result"], full_pipeline_run["new_result"]
    base_elapsed, new_elapsed = full_pipeline_run["base_elapsed"], full_pipeline_run["new_elapsed"]
    base_time_per_feature = base_elapsed / max(base_result.feature_count, 1)
    new_time_per_feature = new_elapsed / max(new_result.feature_count, 1)
    overhead_ratio = (new_time_per_feature - base_time_per_feature) / max(base_time_per_feature, 1e-6)
    # Keep a broad ratio guard plus absolute wall-time guard to reduce environment flakiness.
    assert overhead_ratio < 5.0
    assert new_elapsed < 60.0
