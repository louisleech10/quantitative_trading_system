"""Feature Factory configuration models."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Literal, Union

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_serializer


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
            "volume",
            "taker_ratio",
        ]
    )
    synthetic_sources: List[str] = Field(
        default_factory=lambda: ["avg-price", "med-price", "typ-price", "wcl-price"]
    )
    adapters: Dict[str, AdapterConfig] = Field(default_factory=dict)


class FeatureCountPreview(BaseModel):
    total_features: int
    estimated_time_seconds: float
    memory_mb: float
    breakdown: Dict[str, int]


class AlignmentMode(str, Enum):
    """Timeframe alignment mode."""

    CLOSE_TIME = "close_time"
    OPEN_MINUS = "open_minus"


SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d", "1w"]


class TimeframeConfig(BaseModel):
    primary: str = "12h"
    training: List[str] = Field(default_factory=lambda: ["12h"])
    alignment: str = "point_in_time"
    alignment_mode: AlignmentMode = AlignmentMode.OPEN_MINUS

    @field_validator("training")
    @classmethod
    def validate_training_tf(cls, value: List[str]) -> List[str]:
        for timeframe in value:
            if timeframe not in SUPPORTED_TIMEFRAMES:
                raise ValueError(
                    f"Unsupported timeframe: {timeframe}, available: {SUPPORTED_TIMEFRAMES}"
                )
        return value

    @field_validator("primary")
    @classmethod
    def validate_primary_tf(cls, value: str) -> str:
        if value not in SUPPORTED_TIMEFRAMES:
            raise ValueError(
                f"Unsupported primary timeframe: {value}, available: {SUPPORTED_TIMEFRAMES}"
            )
        return value


class IndicatorDef(BaseModel):
    name: str
    enabled: bool = True
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


class AdvancedFeatureItemConfig(BaseModel):
    """Microstructure/Entropy/TailRisk 子特徵配置"""
    enabled: bool = True
    model_config = ConfigDict(extra="allow")


class MicrostructureConfig(BaseModel):
    enabled: bool = False
    features: Dict[str, AdvancedFeatureItemConfig] = Field(default_factory=dict)
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
    features: Dict[str, AdvancedFeatureItemConfig] = Field(default_factory=dict)
    windows: List[int] = Field(default_factory=lambda: [55, 100])
    n_bins: int = 10
    apen_m: int = 2
    apen_r_ratio: float = 0.2
    hurst_windows: List[int] = Field(default_factory=lambda: [55, 100, 200])
    fractal_kmax: int = 10
    use_numba: bool = True
    perm_m: int = 3
    perm_windows: List[int] = Field(default_factory=lambda: [21, 55, 100])
    apply_to: List[str] = Field(default_factory=lambda: ["close_return", "volume", "taker_ratio"])
    shannon_windows: List[int] = Field(default_factory=lambda: [21, 55, 100])

    @field_validator("perm_m")
    @classmethod
    def validate_perm_m(cls, value: int) -> int:
        if value < 2:
            raise ValueError(f"perm_m must be >= 2, got {value}")
        return value


class TailRiskConfig(BaseModel):
    enabled: bool = False
    features: Dict[str, AdvancedFeatureItemConfig] = Field(default_factory=dict)
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
    method: str = "quantile"
    sigma_k: float = 3.0
    quantile_range: List[float] = Field(default_factory=lambda: [0.01, 0.99])
    apply_to: Union[str, List[str]] = "all"


class ADFDifferencingConfig(BaseModel):
    enabled: bool = False
    # 0.10 為業界常用顯著水準；金融序列難以通過嚴格的 0.05（如長週期 EMA）
    adf_threshold: float = 0.10
    max_diff: int = 2
    sample_size: int = 500
    apply_to: str = "non_stationary"


class FractionalDifferencingConfig(BaseModel):
    enabled: bool = False
    d_range: List[float] = Field(default_factory=lambda: [0.0, 1.0])
    # 0.10 同上，避免長週期 EMA（EMA_89/100）在 d*=1.0 仍無法通過 0.05 檢定
    adf_threshold: float = 0.10
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
    # replace：原地覆蓋，確保跨標的欄位名稱一致（業界標準）
    # append 會產生 _diff1/_diff2/_fracdiff，不同標的欄位名可能不同 → 多標的訓練 schema 錯誤
    mode: str = "replace"
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


class BinarySignalRule(BaseModel):
    """Binary signal 規則定義"""
    indicator: str
    condition: str
    name_suffix: str
    enabled: bool = True


class BinarySignalToggle(OperatorToggle):
    """Binary signal operator 配置（含 per-rule 控制）"""
    rules: List[BinarySignalRule] = Field(default_factory=list)


class OperatorItemConfig(BaseModel):
    """WorldQuant / 通用 per-operator 配置"""
    enabled: bool = True
    model_config = ConfigDict(extra="allow")


class WorldQuantToggle(OperatorToggle):
    """WorldQuant operator 配置（含 per-sub-operator 控制）"""
    operators: Optional[Dict[str, OperatorItemConfig]] = None

    @model_serializer(mode="wrap")
    def _serialize(self, handler: Any) -> Dict[str, Any]:
        d = handler(self)
        if d.get("operators") is None:
            d.pop("operators", None)
        return d


class OperatorConfig(BaseModel):
    enabled: bool = True
    distance: OperatorToggle = Field(default_factory=OperatorToggle)
    cross: OperatorToggle = Field(default_factory=OperatorToggle)
    momentum_change: OperatorToggle = Field(default_factory=OperatorToggle, alias="momentum")
    ratio: OperatorToggle = Field(default_factory=OperatorToggle)
    binary_signal: BinarySignalToggle = Field(default_factory=BinarySignalToggle)
    worldquant: WorldQuantToggle = Field(default_factory=WorldQuantToggle)
    model_config = ConfigDict(populate_by_name=True)


class AggregatorConfig(BaseModel):
    """Rolling aggregation 單一聚合器配置"""
    enabled: bool = True
    model_config = ConfigDict(extra="allow")


class RollingAggConfig(BaseModel):
    enabled: bool = True
    windows: List[int] = Field(default_factory=lambda: [5, 13, 21])
    aggregators: Dict[str, AggregatorConfig] = Field(
        default_factory=lambda: {
            name: AggregatorConfig()
            for name in [
                "slope", "std", "mean", "rank", "zscore",
                "skew", "kurt", "min", "max", "range",
            ]
        }
    )
    apply_to: Union[str, List[str]] = "all"
    model_config = ConfigDict(extra="allow")

    @field_validator("aggregators", mode="before")
    @classmethod
    def normalize_aggregators(cls, v: Any) -> Any:
        """向後相容：list[str] → dict[str, AggregatorConfig]"""
        if isinstance(v, list):
            return {name: {"enabled": True} for name in v}
        return v


class LagConfig(BaseModel):
    enabled: bool = True
    apply_to: Union[str, List[str]] = "layer1_and_raw"
    exclude_patterns: List[str] = Field(default_factory=lambda: ["meta_*", "label_*"])
    model_config = ConfigDict(extra="allow")


class CrossFeatureConfig(BaseModel):
    """Cross-sectional 單一特徵配置"""
    enabled: bool = True
    model_config = ConfigDict(extra="allow")


class CrossSectionalConfig(BaseModel):
    enabled: bool = True
    reference_symbol: str = "BTCUSDT"
    features: Dict[str, CrossFeatureConfig] = Field(
        default_factory=lambda: {
            name: CrossFeatureConfig()
            for name in ["relative_price", "beta", "idiosyncratic_momentum"]
        }
    )
    model_config = ConfigDict(extra="allow")

    @field_validator("features", mode="before")
    @classmethod
    def normalize_features(cls, v: Any) -> Any:
        """向後相容：list[str] → dict[str, CrossFeatureConfig]"""
        if isinstance(v, list):
            return {name: {"enabled": True} for name in v}
        return v


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

    PARAM_VALUE_DELIMITER = "-"

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
        param_str = FeatureNamingConfig.PARAM_VALUE_DELIMITER.join(param_values)
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
