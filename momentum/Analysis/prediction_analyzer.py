"""
Prediction Analyzer - 預測結果分析工具

提供機率分佈、權益曲線、錯誤診斷與滾動 AUC 計算

Author: AI Agent
Date: 2026-01-29
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from api.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ProbabilityDensityData:
    positive_density: Dict[str, List[float]]
    negative_density: Dict[str, List[float]]
    overlap_score: float

    def to_dict(self) -> Dict:
        return {
            "positive_density": self.positive_density,
            "negative_density": self.negative_density,
            "overlap_score": self.overlap_score
        }


@dataclass
class EquityCurveData:
    timestamps: List[int]
    strategy_returns: List[float]
    benchmark_returns: List[float]
    threshold: float
    final_return_pct: Dict[str, float]

    def to_dict(self) -> Dict:
        return {
            "timestamps": self.timestamps,
            "strategy_returns": self.strategy_returns,
            "benchmark_returns": self.benchmark_returns,
            "threshold": self.threshold,
            "final_return_pct": self.final_return_pct
        }


@dataclass
class FalsePositiveCase:
    case_id: str
    timestamp: str
    symbol: str
    predicted_proba: float
    actual_return: float

    def to_dict(self) -> Dict:
        return {
            "case_id": self.case_id,
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "predicted_proba": self.predicted_proba,
            "actual_return": self.actual_return
        }


@dataclass
class RollingAUCData:
    timestamps: List[int]
    auc_values: List[Optional[float]]
    window_size: int
    warning_zones: List[Dict[str, str]]

    def to_dict(self) -> Dict:
        return {
            "timestamps": self.timestamps,
            "auc_values": self.auc_values,
            "window_size": self.window_size,
            "warning_zones": self.warning_zones
        }


class PredictionAnalyzer:
    """預測結果分析器"""

    def __init__(self):
        self.logger = logger

    def calculate_probability_density(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        n_bins: int = 50
    ) -> ProbabilityDensityData:
        """計算正負樣本的機率分佈密度"""
        if n_bins < 5:
            raise ValueError("n_bins 必須 >= 5")

        y_true = np.asarray(y_true)
        y_pred_proba = np.asarray(y_pred_proba)

        if len(y_true) == 0:
            raise ValueError("y_true 為空")
        if len(y_true) != len(y_pred_proba):
            raise ValueError("y_true 與 y_pred_proba 長度不一致")

        positive_proba = y_pred_proba[y_true == 1]
        negative_proba = y_pred_proba[y_true == 0]

        bins = np.linspace(0.0, 1.0, n_bins + 1)
        pos_hist, _ = np.histogram(positive_proba, bins=bins, density=True)
        neg_hist, _ = np.histogram(negative_proba, bins=bins, density=True)

        bin_centers = (bins[:-1] + bins[1:]) / 2.0

        overlap = float(np.minimum(pos_hist, neg_hist).sum() / n_bins)

        return ProbabilityDensityData(
            positive_density={
                "bins": bin_centers.tolist(),
                "density": pos_hist.tolist()
            },
            negative_density={
                "bins": bin_centers.tolist(),
                "density": neg_hist.tolist()
            },
            overlap_score=overlap
        )

    def calculate_strategy_equity_curve(
        self,
        timestamps: List[int],
        y_pred_proba: np.ndarray,
        actual_returns: np.ndarray,
        threshold: float = 0.75
    ) -> EquityCurveData:
        """計算簡易策略權益曲線"""
        y_pred_proba = np.asarray(y_pred_proba)
        actual_returns = np.asarray(actual_returns)

        if len(y_pred_proba) != len(actual_returns):
            raise ValueError("y_pred_proba 與 actual_returns 長度不一致")
        if len(timestamps) != len(y_pred_proba):
            raise ValueError("timestamps 與 y_pred_proba 長度不一致")

        strategy_positions = (y_pred_proba > threshold).astype(float)
        strategy_returns = actual_returns * strategy_positions

        cum_strategy = np.cumsum(strategy_returns)
        cum_benchmark = np.cumsum(actual_returns)

        final_strategy = float(cum_strategy[-1] * 100) if len(cum_strategy) > 0 else 0.0
        final_benchmark = float(cum_benchmark[-1] * 100) if len(cum_benchmark) > 0 else 0.0

        return EquityCurveData(
            timestamps=[int(ts) for ts in timestamps],
            strategy_returns=cum_strategy.tolist(),
            benchmark_returns=cum_benchmark.tolist(),
            threshold=float(threshold),
            final_return_pct={
                "strategy": final_strategy,
                "benchmark": final_benchmark
            }
        )

    def get_top_false_positives(
        self,
        case_ids: List[str],
        timestamps: List[int],
        symbols: List[str],
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        actual_returns: np.ndarray,
        top_n: int = 5
    ) -> List[FalsePositiveCase]:
        """找出模型最有信心但錯誤的案例"""
        if top_n <= 0:
            raise ValueError("top_n 必須 > 0")

        y_true = np.asarray(y_true)
        y_pred_proba = np.asarray(y_pred_proba)
        actual_returns = np.asarray(actual_returns)

        if len(y_true) == 0:
            return []

        fp_mask = (y_true == 0) & (y_pred_proba > 0.5)
        fp_indices = np.where(fp_mask)[0]

        if len(fp_indices) == 0:
            return []

        sorted_indices = fp_indices[np.argsort(y_pred_proba[fp_indices])[::-1]][:top_n]

        results: List[FalsePositiveCase] = []
        for idx in sorted_indices:
            ts = int(timestamps[idx]) if idx < len(timestamps) else 0
            results.append(
                FalsePositiveCase(
                    case_id=case_ids[idx] if idx < len(case_ids) else f"case_{idx}",
                    timestamp=datetime.fromtimestamp(ts if ts < 10**12 else ts / 1000).isoformat(),
                    symbol=symbols[idx] if idx < len(symbols) else "UNKNOWN",
                    predicted_proba=float(y_pred_proba[idx]),
                    actual_return=float(actual_returns[idx]) if idx < len(actual_returns) else 0.0
                )
            )

        return results

    def calculate_rolling_auc(
        self,
        timestamps: List[int],
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        window: int = 500
    ) -> RollingAUCData:
        """計算滾動 AUC"""
        from sklearn.metrics import roc_auc_score

        if window < 10:
            raise ValueError("window 必須 >= 10")

        y_true = np.asarray(y_true)
        y_pred_proba = np.asarray(y_pred_proba)

        if len(y_true) != len(y_pred_proba):
            raise ValueError("y_true 與 y_pred_proba 長度不一致")

        n_samples = len(y_true)
        if n_samples < window:
            raise ValueError(f"樣本不足以計算滾動 AUC: {n_samples} < {window}")

        auc_values: List[Optional[float]] = []
        ts_values: List[int] = []

        for i in range(window, n_samples):
            window_y_true = y_true[i - window:i]
            window_y_pred = y_pred_proba[i - window:i]

            if len(np.unique(window_y_true)) < 2:
                auc_values.append(None)
            else:
                auc_values.append(float(roc_auc_score(window_y_true, window_y_pred)))
            ts_values.append(int(timestamps[i]))

        warning_zones = self._detect_warning_zones(ts_values, auc_values, threshold=0.55)

        return RollingAUCData(
            timestamps=ts_values,
            auc_values=auc_values,
            window_size=window,
            warning_zones=warning_zones
        )

    def _detect_warning_zones(
        self,
        timestamps: List[int],
        auc_values: List[Optional[float]],
        threshold: float = 0.55
    ) -> List[Dict[str, str]]:
        """偵測 AUC 低於閾值的連續區間"""
        warning_zones: List[Dict[str, str]] = []
        in_warning = False
        zone_start: Optional[int] = None

        for i, (ts, auc) in enumerate(zip(timestamps, auc_values)):
            is_warning = auc is not None and auc < threshold

            if is_warning and not in_warning:
                zone_start = ts
                in_warning = True
            elif not is_warning and in_warning:
                end_ts = timestamps[i - 1]
                warning_zones.append({
                    "start": datetime.fromtimestamp(self._normalize_ts(zone_start)).isoformat(),
                    "end": datetime.fromtimestamp(self._normalize_ts(end_ts)).isoformat()
                })
                in_warning = False

        if in_warning and zone_start is not None and timestamps:
            warning_zones.append({
                "start": datetime.fromtimestamp(self._normalize_ts(zone_start)).isoformat(),
                "end": datetime.fromtimestamp(self._normalize_ts(timestamps[-1])).isoformat()
            })

        return warning_zones

    @staticmethod
    def _normalize_ts(ts: int) -> float:
        return ts / 1000 if ts > 10**12 else ts
