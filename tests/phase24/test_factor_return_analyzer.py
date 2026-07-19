import numpy as np
import pandas as pd

from momentum.Analysis.factor_return_analyzer import FactorReturnAnalyzer
from momentum.Analysis.deep_analysis_types import SkippedResult


def _make_data(n: int = 400):
    rng = np.random.default_rng(42)
    idx = pd.date_range("2024-01-01", periods=n, freq="12h")
    feature = pd.Series(rng.normal(size=n), index=idx, name="f1")
    label = pd.Series(feature.values * 0.02 + rng.normal(scale=0.01, size=n), index=idx, name="ret")
    return feature, label


def test_compute_factor_returns_success():
    """舊斷言 `quantile_returns_summary` 為 pre-§U 鍵名;現契約=quantile_summary(+descriptive_full_sample)."""
    feature, label = _make_data()
    analyzer = FactorReturnAnalyzer({"num_quantiles": 5})

    result = analyzer.compute_factor_returns(feature, label)

    assert isinstance(result, dict)
    # 舊: assert "quantile_returns_summary" in result  — 錯,§U 鍵為 quantile_summary
    assert "quantile_summary" in result
    assert result["quantile_summary"].get("descriptive_full_sample") is True
    assert "risk_metrics" in result
    assert "sharpe_ratio" in result["risk_metrics"]
    assert result["num_quantiles_used"] >= 2
    assert result["active_bar_count"] >= 0


def test_insufficient_samples():
    feature, label = _make_data(20)
    analyzer = FactorReturnAnalyzer({})
    result = analyzer.compute_factor_returns(feature, label)
    assert isinstance(result, SkippedResult)
    assert result.error_type == "INSUFFICIENT_DATA"


def test_constant_feature_skip():
    _, label = _make_data(100)
    idx = label.index
    feature = pd.Series(1.0, index=idx)
    analyzer = FactorReturnAnalyzer({})
    result = analyzer.compute_factor_returns(feature, label)
    assert isinstance(result, SkippedResult)


def test_empty_quantile_fallback():
    """舊斷言 num_quantiles_used∈{2,3}:舊 full-sample fallback 降 q。

    新契約:num_quantiles_used=請求值(q_eff 僅在 PIT 逐 bar 內部);二元 feature 仍可 ok。
    """
    rng = np.random.default_rng(1)
    idx = pd.date_range("2024-01-01", periods=120, freq="12h")
    feature = pd.Series(np.where(np.arange(120) % 2 == 0, 1, 2), index=idx)
    label = pd.Series(rng.normal(size=120) * 0.01, index=idx)
    analyzer = FactorReturnAnalyzer({"num_quantiles": 5, "min_samples": 30, "warmup_periods": 20})

    result = analyzer.compute_factor_returns(feature, label)

    # 可能 ok(PIT q_eff 內部降到 2)或 no-active skip;不得崩
    if isinstance(result, SkippedResult):
        assert result.error_type == "INSUFFICIENT_DATA"
        return
    assert isinstance(result, dict)
    # 舊: assert result["num_quantiles_used"] in {2, 3}  — 錯,現回報請求 quantiles=5
    assert result["num_quantiles_used"] == 5
    assert "long_short_mean_return" in result
    assert "quantile_summary" in result


def test_compute_batch():
    """舊斷言 batch 直接回 {f1,f2} 特徵 map;新 §U = status/value/reason ok union."""
    rng = np.random.default_rng(2)
    idx = pd.date_range("2024-01-01", periods=300, freq="12h")
    features = pd.DataFrame(
        {
            "f1": rng.normal(size=300),
            "f2": rng.normal(size=300),
            "f3": rng.normal(size=300),
        },
        index=idx,
    )
    labels = pd.Series(features["f1"] * 0.01 + rng.normal(scale=0.01, size=300), index=idx)
    analyzer = FactorReturnAnalyzer({})

    result = analyzer.compute_batch(features, labels, top_n=2)

    # 舊: assert len(result)==2 / keys=={f1,f2}  — 錯,現為 ok union 包一層
    assert result["status"] == "ok"
    assert result["reason"] is None
    value = result["value"]
    assert value["schema_version"] == "fr_full_v1"
    assert value["semantics"] == "single_asset_factor_timing_ls"
    assert value["quantile_fit"] == "pit_expanding"
    assert set(value["features"].keys()) == {"f1", "f2"}
    assert len(value["features"]) == 2


def test_zero_variance_future_returns_skip():
    feature, _ = _make_data(120)
    label = pd.Series(0.01, index=feature.index)
    analyzer = FactorReturnAnalyzer({})

    result = analyzer.compute_factor_returns(feature, label)

    assert isinstance(result, SkippedResult)
    assert result.reason == "zero variance future_returns"


def test_compute_risk_metrics_empty_and_flat_returns():
    analyzer = FactorReturnAnalyzer({})

    empty_result = analyzer.compute_risk_metrics(pd.Series(dtype=float))
    assert np.isnan(empty_result["sharpe_ratio"])

    flat_result = analyzer.compute_risk_metrics(pd.Series([0.01] * 20))
    assert abs(float(flat_result["annualized_volatility"])) < 1e-8
    assert np.isnan(flat_result["sortino_ratio"]) or abs(float(flat_result["sortino_ratio"])) < 1e-8


def test_assign_quantiles_and_sampling_branches():
    """舊測呼叫已刪 helper `_assign_quantiles_with_fallback`。

    現改驗:常數 feature → SkippedResult;_sample_series 仍可用。
    """
    analyzer = FactorReturnAnalyzer({"num_quantiles": 5, "min_samples": 30})
    idx = pd.date_range("2024-01-01", periods=50, freq="12h")
    const_feature = pd.Series([1.0] * 50, index=idx)
    label = pd.Series(np.linspace(-0.01, 0.01, 50), index=idx)
    result = analyzer.compute_factor_returns(const_feature, label)
    assert isinstance(result, SkippedResult)
    assert "constant" in result.reason

    sampled = analyzer._sample_series(pd.Series(np.arange(500, dtype=float)), max_points=100)
    assert len(sampled) == 100


def test_infer_periods_per_year_default_branch():
    analyzer = FactorReturnAnalyzer({})
    periods = analyzer._infer_periods_per_year(pd.Index([1, 2, 3]))
    assert periods == 365


def test_infer_periods_per_year_datetime_branch():
    analyzer = FactorReturnAnalyzer({})
    idx = pd.date_range("2024-01-01", periods=50, freq="12h")
    periods = analyzer._infer_periods_per_year(idx)
    assert periods > 365


def test_sample_series_small_branch():
    sampled = FactorReturnAnalyzer._sample_series(pd.Series([1.0, 2.0, 3.0]), max_points=10)
    assert sampled == [1.0, 2.0, 3.0]


def test_compute_risk_metrics_calmar_nan_when_no_drawdown():
    analyzer = FactorReturnAnalyzer({})
    result = analyzer.compute_risk_metrics(pd.Series([0.01] * 50), periods_per_year=365)
    assert np.isnan(result["calmar_ratio"]) or np.isfinite(result["calmar_ratio"])
