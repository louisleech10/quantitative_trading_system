"""
Pattern Management Models - 模式管理 Pydantic 模型

LA-2 B3：Create/Update 移除 client rules/performance/importance/case_id/metadata/status；
改帶 task_id，server 從 oot_receipt 重建。

Author: AI Agent
Date: 2026-01-10
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Dict, Optional, Literal


class FeatureCondition(BaseModel):
    """單一特徵條件（compound rule 元素）。"""
    feature: str = Field(..., description="特徵名稱")
    operator: str = Field(..., description="運算符")
    threshold: float = Field(..., description="閾值（分位值，非 confidence）")


class PatternRuleRequest(BaseModel):
    """規則請求/回應模型（server 重建用；compound feature_conditions 鎖 AND）。

    空集 feature_conditions 拒；connective 固定 AND；順序保留。
    """
    feature_conditions: List[FeatureCondition] = Field(
        ..., min_length=1, description="條件列表（AND 連接，順序保留）"
    )
    connective: Literal["AND"] = Field(default="AND", description="只允許 AND")
    description: str = Field(default="", description="中文描述")

    @field_validator("feature_conditions")
    @classmethod
    def _reject_empty(cls, v: List[FeatureCondition]) -> List[FeatureCondition]:
        if not v:
            raise ValueError("feature_conditions must be non-empty")
        return v

    @field_validator("connective")
    @classmethod
    def _and_only(cls, v: str) -> str:
        if v != "AND":
            raise ValueError("connective must be AND")
        return v


class CreatePatternRequest(BaseModel):
    """建立模式請求（server 權威：帶 task_id，禁 client rules/metrics/metadata）。"""
    name: str = Field(..., description="模式名稱")
    description: str = Field(..., description="模式描述")
    task_id: str = Field(..., description="來源 XGBoost/batch 任務 ID（lookup oot_receipt）")
    tags: Optional[List[str]] = Field(default=None, description="標籤")

    # B3-F5：extra=forbid → 偽造 rules/status/metadata/performance_metrics → 422
    model_config = ConfigDict(extra="forbid")


class UpdatePatternRequest(BaseModel):
    """更新模式請求（禁 client status/metadata；status 由 server 依 receipt 推導）。"""
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    # 可選：重新綁定 task 以 re-verify OOT（晉升 active）
    task_id: Optional[str] = Field(
        default=None, description="可選 task_id 以 re-verify OOT receipt"
    )

    # B3-F5：extra=forbid → 偽造 status/metadata/rules → 422
    model_config = ConfigDict(extra="forbid")


class PatternRuleResponse(BaseModel):
    """規則回應模型"""
    feature: str
    operator: str
    threshold: float
    description: str
    feature_conditions: Optional[List[FeatureCondition]] = None
    connective: Literal["AND"] = "AND"


class PatternResponse(BaseModel):
    """模式回應模型"""
    pattern_id: str
    name: str
    description: str
    rules: List[PatternRuleResponse]
    case_id: str
    xgboost_importance: Dict[str, float]
    performance_metrics: Dict[str, float]
    created_at: str
    updated_at: str
    status: str
    tags: List[str]
    metadata: Dict


class PatternListResponse(BaseModel):
    """模式列表回應"""
    success: bool
    count: int
    patterns: List[PatternResponse]


class PatternSummaryResponse(BaseModel):
    """模式摘要回應"""
    pattern_id: str
    name: str
    description: str
    rule_count: int
    rule_condition: str
    case_id: str
    performance_metrics: Dict[str, float]
    status: str
    tags: List[str]
    created_at: str
    updated_at: str


class PatternStatisticsResponse(BaseModel):
    """模式統計回應"""
    total: int
    active: int
    archived: int
    testing: int
    avg_rules_per_pattern: float
    top_tags: List[tuple]
