"""
Pattern Management Models - 模式管理 Pydantic 模型

Author: AI Agent
Date: 2026-01-10
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class PatternRuleRequest(BaseModel):
    """規則請求模型"""
    feature: str = Field(..., description="特徵名稱")
    operator: str = Field(..., description="運算符")
    threshold: float = Field(..., description="閾值")
    description: str = Field(..., description="中文描述")


class CreatePatternRequest(BaseModel):
    """建立模式請求"""
    name: str = Field(..., description="模式名稱")
    description: str = Field(..., description="模式描述")
    rules: List[PatternRuleRequest] = Field(..., description="規則列表")
    case_id: str = Field(..., description="來源案例 ID")
    xgboost_importance: Dict[str, float] = Field(..., description="XGBoost 特徵重要性")
    performance_metrics: Dict[str, float] = Field(..., description="效能指標")
    tags: Optional[List[str]] = Field(default=None, description="標籤")
    metadata: Optional[Dict] = Field(default=None, description="元數據")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "EMA順勢+成交量確認模式",
                "description": "EMA三線順勢排列，且主動買入比例超過60%",
                "rules": [
                    {
                        "feature": "ema_distance_5_20",
                        "operator": ">",
                        "threshold": 0.02,
                        "description": "EMA5 高於 EMA20 2%以上"
                    }
                ],
                "case_id": "case_20260110_123456",
                "xgboost_importance": {
                    "ema_distance_5_20": 0.25,
                    "taker_buy_ratio": 0.18
                },
                "performance_metrics": {
                    "precision": 0.72,
                    "recall": 0.68,
                    "f1_score": 0.70
                },
                "tags": ["趨勢", "成交量"]
            }
        }


class UpdatePatternRequest(BaseModel):
    """更新模式請求"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict] = None


class PatternRuleResponse(BaseModel):
    """規則回應模型"""
    feature: str
    operator: str
    threshold: float
    description: str


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
