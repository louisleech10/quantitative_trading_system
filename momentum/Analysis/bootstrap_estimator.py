"""
Bootstrap Estimator - 信賴區間估計

Author: AI Agent
Date: 2026-01-29
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional

import numpy as np
from sklearn.metrics import roc_auc_score, precision_recall_curve, auc, brier_score_loss

from momentum.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BootstrapResult:
    """Bootstrap 信賴區間結果"""
    metric: str
    point_estimate: float
    ci_lower: float
    ci_upper: float
    confidence_level: float
    n_bootstrap: int

    def to_dict(self) -> Dict:
        return {
            "metric": self.metric,
            "point_estimate": self.point_estimate,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "confidence_level": self.confidence_level,
            "n_bootstrap": self.n_bootstrap
        }


class BootstrapEstimator:
    """Bootstrap 估計器"""

    def _get_metric_func(self, metric: str) -> Callable[[np.ndarray, np.ndarray], float]:
        if metric == "auc":
            return self._auc_metric
        if metric == "pr_auc":
            return self._pr_auc_metric
        if metric == "brier":
            return self._brier_metric
        if metric == "precision_at_10":
            return self._precision_at_10_metric
        raise ValueError("不支援的 metric，請使用 'auc'/'pr_auc'/'brier'/'precision_at_10'")

    def bootstrap_confidence_interval(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        metric: str = "auc",
        n_bootstrap: int = 1000,
        confidence: float = 0.95,
        random_state: int = 42
    ) -> BootstrapResult:
        """
        計算信賴區間
        """
        if len(y_true) == 0:
            raise ValueError("y_true 為空")
        if len(y_true) != len(y_pred_proba):
            raise ValueError("y_true 與 y_pred_proba 長度不一致")
        if n_bootstrap <= 0:
            raise ValueError("n_bootstrap 必須大於 0")
        if confidence <= 0 or confidence >= 1:
            raise ValueError("confidence 必須在 (0, 1) 之間")

        metric_func = self._get_metric_func(metric)
        rng = np.random.default_rng(random_state)

        point_estimate = metric_func(y_true, y_pred_proba)
        scores = []

        n_samples = len(y_true)
        for _ in range(n_bootstrap):
            indices = rng.integers(0, n_samples, n_samples)
            y_true_sample = y_true[indices]
            y_pred_sample = y_pred_proba[indices]
            score = metric_func(y_true_sample, y_pred_sample)
            if not np.isnan(score):
                scores.append(score)

        if len(scores) == 0:
            raise ValueError("所有 bootstrap 樣本無法計算指標")

        alpha = (1 - confidence) / 2
        ci_lower = float(np.quantile(scores, alpha))
        ci_upper = float(np.quantile(scores, 1 - alpha))

        logger.info(
            f"Bootstrap 完成 - metric={metric}, point={point_estimate:.4f}, "
            f"CI=({ci_lower:.4f}, {ci_upper:.4f})"
        )

        return BootstrapResult(
            metric=metric,
            point_estimate=float(point_estimate),
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            confidence_level=confidence,
            n_bootstrap=n_bootstrap
        )

    def _auc_metric(self, y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
        if len(np.unique(y_true)) < 2:
            return float("nan")
        return float(roc_auc_score(y_true, y_pred_proba))

    def _pr_auc_metric(self, y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
        precision, recall, _ = precision_recall_curve(y_true, y_pred_proba)
        return float(auc(recall, precision))

    def _brier_metric(self, y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
        return float(brier_score_loss(y_true, y_pred_proba))

    def _precision_at_10_metric(self, y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
        if len(y_true) == 0:
            return float("nan")
        n_top = max(1, int(len(y_true) * 0.10))
        top_indices = np.argsort(y_pred_proba)[-n_top:]
        return float(np.mean(y_true[top_indices]))
