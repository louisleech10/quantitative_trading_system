"""滾動樣本偏態／超額峰度之精確 oracle（TESTSEL I1b；SPEC docs/TESTSEL_I1_REDS_SPEC.md Task 2.1／2.4）。

整數滑動冪次和：有限段內每個 float64 化為同一 2 冪分母下之整數，Python int 維護 Σx¹…Σx⁴ 之加入／移出，中心矩以
`fractions.Fraction` 由冪次和導出（精確）；skew＝scipy.stats.skew(bias=False) 定義，kurt＝scipy.stats.kurtosis(fisher=True,
bias=False) 定義。非有限值語意對齊產品（`numba_rolling._window_moments`）：窗內任一非有限值（NaN、±inf）⇒ NaN；常數窗 ⇒ NaN。
不得以 pandas rolling 作 oracle（I1 原型：pandas rolling(5).kurt() 對精確值最大差 36.5）。
原型與交叉驗證：runs/testsel_route/i1_proto/exact_sliding.py（與逐窗 Fraction 直接計算逐窗相等）。
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Tuple

import numpy as np


def _to_ints(x: np.ndarray) -> List[int]:
    ratios = [float(v).as_integer_ratio() for v in x]
    den = max(d for _, d in ratios)  # 皆為 2 的冪
    return [n * (den // d) for n, d in ratios]


def _exact_finite(x: np.ndarray, w: int) -> np.ndarray:
    """有限段之精確滑動（輸入須全有限）；回 (len, 2) [skew, kurt]，未滿窗與常數窗為 NaN。"""
    out = np.full((len(x), 2), np.nan)
    N = _to_ints(x)
    s = [0, 0, 0, 0]
    for i, v in enumerate(N):
        s[0] += v; s[1] += v * v; s[2] += v ** 3; s[3] += v ** 4
        if i >= w:
            u = N[i - w]
            s[0] -= u; s[1] -= u * u; s[2] -= u ** 3; s[3] -= u ** 4
        if i < w - 1:
            continue
        n = w
        S1, S2, S3, S4 = s
        M2 = Fraction(S2) - Fraction(S1 * S1, n)
        if M2 == 0:
            continue
        M3 = Fraction(S3) - Fraction(3 * S1 * S2, n) + Fraction(2 * S1 ** 3, n * n)
        M4 = Fraction(S4) - Fraction(4 * S1 * S3, n) + Fraction(6 * S1 * S1 * S2, n * n) - Fraction(3 * S1 ** 4, n ** 3)
        if n > 2:
            g1 = float(M3 / n) / float(M2 / n) ** 1.5
            out[i, 0] = g1 * (n * (n - 1)) ** 0.5 / (n - 2)
        if n > 3:
            k = (Fraction(n * (n + 1) * (n - 1)) * M4 / (M2 * M2) / ((n - 2) * (n - 3))
                 - Fraction(3 * (n - 1) ** 2, (n - 2) * (n - 3)))
            out[i, 1] = float(k)
    return out


def exact_rolling_skew_kurt(x: np.ndarray, w: int) -> np.ndarray:
    """精確 oracle（含非有限語意）：回 (len(x), 2) [skew, kurt] float64。"""
    x = np.asarray(x, dtype=np.float64)
    out = np.full((len(x), 2), np.nan)
    fin = np.isfinite(x)
    i = 0
    while i < len(x):
        if not fin[i]:
            i += 1
            continue
        j = i
        while j < len(x) and fin[j]:
            j += 1
        if j - i >= w:
            out[i:j] = _exact_finite(x[i:j], w)
        i = j
    return out


def judge_f32_ulp(out: np.ndarray, ref: np.ndarray) -> Tuple[int, int]:
    """SPEC Task 2.1 (i)–(iii)：兩者有限 ⇒ |float32(out) − ref| ≤ |spacing(float32(ref))|；兩者 NaN ⇒ 相符；其餘不符。
    回 (不符數, 兩者有限之窗數)。"""
    o = np.asarray(out, dtype=np.float64).astype(np.float32).astype(np.float64)
    r = np.asarray(ref, dtype=np.float64)
    both_f = np.isfinite(o) & np.isfinite(r)
    both_n = np.isnan(o) & np.isnan(r)
    ok = both_n.copy()
    tol = np.abs(np.spacing(r.astype(np.float32)).astype(np.float64))
    ok[both_f] = np.abs(o[both_f] - r[both_f]) <= tol[both_f]
    return int((~ok).sum()), int(both_f.sum())
