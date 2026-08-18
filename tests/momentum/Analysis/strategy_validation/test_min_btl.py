"""Task 3.1 驗證：MinBTL 上界／試驗預算／資格三態（含 A1-9 保守性統計 oracle）。

mutation §V-2（`ln(n)` 改 `n`）⇒ ①③ 轉紅；§V-3（`floor` 改 `round`）⇒ ②③ 轉紅。
"""

import math

import numpy as np
import pytest
from scipy.stats import norm

from momentum.Analysis.strategy_validation.ledger import LedgerReadResult
from momentum.Analysis.strategy_validation.min_btl import (
    EligibilityResult,
    InvalidValidationArgument,
    assess_eligibility,
    max_trials_budget,
    min_btl_years_upper_bound,
)

_T_100 = 2.3232876712328765  # §A FACT-RECEIPT 真實 kline 年數（1h=20352 bars）


def _ledger(n_for_dsr=100, status="ok", reason=""):
    return LedgerReadResult(
        n_candidates_considered=n_for_dsr,
        n_evaluated=n_for_dsr,
        n_valid_metrics=n_for_dsr,
        n_failed_or_pruned=0,
        n_rows_rejected=0,
        n_is_lower_bound=True,
        n_for_dsr=n_for_dsr,
        snapshot_hash="x",
        artifact_hashes=frozenset({"h"}),
        candidate_ids=frozenset(f"c{i}" for i in range(n_for_dsr)),
        n_semantics="unknown",
        valid_sharpe_values=(),
        status=status,
        reason=reason,
    )


def test_upper_bound_hand_value():
    """① (100, 1.0) = 2·ln(100) = 9.210340371976184。"""
    assert min_btl_years_upper_bound(n_trials=100, target_sharpe=1.0) == pytest.approx(
        9.210340371976184, abs=1e-12
    )


def test_budget_hand_values():
    """② 真實 T=2.3232876712328765：SR=1.5→13；1.0→3；2.0→104；2.5→1422（floor）。"""
    assert max_trials_budget(t_years=_T_100, target_sharpe=1.5) == 13
    assert max_trials_budget(t_years=_T_100, target_sharpe=1.0) == 3
    assert max_trials_budget(t_years=_T_100, target_sharpe=2.0) == 104
    assert max_trials_budget(t_years=_T_100, target_sharpe=2.5) == 1422


@pytest.mark.parametrize(
    "t_years, target_sharpe",
    [
        (0.5, 1.0), (1.0, 1.0), (2.0, 1.0), (5.0, 1.0), (9.0, 1.0),
        (0.5, 2.0), (1.5, 2.0), (3.0, 2.0), (2.3232876712328765, 1.5), (7.7, 0.8),
        (12.0, 0.5), (0.25, 3.0), (4.0, 1.25), (6.5, 0.9), (10.0, 1.1),
        (2.0, 2.5), (1.0, 3.0), (3.3, 1.7), (8.0, 0.75), (2.5, 2.2),
    ],
)
def test_bound_and_budget_are_inverse_pair(t_years, target_sharpe):
    """③ 20 組：`ub(budget) <= T < ub(budget+1)`（上界與預算互為反函式；floor 改 round 即紅）。"""
    budget = max_trials_budget(t_years=t_years, target_sharpe=target_sharpe)
    assert budget >= 1
    lo = min_btl_years_upper_bound(n_trials=budget, target_sharpe=target_sharpe)
    hi = min_btl_years_upper_bound(n_trials=budget + 1, target_sharpe=target_sharpe)
    assert lo <= t_years < hi


def test_n_equals_one_is_zero_and_invalid_arguments_raise():
    """④ N=1 ⇒ 0.0；N<1／SR<=0／T<=0 ⇒ InvalidValidationArgument（ValueError 子類）。"""
    assert min_btl_years_upper_bound(n_trials=1, target_sharpe=1.0) == 0.0
    assert min_btl_years_upper_bound(n_trials=1, target_sharpe=0.3) == 0.0
    with pytest.raises(InvalidValidationArgument):
        min_btl_years_upper_bound(n_trials=0, target_sharpe=1.0)
    with pytest.raises(InvalidValidationArgument):
        min_btl_years_upper_bound(n_trials=10, target_sharpe=0.0)
    with pytest.raises(InvalidValidationArgument):
        min_btl_years_upper_bound(n_trials=10, target_sharpe=-1.0)
    with pytest.raises(InvalidValidationArgument):
        max_trials_budget(t_years=0.0, target_sharpe=1.0)
    with pytest.raises(InvalidValidationArgument):
        max_trials_budget(t_years=-2.0, target_sharpe=1.0)
    with pytest.raises(InvalidValidationArgument):
        assess_eligibility(t_years=-1.0, ledger_result=_ledger(), target_sharpe=1.0)
    with pytest.raises(InvalidValidationArgument):
        assess_eligibility(t_years=1.0, ledger_result=_ledger(), target_sharpe=0.0)
    assert issubclass(InvalidValidationArgument, ValueError)


def test_c5_oracle_real_kline_years_100_trials_not_eligible():
    """⑤ C5 oracle：真實 T=2.32 年、N=100、SR*=1.0 ⇒ eligible False 且 trials_used > trials_budget。"""
    got = assess_eligibility(t_years=_T_100, ledger_result=_ledger(100), target_sharpe=1.0)
    assert isinstance(got, EligibilityResult)
    assert got.eligible is False
    assert got.trials_used == 100
    assert got.trials_budget == 3
    assert got.trials_used > got.trials_budget
    assert got.required_years_upper_bound == pytest.approx(9.210340371976184, abs=1e-12)
    assert got.available_years == _T_100
    assert got.n_source == "ledger"
    assert got.status == "ok" and got.reason == ""


def test_ledger_not_ok_gives_eligible_none_and_passes_status():
    """⑥ ledger status≠ok ⇒ eligible None、status/reason 傳遞、trials_used None（禁 N=1 頂替）。"""
    got = assess_eligibility(
        t_years=_T_100, ledger_result=_ledger(0, status="unavailable", reason="n_unknown"), target_sharpe=1.0
    )
    assert got.eligible is None
    assert got.status == "unavailable"
    assert got.reason == "n_unknown"
    assert got.trials_used is None
    assert got.required_years_upper_bound is None
    assert got.n_source == "ledger_unavailable"
    assert got.trials_budget == 3  # 預算只依 T／SR，仍可算


def test_large_n_is_finite():
    """⑦ N=10**6 有限。"""
    v = min_btl_years_upper_bound(n_trials=10**6, target_sharpe=1.0)
    assert math.isfinite(v)
    assert v == pytest.approx(2 * math.log(10**6), abs=1e-9)


def test_eligible_true_when_data_long_enough():
    got = assess_eligibility(t_years=10.0, ledger_result=_ledger(100), target_sharpe=1.0)
    assert got.eligible is True


def test_exp_overflow_argument_raises_not_capped():
    """⑧ A1-5：t_years=1500, SR=1.0 ⇒ x=750 > 700 ⇒ raise（禁 cap 常數）。"""
    with pytest.raises(InvalidValidationArgument):
        max_trials_budget(t_years=1500, target_sharpe=1.0)
    with pytest.raises(InvalidValidationArgument):
        assess_eligibility(t_years=1500, ledger_result=_ledger(), target_sharpe=1.0)


def test_eligibility_result_fields_are_subset_of_contract_eligibility_keys():
    """A1-5 第 3 點：欄位 ⊆ 契約 eligibility_keys ∪ {status, reason}（禁自創 budget_capped）。"""
    from dataclasses import fields

    from momentum.Analysis.strategy_validation.contract import load_strategy_validation_contract

    keys = set(load_strategy_validation_contract()["eligibility_keys"]) | {"status", "reason"}
    assert {f.name for f in fields(EligibilityResult)} <= keys


def test_minbtl_upper_bound_is_conservative_statistical_oracle():
    """⑨ A1-9：T=ub(N=100, SR*=1.0)=9.21 年、日頻 3362 obs、20 seed × 100 條 iid 噪音策略 ⇒
    mean(max annualized SR) <= 1.0 且與解析值 0.833943 rtol<0.05。🔴 只斷言 20 seed 平均（per-seed 上界不成立）。"""
    n_trials, target_sr, ppy = 100, 1.0, 365
    t_years = min_btl_years_upper_bound(n_trials=n_trials, target_sharpe=target_sr)
    n_obs = int(round(t_years * ppy))
    assert n_obs == 3362
    maxima = []
    for k in range(20):
        rng = np.random.default_rng(20260817 + k)
        m = rng.standard_normal((n_obs, n_trials)) * 0.01
        sr_pp = m.mean(axis=0) / m.std(axis=0, ddof=1)
        maxima.append(float(np.max(sr_pp) * math.sqrt(ppy)))
    mean_max = float(np.mean(maxima))
    g = 0.5772156649015329
    analytic = (
        ((1 - g) * norm.ppf(1 - 1 / n_trials) + g * norm.ppf(1 - 1 / (n_trials * math.e)))
        / math.sqrt(n_obs - 1)
        * math.sqrt(ppy)
    )
    assert analytic == pytest.approx(0.833943, abs=1e-6)
    assert mean_max <= target_sr
    assert mean_max == pytest.approx(analytic, rel=0.05)
