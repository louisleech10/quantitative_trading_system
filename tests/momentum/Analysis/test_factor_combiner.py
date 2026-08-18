"""GAP-2a 多因子組合 IC 測試（Task 2.1／2.2；SPEC §G O4／O8／O9＋①–⑦）。

探針對映（Task 2.2；每 V_ID 全票唯一）：V-7→``test_o8_sign_from_train_negative_case``；
V-8→``test_ic_weighted_uses_train_ic_reference``；V-9→``test_delta_ci_uses_block_len_reference``。
合成產生器參數寫死於 SPEC §G 表（O4：seed 20260818、n=20000、f1..f4、y=0.3·Σf+ε(σ=0.8)）。
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from momentum.Analysis import factor_combiner as fcm
from momentum.Analysis import marginal_ic as mic
from momentum.Analysis.factor_combiner import CompositeResult, block_bootstrap_ci, combine_factors
from momentum.Analysis.marginal_ic import MarginalICParams, compute_marginal_ic, normal_scores
from momentum.Analysis.survivor_contract import load_survivor_contract

FAST = MarginalICParams(n_bootstrap=100, block_len=5)


def _masks(n: int) -> Tuple[np.ndarray, np.ndarray]:
    tr = np.zeros(n, dtype=bool)
    tr[: int(n * 0.6)] = True
    return tr, ~tr


def _gen_o4():
    rng = np.random.default_rng(20260818)
    n = 20000
    f = rng.standard_normal((n, 4))
    eps = rng.normal(0.0, 0.8, n)
    y = 0.3 * f.sum(axis=1) + eps
    df = pd.DataFrame(f, columns=["f1", "f2", "f3", "f4"])
    tr, te = _masks(n)
    return df, pd.Series(y), tr, te


def _gen_o2():
    rng = np.random.default_rng(20260803)
    n = 5000
    s1 = rng.standard_normal(n)
    s2 = rng.standard_normal(n)
    f = rng.standard_normal(n)
    eps = rng.normal(0.0, 0.812, n)
    y = 0.3 * s1 + 0.3 * s2 + 0.4 * f + eps
    df = pd.DataFrame({"s1": s1, "s2": s2, "f": f})
    tr, te = _masks(n)
    return df, pd.Series(y), tr, te


def _gen_o7():
    rng = np.random.default_rng(20260807)
    n = 4000
    s = rng.standard_normal(n)
    eta = rng.standard_normal(n)
    tr, te = _masks(n)
    f = np.where(tr, s + 0.3 * eta, -s + 0.3 * eta)
    eps = rng.normal(0.0, 0.866, n)
    y = 0.5 * s + eps
    return pd.DataFrame({"s": s, "f": f}), pd.Series(y), tr, te


def _run(df, y, tr, te, survivors, *, params=FAST, fit_scope="train") -> CompositeResult:
    return combine_factors(df, y, train_mask=tr, test_mask=te, survivors=list(survivors), params=params, fit_scope=fit_scope)


def _sp(a, b) -> float:
    return float(stats.spearmanr(a, b)[0])


# ============================================================================
# §G O4 — 加法性／組合帶寬（等 ρ 四因子）
# ============================================================================
def test_o4_additivity_and_composite_band():
    df, y, tr, te = _gen_o4()
    surv = ["f1", "f2", "f3", "f4"]
    p = MarginalICParams(n_bootstrap=20, block_len=5)
    comp_eq = _run(df, y, tr, te, surv, params=p)
    comp_w = _run(df, y, tr, te, surv, params=MarginalICParams(n_bootstrap=20, block_len=5, weights_method="ic_weighted"))
    assert comp_eq.status == "ok"
    assert 0.55 <= comp_eq.composite_ic <= 0.61
    assert abs(comp_eq.composite_ic - comp_w.composite_ic) <= 1e-3
    marg = compute_marginal_ic(df, y, train_mask=tr, test_mask=te, survivors=surv, params=p, fit_scope="train")
    seq = [e["marginal_ic"] for e in marg.sequential]
    for v in seq:
        assert 0.26 <= v <= 0.31, seq
    ratio = sum(v * v for v in seq) / (comp_eq.composite_ic ** 2)
    assert 0.90 <= ratio <= 1.10, ratio
    assert abs(sum(comp_eq.weights.values()) - 1.0) <= 1e-12
    assert abs(sum(comp_w.weights.values()) - 1.0) <= 1e-12


# ============================================================================
# §G O8 — 組合對照
# ============================================================================
def test_o8_single_factor_composite_equals_signed_gross():
    df, y, tr, te = _gen_o2()
    for name in ["s1", "f"]:
        r = _run(df, y, tr, te, [name])
        rows = te
        gross = _sp(df[name].to_numpy()[rows], y.to_numpy()[rows])
        train_ic = _sp(df[name].to_numpy()[tr], y.to_numpy()[tr])
        assert abs(r.composite_ic - math.copysign(1.0, train_ic) * gross) <= 1e-12
    # 三因子 equal：composite_ic ≥ max(gross) − 0.02
    r3 = _run(df, y, tr, te, ["s1", "s2", "f"])
    grosses = [_sp(df[n].to_numpy()[te], y.to_numpy()[te]) for n in ["s1", "s2", "f"]]
    assert r3.composite_ic >= max(grosses) - 0.02
    # f2 = f1 ⇒ composite_ic == sign(train_ic)·gross(f1)；等 train IC 下 ic_weighted == equal（1e-12）
    df2 = df.copy()
    df2["f_dup"] = df2["f"]
    r_dup = _run(df2, y, tr, te, ["f", "f_dup"])
    r_dup_w = _run(df2, y, tr, te, ["f", "f_dup"], params=MarginalICParams(n_bootstrap=100, block_len=5, weights_method="ic_weighted"))
    gross_f = _sp(df["f"].to_numpy()[te], y.to_numpy()[te])
    train_f = _sp(df["f"].to_numpy()[tr], y.to_numpy()[tr])
    assert abs(r_dup.composite_ic - math.copysign(1.0, train_f) * gross_f) <= 1e-12
    assert abs(r_dup.composite_ic - r_dup_w.composite_ic) <= 1e-12
    assert set(r_dup.to_dict().keys()) == set(load_survivor_contract()["marginal_ic_section_keys"]["composite_keys"]["keys"].keys())  # ⑦


def test_o8_sign_from_train_negative_case():
    """O8 含 train_ic<0 案例（V-7 對映）：符號只由 train 段決定。

    O7 資料：f 於 train ≈ +s（train_ic>0）、於 test ≈ −s（test IC<0）；
    S={f} ⇒ composite_ic == sign(train_ic)·gross_ic == (+1)·(負值)。若符號改用 test IC ⇒ composite_ic 變正 ⇒ 紅。
    再以 −f 建 train_ic<0 之案例：composite_ic == (−1)·gross(−f)。
    """
    df, y, tr, te = _gen_o7()
    r = _run(df, y, tr, te, ["f"])
    train_ic = _sp(df["f"].to_numpy()[tr], y.to_numpy()[tr])
    gross = _sp(df["f"].to_numpy()[te], y.to_numpy()[te])
    assert train_ic > 0.3 and gross < -0.3
    assert r.signs["f"] == 1.0
    assert abs(r.composite_ic - math.copysign(1.0, train_ic) * gross) <= 1e-12
    assert r.composite_ic < 0
    df2 = df.copy()
    df2["nf"] = -df2["f"]
    r2 = _run(df2, y, tr, te, ["nf"])
    train_nf = _sp(df2["nf"].to_numpy()[tr], y.to_numpy()[tr])
    gross_nf = _sp(df2["nf"].to_numpy()[te], y.to_numpy()[te])
    assert train_nf < 0 and r2.signs["nf"] == -1.0
    assert abs(r2.composite_ic - math.copysign(1.0, train_nf) * gross_nf) <= 1e-12


def test_ic_weighted_uses_train_ic_reference():
    """V-8 對映：ic_weighted 權重 == |train_ic|/Σ|train_ic|（獨立重算，1e-12）；train≠test IC 之案例。"""
    df, y, tr, te = _gen_o7()
    df2 = df.copy()
    rng = np.random.default_rng(11)
    df2["w"] = 0.15 * df2["s"] + rng.standard_normal(len(df2))
    surv = ["s", "f", "w"]
    r = _run(df2, y, tr, te, surv, params=MarginalICParams(n_bootstrap=20, block_len=5, weights_method="ic_weighted"))
    train_ic = {n: _sp(df2[n].to_numpy()[tr], y.to_numpy()[tr]) for n in surv}
    test_ic = {n: _sp(df2[n].to_numpy()[te], y.to_numpy()[te]) for n in surv}
    tot = sum(abs(v) for v in train_ic.values())
    for n in surv:
        assert abs(r.weights[n] - abs(train_ic[n]) / tot) <= 1e-12, n
    # 可證偽：test IC 權重與 train IC 權重明顯不同（f 於 test 段反向且 w 比例不同）
    tot_te = sum(abs(v) for v in test_ic.values())
    assert max(abs(abs(train_ic[n]) / tot - abs(test_ic[n]) / tot_te) for n in surv) > 0.02
    assert r.top_train_single == max(surv, key=lambda n: abs(train_ic[n]))
    assert abs(r.top_train_single_test_ic - test_ic[r.top_train_single]) <= 1e-12
    assert r.best_single_feature == max(surv, key=lambda n: abs(test_ic[n]))


# ============================================================================
# §G O9 — bootstrap（含 V-9 對映）
# ============================================================================
def _ref_block_ci(stat_fn, arrays, *, block_len: int, n_bootstrap: int, seed: int) -> Tuple[float, float]:
    """獨立參考 moving-block bootstrap（與待測同協定，測試內自寫）。"""
    n = len(arrays[0])
    b = min(block_len, n)
    n_blocks = int(math.ceil(n / b))
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_bootstrap):
        starts = rng.integers(0, n - b + 1, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + b) for s in starts])[:n]
        v = float(stat_fn(*[a[idx] for a in arrays]))
        if math.isfinite(v):
            vals.append(v)
    lo, hi = float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))
    point = float(stat_fn(*arrays))
    return (min(lo, point), max(hi, point))  # A1-8 包絡（與待測同定義）


def test_delta_ci_uses_block_len_reference():
    """V-9 對映：delta_ci95 == 獨立參考 block bootstrap（同 block_len=7、seed）；block_len 強制 1 ⇒ 不等。"""
    df, y, tr, te = _gen_o2()
    surv = ["s1", "s2", "f"]
    p = MarginalICParams(n_bootstrap=150, block_len=7, seed=20260818)
    r = _run(df, y, tr, te, surv, params=p)
    # 重建 composite（等權、train 符號）與 f_top、y_te
    yv = y.to_numpy()
    train_ic = {n: _sp(df[n].to_numpy()[tr], yv[tr]) for n in surv}
    comp = sum(math.copysign(1.0, train_ic[n]) * normal_scores(df[n].to_numpy()[te]) for n in surv) / len(surv)
    top = max(surv, key=lambda n: abs(train_ic[n]))
    f_top = df[top].to_numpy()[te]
    ref7 = _ref_block_ci(lambda c, f, yy: _sp(c, yy) - _sp(f, yy), (comp, f_top, yv[te]), block_len=7, n_bootstrap=150, seed=20260818)
    ref1 = _ref_block_ci(lambda c, f, yy: _sp(c, yy) - _sp(f, yy), (comp, f_top, yv[te]), block_len=1, n_bootstrap=150, seed=20260818)
    assert abs(r.delta_ci95[0] - ref7[0]) <= 1e-12 and abs(r.delta_ci95[1] - ref7[1]) <= 1e-12
    assert r.delta_ci95 != pytest.approx(ref1, abs=1e-9)  # block_len 真被使用（≥ effective_horizon 之語意）
    assert r.delta_ci95[0] <= r.delta_vs_top_train_single <= r.delta_ci95[1]  # ④ CI 含點估


def test_o9_same_seed_exact_and_block_len_zero_raises():
    df, y, tr, te = _gen_o2()
    p = MarginalICParams(n_bootstrap=80, block_len=5, seed=7)
    a = _run(df, y, tr, te, ["s1", "s2", "f"], params=p)
    b = _run(df, y, tr, te, ["s1", "s2", "f"], params=p)
    assert a.delta_ci95 == b.delta_ci95 and a.delta_ci95[0] < a.delta_ci95[1]  # ⑤
    with pytest.raises(ValueError):
        block_bootstrap_ci(lambda u, v: float(np.mean(u * v)), (np.arange(10.0), np.arange(10.0)), block_len=0, n_bootstrap=5, seed=1)  # ⑥
    with pytest.raises(ValueError):
        _run(df, y, tr, te, ["s1"], params=MarginalICParams(n_bootstrap=5, block_len=0))
    one = _run(df, y, tr, te, ["s1"], params=MarginalICParams(n_bootstrap=1, block_len=5))
    assert one.delta_ci95[0] <= one.delta_vs_top_train_single <= one.delta_ci95[1]  # n_bootstrap=1 可跑且含點估（A1-8）
    # codex R15 反例：O2 三因子、block_len=7、seed=1、n_bootstrap=1 ⇒ CI 仍含 delta
    cx = _run(df, y, tr, te, ["s1", "s2", "f"], params=MarginalICParams(n_bootstrap=1, block_len=7, seed=1))
    assert cx.delta_ci95[0] <= cx.delta_vs_top_train_single <= cx.delta_ci95[1]
    # bootstrap 搬移後 marginal_ic 之 re-export 為同一物件
    assert mic.block_bootstrap_ci is fcm.block_bootstrap_ci


# ============================================================================
# ①–③ 與邊界
# ============================================================================
def test_two_identical_factors_equal_weight_and_alignment_helps():
    df, y, tr, te = _gen_o2()
    df2 = df.copy()
    df2["neg"] = -df2["s1"]  # train_ic<0、test 同號
    r = _run(df2, y, tr, te, ["neg", "s2"])
    assert r.signs["neg"] == -1.0 and r.signs["s2"] == 1.0
    # 未對齊版（手算：不翻符號）之 composite_ic 應更低（②）
    yv = y.to_numpy()
    comp_unaligned = normal_scores(df2["neg"].to_numpy()[te]) + normal_scores(df2["s2"].to_numpy()[te])
    assert r.composite_ic > _sp(comp_unaligned, yv[te]) + 0.1
    assert abs(sum(r.weights.values()) - 1.0) <= 1e-12  # ③


def test_zero_train_ic_exclusion_and_all_zero():
    df, y, tr, te = _gen_o2()
    df2 = df.copy()
    df2["c"] = 1.0  # 常數 ⇒ train_ic NaN ⇒ 排除
    r = _run(df2, y, tr, te, ["c", "s1"])
    assert r.excluded == {"c": "zero_train_ic"} and set(r.weights) == {"s1"}
    df3 = df.copy()
    df3["c1"] = 1.0
    df3["c2"] = 2.0
    r_all = _run(df3, y, tr, te, ["c1", "c2"])
    assert (r_all.status, r_all.reason) == ("not_computed", "all_zero_train_ic")
    assert set(r_all.excluded) == {"c1", "c2"} and r_all.weights == {}


def test_section_gates_and_scope():
    df, y, tr, te = _gen_o2()
    r0 = _run(df, y, tr, te, [])
    assert (r0.status, r0.reason) == ("not_applicable", "no_survivors")
    r1 = _run(df, y, None, None, ["s1"])
    assert (r1.status, r1.reason) == ("not_applicable", "no_holdout_split")
    small = np.zeros(len(df), dtype=bool)
    small[-5:] = True
    r2 = _run(df, y, tr, small, ["s1"])
    assert (r2.status, r2.reason) == ("not_computed", "insufficient_test_rows")
    with pytest.raises(ValueError):
        _run(df, y, np.ones(len(df), bool), np.ones(len(df), bool), ["s1"])
    with pytest.raises(ValueError):
        _run(df, y, tr, te, ["s1"], params=MarginalICParams(n_bootstrap=5, weights_method="ols"))
    full = _run(df, y, np.ones(len(df), bool), np.ones(len(df), bool), ["s1"], fit_scope="full_sample")
    assert full.status == "ok" and full.fit_scope == "full_sample" and full.oos_guarantees is None
    # complete-case：NaN 列被剔除且 n_used 反映
    df2 = df.copy()
    df2.loc[df2.index[-50:], "s2"] = np.nan
    r3 = _run(df2, y, tr, te, ["s1", "s2"])
    assert r3.n_used_test == int(te.sum()) - 50
    assert set(r3.to_dict()["signs"]) == {"s1", "s2"}
    with pytest.raises(ValueError):
        _run(df, y, tr, te, ["s1", "s1"])


def test_marginal_ic_o9_still_green_after_bootstrap_move():
    """Task 1.2 測試搬移後仍綠（本檔只確認 re-export 路徑可用；完整 B1 測試於 test_marginal_ic.py）。"""
    ci = mic.block_bootstrap_ci(lambda u, v: float(np.mean(u * v)), (np.arange(20.0), np.arange(20.0)), block_len=4, n_bootstrap=30, seed=5)
    assert ci is not None and ci[0] <= ci[1]


def test_mutation_test_sign_breaks_o8(monkeypatch):
    """探針：符號改由 test 段估 ⇒ O8 之 O7 負 IC 案例必紅（最窄 seam：把 ``_spearman`` 於 train 段呼叫改讀 test 段結果）。

    seam：monkeypatch ``mic._spearman`` 為「若輸入長度 == n_train 則改用對應 test 段陣列計算」——
    使 sign／weight 由 test IC 決定，其餘不變。
    """
    df, y, tr, te = _gen_o7()
    train_ic = _sp(df["f"].to_numpy()[tr], y.to_numpy()[tr])
    gross = _sp(df["f"].to_numpy()[te], y.to_numpy()[te])
    base = _run(df, y, tr, te, ["f"])
    assert abs(base.composite_ic - math.copysign(1.0, train_ic) * gross) <= 1e-12  # 基線綠

    real = mic._spearman
    f_te = df["f"].to_numpy()[te]
    y_te = y.to_numpy()[te]

    def test_sign_variant(a, b):
        if a.shape[0] == int(tr.sum()):  # train 段呼叫 ⇒ 偷換成 test 段
            return real(f_te, y_te)
        return real(a, b)

    monkeypatch.setattr(mic, "_spearman", test_sign_variant)
    mutant = _run(df, y, tr, te, ["f"])
    with pytest.raises(AssertionError):
        assert abs(mutant.composite_ic - math.copysign(1.0, train_ic) * gross) <= 1e-12
