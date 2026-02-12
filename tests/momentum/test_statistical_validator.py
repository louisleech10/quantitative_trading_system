import numpy as np
from scipy import stats

from momentum.Analysis.statistical_validator import StatisticalValidator


def test_compute_ic_statistics_matches_ttest():
    """t-stat 與 p-value 與 scipy 驗算一致。"""
    values = np.array([0.1, 0.2, 0.05, 0.15, 0.12], dtype=float)
    rolling = {"feat": {"window_5": values.tolist()}}

    validator = StatisticalValidator({"p_value_max": 0.05})
    stats_result = validator.compute_ic_statistics(rolling)["feat"]

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


def test_apply_significance_filter_low_confidence():
    """low_confidence 時 p-value 閾值放寬至 0.10。"""
    validator = StatisticalValidator({"p_value_max": 0.05})
    ic_stats = {
        "good": {"p_value": 0.08, "n_observations": 60},
        "bad": {"p_value": 0.12, "n_observations": 60},
    }

    filtered = validator.apply_significance_filter(
        ic_stats, sample_tier="low_confidence"
    )
    assert "good" in filtered
    assert "bad" not in filtered


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


def test_apply_significance_filter_default_threshold():
    """p_value_max 為 None 時回退預設。"""
    validator = StatisticalValidator({"p_value_max": 0.05})
    ic_stats = {"feat": {"p_value": 0.04}}

    filtered = validator.apply_significance_filter(ic_stats, p_value_max=None)
    assert "feat" in filtered


def test_compute_stats_edge_cases():
    """樣本不足或 std=0 應回 NaN。"""
    validator = StatisticalValidator({})

    stats_small = validator.compute_ic_statistics({"feat": {"window": [0.1]}})["feat"]
    assert np.isnan(stats_small["t_stat"])

    stats_zero_std = validator.compute_ic_statistics({"feat": {"window": [0.0, 0.0, 0.0]}})["feat"]
    assert np.isnan(stats_zero_std["t_stat"])


def test_apply_significance_filter_skips_nan():
    """p_value 為 NaN 時應被跳過。"""
    validator = StatisticalValidator({})
    ic_stats = {"feat": {"p_value": np.nan}}

    assert validator.apply_significance_filter(ic_stats) == {}


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
