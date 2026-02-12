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


def create_optuna_optimizer(**kwargs: Any) -> OptunaOptimizer:
    from momentum.Optimization.optuna_optimizer import OptunaOptimizer

    return OptunaOptimizer(**kwargs)


def create_optimization_result(**kwargs: Any) -> OptimizationResult:
    from momentum.Optimization.optuna_optimizer import OptimizationResult

    return OptimizationResult(**kwargs)


def get_data_source_values() -> List[str]:
    return [source.value for source in DataSourceEnum]


def create_ic_analyzer(config: Optional[dict] = None) -> "ICFilterOrchestrator":
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
    from momentum.Analysis.ic_config_schema import load_ic_config

    ic_config = load_ic_config(api_override=config)
    return ICFilterOrchestrator(ic_config)


def create_label_generator(config: Optional[dict] = None) -> "LabelGenerator":
    from momentum.FeatureEngineering.labels.label_generator import LabelGenerator

    return LabelGenerator(config or {})


def create_cv_validator(config: Optional[dict] = None) -> "CVValidator":
    from momentum.Analysis.model_validation.cv_validator import CVValidator

    return CVValidator(config or {})


def create_psi_calculator() -> "PSICalculator":
    from momentum.Analysis.model_validation.psi_calculator import PSICalculator

    return PSICalculator()
