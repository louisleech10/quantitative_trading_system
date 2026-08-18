"""Task 1.2 驗證：typed Sharpe（退化 NaN＋status、Mertens 變異數、單位鎖定）。

mutation §V-5（退化回 0.0）與 §V-10（Mertens 係數改錯）須使本檔轉紅。
"""

import math

import numpy as np
import pytest
from scipy import stats as scipy_stats

from momentum.Analysis.strategy_validation.sharpe import SharpeResult, compute_sharpe

_RNG = np.random.default_rng(20260817)


def _sample(n=512):
    return _RNG.standard_normal(n) * 0.01 + 0.0005


@pytest.mark.parametrize(
    "series",
    [
        [],                       # 空
        [0.01],                   # 單一觀測
        [float("nan")] * 8,       # 全 NaN
        [0.01, float("nan")],     # 含 NaN
        [0.01, float("inf")],     # 含 inf
        [0.0] * 16,               # 全零（std=0）
        [0.02] * 16,              # 常數序列（std=0）
    ],
)
def test_degenerate_returns_nan_and_non_ok_status(series):
    """§V-5 mutation 鎖：退化情形若回 0.0 而非 NaN ⇒ 轉紅。"""
    res = compute_sharpe(series, periods_per_year=8760)
    assert isinstance(res, SharpeResult)
    assert math.isnan(res.value_per_period)
    assert math.isnan(res.value_annualized)
    assert math.isnan(res.sr_estimator_variance)
    assert res.status != "ok"
    assert res.reason == "degenerate_returns"


def test_hand_computed_case():
    values = np.array([0.01, -0.005, 0.02, 0.0, 0.015])
    res = compute_sharpe(values, periods_per_year=730)
    expected = values.mean() / values.std(ddof=1)
    assert res.value_per_period == pytest.approx(expected, abs=1e-12)
    assert res.n_obs == 5
    assert res.status == "ok"


def test_moments_match_scipy_per_period():
    values = _sample()
    res = compute_sharpe(values, periods_per_year=8760)
    assert res.skew == pytest.approx(scipy_stats.skew(values), abs=1e-10)
    assert res.kurtosis == pytest.approx(
        scipy_stats.kurtosis(values, fisher=False), abs=1e-10
    )


def test_mertens_estimator_variance_hand_formula():
    """§V-10 mutation 鎖：`(γ4-1)/4` 改成 `γ4/4` 即轉紅。"""
    values = _sample()
    res = compute_sharpe(values, periods_per_year=8760)
    sr = res.value_per_period
    expected = (1.0 - res.skew * sr + (res.kurtosis - 1.0) / 4.0 * sr**2) / (res.n_obs - 1)
    assert res.sr_estimator_variance == pytest.approx(expected, abs=1e-12)
    # 與 γ4/4 之錯誤形式確實不同（證明本斷言可證偽）
    wrong = (1.0 - res.skew * sr + res.kurtosis / 4.0 * sr**2) / (res.n_obs - 1)
    assert not math.isclose(expected, wrong, rel_tol=0, abs_tol=1e-15)


def test_annualization_relation_with_zero_rf():
    values = _sample()
    res = compute_sharpe(values, periods_per_year=8760, risk_free_rate=0.0)
    assert res.value_annualized == pytest.approx(
        res.value_per_period * math.sqrt(8760), abs=1e-12
    )


def test_per_period_moments_are_unit_invariant():
    """§V-12 之前哨：moments 與 periods_per_year 無關（單位鎖定）。"""
    values = _sample()
    a = compute_sharpe(values, periods_per_year=1)
    b = compute_sharpe(values, periods_per_year=8760)
    assert a.skew == pytest.approx(b.skew, abs=1e-15)
    assert a.kurtosis == pytest.approx(b.kurtosis, abs=1e-15)
    assert a.value_per_period == pytest.approx(b.value_per_period, abs=1e-15)
    assert a.sr_estimator_variance == pytest.approx(b.sr_estimator_variance, abs=1e-15)


def test_risk_free_rate_shifts_per_period_sharpe():
    values = _sample()
    zero_rf = compute_sharpe(values, periods_per_year=8760, risk_free_rate=0.0)
    with_rf = compute_sharpe(values, periods_per_year=8760, risk_free_rate=0.02)
    assert with_rf.value_per_period < zero_rf.value_per_period


def test_rejects_non_positive_periods():
    with pytest.raises(ValueError):
        compute_sharpe(_sample(), periods_per_year=0)


def test_non_binary_exact_constant_series_is_degenerate_not_huge_sharpe():
    """G1-R11（consult r20 三家一致）：80 個 `0.01`（非二進位可精確表示之常數）以往因求和捨入 std≈1.75e-18≠0 而回 SR≈5.7e15；
    現以 `ptp==0`（位元全等）併判 ⇒ 退化 NaN＋status 非 ok。近常數微擾（`0.01+1e-9·k`）仍為有限值（不引入相對容差）。"""
    import numpy as np

    const = np.full(80, 0.01)
    assert float(np.ptp(const)) == 0.0 and const.std(ddof=1) != 0.0  # 前提：std 精確比對會漏判
    got = compute_sharpe(const, periods_per_year=1)
    assert math.isnan(got.value_per_period) and math.isnan(got.value_annualized)
    assert got.status != "ok" and got.reason == "degenerate_returns"
    perturbed = 0.01 + np.linspace(0.0, 1e-9, 80)
    got2 = compute_sharpe(perturbed, periods_per_year=1)
    assert got2.status == "ok" and math.isfinite(got2.value_per_period) and abs(got2.value_per_period) > 1e6
