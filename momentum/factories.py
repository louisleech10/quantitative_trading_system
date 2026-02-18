"""Factory functions for momentum domain objects."""

from __future__ import annotations

from typing import Any, Dict, Optional, List

from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.DataExtraction.kline_download_service import KlineDownloadService
from momentum.DataExtraction.providers.binance_provider import BinanceProvider
from momentum.DataExtraction.Momentum_Strategy_Data_Loader import MomentumDataLoader
from momentum.DataExtraction.case_search_engine import (
    CaseSearchEngine,
    SearchConfiguration,
    FilterCondition,
)
from momentum.DataExtraction.Market_Screener_Configuration import MarketConfig
from momentum.Indicators import IndicatorEngine
from momentum.FeatureEngineering.feature_extractor import FeatureExtractor, StrategyParams
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.feature_validator import FeatureValidator
from momentum.Indicators.types import DataSourceEnum


def create_kline_storage_manager(cache_dir: Optional[str] = None) -> KlineStorageManager:
    return KlineStorageManager(cache_dir=cache_dir) if cache_dir else KlineStorageManager()


def create_kline_download_service(
    storage_manager: Optional[KlineStorageManager] = None,
) -> KlineDownloadService:
    return KlineDownloadService(storage_manager=storage_manager) if storage_manager else KlineDownloadService()


def create_binance_provider() -> BinanceProvider:
    return BinanceProvider()


def create_momentum_data_loader() -> MomentumDataLoader:
    return MomentumDataLoader()


def create_case_search_engine(
    data_loader: Any,
    enable_parallel: bool = True,
    num_workers: Optional[int] = None,
) -> CaseSearchEngine:
    return CaseSearchEngine(
        data_loader,
        enable_parallel=enable_parallel,
        num_workers=num_workers,
    )


def create_search_configuration(**kwargs: Any) -> SearchConfiguration:
    return SearchConfiguration(**kwargs)


def create_filter_condition(**kwargs: Any) -> FilterCondition:
    return FilterCondition(**kwargs)


def create_market_config() -> MarketConfig:
    return MarketConfig()


def create_indicator_engine() -> IndicatorEngine:
    return IndicatorEngine()


def create_signal_density_analyzer(
    kline_storage: KlineStorageManager,
    indicator_engine: IndicatorEngine,
) -> SignalDensityAnalyzer:
    from momentum.Analysis.signal_density_analyzer import SignalDensityAnalyzer

    return SignalDensityAnalyzer(
        kline_storage=kline_storage,
        indicator_engine=indicator_engine,
    )


def create_xgboost_analyzer() -> XGBoostAnalyzer:
    from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer

    return XGBoostAnalyzer()


def create_model_trainer(
    engine: str = "lightgbm",
    config: Optional[Dict[str, Any]] = None,
) -> "IModelTrainer":
    normalized_engine = engine.lower().strip()
    if normalized_engine == "lightgbm":
        from momentum.Analysis.lightgbm_analyzer import LightGBMAnalyzer

        return LightGBMAnalyzer(params=config)

    if normalized_engine == "xgboost":
        from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer

        return XGBoostAnalyzer(params=config)

    raise ValueError(f"不支援的引擎: {engine}")


def create_model_comparison(
    engines: Optional[List[str]] = None,
    configs: Optional[Dict[str, Dict[str, Any]]] = None,
) -> "ModelComparison":
    from momentum.Analysis.model_comparison import ModelComparison

    selected_engines = engines or ["lightgbm", "xgboost"]
    engine_configs = configs or {}

    trainers = {
        engine_name: create_model_trainer(engine_name, engine_configs.get(engine_name))
        for engine_name in selected_engines
    }
    return ModelComparison(trainers=trainers)


def create_model_config_manager() -> "ModelConfigManager":
    from momentum.Analysis.model_config import ModelConfigManager

    return ModelConfigManager()


def create_model_storage() -> ModelStorage:
    from momentum.Analysis.model_storage import ModelStorage

    return ModelStorage()


def create_feature_storage() -> FeatureStorage:
    return FeatureStorage()


def create_feature_extractor() -> FeatureExtractor:
    return FeatureExtractor()


def create_strategy_params(**kwargs: Any) -> StrategyParams:
    return StrategyParams(**kwargs)


def create_feature_validator() -> FeatureValidator:
    return FeatureValidator()


def create_feature_factory(cache_dir: Optional[str] = None) -> "FeatureFactory":
    """Create a FeatureFactory instance with ConfigManager and AdapterRegistry."""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.config_manager import ConfigManager
    from momentum.FeatureEngineering.adapters.adapter_registry import AdapterRegistry
    from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter

    storage = create_kline_storage_manager(cache_dir)
    config_manager = ConfigManager()
    registry = AdapterRegistry()
    registry.register(CryptoSpotAdapter(storage))

    return FeatureFactory(config_manager, registry)


def create_expectancy_calculator() -> ExpectancyCalculator:
    from momentum.Analysis.expectancy_calculator import ExpectancyCalculator

    return ExpectancyCalculator()


def create_bootstrap_estimator() -> BootstrapEstimator:
    from momentum.Analysis.bootstrap_estimator import BootstrapEstimator

    return BootstrapEstimator()


def create_cross_symbol_validator() -> CrossSymbolValidator:
    from momentum.Analysis.cross_symbol_validator import CrossSymbolValidator

    return CrossSymbolValidator()


def create_regime_analyzer() -> RegimeAnalyzer:
    from momentum.Analysis.regime_analyzer import RegimeAnalyzer

    return RegimeAnalyzer()


def create_pattern_extractor() -> PatternExtractor:
    from momentum.Analysis.pattern_extractor import PatternExtractor

    return PatternExtractor()


def create_pattern_storage() -> PatternStorage:
    from momentum.Analysis.pattern_storage import PatternStorage

    return PatternStorage()


def create_pattern_validator() -> PatternValidator:
    from momentum.Analysis.pattern_validator import PatternValidator

    return PatternValidator()


def create_pattern_rule(**kwargs: Any) -> PatternRule:
    from momentum.Analysis.pattern_definition import PatternRule

    return PatternRule(**kwargs)


def create_pattern(**kwargs: Any) -> Pattern:
    from momentum.Analysis.pattern_definition import Pattern

    return Pattern(**kwargs)


def create_parameter_ranges(**kwargs: Any) -> ParameterRanges:
    from momentum.Optimization.optuna_optimizer import ParameterRanges

    return ParameterRanges(**kwargs)


def create_optuna_optimizer(
    objective: Optional["IOptimizationObjective"] = None,
    sampler_type: str = "tpe",
    checkpoint_dir: Optional[str] = None,
    enable_progress: bool = True,
    **kwargs: Any,
) -> OptunaOptimizer:
    from momentum.Optimization.optuna_optimizer import OptunaOptimizer

    init_kwargs = dict(kwargs)
    init_kwargs["sampler_type"] = init_kwargs.get("sampler_type", sampler_type)
    init_kwargs["enable_progress_monitor"] = init_kwargs.get("enable_progress_monitor", enable_progress)
    if checkpoint_dir is not None:
        init_kwargs["checkpoint_dir"] = init_kwargs.get("checkpoint_dir", checkpoint_dir)
    if objective is not None:
        init_kwargs["objective"] = objective

    return OptunaOptimizer(**init_kwargs)


def create_optimization_result(**kwargs: Any) -> OptimizationResult:
    from momentum.Optimization.optuna_optimizer import OptimizationResult

    return OptimizationResult(**kwargs)


def create_backtest_engine(
    commission: float = 0.001,
    slippage: float = 0.0005,
) -> "IBacktestEngine":
    from momentum.Strategy.vectorized_backtest import VectorizedBacktest

    return VectorizedBacktest(commission=commission, slippage=slippage)


def create_position_sizer(
    method: str = "kelly",
    **kwargs: Any,
) -> "IPositionSizer":
    from momentum.Strategy.position_sizing import (
        KellyPositionSizer,
        FixedPositionSizer,
        ProbabilityScaledSizer,
    )

    sizers = {
        "kelly": KellyPositionSizer,
        "fixed": FixedPositionSizer,
        "probability_scaled": ProbabilityScaledSizer,
    }
    if method not in sizers:
        raise ValueError(
            f"Unknown position sizing method: {method}. Options: {list(sizers.keys())}"
        )
    return sizers[method](**kwargs)


def get_data_source_values() -> List[str]:
    return [source.value for source in DataSourceEnum]


def create_ic_analyzer(config: Optional[dict] = None) -> "ICFilterOrchestrator":
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
    from momentum.Analysis.ic_config_schema import load_ic_config

    ic_config = load_ic_config(api_override=config)
    return ICFilterOrchestrator(ic_config)


def create_factor_return_analyzer(config: Optional[dict] = None) -> "FactorReturnAnalyzer":
    from momentum.Analysis.factor_return_analyzer import FactorReturnAnalyzer

    return FactorReturnAnalyzer(config or {})


def create_factor_centrality_analyzer(config: Optional[dict] = None) -> "FactorCentralityAnalyzer":
    from momentum.Analysis.factor_centrality_analyzer import FactorCentralityAnalyzer

    return FactorCentralityAnalyzer(config or {})


def create_trend_analyzer(config: Optional[dict] = None) -> "TrendAnalyzer":
    from momentum.Analysis.trend_analyzer import TrendAnalyzer

    return TrendAnalyzer(config or {})


def create_parameter_sensitivity_analyzer(config: Optional[dict] = None) -> "ParameterSensitivityAnalyzer":
    from momentum.Analysis.parameter_sensitivity_analyzer import ParameterSensitivityAnalyzer

    return ParameterSensitivityAnalyzer(config or {})


def create_rolling_oos_validator(config: Optional[dict] = None) -> "RollingOOSValidator":
    from momentum.Analysis.rolling_oos_validator import RollingOOSValidator

    return RollingOOSValidator(config or {})


def create_factor_orthogonalizer(config: Optional[dict] = None) -> "FactorOrthogonalizer":
    from momentum.Analysis.factor_orthogonalizer import FactorOrthogonalizer

    return FactorOrthogonalizer(config or {})


def create_factor_exposure_analyzer(config: Optional[dict] = None) -> "FactorExposureAnalyzer":
    from momentum.Analysis.factor_exposure_analyzer import FactorExposureAnalyzer

    return FactorExposureAnalyzer(config or {})


def create_long_short_analyzer(config: Optional[dict] = None) -> "LongShortAnalyzer":
    from momentum.Analysis.long_short_analyzer import LongShortAnalyzer

    return LongShortAnalyzer(config or {})


def create_feature_quality_diagnostics(config: Optional[dict] = None) -> "FeatureQualityDiagnostics":
    from momentum.Analysis.feature_quality_diagnostics import FeatureQualityDiagnostics

    return FeatureQualityDiagnostics(config or {})


def create_net_ic_analyzer(config: Optional[dict] = None) -> "NetICAnalyzer":
    from momentum.Analysis.net_ic_analyzer import NetICAnalyzer

    return NetICAnalyzer(config or {})


def create_label_generator(config: Optional[dict] = None) -> "LabelGenerator":
    from momentum.FeatureEngineering.labels.label_generator import LabelGenerator

    return LabelGenerator(config or {})


def create_cv_validator(config: Optional[dict] = None) -> "CVValidator":
    from momentum.Analysis.model_validation.cv_validator import CVValidator

    return CVValidator(config or {})


def create_psi_calculator() -> "PSICalculator":
    from momentum.Analysis.model_validation.psi_calculator import PSICalculator

    return PSICalculator()


def create_probability_calibrator(
    config: Optional[Dict] = None,
) -> "ProbabilityCalibrator":
    """Factory — M1 機率校準器。"""
    from momentum.Analysis.probability_calibrator import ProbabilityCalibrator

    return ProbabilityCalibrator(config=config)


def create_walk_forward_validator(
    config: Optional[Dict] = None,
) -> "WalkForwardValidator":
    """Factory — M2 Walk-Forward 驗證器。"""
    from momentum.Analysis.model_validation.walk_forward_validator import WalkForwardValidator

    return WalkForwardValidator(config=config)


def create_sample_weight_calculator(
    config: Optional[Dict] = None,
) -> "SampleWeightCalculator":
    """Factory — M3 樣本加權計算器。"""
    from momentum.Analysis.sample_weight_calculator import SampleWeightCalculator

    return SampleWeightCalculator(config=config)


def create_adversarial_validator(
    config: Optional[Dict] = None,
) -> "AdversarialValidator":
    """Factory — M4 Adversarial 驗證器。"""
    from momentum.Analysis.adversarial_validator import AdversarialValidator

    return AdversarialValidator(config=config)


def create_combinatorial_purged_cv(
    config: Optional[Dict] = None,
) -> "CombinatorialPurgedCV":
    """Factory — M5 CPCV。"""
    from momentum.Analysis.model_validation.combinatorial_purged_cv import CombinatorialPurgedCV

    return CombinatorialPurgedCV(config=config)


def create_learning_curve_analyzer(
    config: Optional[Dict] = None,
) -> "LearningCurveAnalyzer":
    """Factory — M6 Learning Curve 分析器。"""
    from momentum.Analysis.learning_curve_analyzer import LearningCurveAnalyzer

    return LearningCurveAnalyzer(config=config)


def create_feature_toggle_registry(
    yaml_path: Optional[str] = None,
) -> "FeatureToggleRegistry":
    """Factory — M7 Feature Toggle Registry。"""
    from momentum.Analysis.feature_toggle_registry import FeatureToggleRegistry

    return FeatureToggleRegistry(yaml_path=yaml_path)


def create_analysis_exporter() -> "AnalysisExporter":
    """Factory — M8 多格式匯出器。"""
    from momentum.Analysis.analysis_exporter import AnalysisExporter

    return AnalysisExporter()
