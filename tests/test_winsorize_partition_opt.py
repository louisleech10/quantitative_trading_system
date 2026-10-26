"""
tests/test_winsorize_partition_opt.py

驗證 L6.5 winsorization 優化的正確性與邊界條件：
  1. _winsorize_2d_legacy_equivalent 多餘 copy 已消除
  2. 完整 pipeline end-to-end 等價
（原 partition 分位與 2D in-place 縮尾之並存實作已於 FFPROD Task 1.1 刪除：生產無呼叫者，其等價案一併移除。）

執行：
  ./venv/bin/pytest tests/test_winsorize_partition_opt.py -v
"""

from __future__ import annotations

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


# ---------------------------------------------------------------------------
# 11. np.ascontiguousarray zero-copy 特性驗證（優化核心原理）
# ---------------------------------------------------------------------------

def test_legacy_equivalent_no_extra_copy_quantile():
    """驗證 Change 1 的核心假設：np.ascontiguousarray 在 C-contiguous float64 輸入時為 zero-copy。

    策略：
    - 直接驗證 np.shares_memory：ascontiguousarray 不複製記憶體
    - 同時驗證舊版 .copy() 確實產生獨立副本
    - 這就是為什麼移除 .copy() 是安全且有效的優化

    注意：不用 tracemalloc 全方法測量，因分位計算內部之暫存複本也會配置記憶體，使整體 peak 難以獨立衡量。
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

def _oracle_mask_incomplete_window(expected: np.ndarray, window: int) -> np.ndarray:
    """FFSTAT b4（SPEC v32 逐欄穩定點第①類）：縮尾輸出逐欄自首個有限值起 window−1 列（及其前）不穩定 ⇒ NaN。
    獨立於生產 `stable_mask.mask_incomplete_window_inplace` 之逐欄迴圈實作；其後各值仍須與 oracle 逐值相等。"""
    out = expected.copy()
    for j in range(out.shape[1]):
        finite = np.flatnonzero(np.isfinite(expected[:, j]))
        cut = out.shape[0] if finite.size == 0 else min(int(finite[0]) + int(window) - 1, out.shape[0])
        out[:cut, j] = np.nan
    return out


def test_transform_single_optimized_df_end_to_end():
    """因果模式與 rolling PIT oracle 一致，且不受未來值擾動。"""
    pp = _make_preprocessor(winsor_method="quantile", quantile_range=[0.01, 0.99])

    rng = np.random.default_rng(314)
    # FFSTAT b4：縮尾窗 252 之不完整窗遮罩 ⇒ 列數須 > 20＋251 方有可比之值（原 150 列遮罩後全 NaN）
    n_rows, n_cols = 400, 15
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
    expected = _oracle_mask_incomplete_window(expected, window)
    assert np.isfinite(expected).sum() > 0, "前提：遮罩後仍有可比之有限值"
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
    arr_f64 = rng.standard_normal((400, 15)).astype(np.float64)  # FFSTAT b4：同上，須 > 20＋251 列
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
    expected = _oracle_mask_incomplete_window(expected, window)
    assert np.isfinite(expected).sum() > 0, "前提：遮罩後仍有可比之有限值"

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
