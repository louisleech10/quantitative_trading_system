"""API 數據模型導出（lazy 匯入版本）。"""

from importlib import import_module
from typing import Dict


_EXPORT_MAP: Dict[str, str] = {
    # Task 3.2 模型
    "TrainingWindowConfig": "api.models.training_window_config",
    "StrategyConfig": "api.models.training_window_config",
    "SignalDensityRequest": "api.models.training_window_config",
    "SignalDensityResponse": "api.models.training_window_config",

    # Task 3.3+3.4 模型
    "ParameterRange": "api.models.strategy_test_models",
    "EMAParameterRanges": "api.models.strategy_test_models",
    "StrategyConfigTemplate": "api.models.strategy_test_models",
    "ChartSignalCalculationRequest": "api.models.strategy_test_models",
    "ChartSignalCalculationResponse": "api.models.strategy_test_models",
    "SignalPoint": "api.models.strategy_test_models",
    "StrategyTestRequest": "api.models.strategy_test_models",
    "StrategyTestResponse": "api.models.strategy_test_models",
    "StrategyConfigValidationRequest": "api.models.strategy_test_models",
    "StrategyConfigValidationResponse": "api.models.strategy_test_models",

    # Phase 4 Task 4.1 模型
    "FeatureExtractionRequest": "api.models.feature_engineering_models",
    "FeatureExtractionStartResponse": "api.models.feature_engineering_models",
    "FeatureTaskStatusResponse": "api.models.feature_engineering_models",
    "FeatureSummaryResponse": "api.models.feature_engineering_models",
    "ValidationResult": "api.models.feature_engineering_models",
    "FeatureExtractionResult": "api.models.feature_engineering_models",
    "FeatureStats": "api.models.feature_engineering_models",
    "CorrelationPair": "api.models.feature_engineering_models",

    # Phase 3.5 Task 1.1.4 模型
    "CalibrateRequest": "api.models.model_enhancement",
    "WalkForwardRequest": "api.models.model_enhancement",
    "SampleWeightRequest": "api.models.model_enhancement",
    "AdversarialValidateRequest": "api.models.model_enhancement",
    "CPCVRequest": "api.models.model_enhancement",
    "LearningCurveRequest": "api.models.model_enhancement",
    "FullEnhancementRequest": "api.models.model_enhancement",
    "ModelEnhancementResponse": "api.models.model_enhancement",
    "FullEnhancementResponse": "api.models.model_enhancement",

    # Phase 6 Task 6.3 模型
    "FeatureToggleDTO": "api.models.feature_toggle_models",
    "FeatureToggleSummary": "api.models.feature_toggle_models",
    "FeatureToggleListResponse": "api.models.feature_toggle_models",
    "FeatureToggleUpdateRequest": "api.models.feature_toggle_models",
    "FeatureToggleResponse": "api.models.feature_toggle_models",
    "BatchToggleUpdateRequest": "api.models.feature_toggle_models",
    "BatchToggleResponse": "api.models.feature_toggle_models",

    # Phase 7 Task 7.2 模型
    "ExportFormatEnum": "api.models.export_models",
    "ExportScopeEnum": "api.models.export_models",
    "ExportPreviewResponse": "api.models.export_models",
    "ExportQuery": "api.models.export_models",
    "ExportErrorResponse": "api.models.export_models",

    # Phase 8 Task 8.1 模型
    "FeatureOverviewResponse": "api.models.feature_browser_models",
    "FeatureDistributionResponse": "api.models.feature_browser_models",
    "ICDashboardResponse": "api.models.feature_browser_models",
    "RollingICResponse": "api.models.feature_browser_models",
    "QualityScorecardResponse": "api.models.feature_browser_models",
    "CorrelationMatrixResponse": "api.models.feature_browser_models",
    "VIFResponse": "api.models.feature_browser_models",
    "DriftMonitorResponse": "api.models.feature_browser_models",
    "SHAPSummaryResponse": "api.models.feature_browser_models",
    "ImportanceComparisonResponse": "api.models.feature_browser_models",
}


__all__ = list(_EXPORT_MAP.keys())


def __getattr__(name: str):
    module_path = _EXPORT_MAP.get(name)
    if module_path is None:
        raise AttributeError(f"module 'api.models' has no attribute '{name}'")
    module = import_module(module_path)
    return getattr(module, name)


def __dir__():
    return sorted(set(globals().keys()) | set(__all__))
