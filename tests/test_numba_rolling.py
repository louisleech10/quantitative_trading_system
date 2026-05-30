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


# ── Regression: scale-relative degeneracy guard (skew/kurt explosion fix) ──────
# Root cause: incremental Pébay sliding-window skew/kurt exploded to ~1e32 at the
# exact moment a window became constant (last differing value removed → m2 drifts
# to ~1e-25 via catastrophic cancellation; absolute guard `m2 < 1e-30` missed it,
# m3/m2**1.5 → 1e32). Triggered in production by binary signals (HT-TRENDMODE on
# native 12h) sliding from a choppy region into a long constant run. Fix: nullify
# when m2 is negligible RELATIVE to Σx² (scale-invariant), matching scipy.stats.

def _binary_choppy_then_constant(n: int = 400, window: int = 55) -> np.ndarray:
    """Binary 0/1 series: a choppy region then a long constant run.

    Reproduces the exact pathology — a window slides from "has a few 0s" into
    "all 1s", the variance→0 boundary that broke the incremental kernel.
    """
    v = np.ones(n, dtype=np.float64)
    # choppy 0/1 in the first stretch
    v[: 2 * window] = 0.0
    v[window : 2 * window : 2] = 1.0  # alternating inside the early stretch
    # everything after 2*window stays constant 1.0 (the danger zone)
    return v


def test_skew_kurt_no_explosion_on_constant_transition():
    """REG: choppy→constant binary must NOT explode; constant windows → NaN."""
    values = _binary_choppy_then_constant()
    sk = rolling_skew_kurt(values, 55).astype(np.float64)
    skew, kurt = sk[:, 0], sk[:, 1]

    # No finite value may be astronomically large (the bug produced ~1e32).
    assert np.nanmax(np.abs(skew)) < 1e6, "skew exploded on constant transition"
    assert np.nanmax(np.abs(kurt)) < 1e6, "kurt exploded on constant transition"
    assert not np.isinf(skew).any() and not np.isinf(kurt).any()

    # Deep in the constant run the window is all-1.0 → undefined → NaN.
    assert np.isnan(skew[-30:]).all()
    assert np.isnan(kurt[-30:]).all()


def test_skew_kurt_matches_pandas_on_nondegenerate_windows():
    """REG: where pandas yields a finite non-zero skew, numba must agree."""
    values = _binary_choppy_then_constant()
    numba_skew = rolling_skew_kurt(values, 55)[:, 0].astype(np.float64)
    pandas_skew = pd.Series(values).rolling(55).skew().to_numpy(dtype=np.float64)

    # Compare only on windows pandas considers non-degenerate (|skew| > 1e-9):
    # constant windows differ by convention (numba=NaN, pandas=0.0) but both mean
    # "no skewness", which is not a correctness gap.
    mask = np.isfinite(pandas_skew) & (np.abs(pandas_skew) > 1e-9)
    assert mask.any()
    np.testing.assert_allclose(numba_skew[mask], pandas_skew[mask], atol=1e-4)


@pytest.mark.parametrize("scale", [1e-10, 1.0, 1e20])
def test_skew_kurt_preserved_across_extreme_scales(scale: float):
    """REG: scale-relative guard must NOT kill genuine variance at any scale.

    Because skewness is dimensionless, a window with genuine 10%-of-scale
    variance has a well-defined skew at 1e-10, 1.0, or 1e20 alike. Our guard
    (relative m2/Σx²) preserves all three. NOTE: pandas' rolling().skew() uses an
    absolute variance floor and WRONGLY nulls the entire 1e-10 series — our fix
    is strictly more correct there, so parity is only asserted where pandas is
    also finite.
    """
    rng = np.random.default_rng(7)
    values = (scale + scale * 0.1 * rng.standard_normal(300)).astype(np.float64)
    numba_skew = rolling_skew_kurt(values, 55)[:, 0].astype(np.float64)
    pandas_skew = pd.Series(values).rolling(55).skew().to_numpy(dtype=np.float64)

    valid = np.arange(54, len(values))
    # Core requirement: genuine variance must stay finite & defined (not nulled).
    assert np.isfinite(numba_skew[valid]).all(), f"guard wrongly nulled scale={scale}"
    # Parity only where pandas is also finite (pandas nulls all of 1e-10).
    both = valid[np.isfinite(pandas_skew[valid])]
    if both.size:
        np.testing.assert_allclose(numba_skew[both], pandas_skew[both], atol=1e-3)


def test_skew_kurt_single_outlier_window_preserved():
    """REG: a 54:1 window has a real (large) skew — must be kept, not nulled."""
    values = np.ones(60, dtype=np.float64)
    values[0] = 2.0  # one different value; window [0..54] is 54-ones + 1-two
    skew = rolling_skew_kurt(values, 55)[:, 0].astype(np.float64)
    pandas_skew = pd.Series(values).rolling(55).skew().to_numpy(dtype=np.float64)

    assert np.isfinite(skew[54]), "genuine one-outlier skew was wrongly nulled"
    assert abs(skew[54]) > 1.0
    np.testing.assert_allclose(skew[54], pandas_skew[54], atol=1e-4)


def test_skew_kurt_deterministic_on_binary_series():
    """REG: repeated runs on the pathological series are bit-identical."""
    values = _binary_choppy_then_constant()
    r1 = rolling_skew_kurt(values, 55)[:, 0]
    r2 = rolling_skew_kurt(values, 55)[:, 0]
    np.testing.assert_array_equal(np.nan_to_num(r1, nan=-999.0), np.nan_to_num(r2, nan=-999.0))


def test_skew_kurt_zero_centered_no_explosion():
    """REG: ZERO-CENTERED near-constant (microstructure spread) must not explode.

    The earlier Σx²-relative guard degenerated when mean≈0 (Σx²≈m2), leaving the
    explosion on zero-centred data (e.g. roll_spread: 61 values ~1e36). The exact
    √n / n sample bounds are centring-independent and catch it. Constant-run of
    zeros + a sparse choppy lead-in reproduces the pattern.
    """
    rng = np.random.default_rng(3)
    n = 400
    v = np.zeros(n, dtype=np.float64)
    v[:60] = rng.standard_normal(60) * 1e-3  # tiny choppy lead-in near zero
    # rest stays exactly 0.0 → windows slide from "tiny spread" into "all-zero"
    sk = rolling_skew_kurt(v, 34).astype(np.float64)
    skew, kurt = sk[:, 0], sk[:, 1]
    assert np.nanmax(np.abs(skew)) <= np.sqrt(34) * (1 + 1e-6), "skew exceeded √n bound"
    assert not np.isinf(skew).any() and not np.isinf(kurt).any()
    assert int((np.abs(np.nan_to_num(skew)) > 1e10).sum()) == 0


@pytest.mark.parametrize("window", [5, 21, 55])
def test_skew_within_sqrt_n_bound(window: int):
    """REG: sample skewness can never exceed √n; assert the hard bound holds."""
    rng = np.random.default_rng(11)
    # adversarial: mostly-constant with rare spikes (maximises |skew| toward √n)
    v = np.ones(600, dtype=np.float64)
    v[::97] = 50.0
    skew = rolling_skew_kurt(v, window)[:, 0].astype(np.float64)
    finite = skew[np.isfinite(skew)]
    assert (np.abs(finite) <= np.sqrt(window) * (1 + 1e-6)).all()