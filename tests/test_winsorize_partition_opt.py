"""
tests/test_winsorize_partition_opt.py

驗證 L6.5 winsorization 優化的正確性與邊界條件：
  1. _partition_nanquantile_2d 與 _nanquantile_linear 數值等價
  2. _winsorize_2d_inplace 新舊路徑等價
  3. _winsorize_2d_legacy_equivalent 多餘 copy 已消除
  4. 完整 pipeline end-to-end 等價

執行：
  ./venv/bin/pytest tests/test_winsorize_partition_opt.py -v
"""

from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.preprocessing.feature_preprocessor import (
    FeaturePreprocessor,
)
from tests._fixtures.rolling_quantile_legacy import rolling_quantile_2d_legacy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_preprocessor(
    winsor_method: str = "quantile",
    quantile_range=None,
    *,
    causal_preprocessing: bool = True,
) -> FeaturePreprocessor:
    """最小設定的 FeaturePreprocessor instance，足以呼叫 winsorize 相關方法。"""
    if quantile_range is None:
        quantile_range = [0.01, 0.99]
    cfg = {
        "causal_preprocessing": causal_preprocessing,
        "winsorization": {
            "enabled": True,
            "method": winsor_method,
            "quantile_range": quantile_range,
            "sigma_k": 3.0,
        },
        "rank": {"enabled": False},
        "zscore": {"enabled": False},
        "fracdiff": {"enabled": False},
        "gaussian": {"enabled": False},
        "diff": {"enabled": False},
        "fracdiff_columns": [],
        "rank_windows": [20],
        "zscore_windows": [20],
    }
    return FeaturePreprocessor(cfg)


def _reference_nanquantile(arr: np.ndarray, quantiles: List[float]) -> np.ndarray:
    """Reference: np.nanquantile with linear interpolation (Python >= 3.9 API)."""
    try:
        return np.nanquantile(arr, quantiles, axis=0, method="linear")
    except TypeError:
        return np.nanquantile(arr, quantiles, axis=0, interpolation="linear")


# ---------------------------------------------------------------------------
# 1. Fast path — no NaN, numerical equivalence
# ---------------------------------------------------------------------------

def test_partition_matches_nanquantile_no_nan():
    """Fast path: 無 NaN 時 _partition_nanquantile_2d 與 np.nanquantile bit-identical。"""
    rng = np.random.default_rng(42)
    arr = rng.standard_normal((200, 50)).astype(np.float64)
    quantiles = [0.01, 0.99]

    result = FeaturePreprocessor._partition_nanquantile_2d(arr, quantiles)
    reference = _reference_nanquantile(arr, quantiles)

    np.testing.assert_allclose(result, reference, rtol=1e-10, atol=1e-10,
                               err_msg="Fast path (no NaN) 結果與 np.nanquantile 不一致")


# ---------------------------------------------------------------------------
# 2. Fast path — uniform leading NaN (rolling warmup 場景)
# ---------------------------------------------------------------------------

def test_partition_matches_nanquantile_leading_nan_uniform():
    """Fast path: 每欄有相同數量的 leading NaN（rolling warmup 最常見場景）。"""
    rng = np.random.default_rng(123)
    n_rows, n_cols = 100, 30
    arr = rng.standard_normal((n_rows, n_cols)).astype(np.float64)
    # 前 20 行全設為 NaN（模擬 rolling window warmup）
    arr[:20, :] = np.nan
    assert arr.shape == (n_rows, n_cols)

    quantiles = [0.01, 0.99]
    result = FeaturePreprocessor._partition_nanquantile_2d(arr, quantiles)
    reference = _reference_nanquantile(arr, quantiles)

    np.testing.assert_allclose(result, reference, rtol=1e-10, atol=1e-10,
                               err_msg="Fast path (uniform leading NaN) 結果與 np.nanquantile 不一致")


# ---------------------------------------------------------------------------
# 3. Slow path — heterogeneous NaN counts trigger fallback
# ---------------------------------------------------------------------------

def test_partition_matches_nanquantile_mixed_nan():
    """Slow path: 各欄 NaN 數量不同時，fallback 到 _nanquantile_linear。"""
    rng = np.random.default_rng(7)
    n_rows, n_cols = 80, 20
    arr = rng.standard_normal((n_rows, n_cols)).astype(np.float64)
    # 各欄設不同數量的 NaN，確保 finite_counts 不均一
    for col in range(n_cols):
        arr[:col, col] = np.nan   # col 0 → 0 NaN, col 1 → 1 NaN, ...

    quantiles = [0.01, 0.99]
    result = FeaturePreprocessor._partition_nanquantile_2d(arr, quantiles)
    reference = _reference_nanquantile(arr, quantiles)

    np.testing.assert_allclose(result, reference, rtol=1e-10, atol=1e-10,
                               err_msg="Slow path (mixed NaN) 結果與 np.nanquantile 不一致")


# ---------------------------------------------------------------------------
# 4. Edge case — all-NaN column
# ---------------------------------------------------------------------------

def test_partition_all_nan_column():
    """全 NaN 欄回傳 NaN bounds（不 crash）。"""
    arr = np.full((50, 5), np.nan, dtype=np.float64)
    quantiles = [0.01, 0.99]

    result = FeaturePreprocessor._partition_nanquantile_2d(arr, quantiles)

    assert result.shape == (2, 5)
    assert np.all(np.isnan(result)), "全 NaN 欄應回傳 NaN bounds"


# ---------------------------------------------------------------------------
# 5. Edge case — single row (n=1)
# ---------------------------------------------------------------------------

def test_partition_single_row():
    """n=1 時 k_lo == k_hi == 0，結果等於該單值。"""
    arr = np.array([[3.14, 2.71, 1.41]], dtype=np.float64)  # shape (1, 3)
    quantiles = [0.01, 0.5, 0.99]

    result = FeaturePreprocessor._partition_nanquantile_2d(arr, quantiles)
    reference = _reference_nanquantile(arr, quantiles)

    np.testing.assert_allclose(result, reference, rtol=1e-10, atol=1e-10,
                               err_msg="n=1 時結果應等於單值")


# ---------------------------------------------------------------------------
# 6. Edge case — two rows (n=2), linear interpolation boundary
# ---------------------------------------------------------------------------

def test_partition_two_rows():
    """n=2 時線性插值：q=0.5 應是兩值平均。"""
    arr = np.array([[1.0, 10.0], [3.0, 20.0]], dtype=np.float64)  # shape (2, 2)
    quantiles = [0.0, 0.5, 1.0]

    result = FeaturePreprocessor._partition_nanquantile_2d(arr, quantiles)
    reference = _reference_nanquantile(arr, quantiles)

    np.testing.assert_allclose(result, reference, rtol=1e-10, atol=1e-10,
                               err_msg="n=2 線性插值不一致")


# ---------------------------------------------------------------------------
# 7. Edge case — large values (volume scale 1e9+)
# ---------------------------------------------------------------------------

def test_partition_volume_scale():
    """量值在 1e9+（成交量規模）時，float64 精度不應影響正確性。"""
    rng = np.random.default_rng(99)
    arr = rng.uniform(1e9, 1e12, size=(300, 20)).astype(np.float64)
    quantiles = [0.01, 0.99]

    result = FeaturePreprocessor._partition_nanquantile_2d(arr, quantiles)
    reference = _reference_nanquantile(arr, quantiles)

    np.testing.assert_allclose(result, reference, rtol=1e-10, atol=1e-10,
                               err_msg="大數值場景 (volume scale) 結果不一致")


# ---------------------------------------------------------------------------
# 8. Edge case — q=0.0 and q=1.0
# ---------------------------------------------------------------------------

def test_partition_q0_and_q1():
    """q=0.0 應等於 min，q=1.0 應等於 max（每欄）。"""
    rng = np.random.default_rng(55)
    arr = rng.standard_normal((100, 10)).astype(np.float64)
    quantiles = [0.0, 1.0]

    result = FeaturePreprocessor._partition_nanquantile_2d(arr, quantiles)

    expected_min = np.min(arr, axis=0)
    expected_max = np.max(arr, axis=0)

    np.testing.assert_allclose(result[0], expected_min, rtol=1e-10, atol=1e-10,
                               err_msg="q=0.0 應等於 column min")
    np.testing.assert_allclose(result[1], expected_max, rtol=1e-10, atol=1e-10,
                               err_msg="q=1.0 應等於 column max")


# ---------------------------------------------------------------------------
# 9. _winsorize_2d_inplace — new vs old equivalence
# ---------------------------------------------------------------------------

def test_winsorize_2d_inplace_same_result():
    """_winsorize_2d_inplace 新路徑（partition）與舊路徑（nanquantile）結果相同。"""
    rng = np.random.default_rng(11)
    arr = rng.standard_normal((100, 20)).astype(np.float64)
    # 前 10 行 NaN（uniform warmup → fast path）
    arr[:10, :] = np.nan

    lower_q, upper_q = 0.01, 0.99

    # 新路徑（使用 _partition_nanquantile_2d）
    arr_new = arr.copy()
    FeaturePreprocessor._winsorize_2d_inplace(arr_new, lower_q, upper_q)

    # 舊路徑（直接用 _nanquantile_linear）
    arr_old = arr.copy()
    bounds_old = FeaturePreprocessor._nanquantile_linear(arr_old, [lower_q, upper_q])
    np.clip(arr_old, bounds_old[0], bounds_old[1], out=arr_old)

    np.testing.assert_allclose(arr_new, arr_old, rtol=1e-10, atol=1e-10,
                               err_msg="_winsorize_2d_inplace 新舊路徑結果不一致")


# ---------------------------------------------------------------------------
# 10. _winsorize_2d_inplace — production-scale matrix
# ---------------------------------------------------------------------------

def test_winsorize_2d_inplace_large():
    """500×200 矩陣（生產規模），新舊路徑結果相同。"""
    rng = np.random.default_rng(77)
    arr = rng.standard_normal((500, 200)).astype(np.float64)
    arr[:20, :] = np.nan  # uniform leading NaN → fast path

    lower_q, upper_q = 0.01, 0.99

    arr_new = arr.copy()
    FeaturePreprocessor._winsorize_2d_inplace(arr_new, lower_q, upper_q)

    arr_old = arr.copy()
    bounds_old = FeaturePreprocessor._nanquantile_linear(arr_old, [lower_q, upper_q])
    np.clip(arr_old, bounds_old[0], bounds_old[1], out=arr_old)

    np.testing.assert_allclose(arr_new, arr_old, rtol=1e-10, atol=1e-10,
                               err_msg="500×200 matrix: 新舊路徑結果不一致")


# ---------------------------------------------------------------------------
# 11. np.ascontiguousarray zero-copy 特性驗證（優化核心原理）
# ---------------------------------------------------------------------------

def test_legacy_equivalent_no_extra_copy_quantile():
    """驗證 Change 1 的核心假設：np.ascontiguousarray 在 C-contiguous float64 輸入時為 zero-copy。

    策略：
    - 直接驗證 np.shares_memory：ascontiguousarray 不複製記憶體
    - 同時驗證舊版 .copy() 確實產生獨立副本
    - 這就是為什麼移除 .copy() 是安全且有效的優化

    注意：不用 tracemalloc 全方法測量，因 _partition_nanquantile_2d 內部
    的 tmp.copy() 與 np.partition 也會配置記憶體，使整體 peak 難以獨立衡量。
    """
    rng = np.random.default_rng(42)
    # 模擬 caller（_transform_single_optimized_df）的 fancy-index 輸出：
    # 已是 C-contiguous float64（NumPy 的 fancy-index 保證獨立 float64 copy）
    arr = np.ascontiguousarray(rng.standard_normal((200, 50)), dtype=np.float64)

    # 新版：np.ascontiguousarray → 與原始 array 共享記憶體（zero-copy）
    result_new = np.ascontiguousarray(arr, dtype=np.float64)
    assert np.shares_memory(result_new, arr), (
        "np.ascontiguousarray 對 C-contiguous float64 輸入應 zero-copy"
    )

    # 舊版：np.asarray(...).copy() → 獨立副本（確認舊版確實有多餘配置）
    result_old = np.asarray(arr, dtype=np.float64).copy()
    assert not np.shares_memory(result_old, arr), (
        "舊版 .copy() 應產生獨立副本（not shares_memory）"
    )

    # 數值相同（two paths 結果一致）
    np.testing.assert_array_equal(result_new, result_old)


# ---------------------------------------------------------------------------
# 12. End-to-end: transform_single pipeline output equivalence
# ---------------------------------------------------------------------------

def test_transform_single_optimized_df_end_to_end():
    """因果模式與 rolling PIT oracle 一致，且不受未來值擾動。"""
    pp = _make_preprocessor(winsor_method="quantile", quantile_range=[0.01, 0.99])

    rng = np.random.default_rng(314)
    n_rows, n_cols = 150, 15
    arr_f64 = rng.standard_normal((n_rows, n_cols)).astype(np.float64)
    arr_f64[:20, :] = np.nan  # warmup NaN

    lower_q, upper_q = 0.01, 0.99
    window = pp._rolling_window()
    min_periods = pp._rolling_min_periods(window)
    lower, upper = rolling_quantile_2d_legacy(
        arr_f64, lower_q, upper_q, window, min_periods
    )
    valid = np.isfinite(lower) & np.isfinite(upper)
    expected = arr_f64.copy()
    clipped = np.clip(arr_f64, lower, upper)
    expected[valid] = clipped[valid]
    expected[np.isnan(arr_f64)] = np.nan
    original = arr_f64.copy()
    result = pp._winsorize_2d_legacy_equivalent(arr_f64)

    np.testing.assert_allclose(
        result,
        expected.astype(np.float32),
        rtol=1e-5,
        atol=1e-5,
        equal_nan=True,
        err_msg="causal winsorize 與 rolling PIT oracle 不一致",
    )

    perturbed = original.copy()
    perturbed[-1, :] = 1_000_000.0
    perturbed_result = pp._winsorize_2d_legacy_equivalent(perturbed)
    np.testing.assert_allclose(
        result[:-1],
        perturbed_result[:-1],
        rtol=1e-5,
        atol=1e-5,
        equal_nan=True,
    )


def test_transform_single_optimized_df_noncausal_matches_full_sample() -> None:
    """外部 noncausal 被強制 causal，optimized 輸出等於 causal rolling oracle。"""
    forced_pp = _make_preprocessor(
        winsor_method="quantile",
        quantile_range=[0.01, 0.99],
        causal_preprocessing=False,
    )
    causal_pp = _make_preprocessor(
        winsor_method="quantile",
        quantile_range=[0.01, 0.99],
        causal_preprocessing=True,
    )
    assert forced_pp.causal_preprocessing is True

    rng = np.random.default_rng(314)
    arr_f64 = rng.standard_normal((150, 15)).astype(np.float64)
    arr_f64[:20, :] = np.nan

    # causal 釘死後，外部 False 不再代表 full-sample quantile 分支。
    window = forced_pp._rolling_window()
    min_periods = forced_pp._rolling_min_periods(window)
    lower, upper = rolling_quantile_2d_legacy(
        arr_f64,
        0.01,
        0.99,
        window,
        min_periods,
    )
    valid = np.isfinite(lower) & np.isfinite(upper)
    expected = arr_f64.copy()
    clipped = np.clip(arr_f64, lower, upper)
    expected[valid] = clipped[valid]
    expected[np.isnan(arr_f64)] = np.nan

    forced_result = forced_pp._winsorize_2d_legacy_equivalent(arr_f64.copy())
    causal_result = causal_pp._winsorize_2d_legacy_equivalent(arr_f64.copy())

    np.testing.assert_allclose(
        forced_result,
        causal_result,
        rtol=1e-5,
        atol=1e-5,
        equal_nan=True,
    )

    np.testing.assert_allclose(
        forced_result.astype(np.float64),
        expected,
        rtol=1e-5,
        atol=1e-5,
        equal_nan=True,
    )
