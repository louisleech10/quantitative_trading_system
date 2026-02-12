"""Cross-validation validator for time series models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, List, Tuple

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import roc_auc_score, precision_recall_fscore_support
from sklearn.model_selection import TimeSeriesSplit

from momentum.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OOTResult:
    """Out-of-time evaluation results."""

    auc: float
    precision: float
    recall: float
    f1: float
    n_samples: int

    def to_dict(self) -> dict:
        return {
            "auc": self.auc,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "n_samples": self.n_samples,
        }


class CVValidator:
    """交叉驗證器 — Time-Series Split + Fold AUC 記錄"""

    def __init__(self, config: Optional[dict] = None):
        config = config or {}
        self._n_splits = int(config.get("n_splits", 5))
        self._oot_ratio = float(config.get("oot_ratio", 0.2))
        self._oot_result: Optional[OOTResult] = None

    def validate(
        self,
        model: Any,
        X: pd.DataFrame,
        y: pd.Series,
        config: Optional[dict] = None,
    ) -> dict:
        """
        完整 CV + OOT 驗證
        Returns: {
            "cv_auc_mean": float, "cv_auc_std": float,
            "fold_aucs": List[float],
            "oot_auc": float, "cv_oot_gap": float,
            "overfit_warning": bool,
            "oot_precision": float, "oot_recall": float,
            "oot_f1": float
        }
        """

        local_config = config or {}
        n_splits = int(local_config.get("n_splits", self._n_splits))
        oot_ratio = float(local_config.get("oot_ratio", self._oot_ratio))

        X_sorted, y_sorted = self._sort_by_index(X, y)
        X_cv, y_cv, X_oot, y_oot = self._split_cv_oot(
            X_sorted, y_sorted, oot_ratio
        )

        fold_aucs: List[float] = []
        for train_idx, val_idx in self._time_series_split_on_cv(X_cv, n_splits):
            fold_model = clone(model)
            X_train = X_cv.iloc[train_idx]
            y_train = y_cv.iloc[train_idx]
            X_val = X_cv.iloc[val_idx]
            y_val = y_cv.iloc[val_idx]
            fold_model.fit(X_train, y_train)
            auc_value = self._compute_auc(fold_model, X_val, y_val)
            fold_aucs.append(auc_value)

        cv_auc_mean = float(np.nanmean(fold_aucs)) if fold_aucs else np.nan
        cv_auc_std = float(np.nanstd(fold_aucs)) if fold_aucs else np.nan

        oot_eval = self._evaluate_oot(model, X_cv, y_cv, X_oot, y_oot)
        self._oot_result = oot_eval

        cv_oot_gap = cv_auc_mean - oot_eval.auc if np.isfinite(cv_auc_mean) else np.nan
        overfit_warning = bool(cv_oot_gap > 0.1) if np.isfinite(cv_oot_gap) else False

        return {
            "cv_auc_mean": cv_auc_mean,
            "cv_auc_std": cv_auc_std,
            "fold_aucs": fold_aucs,
            "oot_auc": oot_eval.auc,
            "cv_oot_gap": cv_oot_gap,
            "overfit_warning": overfit_warning,
            "oot_precision": oot_eval.precision,
            "oot_recall": oot_eval.recall,
            "oot_f1": oot_eval.f1,
        }

    def time_series_split(
        self, X: pd.DataFrame, y: pd.Series, n_splits: int = 5
    ) -> list[tuple]:
        """
        時間序列切分（非隨機 KFold）
        按時間排序，前 80% 為 CV，最後 20% 為 OOT
        """

        X_sorted, y_sorted = self._sort_by_index(X, y)
        X_cv, _, _, _ = self._split_cv_oot(X_sorted, y_sorted, self._oot_ratio)
        return list(self._time_series_split_on_cv(X_cv, n_splits))

    def get_oot_result(self) -> dict:
        """取得 OOT 驗證結果"""

        if not self._oot_result:
            return {}
        return self._oot_result.to_dict()

    def _split_cv_oot(
        self, X: pd.DataFrame, y: pd.Series, oot_ratio: float
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        if len(X) == 0:
            raise ValueError("X 為空，無法進行 CV")
        if len(X) != len(y):
            raise ValueError("X 與 y 長度不一致")
        if oot_ratio <= 0 or oot_ratio >= 1:
            raise ValueError("oot_ratio 必須在 (0, 1) 之間")

        split_idx = int(len(X) * (1 - oot_ratio))
        if split_idx < 2:
            raise ValueError("CV 樣本數不足")
        if len(X) - split_idx < 2:
            raise ValueError("OOT 樣本數不足")

        X_cv = X.iloc[:split_idx].copy()
        y_cv = y.iloc[:split_idx].copy()
        X_oot = X.iloc[split_idx:].copy()
        y_oot = y.iloc[split_idx:].copy()
        return X_cv, y_cv, X_oot, y_oot

    def _time_series_split_on_cv(
        self, X_cv: pd.DataFrame, n_splits: int
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        if n_splits < 2:
            raise ValueError("n_splits 必須 >= 2")
        if len(X_cv) <= n_splits:
            raise ValueError("CV 樣本數不足以切分")

        tscv = TimeSeriesSplit(n_splits=n_splits)
        return list(tscv.split(X_cv))

    def _sort_by_index(
        self, X: pd.DataFrame, y: pd.Series
    ) -> Tuple[pd.DataFrame, pd.Series]:
        if not isinstance(y, pd.Series):
            y = pd.Series(y, index=X.index)
        if not X.index.is_monotonic_increasing:
            X_sorted = X.sort_index()
            y_sorted = y.reindex(X_sorted.index)
        else:
            X_sorted = X
            y_sorted = y.reindex(X.index)
        return X_sorted, y_sorted

    def _compute_auc(self, model: Any, X: pd.DataFrame, y: pd.Series) -> float:
        if y.nunique() < 2:
            logger.warning("AUC 計算跳過: y 僅單一類別")
            return np.nan
        scores = self._predict_scores(model, X)
        try:
            return float(roc_auc_score(y, scores))
        except ValueError as exc:
            logger.warning("AUC 計算失敗: %s", exc)
            return np.nan

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

    def _evaluate_oot(
        self,
        model: Any,
        X_cv: pd.DataFrame,
        y_cv: pd.Series,
        X_oot: pd.DataFrame,
        y_oot: pd.Series,
    ) -> OOTResult:
        oot_model = clone(model)
        oot_model.fit(X_cv, y_cv)
        scores = self._predict_scores(oot_model, X_oot)
        auc_value = self._compute_auc(oot_model, X_oot, y_oot)

        preds = (scores >= 0.5).astype(int)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_oot, preds, average="binary", zero_division=0
        )

        return OOTResult(
            auc=float(auc_value),
            precision=float(precision),
            recall=float(recall),
            f1=float(f1),
            n_samples=int(len(y_oot)),
        )
