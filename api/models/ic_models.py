"""IC analysis API models."""

from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, Field


class FeatureFilterConfig(BaseModel):
    include_features: Optional[List[str]] = None
    exclude_features: Optional[List[str]] = None
    include_pattern: Optional[str] = None
    include_categories: Optional[List[str]] = None
    include_data_sources: Optional[List[str]] = None
    include_families: Optional[List[str]] = None
    max_features: Optional[int] = Field(default=None, ge=1)


class DeepAnalysisModules(BaseModel):
    factor_return: bool = True
    factor_centrality: bool = True
    trend_analysis: bool = True
    parameter_sensitivity: bool = True
    rolling_oos: bool = True
    factor_orthogonalization: bool = False
    factor_exposure: bool = False
    long_short_analysis: bool = True
    feature_quality_diagnostics: bool = True
    net_ic_analysis: bool = True


class DeepAnalysisRequest(BaseModel):
    selected_features: Optional[List[str]] = None
    top_n: int = Field(default=30, ge=1, le=200)
    modules: DeepAnalysisModules = Field(default_factory=DeepAnalysisModules)
    config_override: Optional[Dict[str, Any]] = None


class FeatureTierRequest(BaseModel):
    active_preset: Literal["foundation", "intermediate", "advanced", "custom"] = Field(default="intermediate")
    presets: Optional[Dict[str, Any]] = None
    custom_overrides: Optional[Dict[str, Dict[str, bool]]] = None


class ICAnalyzeRequest(BaseModel):
    features_path: Optional[str] = Field(None, description="Path to features HDF5 (deprecated, optional)")
    symbol: Optional[str] = Field(None, description="Feature Library symbol")
    symbols: Optional[List[str]] = Field(None, description="Feature Library symbols for cross-sectional mode")
    timeframe: Optional[str] = Field(None, description="Feature Library timeframe")
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
