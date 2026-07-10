import math

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats
from scipy.stats import binom
from statsmodels.stats.multitest import multipletests

from momentum.Analysis.statistical_validator import (
    StatisticalValidator,
    apply_fdr,
    compute_hac_ic_statistics,
)
from tests.momentum.helpers.block_bootstrap import block_bootstrap_ic_pvalue


def test_compute_pooled_ic_statistics_deprecated_matches_ttest():
    """【語意遷移】舊 pooled 函式改名後，t-stat/p-value 與 scipy 驗算一致（斷言未放寬）。"""
    values = np.array([0.1, 0.2, 0.05, 0.15, 0.12], dtype=float)
    rolling = {"feat": {"window_5": values.tolist()}}

    validator = StatisticalValidator({"p_value_max": 0.05})
    stats_result = validator.compute_pooled_ic_statistics_deprecated(rolling)["feat"]

    expected = stats.ttest_1samp(values, 0.0, nan_policy="omit")
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))
    n_obs = len(values)
    t_crit = stats.t.ppf(0.975, df=n_obs - 1)
    margin = t_crit * std / np.sqrt(n_obs)

    assert np.isclose(stats_result["t_stat"], expected.statistic)
    assert np.isclose(stats_result["p_value"], expected.pvalue)
    assert np.isclose(stats_result["ci_lower"], mean - margin)
    assert np.isclose(stats_result["ci_upper"], mean + margin)
    assert stats_result["n_observations"] == n_obs


def test_adjust_multiple_comparisons():
    """Bonferroni 與 FDR 校正結果正確。"""
    validator = StatisticalValidator({})
    p_values = {"a": 0.01, "b": 0.02, "c": 0.5}

    bonf = validator.adjust_multiple_comparisons(p_values, method="bonferroni")
    assert np.isclose(bonf["a"], 0.03)
    assert np.isclose(bonf["b"], 0.06)
    assert np.isclose(bonf["c"], 1.0)

    fdr = validator.adjust_multiple_comparisons(p_values, method="fdr_bh")
    assert np.isclose(fdr["a"], 0.03)
    assert np.isclose(fdr["b"], 0.03)
    assert np.isclose(fdr["c"], 0.5)


def test_adjust_multiple_comparisons_empty_and_unknown():
    """空輸入與未知方法應回原值或空 dict。"""
    validator = StatisticalValidator({})

    assert validator.adjust_multiple_comparisons({}, method="fdr_bh") == {}

    p_values = {"a": 0.2}
    raw = validator.adjust_multiple_comparisons(p_values, method="unknown")
    assert raw == {"a": 0.2}


def test_compute_stats_edge_cases():
    """樣本不足或 std=0 應回 NaN。"""
    validator = StatisticalValidator({})

    stats_small = validator.compute_pooled_ic_statistics_deprecated(
        {"feat": {"window": [0.1]}}
    )["feat"]
    assert np.isnan(stats_small["t_stat"])

    stats_zero_std = validator.compute_pooled_ic_statistics_deprecated(
        {"feat": {"window": [0.0, 0.0, 0.0]}}
    )["feat"]
    assert np.isnan(stats_zero_std["t_stat"])


def test_collect_values_and_to_list_branches():
    """_collect_values 與 _to_list 分支。"""
    validator = StatisticalValidator({})

    assert validator._collect_values(None).size == 0

    values = validator._collect_values({"w1": [1.0, 2.0], "w2": np.array([3.0])})
    assert values.size == 3

    values = validator._collect_values([1.0, 2.0])
    assert values.size == 2

    assert validator._to_list(None) == []
    assert validator._to_list(np.array([1.0, 2.0])) == [1.0, 2.0]
    assert validator._to_list([1.0, 2.0]) == [1.0, 2.0]
    assert validator._to_list(1.5) == [1.5]


def test_confidence_interval_edge_cases():
    """樣本不足或 std=0 時 CI 應為 NaN。"""
    validator = StatisticalValidator({})

    ci = validator._confidence_interval(mean=0.1, std=0.0, n_obs=10)
    assert np.isnan(ci[0]) and np.isnan(ci[1])

    ci = validator._confidence_interval(mean=0.1, std=1.0, n_obs=1)
    assert np.isnan(ci[0]) and np.isnan(ci[1])


# ---------------------------------------------------------------------------
# IC 1e+1b Phase1 B1 — HAC kernel / FDR / block bootstrap (T-1.1 / T-1.2 / T-1.3)
# ---------------------------------------------------------------------------


def _spearman_z(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """與 production kernel 同構的貢獻序列（oracle 用）。"""
    rx = stats.rankdata(x, method="average").astype(float)
    ry = stats.rankdata(y, method="average").astype(float)
    u = (rx - rx.mean()) / rx.std(ddof=1)
    v = (ry - ry.mean()) / ry.std(ddof=1)
    return u * v


def _statsmodels_hac_oracle(z: np.ndarray, maxlags: int):
    """statsmodels OLS(z, ones) HAC use_t=True。"""
    ones = np.ones((z.size, 1))
    res = sm.OLS(z, ones).fit(
        cov_type="HAC", cov_kwds={"maxlags": int(maxlags)}, use_t=True
    )
    return float(res.bse[0]), float(res.tvalues[0]), float(res.pvalues[0])


def _would_fail_closed(n_valid: int, L: int) -> bool:
    return L >= n_valid - 1 or n_valid < max(8, 2 * L)


def test_t11a_hac_matches_statsmodels_oracle():
    """T-1.1a: se/t/p 與 statsmodels HAC use_t=True allclose(rtol=1e-8)。"""
    scenarios = []
    for n in (64, 512):
        for h in (1, 5, 63):
            scenarios.append((n, h, "normal", 0))
    # ties 重場景
    scenarios.append((64, 5, "ties", 1))
    scenarios.append((512, 5, "ties", 2))

    for n, h, mode, seed in scenarios:
        rng = np.random.default_rng(1000 + seed + n + h)
        x = rng.normal(size=n)
        y = 0.25 * x + rng.normal(size=n)
        if mode == "ties":
            # >50% 並列：大量量化到少數 bins
            x = np.round(x * 0.5, 0)

        out = compute_hac_ic_statistics(
            pd.DataFrame({"feat": x}), pd.Series(y), h
        )["feat"]
        auto_bw = int(4 * (n / 100.0) ** (2.0 / 9.0))
        L_expect = max(auto_bw, h - 1)

        if _would_fail_closed(n, L_expect):
            assert np.isnan(out["p_value"]), f"fail-closed expected n={n} h={h}"
            assert out["n_obs"] == n
            continue

        z = _spearman_z(x, y)
        se_o, t_o, p_o = _statsmodels_hac_oracle(z, out["maxlags"])
        assert out["maxlags"] == L_expect
        assert out["n_obs"] == n
        assert np.allclose(out["se"], se_o, rtol=1e-8, atol=0.0)
        assert np.allclose(out["t_stat"], t_o, rtol=1e-8, atol=0.0)
        assert np.allclose(out["p_value"], p_o, rtol=1e-8, atol=0.0)
        # CODEX-2: 不得回傳 ic_mean 類欄位
        assert "ic_mean" not in out
        assert "mean_z" not in out


def test_t11a_explicit_maxlags_floor_raises():
    """T-1.1a / M-C: 顯式 maxlags < horizon-1 → ValueError。"""
    rng = np.random.default_rng(0)
    x = rng.normal(size=64)
    y = rng.normal(size=64)
    with pytest.raises(ValueError, match="maxlags"):
        compute_hac_ic_statistics(
            pd.DataFrame({"f": x}), pd.Series(y), horizon=5, maxlags=2
        )


def test_t11a_explicit_maxlags_legal_override():
    """T-1.1a: 合法 maxlags override（>= h-1）成功路徑，L 採用 override。"""
    rng = np.random.default_rng(42)
    n, h = 256, 5
    floor = h - 1  # 4
    override = floor + 2  # 6 >= 4
    x = rng.normal(size=n)
    y = 0.2 * x + rng.normal(size=n)
    out = compute_hac_ic_statistics(
        pd.DataFrame({"f": x}), pd.Series(y), horizon=h, maxlags=override
    )["f"]
    assert out["maxlags"] == override
    assert np.isfinite(out["p_value"]) and np.isfinite(out["t_stat"])
    assert out["n_obs"] == n
    z = _spearman_z(x, y)
    se_o, t_o, p_o = _statsmodels_hac_oracle(z, override)
    assert np.allclose(
        [out["se"], out["t_stat"], out["p_value"]],
        [se_o, t_o, p_o],
        rtol=1e-8,
        atol=0.0,
    )


@pytest.mark.slow_stat
def test_t11b_ma_ar1_false_positive_size():
    """T-1.1b / M-A: AR(1) φ=0.9 null×200 — 舊法假陽率≫α，HAC 落 binomial 95% 帶。"""
    alpha = 0.05
    n_seeds = 200
    n = 5000
    h = 5
    phi = 0.9
    # binomial 95% 允收帶（寫死進碼，固定 n_seeds/α）
    band_lo = int(binom.ppf(0.025, n_seeds, alpha))  # 4
    band_hi = int(binom.ppf(0.975, n_seeds, alpha))  # 16
    assert (band_lo, band_hi) == (4, 16)

    def _ar1(rng: np.random.Generator, length: int) -> np.ndarray:
        eps = rng.normal(size=length)
        series = np.empty(length, dtype=float)
        series[0] = eps[0] / math.sqrt(1.0 - phi * phi)
        for t in range(1, length):
            series[t] = phi * series[t - 1] + eps[t]
        return series

    old_rej = 0
    new_rej = 0
    for s in range(n_seeds):
        rng = np.random.default_rng(10_000 + s)
        x = _ar1(rng, n)
        y = _ar1(rng, n)  # 獨立 AR(1)，null
        z = _spearman_z(x, y)
        t_old = float(z.mean() / (z.std(ddof=1) / math.sqrt(n)))
        p_old = float(2.0 * stats.t.sf(abs(t_old), df=n - 1))
        if p_old <= alpha:
            old_rej += 1
        p_new = compute_hac_ic_statistics(
            pd.DataFrame({"f": x}), pd.Series(y), h
        )["f"]["p_value"]
        if np.isfinite(p_new) and p_new <= alpha:
            new_rej += 1

    old_rate = old_rej / n_seeds
    new_rate = new_rej / n_seeds
    # 舊法反保守：假陽率遠大於 α
    assert old_rate > 0.20, f"old FPR not >> alpha: {old_rate}"
    # 新法落 binomial 95% 允收帶
    assert band_lo <= new_rej <= band_hi, (
        f"HAC FPR count {new_rej} (rate={new_rate}) outside [{band_lo},{band_hi}]"
    )


def test_t11c_boundary_table():
    """T-1.1c: 全NaN / std=0 / h=1 / ties>50% / n=下限出值 / n=下限-1 NaN / h=63 短序列 NaN。"""
    rng = np.random.default_rng(42)
    n = 64
    y = pd.Series(rng.normal(size=n))

    # ① 全 NaN feature
    r = compute_hac_ic_statistics(
        pd.DataFrame({"f": np.full(n, np.nan)}), y, 5
    )["f"]
    assert np.isnan(r["p_value"]) and r["n_obs"] == 0

    # ② std=0（常數 rank）
    r = compute_hac_ic_statistics(
        pd.DataFrame({"f": np.ones(n)}), y, 5
    )["f"]
    assert np.isnan(r["p_value"]) and r["n_obs"] == n

    # ③ h=1 → L=max(auto_bw,0) 正常出值
    x = rng.normal(size=n)
    r = compute_hac_ic_statistics(pd.DataFrame({"f": x}), y, 1)["f"]
    assert np.isfinite(r["p_value"])
    auto_bw = int(4 * (n / 100.0) ** (2.0 / 9.0))
    assert r["maxlags"] == max(auto_bw, 0)

    # ④ ties >50% → 正常出值且 oracle 恆等
    n_tie = n
    x_tie = np.concatenate(
        [np.zeros(n_tie // 2 + 5), rng.normal(size=n_tie - (n_tie // 2 + 5))]
    )
    y_tie = rng.normal(size=n_tie)
    r = compute_hac_ic_statistics(
        pd.DataFrame({"f": x_tie}), pd.Series(y_tie), 5
    )["f"]
    assert np.isfinite(r["p_value"])
    z = _spearman_z(x_tie, y_tie)
    se_o, t_o, p_o = _statsmodels_hac_oracle(z, r["maxlags"])
    assert np.allclose([r["se"], r["t_stat"], r["p_value"]], [se_o, t_o, p_o], rtol=1e-8)

    # ⑤ n=下限出值、n=下限-1 → NaN（h=1 時下限由 max(8,2L) 與 n 共同決定）
    # n=8, L=int(4*(0.08)**(2/9))=2 → 8>=max(8,4) 且 2<7 → 出值
    x8 = rng.normal(size=8)
    y8 = rng.normal(size=8)
    r8 = compute_hac_ic_statistics(pd.DataFrame({"f": x8}), pd.Series(y8), 1)["f"]
    assert np.isfinite(r8["p_value"]), r8
    r7 = compute_hac_ic_statistics(
        pd.DataFrame({"f": x8[:7]}), pd.Series(y8[:7]), 1
    )["f"]
    assert np.isnan(r7["p_value"])

    # ⑥ h=63 短序列 → fail-closed NaN
    r = compute_hac_ic_statistics(pd.DataFrame({"f": x}), y, 63)["f"]
    assert np.isnan(r["p_value"])
    assert r["maxlags"] == max(int(4 * (n / 100.0) ** (2.0 / 9.0)), 62)


def test_t11d_mi_use_t_not_normal_default():
    """T-1.1d / M-I: 同資料 statsmodels 預設(Normal)p 與 oracle use_t p 不可 allclose。"""
    n = 32
    h = 1
    rng = np.random.default_rng(20260710)
    x = rng.normal(size=n)
    y = 0.2 * x + rng.normal(size=n)
    z = _spearman_z(x, y)
    out = compute_hac_ic_statistics(pd.DataFrame({"f": x}), pd.Series(y), h)["f"]
    assert np.isfinite(out["p_value"])
    L = out["maxlags"]
    ones = np.ones((n, 1))
    res_t = sm.OLS(z, ones).fit(
        cov_type="HAC", cov_kwds={"maxlags": L}, use_t=True
    )
    res_n = sm.OLS(z, ones).fit(cov_type="HAC", cov_kwds={"maxlags": L})
    assert res_t.use_t is True
    assert res_n.use_t is False
    p_oracle = float(res_t.pvalues[0])
    p_normal = float(res_n.pvalues[0])
    assert np.allclose(out["p_value"], p_oracle, rtol=1e-8)
    assert not np.allclose(p_normal, p_oracle), (
        f"Normal p and t p unexpectedly allclose: {p_normal} vs {p_oracle}"
    )


def test_t12a_apply_fdr_matches_multipletests():
    """T-1.2a: apply_fdr vs statsmodels multipletests allclose（含 ties / 單元素）。"""
    cases = [
        {"a": 0.01, "b": 0.02, "c": 0.5},
        {"a": 0.04, "b": 0.04, "c": 0.04},  # ties
        {"only": 0.03},  # 單元素
        {"x": 0.001, "y": 0.02, "z": 0.04, "w": 0.8},
    ]
    for p_values in cases:
        q, n_tests = apply_fdr(p_values, alpha=0.05)
        assert n_tests == len(p_values)
        keys = list(p_values.keys())
        _, q_sm, _, _ = multipletests(
            [p_values[k] for k in keys], method="fdr_bh"
        )
        assert np.allclose([q[k] for k in keys], q_sm, rtol=1e-12, atol=0.0)
        # 單 feature → q=p
        if len(p_values) == 1:
            k = keys[0]
            assert np.isclose(q[k], p_values[k])


def test_t12b_apply_fdr_nan_preserve_and_n_tests():
    """T-1.2b: NaN 保位 + n_tests=finite 數；空 dict→({},0)。"""
    q, n_tests = apply_fdr({}, alpha=0.05)
    assert q == {} and n_tests == 0

    p_values = {"a": 0.01, "b": np.nan, "c": 0.2, "d": float("nan")}
    q, n_tests = apply_fdr(p_values, alpha=0.05)
    assert n_tests == 2
    assert np.isfinite(q["a"]) and np.isfinite(q["c"])
    assert np.isnan(q["b"]) and np.isnan(q["d"])
    # 全 NaN
    q_all, n_all = apply_fdr({"a": np.nan, "b": np.nan}, alpha=0.1)
    assert n_all == 0
    assert np.isnan(q_all["a"]) and np.isnan(q_all["b"])


def test_t13_block_bootstrap_agrees_with_kernel():
    """T-1.3: bootstrap 與 kernel 同判，|p 差|≤0.05（固定 seed）。"""
    alpha = 0.05
    tol = 0.05
    cases = []
    # null
    rng = np.random.default_rng(0)
    n, h = 300, 5
    x0 = rng.normal(size=n)
    y0 = rng.normal(size=n)
    cases.append(("null", x0, y0, h))
    # signal
    rng = np.random.default_rng(100)
    x1 = rng.normal(size=n)
    y1 = 0.35 * x1 + rng.normal(size=n)
    cases.append(("signal", x1, y1, h))

    for name, x, y, horizon in cases:
        kernel = compute_hac_ic_statistics(
            pd.DataFrame({"f": x}), pd.Series(y), horizon
        )["f"]
        boot = block_bootstrap_ic_pvalue(x, y, horizon, seed=0 if name == "null" else 100)
        assert not boot["skip"], boot.get("skip_reason")
        kp = float(kernel["p_value"])
        bp = float(boot["p_value"])
        assert abs(kp - bp) <= tol, f"{name}: |{kp}-{bp}|={abs(kp-bp)} > {tol}"
        assert (kp <= alpha) == (bp <= alpha), f"{name}: decision mismatch kp={kp} bp={bp}"


def test_t13_boundary_n_lt_2block_skips():
    """T-1.3 邊界：n < 2*block → skip=True 且 skip_reason=n<2*block。"""
    # h=10 → block=max(10, ceil(n**(1/3)))；取 n=15 → block=10 → 2*block=20 > n
    n, h = 15, 10
    x = np.arange(n, dtype=float)
    y = np.arange(n, dtype=float)[::-1].copy()
    boot = block_bootstrap_ic_pvalue(x, y, h, n_bootstrap=50, seed=0)
    assert boot["skip"] is True
    assert boot["skip_reason"] == "n<2*block"
    assert np.isnan(boot["p_value"])
    assert boot["n"] == n
    assert boot["block"] == max(h, int(math.ceil(n ** (1.0 / 3.0))))


def test_t13_boundary_all_equal_rank_degenerate():
    """T-1.3 邊界：全相同值 → rank_degenerate，不炸、skip=True。"""
    n, h = 100, 5
    x = np.ones(n, dtype=float)
    y = np.full(n, 3.14, dtype=float)
    boot = block_bootstrap_ic_pvalue(x, y, h, n_bootstrap=50, seed=0)
    assert boot["skip"] is True
    assert boot["skip_reason"] == "rank_degenerate"
    assert np.isnan(boot["p_value"])
    # 不應 raise；distribution 為空
    assert isinstance(boot["ic_distribution"], np.ndarray)
    assert boot["ic_distribution"].size == 0


def test_t13_mutation_kernel_t_times_two_breaks_agreement():
    """T-1.3 可證偽：kernel t 人為 ×2 後與 bootstrap 同判斷言應不成立（轉紅證明）。"""
    alpha = 0.05
    tol = 0.05
    rng = np.random.default_rng(0)
    n, h = 300, 5
    x = rng.normal(size=n)
    y = rng.normal(size=n)
    kernel = compute_hac_ic_statistics(pd.DataFrame({"f": x}), pd.Series(y), h)["f"]
    boot = block_bootstrap_ic_pvalue(x, y, h, seed=0)
    # 人為 ×2 t → 重算 p（t 分布）
    t_mut = float(kernel["t_stat"]) * 2.0
    p_mut = float(2.0 * stats.t.sf(abs(t_mut), df=int(kernel["n_obs"]) - 1))
    bp = float(boot["p_value"])
    agreement = abs(p_mut - bp) <= tol and (p_mut <= alpha) == (bp <= alpha)
    # 在本固定 seed 下 mutation 必須破壞協議，否則本守衛無證偽力
    assert agreement is False, (
        f"mutation t*2 unexpectedly still agrees: p_mut={p_mut} bp={bp}"
    )
