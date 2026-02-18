"""Combinatorial Purged CV module."""

from __future__ import annotations

from itertools import combinations
from typing import Dict, Optional, Any, Iterator, Tuple, List, Callable

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from pydantic import BaseModel, Field, model_validator

from momentum.core.logging import get_logger
from momentum.core.contracts import SkippedResult


class CPCVConfig(BaseModel):
    enabled: bool = True
    n_groups: int = Field(default=6, ge=3, le=20)
    n_test_groups: int = Field(default=2, ge=1, le=5)
    purge_gap: int = Field(default=5, ge=0, le=50)
    embargo_pct: float = Field(default=0.01, ge=0.0, le=0.1)
    max_paths: Optional[int] = Field(default=50, ge=1, le=200)
    compute_backtest_paths: bool = True

    @model_validator(mode="after")
    def check_groups(self) -> "CPCVConfig":
        if self.n_test_groups >= self.n_groups:
            raise ValueError(f"n_test_groups ({self.n_test_groups}) must be < n_groups ({self.n_groups})")
        return self


class CombinatorialPurgedCV:
    """Combinatorial Purged Cross-Validation (CPCV)。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = CPCVConfig(**(config or {}))
        self.logger = get_logger(__name__)

    def split(
        self,
        X: pd.DataFrame,
        y: Optional[np.ndarray] = None,
    ) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        n_samples = len(X)
        if self.config.n_groups < 3:
            raise ValueError("n_groups 必須 >= 3")

        boundaries = self._compute_group_boundaries(n_samples)
        group_size = boundaries[0][1] - boundaries[0][0]
        if group_size < 20:
            self.logger.warning("CombinatorialPurgedCV: group 樣本數 < 20")
        if self.config.purge_gap > group_size:
            raise ValueError("purge_gap 不能大於 group_size")

        test_group_sets = list(combinations(range(self.config.n_groups), self.config.n_test_groups))
        if self.config.max_paths is not None and len(test_group_sets) > self.config.max_paths:
            rng = np.random.default_rng(42)
            selected_idx = rng.choice(len(test_group_sets), size=self.config.max_paths, replace=False)
            test_group_sets = [test_group_sets[idx] for idx in np.sort(selected_idx)]

        for test_group_tuple in test_group_sets:
            test_indices = []
            test_group_ranges = []
            for group in test_group_tuple:
                start, end = boundaries[group]
                test_indices.extend(range(start, end))
                test_group_ranges.append((start, end))

            test_indices_arr = np.asarray(sorted(test_indices), dtype=int)
            train_indices = np.asarray(sorted(set(range(n_samples)) - set(test_indices_arr.tolist())), dtype=int)
            train_indices = self._apply_purge_embargo(train_indices, test_group_ranges, n_samples)

            if train_indices.size == 0:
                embargo_backup = self.config.embargo_pct
                self.logger.warning("CombinatorialPurgedCV: embargo 清空訓練集，自動降低 embargo")
                self.config.embargo_pct = max(0.0, embargo_backup / 2)
                train_indices = self._apply_purge_embargo(np.asarray(sorted(set(range(n_samples)) - set(test_indices_arr.tolist())), dtype=int), test_group_ranges, n_samples)
                self.config.embargo_pct = embargo_backup

            yield train_indices, test_indices_arr

    def validate(
        self,
        model_factory: Callable[[], Any],
        X: pd.DataFrame,
        y: np.ndarray,
        feature_names: List[str],
    ) -> Dict[str, Any]:
        path_results: List[Dict[str, Any]] = []
        path_aucs: List[float] = []
        feature_counts: Dict[str, int] = {}

        split_list = list(self.split(X, y))
        if not split_list:
            skipped = SkippedResult(module_name="cpcv", reason="無可用 path", error_type="INSUFFICIENT_DATA")
            return {"cpcv": {"status": "skipped", "skipped": skipped.__dict__}}

        boundaries = self._compute_group_boundaries(len(X))
        boundary_map = {idx: item for idx, item in enumerate(boundaries)}

        for path_index, (train_idx, test_idx) in enumerate(split_list):
            try:
                model = model_factory()
                model.fit(X.iloc[train_idx], np.asarray(y)[train_idx])
            except Exception as error:
                self.logger.warning(f"CombinatorialPurgedCV: path {path_index} 訓練失敗，跳過 ({error})")
                continue

            y_test = np.asarray(y)[test_idx]
            if np.unique(y_test).size < 2:
                auc = np.nan
            else:
                scores = self._predict_scores(model, X.iloc[test_idx])
                auc = float(roc_auc_score(y_test, scores))

            if not np.isnan(auc):
                path_aucs.append(auc)

            top_features = self._extract_top_features(model, feature_names)
            for feature in top_features:
                feature_counts[feature] = feature_counts.get(feature, 0) + 1

            test_groups = self._infer_test_groups(test_idx, boundary_map)
            path_results.append(
                {
                    "path_index": path_index,
                    "test_groups": test_groups,
                    "auc": None if np.isnan(auc) else auc,
                    "n_train": int(len(train_idx)),
                    "n_test": int(len(test_idx)),
                }
            )

        if not path_aucs:
            skipped = SkippedResult(module_name="cpcv", reason="所有 path AUC 為 NaN", error_type="NUMERICAL_ERROR")
            return {"cpcv": {"status": "skipped", "skipped": skipped.__dict__}}

        n_paths = len(path_results)
        auc_arr = np.asarray(path_aucs, dtype=float)
        feature_stability = {feature: count / max(n_paths, 1) for feature, count in feature_counts.items()}

        return {
            "cpcv": {
                "config": {
                    "n_groups": self.config.n_groups,
                    "n_test_groups": self.config.n_test_groups,
                    "purge_gap": self.config.purge_gap,
                    "embargo_pct": self.config.embargo_pct,
                },
                "n_paths": n_paths,
                "summary": {
                    "mean_auc": float(np.mean(auc_arr)),
                    "std_auc": float(np.std(auc_arr)),
                    "min_auc": float(np.min(auc_arr)),
                    "max_auc": float(np.max(auc_arr)),
                    "hit_rate": float(np.mean(auc_arr >= 0.5)),
                },
                "path_results": path_results,
                "path_aucs": [float(v) for v in auc_arr],
                "backtest_paths": self.generate_backtest_paths(self.config.n_groups, self.config.n_test_groups),
                "feature_stability": feature_stability,
            }
        }

    def generate_backtest_paths(
        self,
        n_groups: int,
        n_test_groups: int,
    ) -> List[List[int]]:
        return [list(groups) for groups in combinations(range(n_groups), n_test_groups)]

    def _compute_group_boundaries(self, n_samples: int) -> List[Tuple[int, int]]:
        boundaries: List[Tuple[int, int]] = []
        indices = np.linspace(0, n_samples, self.config.n_groups + 1, dtype=int)
        for i in range(self.config.n_groups):
            boundaries.append((int(indices[i]), int(indices[i + 1])))
        return boundaries

    def _apply_purge_embargo(
        self,
        train_indices: np.ndarray,
        test_groups: List[Tuple[int, int]],
        n_samples: int,
    ) -> np.ndarray:
        mask = np.ones(n_samples, dtype=bool)
        mask[:] = False
        mask[train_indices] = True

        embargo_len = int(n_samples * self.config.embargo_pct)
        for start, end in test_groups:
            purge_start = max(0, start - self.config.purge_gap)
            purge_end = min(n_samples, end + self.config.purge_gap + embargo_len)
            mask[purge_start:purge_end] = False

        return np.where(mask)[0]

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

    @staticmethod
    def _extract_top_features(model: Any, feature_names: List[str], top_k: int = 5) -> List[str]:
        if hasattr(model, "feature_importances_"):
            values = np.asarray(model.feature_importances_, dtype=float)
        elif hasattr(model, "coef_"):
            coef = np.asarray(model.coef_)
            values = np.abs(coef[0] if coef.ndim > 1 else coef)
        else:
            return feature_names[:top_k]

        if values.size == 0:
            return feature_names[:top_k]
        idx = np.argsort(values)[::-1][:top_k]
        return [feature_names[i] for i in idx if i < len(feature_names)]

    @staticmethod
    def _infer_test_groups(test_idx: np.ndarray, boundaries: Dict[int, Tuple[int, int]]) -> List[int]:
        groups: List[int] = []
        for group_id, (start, end) in boundaries.items():
            if np.any((test_idx >= start) & (test_idx < end)):
                groups.append(group_id)
        return groups
