"""Rolling AUC tracker for model drift detection."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from momentum.core.logging import get_logger

logger = get_logger(__name__)


class RollingAUCTracker:
    """滾動窗口 AUC — 檢測模型時效性"""

    def compute(
        self,
        model: Any,
        X: pd.DataFrame,
        y: pd.Series,
        window: int = 200,
        stride: int = 50,
    ) -> dict:
        """
        Returns: {"timestamps": [...], "auc_values": [...],
                  "trend": "stable"|"declining"|"improving"}
        """

        if window < 2:
            raise ValueError("window 必須 >= 2")
        if stride < 1:
            raise ValueError("stride 必須 >= 1")
        if len(X) != len(y):
            raise ValueError("X 與 y 長度不一致")

        timestamps: List[Any] = []
        auc_values: List[float] = []

        for start in range(0, len(X) - window + 1, stride):
            end = start + window
            X_slice = X.iloc[start:end]
            y_slice = y.iloc[start:end]
            if y_slice.nunique() < 2:
                auc_values.append(np.nan)
                timestamps.append(self._extract_timestamp(X_slice))
                continue

            scores = self._predict_scores(model, X_slice)
            try:
                auc = float(roc_auc_score(y_slice, scores))
            except ValueError:
                auc = np.nan
            auc_values.append(auc)
            timestamps.append(self._extract_timestamp(X_slice))

        trend = self._detect_trend(auc_values)

        return {
            "timestamps": timestamps,
            "auc_values": auc_values,
            "trend": trend,
        }

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

    def _detect_trend(self, auc_values: List[float]) -> str:
        values = np.array([v for v in auc_values if np.isfinite(v)], dtype=float)
        if values.size < 2:
            return "stable"
        x = np.arange(values.size)
        slope = np.polyfit(x, values, 1)[0]
        if slope > 0.001:
            return "improving"
        if slope < -0.001:
            return "declining"
        return "stable"

    def _extract_timestamp(self, X_slice: pd.DataFrame) -> Any:
        if isinstance(X_slice.index, pd.DatetimeIndex):
            return X_slice.index[-1]
        if "timestamp" in X_slice.columns:
            return X_slice["timestamp"].iloc[-1]
        return int(X_slice.index[-1])
