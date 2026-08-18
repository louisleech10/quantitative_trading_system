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

from momentum.core.logging import get_logger

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
    """簡易策略權益曲線——**單利／複利兩條都算、都標清楚**（PA-CUMSUM 小票，2026-08-18 使用者定）。

    - `*_simple`（單利；固定本金／固定金額下注）：每期報酬**相加** ⇒ `cumsum(r)`；等於「每期都拿同一筆本金下注」之累積損益率。
    - `*_compound`（複利；全額滾入／固定比例）：資產**連乘** ⇒ `cumprod(1+r) - 1`；等於帳戶實際淨值變化。
    兩者為不同部位假設下的正確算法，**不是**其中一個對一個錯；本檔不再輸出無標籤之 `strategy_returns`（曾以單利算、標成累積報酬 %）。
    `final_return_pct` 四鍵：`strategy_simple`／`benchmark_simple`／`strategy_compound`／`benchmark_compound`（百分比）。
    """

    timestamps: List[int]
    strategy_returns_simple: List[float]
    benchmark_returns_simple: List[float]
    strategy_returns_compound: List[float]
    benchmark_returns_compound: List[float]
    threshold: float
    final_return_pct: Dict[str, float]
    n_symbols: int = 1
    aggregation: str = "single_series"  # 或 equal_weight_by_timestamp（多標的等權組合；R23 CODEX-P1-01）

    def to_dict(self) -> Dict:
        return {
            "timestamps": self.timestamps,
            "strategy_returns_simple": self.strategy_returns_simple,
            "benchmark_returns_simple": self.benchmark_returns_simple,
            "strategy_returns_compound": self.strategy_returns_compound,
            "benchmark_returns_compound": self.benchmark_returns_compound,
            "threshold": self.threshold,
            "final_return_pct": self.final_return_pct,
            "n_symbols": self.n_symbols,
            "aggregation": self.aggregation,
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
        threshold: float = 0.75,
        symbols: Optional[List[str]] = None,
    ) -> EquityCurveData:
        """計算簡易策略權益曲線：單利（`cumsum`）與複利（`cumprod(1+r)-1`）**兩條都算**（見 `EquityCurveData`）。

        - `actual_returns`：每期簡單報酬率（小數）；`y_pred_proba > threshold` 之期數持倉、否則空手（報酬 0）。
        - 🔴 fail-closed（R23 review）：`actual_returns` **與** `y_pred_proba` 任一含 NaN／inf ⇒ `ValueError`
          （缺失預測**不得**靜默當「低於閾值⇒空手」；呼叫方須先決定如何填補）。
        - 🔴 多標的（R23 `CODEX-R23-P1-01`）：`symbols` 給定且含 >1 個相異 symbol ⇒ **不得**把跨 symbol 的列當同一帳戶連乘；
          改為**逐 timestamp 等權組合**（`aggregation="equal_weight_by_timestamp"`）：同一 timestamp 之各 symbol 策略報酬（持倉×報酬）
          取平均、基準報酬取平均，再對聚合序列做單利／複利；輸出 timestamps 為去重升冪。單一 symbol／未給 ⇒ 逐列（`"single_series"`）。
        """
        y_pred_proba = np.asarray(y_pred_proba, dtype=float)
        actual_returns = np.asarray(actual_returns, dtype=float)
        ts_arr = np.asarray(timestamps)

        if len(y_pred_proba) != len(actual_returns):
            raise ValueError("y_pred_proba 與 actual_returns 長度不一致")
        if len(ts_arr) != len(y_pred_proba):
            raise ValueError("timestamps 與 y_pred_proba 長度不一致")
        if not np.all(np.isfinite(actual_returns)):
            raise ValueError("actual_returns 含 NaN／inf（呼叫方須先填補，禁靜默當 0）")
        if not np.all(np.isfinite(y_pred_proba)):
            raise ValueError("y_pred_proba 含 NaN／inf（缺失預測禁靜默當空手，呼叫方須先填補）")
        if symbols is not None and len(symbols) != len(y_pred_proba):
            raise ValueError("symbols 與 y_pred_proba 長度不一致")

        strategy_positions = (y_pred_proba > threshold).astype(float)
        strategy_returns = actual_returns * strategy_positions

        n_symbols = int(len(set(map(str, symbols)))) if symbols is not None and len(symbols) > 0 else 1
        if n_symbols > 1:
            aggregation = "equal_weight_by_timestamp"
            uniq_ts, inverse = np.unique(ts_arr, return_inverse=True)
            counts = np.bincount(inverse, minlength=len(uniq_ts)).astype(float)
            agg_strategy = np.bincount(inverse, weights=strategy_returns, minlength=len(uniq_ts)) / counts
            agg_benchmark = np.bincount(inverse, weights=actual_returns, minlength=len(uniq_ts)) / counts
            out_ts = [int(t) for t in uniq_ts]
        else:
            aggregation = "single_series"
            agg_strategy = strategy_returns
            agg_benchmark = actual_returns
            out_ts = [int(t) for t in ts_arr]

        # 單利（固定本金）：報酬相加
        cum_strategy_simple = np.cumsum(agg_strategy)
        cum_benchmark_simple = np.cumsum(agg_benchmark)
        # 複利（全額滾入）：資產連乘 − 1
        cum_strategy_compound = np.cumprod(1.0 + agg_strategy) - 1.0
        cum_benchmark_compound = np.cumprod(1.0 + agg_benchmark) - 1.0

        def _final_pct(curve: np.ndarray) -> float:
            return float(curve[-1] * 100.0) if len(curve) > 0 else 0.0

        return EquityCurveData(
            timestamps=out_ts,
            strategy_returns_simple=cum_strategy_simple.tolist(),
            benchmark_returns_simple=cum_benchmark_simple.tolist(),
            strategy_returns_compound=cum_strategy_compound.tolist(),
            benchmark_returns_compound=cum_benchmark_compound.tolist(),
            threshold=float(threshold),
            final_return_pct={
                "strategy_simple": _final_pct(cum_strategy_simple),
                "benchmark_simple": _final_pct(cum_benchmark_simple),
                "strategy_compound": _final_pct(cum_strategy_compound),
                "benchmark_compound": _final_pct(cum_benchmark_compound),
            },
            n_symbols=n_symbols,
            aggregation=aggregation,
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
