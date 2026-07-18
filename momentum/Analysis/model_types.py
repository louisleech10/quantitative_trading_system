"""Shared model training dataclasses for Phase 3 analyzers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import numpy as np


__all__ = [
    "ModelPerformance",
    "FeatureImportance",
    "OOTValidationResult",
    "PRMetrics",
    "PrecisionAtKResult",
    "PredictionOutput",
    "PermutationImportanceResult",
    "FoldImportanceStabilityResult",
    "GlobalSHAPResult",
    "SingleCaseSHAPResult",
    "ComparisonReport",
]


@dataclass
class ModelPerformance:
    """模型效能指標（LightGBM 和 XGBoost 共用）

    LA-2 B2：train_auc → in_sample_train_auc（不並存）；
    fit_pool_auc = ES train∪val 池化 AUC（in_sample_research_only）；
    cal/PR/Brier/ECE scope = cv_oof（OOF 預測，非 in-sample）。
    """

    in_sample_train_auc: float
    cv_auc_mean: float
    cv_auc_std: float
    precision: float
    recall: float
    f1_score: float
    overfitting_score: float  # in_sample_train_auc - cv_auc_mean
    brier_score: Optional[float] = None
    ece: Optional[float] = None
    calibration_quality: Optional[str] = None
    pr_auc: Optional[float] = None
    positive_rate: Optional[float] = None
    engine_type: Optional[str] = None
    training_time_seconds: Optional[float] = None
    n_estimators_actual: Optional[int] = None
    fit_pool_auc: Optional[float] = None
    # 欄位級 eval_scope（§0.6-C）；序列化時一併輸出
    eval_scope: Optional[Dict[str, str]] = None
    # 缺 held-out 時 OOT 相關欄位標記 OMITTED
    oot_auc: Optional[float] = None
    oot_status: Optional[str] = None  # "ok" | "OMITTED" | None


@dataclass
class FeatureImportance:
    feature_name: str
    importance: float
    rank: int


@dataclass
class OOTValidationResult:
    oot_auc: Optional[float]
    cv_oot_gap: Optional[float]
    gap_status: str
    n_samples: int


@dataclass
class PRMetrics:
    pr_auc: float
    precision_curve: List[float]
    recall_curve: List[float]
    thresholds: List[float]


@dataclass
class PrecisionAtKResult:
    k: int
    precision: float
    n_positive: int
    n_total: int


@dataclass
class PredictionOutput:
    case_ids: Optional[List[str]]
    y_true: Optional[np.ndarray]
    y_pred_proba: np.ndarray
    y_pred_label: np.ndarray


@dataclass
class PermutationImportanceResult:
    feature_name: str
    importance_mean: float
    importance_std: float


@dataclass
class FoldImportanceStabilityResult:
    feature_name: str
    mean_importance: float
    std_importance: float
    cv_coefficient: float


@dataclass
class GlobalSHAPResult:
    shap_values: np.ndarray
    feature_names: List[str]
    mean_abs_shap: Dict[str, float]


@dataclass
class SingleCaseSHAPResult:
    case_id: Optional[str]
    shap_values: np.ndarray
    feature_names: List[str]
    base_value: float
    prediction: float


@dataclass
class ComparisonReport:
    """雙引擎對比報告（model_comparison.py 使用）"""

    engine_performances: Dict[str, ModelPerformance]
    auc_comparison: Dict[str, float]
    consensus_rate: float
    feature_rank_correlation: float
    recommended_engine: str
    recommendation_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_performances": {
                engine: asdict(performance)
                for engine, performance in self.engine_performances.items()
            },
            "auc_comparison": self.auc_comparison,
            "consensus_rate": self.consensus_rate,
            "feature_rank_correlation": self.feature_rank_correlation,
            "recommended_engine": self.recommended_engine,
            "recommendation_reason": self.recommendation_reason,
        }
