"""Pydantic models for Feature Browser API.

僅保留跨 Symbol Coverage Matrix 所需模型；其餘骨架期占位端點
（IC / SHAP / 重要度 / quality-scorecard 等）已隨頁面併入 Feature
Factory 而移除。

ICPERF Task 0.6 (h) ⑦／③（L1c）：三個計算端點改背景任務——請求不再帶請求逾時欄（無時間上限，
extra="forbid" 使舊欄 422），POST 回 task id；狀態、取消與結果另由任務端點提供；Group Feature 結果
以 offset／limit 自同一任務之完整結果快照分頁（不再有 top_n 上界）。結果形狀見各 *Response 模型。
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class CoverageMatrixRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbols: List[str] = Field(..., min_length=1)
    timeframe: str
    feature_names: List[str] = Field(default_factory=list)
    feature_base_path: str = "data_cache/features"


class CoverageMatrixSummary(BaseModel):
    avg_coverage: float
    worst_symbol: Optional[str] = None
    worst_feature: Optional[str] = None


class CoverageMatrixResponse(BaseModel):
    matrix: Dict[str, Dict[str, Optional[float]]]
    valid_counts: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    row_counts: Dict[str, int] = Field(default_factory=dict)
    symbols: List[str]
    features: List[str]
    summary: CoverageMatrixSummary


class GroupCoverageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbols: List[str] = Field(..., min_length=1)
    timeframe: str
    feature_base_path: str = "data_cache/features"


class GroupCoverageSummary(BaseModel):
    avg_coverage: float
    worst_symbol: Optional[str] = None
    worst_group: Optional[str] = None
    missing_symbols: List[str] = Field(default_factory=list)


class GroupCoverageResponse(BaseModel):
    groups: List[str]
    symbols: List[str]
    matrix: Dict[str, Dict[str, Optional[float]]]
    divergence: Dict[str, float] = Field(default_factory=dict)
    summary: GroupCoverageSummary


class GroupFeatureCoverageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbols: List[str] = Field(..., min_length=1)
    timeframe: str
    group_name: str
    feature_base_path: str = "data_cache/features"


class GroupFeatureCoverageResponse(BaseModel):
    """Group Feature 結果頁：`features`／`matrix`／`divergence` 為 [offset, offset+limit) 之切片，`total` 為截斷前特徵數。"""

    group_name: str
    features: List[str]
    symbols: List[str]
    matrix: Dict[str, Dict[str, Optional[float]]]
    divergence: Dict[str, float] = Field(default_factory=dict)
    row_counts: Dict[str, int] = Field(default_factory=dict)
    total: int
    offset: int
    limit: int


class CoverageTaskCreatedResponse(BaseModel):
    task_id: str


class CoverageTaskProgress(BaseModel):
    phase: str
    processed: int
    total: int
    updated_at: str


class CoverageTaskStatusResponse(BaseModel):
    """任務狀態：只含狀態、進度與摘要（完整結果由結果端點讀取）。"""

    task_id: str
    kind: str
    state: Literal["queued", "running", "cancelling", "completed", "failed", "cancelled", "interrupted"]
    progress: CoverageTaskProgress
    error: Optional[str] = None
    created_at: str
    summary: Optional[Dict[str, Any]] = None


class CoverageTaskCancelResponse(BaseModel):
    task_id: str
    cancel: Literal["cancelling", "cancelled", "already_terminal"]
