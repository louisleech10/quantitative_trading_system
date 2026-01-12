"""
Pattern Analysis Models - 模式分析 Pydantic 模型

Author: AI Agent
Date: 2026-01-10
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class XGBoostAnalysisRequest(BaseModel):
    """XGBoost 分析請求"""
    case_id: str = Field(..., description="案例 ID")
    xgboost_params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="XGBoost 參數（可選）"
    )
    cv_folds: int = Field(default=5, description="交叉驗證折數")
    top_n_rules: int = Field(default=10, description="提取前 N 條規則")
    min_support: int = Field(default=10, description="最小支持度")
    
    class Config:
        json_schema_extra = {
            "example": {
                "case_id": "case_20260110_123456",
                "xgboost_params": {
                    "max_depth": 5,
                    "learning_rate": 0.05,
                    "n_estimators": 100
                },
                "cv_folds": 5,
                "top_n_rules": 10,
                "min_support": 10
            }
        }


class FeatureCondition(BaseModel):
    """特徵條件"""
    feature: str
    operator: str
    threshold: float


class DecisionRuleResponse(BaseModel):
    """決策規則回應"""
    rule_id: int
    condition: str
    support: int
    confidence: float
    lift: float
    feature_conditions: List[FeatureCondition]


class FeatureImportanceResponse(BaseModel):
    """特徵重要性回應"""
    feature: str
    importance: float
    rank: int
    method: str


class ModelPerformanceResponse(BaseModel):
    """模型效能回應"""
    train_auc: float
    cv_auc_mean: float
    cv_auc_std: float
    precision: float
    recall: float
    f1_score: float
    overfitting_score: float


class XGBoostAnalysisResult(BaseModel):
    """XGBoost 分析結果"""
    case_id: str
    model_performance: ModelPerformanceResponse
    feature_importance: List[FeatureImportanceResponse]
    decision_rules: List[DecisionRuleResponse]
    model_saved: bool
    model_path: Optional[str] = None


class XGBoostAnalysisResponse(BaseModel):
    """XGBoost 分析回應"""
    task_id: str
    message: str
    status: str  # "running", "completed", "failed"


class ModelInfoResponse(BaseModel):
    """模型資訊回應"""
    case_id: str
    feature_count: int
    feature_names: List[str]
    performance: ModelPerformanceResponse
    params: Dict[str, Any]
    saved_at: str
    metadata: Dict[str, Any]


class ModelListItem(BaseModel):
    """模型列表項目"""
    case_id: str
    file_path: str
    file_size: int
    modified_time: str
