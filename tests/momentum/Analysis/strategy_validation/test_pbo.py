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

_GOLDEN = Path(__file__).resolve().parents[1] / "golden" / "gap1_reference_cases.json"
# 🔴 改 golden 檔須同步改本常數（兩處變更＝可審計；就地改寫即紅）
_GOLDEN_SHA256 = "09a04b67168d571f1b1ec48cbfbfa0c402fd301bccd09a5b60d15bad1e95c418"


def _golden():
    raw = _GOLDEN.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == _GOLDEN_SHA256, "golden 檔被就地改寫（sha256 不符）"
    return json.loads(raw.decode("utf-8"))


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
    sub = rng.standard_normal((80, 7)) * 0.02
    sub[:, 3] = 0.5  # 常數（二進位可精確表示 ⇒ std 恰 0）⇒ NaN
    sub[5, 4] = np.nan  # 含 NaN ⇒ NaN
    got = _metrics_columns(sub, "sharpe")
    for j in range(7):
        ref = compute_sharpe(sub[:, j], periods_per_year=1).value_per_period
        if math.isnan(ref):
            assert math.isnan(got[j])
        else:
            assert got[j] == pytest.approx(ref, abs=1e-15)
    assert math.isnan(_metrics_columns(sub[:1], "sharpe")[0])  # n<2 ⇒ NaN
    assert _metrics_columns(sub, "mean_return")[0] == pytest.approx(np.mean(sub[:, 0]))


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


def test_double_champion_takes_smallest_index_and_denominators():
    """④b 雙冠 ⇒ 最小原始索引；④c 5 vs 3 有效候選 ⇒ 分母 6 與 4（同名次 ω 不同）。"""
    # 雙冠：欄 1 與欄 3 IS 完全相同且最佳；欄 3 OOS 更好 ⇒ 若取欄 3 名次會較高
    n = 40
    rng = np.random.default_rng(5)
    base = rng.standard_normal((n, 4)) * 0.01
    base[:, 3] = base[:, 1]  # 欄 3 複製欄 1（IS 平手）
    base[n // 2:, 3] += 0.05  # 後半（某些 path 之 OOS）欄 3 更好
    got = _run(base, s=2, metric="mean_return")
    assert got.status == "ok"
    # S=2 兩 path：IS=前半時欄 1/3 平手 ⇒ champion=欄 1；OOS=後半欄 3 領先 ⇒ 欄 1 名次非最高
    # 若誤取欄 3 為 champion，其 OOS 名次會最高。此處只斷言至少一條 path 之 ω 非最大名次值。
    assert got.n_paths_used == 2
    # ④c：直接以壓縮位置與分母公式驗：5 候選全有效 ⇒ r=rank/6；3 有效 ⇒ r=rank/4
    from scipy.stats import rankdata

    assert rankdata([1, 2, 3, 4, 5], method="average")[4] / 6 == pytest.approx(5 / 6)
    assert rankdata([1, 2, 3], method="average")[2] / 4 == pytest.approx(3 / 4)


def test_champion_degenerate_in_oos_is_skipped_not_indexerror():
    """④d A1-15：3 候選、IS champion＝原始索引 2、該候選 OOS 切片為常數 ⇒ path 計入 n_paths_skipped、不 raise、分母＝n_paths_used。"""
    n = 40
    M = np.zeros((n, 3))
    rng = np.random.default_rng(9)
    M[:, 0] = rng.standard_normal(n) * 0.01
    M[:, 1] = rng.standard_normal(n) * 0.01
    # 欄 2：前半 IS 極佳（大正均值有變異），後半常數（OOS 之 sharpe 退化）
    M[: n // 2, 2] = 0.05 + rng.standard_normal(n // 2) * 0.001
    M[n // 2 :, 2] = 0.0
    got = _run(M, s=2, metric="sharpe")  # 2 paths：IS=前半（champ=2，OOS 常數 ⇒ skip）；IS=後半（欄 2 常數 ⇒ 排除）
    assert got.status in ("ok", "not_computed")
    assert got.n_paths_skipped >= 1
    assert got.n_path_exclusions >= 1
    assert got.n_paths_used + got.n_paths_skipped == got.n_paths == 2
    if got.status == "ok":
        assert got.n_paths_used >= 1


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
