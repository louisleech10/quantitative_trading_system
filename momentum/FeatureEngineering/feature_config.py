"""Feature Factory configuration models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal, Union

from pydantic import BaseModel, Field, ConfigDict, field_validator


class GlobalSettings(BaseModel):
    sequence_length: int = 100
    max_lag_ratio: float = 0.5
    lag_strategy: Literal["adaptive", "dense", "sparse_log", "custom"] = "adaptive"
    custom_lags: Optional[List[int]] = None


class AdapterConfig(BaseModel):
    enabled: bool = True
    cache_dir: Optional[str] = None
    class_name: Optional[str] = Field(default=None, alias="class")
    model_config = ConfigDict(populate_by_name=True, extra="allow")


class DataSourceConfig(BaseModel):
    enabled_sources: List[str] = Field(
        default_factory=lambda: [
            "close",
            "open",
            "high",
            "low",
            "volume",
            "quote_volume",
            "trades",
            "taker_buy_volume",
            "taker_ratio",
        ]
    )
    synthetic_sources: List[str] = Field(
        default_factory=lambda: ["avg_price", "med_price", "typ_price", "wcl_price"]
    )
    adapters: Dict[str, AdapterConfig] = Field(default_factory=dict)


class FeatureCountPreview(BaseModel):
    total_features: int
    estimated_time_seconds: float
    memory_mb: float
    breakdown: Dict[str, int]


class TimeframeConfig(BaseModel):
    primary: str = "12h"
    training: List[str] = Field(default_factory=lambda: ["12h"])
    alignment: Optional[str] = None


class IndicatorDef(BaseModel):
    name: str
    params: Optional[Dict[str, Any]] = None
    param_strategy: Optional[str] = None
    data_sources: Optional[List[str]] = None
    model_config = ConfigDict(extra="allow")


class IndicatorConfig(BaseModel):
    indicator_type: str
    params: Dict[str, Any] = Field(default_factory=dict)
    data_source: str = "close"
    model_config = ConfigDict(extra="allow")


class CategoryConfig(BaseModel):
    enabled: bool = True
    indicators: List[IndicatorDef] = Field(default_factory=list)
    data_sources: Optional[List[str]] = None
    model_config = ConfigDict(extra="allow")


class MicrostructureConfig(BaseModel):
    enabled: bool = False
    windows: List[int] = Field(default_factory=lambda: [5, 13, 21, 55])
    epsilon: float = 1e-10
    min_trades: int = 1
    enabled_features: Union[str, List[str]] = "all"
    cs_spread_smooth: List[int] = Field(default_factory=lambda: [5, 13, 21])
    ofi_raw: bool = True
    kyle_lambda_windows: List[int] = Field(default_factory=lambda: [13, 21, 55])
    vpin_n_buckets: List[int] = Field(default_factory=lambda: [30, 50])
    vpin_zscore_windows: List[int] = Field(default_factory=lambda: [21, 55])


class EntropyConfig(BaseModel):
    enabled: bool = False
    windows: List[int] = Field(default_factory=lambda: [55, 100])
    n_bins: int = 10
    apen_m: int = 2
    apen_r_ratio: float = 0.2
    hurst_windows: List[int] = Field(default_factory=lambda: [55, 100, 200])
    fractal_kmax: int = 10
    use_numba: bool = True
    perm_m: int = 3
    perm_windows: List[int] = Field(default_factory=lambda: [21, 55, 100])
    apply_to: List[str] = Field(default_factory=lambda: ["close_return"])
    shannon_windows: List[int] = Field(default_factory=lambda: [21, 55, 100])

    @field_validator("perm_m")
    @classmethod
    def validate_perm_m(cls, value: int) -> int:
        if value < 2:
            raise ValueError(f"perm_m must be >= 2, got {value}")
        return value


class TailRiskConfig(BaseModel):
    enabled: bool = False
    windows: List[int] = Field(default_factory=lambda: [21, 55, 100])
    cvar_alphas: List[float] = Field(default_factory=lambda: [0.01, 0.05])
    rv_windows: List[int] = Field(default_factory=lambda: [13, 21, 55])
    mdd_windows: List[int] = Field(default_factory=lambda: [21, 55, 100])

    @field_validator("cvar_alphas")
    @classmethod
    def validate_alphas(cls, value: List[float]) -> List[float]:
        for alpha in value:
            if not 0 < alpha < 1:
                raise ValueError(f"cvar_alpha must be in (0, 1), got {alpha}")
        return value


class WinsorConfig(BaseModel):
    enabled: bool = True
    method: str = "sigma"
    sigma_k: float = 3.0
    quantile_range: List[float] = Field(default_factory=lambda: [0.01, 0.99])
    apply_to: Union[str, List[str]] = "all"


class ADFDifferencingConfig(BaseModel):
    enabled: bool = False
    adf_threshold: float = 0.05
    max_diff: int = 2
    sample_size: int = 500
    apply_to: str = "non_stationary"


class FractionalDifferencingConfig(BaseModel):
    enabled: bool = False
    d_range: List[float] = Field(default_factory=lambda: [0.0, 1.0])
    adf_threshold: float = 0.05
    weight_threshold: float = 1e-5
    precision: float = 0.01
    apply_to: str = "non_stationary"
    cache_d_star: bool = True


class RankTransformConfig(BaseModel):
    enabled: bool = True
    window: int = 252
    apply_to: Union[str, List[str]] = "all"


class GaussianNormalizeConfig(BaseModel):
    enabled: bool = False
    clip_range: List[float] = Field(default_factory=lambda: [0.001, 0.999])
    apply_to: Union[str, List[str]] = "all"


class AdaptiveZScoreConfig(BaseModel):
    enabled: bool = True
    windows: List[int] = Field(default_factory=lambda: [100, 252])
    epsilon: float = 1e-8
    apply_to: Union[str, List[str]] = "all"


class PreprocessingConfig(BaseModel):
    enabled: bool = False
    mode: str = "append"
    winsorization: WinsorConfig = Field(default_factory=WinsorConfig)
    adf_differencing: ADFDifferencingConfig = Field(default_factory=ADFDifferencingConfig)
    fractional_differencing: FractionalDifferencingConfig = Field(default_factory=FractionalDifferencingConfig)
    rank_transform: RankTransformConfig = Field(default_factory=RankTransformConfig)
    gaussian_normalize: GaussianNormalizeConfig = Field(default_factory=GaussianNormalizeConfig)
    adaptive_zscore: AdaptiveZScoreConfig = Field(default_factory=AdaptiveZScoreConfig)


class AtomicIndicatorConfig(BaseModel):
    trend: CategoryConfig = Field(default_factory=CategoryConfig)
    momentum: CategoryConfig = Field(default_factory=CategoryConfig)
    volatility: CategoryConfig = Field(default_factory=CategoryConfig)
    volume: CategoryConfig = Field(default_factory=CategoryConfig)
    cycle: CategoryConfig = Field(default_factory=CategoryConfig)
    pattern: CategoryConfig = Field(default_factory=CategoryConfig)
    statistics: CategoryConfig = Field(default_factory=CategoryConfig)
    microstructure: MicrostructureConfig = Field(default_factory=MicrostructureConfig)
    entropy: EntropyConfig = Field(default_factory=EntropyConfig)
    tail_risk: TailRiskConfig = Field(default_factory=TailRiskConfig)


class OperatorToggle(BaseModel):
    enabled: bool = True
    apply_to: Union[List[str], str] = "all"
    model_config = ConfigDict(extra="allow")


class OperatorConfig(BaseModel):
    distance: OperatorToggle = Field(default_factory=OperatorToggle)
    cross: OperatorToggle = Field(default_factory=OperatorToggle)
    momentum_change: OperatorToggle = Field(default_factory=OperatorToggle, alias="momentum")
    ratio: OperatorToggle = Field(default_factory=OperatorToggle)
    binary_signal: OperatorToggle = Field(default_factory=OperatorToggle)
    worldquant: OperatorToggle = Field(default_factory=OperatorToggle)
    model_config = ConfigDict(populate_by_name=True)


class RollingAggConfig(BaseModel):
    enabled: bool = True
    windows: List[int] = Field(default_factory=lambda: [5, 13, 21])
    aggregators: List[str] = Field(
        default_factory=lambda: [
            "slope",
            "std",
            "mean",
            "rank",
            "zscore",
            "skew",
            "kurt",
            "min",
            "max",
            "range",
        ]
    )
    apply_to: Union[str, List[str]] = "all"
    model_config = ConfigDict(extra="allow")


class LagConfig(BaseModel):
    enabled: bool = True
    apply_to: Union[str, List[str]] = "layer1_and_raw"
    exclude_patterns: List[str] = Field(default_factory=lambda: ["meta_*", "label_*"])
    model_config = ConfigDict(extra="allow")


class CrossSectionalConfig(BaseModel):
    enabled: bool = True
    reference_symbol: str = "BTCUSDT"
    features: List[str] = Field(
        default_factory=lambda: ["relative_price", "beta", "idiosyncratic_momentum"]
    )
    model_config = ConfigDict(extra="allow")


class MetaFeatureConfig(BaseModel):
    enabled: bool = True
    consensus: bool = True
    interaction: bool = True
    time_features: bool = True
    trend_consensus: bool = True
    momentum_divergence: bool = True
    volume_price_divergence: bool = True
    volatility_regime: bool = True
    model_config = ConfigDict(extra="allow")


class BinaryLabelConfig(BaseModel):
    horizons: List[int] = Field(default_factory=lambda: [3, 5, 8, 13, 21])
    threshold: float = 0.0


class RegressionLabelConfig(BaseModel):
    horizons: List[int] = Field(default_factory=lambda: [5, 13])


class LabelConfig(BaseModel):
    binary: BinaryLabelConfig = Field(default_factory=BinaryLabelConfig)
    regression: RegressionLabelConfig = Field(default_factory=RegressionLabelConfig)


class CustomIndicatorDef(BaseModel):
    name: str
    module: str
    function: str
    params: Dict[str, Any] = Field(default_factory=dict)
    data_sources: Optional[List[str]] = None
    model_config = ConfigDict(extra="allow")


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class FactoryConfig(BaseModel):
    version: str = "2.2"
    global_settings: GlobalSettings = Field(alias="global")
    data_sources: DataSourceConfig
    timeframes: TimeframeConfig
    atomic_indicators: AtomicIndicatorConfig
    operators: OperatorConfig
    rolling_aggregation: RollingAggConfig
    lag_features: LagConfig
    cross_sectional: CrossSectionalConfig
    meta_features: MetaFeatureConfig
    labels: LabelConfig
    custom_indicators: List[CustomIndicatorDef] = Field(default_factory=list)
    preprocessing: PreprocessingConfig = Field(default_factory=PreprocessingConfig)
    model_config = ConfigDict(populate_by_name=True, extra="allow")


class FeatureNamingConfig:
    """Legacy naming helpers used by FeatureExtractor and indicators."""

    @staticmethod
    def make_feature_name(
        data_source: str,
        indicator_type: str,
        param_keys: List[str],
        params: Dict[str, Any],
        feature_type: str,
    ) -> str:
        prefix = f"{data_source}_{indicator_type}"
        param_values: List[str] = []
        for key in param_keys:
            if key not in params:
                raise KeyError(f"Missing param '{key}' in params: {params}")
            value = params[key]
            if isinstance(value, float) and value.is_integer():
                param_values.append(str(int(value)))
            else:
                param_values.append(str(value))
        param_str = "_".join(param_values)
        return f"{prefix}{param_str}_{feature_type}"

    @staticmethod
    def make_ema_feature_names(
        data_source: str,
        params: Dict[str, Any],
    ) -> Dict[str, str]:
        volume_threshold = params.get("volume_threshold", 0.6)
        return {
            "ema_short": FeatureNamingConfig.make_feature_name(
                data_source, "ema", ["ema_short"], params, "value"
            ),
            "ema_mid": FeatureNamingConfig.make_feature_name(
                data_source, "ema", ["ema_mid"], params, "value"
            ),
            "ema_long": FeatureNamingConfig.make_feature_name(
                data_source, "ema", ["ema_long"], params, "value"
            ),
            "ema_distance_short_mid": FeatureNamingConfig.make_feature_name(
                data_source, "ema", ["ema_short", "ema_mid"], params, "distance"
            ),
            "ema_distance_mid_long": FeatureNamingConfig.make_feature_name(
                data_source, "ema", ["ema_mid", "ema_long"], params, "distance"
            ),
            "ema_cross_signal": FeatureNamingConfig.make_feature_name(
                data_source, "ema", ["ema_short", "ema_mid"], params, "cross_signal"
            ),
            "volume_spike": f"volume_spike_{int(volume_threshold * 100) if isinstance(volume_threshold, float) else volume_threshold}",
            "taker_ratio_distance": f"taker_ratio_distance_{int(volume_threshold * 100) if isinstance(volume_threshold, float) else volume_threshold}",
        }

    @staticmethod
    def make_rsi_feature_names(
        data_source: str,
        params: Dict[str, Any],
    ) -> Dict[str, str]:
        overbought = params.get("overbought", 70)
        oversold = params.get("oversold", 30)
        return {
            "rsi_value": FeatureNamingConfig.make_feature_name(
                data_source, "rsi", ["period"], params, "value"
            ),
            "rsi_overbought": FeatureNamingConfig.make_feature_name(
                data_source,
                "rsi",
                ["period", "overbought"],
                {**params, "overbought": overbought},
                "signal",
            ),
            "rsi_oversold": FeatureNamingConfig.make_feature_name(
                data_source,
                "rsi",
                ["period", "oversold"],
                {**params, "oversold": oversold},
                "signal",
            ),
            "rsi_momentum": FeatureNamingConfig.make_feature_name(
                data_source, "rsi", ["period"], params, "momentum"
            ),
        }

    @staticmethod
    def make_macd_feature_names(
        data_source: str,
        params: Dict[str, Any],
    ) -> Dict[str, str]:
        return {
            "macd_line": FeatureNamingConfig.make_feature_name(
                data_source, "macd", ["fast", "slow"], params, "line"
            ),
            "macd_signal": FeatureNamingConfig.make_feature_name(
                data_source, "macd", ["fast", "slow", "signal"], params, "signal"
            ),
            "macd_histogram": FeatureNamingConfig.make_feature_name(
                data_source, "macd", ["fast", "slow", "signal"], params, "histogram"
            ),
            "macd_cross": FeatureNamingConfig.make_feature_name(
                data_source, "macd", ["fast", "slow", "signal"], params, "cross"
            ),
        }
