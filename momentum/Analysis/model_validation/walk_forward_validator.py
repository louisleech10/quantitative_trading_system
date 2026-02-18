"""Walk-forward validation module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Any, Callable, List, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, brier_score_loss

from pydantic import BaseModel, Field

from momentum.core.logging import get_logger
from momentum.core.contracts import SkippedResult


class WalkForwardConfig(BaseModel):
    enabled: bool = True
    mode: str = Field(default="rolling", pattern="^(rolling|expanding|both)$")
    train_size: int = Field(default=500, ge=50)
    test_size: int = Field(default=100, ge=20)
    step_size: Optional[int] = None
    purge_gap: int = Field(default=5, ge=0, le=50)
    embargo_pct: float = Field(default=0.01, ge=0.0, le=0.1)
    auc_threshold: float = Field(default=0.55, ge=0.5, le=1.0)
    min_periods: int = Field(default=3, ge=1)


@dataclass
class WalkForwardPeriodResult:
    period_index: int
    train_start_idx: int
    train_end_idx: int
    test_start_idx: int
    test_end_idx: int
    train_samples: int
    test_samples: int
    test_auc: Optional[float]
    test_precision_at_k: Optional[float]
    test_brier_score: Optional[float]
    is_auc: Optional[float]
    is_oos_gap: Optional[float]
    top_features: List[str]


@dataclass
class WalkForwardReport:
    mode: str
    n_periods: int
    period_results: List[WalkForwardPeriodResult]
    mean_oos_auc: float
    std_oos_auc: float
    min_oos_auc: float
    max_oos_auc: float
    oos_hit_rate: float
    mean_is_oos_gap: float
    auc_trend: str
    degradation_periods: List[int]
    feature_stability: Dict[str, float]
    assessment: str


class WalkForwardValidator:
    """Walk-Forward 滾動驗證引擎。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = WalkForwardConfig(**(config or {}))
        self.logger = get_logger(__name__)

    def validate(
        self,
        model_factory: Callable[[], Any],
        X: pd.DataFrame,
        y: np.ndarray,
        feature_names: List[str],
    ) -> Dict[str, Any]:
        mode = self.config.mode
        if mode == "rolling":
            return {"rolling": self.validate_rolling(model_factory, X, y, feature_names, self.config.train_size, self.config.test_size)}
        if mode == "expanding":
            return {"expanding": self.validate_expanding(model_factory, X, y, feature_names, self.config.train_size, self.config.test_size)}
        return {
            "rolling": self.validate_rolling(model_factory, X, y, feature_names, self.config.train_size, self.config.test_size),
            "expanding": self.validate_expanding(model_factory, X, y, feature_names, self.config.train_size, self.config.test_size),
        }

    def validate_rolling(
        self,
        model_factory: Callable[[], Any],
        X: pd.DataFrame,
        y: np.ndarray,
        feature_names: List[str],
        train_size: int,
        test_size: int,
        step_size: Optional[int] = None,
    ) -> Union[WalkForwardReport, SkippedResult]:
        if self.config.purge_gap >= test_size:
            raise ValueError("purge_gap 必須小於 test_size")

        n_samples = len(X)
        minimum_required = train_size + test_size + self.config.purge_gap
        if n_samples < minimum_required:
            return SkippedResult(
                module_name="walk_forward_validator",
                reason="資料長度不足",
                error_type="INSUFFICIENT_DATA",
            )

        if train_size < 50:
            self.logger.warning("WalkForwardValidator: train_size < 50，結果可能不穩定")

        effective_step = step_size or test_size
        if effective_step > test_size:
            self.logger.warning("WalkForwardValidator: step_size > test_size，允許但可能跳躍過大")

        splits = self._generate_rolling_splits(n_samples, train_size, test_size, effective_step)
        if len(splits) <= 2:
            self.logger.warning("WalkForwardValidator: 可用 period 少於等於 2")

        period_results: List[WalkForwardPeriodResult] = []
        for period_index, (train_range, test_range) in enumerate(splits):
            train_start, train_end = train_range
            test_start, test_end = test_range
            X_train = X.iloc[train_start:train_end]
            y_train = np.asarray(y[train_start:train_end])
            X_test = X.iloc[test_start:test_end]
            y_test = np.asarray(y[test_start:test_end])

            try:
                period_result = self._run_single_period(
                    model_factory=model_factory,
                    X_train=X_train,
                    y_train=y_train,
                    X_test=X_test,
                    y_test=y_test,
                    feature_names=feature_names,
                    period_index=period_index,
                    train_range=train_range,
                    test_range=test_range,
                )
            except Exception as error:
                self.logger.warning(f"WalkForwardValidator: period {period_index} 訓練失敗，跳過 ({error})")
                continue

            period_results.append(period_result)

        return self._build_report(mode="rolling", period_results=period_results)

    def validate_expanding(
        self,
        model_factory: Callable[[], Any],
        X: pd.DataFrame,
        y: np.ndarray,
        feature_names: List[str],
        initial_train_size: int,
        test_size: int,
        step_size: Optional[int] = None,
    ) -> Union[WalkForwardReport, SkippedResult]:
        if self.config.purge_gap >= test_size:
            raise ValueError("purge_gap 必須小於 test_size")

        n_samples = len(X)
        minimum_required = initial_train_size + test_size + self.config.purge_gap
        if n_samples < minimum_required:
            return SkippedResult(
                module_name="walk_forward_validator",
                reason="資料長度不足",
                error_type="INSUFFICIENT_DATA",
            )

        effective_step = step_size or test_size
        period_results: List[WalkForwardPeriodResult] = []

        period_index = 0
        train_end = initial_train_size
        while True:
            test_start = train_end + self.config.purge_gap
            test_end = test_start + test_size
            if test_end > n_samples:
                break

            if train_end > max(10000, n_samples * 0.8):
                self.logger.warning("WalkForwardValidator: expanding 視窗可能有記憶體壓力")

            X_train = X.iloc[:train_end]
            y_train = np.asarray(y[:train_end])
            X_test = X.iloc[test_start:test_end]
            y_test = np.asarray(y[test_start:test_end])

            try:
                result = self._run_single_period(
                    model_factory=model_factory,
                    X_train=X_train,
                    y_train=y_train,
                    X_test=X_test,
                    y_test=y_test,
                    feature_names=feature_names,
                    period_index=period_index,
                    train_range=(0, train_end),
                    test_range=(test_start, test_end),
                )
                period_results.append(result)
            except Exception as error:
                self.logger.warning(f"WalkForwardValidator: period {period_index} 訓練失敗，跳過 ({error})")

            train_end += effective_step
            period_index += 1

        return self._build_report(mode="expanding", period_results=period_results)

    def _run_single_period(
        self,
        model_factory: Callable,
        X_train,
        y_train,
        X_test,
        y_test,
        feature_names: List[str],
        period_index: int,
        train_range: Tuple[int, int],
        test_range: Tuple[int, int],
    ) -> WalkForwardPeriodResult:
        model = model_factory()
        model.fit(X_train, y_train)

        train_scores = self._predict_scores(model, X_train)
        test_scores = self._predict_scores(model, X_test)

        is_auc = self._safe_auc(y_train, train_scores)
        test_auc = self._safe_auc(y_test, test_scores)
        test_brier = self._safe_brier(y_test, test_scores)
        precision_at_k = self._precision_at_k(y_test, test_scores)

        top_features = self._extract_top_features(model=model, feature_names=feature_names)
        is_oos_gap = None
        if is_auc is not None and test_auc is not None:
            is_oos_gap = float(is_auc - test_auc)

        return WalkForwardPeriodResult(
            period_index=period_index,
            train_start_idx=int(train_range[0]),
            train_end_idx=int(train_range[1]),
            test_start_idx=int(test_range[0]),
            test_end_idx=int(test_range[1]),
            train_samples=int(len(y_train)),
            test_samples=int(len(y_test)),
            test_auc=test_auc,
            test_precision_at_k=precision_at_k,
            test_brier_score=test_brier,
            is_auc=is_auc,
            is_oos_gap=is_oos_gap,
            top_features=top_features,
        )

    def _generate_rolling_splits(
        self,
        n_samples: int,
        train_size: int,
        test_size: int,
        step_size: int,
    ) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        splits: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
        train_start = 0
        while True:
            train_end = train_start + train_size
            test_start = train_end + self.config.purge_gap
            test_end = test_start + test_size
            if test_end > n_samples:
                break
            splits.append(((train_start, train_end), (test_start, test_end)))
            train_start += step_size
        return splits

    def _assess_stability(self, report: WalkForwardReport) -> str:
        if report.oos_hit_rate >= 0.7 and report.mean_is_oos_gap < 0.05:
            return "robust"
        if report.oos_hit_rate >= 0.5 and report.mean_is_oos_gap < 0.10:
            return "moderate"
        return "unstable"

    def _build_report(self, mode: str, period_results: List[WalkForwardPeriodResult]) -> WalkForwardReport:
        valid_aucs = [r.test_auc for r in period_results if r.test_auc is not None]
        valid_gaps = [r.is_oos_gap for r in period_results if r.is_oos_gap is not None]

        if valid_aucs:
            auc_array = np.asarray(valid_aucs, dtype=float)
            mean_auc = float(np.mean(auc_array))
            std_auc = float(np.std(auc_array))
            min_auc = float(np.min(auc_array))
            max_auc = float(np.max(auc_array))
            hit_rate = float(np.mean(auc_array >= self.config.auc_threshold))
        else:
            mean_auc = 0.0
            std_auc = 0.0
            min_auc = 0.0
            max_auc = 0.0
            hit_rate = 0.0

        mean_gap = float(np.mean(valid_gaps)) if valid_gaps else 0.0
        trend = self._infer_auc_trend(valid_aucs)
        degradation_periods = [r.period_index for r in period_results if r.test_auc is not None and r.test_auc < 0.5]
        feature_stability = self._compute_feature_stability(period_results)

        report = WalkForwardReport(
            mode=mode,
            n_periods=len(period_results),
            period_results=period_results,
            mean_oos_auc=mean_auc,
            std_oos_auc=std_auc,
            min_oos_auc=min_auc,
            max_oos_auc=max_auc,
            oos_hit_rate=hit_rate,
            mean_is_oos_gap=mean_gap,
            auc_trend=trend,
            degradation_periods=degradation_periods,
            feature_stability=feature_stability,
            assessment="unstable",
        )
        report.assessment = self._assess_stability(report)
        return report

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
    def _safe_auc(y_true: np.ndarray, y_score: np.ndarray) -> Optional[float]:
        if np.unique(y_true).size < 2:
            return None
        return float(roc_auc_score(y_true, y_score))

    @staticmethod
    def _safe_brier(y_true: np.ndarray, y_score: np.ndarray) -> Optional[float]:
        if np.unique(y_true).size < 2:
            return None
        return float(brier_score_loss(y_true, y_score))

    @staticmethod
    def _precision_at_k(y_true: np.ndarray, y_score: np.ndarray, k_ratio: float = 0.1) -> Optional[float]:
        if y_true.size == 0:
            return None
        k = max(1, int(len(y_true) * k_ratio))
        idx = np.argsort(y_score)[-k:]
        return float(np.mean(y_true[idx]))

    @staticmethod
    def _extract_top_features(model: Any, feature_names: List[str], top_k: int = 5) -> List[str]:
        if hasattr(model, "feature_importances_"):
            importance = np.asarray(model.feature_importances_, dtype=float)
        elif hasattr(model, "coef_"):
            coef = np.asarray(model.coef_)
            importance = np.abs(coef[0] if coef.ndim > 1 else coef)
        else:
            return feature_names[:top_k]

        if importance.size == 0:
            return feature_names[:top_k]

        sorted_idx = np.argsort(importance)[::-1][:top_k]
        return [feature_names[i] for i in sorted_idx if i < len(feature_names)]

    @staticmethod
    def _infer_auc_trend(valid_aucs: List[float]) -> str:
        if len(valid_aucs) < 3:
            return "stable"
        x = np.arange(len(valid_aucs))
        slope = np.polyfit(x, np.asarray(valid_aucs, dtype=float), 1)[0]
        if slope > 1e-3:
            return "improving"
        if slope < -1e-3:
            return "degrading"
        return "stable"

    @staticmethod
    def _compute_feature_stability(period_results: List[WalkForwardPeriodResult]) -> Dict[str, float]:
        if not period_results:
            return {}
        freq: Dict[str, int] = {}
        for result in period_results:
            for feature in result.top_features:
                freq[feature] = freq.get(feature, 0) + 1
        total = len(period_results)
        return {feature: count / total for feature, count in freq.items()}
