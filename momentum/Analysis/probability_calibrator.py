"""Probability calibration module."""

from __future__ import annotations

from typing import Dict, Optional, Any, Callable, Tuple, Union, List

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from pydantic import BaseModel, Field

from momentum.Analysis.calibration_analyzer import CalibrationAnalyzer
from momentum.core.logging import get_logger
from momentum.core.contracts import (
    CalibratorReceipt,
    ReceiptVerificationError,
    SkippedResult,
    SplitPlan,
    build_receipt_envelope,
    model_artifact_digest,
    verify_calibrator_receipt,
)


class ProbabilityCalibratorConfig(BaseModel):
    enabled: bool = True
    method: str = Field(default="auto", pattern="^(auto|platt|isotonic|beta|venn_abers)$")
    cv: int = Field(default=5, ge=2, le=10)
    min_samples_isotonic: int = Field(default=1000, ge=100)
    fallback_on_degradation: bool = True
    venn_abers_max_samples: int = Field(default=5000, ge=100)


class ProbabilityCalibrator:
    """機率校準修正引擎。

    LA-2 B2：fit / fit_from_predictions 共用 verify_calibrator_receipt；
    signal-facing 缺 receipt → fail-closed。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = ProbabilityCalibratorConfig(**(config or {}))
        self.logger = get_logger(__name__)
        self._analyzer = CalibrationAnalyzer(min_samples=50)
        self._fitted = False
        self._model: Optional[Any] = None
        self._expected_n_features: Optional[int] = None
        self._selected_method: Optional[str] = None
        self._comparison: Dict[str, Any] = {}
        self._venn_margin: float = 0.03
        self._transformer: Optional[Callable[[np.ndarray], np.ndarray]] = None
        self.last_calibrator_receipt: Optional[Dict[str, Any]] = None

    def _require_and_verify_receipt(
        self,
        *,
        train_plan: Optional[SplitPlan],
        calib_idx: Optional[Any],
        model_artifact: Optional[bytes],
        receipt: Optional[CalibratorReceipt],
        require_receipt: bool,
    ) -> Optional[Dict[str, Any]]:
        """signal-facing 缺 receipt → raise；有則四步 verify。"""
        if not require_receipt:
            return None
        if train_plan is None or calib_idx is None or model_artifact is None:
            raise ReceiptVerificationError(
                "CalibratorReceipt required: pass train_plan, calib_idx, model_artifact "
                "(signal-facing fail-closed)"
            )
        # F4：require_receipt=True 時 receipt 必須外部傳入，禁止 calibrator 自簽
        if receipt is None:
            raise ReceiptVerificationError(
                "CalibratorReceipt required: receipt must be supplied by trusted caller "
                "(calibrator does not self-issue under require_receipt=True)"
            )
        envelope = build_receipt_envelope("calibrator", receipt)
        verify_calibrator_receipt(
            receipt,
            train_plan,
            calib_idx,
            model_artifact,
            envelope=envelope,
        )
        self.last_calibrator_receipt = envelope
        return envelope

    def fit(
        self,
        model: Any,
        X_cal: Union[pd.DataFrame, np.ndarray],
        y_cal: np.ndarray,
        method: str = "auto",
        cv: Optional[int] = None,
        *,
        train_plan: Optional[SplitPlan] = None,
        calib_idx: Optional[Any] = None,
        model_artifact: Optional[bytes] = None,
        receipt: Optional[CalibratorReceipt] = None,
        require_receipt: bool = True,
    ) -> Dict[str, Any]:
        if not hasattr(model, "predict_proba"):
            raise ValueError("model 必須支援 predict_proba")

        X_array = np.asarray(X_cal)
        if X_array.ndim != 2:
            raise ValueError("X_cal 必須為 2 維矩陣")

        y_pred = np.asarray(model.predict_proba(X_cal))[:, 1]
        self._model = model
        self._expected_n_features = int(X_array.shape[1])

        if model_artifact is None and require_receipt:
            # 以 model pickle 位元作 artifact；失敗則用 params digest 字節
            import pickle

            try:
                model_artifact = pickle.dumps(model)
            except Exception as exc:  # noqa: BLE001
                raise ReceiptVerificationError(
                    f"cannot serialize model for CalibratorReceipt: {exc}"
                ) from exc

        if calib_idx is None and require_receipt:
            calib_idx = np.arange(len(y_cal), dtype=int)

        return self.fit_from_predictions(
            y_true=np.asarray(y_cal),
            y_pred_proba=y_pred,
            method=method,
            cv=cv,
            train_plan=train_plan,
            calib_idx=calib_idx,
            model_artifact=model_artifact,
            receipt=receipt,
            require_receipt=require_receipt,
        )

    def fit_from_predictions(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        method: str = "auto",
        cv: Optional[int] = None,
        *,
        train_plan: Optional[SplitPlan] = None,
        calib_idx: Optional[Any] = None,
        model_artifact: Optional[bytes] = None,
        receipt: Optional[CalibratorReceipt] = None,
        require_receipt: bool = True,
    ) -> Dict[str, Any]:
        # LA-2 B2：兩分支共用 verify（缺 → fail-closed）
        receipt_envelope = self._require_and_verify_receipt(
            train_plan=train_plan,
            calib_idx=calib_idx,
            model_artifact=model_artifact,
            receipt=receipt,
            require_receipt=require_receipt,
        )

        y_true = np.asarray(y_true).astype(int)
        y_pred_proba = np.asarray(y_pred_proba, dtype=float)

        if y_true.shape[0] != y_pred_proba.shape[0]:
            raise ValueError("y_true 與 y_pred_proba 長度不一致")

        valid_mask = (~np.isnan(y_true)) & (~np.isnan(y_pred_proba))
        if valid_mask.sum() < y_true.shape[0]:
            self.logger.warning("ProbabilityCalibrator: 偵測到 NaN，將自動移除後校準")
        y_true = y_true[valid_mask]
        y_pred_proba = np.clip(y_pred_proba[valid_mask], 0.0, 1.0)

        if y_true.shape[0] < 50:
            self.logger.warning("ProbabilityCalibrator: 樣本數 < 50，將限制為 Platt")

        if np.unique(y_true).size < 2:
            return self._skip("SINGLE_CLASS", "y_cal 僅單一類別")

        if np.var(y_pred_proba) == 0.0:
            return self._skip("ZERO_VARIANCE", "預測機率無變化")

        effective_cv = int(cv or self.config.cv)
        max_safe_cv = max(2, int(len(y_true) // 2))
        if effective_cv > max_safe_cv:
            self.logger.warning("ProbabilityCalibrator: cv 過大，自動降低")
            effective_cv = max_safe_cv

        candidate_methods = self._resolve_candidate_methods(method=method, n_samples=len(y_true))
        baseline = self._compute_metrics(y_true=y_true, y_pred=y_pred_proba)

        comparisons: Dict[str, Dict[str, float]] = {"original": baseline}
        method_outputs: Dict[str, np.ndarray] = {}

        for candidate in candidate_methods:
            try:
                calibrated = self._apply_calibration_method(
                    method=candidate,
                    y_true=y_true,
                    y_pred=y_pred_proba,
                    cv=effective_cv,
                )
                metrics = self._compute_metrics(y_true=y_true, y_pred=calibrated)
                comparisons[candidate] = metrics
                method_outputs[candidate] = calibrated
            except Exception as error:
                self.logger.warning(f"ProbabilityCalibrator: {candidate} 校準失敗，略過 ({error})")

        if not method_outputs:
            return self._skip("NUMERICAL_ERROR", "所有校準方法失敗")

        best_method = min(method_outputs.keys(), key=lambda m: comparisons[m]["ece"])
        best_proba = method_outputs[best_method]

        calibration_failed = False
        if self.config.fallback_on_degradation and comparisons[best_method]["ece"] > baseline["ece"]:
            calibration_failed = True
            best_method = "original"
            best_proba = y_pred_proba

        self._selected_method = best_method
        self._comparison = comparisons
        self._fitted = True
        self._transformer = self._build_transformer(best_method=best_method, y_input=y_pred_proba, y_output=best_proba)

        reliability_curve = self._build_reliability_curve(y_true=y_true, original=y_pred_proba, calibrated=best_proba)

        improvement = (baseline["ece"] - comparisons.get(best_method, baseline)["ece"]) / max(baseline["ece"], 1e-12) * 100

        result: Dict[str, Any] = {
            "probability_calibration": {
                "method": best_method,
                "comparison": comparisons,
                "best_method": best_method,
                "improvement_pct": float(improvement),
                "calibration_failed": calibration_failed,
                "reliability_curve": reliability_curve,
                "sample_size": int(len(y_true)),
                "cv_folds": int(effective_cv),
            }
        }
        if receipt_envelope is not None:
            result["calibrator_receipt"] = receipt_envelope
        return result

    def predict_calibrated(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        if not self._fitted:
            raise ValueError("ProbabilityCalibrator 尚未 fit")
        if self._model is None:
            raise ValueError("尚未綁定模型，請使用 fit(model, X_cal, y_cal)")

        X_array = np.asarray(X)
        if X_array.ndim != 2:
            raise ValueError("X 必須為 2 維矩陣")
        if self._expected_n_features is not None and X_array.shape[1] != self._expected_n_features:
            raise ValueError("X 特徵數與 fit 時不一致")

        y_pred = np.asarray(self._model.predict_proba(X))[:, 1]
        return self.transform_proba(y_pred)

    def transform_proba(self, y_pred_proba: np.ndarray) -> np.ndarray:
        if not self._fitted or self._transformer is None:
            raise ValueError("ProbabilityCalibrator 尚未 fit")
        y_pred = np.asarray(y_pred_proba, dtype=float)
        y_pred = np.clip(y_pred, 0.0, 1.0)
        return np.clip(self._transformer(y_pred), 0.0, 1.0)

    def get_calibration_comparison(self) -> Dict[str, Any]:
        return {
            "method": self._selected_method,
            "comparison": self._comparison,
        }

    def get_venn_abers_intervals(
        self,
        X: Union[pd.DataFrame, np.ndarray],
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        center = self.predict_calibrated(X)
        margin = self._venn_margin if self._selected_method == "venn_abers" else 0.02
        lower = np.clip(center - margin, 0.0, 1.0)
        upper = np.clip(center + margin, 0.0, 1.0)
        return lower, center, upper

    def _resolve_candidate_methods(self, method: str, n_samples: int) -> List[str]:
        normalized_method = method.lower().strip()
        if normalized_method not in {"auto", "platt", "isotonic", "beta", "venn_abers"}:
            raise ValueError(f"不支援的校準方法: {method}")

        if normalized_method != "auto":
            if normalized_method == "beta" and not self._betacal_available():
                self.logger.warning("ProbabilityCalibrator: betacal 不可用，回退 platt")
                return ["platt"]
            if normalized_method == "isotonic" and n_samples < self.config.min_samples_isotonic:
                self.logger.warning("ProbabilityCalibrator: isotonic 樣本不足，回退 platt")
                return ["platt"]
            return [normalized_method]

        if n_samples < 50:
            return ["platt"]

        methods = ["platt", "isotonic", "beta", "venn_abers"]
        if n_samples < self.config.min_samples_isotonic:
            methods.remove("isotonic")
        if not self._betacal_available() and "beta" in methods:
            self.logger.warning("ProbabilityCalibrator: betacal 不可用，auto 模式移除 beta")
            methods.remove("beta")
        return methods

    def _apply_calibration_method(
        self,
        method: str,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        cv: int,
    ) -> np.ndarray:
        y_pred = np.clip(y_pred, 1e-6, 1 - 1e-6)

        if method == "platt":
            model = LogisticRegression(max_iter=1000, solver="lbfgs")
            model.fit(y_pred.reshape(-1, 1), y_true)
            return model.predict_proba(y_pred.reshape(-1, 1))[:, 1]

        if method == "isotonic":
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(y_pred, y_true)
            return iso.predict(y_pred)

        if method == "beta":
            try:
                from betacal import BetaCalibration
            except Exception:
                self.logger.warning("ProbabilityCalibrator: betacal 不可用，回退 platt")
                return self._apply_calibration_method("platt", y_true=y_true, y_pred=y_pred, cv=cv)

            beta = BetaCalibration(parameters="abm")
            beta.fit(y_pred.reshape(-1, 1), y_true)
            return np.asarray(beta.predict(y_pred.reshape(-1, 1))).reshape(-1)

        if method == "venn_abers":
            if len(y_true) > self.config.venn_abers_max_samples:
                self.logger.warning("ProbabilityCalibrator: venn_abers 樣本過大，將降採樣")
                rng = np.random.default_rng(42)
                selected = rng.choice(len(y_true), size=self.config.venn_abers_max_samples, replace=False)
                y_true = y_true[selected]
                y_pred = y_pred[selected]
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(y_pred, y_true)
            calibrated = iso.predict(np.clip(y_pred, 1e-6, 1 - 1e-6))
            self._venn_margin = float(np.std(calibrated - y_true) * 0.5)
            self._venn_margin = float(np.clip(self._venn_margin, 0.01, 0.08))
            return calibrated

        raise ValueError(f"不支援的 method: {method}")

    def _compute_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        return {
            "ece": float(self._analyzer.calculate_ece(y_true, y_pred)),
            "brier": float(self._analyzer.calculate_brier_score(y_true, y_pred)),
        }

    def _build_transformer(
        self,
        best_method: str,
        y_input: np.ndarray,
        y_output: np.ndarray,
    ) -> Callable[[np.ndarray], np.ndarray]:
        if best_method == "original":
            return lambda pred: pred

        if best_method == "isotonic" or best_method == "venn_abers":
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(np.clip(y_input, 0.0, 1.0), np.clip(y_output, 0.0, 1.0))
            return lambda pred: iso.predict(pred)

        model = LogisticRegression(max_iter=1000, solver="lbfgs")
        pseudo_target = np.clip(y_output, 1e-6, 1 - 1e-6)
        hard_target = (pseudo_target >= np.median(pseudo_target)).astype(int)
        model.fit(np.clip(y_input, 1e-6, 1 - 1e-6).reshape(-1, 1), hard_target)
        return lambda pred: model.predict_proba(pred.reshape(-1, 1))[:, 1]

    def _build_reliability_curve(self, y_true: np.ndarray, original: np.ndarray, calibrated: np.ndarray) -> Dict[str, Any]:
        curve_original = self._analyzer.get_calibration_curve(y_true, original)
        curve_calibrated = self._analyzer.get_calibration_curve(y_true, calibrated)
        return {
            "bin_midpoints": curve_original.bin_midpoints,
            "original_freq": curve_original.actual_positive_rate,
            "calibrated_freq": curve_calibrated.actual_positive_rate,
        }

    def _skip(self, error_type: str, reason: str) -> Dict[str, Any]:
        skipped = SkippedResult(
            module_name="probability_calibrator",
            reason=reason,
            error_type=error_type,
            retryable=False,
        )
        self.logger.warning(f"ProbabilityCalibrator skipped: {reason}")
        return {
            "probability_calibration": {
                "status": "skipped",
                "skipped": skipped.__dict__,
            }
        }

    @staticmethod
    def _betacal_available() -> bool:
        try:
            from betacal import BetaCalibration  # noqa: F401

            return True
        except Exception:
            return False
