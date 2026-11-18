"""L2 Cross／Ratio 之獨立 oracle（TESTSEL I1f2，SPEC `docs/TESTSEL_I1_REDS_SPEC.md` Task 3.3、§G 第二層）。

只依標準庫（含 fractions）與 numpy：不得 import `momentum`、不得呼叫產品遮罩／尺度函式
（`test_l2_oracle_module_imports_numpy_only` 驗）。定義照 SPEC 原樣：
- Cross＝a − b。
- Ratio＝a ／ b，b 於遮罩列為 NaN；遮罩＝非有限 ∪ exact 0 ∪ 因果尺度非有限 ∪ `|b| < REL_EPS·scale`。
- 因果尺度：第 t 列（含）往回 WINDOW 列內「有限且非零」之 |值| 中位數；自首個有限值起未滿 WINDOW 列為 NaN；窗內無者為 0。
- (i) `within_1ulp(out, ref)`：依 dtype 判，out 與 ref dtype 須相同（float32 或 float64），`|out−ref| ≤ |spacing(ref)|`，
  差以 float64 計；category 臂 float64 判、禁止先轉 float32（審 r1 GROK-R1-P1-01）。
- (ii)（審 r1 CODEX-R1-P1-01 改寫）：A＝fl32(a)、B＝fl32(b)、Ea＝½|sp(A)|、Eb＝½|sp(B)|、Eo＝½|sp(out32)|；
  Cross 界＝Ea＋Eb＋Eo；Ratio 界＝(Ea＋|r|·Eb)/|B|＋Eo（r＝a/b）。適用於 oracle 與臂皆有限之格；
  float64 判 err＞界·(1−2^-30) 者以 Fraction 精確重判。不得近似。
"""

from __future__ import annotations

import re
import warnings
from fractions import Fraction
from typing import Dict, Optional, Tuple

import numpy as np

#: 相對近零門檻與因果尺度窗（數值照 SPEC Task 3.3；不自產品 import）
REL_EPS: float = 1e-6
WINDOW: int = 252
#: (ii) 之 float64 預篩門檻：err > 界·(1−2^-30) 之格改以 Fraction 精確重判
_EXACT_RECHECK = 1.0 - 2.0 ** -30

_PAIR = re.compile(r"^(?P<pre>.+)_(?P<p1>[^_~]+)~(?P<p2>[^_~]+)_(?P<op>Cross|Ratio)$")


def causal_scale(d: np.ndarray) -> np.ndarray:
    """因果尺度（見模組 docstring）。"""
    d = np.asarray(d, dtype=np.float64)
    n = d.shape[0]
    out = np.full(n, np.nan)
    fin = np.isfinite(d)
    if not fin.any():
        return out
    first = int(np.argmax(fin))
    if n - first < WINDOW:
        return out
    seg = np.abs(d[first:])
    seg = np.where(np.isfinite(seg) & (seg != 0), seg, np.nan)
    win = np.lib.stride_tricks.sliding_window_view(seg, WINDOW)  # 第 j 窗＝seg[j:j+WINDOW] ⇒ t＝first+j+WINDOW−1
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # 全 NaN 窗（窗內無有限非零值）
        med = np.nanmedian(win, axis=1)
    out[first + WINDOW - 1:] = np.where(np.isnan(med), 0.0, med)
    return out


def denominator_mask(d: np.ndarray) -> np.ndarray:
    """Ratio 分母遮罩（True＝該列輸出 NaN）。"""
    d = np.asarray(d, dtype=np.float64)
    scale = causal_scale(d)
    with np.errstate(invalid="ignore"):
        return ~np.isfinite(d) | (d == 0) | ~np.isfinite(scale) | (np.abs(d) < REL_EPS * scale)


def oracle_cross(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a − b（float64 計算）。"""
    return np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)


def oracle_ratio(a: np.ndarray, b: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
    """a ／ 遮罩後 b（float64 計算）。`mask` 可傳入同一分母已算之 `denominator_mask(b)`（同分母多欄共用，省重算）。"""
    b = np.asarray(b, dtype=np.float64)
    d = np.where(denominator_mask(b) if mask is None else mask, np.nan, b)
    with np.errstate(all="ignore"):
        return np.asarray(a, dtype=np.float64) / d


def oracle(op: str, a: np.ndarray, b: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
    """依算子名（Cross／Ratio）取 oracle；`mask` 只用於 Ratio。"""
    if op == "Cross":
        return oracle_cross(a, b)
    if op == "Ratio":
        return oracle_ratio(a, b, mask)
    raise ValueError(f"未支援之算子：{op}")


def arm_inputs_float32(a: np.ndarray, b: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Polars 臂之實際輸入精度：L1 先轉 float32（產品 `derived_operators.py:138`），再升 float64 供 oracle 計算。"""
    return (np.asarray(a, dtype=np.float64).astype(np.float32).astype(np.float64),
            np.asarray(b, dtype=np.float64).astype(np.float32).astype(np.float64))


def pair_inputs(name: str, l1_cols: set) -> Tuple[str, str, str]:
    """由輸出欄名 `<前綴>_<p1>~<p2>_<Cross|Ratio>` 拆出兩輸入欄名與算子；兩輸入須皆在 L1。"""
    m = _PAIR.match(name)
    if m is None:
        raise ValueError(f"欄名無法拆解：{name}")
    a, b = f"{m['pre']}_{m['p1']}", f"{m['pre']}_{m['p2']}"
    if a not in l1_cols or b not in l1_cols:
        raise ValueError(f"{name} → {a}／{b} 不在 L1")
    return a, b, m["op"]


def within_1ulp(out: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """(i)：依 dtype 之 1 ulp 判定（dtype 不同即 raise）。兩側皆有限才比 ulp；雙 NaN 通過；雙 inf 須同號；
    有限↔非有限、NaN↔inf、異號 inf 一律 False（審碼 b1 r1 CODEX-R1-P1-01／GROK-R1-P1-01：原「任一側非有限即通過」漏判 ±inf）。"""
    out, ref = np.asarray(out), np.asarray(ref)
    if out.dtype != ref.dtype or out.dtype not in (np.float32, np.float64):
        raise TypeError(f"within_1ulp：out {out.dtype} 與 ref {ref.dtype} 須同為 float32 或 float64")
    finite_pair = np.isfinite(out) & np.isfinite(ref)
    with np.errstate(invalid="ignore"):
        err = np.abs(out.astype(np.float64) - ref.astype(np.float64))
        ok = err <= np.abs(np.spacing(ref)).astype(np.float64)
    both_nan = np.isnan(out) & np.isnan(ref)
    both_inf = np.isinf(out) & np.isinf(ref) & (out == ref)
    return (finite_pair & ok) | both_nan | both_inf


def _half_sp32(x: np.ndarray) -> np.ndarray:
    return 0.5 * np.abs(np.spacing(np.asarray(x).astype(np.float32))).astype(np.float64)


def bound_cross(a: np.ndarray, b: np.ndarray, out32: np.ndarray) -> np.ndarray:
    """(ii) Cross 界（a、b 為 float64 輸入）：Ea＋Eb＋Eo。"""
    return _half_sp32(a) + _half_sp32(b) + _half_sp32(out32)


def bound_ratio(a: np.ndarray, b: np.ndarray, out32: np.ndarray, r: np.ndarray) -> np.ndarray:
    """(ii) Ratio 界（r＝float64 真值 a/b）：(Ea＋|r|·Eb)/|B|＋Eo。"""
    B = np.abs(np.asarray(b, dtype=np.float64).astype(np.float32).astype(np.float64))
    with np.errstate(all="ignore"):
        return (_half_sp32(a) + np.abs(r) * _half_sp32(b)) / B + _half_sp32(out32)


def exact_within_bound(op: str, a: float, b: float, out32: np.float32) -> bool:
    """(ii) 之 Fraction 精確重判（候選格用）：輸入皆二進浮點值，可精確表示。"""
    A, B, O = np.float32(a), np.float32(b), np.float32(out32)
    Ea = Fraction(float(np.abs(np.spacing(A)))) / 2
    Eb = Fraction(float(np.abs(np.spacing(B)))) / 2
    Eo = Fraction(float(np.abs(np.spacing(O)))) / 2
    fa, fb, fo = Fraction(float(a)), Fraction(float(b)), Fraction(float(O))
    if op == "Cross":
        r, bound = fa - fb, Ea + Eb + Eo
    elif op == "Ratio":
        r = fa / fb
        bound = (Ea + abs(r) * Eb) / abs(Fraction(float(B))) + Eo
    else:
        raise ValueError(f"未支援之算子：{op}")
    return abs(fo - r) <= bound


def judge_bound(op: str, a: np.ndarray, b: np.ndarray, out32: np.ndarray,
                r: Optional[np.ndarray] = None) -> Dict[str, object]:
    """(ii) 判定（Polars 臂對 float64 真值）：回 finite、nan_mismatch、候選數、精確超界列（list）、max err/界。
    `r` 可傳入已算之 float64 真值 `oracle(op, a, b)`（省重算）。"""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    out32 = np.asarray(out32).astype(np.float32)
    r = oracle(op, a, b) if r is None else np.asarray(r, dtype=np.float64)
    bound = bound_cross(a, b, out32) if op == "Cross" else bound_ratio(a, b, out32, r)
    fo, fr = np.isfinite(out32), np.isfinite(r)
    fin = fo & fr
    with np.errstate(all="ignore"):
        err = np.abs(out32.astype(np.float64) - r)
        ratio = np.where(fin, err / bound, 0.0)
    cand = np.flatnonzero(fin & (err > bound * _EXACT_RECHECK))
    viol = [int(i) for i in cand if not exact_within_bound(op, float(a[i]), float(b[i]), out32[i])]
    return {"finite": int(fin.sum()), "nan_mismatch": int((fo != fr).sum()), "candidates": int(cand.size),
            "violations": viol, "max_err_over_bound": float(np.max(ratio)) if ratio.size else 0.0}
