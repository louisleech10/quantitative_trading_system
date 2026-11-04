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


def _ewc_oracle(z: np.ndarray):
    """LLSW 2018 EWC oracle（論文式餘弦基底矩陣直算；ν＝⌊0.4·n^(2/3)⌋ 以十進位高精度）：回 (se, t, p, ν)。"""
    import decimal

    n = z.size
    with decimal.localcontext() as ctx:
        ctx.prec = 50
        nu = int((decimal.Decimal("0.4") * decimal.Decimal(n) ** (decimal.Decimal(2) / decimal.Decimal(3)))
                 .to_integral_value(rounding=decimal.ROUND_FLOOR))
    t_idx = np.arange(1, n + 1, dtype=float)
    basis = np.sqrt(2.0 / n) * np.cos(np.pi * np.arange(1, nu + 1, dtype=float)[:, None] * (t_idx[None, :] - 0.5) / n)
    lam = basis @ (z - z.mean())
    se = math.sqrt(float(np.mean(lam ** 2)) / n)
    t = float(z.mean()) / se
    return se, t, float(2.0 * stats.t.sf(abs(t), df=nu)), nu


def test_t11a_hac_matches_statsmodels_oracle():
    """T-1.1a（SPEC v5.63 ㊹ 改寫）：預設路徑 se/t/p 與 EWC 論文式 oracle allclose(rtol=1e-8)；maxlags 記 None、
    ewc_dof＝ν。場景同前（n×h 含 h＝63 短序列、ties 重場景）——EWC 無 horizon 上限，h＝63 亦照常出 p。"""
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
            pd.DataFrame({"feat": x}), pd.Series(y), h, method="spearman", alpha=0.05
        )["feat"]

        z = _spearman_z(x, y)
        se_o, t_o, p_o, nu = _ewc_oracle(z)
        assert out["maxlags"] is None and out["ewc_dof"] == nu
        assert out["n_obs"] == n and out["inference_status"] == "ok"
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
            pd.DataFrame({"f": x}), pd.Series(y), horizon=5, method="spearman", alpha=0.05, maxlags=2
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
        pd.DataFrame({"f": x}), pd.Series(y), horizon=h, method="spearman", alpha=0.05, maxlags=override
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
    """T-1.1b / M-A: AR(1) φ=0.9 null — 舊法假陽率≫α，HAC（SPEC v5.64 ㊹：預設 EWC）落 binomial 95% 帶。
    seed 10_000＋s、s＝0..1,999（含原 200 個；原 200 seed 得 3／200 低於舊下限 4，同 DGP 2,000 次實測 5.5%），
    接受區間依同一二項 95% 規則以 2,000 次重算（諮詢 R4 收斂）。"""
    alpha = 0.05
    n_seeds = 2000
    n = 5000
    h = 5
    phi = 0.9
    # binomial 95% 允收帶（寫死進碼，固定 n_seeds/α）
    band_lo = int(binom.ppf(0.025, n_seeds, alpha))  # 81
    band_hi = int(binom.ppf(0.975, n_seeds, alpha))  # 120
    assert (band_lo, band_hi) == (81, 120)

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
            pd.DataFrame({"f": x}), pd.Series(y), h, method="spearman", alpha=alpha
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
    """T-1.1c（SPEC v5.63 ㊹ 改寫，預設 EWC）：全NaN ⇒ insufficient_sample／std=0 ⇒ degenerate／h=1 出值且 maxlags
    記 None／ties>50% oracle 恆等／n=8、n=7 皆出值（不另設樣本數下限，原「n=7 NaN」為刻意語意改變）／
    n=3 ⇒ insufficient_sample／h=63 短序列照常出 p（無 horizon 上限）。"""
    rng = np.random.default_rng(42)
    n = 64
    y = pd.Series(rng.normal(size=n))
    kw = {"method": "spearman", "alpha": 0.05}

    # ① 全 NaN feature
    r = compute_hac_ic_statistics(
        pd.DataFrame({"f": np.full(n, np.nan)}), y, 5, **kw
    )["f"]
    assert np.isnan(r["p_value"]) and r["n_obs"] == 0
    assert r["inference_status"] == "insufficient_sample"

    # ② std=0（常數 rank）
    r = compute_hac_ic_statistics(
        pd.DataFrame({"f": np.ones(n)}), y, 5, **kw
    )["f"]
    assert np.isnan(r["p_value"]) and r["n_obs"] == n
    assert r["inference_status"] == "degenerate"

    # ③ h=1 正常出值；EWC 之 maxlags 記 None、ewc_dof＝ν
    x = rng.normal(size=n)
    r = compute_hac_ic_statistics(pd.DataFrame({"f": x}), y, 1, **kw)["f"]
    assert np.isfinite(r["p_value"])
    assert r["maxlags"] is None and r["ewc_dof"] == _ewc_oracle(_spearman_z(x, y.to_numpy()))[3]

    # ④ ties >50% → 正常出值且 oracle 恆等
    n_tie = n
    x_tie = np.concatenate(
        [np.zeros(n_tie // 2 + 5), rng.normal(size=n_tie - (n_tie // 2 + 5))]
    )
    y_tie = rng.normal(size=n_tie)
    r = compute_hac_ic_statistics(
        pd.DataFrame({"f": x_tie}), pd.Series(y_tie), 5, **kw
    )["f"]
    assert np.isfinite(r["p_value"])
    z = _spearman_z(x_tie, y_tie)
    se_o, t_o, p_o, _ = _ewc_oracle(z)
    assert np.allclose([r["se"], r["t_stat"], r["p_value"]], [se_o, t_o, p_o], rtol=1e-8)

    # ⑤ n=8、n=7 皆出值（ν＝1）；n=3 ⇒ ν＝0 ⇒ insufficient_sample
    x8 = rng.normal(size=8)
    y8 = rng.normal(size=8)
    r8 = compute_hac_ic_statistics(pd.DataFrame({"f": x8}), pd.Series(y8), 1, **kw)["f"]
    assert np.isfinite(r8["p_value"]), r8
    r7 = compute_hac_ic_statistics(
        pd.DataFrame({"f": x8[:7]}), pd.Series(y8[:7]), 1, **kw
    )["f"]
    assert np.isfinite(r7["p_value"]) and r7["ewc_dof"] == 1 and r7["inference_status"] == "ok"
    r3 = compute_hac_ic_statistics(
        pd.DataFrame({"f": x8[:3]}), pd.Series(y8[:3]), 1, **kw
    )["f"]
    assert np.isnan(r3["p_value"]) and r3["inference_status"] == "insufficient_sample"

    # ⑥ h=63 短序列 → 照常出 p（EWC 無 horizon 上限；可能附資料不足警示）
    r = compute_hac_ic_statistics(pd.DataFrame({"f": x}), y, 63, **kw)["f"]
    assert np.isfinite(r["p_value"]) and r["inference_status"] == "ok"
    assert r["maxlags"] is None


def test_t11d_mi_use_t_not_normal_default():
    """T-1.1d / M-I（SPEC v5.63 ㊹ 改寫）：p 依 t_ν（ν＝EWC 自由度），同資料以常態分布算之 p 不可 allclose。"""
    n = 32
    h = 1
    rng = np.random.default_rng(20260710)
    x = rng.normal(size=n)
    y = 0.2 * x + rng.normal(size=n)
    z = _spearman_z(x, y)
    out = compute_hac_ic_statistics(pd.DataFrame({"f": x}), pd.Series(y), h, method="spearman", alpha=0.05)["f"]
    assert np.isfinite(out["p_value"])
    se_o, t_o, p_oracle, nu = _ewc_oracle(z)
    p_normal = float(2.0 * stats.norm.sf(abs(t_o)))
    assert out["ewc_dof"] == nu
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


def test_t12c_apply_fdr_unknown_method_raises():
    """SIGNFIX/SIGNFIX2：未知 method 禁 fail-open raw-p；exact-whitelist 僅 fdr_bh。"""
    p_values = {"a": 0.01, "b": 0.04}
    # 含大小寫/空白/None/空字串/非字串 — 一律 raise（禁 strip/lower 正規化）
    for bad in (
        "typo",
        "bonferroni",
        "fdr_by",
        "fdr",
        "",
        "unknown",
        "FDR_BH",
        " fdr_bh ",
        None,
        "banana",
        123,
    ):
        with pytest.raises(ValueError, match="Unsupported FDR method"):
            apply_fdr(p_values, alpha=0.05, method=bad)  # type: ignore[arg-type]
    # 白名單合法值仍可跑，且不得等於 raw p（對多假設 BH 會抬升）
    q, n_tests = apply_fdr(p_values, alpha=0.05, method="fdr_bh")
    assert n_tests == 2
    assert q["a"] >= p_values["a"] or np.isclose(q["a"], p_values["a"])


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
            pd.DataFrame({"f": x}), pd.Series(y), horizon, method="spearman", alpha=alpha
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
    kernel = compute_hac_ic_statistics(pd.DataFrame({"f": x}), pd.Series(y), h, method="spearman", alpha=alpha)["f"]
    boot = block_bootstrap_ic_pvalue(x, y, h, seed=0)
    # 人為 ×2 t → 重算 p（t 分布，自由度＝EWC ν）
    t_mut = float(kernel["t_stat"]) * 2.0
    p_mut = float(2.0 * stats.t.sf(abs(t_mut), df=int(kernel["ewc_dof"])))
    bp = float(boot["p_value"])
    agreement = abs(p_mut - bp) <= tol and (p_mut <= alpha) == (bp <= alpha)
    # 在本固定 seed 下 mutation 必須破壞協議，否則本守衛無證偽力
    assert agreement is False, (
        f"mutation t*2 unexpectedly still agrees: p_mut={p_mut} bp={bp}"
    )
