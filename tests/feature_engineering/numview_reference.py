"""NUMVIEW Task 0.6 — post-IC 步驟之獨立參考實作（標準答案；docs/NUMVIEW_SPEC.md Task 0.6）。

依 SPEC Task 0.6 之封閉書面定義逐條實作；逐元素迴圈、float64；**不得 import 任何 `momentum.` 模組**（AST 檢查，
`tests/feature_engineering/test_numview_reference.py`）。允許之 import 限 `math`、`fractions`、`decimal`、`numpy`（只作陣列輸入
輸出）、`scipy.special`（`ndtri`／`ndtr`，第三方反常態累積分布）。

約定以模組常數具名（四類證明與 mutation 以之為對象；實作必須讀這些常數，不得另寫字面）：
- rank：average 平手規則之百分位名次 `(L + (E + 1)/2) / c`，`L`＝窗內有效值嚴格小於 `x[t]` 者之數、`E`＝等於 `x[t]` 者之數
  （**含自身**；三臂與 scipy／pandas `pct=True` 之 average 皆如此，見 `_numba_transforms.py:69-79` 之 `equal` 含自身）、`c`＝
  窗內有效值數；`x[t]` 為 NaN ⇒ NaN；`c < min_periods` ⇒ NaN；窗內有效值逐一相等 ⇒ `CONSTANT_WINDOW_RANK`。
- gaussian：`ndtri(clip(rank, lo, hi))`。
- zscore：主窗內有效值之平均 `m` 與樣本標準差 `s`（ddof＝`ZSCORE_DDOF`）；有效值數 < 2 或 `s`＝0 ⇒ `CONSTANT_WINDOW_ZSCORE`；
  否則 `(x[t] − m) / (s + ε)`（`EPSILON_IN_DENOMINATOR`）；`x[t]` 為 NaN ⇒ NaN。
- 窗未滿遮罩：錨點＝步驟輸入，欄首個有限值列 `f`，`[0, f + w − 1)` 設 NaN（`MASK_OFFSET`＝0）。
- 輸入域：有限 float64 或 NaN（缺值）；±inf ⇒ `NonFiniteInputError`（具名拒收；各步一致，不各自解讀 inf）。
- 任意精度重算：`fractions.Fraction`（rank、平均、變異）與 `decimal`（平方根、除法），精度 `PROOF_PRECISIONS`。

數值作法：rank 以整數計數組成有理數後轉 float64（恰為最近之 float64）；zscore 之平均、離差、變異以 `Fraction` 精確計算後各轉
float64，平方根與除法以 float64——價格級距（BTC 約 1e5）時 `x[t] − m` 之相消不再放大平均之捨入誤差（2026-10-22 實測：BTCUSDT 1h
末 240 根、窗 20，逐窗 float64 numpy 對 100 位重算之最大相對誤差 8.1e-13，本作法 2.5e-16）。輸出一律 float64。
"""

from __future__ import annotations

import math
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.special import ndtri

#: 允許之 import 根（AST 檢查之白名單；SPEC Task 0.6「參考實作」）
ALLOWED_IMPORT_ROOTS: Tuple[str, ...] = ("__future__", "math", "fractions", "decimal", "numpy", "scipy.special", "typing")

#: 定義常數（SPEC Task 0.6 書面定義；mutation 以 monkeypatch 改之）
RANK_TIE_RULE = "average"
CONSTANT_WINDOW_RANK = 0.5
CONSTANT_WINDOW_ZSCORE = 0.0
ZSCORE_DDOF = 1
EPSILON_IN_DENOMINATOR = True
DEFAULT_EPSILON = 1e-8
GAUSSIAN_CLIP: Tuple[float, float] = (0.001, 0.999)
MASK_OFFSET = 0

#: 正確性證明 (d) 之自足門檻（SPEC v17 Task 0.6；本 Task 自身之門檻，不引後續 Task 之容差）
PROOF_RELATIVE_THRESHOLD = 1e-12
PROOF_NEAR_ZERO_CUTOFF = 1e-12
PROOF_NEAR_ZERO_ABS = 1e-24
PROOF_PRECISIONS: Tuple[int, ...] = (50, 100)
PROOF_MIN_AGREEING_DIGITS = 40


class NonFiniteInputError(ValueError):
    """輸入含 ±inf（參考定義之輸入域＝有限值或 NaN）。"""


def _as_input(x: Sequence[float]) -> np.ndarray:
    """輸入轉 float64；含 ±inf ⇒ `NonFiniteInputError`。"""
    arr = np.asarray(x, dtype=np.float64)
    if np.isinf(arr).any():
        raise NonFiniteInputError(f"輸入含 ±inf 於列 {np.flatnonzero(np.isinf(arr))[:5].tolist()}（輸入域＝有限值或 NaN）")
    return arr


def min_periods_for(window: int) -> int:
    """rank 之 `min_periods`：SPEC 之明確公式 `min(w, max(20, w // 4))`（現行 `utils/winsor_params.py:6-10` 之同式；本檔自行
    實作、不 import 產品 helper）；`window` ≤ 0 ⇒ ValueError。"""
    if int(window) <= 0:
        raise ValueError(f"window 須為正整數，得 {window!r}")
    window = int(window)
    return min(window, max(20, window // 4))


def _window_values(arr: np.ndarray, t: int, window: int) -> List[float]:
    """因果窗 `x[t−w+1..t]` 內之有效值（非 NaN），依時間序。"""
    return [float(v) for v in arr[max(0, t - window + 1): t + 1] if not math.isnan(float(v))]


def _rank_counts(valid: Sequence[Any], value: Any) -> Tuple[int, int, int]:
    """(L, E, c)：嚴格小於 `value` 者之數、等於者之數（含自身）、有效值數。"""
    less = sum(1 for v in valid if v < value)
    equal = sum(1 for v in valid if v == value)
    return less, equal, len(valid)


def _rank_fraction(less: int, equal: int, count: int) -> Fraction:
    """平手規則（`RANK_TIE_RULE`）之百分位名次；average＝`(L + (E + 1)/2) / c`。"""
    if RANK_TIE_RULE == "average":
        return Fraction(2 * less + equal + 1, 2 * count)
    if RANK_TIE_RULE == "min":
        return Fraction(less + 1, count)
    if RANK_TIE_RULE == "max":
        return Fraction(less + equal, count)
    raise ValueError(f"未知平手規則 {RANK_TIE_RULE!r}")


def rolling_rank(x: Sequence[float], window: int, min_periods: int) -> np.ndarray:
    """因果滾動 rank（書面定義；float64；不含窗未滿遮罩）。"""
    arr = _as_input(x)
    out = np.full(arr.shape[0], np.nan, dtype=np.float64)
    for t in range(arr.shape[0]):
        value = float(arr[t])
        if math.isnan(value):
            continue
        valid = _window_values(arr, t, window)
        if len(valid) < min_periods:
            continue
        if all(v == valid[0] for v in valid):
            out[t] = CONSTANT_WINDOW_RANK
            continue
        out[t] = float(_rank_fraction(*_rank_counts(valid, value)))
    return out


def gaussian(x: Sequence[float], window: int, min_periods: int,
             clip: Tuple[float, float] = GAUSSIAN_CLIP) -> np.ndarray:
    """`ndtri(clip(rolling_rank(x, window, min_periods), lo, hi))`；`x[t]` 為 NaN ⇒ NaN。"""
    lo, hi = clip
    return np.asarray(ndtri(np.clip(rolling_rank(_as_input(x), window, min_periods), lo, hi)), dtype=np.float64)


def _exact_moments(valid: Sequence[Fraction]) -> Tuple[Fraction, Fraction]:
    """窗內有效值之精確平均與變異（ddof＝`ZSCORE_DDOF`）。"""
    n = len(valid)
    mean = sum(valid, Fraction(0)) / n
    return mean, sum(((v - mean) ** 2 for v in valid), Fraction(0)) / (n - ZSCORE_DDOF)


def rolling_zscore(x: Sequence[float], window: int, epsilon: float = DEFAULT_EPSILON) -> np.ndarray:
    """因果滾動 zscore（主窗；`min_periods`＝1；ddof＝`ZSCORE_DDOF`；ε 位置依 `EPSILON_IN_DENOMINATOR`）。"""
    arr = _as_input(x)
    out = np.full(arr.shape[0], np.nan, dtype=np.float64)
    for t in range(arr.shape[0]):
        value = float(arr[t])
        if math.isnan(value):
            continue
        valid = [Fraction(v) for v in _window_values(arr, t, window)]
        if len(valid) < 2:
            out[t] = CONSTANT_WINDOW_ZSCORE
            continue
        mean, var = _exact_moments(valid)
        if var == 0:
            out[t] = CONSTANT_WINDOW_ZSCORE
            continue
        dev = float(Fraction(value) - mean)
        denom = math.sqrt(float(var)) + epsilon if EPSILON_IN_DENOMINATOR else math.sqrt(float(var) + epsilon)
        out[t] = dev / denom
    return out


def mask_incomplete_window(output: Sequence[float], step_input: Sequence[float], window: int) -> np.ndarray:
    """窗未滿遮罩（錨點＝步驟輸入；`[0, f + window − 1 + MASK_OFFSET)` 設 NaN；全無有限值 ⇒ 全 NaN）。"""
    out = _as_input(output).copy()
    finite = np.flatnonzero(np.isfinite(_as_input(step_input)))
    if finite.size == 0:
        out[:] = np.nan
        return out
    out[: max(0, int(finite[0]) + int(window) - 1 + MASK_OFFSET)] = np.nan
    return out


def post_ic_chain(x: Sequence[float], *, rank_window: Optional[int], gaussian_window: Optional[int],
                  zscore_windows: Optional[Sequence[int]], epsilon: float = DEFAULT_EPSILON) -> np.ndarray:
    """ICPOSTLEAK 正式順序 rank → gaussian → zscore（None ⇒ 該步關）；每步輸出以該步之步驟輸入為錨點遮罩。rank 與 gaussian 之
    `min_periods` 依 `min_periods_for`（生產端同用該窗之 `_rolling_min_periods`）；zscore 主窗＝窗清單之第一個，空清單 ⇒
    ValueError（fail-closed）。"""
    cur = _as_input(x).copy()
    if rank_window is not None:
        step_input = cur
        cur = mask_incomplete_window(rolling_rank(step_input, rank_window, min_periods_for(rank_window)),
                                     step_input, rank_window)
    if gaussian_window is not None:
        step_input = cur
        cur = mask_incomplete_window(gaussian(step_input, gaussian_window, min_periods_for(gaussian_window)),
                                     step_input, gaussian_window)
    if zscore_windows is not None:
        windows = [int(w) for w in zscore_windows]
        if not windows:
            raise ValueError("zscore_windows 為空清單（fail-closed）")
        step_input = cur
        cur = mask_incomplete_window(rolling_zscore(step_input, windows[0], epsilon), step_input, windows[0])
    return cur


def exact_rank(x: Sequence[Optional[Fraction]], window: int, min_periods: int) -> List[Optional[Fraction]]:
    """rank 之精確有理數重算（`fractions.Fraction`；None＝缺值）。"""
    out: List[Optional[Fraction]] = []
    for t, value in enumerate(x):
        valid = [v for v in x[max(0, t - window + 1): t + 1] if v is not None]
        if value is None or len(valid) < min_periods:
            out.append(None)
        elif all(v == valid[0] for v in valid):
            out.append(None if math.isnan(CONSTANT_WINDOW_RANK) else Fraction(CONSTANT_WINDOW_RANK))
        else:
            out.append(_rank_fraction(*_rank_counts(valid, value)))
    return out


def _decimal(value: Any) -> Decimal:
    """`Fraction`／`Decimal`／float／int ⇒ `Decimal`（Fraction 之分子分母為整數、精確轉入；除法依當前 context 精度）。"""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, Fraction):
        return Decimal(value.numerator) / Decimal(value.denominator)
    return Decimal(value)


def high_precision_zscore(x: Sequence[Optional[Fraction]], window: int, epsilon: Fraction, *,
                          precision: int) -> List[Optional[Decimal]]:
    """zscore 之任意精度重算：平均與變異以 `Fraction` 精確、平方根與除法以 `decimal`（`precision` 位）；回 `Decimal`。"""
    out: List[Optional[Decimal]] = []
    with localcontext() as ctx:
        ctx.prec = int(precision)
        for t, value in enumerate(x):
            if value is None:
                out.append(None)
                continue
            valid = [v for v in x[max(0, t - window + 1): t + 1] if v is not None]
            if len(valid) < 2:
                out.append(_decimal(Fraction(CONSTANT_WINDOW_ZSCORE)))
                continue
            mean, var = _exact_moments(valid)
            if var == 0:
                out.append(_decimal(Fraction(CONSTANT_WINDOW_ZSCORE)))
                continue
            if EPSILON_IN_DENOMINATOR:
                denom = _decimal(var).sqrt() + _decimal(epsilon)
            else:
                denom = _decimal(var + epsilon).sqrt()
            out.append(_decimal(value - mean) / denom)
    return out


def agreeing_significant_digits(a: Decimal, b: Decimal) -> int:
    """兩任意精度值一致之有效數字位數（兩者相等含皆 0 ⇒ 視為全精度一致，回 `max(PROOF_PRECISIONS)`）。"""
    a, b = _decimal(a), _decimal(b)
    full = max(PROOF_PRECISIONS)
    if a == b:
        return full
    with localcontext() as ctx:
        ctx.prec = full + 20
        scale = max(abs(a), abs(b))
        rel = abs(a - b) / scale
        digits = int(-rel.log10())
    return max(0, min(full, digits))


def proof_d_report(x: Sequence[float], window: int, epsilon: float) -> Dict[str, Any]:
    """(d) 任意精度重算之報告：{max_relative_error, near_zero_count, near_zero_max_abs_error, min_agreeing_digits,
    precisions, value_types}；收據 `handoffs/run_receipts/<date>-numview-reference-proof.json` 之內容（寫檔由實作之 CLI 為之，
    本函式不寫檔）。ε 以其 float64 二進位值之精確有理數入任意精度計算（與 float64 參考實作所用者同值）。"""
    arr = _as_input(x)
    exact = [None if math.isnan(float(v)) else Fraction(float(v)) for v in arr]
    reference = rolling_zscore(arr, window, epsilon)
    precisions = [int(p) for p in PROOF_PRECISIONS]
    by_precision = {p: high_precision_zscore(exact, window, Fraction(epsilon), precision=p) for p in precisions}
    top = by_precision[max(precisions)]
    low = by_precision[min(precisions)]
    if any(len(v) != arr.shape[0] for v in by_precision.values()) or reference.shape[0] != arr.shape[0]:
        raise ValueError("任意精度或 float64 參考之輸出長度 ≠ 輸入長度（逐值覆蓋不完整）")
    value_types = sorted({type(v).__name__ for values in by_precision.values() for v in values if v is not None})
    max_rel, near_count, near_abs = 0.0, 0, None
    digits = max(PROOF_PRECISIONS)
    with localcontext() as ctx:
        ctx.prec = max(precisions) + 20
        cutoff = Decimal(PROOF_NEAR_ZERO_CUTOFF)
        for t, hp in enumerate(top):
            if hp is None or math.isnan(float(reference[t])):
                continue
            hp_dec = _decimal(hp)
            err = abs(_decimal(float(reference[t])) - hp_dec)
            if abs(hp_dec) < cutoff:
                near_count += 1
                near_abs = float(err) if near_abs is None else max(near_abs, float(err))
            else:
                max_rel = max(max_rel, float(err / abs(hp_dec)))
            if low[t] is not None:
                digits = min(digits, agreeing_significant_digits(_decimal(low[t]), hp_dec))
    return {"max_relative_error": float(max_rel), "near_zero_count": int(near_count),
            "near_zero_max_abs_error": near_abs, "min_agreeing_digits": int(digits),
            "precisions": precisions, "value_types": value_types}
