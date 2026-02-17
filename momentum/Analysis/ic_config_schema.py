"""IC Gatekeeper configuration schema and loader."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Literal, Any, Dict

import yaml
from pydantic import BaseModel, Field, model_validator

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class ICGlobalConfig(BaseModel):
    default_method: Literal["pearson", "spearman", "kendall"] = "spearman"
    default_horizon: int = 5
    time_duration_mode: bool = False


class PreprocessingConfig(BaseModel):
    class WinsorConfig(BaseModel):
        enabled: bool = True
        method: Literal["percentile", "mad", "zscore", "none"] = "percentile"
        lower_percentile: float = 1.0
        upper_percentile: float = 99.0

    class MissingConfig(BaseModel):
        max_fill_forward: int = 3
        min_coverage: float = 0.3

    winsorization: WinsorConfig = WinsorConfig()
    missing_values: MissingConfig = MissingConfig()


class LabelConfig(BaseModel):
    return_type: Literal[
        "simple",
        "log",
        "excess",
        "risk_adjusted",
        "winsorized",
    ] = "simple"
    horizons: list[int] = [1, 2, 3, 5, 8, 13, 21]
    horizons_time: Optional[list[str]] = None
    winsorize_returns: bool = True


class EventFilterConfig(BaseModel):
    enabled: bool = False
    query: Optional[str] = None
    min_events: int = 30

    class SampleSizeTiers(BaseModel):
        sufficient: int = 200
        marginal: int = 100
        low_confidence: int = 30

    sample_size_tiers: SampleSizeTiers = SampleSizeTiers()


class ICCalculationConfig(BaseModel):
    methods: list[str] = ["spearman"]
    rolling_windows: list[int] = [21, 63, 126]
    rolling_stride: int = 1
    ic_decay_horizons: list[int] = [1, 2, 3, 5, 8, 13, 21]

    class ICIRConfig(BaseModel):
        window: int = 63
        reference_tf: str = "12h"

    icir: ICIRConfig = ICIRConfig()

    class GroupedConfig(BaseModel):
        by_year: bool = True
        by_quarter: bool = False
        by_regime: bool = True
        by_volatility: bool = True
        by_category: bool = True
        by_data_source: bool = True
        by_layer: bool = True
        regime_definitions: dict = {
            "bull": "close > close_EMA_55",
            "bear": "close < close_EMA_55",
            "high_vol_percentile": 80,
            "low_vol_percentile": 20,
        }

    grouped_analysis: GroupedConfig = GroupedConfig()


class ThresholdsConfig(BaseModel):
    ic_mean_min: float = 0.02
    icir_min: float = 0.5
    p_value_max: float = 0.05
    ic_hit_rate_min: float = 0.55
    monotonicity_score_min: float = 0.6
    coverage_min: float = 0.5

    class LongShortConfig(BaseModel):
        enabled: bool = False
        min_spread: float = 0.01

    long_short_spread: LongShortConfig = LongShortConfig()


class RedundancyConfig(BaseModel):
    method: Literal["greedy", "hierarchical", "vif"] = "greedy"
    correlation_threshold: float = 0.7
    tiebreaker: Literal["icir", "ic_mean", "monotonicity"] = "icir"

    class HierarchicalConfig(BaseModel):
        linkage_method: str = "average"

    hierarchical: HierarchicalConfig = HierarchicalConfig()

    class VIFConfig(BaseModel):
        max_vif: float = 10.0

    vif: VIFConfig = VIFConfig()

    class DiversificationConfig(BaseModel):
        min_categories: int = 3
        min_data_sources: int = 2
        max_same_category_pct: float = 0.4

    diversification: DiversificationConfig = DiversificationConfig()


class TurnoverConfig(BaseModel):
    enabled: bool = True
    transaction_cost: float = 0.001


class ReportConfig(BaseModel):
    top_n_features: int = 30
    include_decay_analysis: bool = True
    include_quantile_curves: bool = True
    include_correlation_heatmap: bool = True
    include_regime_analysis: bool = True
    include_layer_analysis: bool = True
    include_turnover_analysis: bool = True
    ai_summary: bool = True


class PerformanceConfig(BaseModel):
    max_features_for_correlation: int = 200
    parallel_ic_calculation: bool = True
    n_jobs: int = -1


class FactorReturnConfig(BaseModel):
    enabled: bool = True
    num_quantiles: int = Field(default=5, ge=2, le=20)
    calculate_risk_metrics: bool = True
    risk_free_rate: float = Field(default=0.0, ge=-1.0, le=1.0)


class FactorCentralityConfig(BaseModel):
    enabled: bool = True
    n_components: int = Field(default=5, ge=1, le=50)
    rolling_window: int = Field(default=60, ge=5, le=500)
    crowded_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    min_samples_for_pca: int = Field(default=30, ge=10, le=10000)


class TrendAnalysisConfig(BaseModel):
    enabled: bool = True
    min_samples: int = Field(default=20, ge=5, le=10000)
    significance_level: float = Field(default=0.05, gt=0.0, le=0.2)
    r_squared_threshold: float = Field(default=0.1, ge=0.0, le=1.0)
    dimensions: list[str] = Field(
        default_factory=lambda: ["ic", "centrality", "factor_return", "ls_spread"]
    )


class ParameterSensitivityConfig(BaseModel):
    enabled: bool = True
    min_family_size: int = Field(default=3, ge=2, le=100)
    ic_std_threshold_low: float = Field(default=0.02, ge=0.0, le=1.0)
    ic_std_threshold_high: float = Field(default=0.05, ge=0.0, le=1.0)
    auto_detect_families: bool = True


class RollingOOSAssessmentThresholds(BaseModel):
    robust_hit_rate: float = Field(default=0.7, ge=0.0, le=1.0)
    robust_max_degradation: float = Field(default=0.3, ge=0.0, le=5.0)
    moderate_hit_rate: float = Field(default=0.5, ge=0.0, le=1.0)
    moderate_max_degradation: float = Field(default=0.5, ge=0.0, le=5.0)


class RollingOOSConfig(BaseModel):
    enabled: bool = True
    train_window: int = Field(default=252, ge=10, le=20000)
    test_window: int = Field(default=63, ge=5, le=5000)
    step: int = Field(default=21, ge=1, le=5000)
    min_splits: int = Field(default=5, ge=1, le=200)
    assessment_thresholds: RollingOOSAssessmentThresholds = Field(
        default_factory=RollingOOSAssessmentThresholds
    )


class FactorOrthogonalizationConfig(BaseModel):
    enabled: bool = False
    method: Literal["gram_schmidt", "pca"] = "gram_schmidt"


class FactorExposureConfig(BaseModel):
    enabled: bool = False
    max_single_exposure: float = Field(default=0.4, ge=0.0, le=1.0)


class LongShortAnalysisConfig(BaseModel):
    enabled: bool = True
    num_quantiles: int = Field(default=5, ge=2, le=20)
    long_quantiles: list[int] = Field(default_factory=lambda: [4, 5])
    short_quantiles: list[int] = Field(default_factory=lambda: [1, 2])

    @model_validator(mode="after")
    def _validate_non_overlap(self) -> "LongShortAnalysisConfig":
        long_set = set(self.long_quantiles)
        short_set = set(self.short_quantiles)
        overlap = long_set.intersection(short_set)
        if overlap:
            raise ValueError(
                f"long_quantiles and short_quantiles must not overlap, got {sorted(overlap)}"
            )
        max_quantile = self.num_quantiles
        if any(q < 1 or q > max_quantile for q in self.long_quantiles + self.short_quantiles):
            raise ValueError("quantile index out of range for num_quantiles")
        return self


class FeatureQualityDiagnosticsConfig(BaseModel):
    enabled: bool = True
    adf_significance: float = Field(default=0.05, gt=0.0, le=0.2)
    ljungbox_lags: int = Field(default=10, ge=1, le=500)
    ljungbox_significance: float = Field(default=0.05, gt=0.0, le=0.2)
    coverage_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    drift_window: int = Field(default=60, ge=10, le=5000)
    drift_threshold: float = Field(default=0.25, ge=0.0, le=10.0)
    redundancy_threshold: float = Field(default=0.85, ge=0.0, le=1.0)


class NetICAnalysisConfig(BaseModel):
    enabled: bool = True
    default_cost_bps: float = Field(default=5.0, ge=0.0, le=10000.0)
    slippage_bps: float = Field(default=2.0, ge=0.0, le=10000.0)
    cost_scenarios: list[float] = Field(default_factory=lambda: [1, 3, 5, 10, 20])
    participation_rate: float = Field(default=0.01, ge=0.0, le=1.0)


class DeepAnalysisGlobalConfig(BaseModel):
    timeout_overrides: dict[str, int] = Field(default_factory=dict)
    regime_aware: bool = False


class ShapleyConfig(BaseModel):
    enabled: bool = False
    max_factors: int = Field(default=20, ge=1, le=500)
    use_approximation: bool = True


class ICConfig(BaseModel):
    """IC 篩選器完整配置 — 頂層 Schema."""

    model_config = {"populate_by_name": True}
    version: str = "1.0"
    global_settings: ICGlobalConfig = Field(
        default_factory=ICGlobalConfig,
        alias="global",
    )
    preprocessing: PreprocessingConfig = Field(default_factory=PreprocessingConfig)
    labels: LabelConfig = Field(default_factory=LabelConfig)
    event_filter: EventFilterConfig = Field(default_factory=EventFilterConfig)
    ic_calculation: ICCalculationConfig = Field(default_factory=ICCalculationConfig)
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    redundancy: RedundancyConfig = Field(default_factory=RedundancyConfig)
    turnover: TurnoverConfig = Field(default_factory=TurnoverConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    factor_return: FactorReturnConfig = Field(default_factory=FactorReturnConfig)
    factor_centrality: FactorCentralityConfig = Field(default_factory=FactorCentralityConfig)
    trend_analysis: TrendAnalysisConfig = Field(default_factory=TrendAnalysisConfig)
    parameter_sensitivity: ParameterSensitivityConfig = Field(default_factory=ParameterSensitivityConfig)
    rolling_oos: RollingOOSConfig = Field(default_factory=RollingOOSConfig)
    factor_orthogonalization: FactorOrthogonalizationConfig = Field(
        default_factory=FactorOrthogonalizationConfig
    )
    factor_exposure: FactorExposureConfig = Field(default_factory=FactorExposureConfig)
    long_short_analysis: LongShortAnalysisConfig = Field(default_factory=LongShortAnalysisConfig)
    feature_quality_diagnostics: FeatureQualityDiagnosticsConfig = Field(
        default_factory=FeatureQualityDiagnosticsConfig
    )
    net_ic_analysis: NetICAnalysisConfig = Field(default_factory=NetICAnalysisConfig)
    deep_analysis_global: DeepAnalysisGlobalConfig = Field(default_factory=DeepAnalysisGlobalConfig)
    shapley: ShapleyConfig = Field(default_factory=ShapleyConfig)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _read_yaml(path: Path, required: bool) -> Dict[str, Any]:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"IC config file not found: {path}")
        return {}
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
        if not isinstance(data, dict):
            raise ValueError(f"IC config must be a mapping: {path}")
        return data


def load_ic_config(
    default_path: str = "config/ic_config.yaml",
    user_path: str = "config/user_ic_config.yaml",
    api_override: Optional[dict] = None,
) -> ICConfig:
    """三層合併載入 IC Config：預設 < 使用者 < API Override."""

    default_data = _read_yaml(Path(default_path), required=True)
    user_data = _read_yaml(Path(user_path), required=False)

    merged = _deep_merge(default_data, user_data)
    if api_override:
        if not isinstance(api_override, dict):
            raise ValueError("api_override must be a dict")
        merged = _deep_merge(merged, api_override)

    logger.info("IC config loaded")
    return ICConfig.model_validate(merged)
