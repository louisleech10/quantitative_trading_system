from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.operators.numba_rolling import (
    fused_rolling_stats,
    rolling_rank,
    rolling_skew_kurt,
    rolling_slope,
)
from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator


WINDOWS_SMALL = [5, 21]
WINDOWS_NINE = [5, 8, 13, 21, 34, 55, 89, 144, 233]
ALL_AGGS = ["slope", "std", "mean", "rank", "zscore", "skew", "kurt", "min", "max", "range"]


@pytest.fixture
def sample_series() -> np.ndarray:
    """產生含 NaN 的 rolling 測試序列。"""
    rng = np.random.default_rng(42)
    values = rng.normal(loc=0.0, scale=1.0, size=900).astype(np.float64)
    values[::37] = np.nan
    return values


@pytest.mark.parametrize("window", WINDOWS_SMALL)
def test_numba_rolling_mean_vs_pandas(sample_series: np.ndarray, window: int):
    """T3.1: fused mean 與 pandas rolling.mean 數值等價。"""
    expected = pd.Series(sample_series, dtype=np.float64).rolling(window).mean().to_numpy(dtype=np.float64)
    actual = fused_rolling_stats(sample_series, window)[:, 0].astype(np.float64)

    np.testing.assert_allclose(actual, expected, atol=1e-6, equal_nan=True)


@pytest.mark.parametrize("window", WINDOWS_SMALL)
def test_numba_rolling_std_vs_pandas(sample_series: np.ndarray, window: int):
    """T3.2: fused std 與 pandas rolling.std(ddof=1) 數值等價。"""
    expected = pd.Series(sample_series, dtype=np.float64).rolling(window).std().to_numpy(dtype=np.float64)
    actual = fused_rolling_stats(sample_series, window)[:, 1].astype(np.float64)

    np.testing.assert_allclose(actual, expected, atol=1e-6, equal_nan=True)


@pytest.mark.parametrize("window", WINDOWS_SMALL)
def test_numba_rolling_min_vs_pandas(sample_series: np.ndarray, window: int):
    """T3.3: fused min 與 pandas rolling.min 數值等價。"""
    expected = pd.Series(sample_series, dtype=np.float64).rolling(window).min().to_numpy(dtype=np.float64)
    actual = fused_rolling_stats(sample_series, window)[:, 2].astype(np.float64)

    np.testing.assert_allclose(actual, expected, atol=1e-6, equal_nan=True)


@pytest.mark.parametrize("window", WINDOWS_SMALL)
def test_numba_rolling_max_vs_pandas(sample_series: np.ndarray, window: int):
    """T3.4: fused max 與 pandas rolling.max 數值等價。"""
    expected = pd.Series(sample_series, dtype=np.float64).rolling(window).max().to_numpy(dtype=np.float64)
    actual = fused_rolling_stats(sample_series, window)[:, 3].astype(np.float64)

    np.testing.assert_allclose(actual, expected, atol=1e-6, equal_nan=True)


@pytest.mark.parametrize("window", WINDOWS_SMALL)
def test_numba_rolling_range_vs_pandas(sample_series: np.ndarray, window: int):
    """T3.5: fused range 與 pandas (max-min) 數值等價。"""
    rolling = pd.Series(sample_series, dtype=np.float64).rolling(window)
    expected = (rolling.max() - rolling.min()).to_numpy(dtype=np.float64)
    actual = fused_rolling_stats(sample_series, window)[:, 4].astype(np.float64)

    np.testing.assert_allclose(actual, expected, atol=1e-6, equal_nan=True)


@pytest.mark.parametrize("window", WINDOWS_SMALL)
def test_numba_rolling_zscore_vs_pandas(sample_series: np.ndarray, window: int):
    """T3.6: fused zscore 與 pandas ((x-mean)/std) 數值等價。"""
    series = pd.Series(sample_series, dtype=np.float64)
    rolling = series.rolling(window)
    mean = rolling.mean()
    std = rolling.std().replace(0.0, np.nan)
    expected = ((series - mean) / std).to_numpy(dtype=np.float64)
    actual = fused_rolling_stats(sample_series, window)[:, 5].astype(np.float64)

    np.testing.assert_allclose(actual, expected, atol=1e-6, equal_nan=True)


@pytest.mark.parametrize("window", WINDOWS_SMALL)
def test_numba_rolling_skew_vs_pandas(sample_series: np.ndarray, window: int):
    """T3.7: rolling_skew_kurt 的 skew 與 pandas rolling.skew 數值等價。"""
    expected = pd.Series(sample_series, dtype=np.float64).rolling(window).skew().to_numpy(dtype=np.float64)
    actual = rolling_skew_kurt(sample_series, window)[:, 0].astype(np.float64)

    np.testing.assert_allclose(actual, expected, atol=1e-4, equal_nan=True)


@pytest.mark.parametrize("window", WINDOWS_SMALL)
def test_numba_rolling_kurt_vs_pandas(sample_series: np.ndarray, window: int):
    """T3.8: rolling_skew_kurt 的 kurt 與 pandas rolling.kurt 數值等價。"""
    expected = pd.Series(sample_series, dtype=np.float64).rolling(window).kurt().to_numpy(dtype=np.float64)
    actual = rolling_skew_kurt(sample_series, window)[:, 1].astype(np.float64)

    np.testing.assert_allclose(actual, expected, atol=1e-4, equal_nan=True)


@pytest.mark.parametrize("window", WINDOWS_SMALL)
def test_numba_rolling_rank_vs_pandas(sample_series: np.ndarray, window: int):
    """T3.9: rolling_rank 與 pandas rolling.rank(method='average', pct=True) 等價。"""
    expected = (
        pd.Series(sample_series, dtype=np.float64)
        .rolling(window)
        .rank(method="average", pct=True)
        .to_numpy(dtype=np.float64)
    )
    actual = rolling_rank(sample_series, window).astype(np.float64)

    np.testing.assert_allclose(actual, expected, atol=1e-6, equal_nan=True)


@pytest.mark.parametrize("window", WINDOWS_SMALL)
def test_numba_rolling_slope_vs_existing(sample_series: np.ndarray, window: int):
    """T3.10: rolling_slope 與既有向量化 slope 實作一致。"""
    df = pd.DataFrame({"feature": sample_series}, dtype=np.float64)
    expected = RollingAggregator._compute_slope_vectorized(df, window)["feature"].to_numpy(dtype=np.float64)
    actual = rolling_slope(sample_series, window).astype(np.float64)

    np.testing.assert_allclose(actual, expected, atol=1e-5, equal_nan=True)


def test_fused_multi_window_equivalent(sample_series: np.ndarray):
    """T3.11: 多個 window 的 fused 結果應與逐一 pandas rolling 一致。"""
    series = pd.Series(sample_series, dtype=np.float64)

    for window in WINDOWS_NINE:
        rolling = series.rolling(window)
        expected = np.column_stack(
            [
                rolling.mean().to_numpy(dtype=np.float64),
                rolling.std().to_numpy(dtype=np.float64),
                rolling.min().to_numpy(dtype=np.float64),
                rolling.max().to_numpy(dtype=np.float64),
                (rolling.max() - rolling.min()).to_numpy(dtype=np.float64),
                ((series - rolling.mean()) / rolling.std().replace(0.0, np.nan)).to_numpy(dtype=np.float64),
            ]
        )
        actual = fused_rolling_stats(sample_series, window).astype(np.float64)
        np.testing.assert_allclose(actual, expected, atol=1e-6, equal_nan=True)


def test_fused_golden_output_match(monkeypatch):
    """T3.12: RollingAggregator Numba 與 pandas fallback 的輸出（欄位與數值）應一致。"""
    rng = np.random.default_rng(123)
    base = rng.normal(loc=0.0, scale=1.0, size=(900, 24)).astype(np.float64)
    base[::41, 3] = np.nan
    base[::53, 7] = np.nan
    df = pd.DataFrame(base, columns=[f"feat_{idx:03d}" for idx in range(base.shape[1])])

    config = {
        "enabled": True,
        "windows": [5, 13, 21],
        "aggregators": ALL_AGGS,
        "apply_to": "all",
    }

    monkeypatch.setenv("FFACT_L3_STREAMING", "1")

    monkeypatch.setenv("FFACT_USE_NUMBA_ROLLING", "0")
    pandas_result = RollingAggregator(config).compute_all(df)

    monkeypatch.setenv("FFACT_USE_NUMBA_ROLLING", "1")
    numba_result = RollingAggregator(config).compute_all(df)

    assert list(numba_result.columns) == list(pandas_result.columns)

    cols_by_atol: dict[float, list[str]] = defaultdict(list)
    for column_name in pandas_result.columns:
        if "_Skew_" in column_name or "_Kurt_" in column_name:
            cols_by_atol[1e-4].append(column_name)
        elif "_Slope_" in column_name:
            cols_by_atol[1e-5].append(column_name)
        else:
            cols_by_atol[1e-6].append(column_name)

    for atol, cols in cols_by_atol.items():
        np.testing.assert_allclose(
            numba_result[cols].to_numpy(dtype=np.float64),
            pandas_result[cols].to_numpy(dtype=np.float64),
            atol=atol,
            equal_nan=True,
        )


def test_numba_rolling_all_nan_input():
    """T3.B1: 全 NaN 輸入時，fused/rank/slope 皆應輸出全 NaN。"""
    values = np.full(64, np.nan, dtype=np.float64)

    fused = fused_rolling_stats(values, 5)
    rank = rolling_rank(values, 5)
    slope = rolling_slope(values, 5)

    assert np.isnan(fused).all()
    assert np.isnan(rank).all()
    assert np.isnan(slope).all()


def test_numba_rolling_skew_kurt_constant_is_nan():
    """T3.B2: 常數序列的 skew/kurt 應為 NaN（zero-variance guard）。"""
    values = np.full(64, 3.14, dtype=np.float64)

    skew_kurt = rolling_skew_kurt(values, 21).astype(np.float64)

    assert np.isnan(skew_kurt[20:, 0]).all()
    assert np.isnan(skew_kurt[20:, 1]).all()


def test_numba_rolling_window_one_stats():
    """T3.B3: window=1 時，fused mean 應等於原值，std 為 NaN。"""
    values = np.array([3.0, np.nan, -2.0], dtype=np.float64)

    fused = fused_rolling_stats(values, 1).astype(np.float64)

    assert fused[0, 0] == pytest.approx(3.0, abs=1e-6)
    assert np.isnan(fused[0, 1])
    assert np.isnan(fused[1, 0])
    assert fused[2, 0] == pytest.approx(-2.0, abs=1e-6)


def test_numba_rolling_rank_window_one_returns_one():
    """T3.B3: window=1 且值非 NaN 時，rank 應為 1.0。"""
    values = np.array([3.0, np.nan, -2.0], dtype=np.float64)

    actual = rolling_rank(values, 1)

    assert actual[0] == pytest.approx(1.0, abs=1e-6)
    assert np.isnan(actual[1])
    assert actual[2] == pytest.approx(1.0, abs=1e-6)


def test_numba_rolling_n_less_than_window_all_nan():
    """T3.B4: rows < window 時，輸出應為全 NaN。"""
    values = np.array([1.0, 2.0, 3.0], dtype=np.float64)

    fused = fused_rolling_stats(values, 5)
    rank = rolling_rank(values, 5)
    slope = rolling_slope(values, 5)
    skew_kurt = rolling_skew_kurt(values, 5)

    assert np.isnan(fused).all()
    assert np.isnan(rank).all()
    assert np.isnan(slope).all()
    assert np.isnan(skew_kurt).all()


def test_numba_rolling_large_small_alternating_values():
    """T3.B5: 極大/極小值交替不應造成 overflow。"""
    values = np.empty(256, dtype=np.float64)
    values[0::2] = 1e30
    values[1::2] = 1e-30

    fused = fused_rolling_stats(values, 21).astype(np.float64)

    assert np.isfinite(fused[20:, 0]).all()
    assert np.isfinite(fused[20:, 4]).all()


def test_numba_rolling_window_233_tail_matches_pandas(sample_series: np.ndarray):
    """T3.B6: window=233 時 tail 計算應與 pandas 一致。"""
    window = 233
    expected = pd.Series(sample_series, dtype=np.float64).rolling(window).mean().to_numpy(dtype=np.float64)
    actual = fused_rolling_stats(sample_series, window)[:, 0].astype(np.float64)

    np.testing.assert_allclose(actual, expected, atol=1e-6, equal_nan=True)


def test_numba_rolling_inf_propagation():
    """T3.B7: 含 ±inf 的輸入應可完成計算，且輸出包含對應 inf/NaN。"""
    values = np.array([1.0, 2.0, np.inf, 4.0, 5.0, -np.inf, 7.0, 8.0], dtype=np.float64)

    fused = fused_rolling_stats(values, 5).astype(np.float64)

    assert np.isinf(fused[:, 2]).any() or np.isinf(fused[:, 3]).any() or np.isnan(fused[:, 1]).any()


def test_numba_rolling_single_row_input():
    """T3.B8: 單行輸入且 window>1 時，各輸出應為 NaN。"""
    values = np.array([42.0], dtype=np.float64)

    fused = fused_rolling_stats(values, 5)
    rank = rolling_rank(values, 5)
    slope = rolling_slope(values, 5)
    skew_kurt = rolling_skew_kurt(values, 5)

    assert np.isnan(fused).all()
    assert np.isnan(rank).all()
    assert np.isnan(slope).all()
    assert np.isnan(skew_kurt).all()


def test_numba_rolling_rank_ties_average_method():
    """T3.B9: ties 應使用 average rank method。"""
    values = np.array([1.0, 2.0, 2.0, 2.0, 2.0], dtype=np.float64)

    actual = rolling_rank(values, 5)

    assert np.isnan(actual[:4]).all()
    assert actual[4] == pytest.approx(0.7, abs=1e-6)


def test_numba_rolling_float32_float64_precision_gap():
    """T3.B10: float64 與 float32 輸入的 skew/kurt 誤差應小於 1e-4。"""
    rng = np.random.default_rng(77)
    values64 = rng.normal(size=800).astype(np.float64)
    values32 = values64.astype(np.float32)

    out64 = rolling_skew_kurt(values64, 21).astype(np.float64)
    out32 = rolling_skew_kurt(values32, 21).astype(np.float64)

    np.testing.assert_allclose(out64, out32, atol=1e-4, equal_nan=True)


def test_numba_rolling_intermittent_nan_returns_nan_when_insufficient_points():
    """T3.B11: window 內有效值不足 min_periods 時，輸出應為 NaN。"""
    values = np.array([1.0, np.nan, 3.0, np.nan, 5.0, 6.0, 7.0], dtype=np.float64)

    fused = fused_rolling_stats(values, 5).astype(np.float64)
    rank = rolling_rank(values, 5).astype(np.float64)

    assert np.isnan(fused).all()
    assert np.isnan(rank).all()


def test_numba_rolling_min_periods_behavior_exact_match():
    """T3.B12: min_periods=window 行為應與 pandas 一致。"""
    values = np.arange(1.0, 21.0, dtype=np.float64)
    window = 5

    expected = pd.Series(values, dtype=np.float64).rolling(window).mean().to_numpy(dtype=np.float64)
    actual = fused_rolling_stats(values, window)[:, 0].astype(np.float64)

    assert np.isnan(actual[: window - 1]).all()
    np.testing.assert_allclose(actual, expected, atol=1e-6, equal_nan=True)


def test_numba_rolling_nine_windows_all_valid():
    """T3.B13: 九個 windows 連續計算應正確完成。"""
    rng = np.random.default_rng(100)
    values = rng.normal(size=1200).astype(np.float64)

    for window in WINDOWS_NINE:
        fused = fused_rolling_stats(values, window)
        assert fused.shape == (values.shape[0], 6)
        assert np.isnan(fused[: window - 1]).all()