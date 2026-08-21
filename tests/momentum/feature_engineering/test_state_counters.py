"""Task B3.3 驗證：五算子手算 exact（寫死序列）＋NaN 語意（不填 0；無事件 ⇒ NaN，cross_count ⇒ 0）＋
warmup NaN 前綴＋因果（截斷未來不變）＋history-start invariance（截去窗外歷史不變；真實 kline）＋registry 註冊。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.operators import state_counters as sc
from momentum.FeatureEngineering.operators.operator_registry import OperatorRegistry
from tests.momentum.event_samples.helpers import load_bars

NAN = float("nan")


def _eq(got: pd.Series, expected: list) -> None:
    np.testing.assert_array_equal(got.to_numpy(dtype=float), np.array(expected, dtype=float))  # NaN==NaN 視為相等


# ---- bars_since_cross／cross_count：嚴格變號、d=0 不計、窗內無交叉 ⇒ NaN／0 ----
def test_bars_since_cross_hand_exact():
    a = pd.Series([1, 3, 1, 1, 3, 3, 1], dtype=float)
    b = pd.Series([2] * 7, dtype=float)                   # d=[-1,1,-1,-1,1,1,-1] ⇒ 交叉於 1,2,4,6
    _eq(sc.bars_since_cross(a, b, 3), [NAN, NAN, NAN, 1, 0, 1, 0])
    _eq(sc.cross_count(a, b, 3), [NAN, NAN, NAN, 2, 2, 1, 2])


def test_cross_zero_not_counted_and_nan_breaks_pair():
    a = pd.Series([1, 2, 3], dtype=float)
    b = pd.Series([2, 2, 2], dtype=float)                 # d=[-1,0,1]：經 0 不算交叉
    _eq(sc.bars_since_cross(a, b, 1), [NAN, NAN, NAN])
    _eq(sc.cross_count(a, b, 1), [NAN, 0, 0])             # 計數語意：無 ⇒ 0（非 NaN）
    a2 = pd.Series([1, 3, NAN, 1, 3], dtype=float)
    b2 = pd.Series([2] * 5, dtype=float)                  # d=[-1,1,nan,-1,1]：交叉於 1,4
    _eq(sc.bars_since_cross(a2, b2, 2), [NAN, NAN, 1, NAN, 0])
    _eq(sc.cross_count(a2, b2, 2), [NAN, NAN, 1, 0, 1])


def test_cross_window_exclusive_of_older_events():
    a = pd.Series([1, 3, 3, 3, 3, 3], dtype=float)
    b = pd.Series([2] * 6, dtype=float)                   # 唯一交叉於 1
    _eq(sc.bars_since_cross(a, b, 2), [NAN, NAN, 1, NAN, NAN, NAN])   # t=3 起窗 [2,3] 無交叉 ⇒ NaN
    _eq(sc.cross_count(a, b, 2), [NAN, NAN, 1, 0, 0, 0])


# ---- consecutive_run ----
def test_consecutive_run_hand_exact():
    x = pd.Series([1, 2, -1, -2, -3, -4, 0, NAN, 5], dtype=float)
    _eq(sc.consecutive_run(x, 3), [NAN, NAN, 1, 2, 3, 3, NAN, NAN, 1])   # 上限 3；0／NaN ⇒ NaN；warmup 2 根


# ---- bars_since_threshold ----
def test_bars_since_threshold_hand_exact():
    x = pd.Series([40, 55, 60, 45, 50, 52, 30, 49], dtype=float)          # 上穿 50 於 1（40→55）、4（45→50）
    _eq(sc.bars_since_threshold(x, 50.0, 3), [NAN, NAN, NAN, 2, 0, 1, 2, NAN])


def test_bars_since_threshold_equal_prev_not_upcross():
    x = pd.Series([50, 50, 51, 49, 50], dtype=float)                      # prev 須嚴格 < thr；4：49<50≤50 為上穿
    _eq(sc.bars_since_threshold(x, 50.0, 2), [NAN, NAN, NAN, NAN, 0])


# ---- window_max_ratio ----
def test_window_max_ratio_hand_exact():
    x = pd.Series([2, 4, 8, 4, 2, NAN, 6, -3, 3], dtype=float)
    _eq(sc.window_max_ratio(x, 3), [NAN, NAN, 1.0, 0.5, 0.25, NAN, NAN, NAN, 0.5])
    _eq(sc.window_max_ratio(pd.Series([-1, -2, -3], dtype=float), 3), [NAN, NAN, NAN])   # 分母 ≤0 ⇒ NaN
    _eq(sc.window_max_ratio(pd.Series([0, 0, 1], dtype=float), 2), [NAN, NAN, 1.0])


# ---- 共同：warmup／參數守衛／index 保留 ----
@pytest.mark.parametrize("L", [1, 2, 5])
def test_warmup_prefix_all_nan(L):
    rng = np.random.default_rng(20260821)
    x = pd.Series(rng.normal(size=40))
    y = pd.Series(rng.normal(size=40))
    assert sc.bars_since_cross(x, y, L).iloc[:L].isna().all()
    assert sc.cross_count(x, y, L).iloc[:L].isna().all()
    assert sc.bars_since_threshold(x, 0.0, L).iloc[:L].isna().all()
    assert sc.consecutive_run(x, L).iloc[:max(L - 1, 0)].isna().all()
    assert sc.window_max_ratio(x.abs(), L).iloc[:max(L - 1, 0)].isna().all()
    for name in ("bars_since_cross", "cross_count", "bars_since_threshold"):
        assert sc.state_counter_metadata(name, L)["warmup"] == L
    for name in ("consecutive_run", "window_max_ratio"):
        assert sc.state_counter_metadata(name, L)["warmup"] == L - 1


def test_guards_and_index_preserved():
    idx = pd.Index([10, 20, 30, 40])
    x = pd.Series([1.0, 2.0, 3.0, 4.0], index=idx)
    assert sc.window_max_ratio(x, 2).index.equals(idx)
    with pytest.raises(ValueError):
        sc.consecutive_run(x, 0)
    with pytest.raises(ValueError):
        sc.cross_count(x, x.reset_index(drop=True), 2)                        # index 不一致 ⇒ 拒
    with pytest.raises(ValueError):
        sc.bars_since_threshold(x, float("nan"), 2)
    with pytest.raises(KeyError):
        sc.state_counter_metadata("nope", 2)


# ---- 因果＋history-start invariance（真實 kline ETHUSDT 12h close vs MA20） ----
@pytest.fixture(scope="module")
def real():
    b = load_bars("ETHUSDT", ("12h",))["ETHUSDT"]["12h"].iloc[500:1100].reset_index(drop=True)
    close = b["close"].astype(float)
    return close, close.rolling(20).mean(), close.pct_change()


def _all_ops(close, ma, ret, L):
    return {
        "bars_since_cross": sc.bars_since_cross(close, ma, L),
        "cross_count": sc.cross_count(close, ma, L),
        "bars_since_threshold": sc.bars_since_threshold(ret, 0.02, L),
        "consecutive_run": sc.consecutive_run(ret, L),
        "window_max_ratio": sc.window_max_ratio(close, L),
    }


@pytest.mark.parametrize("L", [3, 10])
def test_causal_truncating_future_does_not_change_past(real, L):
    close, ma, ret = real
    full = _all_ops(close, ma, ret, L)
    m = 350
    cut = _all_ops(close.iloc[:m], ma.iloc[:m], ret.iloc[:m], L)
    for k in full:
        np.testing.assert_array_equal(cut[k].to_numpy(), full[k].to_numpy()[:m])


@pytest.mark.parametrize("L", [3, 10])
def test_history_start_invariance_only_window_matters(real, L):
    """截去窗外更早歷史（起點 s），t−s ≥ warmup 之值與全史 exact 相等——算子只依賴閉區間（＋變號所需前一根）。"""
    close, ma, ret = real
    full = _all_ops(close, ma, ret, L)
    s = 200
    sub = _all_ops(close.iloc[s:].reset_index(drop=True), ma.iloc[s:].reset_index(drop=True),
                   ret.iloc[s:].reset_index(drop=True), L)
    for k in full:
        w = sc.state_counter_metadata(k, L)["warmup"]
        np.testing.assert_array_equal(sub[k].to_numpy()[w:], full[k].to_numpy()[s + w:])
        assert np.isfinite(full[k].to_numpy()[s + w:]).any()                   # 非 vacuous


def test_no_future_leak_by_design(real):
    """cross_count 在 t 只受 ≤t 的資料影響：改動 t+1 之後任意值不改 t 及之前。"""
    close, ma, _ = real
    base = sc.cross_count(close, ma, 5)
    pert = close.copy()
    pert.iloc[400:] = pert.iloc[400:] * 1.5
    got = sc.cross_count(pert, ma, 5)
    np.testing.assert_array_equal(got.to_numpy()[:400], base.to_numpy()[:400])


# ---- registry ----
def test_registry_registers_five_and_keeps_existing():
    reg = OperatorRegistry.default_registry()
    for name, fn in [("bars_since_cross", sc.bars_since_cross), ("consecutive_run", sc.consecutive_run),
                     ("bars_since_threshold", sc.bars_since_threshold), ("window_max_ratio", sc.window_max_ratio),
                     ("cross_count", sc.cross_count)]:
        assert reg.get(name) is fn
    for name in ("ts_argmax", "ts_argmin", "cross", "distance", "momentum", "ratio", "binary_signal",
                 "signed_strength", "ts_corr", "ts_rank", "decay_linear", "sign", "log1p", "abs", "clip"):
        assert name in reg.list_all()
