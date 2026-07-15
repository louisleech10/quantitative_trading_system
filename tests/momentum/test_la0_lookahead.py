"""LA-0 M-lookahead mutation 測試（B1 骨架 + B2 rolling IC PIT）。

SPEC: docs/IC_LA0_SPEC.md LA0-1 / RULING-1
TODO: docs/IC_LA0_TODO.md Task 2.1

B1 交付 fixture + truncate helper。
B2 填 ``test_rolling_ic_pit``（P0-1 rolling IC 窗內 rank）。
B3–B4 / B6 仍為 placeholder。
"""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_engine import ICEngine

# ---------------------------------------------------------------------------
# 共用 helper（B2–B6 引用）
# ---------------------------------------------------------------------------

ATOL_F64 = 1e-12
ATOL_F32 = 1e-6


def truncate_future(df: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """截掉最後 n 根 bar（模擬「未來未發生」）供 M-lookahead 早期 equal 對照。

    n <= 0 → 原序列 copy；n >= len → 空序列（保 columns / name / dtype）。
    """
    if n <= 0:
        return df.copy()
    if n >= len(df):
        return df.iloc[0:0].copy()
    return df.iloc[:-n].copy()


def _close_col(df: pd.DataFrame) -> pd.Series:
    if "close" in df.columns:
        return df["close"].astype(float)
    lower = {c.lower(): c for c in df.columns}
    if "close" in lower:
        return df[lower["close"]].astype(float)
    raise KeyError("kline missing close column")


def _build_rolling_ic_inputs(
    kline: pd.DataFrame,
    n_rows: int = 400,
    dtype: np.dtype = np.dtype(np.float64),
) -> Tuple[pd.DataFrame, pd.Series]:
    """從真實 kline 建簡單特徵 + forward return label（供 rolling IC）。"""
    close = _close_col(kline).iloc[:n_rows].reset_index(drop=True)
    # 簡單因果特徵：過去 return / 過去 rolling mean 差（無未來）
    ret1 = close.pct_change(1)
    ret5 = close.pct_change(5)
    ma10 = close.rolling(10, min_periods=1).mean()
    features = pd.DataFrame(
        {
            "ret1": ret1.to_numpy(dtype=dtype),
            "ret5": ret5.to_numpy(dtype=dtype),
            "dev_ma10": (close - ma10).to_numpy(dtype=dtype),
        }
    )
    # label = 下一 bar return（drop 末列 NaN 由 compute_rolling_ic 的 dropna 處理）
    label = close.pct_change(-1).rename("label").astype(dtype)
    return features, label


def _early_emitted_indices(
    n_bars: int, window: int, stride: int, truncate_n: int
) -> List[int]:
    """emitted end-inclusive index = window-1 + k*stride；保留 end < n-TR 的 k。"""
    keep: List[int] = []
    k = 0
    while True:
        end_inclusive = window - 1 + k * stride
        if end_inclusive >= n_bars:
            break
        if end_inclusive < n_bars - truncate_n:
            keep.append(k)
        k += 1
    return keep


def _legacy_global_rank_rolling_ic(
    features_df: pd.DataFrame,
    label: pd.Series,
    windows: List[int],
    stride: int = 1,
) -> dict:
    """Legacy leak path：全序列 pre-rank 後 rolling pearson（mutation oracle）。"""
    engine = ICEngine({})
    label_name = label.name or "label"
    aligned = pd.concat([features_df, label.rename(label_name)], axis=1).dropna()
    if aligned.empty:
        return {name: {} for name in features_df.columns}
    ranked_x = aligned[features_df.columns].rank(axis=0, method="average")
    ranked_y = aligned[label_name].rank(method="average")
    x_values = ranked_x.to_numpy(dtype=float)
    y_values = ranked_y.to_numpy(dtype=float)
    results: dict = {name: {} for name in features_df.columns}
    for window in windows:
        corr = ICEngine._rolling_corr_matrix(x_values, y_values, window, stride)
        key = f"window_{window}"
        for idx, feature in enumerate(features_df.columns):
            results[feature][key] = corr[:, idx].tolist()
    return results


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def la0_real_kline(
    requires_kline_data: Callable[..., pd.DataFrame],
) -> Dict[str, pd.DataFrame]:
    """真實 kline load：BTCUSDT/1h（主）+ ETHUSDT/12h（跨 TF）。

    function-scoped（對齊 conftest ``requires_kline_data``）。
    缺檔 / 列數不足 → requires_kline_data 以 pytest.fail 硬失敗（非 skip）。
    """
    btc = requires_kline_data("BTCUSDT", "1h", min_rows=500)
    eth = requires_kline_data("ETHUSDT", "12h", min_rows=200)
    return {
        "BTCUSDT_1h": btc,
        "ETHUSDT_12h": eth,
    }


# ---------------------------------------------------------------------------
# B1 smoke：fixture + truncate 可運作
# ---------------------------------------------------------------------------


def test_la0_fixture_loads_real_kline(la0_real_kline: Dict[str, pd.DataFrame]) -> None:
    btc = la0_real_kline["BTCUSDT_1h"]
    eth = la0_real_kline["ETHUSDT_12h"]
    assert len(btc) >= 500
    assert len(eth) >= 200
    assert "close" in btc.columns or "close" in [c.lower() for c in btc.columns]


def test_truncate_future_helper(la0_real_kline: Dict[str, pd.DataFrame]) -> None:
    btc = la0_real_kline["BTCUSDT_1h"]
    tr = 50
    trunc = truncate_future(btc, tr)
    assert isinstance(trunc, pd.DataFrame)
    assert len(trunc) == len(btc) - tr
    # 早期 equal
    pd.testing.assert_frame_equal(btc.iloc[: len(trunc)], trunc)
    # n=0 identity copy
    same = truncate_future(btc, 0)
    assert len(same) == len(btc)
    # over-truncate → empty
    empty = truncate_future(btc, len(btc) + 10)
    assert len(empty) == 0


# ---------------------------------------------------------------------------
# B2 — P0-1 rolling IC 窗內 rank（M-lookahead + mutation + pearson control）
# ---------------------------------------------------------------------------


def test_rolling_ic_pit(la0_real_kline: Dict[str, pd.DataFrame]) -> None:
    """P0-1：spearman 窗內 rank 無 look-ahead；mutation 回退全域 rank→FAIL；pearson control 不變。

    驗收（TODO Task 2.1）:
      1. 截尾 → 早期 pure-TEST IC element-equal（emitted ends）
      2. float64 atol=1e-12 / float32 atol=1e-6
      3. mutation：legacy 全域 pre-rank 路徑 M-lookahead 必須 FAIL
      4. pearson control：截尾早期 equal 仍 pass
    """
    kline = la0_real_kline["BTCUSDT_1h"]
    window, stride, tr = 21, 1, 40
    engine = ICEngine({})

    def _assert_early_equal(
        method: str,
        dtype: np.dtype,
        atol: float,
        *,
        force_legacy_global_rank: bool = False,
    ) -> None:
        features, label = _build_rolling_ic_inputs(kline, n_rows=400, dtype=dtype)
        # dropna 後長度 = 有效對齊列數
        aligned_n = int(
            pd.concat([features, label.rename("label")], axis=1).dropna().shape[0]
        )
        assert aligned_n > window + tr + 5

        feat_t = truncate_future(features, tr)
        lab_t = truncate_future(label, tr)

        if force_legacy_global_rank:
            full = _legacy_global_rank_rolling_ic(
                features, label, windows=[window], stride=stride
            )
            trunc = _legacy_global_rank_rolling_ic(
                feat_t, lab_t, windows=[window], stride=stride
            )
        else:
            full = engine.compute_rolling_ic(
                features, label, windows=[window], stride=stride, method=method
            )
            trunc = engine.compute_rolling_ic(
                feat_t, lab_t, windows=[window], stride=stride, method=method
            )

        key = f"window_{window}"
        # 用 aligned length 算 emitted ends（與 dropna 後序列一致）
        # 截尾後 aligned 約 short tr（特徵/label 同 index）
        keep = _early_emitted_indices(aligned_n, window, stride, tr)
        assert len(keep) > 10, "need enough early emitted ends for discrimination"

        for col in features.columns:
            full_arr = np.asarray(full[col][key], dtype=np.float64)
            trunc_arr = np.asarray(trunc[col][key], dtype=np.float64)
            assert full_arr.shape[0] == (aligned_n - window) // stride + 1
            # trunc aligned length ≈ aligned_n - tr（dropna 後同切）
            trunc_aligned_n = int(
                pd.concat([feat_t, lab_t.rename("label")], axis=1).dropna().shape[0]
            )
            assert trunc_arr.shape[0] == (trunc_aligned_n - window) // stride + 1
            np.testing.assert_allclose(
                full_arr[keep],
                trunc_arr[: len(keep)],
                atol=atol,
                equal_nan=True,
                err_msg=f"M-lookahead early equal failed method={method} col={col}",
            )

    # --- 1) spearman float64: 修後 must PASS ---
    _assert_early_equal("spearman", np.dtype(np.float64), ATOL_F64)

    # --- 2) spearman float32: 修後 must PASS (looser atol) ---
    _assert_early_equal("spearman", np.dtype(np.float32), ATOL_F32)

    # --- 3) mutation: legacy 全域 rank → early equal 必須 FAIL ---
    with pytest.raises(AssertionError):
        _assert_early_equal(
            "spearman",
            np.dtype(np.float64),
            ATOL_F64,
            force_legacy_global_rank=True,
        )

    # --- 4) pearson control: 截尾 early equal 仍 pass（路徑未改）---
    _assert_early_equal("pearson", np.dtype(np.float64), ATOL_F64)

    # --- 5) 輸出長度契約：emitted window-ends ---
    features, label = _build_rolling_ic_inputs(kline, n_rows=300)
    rolling = engine.compute_rolling_ic(
        features, label, windows=[21, 63], stride=1, method="spearman"
    )
    aligned_n = int(
        pd.concat([features, label.rename("label")], axis=1).dropna().shape[0]
    )
    for w in (21, 63):
        if aligned_n >= w:
            expected_len = (aligned_n - w) // 1 + 1
        else:
            expected_len = 0
        for col in features.columns:
            assert len(rolling[col][f"window_{w}"]) == expected_len


# ---------------------------------------------------------------------------
# Placeholders — B3 / B4 / B6 填入（勿刪 nodeid 名稱）
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="B3: P0-2 mono/turnover M-lookahead mutation — not in B1 scope")
def test_mono_turnover_pit() -> None:
    """B3 nodeid placeholder."""


@pytest.mark.skip(reason="B4: P0-3 preprocessor pit_expanding M-lookahead — not in B1 scope")
def test_preproc_pit() -> None:
    """B4 nodeid placeholder."""


@pytest.mark.skip(reason="B6: cross-symbol isolation — not in B1 scope")
def test_cross_symbol_isolation() -> None:
    """B6 nodeid placeholder."""


@pytest.mark.skip(reason="B6: attribution schema validator — not in B1 scope")
def test_attribution_schema_valid() -> None:
    """B6 nodeid placeholder."""
