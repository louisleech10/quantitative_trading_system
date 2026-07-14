"""IC analysis API models."""

from __future__ import annotations

import math
from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FeatureFilterConfig(BaseModel):
    include_features: Optional[List[str]] = None
    exclude_features: Optional[List[str]] = None
    include_pattern: Optional[str] = None
    include_categories: Optional[List[str]] = None
    include_data_sources: Optional[List[str]] = None
    include_families: Optional[List[str]] = None
    max_features: Optional[int] = Field(default=None, ge=1)


class DeepAnalysisModules(BaseModel):
    # IC1C-FR-STOPGAP: default-off(單數 factor_return;修復歸 1c-FR-FULL)
    factor_return: bool = False
    factor_centrality: bool = True
    trend_analysis: bool = True
    parameter_sensitivity: bool = True
    rolling_oos: bool = True
    factor_orthogonalization: bool = False
    factor_exposure: bool = False
    long_short_analysis: bool = True
    feature_quality_diagnostics: bool = True
    net_ic_analysis: bool = True


class NetICAnalysisRequest(BaseModel):
    """Deep analysis 成本參數(typed 一等公民)。

    統一 validator 偽碼(TODO Task 2.1 / Task 1.1 ④):
    - cost_bps 非 None → 一律驗域(有限且 0<x≤1000),與 enabled 無關
    - cost_enabled=True → 另驗 cost_bps 非 None
    - 0 非法;「無成本」唯一表示=cost_enabled=False
    """

    cost_enabled: bool = False
    cost_bps: Optional[float] = None

    @model_validator(mode="after")
    def _validate_cost_params(self) -> "NetICAnalysisRequest":
        cost_bps = self.cost_bps
        if cost_bps is not None:
            try:
                bps = float(cost_bps)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"cost_bps must be finite and in (0, 1000], got {cost_bps!r}"
                ) from exc
            if not math.isfinite(bps) or not (0.0 < bps <= 1000.0):
                raise ValueError(
                    f"cost_bps must be finite and in (0, 1000], got {cost_bps!r}"
                )
        if self.cost_enabled and cost_bps is None:
            raise ValueError(
                "cost_enabled=True requires cost_bps to be set (0 is illegal)"
            )
        return self


def _reject_net_ic_analysis_in_config_override(
    config_override: Optional[Dict[str, Any]],
) -> None:
    """T-F12:config_override 禁止 net_ic_analysis 整節(白名單空集)。"""
    if isinstance(config_override, dict) and "net_ic_analysis" in config_override:
        raise ValueError(
            "config_override.net_ic_analysis is rejected; "
            "use typed 'net_ic' field on DeepAnalysisRequest"
        )


class DeepAnalysisRequest(BaseModel):
    selected_features: Optional[List[str]] = None
    top_n: int = Field(default=30, ge=1, le=200)
    modules: DeepAnalysisModules = Field(default_factory=DeepAnalysisModules)
    config_override: Optional[Dict[str, Any]] = None
    net_ic: NetICAnalysisRequest = Field(default_factory=NetICAnalysisRequest)

    @model_validator(mode="after")
    def _reject_net_ic_override(self) -> "DeepAnalysisRequest":
        _reject_net_ic_analysis_in_config_override(self.config_override)
        return self


class ICResultV2Response(BaseModel):
    """Versioned IC result response with artifact-backed top-N summary."""

    schema_version: Literal[2] = 2
    top_n_summary: List[Dict[str, Any]] = Field(default_factory=list)
    artifact_uri: Optional[str] = None
    total_features: int = 0


class ICArtifactFilter(BaseModel):
    """Whitelist-only artifact filter model for the future HTTP query endpoint."""

    model_config = ConfigDict(extra="forbid")

    feature_name: Optional[str] = None
    horizon: Optional[int] = None
    eval_status: Optional[str] = None
    selection_scope_id: Optional[str] = None


class ICArtifactQueryParams(BaseModel):
    """Artifact query contract; HTTP filtering endpoint lands in a later phase."""

    sort_by: Literal["icir", "ic_mean", "p_value"] = "icir"
    filter: Optional[ICArtifactFilter] = None
    page_size: int = Field(default=5000, ge=1, le=50000)
    cursor: Optional[str] = None


class FeatureTierRequest(BaseModel):
    active_preset: Literal["foundation", "intermediate", "advanced", "custom"] = Field(default="intermediate")
    presets: Optional[Dict[str, Any]] = None
    custom_overrides: Optional[Dict[str, Dict[str, bool]]] = None


class CrossRunRef(BaseModel):
    symbol: str
    config_hash: str


class ICAnalyzeRequest(BaseModel):
    features_path: Optional[str] = Field(None, description="Path to features HDF5 (deprecated, optional)")
    symbol: Optional[str] = Field(None, description="Feature Library symbol")
    symbols: Optional[List[str]] = Field(None, description="Feature Library symbols for cross-sectional mode")
    timeframe: Optional[str] = Field(None, description="Feature Library timeframe")
    config_hash: Optional[str] = Field(None, description="精確指定 run，None 則回退最新")
    cross_sectional_runs: Optional[List[CrossRunRef]] = Field(
        None,
        description="橫截面 per-symbol config_hash",
    )
    mode: Literal["longitudinal", "cross_sectional"] = Field(
        "longitudinal",
        description="IC analysis mode",
    )
    labels_path: Optional[str] = Field(None, description="Path to labels HDF5")
    meta_path: Optional[str] = Field(None, description="Path to metadata JSON")
    config_override: Optional[Dict[str, Any]] = Field(None, description="Config override")
    event_query: Optional[str] = Field(None, description="Event filter query")
    event_timestamps: Optional[List[int]] = Field(
        None,
        description="Event timestamps for filtering",
    )
    feature_filter: Optional[FeatureFilterConfig] = Field(None, description="Feature pre-filter config")
    deep_analysis: bool = Field(False, description="Enable deep analysis after main IC workflow")
    deep_analysis_config: Optional[DeepAnalysisRequest] = Field(
        None,
        description="Deep analysis request payload",
    )
    feature_tiers: Optional[FeatureTierRequest] = Field(
        None,
        description="Feature tier configuration override",
    )

    @model_validator(mode="after")
    def _reject_net_ic_override(self) -> "ICAnalyzeRequest":
        """T-F12 雙入口:ICAnalyzeRequest.config_override 亦拒 net_ic_analysis 整節。"""
        _reject_net_ic_analysis_in_config_override(self.config_override)
        return self


class ICFullAnalysisRequest(ICAnalyzeRequest):
    """一站式分析請求（主流程 + 深度分析）。"""

    labels_path: str = Field(..., description="Path to labels HDF5")


class ICAnalyzeResponse(BaseModel):
    task_id: str
    status: str


class ICTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    current_stage: Optional[str] = None
    error: Optional[str] = None


class ICTopFeaturesRequest(BaseModel):
    n: int = 30
    horizon: int = 5
    sort_by: str = "icir"


class ICRefilterRequest(BaseModel):
    thresholds: Dict[str, Any]


class ModuleStatusResponse(BaseModel):
    module_name: str
    status: str
    reason: Optional[str] = None
    error_type: Optional[str] = None


class DeepAnalysisSummaryResponse(BaseModel):
    total_modules: int = 10
    completed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    total_execution_time_s: float = 0.0


class DeepAnalysisResponse(BaseModel):
    task_id: str
    status: str
    progress: float = 0.0
    current_step: Optional[str] = None
    summary: Optional[DeepAnalysisSummaryResponse] = None
    module_status: Optional[List[ModuleStatusResponse]] = None
    results: Optional[Dict[str, Any]] = None
    applied_tier: Optional[str] = None
    error: Optional[str] = None


class FeatureListItem(BaseModel):
    feature_name: str
    category: Optional[str] = None
    data_source: Optional[str] = None
    family: Optional[str] = None
    layer: Optional[int] = None


class FeatureListResponse(BaseModel):
    total: int
    features: List[FeatureListItem]


class ApplyTransformsRequest(BaseModel):
    """Request body for POST /api/v1/ic/{task_id}/apply-transforms."""

    selected_features: List[str] = Field(..., description="IC 篩選後的特徵名稱清單")
    rank: bool = Field(default=True, description="套用 Rank Transform")
    zscore: bool = Field(default=True, description="套用 Adaptive Z-Score")
    gaussian: bool = Field(default=False, description="套用 Gaussian Normalize（在 rank/zscore 之後執行）")
    rank_window: int = Field(default=252, ge=2, description="Rank Transform 滾動窗口（天）")
    zscore_windows: List[int] = Field(default_factory=lambda: [100, 252], description="Adaptive Z-Score 窗口清單")


class ApplyTransformsResponse(BaseModel):
    """Response for apply-transforms endpoint."""

    task_id: str
    selected_feature_count: int
    transforms_applied: List[str]
    output_path: str
    output_rows: int
    output_cols: int
