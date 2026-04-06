import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.turnover_analyzer import TurnoverAnalyzer


def test_quantile_turnover_matches_expected():
    """頂部分位變化比例計算正確。"""
    series = pd.Series([1, 9, 2, 8, 3, 7, 4, 6, 5, 10])
    analyzer = TurnoverAnalyzer({"num_quantiles": 5})

    turnover = analyzer.compute_quantile_turnover(series, num_quantiles=5)

    quantiles = pd.qcut(series, q=5, labels=False, duplicates="drop")
    top_mask = quantiles == quantiles.max()
    expected = top_mask.astype(int).diff().abs().dropna().mean()
    assert np.isclose(turnover, expected)


def test_rank_change_rate_for_increasing_series():
    """遞增序列的 rank change 應為 1。"""
    series = pd.Series([1, 2, 3, 4, 5])
    analyzer = TurnoverAnalyzer({})

    rate = analyzer.compute_rank_change_rate(series)

    assert np.isclose(rate, 1.0)


def test_factor_autocorrelation_matches_pandas():
    """因子自相關應與 pandas.autocorr 一致。"""
    series = pd.Series([1, 2, 3, 4, 5, 6, 7])
    analyzer = TurnoverAnalyzer({})

    autocorr = analyzer.compute_factor_autocorrelation(series)

    assert np.isclose(autocorr, series.autocorr(lag=1))


def test_compute_all_outputs_metrics():
    """批次輸出包含必要欄位。"""
    df = pd.DataFrame(
        {
            "feature_a": [1, 2, 3, 4, 5, 6],
            "feature_b": [6, 5, 4, 3, 2, 1],
        }
    )
    analyzer = TurnoverAnalyzer({"num_quantiles": 3})

    results = analyzer.compute_all(df, num_quantiles=3)

    assert set(results.keys()) == {"feature_a", "feature_b"}
    assert "quantile_turnover" in results["feature_a"]
    assert "rank_change_rate" in results["feature_a"]
    assert "autocorrelation" in results["feature_a"]
    assert "time_series" in results["feature_a"]


def test_net_ic_proxy():
    """Net IC 近似值計算正確。"""
    analyzer = TurnoverAnalyzer({"transaction_cost": 0.01})

    net_ic = analyzer.compute_net_ic_proxy(gross_ic=0.1, turnover_rate=2.0)

    assert np.isclose(net_ic, 0.08)


def test_turnover_handles_empty_and_qcut_failure(monkeypatch):
    """空序列與 qcut 失敗應回 NaN。"""
    analyzer = TurnoverAnalyzer({})

    assert np.isnan(analyzer.compute_quantile_turnover(pd.Series([], dtype=float)))

    def _raise(*_args, **_kwargs):
        raise ValueError("qcut fail")

    monkeypatch.setattr(pd, "qcut", _raise)
    series = pd.Series([1.0, 2.0, 3.0])
    assert np.isnan(analyzer.compute_quantile_turnover(series, num_quantiles=5))


def test_rank_change_and_autocorr_empty():
    """資料不足時回 NaN。"""
    analyzer = TurnoverAnalyzer({})
    series = pd.Series([1.0])

    assert np.isnan(analyzer.compute_rank_change_rate(series))
    assert np.isnan(analyzer.compute_factor_autocorrelation(series))


def test_net_ic_proxy_nan_turnover():
    """Turnover 為 NaN 時回 NaN。"""
    analyzer = TurnoverAnalyzer({})

    assert np.isnan(analyzer.compute_net_ic_proxy(gross_ic=0.1, turnover_rate=float("nan")))


def test_compute_all_defaults_num_quantiles():
    """compute_all 應使用預設分位數。"""
    analyzer = TurnoverAnalyzer({"num_quantiles": 3})
    df = pd.DataFrame({"feature_a": [1.0, 2.0, 3.0], "feature_b": [3.0, 2.0, 1.0]})

    results = analyzer.compute_all(df, num_quantiles=None)

    assert set(results.keys()) == {"feature_a", "feature_b"}


def test_quantile_turnover_empty_changes(monkeypatch):
    """changes 空時回 0。"""
    analyzer = TurnoverAnalyzer({})
    series = pd.Series([1.0, 2.0, 3.0])

    monkeypatch.setattr(pd, "qcut", lambda *_args, **_kwargs: pd.Series([], dtype=float))
    assert analyzer.compute_quantile_turnover(series, num_quantiles=5) == 0.0


def test_rank_change_rate_empty_diffs(monkeypatch):
    """diffs 空時回 0。"""
    analyzer = TurnoverAnalyzer({})
    series = pd.Series([1.0, 2.0])

    def _rank(*_args, **_kwargs):
        return pd.Series([np.nan, np.nan], index=series.index)

    monkeypatch.setattr(pd.Series, "rank", _rank)
    assert analyzer.compute_rank_change_rate(series) == 0.0


def test_compute_turnover_time_series_structure():
    """Turnover 時序輸出結構應完整且長度一致。"""
    analyzer = TurnoverAnalyzer({"num_quantiles": 3})
    series = pd.Series([1, 3, 2, 5, 4], index=[100, 101, 102, 103, 104])

    result = analyzer.compute_turnover_time_series(series, num_quantiles=3)

    assert set(result.keys()) == {"quantile_turnovers", "rank_change_rates", "timestamps"}
    assert len(result["quantile_turnovers"]) == len(result["rank_change_rates"]) == len(result["timestamps"])
    assert len(result["quantile_turnovers"]) == len(series) - 1
    assert all(isinstance(ts, int) for ts in result["timestamps"])


def test_compute_turnover_time_series_qcut_failure(monkeypatch):
    """qcut 失敗時應回傳空時序，不拋例外。"""
    analyzer = TurnoverAnalyzer({})
    series = pd.Series([1.0, 2.0, 3.0, 4.0])

    def _raise(*_args, **_kwargs):
        raise ValueError("qcut fail")

    monkeypatch.setattr(pd, "qcut", _raise)
    result = analyzer.compute_turnover_time_series(series, num_quantiles=4)
    assert result == {
        "quantile_turnovers": [],
        "rank_change_rates": [],
        "timestamps": [],
    }
