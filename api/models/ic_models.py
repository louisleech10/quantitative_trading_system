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
    # F5.2: 單數 factor_return 預設 True(與 schema enabled flip 對齊)
    # tier 意圖見 frontend PRESET_TOGGLES(foundation=false;其餘 true)
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
    # ── GAP-3 UX Task 7.0b ③：事件批之分析時 transport ────────────────────────
    # 🔴 **不另開端點**（SPEC 之三選一裁決）：另開端點會讓 `label_value` 經前端往返一趟，
    #    前端就可能以 h=3 取得值卻以 h=7 送出分析 ⇒ purge 與 label 分屬不同 h。
    #    §D-3′-a（iii）之五階段**必須在同一次分析內原子完成**，跨請求即無法保證。
    event_import_id: Optional[str] = Field(
        None,
        description="GAP-3 事件批 id；給定時走事件分析分支（後端自行查出該批已落檔 records）",
    )
    event_label_spec: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "GAP-3 分析參數，欄集恰四鍵 "
            "{horizon_bars, entry_price_semantic, label_return_mode, decision_offset_bars}；"
            "只作用於本次分析，**不回寫**事件批"
        ),
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

    @model_validator(mode="after")
    def _gap3_event_transport_invariants(self) -> "ICAnalyzeRequest":
        """GAP-3 UX Task 7.0b ③ 之兩條 transport 不變式。

        ① `event_label_spec` 存在而 `event_import_id` 缺 ⇒ 400（SPEC 驗收 ⑪）。
           理由：spec 是「對哪一批做什麼分析」的後半，沒有前半就沒有意義；
           放行的話會靜默套到某個**預設批**上，而使用者以為自己指定了。
        ② `event_import_id` 與 `event_timestamps` **互斥** ⇒ 同時給 400（SPEC L3370）。
           理由：兩者都在說「要分析哪些事件」，同時給就有兩個真相源。
           legacy 非事件呼叫端只帶 `event_timestamps`、不帶 `event_import_id`，**行為不變**。
        """
        if self.event_label_spec is not None and self.event_import_id is None:
            raise ValueError(
                "event_label_spec 需搭配 event_import_id（GAP-3 Task 7.0b ③）"
                "——只給分析參數而不說對哪一批，會靜默套到預設批上"
            )
        if self.event_import_id is not None and self.event_timestamps:
            raise ValueError(
                "event_import_id 與 event_timestamps 不得同時給定（GAP-3 Task 7.0b）"
                "——兩者都在指定要分析哪些事件，同時給就有兩個真相源"
            )
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
    # LA-1 B3：completed 時可帶 root 紅標（optional，舊 client 相容）
    analysis_status: Optional[str] = None
    oos_guarantees: Optional[bool] = None
    # GAP-3 UX Task 6.3：這個 run 有幾個特徵。
    # 🔴 **必須在此宣告**，否則 service 塞了值也會被 `response_model` 靜默濾掉、前端永遠看不到
    #    （本 epic §4.2 之假綠實例第 5 條）。
    # 🔴 `current_stage` 為**可擴充集合**，不是固定 enum：GAP-6 之分塊計算會細分更多階段，
    #    測試不得以窮舉相等斷言鎖死（改測試是掩蓋行為變更的常見路徑）。
    feature_count: Optional[int] = None


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
    # LA-1 B3 oracle ⑤：transforms carrier 紅標（與 report root 同源）
    analysis_status: Optional[str] = Field(
        default=None,
        description="ok_oos | degraded_full_sample；degraded 時輸出僅 research-only",
    )
    oos_guarantees: Optional[bool] = Field(
        default=None,
        description="root 鏡像；False 表示無 OOS 保證",
    )
