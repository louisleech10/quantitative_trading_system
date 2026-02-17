import numpy as np
import pandas as pd

from momentum.Analysis.net_ic_analyzer import NetICAnalyzer


def test_no_turnover_data():
    analyzer = NetICAnalyzer(config={})
    result = analyzer.batch_analyze(ic_summary={"f1": {"gross_ic": 0.05}}, turnover_data={})
    assert result["skipped"] is True
    assert result["reason"] == "turnover_not_available"


def test_partial_turnover_data():
    analyzer = NetICAnalyzer(config={})
    result = analyzer.batch_analyze(
        ic_summary={"f1": {"gross_ic": 0.05}, "f2": {"gross_ic": 0.02}},
        turnover_data={"f1": 0.3},
    )
    assert result["features"]["f2"]["skipped"] is True


def test_zero_turnover():
    analyzer = NetICAnalyzer(config={"default_cost_bps": 5})
    result = analyzer.compute_net_ic(gross_ic=0.05, turnover=0.0)
    assert np.isclose(result["net_ic"], result["gross_ic"])


def test_extreme_turnover():
    analyzer = NetICAnalyzer(config={})
    capacity = analyzer.estimate_factor_capacity(turnover=1.2, avg_daily_volume_usd=1_000_000)
    assert capacity["capacity_tier"] == "low"


def test_negative_gross_ic():
    analyzer = NetICAnalyzer(config={})
    result = analyzer.compute_net_ic(gross_ic=-0.01, turnover=0.5)
    assert result["profitable_after_cost"] is False


def test_zero_cost():
    analyzer = NetICAnalyzer(config={"default_cost_bps": 0})
    result = analyzer.compute_net_ic(gross_ic=0.02, turnover=0.6)
    assert np.isclose(result["net_ic"], result["gross_ic"])


def test_no_volume_for_capacity():
    analyzer = NetICAnalyzer(config={})
    result = analyzer.estimate_factor_capacity(turnover=0.2, avg_daily_volume_usd=None)
    assert result["capacity_tier"] == "unknown"


def test_all_unprofitable():
    analyzer = NetICAnalyzer(config={"default_cost_bps": 50})
    summary = analyzer.batch_analyze(
        ic_summary={"f1": {"gross_ic": 0.001}, "f2": {"gross_ic": 0.0012}},
        turnover_data={"f1": 1.0, "f2": 1.1},
    )
    assert summary["summary"]["profitable_count"] == 0
    assert summary["summary"]["total_analyzed"] == 2


def test_compute_net_factor_return_empty_aligned():
    analyzer = NetICAnalyzer(config={})
    result = analyzer.compute_net_factor_return(pd.Series(dtype=float), pd.Series(dtype=float))
    assert result["net_return_series"] == []
    assert np.isnan(result["gross_mean"])


def test_cost_sensitivity_custom_scenarios():
    analyzer = NetICAnalyzer(config={})
    result = analyzer.cost_sensitivity_analysis(0.05, 0.3, scenarios=[2, 4])
    assert [item["cost_bps"] for item in result["scenarios"]] == [2.0, 4.0]


def test_capacity_high_and_medium_tiers():
    analyzer = NetICAnalyzer(config={})
    high = analyzer.estimate_factor_capacity(turnover=0.2, avg_daily_volume_usd=1_000_000)
    medium = analyzer.estimate_factor_capacity(turnover=0.7, avg_daily_volume_usd=1_000_000)
    assert high["capacity_tier"] == "high"
    assert medium["capacity_tier"] == "medium"


def test_batch_analyze_gross_ic_missing_and_factor_returns_integration():
    analyzer = NetICAnalyzer(config={})
    result = analyzer.batch_analyze(
        ic_summary={
            "f1": {"gross_ic": np.nan},
            "f2": {"gross_ic": 0.03, "avg_daily_volume_usd": 2_000_000},
        },
        turnover_data={"f1": 0.2, "f2": 0.3},
        factor_returns={"f2": pd.Series(np.random.randn(50) * 0.01)},
    )
    assert result["features"]["f1"]["reason"] == "gross_ic_missing"
    assert "net_factor_return" in result["features"]["f2"]
