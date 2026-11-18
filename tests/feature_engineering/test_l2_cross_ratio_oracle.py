"""TESTSEL I1f2（SPEC `docs/TESTSEL_I1_REDS_SPEC.md` Task 3.3 ②）：L2 Cross／Ratio 兩臂對獨立 oracle（快速層、純真實資料）。

格 B 真實配對觸發不到 exact 0 與相對近零兩分支（`runs/testsel_route/i1f2/probe_mask_all_l1.log` hit_cols=0）；
真實 BTCUSDT/1h 之 TA-Lib STOCHRSI（預設參數）可觸發全部四分支（`runs/testsel_route/i1f2/probe_osc_branches.log`）⇒
以其為分母，不置入或改寫任何值（審 r1 CODEX-R1-P1-03）。兩臂各依 §G 第二層 (i)：Polars 臂吃 float32(L1)、判 float32；
category 臂吃 float64、判 float64（審 r1 GROK-R1-P1-01）。
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import pytest
import talib

from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine
from momentum.FeatureEngineering.polars_adapter import (
    pandas_to_polars,
    polars_l2_derived_diff,
    polars_l2_derived_ratio,
    polars_to_pandas,
)
from momentum.FeatureEngineering.utils import numeric_guards
from tests.feature_engineering import l2_oracle as lo

pytestmark = pytest.mark.requires_kline

#: 真實 BTCUSDT/1h 相對近零之具名列（`runs/testsel_route/i1f2/probe_ts_rows.py`：fastk 5.19e-14、fastd −5.98e-14）
NEAR_ZERO_TS = {"fastk": 1717322400, "fastd": 1705071600}


def _real(requires_kline_data) -> Dict[str, np.ndarray]:
    raw = requires_kline_data("BTCUSDT", "1h", min_rows=4 * lo.WINDOW)
    close = raw["close"].to_numpy(dtype=np.float64)
    fastk, fastd = talib.STOCHRSI(close)
    return {"ts": raw["timestamp"].to_numpy(dtype=np.int64), "close": close, "fastk": fastk, "fastd": fastd,
            "ema": talib.EMA(close, 30)}


def _polars_arm(op: str, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    frame = pd.DataFrame({"a": a, "b": b})
    fn = polars_l2_derived_ratio if op == "Ratio" else polars_l2_derived_diff
    out = polars_to_pandas(fn(pandas_to_polars(frame), [("a", "b", "out")]), index=frame.index)["out"].to_numpy()
    assert out.dtype == np.float32, f"Polars 臂輸出 dtype {out.dtype}（預期 float32）"
    return out


def _category_arm(op: str, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    engine = DerivedOperatorEngine(None)
    fn = engine.compute_ratio if op == "Ratio" else engine.compute_cross
    out = fn(pd.Series(a), pd.Series(b), "x").to_numpy()
    assert out.dtype == np.float64, f"category 臂輸出 dtype {out.dtype}（預期 float64）"
    return out


def _arm_violations(op: str, a: np.ndarray, b: np.ndarray, polars_out: np.ndarray,
                    category_out: np.ndarray) -> List[str]:
    """§G 第二層 (i)：兩臂各對其實際輸入精度之 oracle 1 ulp、NaN 位置一致。不含 assert。"""
    bad: List[str] = []
    ref32 = lo.oracle(op, *lo.arm_inputs_float32(a, b)).astype(np.float32)
    ref64 = lo.oracle(op, a, b)
    for arm, out, ref in (("polars", polars_out, ref32), ("category", category_out, ref64)):
        nan_mm = np.flatnonzero(np.isnan(out) != np.isnan(ref))
        ulp_bad = np.flatnonzero(~lo.within_1ulp(out, ref))
        bad += [f"{op}|{arm}|NaN 位置不一致 列 {i}：out={out[i]!r} ref={ref[i]!r}" for i in nan_mm[:5]]
        bad += [f"{op}|{arm}|超 1 ulp 列 {i}：out={out[i]!r} ref={ref[i]!r}" for i in ulp_bad[:5]]
    return bad


def _branch_counts(d: np.ndarray) -> Dict[str, np.ndarray]:
    scale = lo.causal_scale(d)
    nf = ~np.isfinite(d)
    zero = (d == 0) & ~nf
    undefined = ~np.isfinite(scale) & ~nf & ~zero
    with np.errstate(invalid="ignore"):
        rel = (np.abs(d) < lo.REL_EPS * scale) & ~nf & ~zero & ~undefined
    return {"nonfinite": nf, "zero": zero, "scale_undefined": undefined, "rel_near_zero": rel}


def test_l2_oracle_module_imports_numpy_only() -> None:
    """oracle 模組之 import 只含標準庫與 numpy（不 import momentum、不呼叫產品遮罩／尺度函式）。"""
    tree = ast.parse(Path(lo.__file__).read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            roots.add((node.module or "").split(".")[0])
    assert roots <= {"__future__", "re", "warnings", "fractions", "typing", "numpy"}, sorted(roots)
    source = Path(lo.__file__).read_text(encoding="utf-8")
    for name in ("momentum", "causal_near_zero_mask(", "causal_denominator_scale(", "safe_denominator(",
                 "_safe_denom_expr("):
        assert name not in source.split('"""', 2)[-1], f"oracle 本體含 {name}"


def test_ratio_mask_branches_both_arms_match_oracle_on_real_stochrsi(requires_kline_data) -> None:
    """真實 STOCHRSI fastk／fastd 為分母：四分支各至少 1 格命中（具名近零列）；兩臂依 (i) 對 oracle、NaN 位置一致。"""
    r = _real(requires_kline_data)
    hits = {k: 0 for k in ("nonfinite", "zero", "scale_undefined", "rel_near_zero")}
    for name in ("fastk", "fastd"):
        for x in (r[name], lo.arm_inputs_float32(r[name], r[name])[1]):  # float64 與 Polars 臂之 float32 輸入
            for k, m in _branch_counts(x).items():
                hits[k] += int(m.sum())
        row = int(np.flatnonzero(r["ts"] == NEAR_ZERO_TS[name])[0])
        value = r[name][row]
        assert np.isfinite(value) and value != 0 and lo.denominator_mask(r[name])[row], (name, row, value)
        assert _branch_counts(r[name])["rel_near_zero"][row], f"{name} 列 {row} 不在相對近零分支"
    assert all(v > 0 for v in hits.values()), hits
    bad: List[str] = []
    for num, den in (("close", "fastk"), ("close", "fastd"), ("fastk", "close")):
        a, b = r[num], r[den]
        p, c = _polars_arm("Ratio", a, b), _category_arm("Ratio", a, b)
        for name in ("fastk", "fastd"):
            if den == name:
                row = int(np.flatnonzero(r["ts"] == NEAR_ZERO_TS[name])[0])
                assert np.isnan(p[row]) and np.isnan(c[row]), f"{num}/{den} 近零列 {row} 兩臂未遮罩"
        bad += _arm_violations("Ratio", a, b, p, c)
    assert bad == [], bad[:20]


def test_cross_both_arms_match_oracle_on_real_kline(requires_kline_data) -> None:
    """Cross 兩臂於真實欄依 (i) 對 oracle（Polars 臂 float32 輸入、category 臂 float64 輸入與 float64 判定）。"""
    r = _real(requires_kline_data)
    bad: List[str] = []
    for fast, slow in (("fastk", "fastd"), ("close", "ema")):
        a, b = r[fast], r[slow]
        bad += _arm_violations("Cross", a, b, _polars_arm("Cross", a, b), _category_arm("Cross", a, b))
    assert bad == [], bad[:20]


def test_causal_scale_product_bitwise_equals_oracle_on_real_columns(requires_kline_data) -> None:
    """產品 causal_denominator_scale 對 oracle 逐位元相等（float64／float32 輸入，含 NaN 位置與起算點）；中位數奇偶兩路徑
    皆命中（審 r1 CODEX-R1-P2-04）。「窗內全無⇒尺度 0」路徑：真實資料若出現，該列本身須為 0 或非有限（定義推論之實證）；
    不出現則為未覆蓋（`i1f2_facts.md` §6），不宣稱已驗。"""
    r = _real(requires_kline_data)
    even = odd = 0
    for name in ("fastk", "fastd", "close"):
        for x in (r[name], lo.arm_inputs_float32(r[name], r[name])[1]):
            ours, prod = lo.causal_scale(x), numeric_guards.causal_denominator_scale(x)
            assert np.array_equal(np.isnan(ours), np.isnan(prod)), f"{name}：尺度 NaN 位置不同"
            fin = np.isfinite(ours)
            assert np.array_equal(ours[fin].view(np.int64), prod[fin].view(np.int64)), f"{name}：尺度值不逐位元相等"
            good = (np.isfinite(x) & (x != 0)).astype(np.int64)
            count = np.convolve(good, np.ones(lo.WINDOW, dtype=np.int64))[: len(x)]
            even += int(((count % 2 == 0) & (count > 0) & fin).sum())
            odd += int(((count % 2 == 1) & fin).sum())
            zero_scale = np.flatnonzero((ours == 0) & fin)
            assert all(not np.isfinite(x[i]) or x[i] == 0 for i in zero_scale), f"{name}：尺度 0 之列本身非 0"
    assert even > 0 and odd > 0, (even, odd)


def test_bound_formulas_cover_exact_error_with_fractions(requires_kline_data) -> None:
    """(ii) 界 ≥ Fraction 精確 err（審 r1 CODEX-R1-P1-01）：真實欄全格以 judge_bound 判 0 超界；另抽真實格（含 a＝0 之
    fastk 分子；輸入捨入跨 binade 之格若出現亦併入）逐格以 Fraction 驗 float64 界 ≥ 精確 err。次正規輸入與跨 binade 捨入於
    真實 BTCUSDT/1h 不出現（實測 0 格）⇒ 具名未覆蓋，只記錄不斷言（SPEC Task 3.3 ②「無則具名記未覆蓋」）。"""
    r = _real(requires_kline_data)
    pairs: List[Tuple[str, str, str]] = [("Ratio", "close", "fastk"), ("Ratio", "fastk", "close"),
                                          ("Cross", "close", "ema"), ("Cross", "fastk", "fastd")]
    a_zero = cross_binade = 0
    for op, num, den in pairs:
        a, b = r[num], r[den]
        out32 = _polars_arm(op, a, b)
        report = lo.judge_bound(op, a, b, out32)
        assert report["violations"] == [] and report["nan_mismatch"] == 0 and report["finite"] > 0, (op, num, den, report)
        ref = lo.oracle(op, a, b)
        fin = np.flatnonzero(np.isfinite(out32) & np.isfinite(ref))
        binade = fin[(np.frexp(a[fin].astype(np.float32).astype(np.float64))[1] != np.frexp(a[fin])[1])
                     | (np.frexp(b[fin].astype(np.float32).astype(np.float64))[1] != np.frexp(b[fin])[1])]
        zeros = fin[a[fin] == 0]
        sample = np.unique(np.concatenate([fin[:: max(1, len(fin) // 400)], zeros[:50], binade[:50]]))
        a_zero += int(zeros.size)
        cross_binade += int(binade.size)
        for i in sample:
            assert lo.exact_within_bound(op, float(a[i]), float(b[i]), out32[i]), (op, num, den, int(i))
    assert a_zero > 0, "真實資料未出現 a＝0 之格"
    # 跨 binade 捨入（值在 2 的冪下方半個 float32 ulp 內）：真實資料出現則已併入逐格精確驗；不出現即未覆蓋（只記錄）
    print(f"[I1f2] 跨 binade 捨入之真實格數＝{cross_binade}（0＝未覆蓋）；次正規輸入＝未覆蓋")


def test_mutation_near_zero_term_removed_breaks_ratio_oracle(requires_kline_data, monkeypatch) -> None:
    """改壞對照：`causal_near_zero_mask` 去掉相對近零項（兩臂共用）⇒ 真實近零列兩臂非 NaN ⇒ 判定失敗。"""
    r = _real(requires_kline_data)
    real_scale = numeric_guards.causal_denominator_scale

    def mutant(values, rel_eps=numeric_guards.DEFAULT_DENOM_REL_EPS, window=numeric_guards.DEFAULT_DENOM_SCALE_WINDOW):
        d = np.asarray(values, dtype=np.float64)
        scale = real_scale(d, window)
        return ~np.isfinite(d) | (np.abs(d) == 0) | ~np.isfinite(scale)

    monkeypatch.setattr(numeric_guards, "causal_near_zero_mask", mutant)
    a, b = r["close"], r["fastk"]
    p, c = _polars_arm("Ratio", a, b), _category_arm("Ratio", a, b)
    row = int(np.flatnonzero(r["ts"] == NEAR_ZERO_TS["fastk"])[0])
    assert np.isfinite(p[row]) and np.isfinite(c[row]), "改壞未生效：近零列仍被遮罩"
    bad = _arm_violations("Ratio", a, b, p, c)
    assert any("|polars|NaN 位置不一致" in x for x in bad) and any("|category|NaN 位置不一致" in x for x in bad), bad[:6]


def test_mutation_category_judged_in_float32_misses_f64_error(requires_kline_data) -> None:
    """改壞對照：category 臂有限格加 2·spacing(ref64)；float64 判須報超界、float32 視角漏報（審 r1 GROK-R1-P1-01）。"""
    r = _real(requires_kline_data)
    a, b = r["close"], r["ema"]
    out = _category_arm("Cross", a, b)
    ref64 = lo.oracle("Cross", a, b)
    i = int(np.flatnonzero(np.isfinite(ref64) & (np.abs(ref64) > 1.0))[0])
    bad = out.copy()
    bad[i] = ref64[i] + 2 * np.spacing(ref64[i])
    assert lo.within_1ulp(out, ref64).all()
    assert not lo.within_1ulp(bad, ref64)[i], "float64 判定未抓到 2 ulp64 誤差"
    assert lo.within_1ulp(bad.astype(np.float32), ref64.astype(np.float32))[i], "float32 視角應漏報（對照不成立）"
    with pytest.raises(TypeError):
        lo.within_1ulp(bad.astype(np.float32), ref64)


def test_mutation_nonfinite_vs_finite_detected_both_arms(requires_kline_data) -> None:
    """改壞對照（審碼 b1 r1 CODEX-R1-P1-01／GROK-R1-P1-01）：兩臂真實有限格改為 +inf、−inf、NaN ⇒ (i) 判定皆報出；
    雙 NaN 與同號 inf 仍通過、異號 inf 不通過。"""
    r = _real(requires_kline_data)
    a, b = r["close"], r["ema"]
    p, c = _polars_arm("Cross", a, b), _category_arm("Cross", a, b)
    assert _arm_violations("Cross", a, b, p, c) == [], "前提不成立：正案已有違規"
    i = int(np.flatnonzero(np.isfinite(c) & np.isfinite(p))[0])
    for value in (np.inf, -np.inf, np.nan):
        for arm in ("polars", "category"):
            pm, cm = p.copy(), c.copy()
            (pm if arm == "polars" else cm)[i] = value
            bad = _arm_violations("Cross", a, b, pm, cm)
            assert any(f"|{arm}|" in x and f"列 {i}：" in x for x in bad), (arm, value, bad[:4])
    for dtype in (np.float32, np.float64):
        pairs = np.array([np.nan, np.inf, -np.inf, np.inf], dtype=dtype), np.array([np.nan, np.inf, -np.inf, -np.inf], dtype=dtype)
        assert lo.within_1ulp(*pairs).tolist() == [True, True, True, False], dtype
