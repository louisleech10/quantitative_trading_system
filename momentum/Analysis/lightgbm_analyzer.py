"""LightGBM Analyzer - Phase 3 model trainer implementation."""

from __future__ import annotations

import pickle
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import auc, f1_score, precision_recall_curve, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, TimeSeriesSplit

from momentum.Analysis.calibration_analyzer import CalibrationAnalyzer
from momentum.Analysis.model_types import (
    FeatureImportance,
    FoldImportanceStabilityResult,
    GlobalSHAPResult,
    ModelPerformance,
    OOTValidationResult,
    PRMetrics,
    PermutationImportanceResult,
    PrecisionAtKResult,
    PredictionOutput,
    SingleCaseSHAPResult,
)
from momentum.Analysis.shap_analyzer import SHAPAnalyzer
from momentum.Analysis.time_splitter import PurgedTimeSeriesSplit
from momentum.core.logging import get_logger

logger = get_logger(__name__)


class LightGBMAnalyzer:
    """LightGBM 分析引擎 — 符合 IModelTrainer Protocol。"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        self.logger = logger
        self.default_params: Dict[str, Any] = {
            "objective": "binary",
            "metric": "auc",
            "boosting_type": "gbdt",
            "num_leaves": 31,
            "max_depth": -1,
            "learning_rate": 0.05,
            "n_estimators": 200,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "subsample_freq": 5,
            "min_child_samples": 20,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "min_gain_to_split": 0.01,
            "random_state": 42,
            "n_jobs": -1,
            "verbose": -1,
            "force_col_wise": True,
        }
        self.params = {**self.default_params, **(params or {})}
        self.model: Optional[lgb.LGBMClassifier] = None
        self.feature_names: Optional[List[str]] = None
        self.calibration_analyzer = CalibrationAnalyzer()
        self.shap_analyzer = SHAPAnalyzer()
        self._shap_explainer = None
        self._shap_model_id: Optional[int] = None
        self._last_training_time: Optional[float] = None
        self.last_calibration_curve = None
        self.last_pr_curve: Optional[Dict[str, Any]] = None

    def _validate_train_inputs(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        feature_names: Optional[List[str]],
    ) -> None:
        if len(X) == 0:
            raise ValueError("X 為空")
        if len(y) == 0:
            raise ValueError("y 為空")
        if len(X) != len(y):
            raise ValueError("X 與 y 長度不一致")

        unique_labels = np.unique(y)
        if len(unique_labels) < 2:
            raise ValueError("標籤只有一個類別")

        if isinstance(X, pd.DataFrame):
            self.feature_names = X.columns.tolist()
            values = X.to_numpy(dtype=float, copy=False)
        else:
            if feature_names is None:
                raise ValueError("必須提供 feature_names")
            if X.shape[1] != len(feature_names):
                raise ValueError("特徵數量不匹配")
            self.feature_names = feature_names
            values = np.asarray(X, dtype=float)

        if np.isinf(values).any():
            raise ValueError("X 含無限值")

    def _resolve_model_path(self, path: str) -> Path:
        allowed_root = Path("data_cache/models").resolve()
        target = Path(path).expanduser().resolve()
        if Path(target).suffix != ".pkl":
            raise ValueError("模型檔案必須為 .pkl")
        if allowed_root != target and allowed_root not in target.parents:
            raise ValueError("模型路徑必須在 data_cache/models/ 下")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def _time_series_split(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        eval_size: float,
        timestamps: Optional[List[int]],
    ) -> Tuple[Any, Any, np.ndarray, np.ndarray]:
        if eval_size <= 0:
            raise ValueError("eval_size 必須 > 0")
        if eval_size >= 1:
            raise ValueError("eval_size 必須 < 1")

        X_array = X.to_numpy(dtype=float, copy=False) if isinstance(X, pd.DataFrame) else np.asarray(X, dtype=float)
        y_array = np.asarray(y)

        order = np.argsort(np.array(timestamps)) if timestamps is not None else np.arange(len(y_array))
        X_sorted = X_array[order]
        y_sorted = y_array[order]

        split_idx = int(len(y_sorted) * (1 - eval_size))
        if split_idx < 1 or split_idx >= len(y_sorted):
            raise ValueError("時間序列切分比例不合理，請調整 eval_size")

        X_train = X_sorted[:split_idx]
        X_val = X_sorted[split_idx:]
        y_train = y_sorted[:split_idx]
        y_val = y_sorted[split_idx:]
        return X_train, X_val, y_train, y_val

    def _stratified_holdout_split(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        eval_size: float,
    ) -> Tuple[Any, Any, np.ndarray, np.ndarray]:
        """使用穩定的索引切分，避免 pandas/sklearn 在特定環境下索引異常。"""
        X_array = X.to_numpy(dtype=float, copy=False) if isinstance(X, pd.DataFrame) else np.asarray(X, dtype=float)
        y_array = np.asarray(y)
        unique_labels = np.unique(y_array)
        if len(unique_labels) < 2:
            raise ValueError("標籤只有一個類別")

        rng = np.random.default_rng(42)
        train_parts: List[np.ndarray] = []
        val_parts: List[np.ndarray] = []

        for label in unique_labels:
            label_idx = np.flatnonzero(y_array == label)
            if len(label_idx) < 2:
                raise ValueError("每個類別至少需要 2 筆樣本以進行分層切分")

            shuffled = rng.permutation(label_idx)
            n_val = int(round(len(label_idx) * eval_size))
            n_val = max(1, min(len(label_idx) - 1, n_val))

            val_parts.append(shuffled[:n_val])
            train_parts.append(shuffled[n_val:])

        train_idx = np.concatenate(train_parts)
        val_idx = np.concatenate(val_parts)
        rng.shuffle(train_idx)
        rng.shuffle(val_idx)

        X_train = X_array[train_idx]
        X_val = X_array[val_idx]

        y_train = y_array[train_idx]
        y_val = y_array[val_idx]
        return X_train, X_val, y_train, y_val

    def train_model(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        early_stopping_rounds: int = 50,
        eval_size: float = 0.2,
        lightgbm_params: Optional[Dict[str, Any]] = None,
        cv_folds: int = 5,
        time_series_split: bool = False,
        timestamps: Optional[List[int]] = None,
        purge_gap: Optional[int] = None,
        embargo_pct: Optional[float] = None,
        categorical_features: Optional[List[str]] = None,
    ) -> ModelPerformance:
        self._validate_train_inputs(X, y, feature_names)
        if eval_size <= 0:
            raise ValueError("eval_size 必須 > 0")
        if eval_size >= 1:
            raise ValueError("eval_size 必須 < 1")

        if lightgbm_params:
            self.params = {**self.default_params, **lightgbm_params}

        self.logger.info(f"開始訓練 LightGBM 模型 - 樣本數: {len(X)}, 特徵數: {len(self.feature_names or [])}")

        X_input = X.to_numpy(dtype=float, copy=False) if isinstance(X, pd.DataFrame) else np.asarray(X, dtype=float)
        y_input = np.asarray(y)

        unique, counts = np.unique(y_input, return_counts=True)
        label_dist = {int(label): int(count) for label, count in zip(unique, counts)}
        self.logger.info(f"標籤分佈: {label_dist}")

        if time_series_split:
            X_train, X_val, y_train, y_val = self._time_series_split(X_input, y_input, eval_size, timestamps)
        else:
            X_train, X_val, y_train, y_val = self._stratified_holdout_split(X_input, y_input, eval_size)

        self.logger.info(f"訓練集: {len(X_train)} 樣本, 驗證集: {len(X_val)} 樣本")

        fit_kwargs: Dict[str, Any] = {
            "eval_set": [(X_val, y_val)],
        }
        callbacks = []
        if early_stopping_rounds and early_stopping_rounds > 0:
            callbacks.append(lgb.early_stopping(stopping_rounds=early_stopping_rounds, verbose=False))
        if callbacks:
            fit_kwargs["callbacks"] = callbacks
        if categorical_features:
            fit_kwargs["categorical_feature"] = categorical_features

        started_at = time.perf_counter()
        self.model = lgb.LGBMClassifier(**self.params)
        self.model.fit(X_train, y_train, **fit_kwargs)
        self._last_training_time = time.perf_counter() - started_at

        self._shap_explainer = None
        self._shap_model_id = None

        performance = self.validate_model(
            X=X_input,
            y=y_input,
            cv_folds=cv_folds,
            time_series_split=time_series_split,
            timestamps=timestamps,
            purge_gap=purge_gap,
            embargo_pct=embargo_pct,
        )
        performance.engine_type = "lightgbm"
        performance.training_time_seconds = self._last_training_time
        performance.n_estimators_actual = int(getattr(self.model, "n_estimators_", self.params.get("n_estimators", 0)))
        self.logger.info(
            f"訓練完成 - Train AUC: {performance.train_auc:.4f}, "
            f"CV AUC: {performance.cv_auc_mean:.4f} ± {performance.cv_auc_std:.4f}"
        )
        return performance

    def train_with_purged_cv(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        n_splits: int = 5,
        purge_gap: int = 5,
        **kwargs: Any,
    ) -> ModelPerformance:
        timestamps = kwargs.pop("timestamps", None)
        return self.train_model(
            X=X,
            y=y,
            cv_folds=n_splits,
            time_series_split=True,
            purge_gap=purge_gap,
            timestamps=timestamps,
            **kwargs,
        )

    def validate_model(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        cv_folds: int = 5,
        time_series_split: bool = False,
        timestamps: Optional[List[int]] = None,
        purge_gap: Optional[int] = None,
        embargo_pct: Optional[float] = None,
    ) -> ModelPerformance:
        self.logger.info(f"開始交叉驗證 - {cv_folds}-fold CV")
        if self.model is None:
            raise ValueError("模型尚未訓練")
        if cv_folds < 2:
            raise ValueError("交叉驗證至少 2 折")
        if cv_folds > len(y):
            raise ValueError("折數超過樣本數")
        if purge_gap is not None and purge_gap >= len(y):
            raise ValueError("purge_gap 過大")

        X_input = X.to_numpy(dtype=float, copy=False) if isinstance(X, pd.DataFrame) else np.asarray(X, dtype=float)
        y_input = np.asarray(y)

        if time_series_split:
            order = np.argsort(np.array(timestamps)) if timestamps is not None else np.arange(len(y_input))
            X_ordered = X_input[order]
            y_ordered = y_input[order]
            if purge_gap is not None or embargo_pct is not None:
                splitter = PurgedTimeSeriesSplit(
                    n_splits=cv_folds,
                    purge_gap=int(purge_gap or 0),
                    embargo_pct=float(embargo_pct or 0.0),
                )
            else:
                splitter = TimeSeriesSplit(n_splits=cv_folds)
            split_iter = splitter.split(X_ordered)
        else:
            X_ordered = X_input
            y_ordered = y_input
            splitter = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
            split_iter = splitter.split(X_ordered, y_ordered)

        cv_auc_scores: List[float] = []
        cv_precision_scores: List[float] = []
        cv_recall_scores: List[float] = []
        cv_f1_scores: List[float] = []

        for fold_idx, (train_idx, val_idx) in enumerate(split_iter, start=1):
            X_train = X_ordered[train_idx]
            X_val = X_ordered[val_idx]
            y_train = y_ordered[train_idx]
            y_val = y_ordered[val_idx]

            fold_model = lgb.LGBMClassifier(**self.params)
            fold_model.fit(X_train, y_train)

            y_pred_proba = fold_model.predict_proba(X_val)[:, 1]
            y_pred = (y_pred_proba >= 0.5).astype(int)

            if len(np.unique(y_val)) < 2:
                auc_value = np.nan
                self.logger.warning(f"Fold {fold_idx}/{cv_folds} - 驗證集只有單一類別，AUC 設為 NaN")
            else:
                auc_value = float(roc_auc_score(y_val, y_pred_proba))
            precision_value = float(precision_score(y_val, y_pred, zero_division=0))
            recall_value = float(recall_score(y_val, y_pred, zero_division=0))
            f1_value = float(f1_score(y_val, y_pred, zero_division=0))

            cv_auc_scores.append(auc_value)
            cv_precision_scores.append(precision_value)
            cv_recall_scores.append(recall_value)
            cv_f1_scores.append(f1_value)

            self.logger.info(
                f"Fold {fold_idx}/{cv_folds} - "
                f"AUC: {auc_value:.4f}, Precision: {precision_value:.4f}, "
                f"Recall: {recall_value:.4f}, F1: {f1_value:.4f}"
            )

        y_train_pred = self.model.predict_proba(X_ordered)[:, 1]
        train_auc = float(roc_auc_score(y_ordered, y_train_pred)) if len(np.unique(y_ordered)) > 1 else np.nan

        valid_auc = [value for value in cv_auc_scores if not np.isnan(value)]
        cv_auc_mean = float(np.mean(valid_auc)) if valid_auc else np.nan
        cv_auc_std = float(np.std(valid_auc)) if valid_auc else np.nan
        overfitting_score = float(train_auc - cv_auc_mean) if not (np.isnan(train_auc) or np.isnan(cv_auc_mean)) else np.nan

        calibration = self.calibration_analyzer.calculate_metrics(y_ordered, y_train_pred)
        pr = self.calculate_pr_metrics(X_ordered, y_ordered)
        self.last_calibration_curve = calibration.curve_data
        self.last_pr_curve = {
            "precision": pr.precision_curve,
            "recall": pr.recall_curve,
            "thresholds": pr.thresholds,
            "pr_auc": pr.pr_auc,
        }

        self.logger.info(
            f"校準指標 - Brier: {calibration.brier_score:.4f}, ECE: {calibration.ece:.4f}, "
            f"品質: {calibration.calibration_quality}"
        )
        if calibration.calibration_quality == "poor":
            self.logger.warning("校準品質偏低，建議重新調整模型或做機率校準")

        if not np.isnan(cv_auc_mean) and not np.isnan(pr.pr_auc):
            roc_pr_gap = cv_auc_mean - pr.pr_auc
            if roc_pr_gap > 0.15:
                self.logger.warning(
                    f"ROC AUC 與 PR AUC 差距較大 ({roc_pr_gap:.4f})，ROC AUC 可能過度樂觀"
                )

        self.logger.info(
            f"交叉驗證完成 - Train AUC: {train_auc:.4f}, "
            f"CV AUC: {cv_auc_mean:.4f} ± {cv_auc_std:.4f}, "
            f"Overfitting: {overfitting_score:.4f}"
        )

        return ModelPerformance(
            train_auc=float(train_auc),
            cv_auc_mean=float(cv_auc_mean),
            cv_auc_std=float(cv_auc_std),
            precision=float(np.mean(cv_precision_scores)),
            recall=float(np.mean(cv_recall_scores)),
            f1_score=float(np.mean(cv_f1_scores)),
            overfitting_score=float(overfitting_score),
            brier_score=float(calibration.brier_score),
            ece=float(calibration.ece),
            calibration_quality=calibration.calibration_quality,
            pr_auc=float(pr.pr_auc),
            positive_rate=float(np.mean(y_ordered)),
            engine_type="lightgbm",
            training_time_seconds=self._last_training_time,
            n_estimators_actual=int(getattr(self.model, "n_estimators_", self.params.get("n_estimators", 0))),
        )

    def validate_oot(
        self,
        X_oot: Union[pd.DataFrame, np.ndarray],
        y_oot: np.ndarray,
        cv_auc_mean: Optional[float] = None,
    ) -> OOTValidationResult:
        if self.model is None:
            raise ValueError("模型尚未訓練")
        if len(X_oot) == 0:
            raise ValueError("OOT 資料為空")
        if len(X_oot) != len(y_oot):
            raise ValueError("OOT 標籤長度不匹配")

        n_samples = len(y_oot)
        if n_samples < 50:
            self.logger.warning("OOT 樣本數不足 50")

        unique_labels = np.unique(y_oot)
        if len(unique_labels) < 2:
            self.logger.warning("OOT 標籤只有單一類別，無法計算 AUC")
            return OOTValidationResult(
                oot_auc=None,
                cv_oot_gap=None,
                gap_status="warning",
                n_samples=n_samples,
            )

        y_pred_proba = self.model.predict_proba(X_oot)[:, 1]
        oot_auc = float(roc_auc_score(y_oot, y_pred_proba))
        if cv_auc_mean is None:
            return OOTValidationResult(
                oot_auc=oot_auc,
                cv_oot_gap=None,
                gap_status="good",
                n_samples=n_samples,
            )

        gap = float(cv_auc_mean - oot_auc)
        if gap < 0.05:
            status = "good"
        elif gap < 0.08:
            status = "warning"
        else:
            status = "severe"
        return OOTValidationResult(
            oot_auc=oot_auc,
            cv_oot_gap=gap,
            gap_status=status,
            n_samples=n_samples,
        )

    def calculate_feature_importance(
        self,
        feature_names: List[str],
        method: str = "gain",
        top_n: Optional[int] = None,
    ) -> List[FeatureImportance]:
        if self.model is None:
            raise ValueError("模型尚未訓練")
        if method not in {"gain", "split"}:
            raise ValueError("method 僅支援 gain 或 split")

        if method == "split":
            importances = np.asarray(self.model.booster_.feature_importance(importance_type="split"), dtype=float)
        else:
            importances = np.asarray(self.model.booster_.feature_importance(importance_type="gain"), dtype=float)

        if len(feature_names) != len(importances):
            raise ValueError("特徵數量不匹配")

        total = float(np.sum(importances))
        if total > 0:
            importances = importances / total

        pairs = list(zip(feature_names, importances.tolist()))
        pairs.sort(key=lambda item: item[1], reverse=True)

        results = [
            FeatureImportance(feature_name=name, importance=float(value), rank=index + 1)
            for index, (name, value) in enumerate(pairs)
        ]
        return results[:top_n] if top_n is not None else results

    def get_all_importance_types(
        self,
        feature_names: List[str],
        top_n: Optional[int] = None,
    ) -> Dict[str, List[FeatureImportance]]:
        return {
            "gain": self.calculate_feature_importance(feature_names, method="gain", top_n=top_n),
            "split": self.calculate_feature_importance(feature_names, method="split", top_n=top_n),
        }

    def calculate_permutation_importance(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        n_repeats: int = 10,
        random_state: int = 42,
        scoring: str = "roc_auc",
    ) -> List[PermutationImportanceResult]:
        if self.model is None:
            raise ValueError("模型尚未訓練")
        result = permutation_importance(
            self.model,
            X,
            y,
            n_repeats=n_repeats,
            random_state=random_state,
            scoring=scoring,
        )
        names = self.feature_names or [f"feature_{i}" for i in range(X.shape[1])]
        return [
            PermutationImportanceResult(
                feature_name=names[i],
                importance_mean=float(result.importances_mean[i]),
                importance_std=float(result.importances_std[i]),
            )
            for i in range(len(names))
        ]

    def calculate_fold_importance_stability(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        cv_folds: int = 5,
    ) -> List[FoldImportanceStabilityResult]:
        names = self.feature_names or [f"feature_{i}" for i in range(X.shape[1])]
        splitter = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        feature_to_values: Dict[str, List[float]] = {name: [] for name in names}

        for train_idx, _ in splitter.split(X, y):
            X_train = X.iloc[train_idx] if isinstance(X, pd.DataFrame) else X[train_idx]
            y_train = y[train_idx]
            fold_model = lgb.LGBMClassifier(**self.params)
            fold_model.fit(X_train, y_train)
            fold_values = np.asarray(fold_model.booster_.feature_importance(importance_type="gain"), dtype=float)
            total = float(np.sum(fold_values))
            if total > 0:
                fold_values = fold_values / total
            for i, name in enumerate(names):
                feature_to_values[name].append(float(fold_values[i]))

        results: List[FoldImportanceStabilityResult] = []
        for name in names:
            values = np.asarray(feature_to_values[name], dtype=float)
            mean_value = float(np.mean(values)) if len(values) > 0 else 0.0
            std_value = float(np.std(values)) if len(values) > 0 else 0.0
            cv = float(std_value / mean_value) if mean_value > 0 else float("inf")
            results.append(
                FoldImportanceStabilityResult(
                    feature_name=name,
                    mean_importance=mean_value,
                    std_importance=std_value,
                    cv_coefficient=cv,
                )
            )
        return results

    def predict_proba(self, features: Any) -> np.ndarray:
        if self.model is None:
            raise ValueError("模型尚未訓練")
        return self.model.predict_proba(features)

    def get_feature_importance(
        self,
        method: str = "gain",
        top_n: Optional[int] = None,
    ) -> List[FeatureImportance]:
        if self.feature_names is None:
            raise ValueError("特徵名稱尚未設定")
        return self.calculate_feature_importance(self.feature_names, method=method, top_n=top_n)

    def get_predictions(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y_true: Optional[np.ndarray] = None,
        case_ids: Optional[List[str]] = None,
    ) -> PredictionOutput:
        if self.model is None:
            raise ValueError("模型尚未訓練")
        if len(X) == 0:
            raise ValueError("X 為空")
        y_pred_proba = self.model.predict_proba(X)
        y_pred_label = (y_pred_proba[:, 1] >= 0.5).astype(int)
        return PredictionOutput(
            case_ids=case_ids,
            y_true=y_true,
            y_pred_proba=y_pred_proba,
            y_pred_label=y_pred_label,
        )

    def calculate_precision_at_k(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
        k_values: Optional[List[int]] = None,
    ) -> List[PrecisionAtKResult]:
        if self.model is None:
            raise ValueError("模型尚未訓練")
        if len(X) == 0:
            raise ValueError("X 為空")
        y_pred_proba = self.model.predict_proba(X)[:, 1]
        n_samples = len(y)
        results: List[PrecisionAtKResult] = []
        for k in (k_values or [1, 5, 10, 20]):
            n_top = max(1, int(n_samples * k / 100))
            top_indices = np.argsort(y_pred_proba)[-n_top:]
            n_positive = int(np.sum(y[top_indices]))
            precision = float(n_positive / n_top)
            results.append(
                PrecisionAtKResult(
                    k=k,
                    precision=precision,
                    n_positive=n_positive,
                    n_total=int(n_top),
                )
            )
        return results

    def calculate_pr_metrics(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: np.ndarray,
    ) -> PRMetrics:
        if self.model is None:
            raise ValueError("模型尚未訓練")
        y_pred_proba = self.model.predict_proba(X)[:, 1]
        precision_curve, recall_curve, thresholds = precision_recall_curve(y, y_pred_proba)
        return PRMetrics(
            pr_auc=float(auc(recall_curve, precision_curve)),
            precision_curve=precision_curve.tolist(),
            recall_curve=recall_curve.tolist(),
            thresholds=thresholds.tolist(),
        )

    def recommend_k(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        target_precision: float = 0.75,
        k_candidates: Optional[List[int]] = None,
    ) -> Dict[str, Optional[Union[int, float]]]:
        best_k: Optional[int] = None
        best_precision: Optional[float] = None
        k_candidates = sorted(k_candidates or [1, 5, 10, 20, 30])
        n_samples = len(y_true)

        for k in k_candidates:
            n_top = max(1, int(n_samples * k / 100))
            top_indices = np.argsort(y_pred_proba)[-n_top:]
            precision = float(np.mean(y_true[top_indices]))
            if precision >= target_precision:
                best_k = k
                best_precision = precision

        return {
            "recommended_k": best_k,
            "precision": best_precision,
        }

    def _get_shap_explainer(self) -> Any:
        if self.model is None:
            raise ValueError("模型尚未訓練")
        model_id = id(self.model)
        if self._shap_explainer is None or self._shap_model_id != model_id:
            self._shap_explainer = self.shap_analyzer.build_explainer(self.model)
            self._shap_model_id = model_id
        return self._shap_explainer

    def analyze_shap_global(self, X: Any, sample_size: int = 100) -> GlobalSHAPResult:
        explainer = self._get_shap_explainer()
        raw = self.shap_analyzer.analyze_global(
            model=self.model,
            X=X,
            sample_size=sample_size,
            explainer=explainer,
            include_summary_points=False,
        )
        mean_abs_shap = {item.feature: float(item.mean_abs_shap) for item in raw.feature_importance_shap}
        shap_values = np.array([item.mean_shap for item in raw.feature_importance_shap], dtype=float)
        feature_names = [item.feature for item in raw.feature_importance_shap]
        return GlobalSHAPResult(
            shap_values=shap_values,
            feature_names=feature_names,
            mean_abs_shap=mean_abs_shap,
        )

    def explain_single_case(self, case_features: Any) -> SingleCaseSHAPResult:
        explainer = self._get_shap_explainer()
        feature_names = self.feature_names
        if feature_names is None:
            raise ValueError("特徵名稱尚未設定")
        raw = self.shap_analyzer.explain_single_case(
            model=self.model,
            case_features=case_features,
            feature_names=feature_names,
            explainer=explainer,
        )
        shap_values = np.array([item.shap_value for item in raw.contributions], dtype=float)
        return SingleCaseSHAPResult(
            case_id=None,
            shap_values=shap_values,
            feature_names=feature_names,
            base_value=float(raw.expected_value),
            prediction=float(raw.predicted_proba),
        )

    def save_model(self, path: str) -> None:
        if self.model is None:
            raise ValueError("無模型可儲存")
        safe_path = self._resolve_model_path(path)
        payload = {
            "model_type": "lightgbm",
            "model": self.model,
            "feature_names": self.feature_names,
            "params": self.params,
        }
        with open(safe_path, "wb") as file:
            pickle.dump(payload, file, protocol=pickle.HIGHEST_PROTOCOL)
        self.logger.info(f"LightGBM 模型已儲存: {safe_path}")

    def load_model(self, path: str) -> None:
        safe_path = self._resolve_model_path(path)
        if not safe_path.exists():
            raise FileNotFoundError(f"模型檔案不存在: {safe_path}")
        with open(safe_path, "rb") as file:
            payload = pickle.load(file)
        if not isinstance(payload, dict):
            raise ValueError("模型檔案格式錯誤")
        if payload.get("model_type") != "lightgbm":
            raise ValueError("模型類型不匹配")
        model = payload.get("model")
        if model is None:
            raise ValueError("模型檔案格式錯誤")
        self.model = model
        self.feature_names = payload.get("feature_names")
        self.params = payload.get("params", dict(self.default_params))
        self._shap_explainer = None
        self._shap_model_id = None

    def get_model_type(self) -> str:
        return "lightgbm"

    def get_model_params(self) -> Dict[str, Any]:
        return dict(self.params)

    def get_native_model(self) -> Any:
        return self.model