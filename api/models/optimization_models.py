"""Phase 4.3 optimization API models."""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class ExecutionOptimizationRequest(BaseModel):
    """策略執行優化請求。"""

    model_predictions_path: str = Field(..., description="model_predictions_{task_id}.csv")
    target_metric: Literal[
        "expectancy",
        "sharpe_ratio",
        "sortino_ratio",
        "calmar_ratio",
        "sqn",
    ] = "expectancy"
    n_trials: int = Field(default=100, ge=1, le=10000)
    timeout_seconds: int = Field(default=300, ge=1)
    search_space_override: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, float]] = None
    backtest_config: Optional[Dict[str, Any]] = None
    multi_objective: bool = False


class ExecutionOptimizationResponse(BaseModel):
    task_id: str
    status: str
    created_at: str


class HyperparamOptimizationRequest(BaseModel):
    """模型超參數優化請求。"""

    model_type: Literal["lightgbm", "xgboost"] = "lightgbm"
    features_path: str
    labels_path: str
    n_trials: int = Field(default=100, ge=1, le=10000)
    timeout_seconds: int = Field(default=1800, ge=1)
    search_space_override: Optional[Dict[str, Any]] = None
    max_train_val_gap: float = Field(default=0.1, ge=0.0)
    cv_folds: int = Field(default=5, ge=2, le=20)


class HyperparamOptimizationResponse(BaseModel):
    task_id: str
    status: str
    created_at: str


class OptimizationResultResponse(BaseModel):
    task_id: str
    task_type: str
    status: str
    best_trial: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    parameter_importance: Optional[Dict[str, Any]] = None


class OptimizationConfigResponse(BaseModel):
    execution: Dict[str, Any]
    hyperparameter: Dict[str, Any]


class OptimizationExportRequest(BaseModel):
    format: Literal["json", "csv", "html", "charts", "full"] = "json"
