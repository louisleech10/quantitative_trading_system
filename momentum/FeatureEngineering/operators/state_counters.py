"""變化類 state-counter 算子（docs/GAP3_EVENT_TODO.md Task B3.3；SPEC K7/C8；W7 精確語意）。

五算子全部只看閉區間 `[t−lookback+1, t]`（含當前根 t），禁 `shift(-n)`（不引入未來）。

**交叉定義**（bars_since_cross／cross_count 共用）：`d_i = a_i − b_i`，交叉發生於 i ⇔
`sign(d_i) ≠ sign(d_{i−1})` 且兩者皆非 NaN、非 0（`d=0` 不計）。交叉指標 c_i 需 d_{i−1} 存在，
故窗 `[t−L+1, t]` 內 L 個交叉指標要求 index t−L ≥ 0 ⇒ **warmup＝L**（t < L ⇒ NaN），
使結果只依賴 `[t−L, t]` 之資料——截去更早歷史不改值（history-start invariance）。
上穿（bars_since_threshold）同理 warmup＝L；consecutive_run／window_max_ratio 只需窗內 L 根 ⇒ warmup＝L−1。

NaN 語意：**不填 0**。「窗內無事件」⇒ NaN（狀態語意），唯 `cross_count` 為計數語意 ⇒ 0 合法。
warmup 不足 ⇒ NaN 前綴。中繼資料見 `state_counter_metadata`。
"""

from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

_OPERATORS = ("bars_since_cross", "consecutive_run", "bars_since_threshold", "window_max_ratio", "cross_count")


def _check_lookback(lookback: int) -> int:
    if not isinstance(lookback, (int, np.integer)) or isinstance(lookback, bool) or int(lookback) < 1:
        raise ValueError(f"lookback 須為正整數，得 {lookback!r}")
    return int(lookback)


def _aligned(a: pd.Series, b: pd.Series) -> None:
    if len(a) != len(b) or not a.index.equals(b.index):
        raise ValueError("series_a／series_b 長度與 index 須一致（禁隱式對齊）")


def _cross_indicator(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """c_i ∈ {True, False}；c_0＝False（無 d_{−1}）。嚴格變號且兩端非 NaN 非 0。"""
    d = a - b
    s = np.sign(d)
    prev = np.roll(s, 1)
    prev[0] = 0.0
    valid = np.isfinite(d) & np.isfinite(np.roll(d, 1)) & (s != 0) & (prev != 0)
    valid[0] = False
    return valid & (s != prev)


def _upcross_indicator(x: np.ndarray, threshold: float) -> np.ndarray:
    """u_i ⇔ x_{i−1} < thr ≤ x_i（兩端非 NaN）；u_0＝False。"""
    prev = np.roll(x, 1)
    u = np.isfinite(x) & np.isfinite(prev) & (prev < threshold) & (threshold <= x)
    u[0] = False
    return u


def _bars_since_last_event(ind: np.ndarray, lookback: int) -> np.ndarray:
    """t − 窗 [t−L+1, t] 內最近一次 ind=True 的 index；無 ⇒ NaN；t < L ⇒ NaN（warmup）。"""
    n = len(ind)
    pos = np.where(ind, np.arange(n), -1)
    last = np.maximum.accumulate(pos) if n else pos
    t = np.arange(n)
    dist = (t - last).astype(float)
    out = np.where((last >= 0) & (dist <= lookback - 1), dist, np.nan)
    out[: min(lookback, n)] = np.nan
    return out


def _rolling_count(ind: np.ndarray, lookback: int) -> np.ndarray:
    """窗 [t−L+1, t] 內 ind=True 次數；t < L ⇒ NaN（warmup；見模組 docstring）。"""
    n = len(ind)
    cs = np.concatenate([[0], np.cumsum(ind.astype(np.int64))])
    t = np.arange(n)
    lo = np.maximum(t - lookback + 1, 0)
    out = (cs[t + 1] - cs[lo]).astype(float)
    out[: min(lookback, n)] = np.nan
    return out


def bars_since_cross(series_a: pd.Series, series_b: pd.Series, lookback: int) -> pd.Series:
    """t 減窗內最近一次交叉之 bar index；交叉在當前根 ⇒ 0；窗內無交叉 ⇒ NaN；t < lookback ⇒ NaN。"""
    L = _check_lookback(lookback)
    _aligned(series_a, series_b)
    c = _cross_indicator(series_a.to_numpy(dtype=float), series_b.to_numpy(dtype=float))
    return pd.Series(_bars_since_last_event(c, L), index=series_a.index, name="bars_since_cross")


def consecutive_run(series: pd.Series, lookback: int) -> pd.Series:
    """以 t 結尾、`sign(series)` 嚴格同號（>0 或 <0）之 run 長度（含 t），上限 lookback；
    `series_t==0` 或 NaN ⇒ NaN；t < lookback−1 ⇒ NaN（warmup，確保只依賴窗內 L 根）。"""
    L = _check_lookback(lookback)
    x = series.to_numpy(dtype=float)
    n = len(x)
    s = np.sign(x)
    s[~np.isfinite(x)] = 0.0
    run = np.zeros(n, dtype=float)
    for i in range(n):  # O(n)；單向遞推（非 hot path 內 log）
        if s[i] == 0.0:
            run[i] = 0.0
        elif i > 0 and s[i - 1] == s[i]:
            run[i] = run[i - 1] + 1.0
        else:
            run[i] = 1.0
    out = np.minimum(run, L)
    out[s == 0.0] = np.nan
    out[: min(L - 1, n)] = np.nan
    return pd.Series(out, index=series.index, name="consecutive_run")


def bars_since_threshold(series: pd.Series, threshold: float, lookback: int) -> pd.Series:
    """t 減窗內最近一次上穿（`series_{i−1} < threshold ≤ series_i`）之 bar index；窗內無上穿 ⇒ NaN；t < lookback ⇒ NaN。"""
    L = _check_lookback(lookback)
    thr = float(threshold)
    if not np.isfinite(thr):
        raise ValueError("threshold 須為有限值")
    u = _upcross_indicator(series.to_numpy(dtype=float), thr)
    return pd.Series(_bars_since_last_event(u, L), index=series.index, name="bars_since_threshold")


def window_max_ratio(series: pd.Series, lookback: int) -> pd.Series:
    """`series_t / rolling_max(series, lookback)_t`（分母含當前根；窗內任一 NaN ⇒ NaN）；分母 ≤0 或 NaN ⇒ NaN。"""
    L = _check_lookback(lookback)
    x = series.astype(float)
    mx = x.rolling(L, min_periods=L).max()
    denom = mx.where(mx > 0)
    out = x / denom
    return pd.Series(out.to_numpy(dtype=float), index=series.index, name="window_max_ratio")


def cross_count(series_a: pd.Series, series_b: pd.Series, lookback: int) -> pd.Series:
    """窗 [t−L+1, t] 內交叉次數（計數語意：無 ⇒ 0 合法）；t < lookback ⇒ NaN（warmup）。"""
    L = _check_lookback(lookback)
    _aligned(series_a, series_b)
    c = _cross_indicator(series_a.to_numpy(dtype=float), series_b.to_numpy(dtype=float))
    return pd.Series(_rolling_count(c, L), index=series_a.index, name="cross_count")


def state_counter_metadata(name: str, lookback: int) -> Dict[str, object]:
    """算子中繼資料：`max_lookback`／`warmup`（首個非 NaN 可能出現之 index）／`as_of`（閉區間含當前根）。"""
    L = _check_lookback(lookback)
    if name not in _OPERATORS:
        raise KeyError(f"unknown state counter: {name}")
    warmup = L if name in ("bars_since_cross", "bars_since_threshold", "cross_count") else L - 1
    return {
        "operator": name,
        "max_lookback": L,
        "warmup": warmup,
        "as_of": "closed_interval_including_current_bar",
        "window": f"[t-{L - 1}, t]" + ("+prev_bar_for_sign_change" if warmup == L else ""),
        "nan_on_no_event": name != "cross_count",
    }


__all__ = [
    "bars_since_cross",
    "bars_since_threshold",
    "consecutive_run",
    "cross_count",
    "state_counter_metadata",
    "window_max_ratio",
]
