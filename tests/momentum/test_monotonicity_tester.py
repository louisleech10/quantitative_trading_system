import numpy as np
import pandas as pd
import pytest
from scipy import stats

from momentum.Analysis.monotonicity_tester import MonotonicityTester


def test_quantile_returns_and_spread():
    """分位數收益與 Long-Short Spread 計算正確。"""
    feature = pd.Series(np.linspace(0, 1, 100), name="feature")
    label = pd.Series(np.linspace(0, 1, 100), name="label")
    tester = MonotonicityTester({"num_quantiles": 5, "min_group_size": 10})

    result = tester.compute_quantile_returns(feature, label, num_quantiles=5)
    q_returns = result["quantile_mean_returns"]

    assert len(q_returns) == 5
    assert q_returns["Q5"] > q_returns["Q1"]

    low_mask = feature <= feature.quantile(0.2)
    high_mask = feature >= feature.quantile(0.8)
    expected_spread = float(label[high_mask].mean() - label[low_mask].mean())

    assert np.isclose(result["long_short_spread"], expected_spread, atol=1e-6)


def test_monotonicity_score_perfect():
    """完美單調時分數為 1.0。"""
    tester = MonotonicityTester({})
    quantile_returns = {
        "quantile_mean_returns": {"Q1": 0.1, "Q2": 0.2, "Q3": 0.3}
    }
    score = tester.compute_monotonicity_score(quantile_returns)
    assert score == 1.0


def test_quantile_downgrade_to_three():
    """樣本不足時自動降級到 3 分位。"""
    feature = pd.Series(np.linspace(0, 1, 60), name="feature")
    label = pd.Series(np.linspace(0, 1, 60), name="label")
    tester = MonotonicityTester({"num_quantiles": 5, "min_group_size": 25})

    result = tester.compute_quantile_returns(feature, label, num_quantiles=5)
    assert len(result["quantile_mean_returns"]) == 3


def test_long_short_tstat_matches_scipy():
    """Long-Short t-stat 與 scipy 驗算一致。"""
    feature = pd.Series(np.linspace(0, 1, 120), name="feature")
    label = pd.Series(np.linspace(0, 1, 120), name="label")
    tester = MonotonicityTester({"num_quantiles": 5, "min_group_size": 10})

    result = tester.compute_long_short_spread(feature, label, num_quantiles=5)

    quantiles = pd.qcut(feature, 5, labels=False, duplicates="drop")
    low_values = label[quantiles == quantiles.min()]
    high_values = label[quantiles == quantiles.max()]
    expected = stats.ttest_ind(high_values, low_values, nan_policy="omit")

    assert np.isclose(result["tstat"], expected.statistic)
    assert np.isclose(result["pvalue"], expected.pvalue)
    assert "sharpe" in result


def test_empty_data_returns_nan_results():
    """空資料應回傳 NaN 結果。"""
    tester = MonotonicityTester({})
    feature = pd.Series([], dtype=float)
    label = pd.Series([], dtype=float)

    result = tester.compute_quantile_returns(feature, label, num_quantiles=5)
    assert all(np.isnan(value) for value in result["quantile_mean_returns"].values())

    long_short = tester.compute_long_short_spread(feature, label, num_quantiles=5)
    assert np.isnan(long_short["spread"])


def test_quantile_assign_failure_fallbacks():
    """qcut 失敗時應回傳空結果。"""
    tester = MonotonicityTester({"min_group_size": 1})
    feature = pd.Series([1.0] * 10)
    label = pd.Series(np.linspace(0, 1, 10))

    result = tester.compute_quantile_returns(feature, label, num_quantiles=5)
    assert all(np.isnan(value) for value in result["quantile_mean_returns"].values())


def test_pooled_sharpe_edge_cases():
    """樣本不足或變異為零時 Sharpe 回 NaN。"""
    tester = MonotonicityTester({})
    low_values = pd.Series([1.0])
    high_values = pd.Series([1.0])
    spread = 0.0

    sharpe = tester._compute_pooled_sharpe(low_values, high_values, spread)
    assert np.isnan(sharpe)


def test_monotonicity_score_empty_and_single():
    """空或單一分位數時回 0。"""
    tester = MonotonicityTester({})

    assert tester.compute_monotonicity_score({}) == 0.0
    assert tester.compute_monotonicity_score({"quantile_mean_returns": {"Q1": 0.1}}) == 0.0


def test_quantile_returns_handles_empty_bin(monkeypatch):
    """空分位數應輸出 NaN 與空序列。"""
    tester = MonotonicityTester({})
    feature = pd.Series([1.0, 2.0], name="feature")
    label = pd.Series([0.1, 0.2], name="label")

    def _nan_bins(_data, _num_quantiles):
        return pd.Series([np.nan, np.nan], index=_data.index)

    monkeypatch.setattr(tester, "_assign_quantiles", _nan_bins)
    result = tester.compute_quantile_returns(feature, label, num_quantiles=5)

    assert all(np.isnan(value) for value in result["quantile_mean_returns"].values())
    assert all(values == [] for values in result["cumulative_returns"].values())


def test_long_short_spread_quantile_bins_none(monkeypatch):
    """quantile_bins 為 None 時回 NaN。"""
    tester = MonotonicityTester({})
    feature = pd.Series([1.0, 2.0, 3.0], name="feature")
    label = pd.Series([0.1, 0.2, 0.3], name="label")

    monkeypatch.setattr(tester, "_assign_quantiles", lambda *_args, **_kwargs: None)
    result = tester.compute_long_short_spread(feature, label, num_quantiles=5)
    assert np.isnan(result["spread"])


def test_long_short_spread_empty_groups(monkeypatch):
    """空分組時回 NaN。"""
    tester = MonotonicityTester({})
    feature = pd.Series([1.0, 2.0], name="feature")
    label = pd.Series([0.1, 0.2], name="label")

    def _nan_bins(_data, _num_quantiles):
        return pd.Series([np.nan, np.nan], index=_data.index)

    monkeypatch.setattr(tester, "_assign_quantiles", _nan_bins)
    result = tester.compute_long_short_spread(feature, label, num_quantiles=5)
    assert np.isnan(result["spread"])


def test_assign_quantiles_error_paths(monkeypatch):
    """qcut 例外時回退或 None。"""
    tester = MonotonicityTester({})
    data = pd.DataFrame({"feature": [1.0, 2.0, 3.0], "label": [0.1, 0.2, 0.3]})

    def _raise(*_args, **_kwargs):
        raise ValueError("bad")

    monkeypatch.setattr(pd, "qcut", _raise)
    assert tester._assign_quantiles(data, 5) is None


def test_assign_quantiles_actual_bins_less():
    """實際分位數少於要求時降級到 3。"""
    tester = MonotonicityTester({"min_group_size": 1})
    feature = pd.Series([0.0, 0.0, 1.0, 1.0, 1.0], name="feature")
    label = pd.Series([0.1, 0.1, 0.2, 0.2, 0.2], name="label")
    data = pd.concat([feature, label], axis=1)

    bins = tester._assign_quantiles(data, 5)
    assert bins is not None


def test_pooled_sharpe_zero_variance():
    """pooled 變異為 0 時回 NaN。"""
    tester = MonotonicityTester({})
    low_values = pd.Series([1.0, 1.0])
    high_values = pd.Series([1.0, 1.0])
    spread = 0.0

    assert np.isnan(tester._compute_pooled_sharpe(low_values, high_values, spread))
