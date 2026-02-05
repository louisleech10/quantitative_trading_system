"""
Calibration Analyzer - 機率校準分析

提供 Brier Score、ECE 與校準曲線計算

Author: AI Agent
Date: 2026-01-28
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass

import numpy as np
from sklearn.metrics import brier_score_loss

from momentum.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CalibrationCurveData:
    """校準曲線資料"""
    bin_midpoints: List[float]
    actual_positive_rate: List[float]
    predicted_mean: List[float]
    sample_count: List[int]

    def to_dict(self) -> Dict:
        return {
            "bin_midpoints": self.bin_midpoints,
            "actual_positive_rate": self.actual_positive_rate,
            "predicted_mean": self.predicted_mean,
            "sample_count": self.sample_count
        }


@dataclass
class CalibrationMetrics:
    """校準指標"""
    brier_score: float
    ece: float
    calibration_quality: str
    curve_data: CalibrationCurveData

    def to_dict(self) -> Dict:
        return {
            "brier_score": self.brier_score,
            "ece": self.ece,
            "calibration_quality": self.calibration_quality,
            "calibration_curve": self.curve_data.to_dict()
        }


class CalibrationAnalyzer:
    """機率校準分析器"""

    def __init__(self, min_samples: int = 50):
        self.min_samples = min_samples
        self.logger = logger

    def _validate_inputs(self, y_true: np.ndarray, y_pred_proba: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if len(y_true) != len(y_pred_proba):
            raise ValueError("y_true 與 y_pred_proba 長度不一致")

        if len(y_true) == 0:
            raise ValueError("y_true 為空，無法計算校準指標")

        y_true = np.asarray(y_true)
        y_pred_proba = np.asarray(y_pred_proba)

        if len(y_true) < self.min_samples:
            self.logger.warning(
                f"校準樣本數偏少 ({len(y_true)} < {self.min_samples})，ECE 可能不穩定"
            )

        # 機率範圍檢查
        min_prob = float(np.min(y_pred_proba))
        max_prob = float(np.max(y_pred_proba))
        if min_prob < 0.0 or max_prob > 1.0:
            self.logger.warning(
                f"預測機率超出 [0, 1] 範圍 (min={min_prob:.4f}, max={max_prob:.4f})，將進行裁切"
            )
            y_pred_proba = np.clip(y_pred_proba, 0.0, 1.0)

        return y_true, y_pred_proba

    def calculate_brier_score(self, y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
        """計算 Brier Score（越小越好）"""
        y_true, y_pred_proba = self._validate_inputs(y_true, y_pred_proba)
        return float(brier_score_loss(y_true, y_pred_proba))

    def calculate_ece(self, y_true: np.ndarray, y_pred_proba: np.ndarray, n_bins: int = 10) -> float:
        """計算 Expected Calibration Error（ECE）"""
        y_true, y_pred_proba = self._validate_inputs(y_true, y_pred_proba)

        if n_bins < 2:
            raise ValueError("n_bins 必須 >= 2")

        bins = np.linspace(0.0, 1.0, n_bins + 1)
        bin_indices = np.digitize(y_pred_proba, bins, right=True) - 1
        bin_indices = np.clip(bin_indices, 0, n_bins - 1)

        ece = 0.0
        total = len(y_true)
        for bin_idx in range(n_bins):
            mask = bin_indices == bin_idx
            count = int(np.sum(mask))
            if count == 0:
                continue
            bin_true = y_true[mask]
            bin_pred = y_pred_proba[mask]
            actual_rate = float(np.mean(bin_true))
            predicted_mean = float(np.mean(bin_pred))
            ece += (count / total) * abs(actual_rate - predicted_mean)

        return float(ece)

    def get_calibration_curve(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        n_bins: int = 10
    ) -> CalibrationCurveData:
        """產生校準曲線資料"""
        y_true, y_pred_proba = self._validate_inputs(y_true, y_pred_proba)

        if n_bins < 2:
            raise ValueError("n_bins 必須 >= 2")

        bins = np.linspace(0.0, 1.0, n_bins + 1)
        bin_indices = np.digitize(y_pred_proba, bins, right=True) - 1
        bin_indices = np.clip(bin_indices, 0, n_bins - 1)

        bin_midpoints: List[float] = []
        actual_positive_rate: List[float] = []
        predicted_mean: List[float] = []
        sample_count: List[int] = []

        for bin_idx in range(n_bins):
            mask = bin_indices == bin_idx
            count = int(np.sum(mask))
            left = bins[bin_idx]
            right = bins[bin_idx + 1]
            midpoint = float((left + right) / 2.0)

            if count == 0:
                actual_rate = 0.0
                pred_mean = 0.0
            else:
                actual_rate = float(np.mean(y_true[mask]))
                pred_mean = float(np.mean(y_pred_proba[mask]))

            bin_midpoints.append(midpoint)
            actual_positive_rate.append(actual_rate)
            predicted_mean.append(pred_mean)
            sample_count.append(count)

        return CalibrationCurveData(
            bin_midpoints=bin_midpoints,
            actual_positive_rate=actual_positive_rate,
            predicted_mean=predicted_mean,
            sample_count=sample_count
        )

    def get_calibration_quality(self, brier: float, ece: float) -> str:
        """判斷校準品質"""
        if brier < 0.15 and ece < 0.05:
            return "good"
        if brier < 0.25 and ece < 0.10:
            return "fair"
        return "poor"

    def calculate_metrics(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        n_bins: int = 10
    ) -> CalibrationMetrics:
        """計算校準指標與曲線資料"""
        brier = self.calculate_brier_score(y_true, y_pred_proba)
        ece = self.calculate_ece(y_true, y_pred_proba, n_bins=n_bins)
        quality = self.get_calibration_quality(brier, ece)
        curve = self.get_calibration_curve(y_true, y_pred_proba, n_bins=n_bins)
        return CalibrationMetrics(
            brier_score=brier,
            ece=ece,
            calibration_quality=quality,
            curve_data=curve
        )
