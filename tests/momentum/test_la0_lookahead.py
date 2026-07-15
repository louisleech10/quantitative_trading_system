"""LA-0 M-lookahead mutation 測試（B1 骨架 + B2 rolling IC + B3 mono/turnover PIT）。

SPEC: docs/IC_LA0_SPEC.md LA0-1 / LA0-2 / RULING-1 / RULING-2 / RULING-5
TODO: docs/IC_LA0_TODO.md Task 2.1 / 3.1 / 3.2

B1 交付 fixture + truncate helper。
B2 填 ``test_rolling_ic_pit``（P0-1 rolling IC 窗內 rank）。
B3 填 ``test_mono_pit`` / ``test_turnover_pit``。
B4 / B6 仍為 placeholder。
"""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_engine import ICEngine
from momentum.Analysis.monotonicity_tester import MonotonicityTester
from momentum.Analysis.pit_stats import MIN_SAMPLES, first_valid_index
from momentum.Analysis.turnover_analyzer import TurnoverAnalyzer

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
# B3 — P0-2 mono / turnover PIT（M-lookahead + mutation）
# ---------------------------------------------------------------------------


def _build_mono_feature_label(
    kline: pd.DataFrame,
    n_rows: int = 400,
) -> Tuple[pd.Series, pd.Series]:
    close = _close_col(kline).iloc[:n_rows].reset_index(drop=True)
    feature = close.pct_change(5).rename("feature")
    label = close.pct_change(-1).rename("label")
    return feature, label


def test_mono_pit(la0_real_kline: Dict[str, pd.DataFrame]) -> None:
    """P0-2 mono：主錨 early bin_t equal；mutation 回退全窗 qcut→FAIL；score 為 float scalar。

    驗收（TODO Task 3.1）:
      1. 截尾 → early bin_t element-equal（atol 1e-12）
      2. mutation：legacy 全窗 qcut → early equal 必須 FAIL
      3. mono score 型別 float scalar
    """
    kline = la0_real_kline["BTCUSDT_1h"]
    tr = 40
    num_q = 5
    tester = MonotonicityTester({"num_quantiles": num_q, "min_group_size": 10})

    feature, label = _build_mono_feature_label(kline, n_rows=400)
    # 在 production 的 joint dropna 樣本上截尾，避免 feature/label 各自 NaN 對齊漂移
    data_full = tester._prepare_data(feature, label)
    assert len(data_full) > MIN_SAMPLES + tr + 20
    data_trunc = data_full.iloc[:-tr].copy()

    bins_full = tester._assign_quantiles(data_full, num_q)
    bins_trunc = tester._assign_quantiles(data_trunc, num_q)
    assert bins_full is not None and bins_trunc is not None

    # 主錨：early bin_t equal（prepared 序列前 n-TR）
    early_full = bins_full.iloc[:-tr].to_numpy(dtype=float)
    early_trunc = bins_trunc.to_numpy(dtype=float)
    assert early_full.shape == early_trunc.shape
    np.testing.assert_allclose(
        early_full,
        early_trunc,
        atol=ATOL_F64,
        equal_nan=True,
        err_msg="mono PIT early bin_t M-lookahead failed",
    )
    assert np.isfinite(early_full).sum() > 10

    # scalar 契約
    qret = tester.compute_quantile_returns(feature, label, num_quantiles=num_q)
    score = tester.compute_monotonicity_score(qret)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0

    # mutation：legacy 全窗 qcut → early equal 必須 FAIL
    try:
        legacy_full = pd.qcut(
            data_full["feature"], q=num_q, labels=False, duplicates="drop"
        )
        legacy_trunc = pd.qcut(
            data_trunc["feature"], q=num_q, labels=False, duplicates="drop"
        )
    except ValueError as exc:  # pragma: no cover
        pytest.fail(f"legacy qcut failed unexpectedly: {exc}")
    with pytest.raises(AssertionError):
        np.testing.assert_allclose(
            legacy_full.iloc[:-tr].to_numpy(dtype=float),
            legacy_trunc.to_numpy(dtype=float),
            atol=ATOL_F64,
            equal_nan=True,
        )


def test_turnover_array_len_and_warmup_null(
    la0_real_kline: Dict[str, pd.DataFrame],
) -> None:
    """S2 / RULING-5 contract（TODO Task 3.2 指定 nodeid）。

    鎖：
      - len(array) == 源 raw n
      - warmup [0, first_valid) 為 JSON null
      - index first_valid 非 null（== 0.0；首個可算 bar 無前態 → change=0）
    """
    kline = la0_real_kline["BTCUSDT_1h"]
    analyzer = TurnoverAnalyzer({"num_quantiles": 5})
    feature, _ = _build_mono_feature_label(kline, n_rows=400)
    raw = feature  # 源 raw index（含 NaN 頭段）— 不 dropna
    n = len(raw)
    assert n > MIN_SAMPLES + 20

    ts = analyzer.compute_turnover_time_series(raw, num_quantiles=5)
    fv = first_valid_index(raw, min_samples=MIN_SAMPLES)
    assert fv is not None
    assert fv >= MIN_SAMPLES - 1

    for key in ("quantile_turnovers", "rank_change_rates"):
        arr = ts[key]
        assert len(arr) == n, f"{key} len must == 源 raw n ({n})"
        assert all(v is None for v in arr[:fv]), (
            f"{key} warmup [0, first_valid) must be JSON null"
        )
        # RULING-5：t=first_valid 本身 valid 不 null（首 bar change=0.0）
        assert arr[fv] is not None, (
            f"{key}[{fv}] must be non-null at first_valid (got null — 假綠若放寬)"
        )
        assert abs(float(arr[fv]) - 0.0) <= ATOL_F64, (
            f"{key}[{fv}] must be 0.0 at first_valid, got {arr[fv]!r}"
        )

    assert len(ts["timestamps"]) == n


def test_turnover_pit(la0_real_kline: Dict[str, pd.DataFrame]) -> None:
    """P0-2 turnover：early equal + len==源 n + warmup null contract；mutation 回退全域→FAIL。

    驗收（TODO Task 3.2 / S2 / RULING-5）:
      1. 截尾 → early turnover/rank_change equal
      2. len(array)==源 raw n 且 warmup [0, first_valid) 為 JSON null；
         first_valid 本身 == 0.0（非 null）
      3. mutation：legacy 全域 qcut/rank + dropna → contract/early FAIL
    """
    kline = la0_real_kline["BTCUSDT_1h"]
    tr = 40
    analyzer = TurnoverAnalyzer({"num_quantiles": 5})

    feature, _ = _build_mono_feature_label(kline, n_rows=400)
    # 源 raw index（含 NaN 頭段）— 不 dropna
    raw = feature
    raw_t = truncate_future(raw, tr)
    n = len(raw)
    assert n > MIN_SAMPLES + tr + 20

    ts_full = analyzer.compute_turnover_time_series(raw, num_quantiles=5)
    ts_trunc = analyzer.compute_turnover_time_series(raw_t, num_quantiles=5)

    # --- contract: len == 源 raw n + warmup null + first_valid == 0.0 ---
    assert len(ts_full["quantile_turnovers"]) == n
    assert len(ts_full["rank_change_rates"]) == n
    assert len(ts_full["timestamps"]) == n
    fv = first_valid_index(raw, min_samples=MIN_SAMPLES)
    assert fv is not None
    assert all(v is None for v in ts_full["quantile_turnovers"][:fv])
    assert all(v is None for v in ts_full["rank_change_rates"][:fv])
    # RULING-5：t=first_valid 本身 valid 不 null（==0.0）；禁放寬為「不強制 non-null」
    assert ts_full["quantile_turnovers"][fv] is not None
    assert ts_full["rank_change_rates"][fv] is not None
    assert abs(float(ts_full["quantile_turnovers"][fv]) - 0.0) <= ATOL_F64
    assert abs(float(ts_full["rank_change_rates"][fv]) - 0.0) <= ATOL_F64
    # first_valid dense with leading NaN from pct_change may be > 99
    assert fv >= MIN_SAMPLES - 1

    # --- M-lookahead early equal on finite post-warmup segment ---
    keep = n - tr
    for key in ("quantile_turnovers", "rank_change_rates"):
        full_arr = ts_full[key][:keep]
        trunc_arr = ts_trunc[key][:keep]
        # None-safe compare
        for i, (a, b) in enumerate(zip(full_arr, trunc_arr)):
            if a is None and b is None:
                continue
            if a is None or b is None:
                raise AssertionError(f"{key}[{i}] null mismatch: {a!r} vs {b!r}")
            assert abs(float(a) - float(b)) <= ATOL_F64, (
                f"{key}[{i}] early equal fail: {a} vs {b}"
            )

    # scalar paths also finite after enough history
    qt = analyzer.compute_quantile_turnover(raw, num_quantiles=5)
    rc = analyzer.compute_rank_change_rate(raw)
    assert np.isfinite(qt)
    assert np.isfinite(rc)

    # --- mutation: legacy global qcut/rank + dropna → length n-1 且 early 洩漏 ---
    def _legacy_turnover_ts(series: pd.Series) -> dict:
        s = series.dropna()
        if s.empty or s.size < 2:
            return {"quantile_turnovers": [], "rank_change_rates": []}
        quantiles = pd.qcut(s, q=5, labels=False, duplicates="drop")
        top_mask = (quantiles == quantiles.max()).astype(float)
        q_to = top_mask.diff().abs().dropna().astype(float)
        ranks = s.rank(method="average")
        r_ch = ranks.diff().abs().dropna().astype(float)
        common = q_to.index.intersection(r_ch.index)
        return {
            "quantile_turnovers": [float(v) for v in q_to.loc[common].tolist()],
            "rank_change_rates": [float(v) for v in r_ch.loc[common].tolist()],
        }

    legacy_full = _legacy_turnover_ts(raw)
    legacy_trunc = _legacy_turnover_ts(raw_t)
    # S2 contract must FAIL for legacy (n-1, no null warmup)
    assert len(legacy_full["quantile_turnovers"]) != n
    with pytest.raises(AssertionError):
        assert len(legacy_full["quantile_turnovers"]) == n
        assert all(v is None for v in legacy_full["quantile_turnovers"][:fv])

    # early value leak: truncate changes early global ranks
    # compare prefix of legacy arrays (aligned by position after dropna)
    lf = np.asarray(legacy_full["rank_change_rates"][: max(0, keep - 5)], dtype=float)
    lt = np.asarray(legacy_trunc["rank_change_rates"][: len(lf)], dtype=float)
    if len(lf) > 20 and len(lt) == len(lf):
        with pytest.raises(AssertionError):
            np.testing.assert_allclose(lf, lt, atol=ATOL_F64, equal_nan=True)


# ---------------------------------------------------------------------------
# Placeholders — B4 / B6 填入（勿刪 nodeid 名稱）
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="B4: P0-3 preprocessor pit_expanding M-lookahead — not in B1 scope")
def test_preproc_pit() -> None:
    """B4 nodeid placeholder."""


@pytest.mark.skip(reason="B6: cross-symbol isolation — not in B1 scope")
def test_cross_symbol_isolation() -> None:
    """B6 nodeid placeholder."""


@pytest.mark.skip(reason="B6: attribution schema validator — not in B1 scope")
def test_attribution_schema_valid() -> None:
    """B6 nodeid placeholder."""
