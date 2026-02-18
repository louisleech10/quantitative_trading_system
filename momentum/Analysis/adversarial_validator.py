"""Adversarial validation module."""

from __future__ import annotations

from typing import Dict, Optional, Any, List

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

from pydantic import BaseModel, Field

from momentum.Analysis.drift_analyzer import DriftAnalyzer
from momentum.core.logging import get_logger
from momentum.core.contracts import SkippedResult


class AdversarialValidationConfig(BaseModel):
    enabled: bool = True
    n_estimators: int = Field(default=100, ge=10, le=1000)
    cv: int = Field(default=5, ge=2, le=10)
    auc_warning_threshold: float = Field(default=0.55, ge=0.5, le=1.0)
    auc_severe_threshold: float = Field(default=0.70, ge=0.5, le=1.0)
    include_feature_tests: bool = True
    include_leakage_detection: bool = True


class AdversarialValidator:
    """Adversarial Validation + Feature-Level Tests + Leakage Detection。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = AdversarialValidationConfig(**(config or {}))
        self.logger = get_logger(__name__)
        self._drift_analyzer = DriftAnalyzer()

    def validate_distribution(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
    ) -> Dict[str, Any]:
        self._ensure_compatible_columns(X_train, X_test)

        if X_train.empty or X_test.empty:
            skipped = SkippedResult(
                module_name="adversarial_validator",
                reason="X_train 或 X_test 為空",
                error_type="INSUFFICIENT_DATA",
            )
            return {"distribution_test": {"status": "skipped", "skipped": skipped.__dict__}}

        if len(X_test) < 20:
            self.logger.warning("AdversarialValidator: X_test < 20，AUC 可能不可靠")

        if len(X_train) == len(X_test) and np.allclose(X_train.to_numpy(dtype=float), X_test.to_numpy(dtype=float), equal_nan=True):
            return {
                "distribution_test": {
                    "auc": 0.5,
                    "std": 0.0,
                    "status": "good",
                    "top_discriminating_features": X_train.columns[:5].tolist(),
                }
            }

        X_all = pd.concat([X_train, X_test], axis=0).reset_index(drop=True)
        y_domain = np.concatenate([np.zeros(len(X_train), dtype=int), np.ones(len(X_test), dtype=int)])

        model = self._create_domain_classifier()
        cv = StratifiedKFold(n_splits=min(self.config.cv, max(2, int(np.min(np.bincount(y_domain))))), shuffle=True, random_state=42)

        aucs: List[float] = []
        for train_idx, val_idx in cv.split(X_all, y_domain):
            model.fit(X_all.iloc[train_idx], y_domain[train_idx])
            scores = self._predict_scores(model, X_all.iloc[val_idx])
            aucs.append(float(roc_auc_score(y_domain[val_idx], scores)))

        model.fit(X_all, y_domain)
        top_features = self._extract_top_features(model, X_all.columns.tolist())
        auc_mean = float(np.mean(aucs))
        auc_std = float(np.std(aucs))
        status = self._status_from_auc(auc_mean)

        return {
            "distribution_test": {
                "auc": auc_mean,
                "std": auc_std,
                "status": status,
                "top_discriminating_features": top_features,
            }
        }

    def feature_level_tests(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        method: str = "ks",
    ) -> Dict[str, Dict]:
        self._ensure_compatible_columns(X_train, X_test)

        results: Dict[str, Dict] = {}
        for feature in X_train.columns:
            train_col = X_train[feature].to_numpy(dtype=float)
            test_col = X_test[feature].to_numpy(dtype=float)

            if np.all(np.isnan(train_col)) or np.all(np.isnan(test_col)):
                self.logger.warning(f"AdversarialValidator: {feature} 全 NaN，跳過 KS/PSI")
                continue

            train_valid = train_col[~np.isnan(train_col)]
            test_valid = test_col[~np.isnan(test_col)]
            if len(train_valid) == 0 or len(test_valid) == 0:
                continue

            ks_stat, ks_pvalue = ks_2samp(train_valid, test_valid)
            psi_value, _, _, _ = self._drift_analyzer.calculate_psi(train_valid, test_valid, bins=10)

            status = "stable"
            if ks_pvalue < 0.01 or psi_value >= 0.25:
                status = "severe"
            elif ks_pvalue < 0.05 or psi_value >= 0.10:
                status = "warning"

            results[feature] = {
                "ks_statistic": float(ks_stat),
                "ks_pvalue": float(ks_pvalue),
                "psi": float(psi_value),
                "status": status,
                "method": method,
            }

        return results

    def detect_leakage(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
        timestamps: np.ndarray,
        future_window: int = 5,
    ) -> Dict[str, Any]:
        if timestamps is None:
            return {"suspicious_features": [], "autocorrelation_flags": {}, "status": "skipped"}

        if future_window > len(X) / 2:
            raise ValueError("future_window 過大，超過樣本長度一半")

        y_arr = np.asarray(y, dtype=float)
        suspicious_features: List[str] = []
        autocorrelation_flags: Dict[str, Dict[str, Any]] = {}

        for feature in X.columns:
            values = X[feature].to_numpy(dtype=float)
            if len(values) <= future_window:
                continue

            cur = values[:-future_window]
            fut = y_arr[future_window:]
            valid = (~np.isnan(cur)) & (~np.isnan(fut))
            if valid.sum() < 10:
                continue

            corr = np.corrcoef(cur[valid], fut[valid])[0, 1]
            lag1 = np.corrcoef(values[1:], values[:-1])[0, 1] if len(values) > 2 else 0.0
            is_suspicious = bool(np.abs(corr) > 0.3 or np.abs(lag1) > 0.95)

            autocorrelation_flags[feature] = {
                "future_corr": float(corr),
                "lag_1_corr": float(lag1),
                "is_suspicious": is_suspicious,
            }
            if is_suspicious:
                suspicious_features.append(feature)

        return {
            "suspicious_features": suspicious_features,
            "autocorrelation_flags": autocorrelation_flags,
            "status": "ok",
        }

    def full_validation(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: Optional[np.ndarray] = None,
        timestamps: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        distribution = self.validate_distribution(X_train, X_test)
        feature_tests = self.feature_level_tests(X_train, X_test) if self.config.include_feature_tests else {}

        leakage = {"status": "skipped", "suspicious_features": [], "autocorrelation_flags": {}}
        if self.config.include_leakage_detection and y_train is not None and timestamps is not None:
            leakage = self.detect_leakage(X_train, y_train, timestamps)

        distribution_status = distribution.get("distribution_test", {}).get("status", "good")
        feature_statuses = [entry.get("status") for entry in feature_tests.values()]
        if distribution_status == "severe" or "severe" in feature_statuses:
            overall_status = "severe"
        elif distribution_status == "warning" or "warning" in feature_statuses:
            overall_status = "warning"
        else:
            overall_status = "good"

        recommendations: List[str] = []
        if overall_status in {"warning", "severe"}:
            recommendations.append("建議檢查分佈差異較高的特徵")
        if leakage.get("suspicious_features"):
            recommendations.append("建議檢查潛在時間洩漏特徵")

        return {
            "adversarial_validation": {
                "distribution_test": distribution.get("distribution_test", {}),
                "feature_level_tests": feature_tests,
                "leakage_detection": leakage,
                "overall_status": overall_status,
                "recommendations": recommendations,
            }
        }

    @staticmethod
    def _create_domain_classifier() -> Any:
        try:
            from lightgbm import LGBMClassifier

            return LGBMClassifier(
                n_estimators=100,
                learning_rate=0.05,
                max_depth=5,
                num_leaves=31,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                verbose=-1,
            )
        except Exception:
            from sklearn.ensemble import RandomForestClassifier

            return RandomForestClassifier(n_estimators=100, random_state=42)

    def _status_from_auc(self, auc: float) -> str:
        if auc >= self.config.auc_severe_threshold:
            return "severe"
        if auc >= self.config.auc_warning_threshold:
            return "warning"
        return "good"

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
    def _ensure_compatible_columns(X_train: pd.DataFrame, X_test: pd.DataFrame) -> None:
        if list(X_train.columns) != list(X_test.columns):
            raise ValueError("X_train 與 X_test 欄位不一致")
