"""Task 4.2 驗證：PBO 值（golden 三案例／轉置／平手／path 級退化 A1-15／NaN 候選／universe_scope A1-4）。

golden：`tests/momentum/Analysis/golden/gap1_reference_cases.json`（sha256 防改；alpha 之 mu 由公式重算 atol=1e-18）。
mutation §V-4（改由 OOS 選 champion）⇒ noise／alpha_detectable 至少一條轉紅；§V-14（改回原始索引取名次）⇒ ④d 轉紅。
"""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest

from momentum.Analysis.strategy_validation.cscv import cscv_path_count
from momentum.Analysis.strategy_validation.deflated_sharpe import expected_max_sharpe_factor
from momentum.Analysis.strategy_validation.ledger import LedgerReadResult
from momentum.Analysis.strategy_validation.min_btl import max_trials_budget, min_btl_years_upper_bound
from momentum.Analysis.strategy_validation.pbo import (
    PBOResult,
    UniverseProvenance,
    _metrics_columns,
    candidate_set_hash,
    probability_of_backtest_overfitting,
)
from momentum.Analysis.strategy_validation.sharpe import compute_sharpe
from momentum.core.frequency import resolve_periods_per_year

from ._golden import GOLDEN_SHA256 as _GOLDEN_SHA256, load_golden as _golden  # noqa: E402  (N6：sha 常數唯一定義處)




def _ledger(ids):
    ids = list(ids)
    return LedgerReadResult(
        n_candidates_considered=len(ids), n_evaluated=len(ids), n_valid_metrics=len(ids), n_failed_or_pruned=0,
        n_rows_rejected=0, n_is_lower_bound=True, n_for_dsr=len(ids), snapshot_hash="s",
        artifact_hashes=frozenset({"h"}), candidate_ids=frozenset(ids), n_semantics="unknown",
        valid_sharpe_values=(), status="ok", reason="",
    )


def _prov(ids, **over):
    base = dict(selection_free=True, source="ledger_all_candidates", candidate_set_hash=candidate_set_hash(ids),
                candidate_count=len(ids), declared_by="test")
    base.update(over)
    return UniverseProvenance(**base)


def _run(M, ids=None, s=12, metric="sharpe", ledger=None, prov=None):
    n_obs, n_cand = M.shape
    ids = [f"c{i}" for i in range(n_cand)] if ids is None else ids
    return probability_of_backtest_overfitting(
        returns_matrix=M, n_obs=n_obs, n_candidates=n_cand, candidate_ids=ids, s_blocks=s,
        selection_metric=metric, universe_provenance=prov or _prov(ids), ledger_result=ledger or _ledger(ids),
    )


def _golden_matrix(g):
    gen = g["generation"]
    rng = np.random.default_rng(20260817)
    assert gen["rng"] == "np.random.default_rng(20260817)"
    return rng.standard_normal((gen["n_obs"], gen["n_candidates"])) * gen["sigma_per_period"], gen


def test_golden_file_sha256_and_analytic_constants():
    """golden sha256 防改；解析常數對照（E[maxSR] 三點、C(S,S/2)、MinBTL 手算／不變式）。"""
    g = _golden()
    for n, v in g["cases"]["expected_max_sharpe_factor"]["values"].items():
        assert expected_max_sharpe_factor(int(n)) == pytest.approx(v, abs=g["cases"]["expected_max_sharpe_factor"]["atol"])
    for s, v in g["cases"]["cscv_path_count"]["values"].items():
        assert cscv_path_count(int(s)) == v == math.comb(int(s), int(s) // 2)
    mb = g["cases"]["min_btl"]
    assert min_btl_years_upper_bound(n_trials=100, target_sharpe=1.0) == pytest.approx(mb["upper_bound_100_sr1"], abs=1e-12)
    t = mb["budget_at_real_kline_years"]["t_years"]
    for key, sr in (("sr_1.5", 1.5), ("sr_1.0", 1.0), ("sr_2.0", 2.0), ("sr_2.5", 2.5)):
        b = max_trials_budget(t_years=t, target_sharpe=sr)
        assert b == mb["budget_at_real_kline_years"][key]
        assert min_btl_years_upper_bound(n_trials=b, target_sharpe=sr) <= t < min_btl_years_upper_bound(n_trials=b + 1, target_sharpe=sr)


def test_golden_noise_band():
    """① A1-2 全噪音：default_rng(20260817).standard_normal((1200,50))*0.01、S=12 ⇒ 0.30<=pbo<=0.70（主委實跑 0.6483）。"""
    g = _golden()
    M, gen = _golden_matrix(g)
    got = _run(M, s=gen["s_blocks"], metric=gen["selection_metric"])
    lo, hi = g["cases"]["pbo"]["noise"]["band"]
    assert got.status == "ok" and got.n_paths_used == 924 and got.n_paths == 924
    assert lo <= got.value <= hi, got.value
    assert got.value == pytest.approx(g["cases"]["pbo"]["noise"]["observed"]["default_rng_TN"], abs=5e-5)
    assert got.universe_scope == "ledger_recorded_only"


def test_golden_alpha_detectable():
    """② A1-1：候選 0 加 mu=sigma*0.15（測試內重算並斷言等於 golden，atol=1e-18）⇒ pbo<0.30。"""
    g = _golden()
    M, gen = _golden_matrix(g)
    mu = gen["sigma_per_period"] * 0.15
    assert mu == pytest.approx(g["cases"]["pbo"]["alpha_detectable"]["mu"], abs=1e-18)
    M2 = M.copy()
    M2[:, 0] += mu
    got = _run(M2, s=gen["s_blocks"])
    assert got.status == "ok" and got.value < 0.30, got.value


def test_golden_alpha_undetectable():
    """②b A1-1：mu = sigma*1.0/sqrt(resolve_periods_per_year('1h')) = 0.01/sqrt(8760)（重算 atol=1e-18）⇒ pbo>0.40。"""
    g = _golden()
    M, gen = _golden_matrix(g)
    mu = gen["sigma_per_period"] * 1.0 / math.sqrt(resolve_periods_per_year("1h"))
    assert resolve_periods_per_year("1h") == 8760
    assert mu == pytest.approx(g["cases"]["pbo"]["alpha_undetectable"]["mu"], abs=1e-18)
    M2 = M.copy()
    M2[:, 0] += mu
    got = _run(M2, s=gen["s_blocks"])
    assert got.status == "ok" and got.value > 0.40, got.value


def test_vectorized_sharpe_matches_compute_sharpe():
    """`_metrics_columns("sharpe")` 逐位＝`compute_sharpe(col, periods_per_year=1).value_per_period`（含退化 NaN）。"""
    rng = np.random.default_rng(3)
    sub = rng.standard_normal((80, 9)) * 0.02
    sub[:, 3] = 0.5  # 常數（二進位可精確表示 ⇒ std 恰 0）⇒ NaN
    sub[5, 4] = np.nan  # 含 NaN ⇒ NaN
    sub[:, 7] = 0.01  # B4 review N5：浮點非精確常數（std≈1e-18 非 0）⇒ 兩邊皆巨大有限值，須**逐位相同**
    sub[:, 8] = 0.01 + np.linspace(0, 1e-9, 80)  # 微擾近常數
    got = _metrics_columns(sub, "sharpe")
    for j in range(9):
        ref = compute_sharpe(sub[:, j], periods_per_year=1).value_per_period
        if math.isnan(ref):
            assert math.isnan(got[j])
        else:
            assert got[j] == ref, (j, got[j], ref)  # 逐位相等（同一 1-D 縮減）
    assert math.isnan(_metrics_columns(sub[:1], "sharpe")[0])  # n<2 ⇒ NaN
    assert _metrics_columns(sub, "mean_return")[0] == pytest.approx(np.mean(sub[:, 0]))
    # 🔴 具名殘留 G1-R11：浮點非精確常數欄 compute_sharpe 不視為退化（回巨大有限 SR）——B1 語意，本批不動
    assert math.isfinite(got[7]) and abs(got[7]) > 1e6


def test_transpose_raises_and_short_t_ok():
    """③ 轉置 raise；合法 T<N（n_obs=50, n_candidates=1200，shape 相符）不 raise。"""
    rng = np.random.default_rng(1)
    M = rng.standard_normal((100, 8)) * 0.01
    ids = [f"c{i}" for i in range(8)]
    with pytest.raises(ValueError):
        probability_of_backtest_overfitting(
            returns_matrix=M.T, n_obs=100, n_candidates=8, candidate_ids=ids, s_blocks=4,
            selection_metric="sharpe", universe_provenance=_prov(ids), ledger_result=_ledger(ids),
        )
    # len(candidate_ids)!=n_candidates：守衛先跑（count 三方不等 ⇒ unverifiable，不到 ValueError）——具名記錄，非 raise
    got = _run(M, ids=ids[:7])
    assert got.status != "ok" and got.reason == "universe_provenance_unverifiable"
    Mw = rng.standard_normal((50, 1200)) * 0.01
    got = _run(Mw, s=4)
    assert isinstance(got, PBOResult) and got.status == "ok"


def test_all_tie_gives_r_half_and_zero_logit():
    """④ 全平手（mean_return，所有候選同值）⇒ 每 path r==0.5、ω==0 ⇒ logits 皆 0、PBO=0（ω<0 為假）。"""
    M = np.tile(np.linspace(-0.01, 0.01, 60)[:, None], (1, 4)) + 0.0  # 四欄完全相同
    got = _run(M, s=4, metric="mean_return")
    assert got.status == "ok"
    assert got.logits_min == got.logits_max == 0.0
    assert got.value == 0.0


def test_double_champion_takes_smallest_index_hand_computed():
    """④b 雙冠 ⇒ 最小原始索引（B4 review N4 重寫；手算可證偽）。mean_return、S=2、4 候選：
    path 0（IS=前半）：欄 1／3 IS 平手最佳 ⇒ champion=欄 1；OOS=後半 欄 1 名次 2/4 ⇒ ω=ln((2/5)/(3/5))=ln(2/3)
    （誤取欄 3 ⇒ 名次 4/4 ⇒ ω=ln 4，本測即紅）；
    path 1（IS=後半）：欄 3 唯一最佳；OOS=前半 欄 3 與欄 1 平手名次 3.5 ⇒ r=0.7 ⇒ ω=ln(7/3)。"""
    n = 40
    h = n // 2
    M = np.zeros((n, 4))
    M[:h] = [0.001, 0.003, 0.002, 0.003]  # 前半：欄 1、3 平手最佳
    M[h:] = [0.001, 0.002, 0.003, 0.004]  # 後半：欄 3 最佳、欄 1 第 2
    got = _run(M, s=2, metric="mean_return")
    assert got.status == "ok" and got.n_paths_used == 2 and got.n_path_exclusions == 0
    expected = sorted([math.log(2 / 3), math.log(0.7 / 0.3)])
    assert got.logits_min == pytest.approx(expected[0], abs=1e-12)
    assert got.logits_max == pytest.approx(expected[1], abs=1e-12)
    assert got.value == 0.5  # 一條 ω<0、一條 ω>0


def test_denominator_is_path_valid_count_plus_one():
    """④c 5 vs 3 有效候選 ⇒ 分母 6 與 4（兩次真實 PBO 呼叫；champion 恆最高名次 ⇒ ω=ln(n/1)）。"""
    n = 40
    M5 = np.tile(np.array([0.001, 0.002, 0.003, 0.004, 0.005]), (n, 1)) + np.linspace(0, 1e-7, n)[:, None]
    got5 = _run(M5, s=2, metric="mean_return")
    assert got5.status == "ok"
    assert got5.logits_min == pytest.approx(math.log((5 / 6) / (1 / 6)), abs=1e-12)  # rank 5/(5+1)
    got3 = _run(M5[:, :3].copy(), s=2, metric="mean_return")
    assert got3.logits_min == pytest.approx(math.log((3 / 4) / (1 / 4)), abs=1e-12)  # rank 3/(3+1)
    assert got5.logits_min != got3.logits_min  # 同「最高名次」不同分母 ⇒ ω 不同


def test_champion_degenerate_in_oos_is_skipped_not_indexerror():
    """④d A1-15：3 候選、IS champion＝原始索引 2、該候選 OOS 切片為常數 ⇒ path 計入 n_paths_skipped、不 raise、分母＝n_paths_used；
    B4 review N3：n_path_exclusions 每候選每 path 至多 +1（本 fixture 手算＝2：path 0 之 OOS 欄 2 非有限 +1；path 1 之 IS 欄 2 非有限 +1）。"""
    n = 40
    M = np.zeros((n, 3))
    rng = np.random.default_rng(9)
    M[:, 0] = rng.standard_normal(n) * 0.01
    M[:, 1] = rng.standard_normal(n) * 0.01
    # 欄 2：前半 IS 極佳（大正均值有變異），後半常數（OOS 之 sharpe 退化）
    M[: n // 2, 2] = 0.05 + rng.standard_normal(n // 2) * 0.001
    M[n // 2 :, 2] = 0.0
    got = _run(M, s=2, metric="sharpe")  # 2 paths：IS=前半（champ=2，OOS 常數 ⇒ skip）；IS=後半（欄 2 常數 ⇒ IS 排除，母體 2 欄）
    assert got.status == "ok"
    assert got.n_paths_skipped == 1 and got.n_paths_used == 1
    assert got.n_path_exclusions == 2
    assert got.n_paths_used + got.n_paths_skipped == got.n_paths == 2


def test_non_champion_oos_degenerate_skips_path_keeps_denominator():
    """B4 review N2：名次母體＝path_valid、分母＝len(path_valid)+1；**非** champion 之候選 OOS 非有限 ⇒ 該 path 跳過（不縮小母體取名次）。"""
    n = 40
    h = n // 2
    M = np.zeros((n, 3))
    M[:h] = [0.001, 0.003, 0.002]  # 前半：欄 1 最佳（IS of path 0）
    M[h:] = [0.001, 0.002, 0.003]  # 後半（OOS of path 0）
    M[:, 0] += np.linspace(0, 1e-7, n)  # 讓 sharpe 有變異
    M[:, 1] += np.linspace(0, 1e-7, n)
    M[:h, 2] += np.linspace(0, 1e-7, h)  # 欄 2 前半有變異（IS of path 0 有效）
    M[h:, 2] = 0.5  # 欄 2 後半恰常數（0.5 二進位精確 ⇒ std 恰 0）⇒ path 0 之 OOS sharpe 退化（非 champion）；path 1 之 IS 退化（排除）
    got = _run(M, s=2, metric="sharpe")
    # path 0：欄 2 OOS 退化 ⇒ 整條 path skip；path 1：IS=後半 欄 2 常數 ⇒ IS 排除，母體={0,1}
    assert got.n_paths_skipped == 1
    assert got.n_paths_used == 1
    assert got.n_path_exclusions == 2
    # path 1 champion＝欄 1（IS 後半 0.002 > 0.001）；OOS 前半 欄 1 (0.003) > 欄 0 (0.001) ⇒ rank 2/(2+1)
    assert got.logits_min == pytest.approx(math.log((2 / 3) / (1 / 3)), abs=1e-9)


def test_rank_uses_compressed_position_not_original_index():
    """④d′（§V-14 可證偽鎖）：欄 0 全 NaN（矩陣層剔除）⇒ valid_cols=[1,2,3]；IS champion＝原始索引 3（壓縮位置 2）。
    以原始索引索引長度 3 之名次陣列 ⇒ IndexError／錯值即紅；正確實作 ⇒ champion OOS 名次可由 mean_return 手算對照。"""
    n = 40
    M = np.zeros((n, 4))
    M[:, 0] = np.nan
    M[:, 1] = 0.001
    M[:, 2] = 0.002
    M[:, 3] = 0.003  # 全程最佳 ⇒ 每 path IS champion＝原始索引 3；OOS 名次＝3（最高，3 個有效候選）
    M[:, 1:] += np.linspace(-1e-6, 1e-6, n)[:, None]  # 打破常數（mean_return 不受影響之排序）
    got = _run(M, s=2, metric="mean_return")
    assert got.status == "ok" and got.n_candidates_invalid == 1 and got.n_paths_used == 2
    expected_omega = math.log((3 / 4) / (1 - 3 / 4))  # rank 3 / (3+1)
    assert got.logits_min == pytest.approx(expected_omega, abs=1e-12)
    assert got.logits_max == pytest.approx(expected_omega, abs=1e-12)
    assert got.value == 0.0


def test_nan_candidate_is_invalid_and_denominator_shrinks():
    """⑤ 5 候選含 1 NaN 欄 ⇒ n_candidates_invalid==1、分母 4（用 mean_return 平手構造證分母）。"""
    n = 40
    rng = np.random.default_rng(11)
    M = rng.standard_normal((n, 5)) * 0.01
    M[3, 4] = np.nan
    got = _run(M, s=2, metric="mean_return")
    assert got.n_candidates_invalid == 1
    assert got.status == "ok"
    # 分母 4 ⇒ 名次 r ∈ {1/5,...,4/5}：ω 只可能取 ln(r/(1-r)) 四值之一
    allowed = {round(math.log(k / 5 / (1 - k / 5)), 9) for k in (1, 2, 3, 4)}
    assert round(got.logits_min, 9) in allowed and round(got.logits_max, 9) in allowed


def test_single_valid_candidate_is_insufficient():
    """⑥ 有效候選 1 ⇒ status!=ok 且 isnan（insufficient_candidates）。"""
    n = 40
    M = np.random.default_rng(2).standard_normal((n, 3)) * 0.01
    M[0, 1] = np.nan
    M[0, 2] = np.inf
    got = _run(M, s=2)
    assert got.status != "ok" and math.isnan(got.value)
    assert got.reason == "insufficient_candidates" and got.n_candidates_invalid == 2
    assert got.universe_scope == "ledger_recorded_only"  # 守衛 ok 仍回填


def test_constant_slices_produce_exclusions_and_all_degenerate():
    """⑦ 常數切片 fixture ⇒ n_path_exclusions>0／n_paths_skipped；⑧ 全退化 ⇒ all_paths_degenerate。"""
    n = 40
    M = np.zeros((n, 3))  # 全常數 ⇒ 每 path 每候選 sharpe 退化 ⇒ 全 path 跳過
    got = _run(M, s=2, metric="sharpe")
    assert got.status == "not_computed" and got.reason == "all_paths_degenerate"
    assert got.n_paths_used == 0 and got.n_paths_skipped == 2 and got.n_path_exclusions > 0
    assert math.isnan(got.value) and got.universe_scope == "ledger_recorded_only"


def test_universe_scope_none_when_guard_not_ok():
    """⑨ A1-4：守衛 ok ⇒ universe_scope=='ledger_recorded_only'；守衛非 ok ⇒ None。"""
    rng = np.random.default_rng(4)
    M = rng.standard_normal((40, 4)) * 0.01
    ids = [f"c{i}" for i in range(4)]
    ok = _run(M, ids=ids, s=2)
    assert ok.universe_scope == "ledger_recorded_only"
    bad = _run(M, ids=ids, s=2, prov=_prov(ids, selection_free=False))
    assert bad.status != "ok" and bad.universe_scope is None and math.isnan(bad.value)


def test_selection_metric_enum_enforced():
    M = np.random.default_rng(6).standard_normal((40, 3)) * 0.01
    with pytest.raises(ValueError):
        _run(M, s=2, metric="sortino")
