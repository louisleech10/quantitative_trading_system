"""Task 3.2 驗證：DSR 全式、N=1 退化為 PSR、E[maxSR] 三點、單調性、單位不變性、輸入語意鎖、snapshot 綁定。

mutation §V-1（刪 γ 項）⇒ ②轉紅；§V-11（分母改跨 trial 變異數）⇒ ①轉紅；§V-12（skew/kurt 用年化 SR）⇒ ⑦轉紅；
§V-10（Mertens 係數）⇒ ①轉紅（分母唯一定義處在 sharpe.py）。
"""

import math

import numpy as np
import pytest
from scipy import stats as sps
from scipy.stats import norm

from momentum.Analysis.strategy_validation.deflated_sharpe import (
    DSRResult,
    deflated_sharpe,
    expected_max_sharpe_factor,
)
from momentum.Analysis.strategy_validation.ledger import LedgerReadResult
from momentum.Analysis.strategy_validation.min_btl import InvalidValidationArgument
from momentum.Analysis.strategy_validation.returns_contract import PeriodReturns

_HASH = "a" * 64


def _returns(n=600, seed=7, mean=0.0015, sd=0.01):
    rng = np.random.default_rng(seed)
    return rng.standard_normal(n) * sd + mean


def _symmetric_returns(n_half=300, seed=11, mean=0.001, sd=0.01):
    """繞均值對稱 ⇒ 樣本 skew 恰為 0（數值 ~1e-16）。"""
    rng = np.random.default_rng(seed)
    d = np.abs(rng.standard_normal(n_half)) * sd
    return np.concatenate([mean + d, mean - d])


def _pr(values, *, ppy=8760, status="ok", reason="", t_semantics="trade_level", src="resolved", h=_HASH):
    return PeriodReturns(
        values=np.asarray(values, dtype=float),
        t_semantics=t_semantics,
        n_obs=int(len(values)),
        periods_per_year=ppy,
        annualization_source=src,
        source_artifact_hash=h,
        status=status,
        reason=reason,
    )


def _kurt3_returns(n_half=20, mean=0.002, s=0.01):
    """恰 skew=0、Pearson kurt=3 之序列（B3 review M3）：`m±s` 各 n_half 個＋ 4·n_half 個 `m`
    ⇒ population m4/m2² = N/(2·n_half) = 3、skew = 0；均值位移不改中央矩。"""
    d = np.concatenate([np.full(n_half, s), np.full(n_half, -s), np.zeros(4 * n_half)])
    return mean + d


def _ledger(n_for_dsr=10, sharpes=(0.01, 0.02, 0.03), hashes=(_HASH,), n_valid=None, status="ok", reason=""):
    """typed 直構帳本；不變式 `n_evaluated == n_valid_metrics + n_failed_or_pruned` 由構造成立（B3 review M4）。"""
    n_valid = len(sharpes) if n_valid is None else n_valid
    n_evaluated = max(n_valid, n_for_dsr)
    n_failed = n_evaluated - n_valid
    assert n_evaluated == n_valid + n_failed and n_failed >= 0
    return LedgerReadResult(
        n_candidates_considered=n_for_dsr,
        n_evaluated=n_evaluated,
        n_valid_metrics=n_valid,
        n_failed_or_pruned=n_failed,
        n_rows_rejected=0,
        n_is_lower_bound=True,
        n_for_dsr=n_for_dsr,
        snapshot_hash="s",
        artifact_hashes=frozenset(hashes),
        candidate_ids=frozenset(f"c{i}" for i in range(n_for_dsr)),
        n_semantics="unknown",
        valid_sharpe_values=tuple(sharpes),
        status=status,
        reason=reason,
    )


def _psr_analytic(values):
    """PSR 解析值（測試側獨立計算：Mertens 分母以 scipy 矩重算，不引用 sharpe.py 之變異數）。"""
    v = np.asarray(values, dtype=float)
    t = v.size
    sr = v.mean() / v.std(ddof=1)
    g3 = float(sps.skew(v))
    g4 = float(sps.kurtosis(v, fisher=False))
    return float(norm.cdf(sr * math.sqrt(t - 1) / math.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr**2)))


def test_n_one_equals_psr_closed_form_with_exact_skew0_kurt3():
    """① 字面版（B3 review M3）：序列**恰** skew=0、Pearson kurt=3（先斷言矩），N=1 ⇒ DSR == 閉式 PSR
    `Φ(SR·√(T-1)/√(1+SR²/2))`（atol 1e-10）——閉式不含任何 sharpe.py 之量。"""
    values = _kurt3_returns()
    assert float(sps.skew(values)) == pytest.approx(0.0, abs=1e-12)
    assert float(sps.kurtosis(values, fisher=False)) == pytest.approx(3.0, abs=1e-12)
    t = values.size
    sr = values.mean() / values.std(ddof=1)
    closed_form = float(norm.cdf(sr * math.sqrt(t - 1) / math.sqrt(1.0 + sr**2 / 2.0)))
    for vs in ("explicit", "ledger_cross_trial"):
        got = deflated_sharpe(period_returns=_pr(values), n_trials=1, variance_source=vs, n_semantics="exhaustive_grid")
        assert got.status == "ok" and got.sr0 == 0.0
        assert got.value == pytest.approx(closed_form, abs=1e-10)


def test_n_one_equals_psr_analytic():
    """①（第二鎖，更強不變量）N=1 ⇒ SR0=0 ⇒ DSR == PSR（atol 1e-10；skew 由對稱構造恰 0，kurt 取**樣本值**並在測試側獨立重算）。"""
    values = _symmetric_returns()
    assert abs(float(sps.skew(values))) < 1e-12
    expected = _psr_analytic(values)
    for vs in ("explicit", "ledger_cross_trial"):
        got = deflated_sharpe(period_returns=_pr(values), n_trials=1, variance_source=vs, n_semantics="exhaustive_grid")
        assert got.status == "ok"
        assert got.sr0 == 0.0
        assert got.value == pytest.approx(expected, abs=1e-10)
    # ledger 路徑：n_for_dsr=1 但 valid_sharpe_values 有 2 值（同 candidate 兩 attempt）——分母若誤用跨 trial 變異數即紅
    got = deflated_sharpe(
        period_returns=_pr(values), ledger_result=_ledger(1, sharpes=(0.05, 0.9)),
        variance_source="ledger_cross_trial", n_semantics="exhaustive_grid",
    )
    assert got.n_trials_used == 1
    assert got.value == pytest.approx(expected, abs=1e-10)


@pytest.mark.parametrize("n, expected", [(10, 1.5746), (100, 2.5306), (1000, 3.2551)])
def test_expected_max_sharpe_factor_three_points(n, expected):
    """② E[maxSR]/√V 三點對照（atol 1e-4）；並經 deflated_sharpe 以 V=1 回讀 sr0。"""
    assert expected_max_sharpe_factor(n) == pytest.approx(expected, abs=1e-4)
    got = deflated_sharpe(
        period_returns=_pr(_returns()), n_trials=n, variance_source="explicit",
        cross_trial_sr_variance=1.0, n_semantics="exhaustive_grid",
    )
    assert got.status == "ok"
    assert got.sr0 == pytest.approx(expected, abs=1e-4)


def test_dsr_monotone_non_increasing_in_n():
    """③ N 遞增（10 點）⇒ DSR 單調不增。"""
    pr = _pr(_returns())
    vals = [
        deflated_sharpe(
            period_returns=pr, n_trials=n, variance_source="explicit",
            cross_trial_sr_variance=0.0004, n_semantics="exhaustive_grid",
        ).value
        for n in (1, 2, 3, 5, 8, 13, 21, 50, 100, 1000)
    ]
    assert all(math.isfinite(v) for v in vals)
    assert all(a >= b for a, b in zip(vals, vals[1:]))
    assert vals[0] > vals[-1]


@pytest.mark.parametrize(
    "kw",
    [
        dict(status="not_applicable", reason="t_semantics_inflates_significance", t_semantics="bar_count"),
        dict(status="unavailable", reason="annualization_unresolved", src="default_730"),
    ],
)
def test_period_returns_not_ok_propagates(kw):
    """④ bar_count／default_730 ⇒ status≠ok、value NaN、reason 傳遞。"""
    got = deflated_sharpe(
        period_returns=_pr(_returns(), **kw), n_trials=5, variance_source="explicit",
        cross_trial_sr_variance=0.01, n_semantics="exhaustive_grid",
    )
    assert got.status != "ok"
    assert math.isnan(got.value)
    assert got.reason == kw["reason"]
    assert got.status == kw["status"]


def test_ledger_cross_trial_with_fewer_than_two_values_is_unavailable():
    """⑤ ledger_cross_trial 且 len(valid_sharpe_values)<2 ⇒ cross_trial_variance_unavailable。"""
    got = deflated_sharpe(
        period_returns=_pr(_returns()), ledger_result=_ledger(10, sharpes=(0.02,)),
        variance_source="ledger_cross_trial", n_semantics="exhaustive_grid",
    )
    assert got.status != "ok"
    assert got.reason == "cross_trial_variance_unavailable"
    assert math.isnan(got.value)


def test_ledger_and_n_trials_are_mutually_exclusive_and_snapshot_binding():
    """⑤b 同傳／皆缺 ⇒ raise；artifact hash 不在帳本 ⇒ ledger_snapshot_mismatch；valid_sharpe 長度 > n_valid_metrics 亦然。"""
    pr = _pr(_returns())
    with pytest.raises(ValueError):
        deflated_sharpe(period_returns=pr, ledger_result=_ledger(), n_trials=3, variance_source="explicit", n_semantics="unknown")
    with pytest.raises(ValueError):
        deflated_sharpe(period_returns=pr, variance_source="explicit", n_semantics="unknown")
    got = deflated_sharpe(
        period_returns=_pr(_returns(), h="b" * 64), ledger_result=_ledger(),
        variance_source="ledger_cross_trial", n_semantics="exhaustive_grid",
    )
    assert got.reason == "ledger_snapshot_mismatch" and got.status != "ok" and math.isnan(got.value)
    got = deflated_sharpe(
        period_returns=pr, ledger_result=_ledger(sharpes=(0.1, 0.2, 0.3), n_valid=2),
        variance_source="ledger_cross_trial", n_semantics="exhaustive_grid",
    )
    assert got.reason == "ledger_snapshot_mismatch"


def test_explicit_variance_none_vs_degenerate_are_distinct_reasons():
    """⑤c A1-12：explicit 且 None ⇒ cross_trial_variance_unavailable；0.0／inf ⇒ degenerate_returns。"""
    pr = _pr(_returns())
    got = deflated_sharpe(period_returns=pr, n_trials=10, variance_source="explicit", n_semantics="exhaustive_grid")
    assert got.reason == "cross_trial_variance_unavailable" and got.status != "ok"
    for bad in (0.0, float("inf"), -0.5, float("nan")):
        got = deflated_sharpe(
            period_returns=pr, n_trials=10, variance_source="explicit",
            cross_trial_sr_variance=bad, n_semantics="exhaustive_grid",
        )
        assert got.reason == "degenerate_returns" and got.status != "ok"


def test_both_variance_sources_agree_when_variance_equal():
    """⑥ 兩 variance_source 皆有案例：ledger 樣本變異數 == explicit 同值 ⇒ 同 DSR。"""
    pr = _pr(_returns())
    sharpes = (0.010, 0.020, 0.030, 0.045)
    import statistics

    v = statistics.variance(sharpes)
    a = deflated_sharpe(period_returns=pr, ledger_result=_ledger(4, sharpes=sharpes), variance_source="ledger_cross_trial", n_semantics="exhaustive_grid")
    b = deflated_sharpe(period_returns=pr, n_trials=4, variance_source="explicit", cross_trial_sr_variance=v, n_semantics="exhaustive_grid")
    assert a.status == b.status == "ok"
    assert a.value == pytest.approx(b.value, abs=1e-12)
    assert a.sr0 == pytest.approx(b.sr0, abs=1e-12)
    assert a.variance_source == "ledger_cross_trial" and b.variance_source == "explicit"


@pytest.mark.parametrize("ppy_pair", [(1, 730), (730, 8760), (1, 8760)])
def test_unit_invariance_across_periods_per_year(ppy_pair):
    """⑦ 同一序列 periods_per_year∈{1,730,8760} ⇒ DSR 不變（atol 1e-12）；把年化 SR 代入矩公式即紅。"""
    values = _returns()
    outs = [
        deflated_sharpe(
            period_returns=_pr(values, ppy=p), n_trials=20, variance_source="explicit",
            cross_trial_sr_variance=0.0004, n_semantics="exhaustive_grid",
        )
        for p in ppy_pair
    ]
    assert outs[0].value == pytest.approx(outs[1].value, abs=1e-12)
    assert outs[0].sr_obs_per_period == pytest.approx(outs[1].sr_obs_per_period, abs=1e-12)


def test_adaptive_search_marks_independence_unverified():
    """⑧ adaptive_search ⇒ n_independence unverified（不做 effective-N 換算，DSR 值不變）。"""
    pr = _pr(_returns())
    a = deflated_sharpe(period_returns=pr, n_trials=10, variance_source="explicit", cross_trial_sr_variance=0.0004, n_semantics="adaptive_search")
    b = deflated_sharpe(period_returns=pr, n_trials=10, variance_source="explicit", cross_trial_sr_variance=0.0004, n_semantics="exhaustive_grid")
    assert a.n_independence == "unverified"
    assert b.n_independence == "assumed_independent"
    assert a.value == pytest.approx(b.value, abs=1e-15)


def test_enum_violations_raise():
    """邊界⑥⑦：n_semantics／variance_source 非枚舉 ⇒ ValueError；n_trials<1 ⇒ InvalidValidationArgument。"""
    pr = _pr(_returns())
    with pytest.raises(ValueError):
        deflated_sharpe(period_returns=pr, n_trials=3, variance_source="explicit", cross_trial_sr_variance=1.0, n_semantics="magic")
    with pytest.raises(ValueError):
        deflated_sharpe(period_returns=pr, n_trials=3, variance_source="analytic", n_semantics="unknown")
    with pytest.raises(InvalidValidationArgument):
        deflated_sharpe(period_returns=pr, n_trials=0, variance_source="explicit", n_semantics="unknown")


def test_degenerate_returns_and_unknown_ledger_n():
    """邊界：序列含 NaN／std=0 ⇒ not_computed+degenerate_returns；ledger status≠ok ⇒ 傳遞（N 不可知）。"""
    bad = np.array([0.01, float("nan"), 0.02, 0.0, 0.01])
    got = deflated_sharpe(period_returns=_pr(bad), n_trials=3, variance_source="explicit", cross_trial_sr_variance=1.0, n_semantics="unknown")
    assert got.status == "not_computed" and got.reason == "degenerate_returns" and math.isnan(got.value)
    got = deflated_sharpe(period_returns=_pr(np.full(50, 0.01)), n_trials=3, variance_source="explicit", cross_trial_sr_variance=1.0, n_semantics="unknown")
    assert got.status == "not_computed" and got.reason == "degenerate_returns"
    got = deflated_sharpe(
        period_returns=_pr(_returns()), ledger_result=_ledger(0, sharpes=(), status="unavailable", reason="n_unknown"),
        variance_source="ledger_cross_trial", n_semantics="unknown",
    )
    assert got.status == "unavailable" and got.reason == "n_unknown" and got.n_trials_used is None
    assert isinstance(got, DSRResult)


def test_expected_max_sharpe_factor_matches_golden_file():
    """B4 review N6：E[maxSR] 三點同時對照 golden 檔（sha256 經 `_golden` 唯一 loader 驗）。"""
    from ._golden import load_golden

    g = load_golden()["cases"]["expected_max_sharpe_factor"]
    for n, v in g["values"].items():
        assert expected_max_sharpe_factor(int(n)) == pytest.approx(v, abs=g["atol"])
