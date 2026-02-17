import numpy as np
import pandas as pd

from momentum.Analysis.factor_exposure_analyzer import FactorExposureAnalyzer


def test_single_asset_mode():
    analyzer = FactorExposureAnalyzer(config={})
    positions = pd.Series({"A": 1.0})
    factor_values = pd.DataFrame({"f1": [0.3], "f2": [0.1]}, index=["A"])
    exposure = analyzer.calculate_portfolio_exposure(positions, factor_values)
    assert np.isfinite(exposure["f1"])


def test_hhi_normalization():
    analyzer = FactorExposureAnalyzer(config={"max_single_exposure": 0.4})
    exposures = pd.Series({"f1": 10.0, "f2": 5.0, "f3": 5.0})
    result = analyzer.monitor_exposure_concentration(exposures)
    assert 0 <= result["hhi"] <= 1
    assert result["max_exposure_factor"] == "f1"


def test_unnormalized_weights():
    analyzer = FactorExposureAnalyzer(config={})
    positions = pd.Series({"A": 10.0, "B": 10.0})
    factor_values = pd.DataFrame({"f1": [1.0, 0.0], "f2": [0.0, 1.0]}, index=["A", "B"])
    exposure = analyzer.calculate_portfolio_exposure(positions, factor_values)
    assert np.isclose(float(exposure["f1"]), 0.5)
    assert np.isclose(float(exposure["f2"]), 0.5)


def test_nan_factor_returns_exposure():
    analyzer = FactorExposureAnalyzer(config={})
    portfolio = pd.Series([0.01, 0.02, np.nan, 0.01, -0.01])
    factors = pd.DataFrame({"f1": [0.01, np.nan, 0.02, 0.0, -0.01], "f2": [0.02, 0.01, 0.0, np.nan, -0.02]})
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    assert "factor_betas" in result


def test_zero_r_squared():
    analyzer = FactorExposureAnalyzer(config={})
    np.random.seed(123)
    portfolio = pd.Series(np.random.randn(120))
    factors = pd.DataFrame(np.random.randn(120, 3), columns=["f1", "f2", "f3"])
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    assert np.isfinite(result["alpha"])
    assert np.isfinite(result["r_squared"])


def test_empty_factor_values_returns_empty_series():
    analyzer = FactorExposureAnalyzer(config={})
    exposure = analyzer.calculate_portfolio_exposure(pd.Series({"A": 1.0}), pd.DataFrame())
    assert exposure.empty


def test_zero_absolute_weights_returns_zero_exposure():
    analyzer = FactorExposureAnalyzer(config={})
    positions = pd.Series({"A": 0.0, "B": 0.0})
    factor_values = pd.DataFrame({"f1": [0.3, -0.1], "f2": [0.2, 0.5]}, index=["A", "B"])
    exposure = analyzer.calculate_portfolio_exposure(positions, factor_values)
    assert (exposure == 0.0).all()


def test_factor_attribution_insufficient_rows():
    analyzer = FactorExposureAnalyzer(config={})
    portfolio = pd.Series(np.random.randn(5))
    factors = pd.DataFrame(np.random.randn(5, 2), columns=["f1", "f2"])
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    assert np.isnan(result["r_squared"])


def test_monitor_near_zero_exposures_warning():
    analyzer = FactorExposureAnalyzer(config={})
    exposures = pd.Series({f"f{i}": 1.0 for i in range(30)})
    result = analyzer.monitor_exposure_concentration(exposures, max_single_exposure=0.9)
    assert "near_zero_exposures" in result["warnings"]
