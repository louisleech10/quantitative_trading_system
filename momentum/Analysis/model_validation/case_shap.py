"""SHAP explanation helpers for single cases and batches."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger

logger = get_logger(__name__)


class CaseSHAPExplainer:
    """單案例 SHAP 解釋"""

    def _load_shap(self):
        try:
            import shap  # type: ignore
            return shap
        except Exception as exc:
            raise ImportError("缺少相依套件 shap，請先安裝：pip install shap") from exc

    def explain_single(
        self, model: Any, X_single: pd.DataFrame, feature_names: List[str]
    ) -> dict:
        """
        單筆預測的 SHAP 解釋
        Returns: {"base_value": float, "shap_values": {feature: value},
                  "prediction": float}
        """

        if isinstance(X_single, pd.Series):
            X_single = X_single.to_frame().T

        if len(X_single) != 1:
            raise ValueError("X_single 必須只有一筆資料")

        X_single = X_single.reindex(columns=feature_names)
        if X_single.isna().any().any():
            missing = X_single.columns[X_single.isna().any()].tolist()
            raise ValueError(f"X_single 缺少特徵: {missing}")

        shap = self._load_shap()
        explainer = shap.Explainer(model, X_single)
        shap_values = explainer(X_single)

        base_value = float(np.array(shap_values.base_values).reshape(-1)[0])
        values = np.array(shap_values.values)[0]
        shap_map = {name: float(val) for name, val in zip(feature_names, values)}

        prediction = float(self._predict_scores(model, X_single)[0])

        return {
            "base_value": base_value,
            "shap_values": shap_map,
            "prediction": prediction,
        }

    def explain_batch(
        self,
        model: Any,
        X: pd.DataFrame,
        feature_names: List[str],
        max_samples: int = 100,
    ) -> dict:
        """
        批次 SHAP 解釋
        Returns: {"mean_abs_shap": {feature: value}, "feature_importance_rank": [...]}
        """

        if len(X) == 0:
            return {"mean_abs_shap": {}, "feature_importance_rank": []}

        X_sample = X.head(max_samples).reindex(columns=feature_names)
        shap = self._load_shap()
        explainer = shap.Explainer(model, X_sample)
        shap_values = explainer(X_sample)

        values = np.array(shap_values.values)
        mean_abs = np.mean(np.abs(values), axis=0)
        mean_abs_map = {
            name: float(val) for name, val in zip(feature_names, mean_abs)
        }

        ranked = sorted(mean_abs_map.items(), key=lambda x: x[1], reverse=True)
        feature_importance_rank = [name for name, _ in ranked]

        return {
            "mean_abs_shap": mean_abs_map,
            "feature_importance_rank": feature_importance_rank,
        }

    def _predict_scores(self, model: Any, X: pd.DataFrame) -> np.ndarray:
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X)
            return np.asarray(proba)[:, 1]
        if hasattr(model, "decision_function"):
            scores = model.decision_function(X)
            return 1 / (1 + np.exp(-np.asarray(scores)))
        scores = model.predict(X)
        return np.asarray(scores).astype(float)
