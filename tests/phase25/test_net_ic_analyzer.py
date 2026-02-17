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
