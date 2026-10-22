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
    if len(got) != len(want):
        out.append(f"mask：長度 {len(got)} ≠ {len(want)}")
    for i, (g, w) in enumerate(zip(got, want)):
        if not _same(float(g), NAN if w is None else float(w)):
            out.append(f"mask[{i}]：{g!r} ≠ {w!r}")
    return out


# ---------------------------------------------------------------------------------------------- (b) 第三方交叉核對

def _len_violation(label: str, arr: Any, n: int) -> List[str]:
    """參考實作輸出列數須＝輸入列數（逐值比對不得靜默截斷或忽略多出之列；審碼 r18／r19）。"""
    got = len(arr)
    return [] if got == n else [f"{label}：輸出 {got} 列 ≠ 輸入 {n} 列"]


def _rel_ok(a: float, b: float) -> bool:
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    if abs(b) < SPEC_NEAR_ZERO_CUTOFF:
        return abs(a - b) <= SPEC_NEAR_ZERO_ABS
    return abs(a - b) / max(abs(b), SPEC_NEAR_ZERO_CUTOFF) <= SPEC_RELATIVE_THRESHOLD


def proof_b_violations(module: Any) -> List[str]:
    """(b) 真實 kline 小段：rank 對 pandas `rolling.rank(method="average", pct=True)`（非常數窗）、gaussian 對
    `scipy.special.ndtri(clip(rank))`、zscore 對逐窗 `numpy.mean`／`numpy.std(ddof=1)`；容差＝(d) 之自足門檻。不含 assert。"""
    return _proof_b_on(module, _real_slice())


def _proof_b_on(module: Any, columns: Dict[str, np.ndarray]) -> List[str]:
    """(b) 之核對本體（對給定之真實欄）；`x[t]` 為 NaN 之列期望 NaN（三步皆然）。不含 assert。"""
    from scipy.special import ndtri

    out: List[str] = []
    window = 20
    for column, x in columns.items():
        mp = module.min_periods_for(window)
        rank = np.asarray(module.rolling_rank(x, window, mp), dtype=np.float64)
        gauss = np.asarray(module.gaussian(x, window, mp), dtype=np.float64)
        z = np.asarray(module.rolling_zscore(x, window, 1e-8), dtype=np.float64)
        lengths = (_len_violation(f"rank {column}", rank, len(x)) + _len_violation(f"gaussian {column}", gauss, len(x))
                   + _len_violation(f"zscore {column}", z, len(x)))
        if lengths:
            out += lengths
            continue
        series = pd.Series(x)
        rolling = series.rolling(window, min_periods=mp)
        want_rank = rolling.rank(method="average", pct=True).to_numpy()
        constant = (rolling.max() == rolling.min()).to_numpy()
        for t in range(len(x)):
            if not constant[t] and not _rel_ok(rank[t], want_rank[t]):
                out.append(f"rank {column}[{t}]：{rank[t]!r} ≠ pandas {want_rank[t]!r}")
        lo, hi = module.GAUSSIAN_CLIP
        want_gauss = ndtri(np.clip(rank, lo, hi))
        for t in range(len(x)):
            if not _rel_ok(gauss[t], want_gauss[t]):
                out.append(f"gaussian {column}[{t}]：{gauss[t]!r} ≠ ndtri {want_gauss[t]!r}")
        eps = 1e-8
        for t in range(len(x)):
            win = x[max(0, t - window + 1): t + 1]
            win = win[~np.isnan(win)]
            if math.isnan(x[t]):
                want = NAN
            elif len(win) < 2 or np.std(win, ddof=1) == 0:
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
    out += _len_violation("rank base", base, len(x))
    for label, y in (("affine", 2.5 * x + 7.0), ("exp", np.exp((x - x.mean()) / x.std()))):
        moved = np.asarray(module.rolling_rank(y, window, mp), dtype=np.float64)
        out += _len_violation(f"rank {label}", moved, len(y))
        if not all(_same(float(a), float(b)) for a, b in zip(base, moved)):
            out.append(f"rank 對 {label} 變換不不變")
    w = x[-window:]
    zs = np.array([((v - w.mean()) / w.std(ddof=1)) for v in w])
    z_win = np.asarray(module.rolling_zscore(w, window, 0.0), dtype=np.float64)
    out += _len_violation("zscore 單窗", z_win, len(w))
    z_last = z_win[-1]
    if not _rel_ok(z_last, zs[-1]):
        out.append(f"zscore 末值 {z_last!r} ≠ 定義 {zs[-1]!r}")
    if not (abs(zs.mean()) <= 1e-9 and _rel_ok(zs.std(ddof=1), 1.0)):
        out.append("單窗 zscore 之平均／ddof=1 標準差非 0／1")
    const = np.full(window, 4.0)
    const_rank = np.asarray(module.rolling_rank(const, window, mp))
    const_z = np.asarray(module.rolling_zscore(const, window, 0.0))
    out += _len_violation("常數窗 rank", const_rank, window) + _len_violation("常數窗 zscore", const_z, window)
    if float(const_rank[-1]) != 0.5:
        out.append("常數窗 rank ≠ 0.5")
    if float(const_z[-1]) != 0.0:
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
    out += _len_violation("high_precision_zscore", hp, len(x))
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
    assert len(out) == 5
    assert math.isnan(out[3]) and math.isnan(out[1]) and math.isnan(out[0])
    assert float(out[4]) == float(Fraction(1))  # 窗 [2, NaN, 3]：c=2、L=1、E（含自身）=1 ⇒ (1 + (1+1)/2)/2
    out_strict = np.asarray(ref().rolling_rank(np.array([1.0, NAN, 2.0, NAN, 3.0]), 3, 3), dtype=np.float64)
    assert len(out_strict) == 5
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


# ---------------------------------------------------------------------------------------------- 審碼 r15 補強（CODEX-R15-P1-01–04）

ICPOSTLEAK_CONTRACT_PATH = nh.REPO / "tests" / "_golden" / "icpostleak" / "contract.json"
#: (b) 之 L1 欄：ICPOSTLEAK §G 輸入集之真實 L1 特徵（TA-Lib＝生產 L1 同一程式庫，於真實 kline 計算；首段 NaN 為自然暖身）
PROOF_B_L1_FEATURE = "close_momentum_RSI_14"


def _real_l1_slice(rows: int = 240) -> Dict[str, np.ndarray]:
    """真實 kline `BTCUSDT/1h` 末 `rows` 根上依 ICPOSTLEAK 契約 `kline.l1_features` 之 `PROOF_B_L1_FEATURE` 以 TA-Lib 計算之 L1 欄。"""
    import json

    import h5py
    import talib

    spec = next(s for s in json.loads(ICPOSTLEAK_CONTRACT_PATH.read_text(encoding="utf-8"))["kline"]["l1_features"]
                if s["name"] == PROOF_B_L1_FEATURE)
    with h5py.File(nh.KLINE_PATH, "r") as handle:
        data = handle["BTCUSDT"]["1h"]["data"][-rows:]
    args = [np.asarray(data[c], dtype=np.float64) for c in spec["inputs"]]
    return {PROOF_B_L1_FEATURE: np.asarray(getattr(talib, spec["fn"])(*args, **spec["args"]), dtype=np.float64)}


def proof_b_l1_violations(module: Any) -> List[str]:
    """(b) 之 L1 欄路徑（SPEC Task 0.6 (b)「close 與一個 L1 欄」）：同 `proof_b_violations` 之核對施於真實 L1 欄（含暖身 NaN）。
    不含 assert。"""
    columns = _real_l1_slice()
    col = columns[PROOF_B_L1_FEATURE]
    out = [] if np.isnan(col).any() else ["L1 欄無暖身 NaN（NaN 路徑未覆蓋）"]
    finite = np.flatnonzero(np.isfinite(col))
    # 有限值見證（審碼 r16 CODEX-R16-P1-02）：NaN 只准出現在暖身段（首個有限值之前），暖身後須全有限且至少兩個 (b) 窗長
    warm_ok = finite.size > 0 and bool(np.isfinite(col[int(finite[0]):]).all())
    if finite.size < 2 * 20 or not warm_ok:
        out.append(f"L1 欄有限值不足或暖身後仍有 NaN（有限 {finite.size} 列）")
    return out + _proof_b_on(module, columns)


def proof_d_near_zero_violations(module: Any) -> List[str]:
    """(d) 之近零格：一般小段與邊界④混合小段之報告，近零格數 > 0 時 `near_zero_max_abs_error` 須存在且 ≤ 1e-24；混合小段之最大
    相對誤差 ≤ 1e-12。不含 assert。"""
    out: List[str] = []
    close40 = _real_slice(40)["close"]
    for label, x in (("regular", _real_slice(120)["close"]),
                     ("mixed", np.concatenate([close40[:20], close40[20:] * 1e-9]))):
        report = module.proof_d_report(x, 20, 1e-8)
        # 近零見證由本測試獨立求得（審碼 r16 CODEX-R16-P1-01）：不以報告自報之格數決定是否檢查
        hp = module.high_precision_zscore([Fraction(float(v)) for v in x], 20, Fraction(1e-8), precision=SPEC_PRECISIONS[-1])
        z = np.asarray(module.rolling_zscore(x, 20, 1e-8), dtype=np.float64)
        if not len(hp) == len(z) == len(x):
            out.append(f"{label}：任意精度 {len(hp)} 列、float64 {len(z)} 列 ≠ 輸入 {len(x)} 列")
            continue
        witnesses = [t for t, v in enumerate(hp) if v is not None and abs(Decimal(v)) < Decimal(SPEC_NEAR_ZERO_CUTOFF)]
        if not witnesses:
            out.append(f"{label}：無近零見證（近零門檻未受檢）")
        for t in witnesses:
            if not abs(Decimal(float(z[t])) - Decimal(hp[t])) <= Decimal(SPEC_NEAR_ZERO_ABS):
                out.append(f"{label}[{t}]：近零絕對誤差 > {SPEC_NEAR_ZERO_ABS}")
        if report.get("near_zero_count") != len(witnesses):
            out.append(f"{label}：報告近零格數 {report.get('near_zero_count')!r} ≠ 獨立見證數 {len(witnesses)}")
        near = report.get("near_zero_max_abs_error")
        if witnesses and (near is None or not near <= SPEC_NEAR_ZERO_ABS):
            out.append(f"{label}：近零最大絕對誤差 {near!r} > {SPEC_NEAR_ZERO_ABS}")
        if not report.get("max_relative_error", math.inf) <= SPEC_RELATIVE_THRESHOLD:
            out.append(f"{label}：最大相對誤差 {report.get('max_relative_error')!r} > {SPEC_RELATIVE_THRESHOLD}")
    return out


def _chain_input() -> np.ndarray:
    x = _real_slice(60)["close"].copy()
    x[:3] = NAN  # 晚生：錨點非 0
    return x


#: 鏈之組態（rank 窗、gaussian 窗、zscore 窗清單）；None＝該步關
CHAIN_CONFIGS: List[Tuple[Optional[int], Optional[int], Optional[List[int]]]] = [
    (5, 7, [6, 9]), (5, None, [6]), (None, 7, [6]), (5, 7, None), (5, None, None), (None, None, [9, 6]),
]


def _composed(module: Any, x: np.ndarray, rw: Optional[int], gw: Optional[int], zw: Optional[List[int]]) -> np.ndarray:
    """書面定義之鏈：rank → gaussian → zscore，每步輸出以該步之步驟輸入為錨點遮罩（逐步組合，與 `post_ic_chain` 分開實作）。"""
    cur = x
    if rw is not None:
        cur = module.mask_incomplete_window(module.rolling_rank(cur, rw, module.min_periods_for(rw)), cur, rw)
    if gw is not None:
        cur = module.mask_incomplete_window(module.gaussian(cur, gw, module.min_periods_for(gw)), cur, gw)
    if zw is not None:
        cur = module.mask_incomplete_window(module.rolling_zscore(cur, zw[0], 1e-8), cur, zw[0])
    return np.asarray(cur, dtype=np.float64)


def chain_violations(module: Any, chain: Optional[Callable[..., Any]] = None) -> List[str]:
    """`post_ic_chain`（或注入之 `chain`）對逐步組合之逐位元一致（含 NaN 位置）；涵蓋 gaussian 分支、順序與每步錨點。不含 assert。"""
    chain = chain or module.post_ic_chain
    x = _chain_input()
    out: List[str] = []
    for rw, gw, zw in CHAIN_CONFIGS:
        got = np.asarray(chain(x, rank_window=rw, gaussian_window=gw, zscore_windows=zw), dtype=np.float64)
        want = _composed(module, x, rw, gw, zw)
        if not len(got) == len(want) == len(x):
            out.append(f"chain(rank={rw}, gaussian={gw}, zscore={zw})：輸出 {len(got)} 列 ≠ 輸入 {len(x)} 列")
            continue
        bad = [t for t in range(len(x)) if not _same(float(got[t]), float(want[t]))]
        if bad:
            out.append(f"chain(rank={rw}, gaussian={gw}, zscore={zw})：{len(bad)} 列不符（首 {bad[:3]}）")
        if np.isnan(want).all():
            out.append(f"chain(rank={rw}, gaussian={gw}, zscore={zw})：期望全 NaN（組態未覆蓋數值路徑）")
    return out


def test_proof_b_real_l1_column() -> None:
    """(b) 之 L1 欄：真實 L1 特徵（ICPOSTLEAK 契約之 RSI_14，TA-Lib 於真實 kline；含暖身 NaN）之第三方交叉核對。"""
    assert proof_b_l1_violations(ref()) == []


def test_proof_d_near_zero_absolute_threshold() -> None:
    """(d) 近零格之絕對誤差門檻（≤ 1e-24）與邊界④混合小段之相對門檻實際受檢。"""
    assert proof_d_near_zero_violations(ref()) == []


def test_post_ic_chain_matches_stepwise_composition() -> None:
    """鏈：rank → gaussian → zscore 與每步錨點（六組態，含 gaussian 分支與晚生欄）對逐步組合逐位元一致。"""
    assert chain_violations(ref()) == []


def test_reference_rejects_infinite_input() -> None:
    """輸入域封閉：±inf ⇒ `NonFiniteInputError`（ValueError 子類）於 rank／gaussian／zscore／鏈／(d) 報告一致拒收。"""
    module = ref()
    assert issubclass(module.NonFiniteInputError, ValueError)
    for bad in ([1.0, math.inf, 3.0], [1.0, -math.inf, 3.0]):
        x = np.asarray(bad, dtype=np.float64)
        for call in (lambda: module.rolling_rank(x, 3, 2), lambda: module.gaussian(x, 3, 2),
                     lambda: module.rolling_zscore(x, 3, 0.0),
                     lambda: module.post_ic_chain(x, rank_window=3, gaussian_window=None, zscore_windows=[3]),
                     lambda: module.proof_d_report(x, 3, 1e-8)):
            with pytest.raises(module.NonFiniteInputError):
                call()


def test_mutation_near_zero_abs_error_breaks_proof(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（CODEX-R15-P1-01）：(d) 報告之近零絕對誤差改為 1e-3 ⇒ 近零門檻檢查紅。"""
    module = ref()
    assert proof_d_near_zero_violations(module) == []
    real = module.proof_d_report

    def bad(*a: Any, **k: Any) -> Dict[str, Any]:
        return {**real(*a, **k), "near_zero_count": 1, "near_zero_max_abs_error": 1e-3}

    monkeypatch.setattr(module, "proof_d_report", bad)
    assert proof_d_near_zero_violations(module) != []


@pytest.mark.parametrize("mutant", ["order_gaussian_before_rank", "anchor_chain_start", "zscore_last_window"])
def test_mutation_chain_order_or_anchor_breaks_proof(mutant: str) -> None:
    """mutation（CODEX-R15-P1-02）：鏈順序對調（gaussian 先於 rank）／每步錨點改用鏈起點／zscore 主窗改取最後一個 ⇒ 鏈檢查紅。"""
    module = ref()
    assert chain_violations(module) == []

    def wrong(x: Any, *, rank_window: Optional[int], gaussian_window: Optional[int],
              zscore_windows: Optional[Sequence[int]], epsilon: float = 1e-8) -> np.ndarray:
        start = np.asarray(x, dtype=np.float64)
        cur = start
        steps = [("rank", rank_window), ("gaussian", gaussian_window)]
        if mutant == "order_gaussian_before_rank":
            steps.reverse()
        for name, w in steps:
            if w is None:
                continue
            fn = module.rolling_rank if name == "rank" else module.gaussian
            anchor = start if mutant == "anchor_chain_start" else cur
            cur = module.mask_incomplete_window(fn(cur, w, module.min_periods_for(w)), anchor, w)
        if zscore_windows is not None:
            w = zscore_windows[-1] if mutant == "zscore_last_window" else zscore_windows[0]
            anchor = start if mutant == "anchor_chain_start" else cur
            cur = module.mask_incomplete_window(module.rolling_zscore(cur, w, epsilon), anchor, w)
        return cur

    assert chain_violations(module, wrong) != []


def test_mutation_near_zero_count_self_reported_zero_still_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（CODEX-R16-P1-01）：(d) 報告自稱近零格數 0、省略近零誤差 ⇒ 獨立見證比對紅（不以自報格數跳過檢查）。"""
    module = ref()
    assert proof_d_near_zero_violations(module) == []
    real = module.proof_d_report
    monkeypatch.setattr(module, "proof_d_report",
                        lambda *a, **k: {**real(*a, **k), "near_zero_count": 0, "near_zero_max_abs_error": None})
    assert any("獨立見證數" in v for v in proof_d_near_zero_violations(module))


@pytest.mark.parametrize("mutant", ["all_nan", "too_few_finite", "nan_after_warmup"])
def test_mutation_l1_column_without_finite_witness_red(mutant: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（CODEX-R16-P1-02）：L1 欄全 NaN／有限值少於兩個窗長／暖身後夾 NaN ⇒ L1 交叉核對紅。"""
    module = ref()
    assert proof_b_l1_violations(module) == []
    real = _real_l1_slice()[PROOF_B_L1_FEATURE]
    col = real.copy()
    if mutant == "all_nan":
        col[:] = NAN
    elif mutant == "too_few_finite":
        col[: len(col) - 30] = NAN
    else:
        col[len(col) // 2] = NAN
    monkeypatch.setattr(THIS, "_real_l1_slice", lambda rows=240: {PROOF_B_L1_FEATURE: col})
    assert any("有限值不足或暖身後仍有 NaN" in v for v in proof_b_l1_violations(module))


# ---------------------------------------------------------------------------------------------- 審碼 r17 補強（CODEX-R17-P1-01／P1-02）

#: (d) 獨立 oracle 之一致位數下限（測試端全程 Decimal 130 位重算 vs 參考 100 位）
INDEPENDENT_MIN_DIGITS = 90


def _decimal_zscore(x: Sequence[float], window: int, epsilon: Decimal, prec: int) -> List[Optional[Decimal]]:
    """測試端獨立重算 zscore：全程 `decimal`（平均、變異、平方根、除法；不經 `Fraction`、不呼叫參考實作），輸入以
    `Decimal(float)` 精確轉入。"""
    from decimal import localcontext

    out: List[Optional[Decimal]] = []
    with localcontext() as ctx:
        ctx.prec = prec
        vals = [None if math.isnan(float(v)) else Decimal(float(v)) for v in x]
        for t, v in enumerate(vals):
            if v is None:
                out.append(None)
                continue
            win = [u for u in vals[max(0, t - window + 1): t + 1] if u is not None]
            if len(win) < 2:
                out.append(Decimal(0))
                continue
            mean = sum(win, Decimal(0)) / len(win)
            var = sum(((u - mean) ** 2 for u in win), Decimal(0)) / (len(win) - 1)
            out.append(Decimal(0) if var == 0 else (v - mean) / (var.sqrt() + epsilon))
    return out


def _digits(a: Decimal, b: Decimal) -> int:
    """測試端獨立之一致有效位數（相等 ⇒ 999）。"""
    from decimal import localcontext

    if a == b:
        return 999
    with localcontext() as ctx:
        ctx.prec = 150
        return int(-(abs(a - b) / max(abs(a), abs(b))).log10())


def proof_d_independent_violations(module: Any) -> List[str]:
    """(d) 之獨立 oracle（審碼 r17 CODEX-R17-P1-01：50／100 位收斂與 (d) 報告皆出自同一 `high_precision_zscore`，不足以證其
    為任意精度）：①閉式手算——窗 [1, 2, 4]、ε＝0 之末值＝5/√21，參考 100 位結果須與測試端 Decimal 110 位閉式值一致 ≥ 95 位；
    ②真實小段——參考 100 位結果逐值與測試端全程 Decimal 130 位獨立重算一致 ≥ `INDEPENDENT_MIN_DIGITS` 位。不含 assert。"""
    from decimal import localcontext

    out: List[str] = []
    closed_out = module.high_precision_zscore([Fraction(1), Fraction(2), Fraction(4)], 3, Fraction(0),
                                              precision=SPEC_PRECISIONS[-1])
    out += _len_violation("閉式 5/√21", closed_out, 3)
    got = closed_out[-1]
    with localcontext() as ctx:
        ctx.prec = 110
        closed = Decimal(5) / Decimal(21).sqrt()
    if not isinstance(got, Decimal) or _digits(got, closed) < 95:
        out.append(f"閉式 5/√21：參考 {got!r} 與閉式值一致位數不足 95")
    x = _real_slice(120)["close"]
    hp = module.high_precision_zscore([Fraction(float(v)) for v in x], 20, Fraction(1e-8), precision=SPEC_PRECISIONS[-1])
    ind = _decimal_zscore(x, 20, Decimal(1e-8), 130)
    if not len(hp) == len(ind) == len(x):  # 逐值覆蓋：長度不符即紅（審碼 r18 CODEX-R18-P1-01；zip 會靜默截斷）
        out.append(f"真實小段：參考輸出 {len(hp)} 列、獨立重算 {len(ind)} 列 ≠ 輸入 {len(x)} 列")
    for t, (a, b) in enumerate(zip(hp, ind)):
        if (a is None) != (b is None):
            out.append(f"真實小段[{t}]：缺值位置不符")
        elif a is not None and (not isinstance(a, Decimal) or _digits(a, b) < INDEPENDENT_MIN_DIGITS):
            out.append(f"真實小段[{t}]：參考與獨立 Decimal 重算一致位數 < {INDEPENDENT_MIN_DIGITS}")
    return out


def test_proof_d_independent_decimal_oracle() -> None:
    """(d) 之獨立 oracle：閉式 5/√21 與真實小段之全程 Decimal 獨立重算。"""
    assert proof_d_independent_violations(ref()) == []


def test_mutation_high_precision_from_float64_breaks_independent_oracle(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（CODEX-R17-P1-01）：任意精度重算改為以 float64 結果包成 `Decimal` ⇒ 獨立 oracle 紅（原 (d) 收斂與報告不足以抓）。"""
    module = ref()
    assert proof_d_independent_violations(module) == []
    real = module.high_precision_zscore
    monkeypatch.setattr(module, "high_precision_zscore",
                        lambda *a, **k: [None if v is None else Decimal(float(v)) for v in real(*a, **k)])
    assert proof_d_independent_violations(module) != []


def test_mask_rejects_infinite_input() -> None:
    """輸入域封閉（CODEX-R17-P1-02）：窗未滿遮罩之 `output` 或 `step_input` 含 ±inf ⇒ `NonFiniteInputError`。"""
    module = ref()
    ok = np.asarray([NAN, 1.0, 2.0, 3.0])
    for bad in (np.asarray([NAN, 1.0, math.inf, 3.0]), np.asarray([NAN, -math.inf, 2.0, 3.0])):
        with pytest.raises(module.NonFiniteInputError):
            module.mask_incomplete_window(ok, bad, 2)
        with pytest.raises(module.NonFiniteInputError):
            module.mask_incomplete_window(bad, ok, 2)


@pytest.mark.parametrize("target", ["independent_oracle", "proof_d_report"])
def test_mutation_high_precision_drops_last_row_red(target: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（CODEX-R18-P1-01）：任意精度重算少回最後一列 ⇒ 獨立 oracle 紅（長度核對）、`proof_d_report` 拋 ValueError。"""
    module = ref()
    assert proof_d_independent_violations(module) == []
    real = module.high_precision_zscore
    monkeypatch.setattr(module, "high_precision_zscore", lambda *a, **k: real(*a, **k)[:-1])
    if target == "independent_oracle":
        assert any("列 ≠ 輸入" in v for v in proof_d_independent_violations(module))
    else:
        with pytest.raises(ValueError):
            module.proof_d_report(_real_slice(120)["close"], 20, 1e-8)


@pytest.mark.parametrize("site", ["mask", "chain_extra_row", "near_zero_short"])
def test_mutation_output_length_mismatch_red_at_every_site(site: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """逐值比對處長度核對（審碼 r18 延伸自查：遮罩手算、鏈、近零見證）：輸出少一列或多一列 ⇒ 對應檢查紅（不靜默截斷）。"""
    module = ref()
    if site == "mask":
        assert proof_a_violations(module) == []
        real = module.mask_incomplete_window
        monkeypatch.setattr(module, "mask_incomplete_window", lambda *a, **k: real(*a, **k)[:-1])
        assert any("mask：長度" in v for v in proof_a_violations(module))
    elif site == "chain_extra_row":
        assert chain_violations(module) == []
        real_chain = module.post_ic_chain
        extra = lambda *a, **k: np.append(np.asarray(real_chain(*a, **k), dtype=np.float64), 0.0)  # noqa: E731
        assert any("輸出" in v and "≠ 輸入" in v for v in chain_violations(module, extra))
    else:
        assert proof_d_near_zero_violations(module) == []
        real_hp = module.high_precision_zscore
        monkeypatch.setattr(module, "high_precision_zscore", lambda *a, **k: real_hp(*a, **k)[:-1])
        monkeypatch.setattr(module, "proof_d_report", lambda *a, **k: {"near_zero_count": 1, "near_zero_max_abs_error": 0.0,
                                                                        "max_relative_error": 0.0})
        assert any("≠ 輸入" in v for v in proof_d_near_zero_violations(module))


@pytest.mark.parametrize("fn, mode, check", [
    ("rolling_rank", "short", "b"), ("rolling_rank", "long", "b"), ("gaussian", "long", "b"),
    ("rolling_zscore", "long", "b"), ("rolling_rank", "short", "c"), ("rolling_zscore", "short", "c"),
])
def test_mutation_step_output_length_red_in_proofs_b_c(fn: str, mode: str, check: str,
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（CODEX-R19-P1-01／P1-02）：rank／gaussian／zscore 輸出少一列或多一列 ⇒ (b)／(c) 之長度核對紅（不靜默截斷、不忽略多列）。"""
    module = ref()
    proof = proof_b_violations if check == "b" else proof_c_violations
    assert proof(module) == []
    real = getattr(module, fn)

    def wrong(*a: Any, **k: Any) -> np.ndarray:
        arr = np.asarray(real(*a, **k), dtype=np.float64)
        return arr[:-1] if mode == "short" else np.append(arr, 0.0)

    monkeypatch.setattr(module, fn, wrong)
    assert any("≠ 輸入" in v for v in proof(module))


def test_boundary_outputs_keep_full_length() -> None:
    """邊界②③之輸出列數＝輸入列數（全 NaN 欄之 rank／gaussian／zscore、窗長大於列數之鏈；全 NaN 不得以截短冒充）。"""
    module = ref()
    x = np.full(10, NAN)
    for out in (module.rolling_rank(x, 3, 3), module.gaussian(x, 3, 3), module.rolling_zscore(x, 3)):
        assert len(out) == 10
    short = _real_slice(10)["close"]
    assert len(module.post_ic_chain(short, rank_window=20, gaussian_window=None, zscore_windows=[20])) == 10
