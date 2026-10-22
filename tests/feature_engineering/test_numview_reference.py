"""NUMVIEW Task 0.6 — 參考實作之正確性證明（docs/NUMVIEW_SPEC.md Task 0.6；審查 r6 CODEX-R6-P1-03 列入 b1 驗收）。

四類證明（全部通過後參考實作方可被 Task 1.1 使用）：(a) 手算案例（`fractions.Fraction` 寫死精確期望值）；(b) 第三方交叉
核對（真實 kline `A:BTCUSDT:1h` 小段，對 pandas／numpy／scipy）；(c) 性質檢查；(d) 任意精度重算（50／100 位兩精度收斂 ≥40
位、自足門檻相對 1e-12／近零絕對 1e-24）。另：AST 檢查參考實作之 import ⊆ 允許集且無 `momentum.`；邊界 ①–④；SPEC 所列
mutation（以參考實作之具名約定常數注入）。

本檔於 Task 0.6 實作前為紅（參考實作空殼拋 NotImplementedError；不 skip、不 xfail）。資料一律真實 kline，秒級。
"""

from __future__ import annotations

import ast
import importlib
import math
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pytest

from tests.feature_engineering import numview_helpers as nh

REFERENCE_PATH = nh.REPO / "tests" / "feature_engineering" / "numview_reference.py"
THIS = sys.modules[__name__]
NAN = float("nan")
#: SPEC Task 0.6 之自足門檻與精度（測試端獨立寫死；參考實作之常數須與之相等）
SPEC_RELATIVE_THRESHOLD = 1e-12
SPEC_NEAR_ZERO_CUTOFF = 1e-12
SPEC_NEAR_ZERO_ABS = 1e-24
SPEC_PRECISIONS = (50, 100)
SPEC_MIN_AGREEING_DIGITS = 40
SPEC_ALLOWED_ROOTS = {"__future__", "math", "fractions", "decimal", "numpy", "scipy.special", "typing"}


def ref() -> Any:
    return importlib.import_module("tests.feature_engineering.numview_reference")


def _read_reference_source() -> str:
    return REFERENCE_PATH.read_text(encoding="utf-8")


def _real_slice(rows: int = 240) -> Dict[str, np.ndarray]:
    """真實 kline `BTCUSDT/1h` 之末 `rows` 根之 close 與 volume（float64；h5py 唯讀）。"""
    import h5py

    with h5py.File(nh.KLINE_PATH, "r") as handle:
        data = handle["BTCUSDT"]["1h"]["data"][-rows:]
    return {"close": np.asarray(data["close"], dtype=np.float64), "volume": np.asarray(data["volume"], dtype=np.float64)}


def _same(a: Optional[float], b: Optional[float]) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return a == b


# ---------------------------------------------------------------------------------------------- (a) 手算案例

#: (案名, 函式, 參數, 輸入, {位置: 期望（Fraction；None＝NaN）})；窗 3 時 min_periods 顯式給 3。rank 之 E 含自身（見
#: numview_reference 檔頭；average 百分位名次），zscore 只核有理數期望之位置（窗 [k, k+1, k+2] 之樣本標準差恰為 1）
HAND_CASES: List[Tuple[str, str, Dict[str, Any], List[float], Dict[int, Optional[Fraction]]]] = [
    ("rank_ties_nan_gap_constant", "rolling_rank", {"window": 3, "min_periods": 3},
     [1.0, 2.0, 2.0, NAN, 5.0, 5.0, 5.0, 3.0],
     {0: None, 1: None, 2: Fraction(5, 6), 3: None, 4: None, 5: None, 6: Fraction(1, 2), 7: Fraction(1, 3)}),
    ("rank_valid_count_equals_min_periods", "rolling_rank", {"window": 4, "min_periods": 3},
     [NAN, 1.0, 3.0, 2.0], {0: None, 1: None, 2: None, 3: Fraction(2, 3)}),
    ("zscore_ddof1_exact", "rolling_zscore", {"window": 3, "epsilon": 0.0},
     [1.0, 2.0, 3.0, 4.0, 5.0], {0: Fraction(0), 2: Fraction(1), 3: Fraction(1), 4: Fraction(1)}),
    ("zscore_epsilon_in_denominator", "rolling_zscore", {"window": 3, "epsilon": 1.0},
     [1.0, 2.0, 3.0], {2: Fraction(1, 2)}),
    ("zscore_single_valid_value", "rolling_zscore", {"window": 3, "epsilon": 0.0}, [NAN, NAN, 5.0],
     {0: None, 1: None, 2: Fraction(0)}),
    ("zscore_constant_window", "rolling_zscore", {"window": 3, "epsilon": 0.0}, [4.0, 4.0, 4.0],
     {0: Fraction(0), 1: Fraction(0), 2: Fraction(0)}),
]
#: 窗未滿遮罩手算：輸入首個有限值列 f＝1、窗 3 ⇒ [0, 3) 設 NaN
MASK_CASE = ([NAN, 1.0, 2.0, 3.0, 4.0], [7.0, 7.0, 7.0, 7.0, 7.0], 3, [None, None, None, Fraction(7), Fraction(7)])


def proof_a_violations(module: Any) -> List[str]:
    """(a) 手算案例：參考實作之 float64 輸出逐值等於 `Fraction` 期望（轉 float64 後恰等；None⇔NaN）。不含 assert。"""
    out: List[str] = []
    for name, fn, kwargs, x, want in HAND_CASES:
        got = list(np.asarray(getattr(module, fn)(np.asarray(x, dtype=np.float64), **kwargs), dtype=np.float64))
        if len(got) != len(x):
            out.append(f"{name}：長度 {len(got)} ≠ {len(x)}")
            continue
        for i, w in sorted(want.items()):
            if not _same(float(got[i]), NAN if w is None else float(w)):
                out.append(f"{name}[{i}]：{got[i]!r} ≠ {w!r}")
    step_input, output, window, want = MASK_CASE
    got = list(np.asarray(module.mask_incomplete_window(np.asarray(output), np.asarray(step_input), window), dtype=np.float64))
    for i, (g, w) in enumerate(zip(got, want)):
        if not _same(float(g), NAN if w is None else float(w)):
            out.append(f"mask[{i}]：{g!r} ≠ {w!r}")
    return out


# ---------------------------------------------------------------------------------------------- (b) 第三方交叉核對

def _rel_ok(a: float, b: float) -> bool:
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    if abs(b) < SPEC_NEAR_ZERO_CUTOFF:
        return abs(a - b) <= SPEC_NEAR_ZERO_ABS
    return abs(a - b) / max(abs(b), SPEC_NEAR_ZERO_CUTOFF) <= SPEC_RELATIVE_THRESHOLD


def proof_b_violations(module: Any) -> List[str]:
    """(b) 真實 kline 小段：rank 對 pandas `rolling.rank(method="average", pct=True)`（非常數窗）、gaussian 對
    `scipy.special.ndtri(clip(rank))`、zscore 對逐窗 `numpy.mean`／`numpy.std(ddof=1)`；容差＝(d) 之自足門檻。不含 assert。"""
    from scipy.special import ndtri

    out: List[str] = []
    window = 20
    for column, x in _real_slice().items():
        mp = module.min_periods_for(window)
        rank = np.asarray(module.rolling_rank(x, window, mp), dtype=np.float64)
        series = pd.Series(x)
        rolling = series.rolling(window, min_periods=mp)
        want_rank = rolling.rank(method="average", pct=True).to_numpy()
        constant = (rolling.max() == rolling.min()).to_numpy()
        for t in range(len(x)):
            if not constant[t] and not _rel_ok(rank[t], want_rank[t]):
                out.append(f"rank {column}[{t}]：{rank[t]!r} ≠ pandas {want_rank[t]!r}")
        lo, hi = module.GAUSSIAN_CLIP
        gauss = np.asarray(module.gaussian(x, window, mp), dtype=np.float64)
        want_gauss = ndtri(np.clip(rank, lo, hi))
        for t in range(len(x)):
            if not _rel_ok(gauss[t], want_gauss[t]):
                out.append(f"gaussian {column}[{t}]：{gauss[t]!r} ≠ ndtri {want_gauss[t]!r}")
        eps = 1e-8
        z = np.asarray(module.rolling_zscore(x, window, eps), dtype=np.float64)
        for t in range(len(x)):
            win = x[max(0, t - window + 1): t + 1]
            win = win[~np.isnan(win)]
            if len(win) < 2 or np.std(win, ddof=1) == 0:
                want = 0.0
            else:
                want = (x[t] - np.mean(win)) / (np.std(win, ddof=1) + eps)
            if not _rel_ok(z[t], want):
                out.append(f"zscore {column}[{t}]：{z[t]!r} ≠ numpy {want!r}")
    return out


# ---------------------------------------------------------------------------------------------- (c) 性質檢查

def proof_c_violations(module: Any) -> List[str]:
    """(c) rank 對嚴格遞增變換（正斜率仿射、exp）逐值不變；單一完整窗以 ε＝0 套 zscore 之窗內平均 0、ddof＝1 標準差 1；
    常數窗 rank＝0.5、zscore＝0；`ndtr(ndtri(p))` 往返；`ndtri(0.5)＝0`、`ndtri(0.975)≈1.959964`。不含 assert。"""
    from scipy.special import ndtr, ndtri

    out: List[str] = []
    x = _real_slice()["close"]
    window, mp = 20, 20
    base = np.asarray(module.rolling_rank(x, window, mp), dtype=np.float64)
    for label, y in (("affine", 2.5 * x + 7.0), ("exp", np.exp((x - x.mean()) / x.std()))):
        moved = np.asarray(module.rolling_rank(y, window, mp), dtype=np.float64)
        if not all(_same(float(a), float(b)) for a, b in zip(base, moved)):
            out.append(f"rank 對 {label} 變換不不變")
    w = x[-window:]
    zs = np.array([((v - w.mean()) / w.std(ddof=1)) for v in w])
    z_last = np.asarray(module.rolling_zscore(w, window, 0.0), dtype=np.float64)[-1]
    if not _rel_ok(z_last, zs[-1]):
        out.append(f"zscore 末值 {z_last!r} ≠ 定義 {zs[-1]!r}")
    if not (abs(zs.mean()) <= 1e-9 and _rel_ok(zs.std(ddof=1), 1.0)):
        out.append("單窗 zscore 之平均／ddof=1 標準差非 0／1")
    const = np.full(window, 4.0)
    if float(np.asarray(module.rolling_rank(const, window, mp))[-1]) != 0.5:
        out.append("常數窗 rank ≠ 0.5")
    if float(np.asarray(module.rolling_zscore(const, window, 0.0))[-1]) != 0.0:
        out.append("常數窗 zscore ≠ 0")
    p = np.linspace(0.001, 0.999, 101)
    if not np.allclose(ndtr(ndtri(p)), p, rtol=0, atol=1e-15):
        out.append("ndtr(ndtri(p)) 往返不成立")
    if ndtri(0.5) != 0.0 or abs(ndtri(0.975) - 1.959964) > 1e-6:
        out.append("ndtri 已知分位數不符")
    return out


# ---------------------------------------------------------------------------------------------- (d) 任意精度重算

def proof_d_violations(module: Any) -> List[str]:
    """(d) 真實小段之 zscore：參考實作之門檻／精度常數等於 SPEC；報告之值型別為 Decimal（非 float）；兩精度至少 40 位有效數字
    一致；float64 對 100 位結果之相對誤差 ≤ 1e-12（近零絕對 ≤ 1e-24）。不含 assert。"""
    out: List[str] = []
    constants = {"PROOF_RELATIVE_THRESHOLD": SPEC_RELATIVE_THRESHOLD, "PROOF_NEAR_ZERO_CUTOFF": SPEC_NEAR_ZERO_CUTOFF,
                 "PROOF_NEAR_ZERO_ABS": SPEC_NEAR_ZERO_ABS, "PROOF_PRECISIONS": SPEC_PRECISIONS,
                 "PROOF_MIN_AGREEING_DIGITS": SPEC_MIN_AGREEING_DIGITS}
    for name, want in constants.items():
        if getattr(module, name, None) != want:
            out.append(f"門檻常數 {name}={getattr(module, name, None)!r} ≠ SPEC {want!r}")
    x = _real_slice(120)["close"]
    report = module.proof_d_report(x, 20, 1e-8)
    if list(report.get("precisions") or []) != list(SPEC_PRECISIONS):
        out.append(f"精度收斂須以 {SPEC_PRECISIONS} 兩精度各算一次，實得 {report.get('precisions')!r}")
    if set(report.get("value_types") or []) != {"Decimal"}:
        out.append(f"任意精度值型別須為 Decimal，實得 {report.get('value_types')!r}")
    digits = report.get("min_agreeing_digits")
    if not isinstance(digits, int) or digits < SPEC_MIN_AGREEING_DIGITS:
        out.append(f"兩精度一致位數 {digits!r} < {SPEC_MIN_AGREEING_DIGITS}")
    rel = report.get("max_relative_error")
    if not isinstance(rel, float) or not rel <= SPEC_RELATIVE_THRESHOLD:
        out.append(f"float64 對 100 位之最大相對誤差 {rel!r} > {SPEC_RELATIVE_THRESHOLD}")
    near = report.get("near_zero_max_abs_error")
    if near is not None and not near <= SPEC_NEAR_ZERO_ABS:
        out.append(f"近零值最大絕對誤差 {near!r} > {SPEC_NEAR_ZERO_ABS}")
    hp = module.high_precision_zscore([Fraction(v) for v in x], 20, Fraction(1, 10 ** 8), precision=SPEC_PRECISIONS[-1])
    if any(v is not None and not isinstance(v, Decimal) for v in hp):
        out.append("high_precision_zscore 回傳非 Decimal")
    return out


# ---------------------------------------------------------------------------------------------- AST：不 import 產品碼

def import_violations(source: str) -> List[str]:
    """參考實作之 import 集合 ⊆ 允許集且不含任何 `momentum.`（AST）。不含 assert。"""
    out: List[str] = []
    for node in ast.walk(ast.parse(source)):
        names: List[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        for name in names:
            if name == "momentum" or name.startswith("momentum."):
                out.append(f"import 產品碼 {name}")
            elif not any(name == root or name.startswith(root + ".") for root in SPEC_ALLOWED_ROOTS):
                out.append(f"import {name} 不在允許集")
    return out


# ============================================================================================== 驗證

def test_reference_imports_allowed_set_and_no_momentum() -> None:
    """AST：`numview_reference.py` 之 import ⊆ SPEC 允許集（math、fractions、decimal、numpy、scipy.special；另標註用
    __future__／typing）且不含任何 `momentum.`。"""
    assert import_violations(_read_reference_source()) == []
    assert set(ref().ALLOWED_IMPORT_ROOTS) == SPEC_ALLOWED_ROOTS


def test_proof_a_fraction_hand_cases() -> None:
    """(a) 手算案例（Fraction 精確期望）：平手、NaN 間隔、常數窗、窗未滿、有效值數恰等於 min_periods、單一有效值之 zscore、
    ddof＝1、ε 位於分母。"""
    assert proof_a_violations(ref()) == []


def test_proof_b_third_party_cross_check_real_kline() -> None:
    """(b) 真實 kline 小段之第三方交叉核對（pandas rank pct／scipy ndtri／numpy mean、std ddof=1）。"""
    assert proof_b_violations(ref()) == []


def test_proof_c_properties() -> None:
    """(c) 性質：單調變換不變、單窗平均 0／標準差 1、常數窗、ndtri 往返與已知分位數。"""
    assert proof_c_violations(ref()) == []


def test_proof_d_arbitrary_precision_convergence_and_threshold() -> None:
    """(d) 任意精度重算：50／100 位兩精度至少 40 位一致、float64 對 100 位相對誤差 ≤ 1e-12（近零絕對 ≤ 1e-24）、值型別 Decimal、
    門檻常數等於 SPEC（本 Task 自身之門檻）。"""
    assert proof_d_violations(ref()) == []


def test_reference_min_periods_formula() -> None:
    """`min_periods_for`＝SPEC 之明確公式 `min(w, max(20, w // 4))`（自行實作，不 import 產品 helper）。"""
    for w in (1, 3, 20, 21, 79, 80, 81, 252, 1000):
        assert ref().min_periods_for(w) == min(w, max(20, w // 4)), w


# ---------------------------------------------------------------------------------------------- 邊界

def test_boundary_reference_nan_gap_below_min_periods_is_nan() -> None:
    """邊界①：窗內含 NaN 間隔使有效值數 < min_periods ⇒ NaN（rank）。"""
    out = np.asarray(ref().rolling_rank(np.array([1.0, NAN, 2.0, NAN, 3.0]), 3, 2), dtype=np.float64)
    assert math.isnan(out[3]) and math.isnan(out[1]) and math.isnan(out[0])
    assert float(out[4]) == float(Fraction(1))  # 窗 [2, NaN, 3]：c=2、L=1、E（含自身）=1 ⇒ (1 + (1+1)/2)/2
    out_strict = np.asarray(ref().rolling_rank(np.array([1.0, NAN, 2.0, NAN, 3.0]), 3, 3), dtype=np.float64)
    assert np.isnan(out_strict).all()  # 任一窗之有效值數 ≤ 2 < min_periods 3


def test_boundary_reference_all_nan_column() -> None:
    """邊界②：全 NaN 欄 ⇒ rank／gaussian／zscore 全 NaN。"""
    x = np.full(10, NAN)
    for out in (ref().rolling_rank(x, 3, 3), ref().gaussian(x, 3, 3), ref().rolling_zscore(x, 3)):
        assert np.isnan(np.asarray(out, dtype=np.float64)).all()


def test_boundary_reference_window_longer_than_rows_masked() -> None:
    """邊界③：窗長大於列數 ⇒ 鏈之輸出全 NaN（窗未滿遮罩）。"""
    x = _real_slice(10)["close"]
    out = np.asarray(ref().post_ic_chain(x, rank_window=20, gaussian_window=None, zscore_windows=[20]), dtype=np.float64)
    assert np.isnan(out).all()


def test_boundary_reference_near_zero_and_large_magnitude_zscore() -> None:
    """邊界④：近零值與 BTC 價格級距混合之 zscore（ε 位置與相消誤差）：對任意精度重算之相對誤差 ≤ 1e-12。"""
    close = _real_slice(40)["close"]
    x = np.concatenate([close[:20], close[20:] * 1e-9])
    report = ref().proof_d_report(x, 20, 1e-8)
    assert report["max_relative_error"] <= SPEC_RELATIVE_THRESHOLD
    assert report["near_zero_count"] >= 0


# ---------------------------------------------------------------------------------------------- mutation（SPEC Task 0.6 所列）

MUTANT_CONSTANTS: Dict[str, Tuple[str, Any, Callable[[Any], List[str]]]] = {
    "ddof_zero": ("ZSCORE_DDOF", 0, proof_a_violations),
    "tie_rule_min": ("RANK_TIE_RULE", "min", proof_a_violations),
    "tie_rule_max": ("RANK_TIE_RULE", "max", proof_a_violations),
    "epsilon_inside_sqrt": ("EPSILON_IN_DENOMINATOR", False, proof_a_violations),
    "constant_window_nan": ("CONSTANT_WINDOW_RANK", NAN, proof_a_violations),
    "mask_off_by_one": ("MASK_OFFSET", 1, proof_a_violations),
    "single_precision_only": ("PROOF_PRECISIONS", (100,), proof_d_violations),
    "threshold_loosened": ("PROOF_RELATIVE_THRESHOLD", 1e-6, proof_d_violations),
}


@pytest.mark.parametrize("mutant", sorted(MUTANT_CONSTANTS))
def test_mutation_reference_convention_breaks_proof(mutant: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：參考實作之具名約定改壞（ddof 0、平手 min／max、ε 移入根號、常數窗 NaN、遮罩錯一列、只做單一精度、門檻
    放寬）⇒ 對應之證明翻紅；未變異時同證明為綠（對照）。"""
    name, value, check = MUTANT_CONSTANTS[mutant]
    module = ref()
    assert check(module) == []
    monkeypatch.setattr(module, name, value)
    assert check(module) != []


def test_mutation_reference_imports_product_core_ast_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：參考實作改 import 產品核心 ⇒ AST 檢查紅。"""
    assert import_violations(_read_reference_source()) == []
    monkeypatch.setattr(THIS, "_read_reference_source", lambda: REFERENCE_PATH.read_text(encoding="utf-8")
                        + "\nfrom momentum.FeatureEngineering.preprocessing import feature_preprocessor\n")
    assert any("momentum" in v for v in import_violations(_read_reference_source()))


def test_mutation_reference_float64_recompute_type_check_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：(d) 改以 float64 重算（非任意精度）⇒ 精度欄型別檢查紅。"""
    module = ref()
    assert proof_d_violations(module) == []
    real = module.high_precision_zscore
    monkeypatch.setattr(module, "high_precision_zscore",
                        lambda *a, **k: [None if v is None else float(v) for v in real(*a, **k)])
    assert any("非 Decimal" in v for v in proof_d_violations(module))
