from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.operators.numba_rolling import (
    fused_rolling_stats,
    fused_rolling_stats_multi_window,
    rolling_rank,
    rolling_skew_kurt,
    rolling_slope,
)
from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator


WINDOWS_SMALL = [5, 13, 21]
WINDOWS_FULL = [5, 8, 13, 21, 34, 55, 89, 144, 233]
ALL_AGGS = ["slope", "std", "mean", "rank", "zscore", "skew", "kurt", "min", "max", "range"]


@pytest.fixture
def sample_series() -> np.ndarray:
    """建立含間歇 NaN 的 rolling 測試序列。"""
    rng = np.random.default_rng(42)
    values = rng.normal(loc=0.0, scale=1.0, size=1024).astype(np.float64)
    values[::29] = np.nan
    values[::71] = np.nan
    return values


@pytest.fixture
def sample_frame() -> pd.DataFrame:
    """建立 Batch 3 驗證用的多欄位輸入資料。"""
    rng = np.random.default_rng(123)
    base = rng.normal(loc=0.0, scale=1.0, size=(1200, 32)).astype(np.float64)
    base[::37, 3] = np.nan
    base[::41, 7] = np.nan
    base[:, 11] = 5.0
    return pd.DataFrame(base, columns=[f"feat_{idx:03d}" for idx in range(base.shape[1])])


def _compute_single_window_reference(values: np.ndarray, windows: list[int]) -> np.ndarray:
    stacks = []
    for window in windows:
        fused = fused_rolling_stats(values, window).astype(np.float64)
        skew_kurt = rolling_skew_kurt(values, window).astype(np.float64)
        rank = rolling_rank(values, window).astype(np.float64)
        slope = rolling_slope(values, window).astype(np.float64)
        stacks.append(
            np.column_stack(
                [
                    fused,
                    skew_kurt[:, 0],
                    skew_kurt[:, 1],
                    rank,
                    slope,
                ]
            )
        )
    return np.stack(stacks, axis=1)


def _build_aggregator_config() -> dict:
    return {
        "enabled": True,
        "windows": WINDOWS_SMALL,
        "aggregators": ALL_AGGS,
        "apply_to": "all",
    }


def _assert_frame_close(actual: pd.DataFrame, expected: pd.DataFrame) -> None:
    assert list(actual.columns) == list(expected.columns)

    cols_by_atol: dict[float, list[str]] = defaultdict(list)
    for column_name in expected.columns:
        if "_Skew_" in column_name or "_Kurt_" in column_name:
            cols_by_atol[1e-4].append(column_name)
        elif "_Slope_" in column_name:
            cols_by_atol[1e-5].append(column_name)
        else:
            cols_by_atol[1e-6].append(column_name)

    for atol, columns in cols_by_atol.items():
        np.testing.assert_allclose(
            actual[columns].to_numpy(dtype=np.float64),
            expected[columns].to_numpy(dtype=np.float64),
            atol=atol,
            equal_nan=True,
        )


def test_multi_window_matches_single_window(sample_series: np.ndarray):
    """T3.1: multi-window kernel 應與逐 window kernel 完全一致。"""
    actual = fused_rolling_stats_multi_window(sample_series, np.asarray(WINDOWS_SMALL, dtype=np.int32))
    expected = _compute_single_window_reference(sample_series, WINDOWS_SMALL)

    np.testing.assert_allclose(actual, expected, atol=1e-4, equal_nan=True)


def test_multi_window_golden_equivalence(sample_frame: pd.DataFrame, monkeypatch: pytest.MonkeyPatch):
    """T3.2: multi-window 路徑與 fallback 路徑的整體輸出應一致。"""
    config = _build_aggregator_config()

    monkeypatch.setenv("FFACT_L3_STREAMING", "1")
    monkeypatch.setenv("FFACT_USE_NUMBA_ROLLING", "1")

    monkeypatch.setenv("FFACT_L3_MULTI_WINDOW", "0")
    fallback_result = RollingAggregator(config).compute_all(sample_frame)

    monkeypatch.setenv("FFACT_L3_MULTI_WINDOW", "1")
    multi_window_result = RollingAggregator(config).compute_all(sample_frame)

    _assert_frame_close(multi_window_result, fallback_result)


def test_multi_window_nan_pattern_preserved(sample_frame: pd.DataFrame, monkeypatch: pytest.MonkeyPatch):
    """T3.3: multi-window 路徑的 NaN pattern 必須與 fallback 一致。"""
    config = _build_aggregator_config()

    monkeypatch.setenv("FFACT_L3_STREAMING", "1")
    monkeypatch.setenv("FFACT_USE_NUMBA_ROLLING", "1")

    monkeypatch.setenv("FFACT_L3_MULTI_WINDOW", "0")
    fallback_result = RollingAggregator(config).compute_all(sample_frame)

    monkeypatch.setenv("FFACT_L3_MULTI_WINDOW", "1")
    multi_window_result = RollingAggregator(config).compute_all(sample_frame)

    assert np.array_equal(
        np.isnan(multi_window_result.to_numpy(dtype=np.float64)),
        np.isnan(fallback_result.to_numpy(dtype=np.float64)),
    )


def test_batch_variance_filter_matches_per_step():
    """T3.4: batch variance filter 的保留結果應與既有 per-step filter 一致。"""
    aggregator = RollingAggregator({"windows": [5], "aggregators": ALL_AGGS})
    n_rows = 128
    base = np.linspace(-1.0, 1.0, n_rows, dtype=np.float32)
    nan_heavy = np.full(n_rows, np.nan, dtype=np.float32)
    nan_heavy[:8] = np.linspace(0.0, 1.0, 8, dtype=np.float32)

    window_results = {
        "mean": base,
        "std": np.full(n_rows, 0.0, dtype=np.float32),
        "rank": nan_heavy,
        "range": np.concatenate([np.array([np.inf], dtype=np.float32), base[1:]]),
    }

    expected_frame = pd.DataFrame(
        {
            "mean": base,
            "std": np.full(n_rows, 0.0, dtype=np.float32),
            "rank": nan_heavy,
            "range": np.concatenate([np.array([np.inf], dtype=np.float32), base[1:]]),
        }
    )
    expected = aggregator._variance_filter(expected_frame)
    actual = aggregator._batch_variance_filter(window_results)

    assert set(actual.keys()) == set(expected.columns)


def test_multi_window_all_nan_input():
    """T3.B1: 輸入全 NaN 時，multi-window 輸出應全部為 NaN。"""
    values = np.full(64, np.nan, dtype=np.float64)

    actual = fused_rolling_stats_multi_window(values, np.asarray(WINDOWS_SMALL, dtype=np.int32))

    assert np.isnan(actual).all()


def test_multi_window_constant_values():
    """T3.B2: 常數序列的 multi-window 輸出應與逐 window 參考一致。"""
    values = np.full(256, 3.14, dtype=np.float64)

    actual = fused_rolling_stats_multi_window(values, np.asarray(WINDOWS_SMALL, dtype=np.int32))
    expected = _compute_single_window_reference(values, WINDOWS_SMALL)

    np.testing.assert_allclose(actual, expected, atol=1e-4, equal_nan=True)


def test_multi_window_single_window(sample_series: np.ndarray):
    """T3.B3: 單一 window 時，multi-window kernel 應退化成單 window 結果。"""
    actual = fused_rolling_stats_multi_window(sample_series, np.asarray([21], dtype=np.int32))
    expected = _compute_single_window_reference(sample_series, [21])

    np.testing.assert_allclose(actual, expected, atol=1e-4, equal_nan=True)


def test_multi_window_short_series():
    """T3.B4: rows 小於最大 window 時，對應輸出應為 NaN。"""
    values = np.arange(10.0, dtype=np.float64)

    actual = fused_rolling_stats_multi_window(values, np.asarray([21], dtype=np.int32))

    assert np.isnan(actual).all()


def test_multi_window_extreme_values():
    """T3.B5: 極大/極小值混合時，multi-window 不應 overflow。"""
    values = np.empty(512, dtype=np.float64)
    values[0::2] = 1e30
    values[1::2] = 1e-30

    actual = fused_rolling_stats_multi_window(values, np.asarray([21], dtype=np.int32))

    assert np.isfinite(actual[20:, 0, 0]).all()
    assert np.isfinite(actual[20:, 0, 4]).all()


def test_multi_window_all_windows(sample_series: np.ndarray):
    """T3.B6: 九個 windows 同時計算時，輸出應與逐 window 參考一致。"""
    actual = fused_rolling_stats_multi_window(sample_series, np.asarray(WINDOWS_FULL, dtype=np.int32))
    expected = _compute_single_window_reference(sample_series, WINDOWS_FULL)

    np.testing.assert_allclose(actual, expected, atol=1e-4, equal_nan=True)


def test_multi_window_intermittent_nan():
    """T3.B7: 間歇 NaN 輸入時，multi-window 行為應與逐 window 參考一致。"""
    values = np.array([1.0, np.nan, 3.0, np.nan, 5.0, 6.0, 7.0, np.nan, 9.0], dtype=np.float64)

    actual = fused_rolling_stats_multi_window(values, np.asarray([5], dtype=np.int32))
    expected = _compute_single_window_reference(values, [5])

    np.testing.assert_allclose(actual, expected, atol=1e-4, equal_nan=True)


def test_fallback_env_var(sample_frame: pd.DataFrame, monkeypatch: pytest.MonkeyPatch):
    """T3.B8: FFACT_L3_MULTI_WINDOW=0 時應回退到舊路徑且結果不變。"""
    config = _build_aggregator_config()

    monkeypatch.setenv("FFACT_L3_STREAMING", "1")
    monkeypatch.setenv("FFACT_USE_NUMBA_ROLLING", "1")
    monkeypatch.setenv("FFACT_L3_MULTI_WINDOW", "0")
    fallback_result = RollingAggregator(config).compute_all(sample_frame)

    monkeypatch.setenv("FFACT_L3_MULTI_WINDOW", "1")
    multi_window_result = RollingAggregator(config).compute_all(sample_frame)

    _assert_frame_close(multi_window_result, fallback_result)