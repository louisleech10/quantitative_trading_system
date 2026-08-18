"""GAP-2a 邊際 IC 純函式測試（Task 1.1／1.2；SPEC §G oracle 規格表逐字實作於 ``_gen``）。

- 合成產生器參數全部寫死於 SPEC §G 表（seed／n／係數／噪聲 σ／mask 前 60% train）；本檔不自選。
- 探針對映（Task 1.3 十條唯一）：V-1→``test_o7_train_fit``；V-2／V-21→``test_o1a_residual_degenerate``；
  V-3→``test_o6_rank_invariance``；V-4→``test_o2_orthogonal_new_info``；V-5→``test_sequential_order_by_train_ic``；
  V-6→``test_o9_bootstrap_seed_determinism``；V-17a→``test_o7_train_insample_differs``；
  V-18→``test_shuffle_survivors_invariance``；V-22a→``test_budget_survivors_whole_not_computed``。
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from momentum.Analysis import marginal_ic as mic
from momentum.Analysis.marginal_ic import (
    MarginalICParams,
    MarginalICResult,
    apply_residual,
    block_bootstrap_ci,
    compute_marginal_ic,
    fit_projection,
    normal_scores,
)
from momentum.Analysis.survivor_contract import load_survivor_contract

FAST = MarginalICParams(n_bootstrap=100, block_len=5)


# ============================================================================
# SPEC §G 合成產生器規格表（逐字）
# ============================================================================
def _masks(n: int) -> Tuple[np.ndarray, np.ndarray]:
    """前 60% 列 train／後 40% 列 test。"""
    tr = np.zeros(n, dtype=bool)
    tr[: int(n * 0.6)] = True
    return tr, ~tr


def _gen(oracle_id: str) -> Tuple[pd.DataFrame, pd.Series, np.ndarray, np.ndarray]:
    if oracle_id == "O1a":
        rng = np.random.default_rng(20260801)
        n = 5000
        s1 = rng.standard_normal(n)
        f = s1 ** 3
        eps = rng.normal(0.0, 0.866, n)
        y = 0.5 * s1 + eps
        df = pd.DataFrame({"s1": s1, "f": f})
    elif oracle_id == "O1b":
        rng = np.random.default_rng(20260802)
        n = 5000
        s1 = rng.standard_normal(n)
        eta = rng.standard_normal(n)
        f = np.tanh(2.0 * s1) + 0.05 * eta
        eps = rng.normal(0.0, 0.866, n)
        y = 0.5 * s1 + eps
        df = pd.DataFrame({"s1": s1, "f": f})
    elif oracle_id in ("O2", "O5"):
        rng = np.random.default_rng(20260803)
        n = 5000
        s1 = rng.standard_normal(n)
        s2 = rng.standard_normal(n)
        f = rng.standard_normal(n)
        eps = rng.normal(0.0, 0.812, n)
        y = 0.3 * s1 + 0.3 * s2 + 0.4 * f + eps
        df = pd.DataFrame({"s1": s1, "s2": s2, "f": f})
        if oracle_id == "O5":
            tr, te = _masks(n)
            perm_rng = np.random.default_rng(20260805)
            y = y.copy()
            y[te] = perm_rng.permutation(y[te])
    elif oracle_id == "O7":
        rng = np.random.default_rng(20260807)
        n = 4000
        s = rng.standard_normal(n)
        eta = rng.standard_normal(n)
        tr, te = _masks(n)
        f = np.where(tr, s + 0.3 * eta, -s + 0.3 * eta)
        eps = rng.normal(0.0, 0.866, n)
        y = 0.5 * s + eps
        df = pd.DataFrame({"s": s, "f": f})
    else:
        raise KeyError(oracle_id)
    tr, te = _masks(len(df))
    return df, pd.Series(y, index=df.index), tr, te


def _run(df, y, tr, te, survivors, *, extra=(), params=FAST, fit_scope="train") -> MarginalICResult:
    return compute_marginal_ic(
        df, y, train_mask=tr, test_mask=te, survivors=list(survivors),
        extra_candidates=list(extra), params=params, fit_scope=fit_scope,
    )


# ============================================================================
# Task 1.1 — 原語（-k "scores or projection"）
# ============================================================================
def test_normal_scores_monotone_invariance():
    rng = np.random.default_rng(1)
    x = np.abs(rng.standard_normal(500)) + 0.1  # 全正 ⇒ x**3 嚴格單調
    z = normal_scores(x)
    np.testing.assert_allclose(normal_scores(x ** 3), z, atol=1e-12)
    np.testing.assert_allclose(normal_scores(2.0 * x + 1.0), z, atol=1e-12)


def test_normal_scores_moments():
    rng = np.random.default_rng(2)
    z = normal_scores(rng.standard_normal(5000))
    assert abs(float(z.mean())) < 1e-9
    assert 0.95 <= float(z.std()) <= 1.0


def test_normal_scores_all_ties_zero_and_small_n():
    np.testing.assert_allclose(normal_scores(np.full(7, 3.3)), np.zeros(7), atol=1e-12)
    with pytest.raises(ValueError):
        normal_scores(np.array([1.0]))
    assert normal_scores(np.array([1.0, 2.0])).shape == (2,)


def test_fit_projection_recovers_beta():
    rng = np.random.default_rng(3)
    z_b = rng.standard_normal(300)
    z_t = 2.0 * z_b + 1.0
    proj = fit_projection(z_t, z_b.reshape(-1, 1))
    np.testing.assert_allclose(proj.beta, [1.0, 2.0], atol=1e-10)
    assert abs(proj.r2_train - 1.0) < 1e-10
    assert proj.n_train == 300
    np.testing.assert_allclose(apply_residual(z_t, z_b.reshape(-1, 1), proj), 0.0, atol=1e-9)


def test_fit_projection_empty_basis_residual_is_demeaned():
    rng = np.random.default_rng(4)
    z_t = rng.standard_normal(200)
    proj = fit_projection(z_t, np.empty((200, 0)))
    assert proj.beta.shape == (1,)
    np.testing.assert_allclose(apply_residual(z_t, np.empty((200, 0)), proj), z_t - z_t.mean(), atol=1e-12)
    assert abs(proj.r2_train) < 1e-12
    assert fit_projection(np.full(9, 2.5), np.empty((9, 0))).r2_train == 0.0  # ss_tot==0 ⇒ 0.0


def test_fit_projection_collinear_does_not_raise():
    rng = np.random.default_rng(5)
    a = rng.standard_normal(100)
    basis = np.column_stack([a, 2.0 * a])
    proj = fit_projection(a, basis)
    assert proj.condition_number > 1e6


def test_normal_scores_nan_raises_and_projection_shape_errors():
    with pytest.raises(ValueError):
        normal_scores(np.array([1.0, np.nan, 2.0]))
    with pytest.raises(ValueError):
        fit_projection(np.zeros(5), np.zeros((4, 1)))
    proj = fit_projection(np.arange(5.0), np.arange(5.0).reshape(-1, 1))
    with pytest.raises(ValueError):
        apply_residual(np.arange(5.0), np.zeros((5, 2)), proj)


def test_mutation_raw_scores_break_monotone_invariance(monkeypatch):
    """探針：把 ``normal_scores`` 換成恆等 ⇒ 單調不變性斷言必紅。"""
    rng = np.random.default_rng(6)
    x = np.abs(rng.standard_normal(300)) + 0.1
    np.testing.assert_allclose(mic.normal_scores(x ** 3), mic.normal_scores(x), atol=1e-12)  # 基線綠
    monkeypatch.setattr(mic, "normal_scores", lambda arr: np.asarray(arr, dtype=float))
    with pytest.raises(AssertionError):
        np.testing.assert_allclose(mic.normal_scores(x ** 3), mic.normal_scores(x), atol=1e-12)


# ============================================================================
# Task 1.2 — §G oracle
# ============================================================================
def test_o1a_residual_degenerate():
    """O1a：秩空間 x³ 與 s1 逐點相等 ⇒ residual_degenerate；raw 空間線性殘差非退化（防退回 raw）。"""
    df, y, tr, te = _gen("O1a")
    res = _run(df, y, tr, te, ["s1", "f"])
    pf = res.per_feature["f"]
    assert pf["status"] == "not_computed"
    assert pf["reason"] == "residual_degenerate"
    assert pf["marginal_ic"] is None and pf["ci95"] is None
    # raw 空間探針：同資料不做 normal_scores 之線性殘差 var>1e-3
    proj_raw = fit_projection(df["f"].to_numpy()[tr], df["s1"].to_numpy()[tr].reshape(-1, 1))
    r_raw = apply_residual(df["f"].to_numpy()[te], df["s1"].to_numpy()[te].reshape(-1, 1), proj_raw)
    assert float(np.var(r_raw)) > 1e-3
    # 條件 s1 自身（S={f}）在秩空間同樣退化
    assert res.per_feature["s1"]["reason"] == "residual_degenerate"


def test_o1b_saturating_transform():
    df, y, tr, te = _gen("O1b")
    res = _run(df, y, tr, te, ["s1", "f"])
    pf = res.per_feature["f"]
    assert (pf["status"] == "not_computed" and pf["reason"] == "residual_degenerate") or (
        pf["status"] == "ok" and abs(pf["marginal_ic"]) <= 0.02
    )


def test_o2_orthogonal_new_info():
    df, y, tr, te = _gen("O2")
    res = _run(df, y, tr, te, ["s1", "s2", "f"])
    pf = res.per_feature["f"]
    assert pf["status"] == "ok"
    assert abs(pf["marginal_ic"] - pf["gross_ic"]) <= 0.02
    assert pf["conditioning_set"] == ["s1", "s2"]
    assert res.n_regressions == 6  # loo 3 + sequential 3


def test_o3_empty_conditioning_set_marginal_equals_gross():
    df, y, tr, te = _gen("O2")
    res = _run(df, y, tr, te, ["f"])  # 單一 survivor ⇒ loo S=∅
    pf = res.per_feature["f"]
    assert pf["conditioning_set"] == []
    assert abs(pf["marginal_ic"] - pf["gross_ic"]) <= 1e-12
    seq0 = res.sequential[0]
    assert seq0["feature"] == "f" and seq0["step"] == 0
    assert abs(seq0["marginal_ic"] - seq0["gross_ic"]) <= 1e-12


def test_o5_label_permutation_bonferroni():
    df, y, tr, te = _gen("O5")
    surv = ["s1", "s2", "f"]
    res = _run(df, y, tr, te, surv)
    k = len(surv)
    n_test = int(te.sum())
    thr = stats.norm.ppf(1 - 0.05 / (2 * k)) / math.sqrt(n_test)
    for name in surv:
        assert res.per_feature[name]["status"] == "ok"
        assert abs(res.per_feature[name]["marginal_ic"]) < thr, name
    for entry in res.sequential:
        assert abs(entry["marginal_ic"]) < thr


def test_o6_rank_invariance():
    df, y, tr, te = _gen("O2")
    base = _run(df, y, tr, te, ["s1", "s2", "f"])
    df2 = df.copy()
    df2["f"] = 3.7 * df2["f"]
    df2["s1"] = df2["s1"] ** 3
    other = _run(df2, y, tr, te, ["s1", "s2", "f"])
    for name in ["s1", "s2", "f"]:
        for key in ("marginal_ic", "gross_ic", "ic_retained_ratio", "marginal_ic_train_insample"):
            assert abs(base.per_feature[name][key] - other.per_feature[name][key]) <= 1e-12, (name, key)
    for a, b in zip(base.sequential, other.sequential):
        assert a["feature"] == b["feature"]
        assert abs(a["marginal_ic"] - b["marginal_ic"]) <= 1e-12


def _reference_marginal_ic(f: np.ndarray, S: np.ndarray, y: np.ndarray, tr: np.ndarray, te: np.ndarray, *, fit_on: np.ndarray) -> float:
    """獨立 numpy 參考實作（同 D1 定義，≤20 行）：秩常態分數→OLS on ``fit_on`` 段→test 殘差→Spearman。"""
    def vdw(v):
        r = stats.rankdata(v, method="average")
        return stats.norm.ppf(r / (len(v) + 1.0))
    zf_fit = vdw(f[fit_on])
    ZS_fit = np.column_stack([vdw(S[fit_on, j]) for j in range(S.shape[1])]) if S.shape[1] else np.empty((fit_on.sum(), 0))
    X_fit = np.column_stack([np.ones(fit_on.sum()), ZS_fit])
    beta = np.linalg.lstsq(X_fit, zf_fit, rcond=None)[0]
    zf_te = vdw(f[te])
    ZS_te = np.column_stack([vdw(S[te, j]) for j in range(S.shape[1])]) if S.shape[1] else np.empty((te.sum(), 0))
    r_te = zf_te - np.column_stack([np.ones(te.sum()), ZS_te]) @ beta
    return float(stats.spearmanr(r_te, y[te])[0])


def test_o7_train_fit():
    """O7：與獨立參考實作 atol=1e-12；與 test 擬合 β 之值差 >0.3。"""
    df, y, tr, te = _gen("O7")
    res = _run(df, y, tr, te, ["s", "f"])
    pf = res.per_feature["f"]
    assert pf["status"] == "ok"
    ref_train = _reference_marginal_ic(df["f"].to_numpy(), df[["s"]].to_numpy(), y.to_numpy(), tr, te, fit_on=tr)
    ref_test = _reference_marginal_ic(df["f"].to_numpy(), df[["s"]].to_numpy(), y.to_numpy(), tr, te, fit_on=te)
    assert abs(pf["marginal_ic"] - ref_train) <= 1e-12
    assert abs(pf["marginal_ic"] - ref_test) > 0.3


def test_o7_train_insample_differs():
    df, y, tr, te = _gen("O7")
    res = _run(df, y, tr, te, ["s", "f"])
    pf = res.per_feature["f"]
    assert pf["marginal_ic_train_insample"] is not None
    assert abs(pf["marginal_ic_train_insample"] - pf["marginal_ic"]) > 0.3


def test_o9_bootstrap_seed_determinism():
    df, y, tr, te = _gen("O2")
    p = MarginalICParams(n_bootstrap=300, block_len=7, seed=20260818)
    a = _run(df, y, tr, te, ["s1", "s2", "f"], params=p)
    b = _run(df, y, tr, te, ["s1", "s2", "f"], params=p)
    for name in ["s1", "s2", "f"]:
        ci = a.per_feature[name]["ci95"]
        assert ci is not None and ci[0] <= a.per_feature[name]["marginal_ic"] <= ci[1]
        assert ci == b.per_feature[name]["ci95"]  # 同 seed exact
    with pytest.raises(ValueError):
        block_bootstrap_ci(lambda u, v: float(np.mean(u * v)), (np.arange(10.0), np.arange(10.0)), block_len=0, n_bootstrap=5, seed=1)
    one = block_bootstrap_ci(lambda u, v: float(np.mean(u * v)), (np.arange(10.0), np.arange(10.0)), block_len=3, n_bootstrap=1, seed=1)
    point = float(np.mean(np.arange(10.0) ** 2))
    assert one is not None and one[0] <= point <= one[1]  # n_bootstrap=1 亦含點估（A1-8）


# ============================================================================
# ⑧–⑮
# ============================================================================
def test_sequential_first_equals_gross_and_single_survivor_loo():
    df, y, tr, te = _gen("O2")
    res = _run(df, y, tr, te, ["s1", "s2", "f"])
    seq0 = res.sequential[0]
    assert abs(seq0["marginal_ic"] - res.per_feature[seq0["feature"]]["gross_ic"]) <= 1e-12  # ⑧
    single = _run(df, y, tr, te, ["s2"])  # ⑨
    assert abs(single.per_feature["s2"]["marginal_ic"] - single.per_feature["s2"]["gross_ic"]) <= 1e-12


def test_section_level_reasons_and_all_true_masks_raise():  # ⑩
    df, y, tr, te = _gen("O2")
    r1 = _run(df, y, None, None, ["s1"])
    assert (r1.status, r1.reason) == ("not_applicable", "no_holdout_split")
    r2 = _run(df, y, tr, te, [])
    assert (r2.status, r2.reason) == ("not_applicable", "no_survivors")
    small_te = np.zeros(len(df), dtype=bool)
    small_te[-5:] = True
    r3 = _run(df, y, tr, small_te, ["s1"])
    assert (r3.status, r3.reason) == ("not_computed", "insufficient_test_rows")
    assert all(v["status"] == "not_computed" for v in r3.views.values())
    with pytest.raises(ValueError):
        _run(df, y, np.ones(len(df), bool), np.ones(len(df), bool), ["s1"])
    with pytest.raises(ValueError):
        _run(df, y, tr, te, ["s1"], fit_scope="bogus")
    # full_sample：呼叫方傳全 True ⇒ 照算；oos 欄佔位 None
    r4 = _run(df, y, np.ones(len(df), bool), np.ones(len(df), bool), ["s1"], fit_scope="full_sample")
    assert r4.status == "ok" and r4.fit_scope == "full_sample"
    assert r4.oos_guarantees is None and r4.pass_class is None
    assert r4.with_root("degraded_full_sample").pass_class == "full_sample_research_only"
    assert r4.with_root("ok_oos").oos_guarantees is True


def test_to_dict_keys_match_contract():  # ⑪
    df, y, tr, te = _gen("O2")
    res = _run(df, y, tr, te, ["s1", "s2"], extra=["f"])
    c = load_survivor_contract()["marginal_ic_section_keys"]
    d = res.to_dict()
    assert set(d.keys()) == set(c["section_keys"]["keys"].keys())
    for name, entry in d["per_feature"].items():
        assert set(entry.keys()) == set(c["per_feature_keys"]["keys"].keys()), name
    for entry in d["sequential"]:
        assert set(entry.keys()) == set(c["sequential_keys"]["keys"].keys())
    for name, entry in d["removed_candidates"].items():
        assert set(entry.keys()) == set(c["removed_candidate_keys"]["keys"].keys()), name
    assert set(d["budget"].keys()) == set(c["budget_keys"]["keys"].keys())
    assert set(d["views"].keys()) == set(load_survivor_contract()["view_values"])
    assert d["independent_oos_validation"] is False
    assert d["selection_sample"] == "test"
    assert d["statistic"] == "semi_partial_rank_ic" and d["projection_space"] == "rank_normal"
    assert d["removed_candidates"]["f"]["conditioning_set"] == ["s1", "s2"]


def test_negative_gross_ratio_is_one():  # ⑫
    df, y, tr, te = _gen("O2")
    df2 = df.copy()
    df2["neg"] = -df2["f"]
    res = _run(df2, y, tr, te, ["neg"])
    pf = res.per_feature["neg"]
    assert pf["gross_ic"] < 0
    assert abs(pf["ic_retained_ratio"] - 1.0) <= 1e-6


def test_shuffle_survivors_invariance():  # ⑬
    df, y, tr, te = _gen("O2")
    a = _run(df, y, tr, te, ["s1", "s2", "f"])
    b = _run(df, y, tr, te, ["f", "s1", "s2"])
    for name in ["s1", "s2", "f"]:
        assert a.per_feature[name]["marginal_ic"] == b.per_feature[name]["marginal_ic"]
        assert set(a.per_feature[name]["conditioning_set"]) == set(b.per_feature[name]["conditioning_set"])
    assert [e["feature"] for e in a.sequential] == [e["feature"] for e in b.sequential]


def test_sequential_order_by_train_ic():
    """順序＝|train_ic| 遞減（tie 依名稱）；O7 型翻轉使 train／test 順序不同，故用 test IC 排會紅。"""
    df, y, tr, te = _gen("O7")
    df2 = df.copy()
    rng = np.random.default_rng(99)
    eta2 = rng.standard_normal(len(df2))
    s_arr = df2["s"].to_numpy()
    # w：train 段弱（0.05·s＋η）、test 段強（s＋0.05·η）⇒ 依 train IC 排最後、依 test IC 排在 f 之前
    df2["w"] = np.where(tr, 0.05 * s_arr + eta2, s_arr + 0.05 * eta2)
    res = _run(df2, y, tr, te, ["w", "s", "f"])
    names = [e["feature"] for e in res.sequential]
    expected = sorted(["w", "s", "f"], key=lambda n: (-abs(res.train_ic[n]), n))
    assert names == expected
    assert names[-1] == "w"  # train 弱 ⇒ 最後
    # 若改用 test 段 IC 排序，w 會排到 f 之前（順序不同 ⇒ 可證偽）
    test_ic = {n: abs(stats.spearmanr(df2[n].to_numpy()[te], y.to_numpy()[te])[0]) for n in ["w", "s", "f"]}
    assert test_ic["w"] > test_ic["f"]
    assert names.index("f") < names.index("w")
    for i, e in enumerate(res.sequential):
        assert e["step"] == i and e["conditioning_set"] == names[:i]


def test_budget_survivors_whole_not_computed():  # ⑭
    df, y, tr, te = _gen("O2")
    p = MarginalICParams(n_bootstrap=20, max_survivors_for_loo=2)
    res = _run(df, y, tr, te, ["s1", "s2", "f"], params=p)
    assert res.views["loo"] == {"status": "not_computed", "reason": "candidate_budget_exceeded"}
    assert res.views["sequential"]["reason"] == "candidate_budget_exceeded"
    assert res.per_feature == {} and res.sequential == ()
    assert res.status == "not_computed" and res.reason == "candidate_budget_exceeded"
    assert res.n_regressions == 0
    assert res.budget == {"max_survivors_for_loo": 2, "max_removed_candidates": 200, "n_survivors": 3, "n_removed_candidates": 0}
    # 只超 removed 預算 ⇒ removed 整體 not_computed、loo 不受影響、n_regressions 不含 removed
    p2 = MarginalICParams(n_bootstrap=20, max_removed_candidates=0)
    r2 = _run(df, y, tr, te, ["s1", "s2"], extra=["f"], params=p2)
    assert r2.views["removed_candidates"]["reason"] == "candidate_budget_exceeded"
    assert r2.removed_candidates == {}
    assert r2.views["loo"]["status"] == "ok" and set(r2.per_feature) == {"s1", "s2"}
    assert r2.status == "ok" and r2.n_regressions == 4


def test_fit_projection_spy_matches_n_regressions(monkeypatch):  # ⑮
    df, y, tr, te = _gen("O2")
    calls: List[int] = []
    real = mic.fit_projection

    def spy(z_target, z_basis):
        calls.append(int(np.asarray(z_basis).shape[1]) if np.asarray(z_basis).ndim == 2 else 0)
        return real(z_target, z_basis)

    monkeypatch.setattr(mic, "fit_projection", spy)
    p = MarginalICParams(n_bootstrap=10)
    res = _run(df, y, tr, te, ["s1", "s2"], extra=["f"], params=p)  # k=2, m=1 ⇒ 2k+m=5
    assert len(calls) == res.n_regressions == 5
    assert max(calls) <= 2
    calls.clear()
    over = _run(df, y, tr, te, ["s1", "s2", "f"], params=MarginalICParams(n_bootstrap=10, max_survivors_for_loo=1))
    assert len(calls) == 0 and over.n_regressions == 0
    calls.clear()
    only_removed_over = _run(df, y, tr, te, ["s1", "s2"], extra=["f"], params=MarginalICParams(n_bootstrap=10, max_removed_candidates=0))
    assert len(calls) == only_removed_over.n_regressions == 4


def test_nan_rows_filtered_per_candidate_and_label_all_nan_test():
    df, y, tr, te = _gen("O2")
    df2 = df.copy()
    df2.loc[df2.index[:100], "s2"] = np.nan  # train 段 100 列 NaN
    res = _run(df2, y, tr, te, ["s1", "s2", "f"])
    assert res.per_feature["s2"]["n_used_train"] == int(tr.sum()) - 100
    assert res.per_feature["s1"]["n_used_train"] == int(tr.sum()) - 100  # 條件集含 s2 ⇒ 同列被濾
    y2 = y.copy()
    y2[te] = np.nan
    r_nan = _run(df, y2, tr, te, ["s1"])
    assert r_nan.per_feature["s1"] == {**r_nan.per_feature["s1"], "status": "not_computed", "reason": "insufficient_rows"}
    assert r_nan.per_feature["s1"]["n_used_test"] == 0
    with pytest.raises(ValueError):
        _run(df, y, tr, te, ["s1", "s1"])


def test_constant_factor_is_degenerate_and_extra_overlap_deduped():
    df, y, tr, te = _gen("O2")
    df2 = df.copy()
    df2["c"] = 1.0
    res = _run(df2, y, tr, te, ["c", "s1"], extra=["s1", "f", "f"])
    assert res.per_feature["c"]["reason"] == "residual_degenerate"
    assert set(res.removed_candidates) == {"f"}
    assert res.budget["n_removed_candidates"] == 1


def test_mutation_test_fit_projection_breaks_o7(monkeypatch):
    """探針：呼叫端若在 test 段擬合 β（等價於 fit_projection 忽略 train、改用 test 資料）⇒ O7 參考值斷言必紅。

    最窄 seam：把 ``fit_projection`` 換成「回傳以 test 段擬合之 β」的變體——由 O7 資料之對稱構造，
    test 段擬合等價於 β 反號；此處以參考實作之 test-fit β 直接注入。
    """
    df, y, tr, te = _gen("O7")
    ref_train = _reference_marginal_ic(df["f"].to_numpy(), df[["s"]].to_numpy(), y.to_numpy(), tr, te, fit_on=tr)
    base = _run(df, y, tr, te, ["s", "f"])
    assert abs(base.per_feature["f"]["marginal_ic"] - ref_train) <= 1e-12  # 基線綠

    real = mic.fit_projection

    def test_fit_variant(z_target, z_basis):
        # 模擬「呼叫端傳入 test 陣列」：用 test 段 z 分數重擬合（形狀相同的最窄替換）
        f_te = normal_scores(df["f"].to_numpy()[te])
        s_te = normal_scores(df["s"].to_numpy()[te]).reshape(-1, 1)
        if np.asarray(z_basis).shape[1] == 1 and z_target.shape[0] == int(tr.sum()):
            return real(f_te, s_te)
        return real(z_target, z_basis)

    monkeypatch.setattr(mic, "fit_projection", test_fit_variant)
    mutant = _run(df, y, tr, te, ["s", "f"])
    with pytest.raises(AssertionError):
        assert abs(mutant.per_feature["f"]["marginal_ic"] - ref_train) <= 1e-12


# ============================================================================
# A1-7（B1 code review K2–K6 修補）
# ============================================================================
def test_reason_literals_in_marginal_ic_subset_of_contract():
    """K2：AST 掃 marginal_ic.py 內傳給 ``_reason(literals, <group>, <name>)`` 之字串常數 ⊆ 契約對應組。"""
    import ast
    import inspect

    src = inspect.getsource(mic)
    tree = ast.parse(src)
    contract = load_survivor_contract()
    pool = {"section": set(contract["reasons"]["marginal_ic"]), "feature": set(contract["reasons"]["marginal_ic_feature"])}
    seen = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "_reason":
            assert len(node.args) == 3, ast.dump(node)
            group, name = node.args[1], node.args[2]
            assert isinstance(group, ast.Constant) and isinstance(name, ast.Constant), ast.dump(node)
            assert name.value in pool[group.value], (group.value, name.value)
            seen += 1
    assert seen >= 8
    # 節級／feature 級 reason 只由 _reason 取得：模組內不得有其他地方直接使用契約 reason 字面
    all_reasons = pool["section"] | pool["feature"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in all_reasons:
            parent_ok = False
            # 允許：作為 _reason 之第三引數
            for call in ast.walk(tree):
                if isinstance(call, ast.Call) and getattr(call.func, "id", None) == "_reason" and len(call.args) == 3 and call.args[2] is node:
                    parent_ok = True
                    break
            assert parent_ok, f"reason literal {node.value!r} used outside _reason()"


def test_view_status_keys_match_contract():
    """K3：每個 view entry 鍵集 == 契約 view_status_keys。"""
    df, y, tr, te = _gen("O2")
    res = _run(df, y, tr, te, ["s1", "s2"], extra=["f"])
    keys = set(load_survivor_contract()["marginal_ic_section_keys"]["view_status_keys"]["keys"].keys())
    for view, entry in res.to_dict()["views"].items():
        assert set(entry.keys()) == keys, view


def test_view_and_section_status_semantics():
    """K4：全部候選退化 ⇒ 節 not_computed:no_computable_candidates；loo 超限＋removed 非空 ⇒ 節仍 not_computed；removed 空 ⇒ not_applicable。"""
    df, y, tr, te = _gen("O2")
    df2 = df.copy()
    df2["c1"] = 1.0
    df2["c2"] = 2.0
    all_deg = _run(df2, y, tr, te, ["c1", "c2"])
    assert all(v["status"] == "not_computed" for v in all_deg.per_feature.values())
    assert all_deg.views["loo"] == {"status": "not_computed", "reason": "no_computable_candidates"}
    assert all_deg.views["sequential"]["reason"] == "no_computable_candidates"
    assert (all_deg.status, all_deg.reason) == ("not_computed", "no_computable_candidates")
    assert all_deg.views["removed_candidates"] == {"status": "not_applicable", "reason": "no_removed_candidates"}
    # grok 反例：loo 超限但 removed 有候選且可算 ⇒ 節級仍 not_computed（removed 不抬升）
    over = _run(df, y, tr, te, ["s1", "s2", "f"], extra=["s1"] , params=MarginalICParams(n_bootstrap=10, max_survivors_for_loo=2))
    assert over.views["removed_candidates"]["status"] == "not_applicable"  # extra ⊆ survivors ⇒ 去重後空
    df3 = df.copy()
    df3["z"] = 0.1 * df3["f"] + np.random.default_rng(7).standard_normal(len(df3))
    over2 = _run(df3, y, tr, te, ["s1", "s2", "f"], extra=["z"], params=MarginalICParams(n_bootstrap=10, max_survivors_for_loo=2))
    assert over2.views["removed_candidates"]["status"] == "ok" and over2.removed_candidates["z"]["status"] == "ok"
    assert over2.per_feature == {} and (over2.status, over2.reason) == ("not_computed", "candidate_budget_exceeded")
    assert over2.n_regressions == 1
    # 正常：removed 有候選 ⇒ ok；無候選 ⇒ not_applicable
    normal = _run(df, y, tr, te, ["s1", "s2"], extra=["f"], params=MarginalICParams(n_bootstrap=10))
    assert normal.views["removed_candidates"]["status"] == "ok" and normal.status == "ok"


def test_constant_label_is_label_degenerate():
    """K4：label 於 test（或 train）段為常數 ⇒ 候選 not_computed:label_degenerate（先於 Spearman）。"""
    df, y, tr, te = _gen("O2")
    y2 = y.copy()
    y2[te] = 1.0
    res = _run(df, y2, tr, te, ["s1", "s2"], params=MarginalICParams(n_bootstrap=10))
    for name in ["s1", "s2"]:
        pf = res.per_feature[name]
        assert (pf["status"], pf["reason"]) == ("not_computed", "label_degenerate")
        assert pf["marginal_ic"] is None and pf["gross_ic"] is None
    assert (res.status, res.reason) == ("not_computed", "no_computable_candidates")
    y3 = y.copy()
    y3[tr] = 0.0
    res_tr = _run(df, y3, tr, te, ["s1"], params=MarginalICParams(n_bootstrap=10))
    assert res_tr.per_feature["s1"]["reason"] == "label_degenerate"


def test_marginal_uses_spearman_not_pearson():
    """K5：重尾 label 下秩常態殘差對 y 之 Spearman 與 Pearson 差 >0.05；marginal_ic 必等於 Spearman 參考（1e-12）。"""
    rng = np.random.default_rng(20260819)
    n = 4000
    s = rng.standard_normal(n)
    f = rng.standard_normal(n)
    heavy = rng.standard_t(df=2, size=n)  # 重尾噪聲
    y = 0.5 * s + 0.4 * f + heavy
    df = pd.DataFrame({"s": s, "f": f})
    tr, te = _masks(n)
    res = _run(df, pd.Series(y), tr, te, ["s", "f"], params=MarginalICParams(n_bootstrap=10))
    pf = res.per_feature["f"]
    assert pf["status"] == "ok"
    # 獨立參考：秩常態殘差（train 擬合）→ test 段 Spearman／Pearson
    def vdw(v):
        r = stats.rankdata(v, method="average")
        return stats.norm.ppf(r / (len(v) + 1.0))
    zf_tr, zs_tr = vdw(f[tr]), vdw(s[tr])
    beta = np.linalg.lstsq(np.column_stack([np.ones(tr.sum()), zs_tr]), zf_tr, rcond=None)[0]
    r_te = vdw(f[te]) - np.column_stack([np.ones(te.sum()), vdw(s[te])]) @ beta
    sp = float(stats.spearmanr(r_te, y[te])[0])
    pe = float(stats.pearsonr(r_te, y[te])[0])
    assert abs(sp - pe) > 0.05, (sp, pe)
    assert abs(pf["marginal_ic"] - sp) <= 1e-12
    assert abs(pf["marginal_ic"] - pe) > 0.05


def test_o9_bootstrap_resamples_nontrivially():
    """K6：CI 寬度 >0（點估 mutant 寬度 0 ⇒ 紅）；換 seed 至少一特徵 CI 不同。"""
    df, y, tr, te = _gen("O2")
    a = _run(df, y, tr, te, ["s1", "s2", "f"], params=MarginalICParams(n_bootstrap=200, block_len=7, seed=1))
    b = _run(df, y, tr, te, ["s1", "s2", "f"], params=MarginalICParams(n_bootstrap=200, block_len=7, seed=2))
    widths = [a.per_feature[n]["ci95"][1] - a.per_feature[n]["ci95"][0] for n in ["s1", "s2", "f"]]
    assert min(widths) > 0.0
    assert any(a.per_feature[n]["ci95"] != b.per_feature[n]["ci95"] for n in ["s1", "s2", "f"])
    arr = np.arange(30.0)
    point = float(np.mean(arr * arr))
    ci = block_bootstrap_ci(lambda u, v: float(np.mean(u * v)), (arr, arr), block_len=3, n_bootstrap=50, seed=3)
    assert ci is not None and ci[0] < ci[1] and not (ci[0] == point == ci[1])
