"""LA-0 M-lookahead mutation 測試（B1–B6）。

SPEC: docs/IC_LA0_SPEC.md LA0-1 / LA0-2 / LA0-3 / LA0-5 / RULING-1..5 / §G
TODO: docs/IC_LA0_TODO.md Task 2.1 / 3.1 / 3.2 / 4.1 / 4.2 / 6.1

B1 交付 fixture + truncate helper。
B2 填 ``test_rolling_ic_pit``（P0-1 rolling IC 窗內 rank）。
B3 填 ``test_mono_pit`` / ``test_turnover_pit``。
B4 填 ``test_preproc_pit``。
B6 填 ``test_cross_symbol_isolation`` / ``test_attribution_schema_valid`` /
   ``test_after_golden_deep_equal``（after golden 強 gate）/
   ``test_after_golden_split_off_deep_equal``（flag-off / pit_expanding live gate）。
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.data_preprocessor import DataPreprocessor
from momentum.Analysis.ic_engine import ICEngine
from momentum.Analysis.monotonicity_tester import MonotonicityTester
from momentum.Analysis.pit_stats import MIN_SAMPLES, PIT_STATS_VERSION, first_valid_index
from momentum.Analysis.turnover_analyzer import TurnoverAnalyzer

LA0_GOLDEN_DIR = Path(__file__).resolve().parents[1] / "golden" / "la0"
ATTR_ALLOWLIST = LA0_GOLDEN_DIR / "attribution_allowlist.json"
ATTR_JSON = LA0_GOLDEN_DIR / "attribution.json"
AFTER_BTC = LA0_GOLDEN_DIR / "BTCUSDT_1h_baseline_after.json"
AFTER_ETH = LA0_GOLDEN_DIR / "ETHUSDT_12h_baseline_after.json"
AFTER_BTC_SPLIT_OFF = LA0_GOLDEN_DIR / "BTCUSDT_1h_baseline_after_split_off.json"
AFTER_ETH_SPLIT_OFF = LA0_GOLDEN_DIR / "ETHUSDT_12h_baseline_after_split_off.json"
BEFORE_BTC = LA0_GOLDEN_DIR / "BTCUSDT_1h_baseline.json"
BEFORE_ETH = LA0_GOLDEN_DIR / "ETHUSDT_12h_baseline.json"

CLASS_ENUM = {"expected-leakfix", "expected-downstream", "unexpected"}
REQUIRED_ROW_KEYS = {
    "name",
    "before",
    "after",
    "delta",
    "component",
    "oracle_passed",
    "class",
    "reason",
}
CONTROL_ATOL = 1e-12

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
# B4 — P0-3 preprocessor fit_mode 四出口（M-lookahead + mutation + control）
# ---------------------------------------------------------------------------


def _preproc_config() -> dict:
    return {
        "winsorization": {
            "enabled": True,
            "method": "percentile",
            "lower_percentile": 1.0,
            "upper_percentile": 99.0,
        },
        "missing_values": {"max_fill_forward": 0, "min_coverage": 0.0},
        "standardize": {"method": "none"},
    }


def _feature_frame_from_kline(kline: pd.DataFrame, n_rows: int = 400) -> pd.DataFrame:
    close = _close_col(kline).iloc[:n_rows].reset_index(drop=True)
    ret1 = close.pct_change(1)
    # 注入尾端極端值，使 full_sample winsor 邊界明顯受未來影響
    series = ret1.fillna(0.0).to_numpy(dtype=np.float64).copy()
    if len(series) > 10:
        series[-5:] = series[-5:] + 50.0  # 尾端 outlier
    return pd.DataFrame({"f0": series})


def test_preproc_pit(la0_real_kline: Dict[str, pd.DataFrame]) -> None:
    """P0-3：pit_expanding 截尾 early equal；full_sample mutation FAIL；
    train_mask control 排尾 train 段 equal；unset+None raise。
    """
    kline = la0_real_kline["BTCUSDT_1h"]
    features = _feature_frame_from_kline(kline, n_rows=400)
    tr = 40
    keep = len(features) - tr
    assert keep > MIN_SAMPLES + 20
    first_valid = MIN_SAMPLES - 1  # dense 無 NaN → t=99
    early_slice = slice(first_valid, keep)

    prep = DataPreprocessor(_preproc_config())

    # --- 1) pit_expanding：截尾 → early equal ---
    full_pit, log_pit = prep.preprocess(features, fit_mode="pit_expanding")
    trunc_pit, _ = prep.preprocess(
        truncate_future(features, tr), fit_mode="pit_expanding"
    )
    assert log_pit["fit_mode"] == "pit_expanding"
    assert log_pit["oos_guarantees"] is True
    np.testing.assert_allclose(
        full_pit["f0"].iloc[early_slice].to_numpy(dtype=np.float64),
        trunc_pit["f0"].iloc[first_valid:keep].to_numpy(dtype=np.float64),
        atol=ATOL_F64,
        equal_nan=True,
    )
    # #5：final first-valid == §MS canonical（dense → 99）；禁雙 warmup 198
    const_valid = log_pit.get("per_bar_validity", {}).get("constant", {}).get("f0")
    assert const_valid is not None
    fv_mask = next(i for i, v in enumerate(const_valid) if v)
    fv_data = int(full_pit["f0"].notna().to_numpy().argmax())
    assert fv_mask == first_valid
    assert fv_data == first_valid


    # --- 2) mutation：full_sample 全期 fit → 截尾 early 必變 → FAIL 契約 ---
    full_fs, log_fs = prep.preprocess(features, fit_mode="full_sample")
    trunc_fs, _ = prep.preprocess(
        truncate_future(features, tr), fit_mode="full_sample"
    )
    assert log_fs["fit_mode"] == "full_sample"
    assert log_fs["oos_guarantees"] is False
    with pytest.raises(AssertionError):
        np.testing.assert_allclose(
            full_fs["f0"].iloc[early_slice].to_numpy(dtype=np.float64),
            trunc_fs["f0"].iloc[first_valid:keep].to_numpy(dtype=np.float64),
            atol=ATOL_F64,
            equal_nan=True,
        )

    # --- 3) train_mask control：只污染 test 尾 → train 段 equal ---
    n = len(features)
    train_mask = np.zeros(n, dtype=bool)
    split = int(n * 0.8)
    train_mask[:split] = True
    dirty = features.copy()
    dirty.loc[~train_mask, "f0"] = dirty.loc[~train_mask, "f0"] + 1e3
    clean_tm, log_tm = prep.preprocess(
        features, fit_mask=train_mask, fit_mode="train_mask"
    )
    dirty_tm, _ = prep.preprocess(
        dirty, fit_mask=train_mask, fit_mode="train_mask"
    )
    assert log_tm["fit_mode"] == "train_mask"
    assert log_tm["oos_guarantees"] is True
    np.testing.assert_allclose(
        dirty_tm.loc[train_mask, "f0"].to_numpy(dtype=np.float64),
        clean_tm.loc[train_mask, "f0"].to_numpy(dtype=np.float64),
        atol=ATOL_F64,
        equal_nan=True,
    )

    # --- 4) unset + None → fail-closed ---
    with pytest.raises(ValueError, match="fail-closed"):
        prep.preprocess(features)
    with pytest.raises(ValueError, match="fail-closed"):
        prep.preprocess(features, fit_mask=None, fit_mode="unset")


# ---------------------------------------------------------------------------
# B6 — 跨 symbol 隔離 + 歸因表 validator + after golden deep-equal
# ---------------------------------------------------------------------------


def _hash_series_payload(arr: np.ndarray) -> str:
    out = np.asarray(arr, dtype=np.float64).reshape(-1).copy()
    nan_mask = ~np.isfinite(out)
    out[nan_mask] = -9.87654321e30
    payload = out.tobytes(order="C") + f"|nan_count={int(nan_mask.sum())}".encode()
    return hashlib.sha256(payload).hexdigest()


def test_cross_symbol_isolation(la0_real_kline: Dict[str, pd.DataFrame]) -> None:
    """BTC-only 擾動不得改變 ETH 引擎輸出 hash（跨 symbol/TF 隔離）。

    SPEC §G L3 / TODO Task 6.1 T8。
    """
    btc = la0_real_kline["BTCUSDT_1h"]
    eth = la0_real_kline["ETHUSDT_12h"]
    engine = ICEngine({})
    mono = MonotonicityTester({})
    to_an = TurnoverAnalyzer({})
    prep = DataPreprocessor(_preproc_config())

    def _engine_digest(kline: pd.DataFrame, *, n_rows: int, seed: int) -> str:
        feats, label = _build_rolling_ic_inputs(kline, n_rows=n_rows)
        # 可選 seed 擾動：只在呼叫端對 BTC 注入
        if seed != 0:
            rng = np.random.default_rng(seed)
            noise = rng.normal(0.0, 0.05, size=feats.shape)
            feats = feats + noise

        rolling = engine.compute_rolling_ic(
            feats, label, windows=[21], stride=1, method="spearman"
        )
        f0 = str(feats.columns[0])
        ric = np.asarray(rolling[f0]["window_21"], dtype=np.float64)

        feat_s, lab_s = _build_mono_feature_label(kline, n_rows=n_rows)
        if seed != 0:
            rng = np.random.default_rng(seed + 1)
            feat_s = feat_s + rng.normal(0.0, 0.05, size=len(feat_s))
        data = mono._prepare_data(feat_s, lab_s)
        n_q = mono._select_num_quantiles(len(data), 5)
        bins = mono._assign_quantiles(data, n_q)
        assert bins is not None
        qret = mono.compute_quantile_returns(feat_s, lab_s, num_quantiles=n_q)
        score = float(mono.compute_monotonicity_score(qret))

        q_to = to_an.compute_quantile_turnover(feat_s)
        ts = to_an.compute_turnover_time_series(feat_s)
        pre, _ = prep.preprocess(
            pd.DataFrame({"f0": feat_s.fillna(0.0)}), fit_mode="pit_expanding"
        )

        parts = [
            _hash_series_payload(ric),
            _hash_series_payload(bins.to_numpy(dtype=np.float64)),
            f"mono={score:.12g}",
            f"qto={q_to:.12g}" if q_to is not None and np.isfinite(q_to) else "qto=nan",
            _hash_series_payload(
                np.asarray(ts.get("quantile_turnovers") or [], dtype=np.float64)
            ),
            _hash_series_payload(pre["f0"].to_numpy(dtype=np.float64)),
        ]
        return hashlib.sha256("\n".join(parts).encode()).hexdigest()

    eth_clean = _engine_digest(eth, n_rows=min(400, len(eth)), seed=0)
    # BTC 強擾動
    _ = _engine_digest(btc, n_rows=400, seed=0)
    _ = _engine_digest(btc, n_rows=400, seed=99)
    eth_after_btc_perturb = _engine_digest(eth, n_rows=min(400, len(eth)), seed=0)

    assert eth_clean == eth_after_btc_perturb, (
        "cross-symbol isolation broken: ETH digest changed after BTC-only perturb"
    )


def _load_la0_baseline_maps() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    allow = json.loads(ATTR_ALLOWLIST.read_text(encoding="utf-8"))
    before_map = {
        "BTCUSDT_1h": json.loads(BEFORE_BTC.read_text(encoding="utf-8")),
        "ETHUSDT_12h": json.loads(BEFORE_ETH.read_text(encoding="utf-8")),
    }
    after_map = {
        "BTCUSDT_1h": json.loads(AFTER_BTC.read_text(encoding="utf-8")),
        "ETHUSDT_12h": json.loads(AFTER_ETH.read_text(encoding="utf-8")),
    }
    return allow, before_map, after_map


def test_attribution_schema_valid() -> None:
    """RULING-4 / §G L2：禁洗歸因 validator。

    (a) 每列 class == B0 predeclare allowlist class（禁 silent 重分類）
    (b) 未列 extractable metric 有 diff → unexpected → FAIL
    (c) 非-control expected-leakfix 值變須綁 m_lookahead oracle
    + before/after/delta 可重算（亂改值打紅）+ control-stable + S2
    """
    from tests.golden.la0.build_after_and_attribution import (  # noqa: WPS433
        validate_attribution_payload,
    )

    assert ATTR_ALLOWLIST.is_file(), f"missing {ATTR_ALLOWLIST}"
    assert ATTR_JSON.is_file(), f"missing {ATTR_JSON}"
    assert BEFORE_BTC.is_file() and BEFORE_ETH.is_file()
    assert AFTER_BTC.is_file() and AFTER_ETH.is_file()

    allow, before_map, after_map = _load_la0_baseline_maps()
    attr = json.loads(ATTR_JSON.read_text(encoding="utf-8"))

    validate_attribution_payload(attr, allow, before_map, after_map)

    after_btc = after_map["BTCUSDT_1h"]
    after_eth = after_map["ETHUSDT_12h"]
    assert after_btc.get("baseline_role") == "after_pit"
    assert after_eth.get("baseline_role") == "after_pit"
    assert after_btc.get("pit_stats_version") == PIT_STATS_VERSION
    assert after_eth.get("pit_stats_version") == PIT_STATS_VERSION

    # S2：turnover after len > before（n-1→n）
    s2 = (attr.get("summary") or {}).get("s2_turnover_size") or {}
    b_lens = s2.get("BTCUSDT_1h_before_lens") or {}
    a_lens = s2.get("BTCUSDT_1h_after_lens") or {}
    if b_lens and a_lens:
        for feat in b_lens:
            if feat in a_lens and b_lens[feat] is not None and a_lens[feat] is not None:
                assert int(a_lens[feat]) == int(b_lens[feat]) + 1, (
                    f"S2 size: {feat} before={b_lens[feat]} after={a_lens[feat]}"
                )


def test_attribution_validator_mutation_rejects_wash() -> None:
    """手動亂改非-control 值 / 洗 class / 漏列 metric → validator 必打紅。"""
    from tests.golden.la0 import build_after_and_attribution as b6  # noqa: WPS433

    allow, before_map, after_map = _load_la0_baseline_maps()
    attr = json.loads(ATTR_JSON.read_text(encoding="utf-8"))

    # --- mutation 1：非-control 列 after 值被洗 ---
    dirty = copy.deepcopy(attr)
    target = next(
        r
        for r in dirty["rows"]
        if r["name"] == "rolling_ic_spearman"
    )
    target["after"] = {"digest": "0" * 64, "n_series": 0}
    target["dual_symbol"]["BTCUSDT_1h"]["after"] = target["after"]
    with pytest.raises(AssertionError, match="washed|after"):
        b6.validate_attribution_payload(dirty, allow, before_map, after_map)

    # --- mutation 2：silent 重分類 expected-leakfix → expected-downstream ---
    reclass = copy.deepcopy(attr)
    row_rc = next(r for r in reclass["rows"] if r["name"] == "mono_bin_t")
    assert row_rc["class"] == "expected-leakfix"
    row_rc["class"] = "expected-downstream"
    with pytest.raises(AssertionError, match="washed|class"):
        b6.validate_attribution_payload(reclass, allow, before_map, after_map)

    # --- mutation 3：expected-leakfix 值變但剝除 m_lookahead oracle ---
    no_oracle = copy.deepcopy(attr)
    row_no = next(r for r in no_oracle["rows"] if r["name"] == "turnover_scalar")
    assert abs(float(row_no["delta"])) > 0
    row_no["oracle_passed"] = {"m_lookahead": None, "control": None}
    with pytest.raises(AssertionError, match="m_lookahead|oracle"):
        b6.validate_attribution_payload(no_oracle, allow, before_map, after_map)

    # --- mutation 4：漏列 metric（allowlist 拿掉仍有 diff 的列）→ unlisted ---
    thin_allow = copy.deepcopy(allow)
    thin_allow["rows"] = [
        r for r in thin_allow["rows"] if r["name"] != "icir"
    ]
    # attr 也拿掉 icir 列以通過 name 對齊，但 extractable catalog 仍會掃到 icir diff
    thin_attr = copy.deepcopy(attr)
    thin_attr["rows"] = [r for r in thin_attr["rows"] if r["name"] != "icir"]
    thin_attr["summary"] = dict(thin_attr.get("summary") or {})
    thin_attr["summary"]["n_unexpected"] = 0
    with pytest.raises(AssertionError, match="unlisted"):
        b6.validate_attribution_payload(
            thin_attr, thin_allow, before_map, after_map
        )

    # --- mutation 5：build_attribution 對非-control 無 oracle 可標 unexpected ---
    # 偽造 allow 列：expected-leakfix 但 m_lookahead=null，且 after≠before
    fake_allow = {
        "policy": allow["policy"],
        "rows": [
            {
                "name": "rolling_ic_spearman",
                "before": None,
                "after": None,
                "delta": None,
                "component": "P0-1",
                "oracle_passed": {"m_lookahead": None, "control": None},
                "class": "expected-leakfix",
                "reason": "mutation fake missing oracle",
            },
            next(r for r in allow["rows"] if r["name"] == "control_pearson_rolling_ic"),
        ],
    }
    # 暫時覆寫 OUT allowlist 不可行；直接呼叫 classify + 組 rows
    filled = copy.deepcopy(fake_allow["rows"][0])
    b_v = b6.metric_value(before_map["BTCUSDT_1h"], "rolling_ic_spearman")
    a_v = b6.metric_value(after_map["BTCUSDT_1h"], "rolling_ic_spearman")
    d = b6.delta_of(b_v, a_v)
    assert d != 0.0
    filled["before"] = b_v
    filled["after"] = a_v
    filled["delta"] = d
    cls, reason = b6.classify_row_runtime(filled, d=d, eth_d=d)
    assert cls == "unexpected"
    assert reason == "leakfix_without_m_lookahead_oracle"


def _assert_live_vs_after_golden(
    *,
    before_path: Path,
    after_path: Path,
    key: str,
    config_override: dict[str, Any] | None,
    expected_role: str,
    expect_split: bool,
) -> None:
    """實跑 analyze → element 級 deep-equal vs after golden（非只比靜態 hash）。"""
    from tests.golden.la0.build_after_and_attribution import (  # noqa: WPS433
        collect_after_from_frozen,
        metric_value,
    )

    before = json.loads(before_path.read_text(encoding="utf-8"))
    golden = json.loads(after_path.read_text(encoding="utf-8"))
    live, _telem = collect_after_from_frozen(
        before,
        config_override=config_override,
        baseline_role=expected_role,
    )

    assert golden.get("baseline_role") == expected_role
    assert live.get("baseline_role") == expected_role
    assert bool(live["config_snapshot"]["ic_train_test_split"]) is expect_split
    assert bool(golden["config_snapshot"]["ic_train_test_split"]) is expect_split

    # pearson / spearman / mono / turnover / winsorize（stage1）
    checks = (
        "control_pearson_rolling_ic",
        "rolling_ic_spearman",
        "mono_bin_t",
        "monotonicity_score",
        "turnover_time_series",
        "turnover_scalar",
        "rank_change_time_series",
        "stage1_winsorize_full_sample_fallback",
    )
    if expect_split:
        checks = checks + ("control_train_mask_winsorize",)

    for metric in checks:
        g_v = metric_value(golden, metric)
        l_v = metric_value(live, metric)
        assert g_v == l_v, f"{key}/{metric}: live != after golden"

    assert (
        live["input_contract"]["features_h5_sha256"]
        == before["input_contract"]["features_h5_sha256"]
    )
    assert live["pit_stats_version"] == PIT_STATS_VERSION
    assert golden["pit_stats_version"] == PIT_STATS_VERSION

    if not expect_split:
        # split OFF → pit_expanding（非 train_mask）
        fit_mode = (live.get("stage1") or {}).get("preproc_log", {}).get("fit_mode")
        assert fit_mode == "pit_expanding", f"{key}: fit_mode={fit_mode}"
        g_fit = (golden.get("stage1") or {}).get("preproc_log", {}).get("fit_mode")
        assert g_fit == "pit_expanding"


def test_after_golden_deep_equal() -> None:
    """B6 golden 強 gate：split-ON 凍結輸入 live re-analyze vs after golden。"""
    assert AFTER_BTC.is_file() and AFTER_ETH.is_file()
    for after_path, before_path, key in (
        (AFTER_BTC, BEFORE_BTC, "BTCUSDT_1h"),
        (AFTER_ETH, BEFORE_ETH, "ETHUSDT_12h"),
    ):
        _assert_live_vs_after_golden(
            before_path=before_path,
            after_path=after_path,
            key=key,
            config_override=None,
            expected_role="after_pit",
            expect_split=True,
        )


def test_after_golden_split_off_deep_equal() -> None:
    """⑤ flag-off / split-OFF live 強 gate（禁假綠）。

    實跑 analyze(ic_train_test_split=False) → pit_expanding after-golden
    element 級 deep-equal（pearson/spearman/mono/turnover/winsorize）。
    非只比靜態 artifact hash。
    """
    from tests.golden.la0.build_after_and_attribution import (  # noqa: WPS433
        SPLIT_OFF_OVERRIDE,
        metric_value,
    )

    assert AFTER_BTC_SPLIT_OFF.is_file() and AFTER_ETH_SPLIT_OFF.is_file()

    for after_path, before_path, key in (
        (AFTER_BTC_SPLIT_OFF, BEFORE_BTC, "BTCUSDT_1h"),
        (AFTER_ETH_SPLIT_OFF, BEFORE_ETH, "ETHUSDT_12h"),
    ):
        _assert_live_vs_after_golden(
            before_path=before_path,
            after_path=after_path,
            key=key,
            config_override=SPLIT_OFF_OVERRIDE,
            expected_role="after_pit_split_off",
            expect_split=False,
        )

    # 回退 legacy 假綠防護：split-OFF golden 不得等於 split-ON after
    # （PIT 路徑不同；若誤共用 split-ON artifact 會被抓）
    for path_on, path_off, key in (
        (AFTER_BTC, AFTER_BTC_SPLIT_OFF, "BTCUSDT_1h"),
        (AFTER_ETH, AFTER_ETH_SPLIT_OFF, "ETHUSDT_12h"),
    ):
        on = json.loads(path_on.read_text(encoding="utf-8"))
        off = json.loads(path_off.read_text(encoding="utf-8"))
        # stage1：split ON=train_mask vs OFF=pit_expanding → winsorize hash 應異
        on_s1 = metric_value(on, "stage1_winsorize_full_sample_fallback")
        off_s1 = metric_value(off, "stage1_winsorize_full_sample_fallback")
        assert on_s1 != off_s1, (
            f"{key}: split-OFF stage1 identical to split-ON "
            f"(flag-off gate would be fake-green if shared)"
        )
        # spearman 在 full series vs test-only 範圍不同 → digest 必異
        on_ric = metric_value(on, "rolling_ic_spearman")
        off_ric = metric_value(off, "rolling_ic_spearman")
        assert on_ric != off_ric, f"{key}: split-OFF rolling IC == split-ON (suspect)"
