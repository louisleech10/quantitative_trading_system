"""Out-of-time validator for model stability."""

from __future__ import annotations

from typing import Any, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, precision_recall_fscore_support

from momentum.core.logging import get_logger

logger = get_logger(__name__)


class OOTValidator:
    """Out-of-Time 驗證 — 時間序列模型的業界標準驗證方法"""

    def __init__(self, oot_ratio: float = 0.2):
        self._oot_ratio = float(oot_ratio)

    def split_oot(self, X: pd.DataFrame, y: pd.Series) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        按時間排序切分
        Returns: (X_train, X_oot, y_train, y_oot)
        """

        X_sorted, y_sorted = self._sort_by_index(X, y)
        if self._oot_ratio <= 0 or self._oot_ratio >= 1:
            raise ValueError("oot_ratio 必須在 (0, 1) 之間")

        split_idx = int(len(X_sorted) * (1 - self._oot_ratio))
        if split_idx < 1 or split_idx >= len(X_sorted):
            raise ValueError("無法切分 OOT 資料")

        X_train = X_sorted.iloc[:split_idx].copy()
        y_train = y_sorted.iloc[:split_idx].copy()
        X_oot = X_sorted.iloc[split_idx:].copy()
        y_oot = y_sorted.iloc[split_idx:].copy()

        return X_train, X_oot, y_train, y_oot

    def evaluate(self, model: Any, X_oot: pd.DataFrame, y_oot: pd.Series) -> dict:
        """
        OOT 評估
        Returns: {"auc": float, "precision": float, "recall": float,
                  "f1": float, "n_samples": int}
        """

        scores = self._predict_scores(model, X_oot)
        auc_value = self._compute_auc(y_oot, scores)
        preds = (scores >= 0.5).astype(int)

        precision, recall, f1, _ = precision_recall_fscore_support(
            y_oot, preds, average="binary", zero_division=0
        )

        return {
            "auc": float(auc_value),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "n_samples": int(len(y_oot)),
        }

    def compute_gap(self, cv_auc: float, oot_auc: float) -> dict:
        """
        CV-OOT Gap
        Returns: {"gap": float, "overfit_warning": bool, "severity": str}
        """

        gap = float(cv_auc - oot_auc)
        if gap > 0.2:
            severity = "severe"
        elif gap > 0.1:
            severity = "warning"
        else:
            severity = "normal"
        return {
            "gap": gap,
            "overfit_warning": gap > 0.1,
            "severity": severity,
        }

    def _sort_by_index(self, X: pd.DataFrame, y: pd.Series) -> Tuple[pd.DataFrame, pd.Series]:
        if not isinstance(y, pd.Series):
            y = pd.Series(y, index=X.index)
        if not X.index.is_monotonic_increasing:
            X_sorted = X.sort_index()
            y_sorted = y.reindex(X_sorted.index)
        else:
            X_sorted = X
            y_sorted = y.reindex(X.index)
        return X_sorted, y_sorted

    def _predict_scores(self, model: Any, X: pd.DataFrame) -> np.ndarray:
        if hasattr(model, "predict_proba"):
            proba = np.asarray(model.predict_proba(X))
            if proba.ndim == 2 and proba.shape[1] > 1:
                return proba[:, 1]
            return proba.reshape(-1)
        if hasattr(model, "decision_function"):
            scores = model.decision_function(X)
            return 1 / (1 + np.exp(-np.asarray(scores)))
        scores = model.predict(X)
        return np.asarray(scores).astype(float)

    def _compute_auc(self, y_true: pd.Series, scores: np.ndarray) -> float:
        if y_true.nunique() < 2:
            logger.warning("AUC 計算跳過: y 僅單一類別")
            return np.nan
        try:
            return float(roc_auc_score(y_true, scores))
        except ValueError as exc:
            logger.warning("AUC 計算失敗: %s", exc)
            return np.nan
