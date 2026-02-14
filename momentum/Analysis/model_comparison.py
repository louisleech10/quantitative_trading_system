"""Model comparison engine for multi-trainer A/B analysis (Task 3.5)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from momentum.Analysis.model_types import ComparisonReport, ModelPerformance
from momentum.core.logging import get_logger
from momentum.core.protocols import IModelTrainer

logger = get_logger(__name__)


class ModelComparison:
    """雙引擎（或多引擎）A/B 對比引擎。"""

    def __init__(self, trainers: Dict[str, IModelTrainer]):
        if not trainers:
            raise ValueError("至少需要一個 trainer")
        self.trainers = trainers
        self._performances: Dict[str, ModelPerformance] = {}
        self._probabilities: Dict[str, np.ndarray] = {}
        self._feature_importances: Dict[str, List[Any]] = {}

    def train_all(
        self,
        X: Any,
        y: Any,
        feature_names: Any,
        **kwargs: Any,
    ) -> Dict[str, ModelPerformance]:
        performances: Dict[str, ModelPerformance] = {}
        probabilities: Dict[str, np.ndarray] = {}
        importances: Dict[str, List[Any]] = {}

        for engine_name, trainer in self.trainers.items():
            logger.info(f"開始訓練引擎: {engine_name}")
            try:
                performance = trainer.train_model(X, y, feature_names=feature_names, **kwargs)
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(f"引擎訓練失敗: {engine_name}") from exc
            performances[engine_name] = performance

            proba = self._extract_positive_proba(trainer.predict_proba(X))
            probabilities[engine_name] = proba

            try:
                importances[engine_name] = trainer.get_feature_importance(method="gain")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"引擎 {engine_name} 無法取得特徵重要性: {exc}")
                importances[engine_name] = []

        self._performances = performances
        self._probabilities = probabilities
        self._feature_importances = importances
        return performances

    def compare(self) -> ComparisonReport:
        if not self._performances:
            raise ValueError("尚未執行 train_all()")

        auc_comparison = {
            engine: float(perf.cv_auc_mean)
            for engine, perf in self._performances.items()
        }
        recommended_engine = max(auc_comparison, key=auc_comparison.get)
        recommendation_reason = (
            f"{recommended_engine} 的 CV AUC 最佳 ({auc_comparison[recommended_engine]:.4f})"
        )

        return ComparisonReport(
            engine_performances=self._performances,
            auc_comparison=auc_comparison,
            consensus_rate=self._compute_consensus_rate(),
            feature_rank_correlation=self._compute_feature_rank_correlation(),
            recommended_engine=recommended_engine,
            recommendation_reason=recommendation_reason,
        )

    def consensus_predictions(
        self,
        X: Any,
        method: str = "soft_voting",
        threshold: float = 0.5,
    ) -> np.ndarray:
        if not 0 <= threshold <= 1:
            raise ValueError("threshold 必須在 0 到 1 之間")

        probabilities = np.vstack(
            [self._extract_positive_proba(trainer.predict_proba(X)) for trainer in self.trainers.values()]
        )

        if method == "soft_voting":
            mean_proba = probabilities.mean(axis=0)
            return (mean_proba >= threshold).astype(int)

        if method == "hard_voting":
            votes = (probabilities >= threshold).astype(int)
            needed = int(np.ceil(votes.shape[0] / 2))
            return (votes.sum(axis=0) >= needed).astype(int)

        if method == "min_confidence":
            predictions = np.full(probabilities.shape[1], -1, dtype=int)
            positive_mask = np.all(probabilities >= threshold, axis=0)
            negative_mask = np.all(probabilities < threshold, axis=0)
            predictions[positive_mask] = 1
            predictions[negative_mask] = 0
            return predictions

        raise ValueError("method 僅支援 soft_voting / hard_voting / min_confidence")

    def _compute_consensus_rate(self) -> float:
        if not self._probabilities:
            return 0.0
        if len(self._probabilities) == 1:
            return 1.0

        label_matrix = np.vstack([
            (proba >= 0.5).astype(int)
            for proba in self._probabilities.values()
        ])
        consensus_mask = np.all(label_matrix == label_matrix[0], axis=0)
        return float(np.mean(consensus_mask))

    def _compute_feature_rank_correlation(self) -> float:
        if len(self._feature_importances) <= 1:
            return 1.0

        engine_names = sorted(self._feature_importances.keys())
        pairwise_scores: List[float] = []

        for i in range(len(engine_names)):
            for j in range(i + 1, len(engine_names)):
                left_rank = self._build_rank_map(self._feature_importances[engine_names[i]])
                right_rank = self._build_rank_map(self._feature_importances[engine_names[j]])

                common_features = sorted(set(left_rank.keys()) & set(right_rank.keys()))
                if len(common_features) < 2:
                    continue

                left_series = pd.Series([left_rank[name] for name in common_features], dtype=float)
                right_series = pd.Series([right_rank[name] for name in common_features], dtype=float)
                corr = float(left_series.corr(right_series, method="spearman"))
                if not np.isnan(corr):
                    pairwise_scores.append(corr)

        if not pairwise_scores:
            return 0.0
        return float(np.mean(pairwise_scores))

    def _build_rank_map(self, importance_items: List[Any]) -> Dict[str, float]:
        rank_map: Dict[str, float] = {}
        for index, item in enumerate(importance_items):
            feature_name = self._extract_feature_name(item)
            if feature_name is None:
                continue
            rank = float(getattr(item, "rank", index + 1))
            rank_map[feature_name] = rank
        return rank_map

    def _extract_feature_name(self, item: Any) -> Optional[str]:
        for attr_name in ("feature_name", "feature"):
            value = getattr(item, attr_name, None)
            if isinstance(value, str) and value:
                return value
        return None

    def _extract_positive_proba(self, proba: Any) -> np.ndarray:
        array = np.asarray(proba)
        if array.ndim == 2 and array.shape[1] >= 2:
            return array[:, 1]
        if array.ndim == 1:
            return array
        raise ValueError("predict_proba 回傳格式錯誤")