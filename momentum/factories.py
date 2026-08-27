"""Factory functions for momentum domain objects."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, List

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


if TYPE_CHECKING:
    from momentum.Analysis.adversarial_validator import AdversarialValidator
    from momentum.Analysis.strategy_validation.reporter import StrategyValidationReporter
    from momentum.Analysis.analysis_exporter import AnalysisExporter
    from momentum.Analysis.bootstrap_estimator import BootstrapEstimator
    from momentum.Analysis.coverage_analyzer import CoverageAnalyzer
    from momentum.Analysis.cross_symbol_validator import CrossSymbolValidator
    from momentum.Analysis.drift_analyzer import DriftAnalyzer
    from momentum.Analysis.expectancy_calculator import ExpectancyCalculator
    from momentum.Analysis.factor_centrality_analyzer import FactorCentralityAnalyzer
    from momentum.Analysis.factor_exposure_analyzer import FactorExposureAnalyzer
    from momentum.Analysis.factor_orthogonalizer import FactorOrthogonalizer
    from momentum.Analysis.factor_return_analyzer import FactorReturnAnalyzer
    from momentum.Analysis.feature_quality_diagnostics import FeatureQualityDiagnostics
    from momentum.Analysis.feature_toggle_registry import FeatureToggleRegistry
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
    from momentum.Analysis.ic_artifact_writer import ICArtifactWriter
    from momentum.Analysis.ic_reporter import ICReporter
    from momentum.Analysis.ic_split_adapter import ICSplitAdapter
    from momentum.Analysis.indicator_cache import IndicatorCache
    from momentum.Analysis.kline_cache import KlineCache
    from momentum.Analysis.learning_curve_analyzer import LearningCurveAnalyzer
    from momentum.Analysis.long_short_analyzer import LongShortAnalyzer
    from momentum.Analysis.lstm_engine import LSTMEngine
    from momentum.Analysis.model_comparison import ModelComparison
    from momentum.Analysis.model_config import ModelConfigManager
    from momentum.Analysis.model_storage import ModelStorage
    from momentum.Analysis.model_validation.combinatorial_purged_cv import CombinatorialPurgedCV
    from momentum.Analysis.model_validation.cv_validator import CVValidator
    from momentum.Analysis.model_validation.psi_calculator import PSICalculator
    from momentum.Analysis.model_validation.walk_forward_validator import WalkForwardValidator
    from momentum.Analysis.net_ic_analyzer import NetICAnalyzer
    from momentum.Analysis.parameter_sensitivity_analyzer import ParameterSensitivityAnalyzer
    from momentum.Analysis.pattern_definition import Pattern, PatternRule
    from momentum.Analysis.pattern_extractor import PatternExtractor
    from momentum.Analysis.pattern_storage import PatternStorage
    from momentum.Analysis.pattern_validator import PatternValidator
    from momentum.Analysis.prediction_analyzer import PredictionAnalyzer
    from momentum.Analysis.probability_calibrator import ProbabilityCalibrator
    from momentum.Analysis.regime_analyzer import RegimeAnalyzer
    from momentum.Analysis.regime_detector import RegimeDetector
    from momentum.Analysis.rolling_oos_validator import RollingOOSValidator
    from momentum.Analysis.sample_weight_calculator import SampleWeightCalculator
    from momentum.Analysis.signal_density_analyzer import SignalDensityAnalyzer
    from momentum.Analysis.strategy_registry import StrategyRegistry
    from momentum.Analysis.trend_analyzer import TrendAnalyzer
    from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.feature_library import FeatureLibrary
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry
    from momentum.FeatureEngineering.labels.label_generator import LabelGenerator
    from momentum.FeatureEngineering.mcp.feature_factory_mcp import FeatureFactoryMCP
    from momentum.FeatureEngineering.preprocessing._d_star_cache import PreprocessingContext
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
    from momentum.Optimization.objectives.model_hyperparam import ModelHyperparamObjective
    from momentum.Optimization.objectives.strategy_backtest import StrategyBacktestObjective
    from momentum.Optimization.optuna_optimizer import (
        OptunaOptimizer,
        OptimizationResult,
        ParameterRanges,
    )
    from momentum.Optimization.result_analyzer import ResultAnalyzer
    from momentum.core.protocols import (
        IBacktestEngine,
        IModelTrainer,
        IOptimizationObjective,
        IPositionSizer,
    )


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


def create_feature_preprocessor(
    config: Dict[str, Any],
    *,
    context: Optional["PreprocessingContext"] = None,
) -> "FeaturePreprocessor":
    """Create a FeaturePreprocessor with optional L6.5 preprocessing context."""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    return FeaturePreprocessor(config, context=context)


def create_feature_factory(
    cache_dir: Optional[str] = None,
    validate_continuity: bool = True,
) -> "FeatureFactory":
    """Create a FeatureFactory instance with ConfigManager and AdapterRegistry."""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.config_manager import ConfigManager
    from momentum.FeatureEngineering.adapters.adapter_registry import AdapterRegistry
    from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter

    storage = create_kline_storage_manager(cache_dir)
    config_manager = ConfigManager()
    registry = AdapterRegistry()
    registry.register(CryptoSpotAdapter(storage, validate_continuity=validate_continuity))

    return FeatureFactory(config_manager, registry)


def create_column_group_registry(
    work_dir: Optional[Path] = None,
) -> "ColumnGroupRegistry":
    """Factory for ColumnGroupRegistry used by CGSA pipeline."""
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

    resolved_work_dir = work_dir or Path(tempfile.mkdtemp(prefix="ffact_cgsa_"))
    return ColumnGroupRegistry(work_dir=resolved_work_dir)


def create_multi_symbol_runner(
    cache_dir: Optional[str] = None,
    max_workers: int = 8,
) -> "FeatureFactory":
    """Factory for multi-symbol parallel FeatureFactory runner.

    Returns a FeatureFactory instance ready for run_multi_symbol().
    """
    return create_feature_factory(cache_dir=cache_dir, validate_continuity=False)


def create_feature_reader(
    feature_base_path: Optional[str] = None,
) -> "FeatureReader":
    """Factory for V7 FeatureReader (Parquet-only read interface)."""
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    return FeatureReader(feature_base_path or "data_cache/features")


def create_feature_library() -> "FeatureLibrary":
    """Create a FeatureLibrary instance with V7 FeatureReader."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    registry = FeatureRegistry()
    storage = FeatureStorage()
    reader = FeatureReader(str(storage.base_path))
    return FeatureLibrary(registry, storage, feature_reader=reader)


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


def create_regime_detector(
    n_clusters: int = 4,
    lookback: int = 55,
    min_samples_for_fit: int = 100,
    refit_interval: int = 50,
) -> "RegimeDetector":
    from momentum.Analysis.regime_detector import RegimeDetector

    return RegimeDetector(
        n_clusters=n_clusters,
        lookback=lookback,
        min_samples_for_fit=min_samples_for_fit,
        refit_interval=refit_interval,
    )


def create_coverage_analyzer() -> "CoverageAnalyzer":
    from momentum.Analysis.coverage_analyzer import CoverageAnalyzer

    return CoverageAnalyzer(feature_reader_factory=create_feature_reader)


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


def get_parameter_ranges_class():
    """Return ParameterRanges class for Pydantic field type usage."""
    from momentum.Optimization.optuna_optimizer import ParameterRanges

    return ParameterRanges


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


def create_ic_split_adapter(
    expected_freq: Optional[str] = None,
    strict_embargo: bool = True,
    allowed_symbols: Optional[set[str]] = None,
) -> "ICSplitAdapter":
    """Factory — IC SplitPlan adapter。"""
    from momentum.Analysis.ic_split_adapter import ICSplitAdapter

    return ICSplitAdapter(
        expected_freq=expected_freq,
        strict_embargo=strict_embargo,
        allowed_symbols=allowed_symbols,
    )


def create_ic_artifact_writer() -> "ICArtifactWriter":
    """Factory — IC artifact Parquet writer。"""
    from momentum.Analysis.ic_artifact_writer import ICArtifactWriter

    return ICArtifactWriter()


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


# ── Phase 2 Rule 3 factories ────────────────────────────────────────────────

def create_feature_factory_mcp(
    factory: Optional[Any] = None,
    cache_dir: Optional[str] = None,
) -> "FeatureFactoryMCP":
    """Factory — Feature Factory MCP server wrapper."""
    from momentum.FeatureEngineering.mcp.feature_factory_mcp import FeatureFactoryMCP

    if factory is None:
        factory = create_feature_factory(cache_dir=cache_dir)
    return FeatureFactoryMCP(factory, factory.config_manager)


def create_ic_reporter(config: Optional[dict] = None) -> "ICReporter":
    """Factory — IC analysis report generator."""
    from momentum.Analysis.ic_reporter import ICReporter

    return ICReporter(config=config or {})


def sanitize_factor_returns(payload: Any) -> Any:
    """Factory re-export — IC1C-FR-STOPGAP factor_returns 輸出邊界 sanitizer.

    api/services 不得直接 import momentum.Analysis.*;經 factories 取得純函式。
    """
    from momentum.Analysis.factor_return_sanitizer import (
        sanitize_factor_returns as _sanitize_factor_returns,
    )

    return _sanitize_factor_returns(payload)


def create_model_hyperparam_objective(**kwargs: Any) -> "ModelHyperparamObjective":
    """Factory — Optuna objective for model hyper-parameter tuning."""
    from momentum.Optimization.objectives.model_hyperparam import ModelHyperparamObjective

    return ModelHyperparamObjective(**kwargs)


def create_strategy_backtest_objective(**kwargs: Any) -> "StrategyBacktestObjective":
    """Factory — Optuna objective for strategy backtesting."""
    from momentum.Optimization.objectives.strategy_backtest import StrategyBacktestObjective

    return StrategyBacktestObjective(**kwargs)


def create_lstm_engine(config: Optional[Any] = None) -> "LSTMEngine":
    """Factory — LSTM/Transformer sequence model engine."""
    from momentum.Analysis.lstm_engine import LSTMEngine, SequenceModelConfig

    if config is None:
        config = SequenceModelConfig()
    return LSTMEngine(config)


def get_sequence_model_config_class():
    """Return SequenceModelConfig class for type construction."""
    from momentum.Analysis.lstm_engine import SequenceModelConfig

    return SequenceModelConfig


def create_feature_registry() -> "FeatureRegistry":
    """Factory — Feature registry for feature name management."""
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    return FeatureRegistry()


def create_run_lifecycle_manager(
    features_root: Optional[Path] = None,
    cgsa_root: Optional[Path] = None,
    locks_dir: Optional[Path] = None,
    registry: Optional["FeatureRegistry"] = None,
) -> Any:
    """Create the persisted feature-run lifecycle manager."""
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry
    from momentum.FeatureEngineering.run_lifecycle import RunLifecycleManager

    resolved_features = Path(features_root or "data_cache/features")
    resolved_cgsa = Path(cgsa_root or "data_cache/cgsa_work")
    resolved_registry = registry or FeatureRegistry(resolved_features / "registry.json")
    return RunLifecycleManager(
        features_root=resolved_features,
        cgsa_root=resolved_cgsa,
        locks_dir=Path(locks_dir or resolved_features / ".locks"),
        registry=resolved_registry,
    )


def create_prediction_analyzer() -> "PredictionAnalyzer":
    """Factory — Prediction analyzer for pattern analysis."""
    from momentum.Analysis.prediction_analyzer import PredictionAnalyzer

    return PredictionAnalyzer()


def get_strategy_registry() -> "StrategyRegistry":
    """Accessor — module-level strategy registry singleton."""
    from momentum.Analysis.strategy_registry import strategy_registry

    return strategy_registry


def compare_trials(study: Any, **kwargs: Any) -> Any:
    """Re-export — Optuna trial comparison function."""
    from momentum.Optimization.trial_comparison import compare_trials as _compare_trials

    return _compare_trials(study, **kwargs)


def get_trial_comparison_result_class():
    """Return TrialComparisonResult class for type annotation/construction."""
    from momentum.Optimization.trial_comparison import TrialComparisonResult

    return TrialComparisonResult


def load_ic_config(**kwargs: Any) -> Any:
    """Re-export — IC config loader with YAML merge."""
    from momentum.Analysis.ic_config_schema import load_ic_config as _load_ic_config

    return _load_ic_config(**kwargs)


def resolve_run_feature_count(
    *, config_hash: Optional[str] = None, symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
) -> Optional[int]:
    """GAP-3 UX Task 6.1／6.3：解析某個 run 有幾個特徵（**只讀 registry，絕不開 HDF5**）。

    解析**必須有 `config_hash`**；`symbol`／`timeframe` 給了就一併比對。
    解析不出來回 `None`——**呼叫端自己決定要擋還是要放**，本函式不替它決定。

    🔴 **沒有「取最新」之 fallback**：`find_latest` 取的是該 symbol/tf 的**最新**一筆，
      未必是使用者當下要分析的那個 run。實測 `BTCUSDT/12h` 的最新一筆是 **15** 個特徵，
      而同一組合下另有 **218,369** 的 run ⇒ 用它當閘門的輸入會拿**別的 run** 的數字去守，
      比不守更糟（會放行真正該擋的那個）。
    🔴 **`symbol`／`timeframe` 必須參與比對**：同一個 `config_hash` 可能對到多個標的
      （`CODEX-R1-P1-02`）；只比對 hash 並取第一筆會污染 cap 與進度顯示。
      多筆相符時 registry 回 `None`（歧義不猜）。
    🔴 不碰 HDF5 是硬性要求：Task 6.4 要證明「止血閘擋下時未載入大矩陣」，
      檢查路徑上只要開過特徵檔，那個證明就沒有意義了。
    """
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    if not config_hash:
        return None
    entry = FeatureRegistry().find_by_config_hash(config_hash, symbol=symbol, timeframe=timeframe)
    if entry is None:
        return None
    count = entry.get("feature_count")
    return int(count) if isinstance(count, int) else None


def ic_report_reason(category: str, index: int = 0) -> str:
    """GAP-3 UX Task 6.0：IC 側契約之 reason 字面出口（api 層唯一取用點）。

    🔴 R3：api 不得直 `from momentum.Analysis...import`；字面亦**不得**在 api／frontend 硬寫
    （驗收②以機械掃描該字串出現數 == 0）。本出口回**純字串**。
    """
    from momentum.Analysis.ic_config_schema import contract_reason as _impl

    return _impl(category, index)


def ic_report_reasons(category: str) -> tuple:
    """同上，回該分類之完整 reason 清單（保序 tuple）；供成員資格斷言使用。"""
    from momentum.Analysis.ic_config_schema import contract_reasons as _impl

    return _impl(category)


def get_ml_pipeline_config_class():
    """Return MLPipelineConfig class for type construction."""
    from momentum.FeatureEngineering.ml_pipeline_config import MLPipelineConfig

    return MLPipelineConfig


# ─── Route-level factories (Rule 3 Phase 2) ───────────────────────────

def create_result_analyzer() -> "ResultAnalyzer":
    """Create ResultAnalyzer for optimization analysis routes."""
    from momentum.Optimization.result_analyzer import ResultAnalyzer

    return ResultAnalyzer()


def create_strategy_validation_reporter() -> "StrategyValidationReporter":
    """GAP-1 Task 3.4：ml_pipeline 回應之「資格狀態＋警語」reporter（懶 import，仿既有）。"""
    from momentum.Analysis.strategy_validation.reporter import StrategyValidationReporter

    return StrategyValidationReporter()


def get_invalid_validation_argument_class() -> type:
    """GAP-1 A1-16：`InvalidValidationArgument`（ValueError 子類）之類別，供 route 精準辨識「呼叫方 bug ⇒ 5xx」（Rule 3）。"""
    from momentum.Analysis.strategy_validation.min_btl import InvalidValidationArgument

    return InvalidValidationArgument


def get_momentum_config_class():
    """Return MomentumConfig class for static method access."""
    from momentum.core.config import MomentumConfig

    return MomentumConfig


def get_data_source_enum():
    """Return DataSourceEnum for strategy validation."""
    from momentum.Indicators.types import DataSourceEnum

    return DataSourceEnum


def create_time_splitter(**kwargs: Any):
    """Create TimeSplitter instance."""
    from momentum.Analysis.time_splitter import TimeSplitter

    return TimeSplitter(**kwargs)


def get_time_splitter_exceptions():
    """Return TimeSplitter exception classes tuple."""
    from momentum.Analysis.time_splitter import (
        TimestampColumnNotFound,
        InsufficientOOTSamples,
        InsufficientTrainSamples,
        TimeRangeOverlap,
    )

    return TimestampColumnNotFound, InsufficientOOTSamples, InsufficientTrainSamples, TimeRangeOverlap


def create_drift_analyzer() -> "DriftAnalyzer":
    """Create DriftAnalyzer instance."""
    from momentum.Analysis.drift_analyzer import DriftAnalyzer

    return DriftAnalyzer()


def create_kline_cache(**kwargs: Any) -> "KlineCache":
    """Create KlineCache for optimization preloading."""
    from momentum.Analysis.kline_cache import KlineCache

    return KlineCache(**kwargs)


def create_indicator_cache(**kwargs: Any) -> "IndicatorCache":
    """Create IndicatorCache for optimization precomputing."""
    from momentum.Analysis.indicator_cache import IndicatorCache

    return IndicatorCache(**kwargs)


# ---------------------------------------------------------------------------
# GAP-3 事件樣本層（Task B5.1；TODO §0-6-⑦／SPEC §RISK 末行授權之**唯一**出口）
# 契約 JSON 經 pipeline.import_contract()／condition_engine_contract() 唯讀取得（R3：api 不直 import momentum 內部）
# ---------------------------------------------------------------------------
def create_event_sample_pipeline() -> "EventSamplePipeline":
    """事件樣本組合殼（validate→align→dedupe→split→materialize＋契約唯讀出口）；服務端唯一消費入口。"""
    from momentum.Analysis.event_samples.pipeline import EventSamplePipeline

    return EventSamplePipeline()
