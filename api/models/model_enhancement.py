"""Model enhancement API request/response models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelEnhancementBaseRequest(BaseModel):
    """所有 M1-M6 Request 共用欄位。"""

    model_task_id: str = Field(..., description="已訓練模型的 task_id")
    symbol: Optional[str] = None
    timeframe: Optional[str] = None


class CalibrateRequest(ModelEnhancementBaseRequest):
    method: str = Field(default="auto", pattern="^(auto|platt|isotonic|beta|venn_abers)$")
    cv: int = Field(default=5, ge=2, le=10)


class WalkForwardRequest(ModelEnhancementBaseRequest):
    mode: str = Field(default="rolling", pattern="^(rolling|expanding|both)$")
    train_size: int = Field(default=500, ge=100, le=50000)
    test_size: int = Field(default=100, ge=20, le=10000)
    step_size: Optional[int] = None
    purge_gap: int = Field(default=5, ge=0, le=50)
    embargo_pct: float = Field(default=0.01, ge=0.0, le=0.1)


class SampleWeightRequest(ModelEnhancementBaseRequest):
    strategies: List[str] = Field(default_factory=lambda: ["time_decay", "class_balance"])
    combination: str = Field(default="multiply", pattern="^(multiply|additive)$")
    time_decay_half_life: int = Field(default=180, ge=10, le=3650)


class AdversarialValidateRequest(ModelEnhancementBaseRequest):
    n_estimators: int = Field(default=100, ge=10, le=1000)
    include_feature_tests: bool = True
    include_leakage_detection: bool = True


class CPCVRequest(ModelEnhancementBaseRequest):
    n_groups: int = Field(default=6, ge=3, le=20)
    n_test_groups: int = Field(default=2, ge=1, le=5)
    max_paths: Optional[int] = Field(default=50, ge=1, le=200)


class LearningCurveRequest(ModelEnhancementBaseRequest):
    train_fractions: List[float] = Field(default_factory=lambda: [0.1, 0.2, 0.4, 0.6, 0.8, 1.0])
    feature_counts: Optional[List[int]] = None
    ranking_method: str = Field(default="gain", pattern="^(gain|weight|cover|shap)$")


class FullEnhancementRequest(ModelEnhancementBaseRequest):
    modules: List[str] = Field(
        default_factory=lambda: [
            "calibration",
            "walk_forward",
            "sample_weight",
            "adversarial",
            "cpcv",
            "learning_curve",
        ]
    )
    config_overrides: Optional[Dict[str, Any]] = None


class ModelEnhancementResponse(BaseModel):
    task_id: str
    status: str = Field(pattern="^(running|completed|failed|skipped)$")
    module: str
    result: Optional[Dict[str, Any]] = None
    skipped_reason: Optional[str] = None
    execution_time_seconds: Optional[float] = None
    created_at: str


class FullEnhancementResponse(BaseModel):
    task_id: str
    status: str
    modules: Dict[str, ModelEnhancementResponse]
    total_execution_time_seconds: float
