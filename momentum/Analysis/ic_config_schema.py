"""IC Gatekeeper configuration schema and loader."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Literal, Any, Dict

import yaml
from pydantic import BaseModel, Field

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


class ICConfig(BaseModel):
    """IC 篩選器完整配置 — 頂層 Schema."""

    model_config = {"populate_by_name": True}
    version: str = "1.0"
    global_settings: ICGlobalConfig = Field(
        default_factory=ICGlobalConfig,
        alias="global",
    )
    preprocessing: PreprocessingConfig = PreprocessingConfig()
    labels: LabelConfig = LabelConfig()
    event_filter: EventFilterConfig = EventFilterConfig()
    ic_calculation: ICCalculationConfig = ICCalculationConfig()
    thresholds: ThresholdsConfig = ThresholdsConfig()
    redundancy: RedundancyConfig = RedundancyConfig()
    turnover: TurnoverConfig = TurnoverConfig()
    report: ReportConfig = ReportConfig()
    performance: PerformanceConfig = PerformanceConfig()


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
