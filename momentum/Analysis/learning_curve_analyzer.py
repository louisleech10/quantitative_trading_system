"""Learning curve analyzer module."""

from __future__ import annotations

from typing import List, Dict, Optional, Any, Callable

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

from pydantic import BaseModel, Field

from momentum.core.logging import get_logger


class LearningCurveConfig(BaseModel):
    enabled: bool = True
    cv: int = Field(default=5, ge=2, le=10)
    metric: str = Field(default="auc", pattern="^(auc|brier|precision_at_k)$")
    train_fractions: List[float] = Field(default_factory=lambda: [0.1, 0.2, 0.4, 0.6, 0.8, 1.0])
    ranking_method: str = Field(default="gain", pattern="^(gain|weight|cover|shap)$")


class LearningCurveAnalyzer:
    """Learning Curve 分析器。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = LearningCurveConfig(**(config or {}))
        self.logger = get_logger(__name__)

    def analyze_data_curve(
        self,
        model_factory: Callable[[], Any],
        X: pd.DataFrame,
        y: np.ndarray,
        feature_names: List[str],
        train_fractions: List[float] = [0.1, 0.2, 0.4, 0.6, 0.8, 1.0],
    ) -> Dict[str, Any]:
        if any(frac <= 0 for frac in train_fractions):
            raise ValueError("train_fractions 不可包含 0 或負數")

        y_arr = np.asarray(y)
        n_samples = len(X)
        fractions_used: List[float] = []
        train_scores: List[float] = []
        cv_scores: List[float] = []
        cv_stds: List[float] = []

        if n_samples < 200:
            self.logger.warning("LearningCurveAnalyzer: n_samples < 200，結果僅供參考")

        for frac in sorted(set(train_fractions)):
            train_n = int(n_samples * frac)
            if train_n < 20:
                self.logger.warning(f"LearningCurveAnalyzer: fraction={frac} 樣本 < 20，跳過")
                continue

            X_sub = X.iloc[:train_n]
            y_sub = y_arr[:train_n]
            if np.unique(y_sub).size < 2:
                continue

            model = model_factory()
            model.fit(X_sub, y_sub)
            train_pred = self._predict_scores(model, X_sub)
            train_auc = float(roc_auc_score(y_sub, train_pred))

            fold_scores = self._time_series_cv_auc(model_factory, X_sub, y_sub)
            fold_scores = [score for score in fold_scores if score is not None and not np.isnan(score)]
            if not fold_scores:
                self.logger.warning(f"LearningCurveAnalyzer: fraction={frac} 無有效 fold，跳過")
                continue

            fractions_used.append(float(frac))
            train_scores.append(train_auc)
            cv_scores.append(float(np.mean(fold_scores)))
            cv_stds.append(float(np.std(fold_scores)))

        return {
            "fractions": fractions_used,
            "train_scores": train_scores,
            "cv_scores": cv_scores,
            "cv_stds": cv_stds,
            "feature_names": feature_names,
        }

    def analyze_feature_curve(
        self,
        model_factory: Callable[[], Any],
        X: pd.DataFrame,
        y: np.ndarray,
        feature_names: List[str],
        feature_counts: Optional[List[int]] = None,
        ranking_method: str = "gain",
    ) -> Dict[str, Any]:
        if ranking_method == "shap":
            try:
                import shap  # noqa: F401
            except Exception:
                self.logger.warning("LearningCurveAnalyzer: SHAP 不可用，fallback 到 gain")
                ranking_method = "gain"

        ranking = self._rank_features(X, feature_names, ranking_method)
        total_features = len(ranking)

        if feature_counts is None:
            feature_counts = [5, 10, 20, 30, 50]
        if total_features == 1:
            feature_counts = [1]

        clipped_counts = sorted(set(max(1, min(total_features, int(count))) for count in feature_counts))
        y_arr = np.asarray(y)

        curve_scores: List[float] = []
        used_counts: List[int] = []
        for count in clipped_counts:
            selected = ranking[:count]
            X_sub = X[selected]
            fold_scores = self._time_series_cv_auc(model_factory, X_sub, y_arr)
            valid = [score for score in fold_scores if score is not None and not np.isnan(score)]
            if not valid:
                continue
            used_counts.append(count)
            curve_scores.append(float(np.mean(valid)))

        if not curve_scores:
            return {
                "feature_counts": [],
                "cv_scores": [],
                "optimal_n_features": 0,
                "feature_ranking": ranking,
            }

        best_idx = int(np.argmax(curve_scores))
        return {
            "feature_counts": used_counts,
            "cv_scores": curve_scores,
            "optimal_n_features": int(used_counts[best_idx]),
            "feature_ranking": ranking,
        }

    def diagnose_bias_variance(
        self,
        train_scores: List[float],
        cv_scores: List[float],
        fractions: List[float],
    ) -> Dict[str, Any]:
        if not train_scores or not cv_scores:
            return {
                "type": "insufficient_data",
                "description": "樣本不足，無法進行偏差/變異診斷",
                "train_cv_gap": 0.0,
                "convergence": False,
                "recommendation": "增加可用資料",
            }

        train_last = float(train_scores[-1])
        cv_last = float(cv_scores[-1])
        gap = float(train_last - cv_last)

        if all(score < 0.52 for score in cv_scores):
            return {
                "type": "no_predictive_power",
                "description": "模型無預測力",
                "train_cv_gap": gap,
                "convergence": False,
                "recommendation": "重新檢查標籤與特徵工程",
            }

        if train_last < 0.60 and cv_last < 0.58 and abs(gap) < 0.05:
            return {
                "type": "high_bias",
                "description": "模型偏差高：訓練與驗證同時偏低",
                "train_cv_gap": gap,
                "convergence": True,
                "recommendation": "新增有效特徵或提高模型表達能力",
            }

        if train_last > 0.70 and gap > 0.08:
            return {
                "type": "high_variance",
                "description": "模型過擬合：訓練高、驗證低",
                "train_cv_gap": gap,
                "convergence": False,
                "recommendation": "增加資料量或提升正則化",
            }

        return {
            "type": "good_fit",
            "description": "模型擬合狀態良好",
            "train_cv_gap": gap,
            "convergence": len(fractions) >= 3,
            "recommendation": "可進入下一步回測驗證",
        }

    def full_analysis(
        self,
        model_factory: Callable[[], Any],
        X: pd.DataFrame,
        y: np.ndarray,
        feature_names: List[str],
    ) -> Dict[str, Any]:
        data_curve = self.analyze_data_curve(
            model_factory=model_factory,
            X=X,
            y=y,
            feature_names=feature_names,
            train_fractions=self.config.train_fractions,
        )
        feature_curve = self.analyze_feature_curve(
            model_factory=model_factory,
            X=X,
            y=y,
            feature_names=feature_names,
            ranking_method=self.config.ranking_method,
        )
        diagnosis = self.diagnose_bias_variance(
            train_scores=data_curve.get("train_scores", []),
            cv_scores=data_curve.get("cv_scores", []),
            fractions=data_curve.get("fractions", []),
        )

        return {
            "learning_curve": {
                "data_curve": data_curve,
                "feature_curve": feature_curve,
                "diagnosis": diagnosis,
            }
        }

    @staticmethod
    def _predict_scores(model: Any, X: pd.DataFrame) -> np.ndarray:
        if hasattr(model, "predict_proba"):
            proba = np.asarray(model.predict_proba(X))
            if proba.ndim == 2 and proba.shape[1] > 1:
                return proba[:, 1]
            return proba.reshape(-1)
        if hasattr(model, "decision_function"):
            scores = np.asarray(model.decision_function(X))
            return 1 / (1 + np.exp(-scores))
        return np.asarray(model.predict(X), dtype=float)

    def _time_series_cv_auc(
        self,
        model_factory: Callable[[], Any],
        X: pd.DataFrame,
        y: np.ndarray,
    ) -> List[Optional[float]]:
        y_arr = np.asarray(y)
        if len(X) < self.config.cv * 5:
            return [None]

        skf = StratifiedKFold(n_splits=min(self.config.cv, np.unique(y_arr, return_counts=True)[1].min()), shuffle=True, random_state=42)
        scores: List[Optional[float]] = []
        for train_idx, val_idx in skf.split(X, y_arr):
            if np.unique(y_arr[val_idx]).size < 2:
                scores.append(None)
                continue
            model = model_factory()
            model.fit(X.iloc[train_idx], y_arr[train_idx])
            pred = self._predict_scores(model, X.iloc[val_idx])
            scores.append(float(roc_auc_score(y_arr[val_idx], pred)))
        return scores

    @staticmethod
    def _rank_features(X: pd.DataFrame, feature_names: List[str], ranking_method: str) -> List[str]:
        if not feature_names:
            return X.columns.tolist()
        usable = [name for name in feature_names if name in X.columns]
        if not usable:
            usable = X.columns.tolist()

        if ranking_method in {"gain", "weight", "cover", "shap"}:
            variances = X[usable].var(axis=0).sort_values(ascending=False)
            return variances.index.tolist()
        return usable
