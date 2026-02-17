from momentum.factories import (
    create_factor_centrality_analyzer,
    create_factor_exposure_analyzer,
    create_factor_orthogonalizer,
    create_factor_return_analyzer,
    create_feature_quality_diagnostics,
    create_long_short_analyzer,
    create_net_ic_analyzer,
    create_parameter_sensitivity_analyzer,
    create_rolling_oos_validator,
    create_trend_analyzer,
)


def test_all_deep_analysis_factories_return_expected_instances():
    created = {
        "FactorReturnAnalyzer": type(create_factor_return_analyzer()).__name__,
        "FactorCentralityAnalyzer": type(create_factor_centrality_analyzer()).__name__,
        "TrendAnalyzer": type(create_trend_analyzer()).__name__,
        "ParameterSensitivityAnalyzer": type(create_parameter_sensitivity_analyzer()).__name__,
        "RollingOOSValidator": type(create_rolling_oos_validator()).__name__,
        "FactorOrthogonalizer": type(create_factor_orthogonalizer()).__name__,
        "FactorExposureAnalyzer": type(create_factor_exposure_analyzer()).__name__,
        "LongShortAnalyzer": type(create_long_short_analyzer()).__name__,
        "FeatureQualityDiagnostics": type(create_feature_quality_diagnostics()).__name__,
        "NetICAnalyzer": type(create_net_ic_analyzer()).__name__,
    }

    assert created == {
        "FactorReturnAnalyzer": "FactorReturnAnalyzer",
        "FactorCentralityAnalyzer": "FactorCentralityAnalyzer",
        "TrendAnalyzer": "TrendAnalyzer",
        "ParameterSensitivityAnalyzer": "ParameterSensitivityAnalyzer",
        "RollingOOSValidator": "RollingOOSValidator",
        "FactorOrthogonalizer": "FactorOrthogonalizer",
        "FactorExposureAnalyzer": "FactorExposureAnalyzer",
        "LongShortAnalyzer": "LongShortAnalyzer",
        "FeatureQualityDiagnostics": "FeatureQualityDiagnostics",
        "NetICAnalyzer": "NetICAnalyzer",
    }
