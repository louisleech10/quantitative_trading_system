"""
Drift Analyzer - 特徵飄移監控

計算 PSI (Population Stability Index) 以量化訓練分佈與新資料分佈差異

Author: AI Agent
Date: 2026-01-28
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

import numpy as np

from momentum.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PSIResult:
    """單一特徵 PSI 結果"""
    feature: str
    psi: float
    status: str  # 'stable' / 'drift_warning' / 'drift_severe'
    bins: List[float]
    train_pct: List[float]
    test_pct: List[float]

    def to_dict(self) -> Dict:
        return {
            "feature": self.feature,
            "psi": float(self.psi),
            "status": self.status,
            "distribution_comparison": {
                "bins": [float(b) for b in self.bins],
                "train_pct": [float(v) for v in self.train_pct],
                "test_pct": [float(v) for v in self.test_pct]
            }
        }


@dataclass
class DriftReport:
    """飄移報告"""
    results: List[PSIResult]

    def to_dict(self) -> Dict:
        drifted = [r.feature for r in self.results if r.status != "stable"]
        severe = [r.feature for r in self.results if r.status == "drift_severe"]
        return {
            "total_features": len(self.results),
            "drifted_features": drifted,
            "severe_features": severe,
            "results": [r.to_dict() for r in self.results]
        }


class DriftAnalyzer:
    """特徵飄移分析器"""

    def __init__(self, epsilon: float = 1e-4):
        self.epsilon = epsilon
        self.logger = logger

    def calculate_psi(
        self,
        expected: np.ndarray,
        actual: np.ndarray,
        bins: int = 10
    ) -> Tuple[float, List[float], List[float], List[float]]:
        """計算 PSI 並回傳分佈比較資料"""
        expected = np.asarray(expected, dtype=float)
        actual = np.asarray(actual, dtype=float)

        expected = expected[~np.isnan(expected)]
        actual = actual[~np.isnan(actual)]

        if expected.size == 0 or actual.size == 0:
            raise ValueError("PSI 計算失敗：輸入資料為空")

        bin_edges = self._build_bins(expected, bins)
        train_pct = self._calculate_distribution(expected, bin_edges)
        test_pct = self._calculate_distribution(actual, bin_edges)

        train_pct_safe = np.where(train_pct == 0, self.epsilon, train_pct)
        test_pct_safe = np.where(test_pct == 0, self.epsilon, test_pct)

        psi = float(np.sum((test_pct_safe - train_pct_safe) * np.log(test_pct_safe / train_pct_safe)))
        return psi, bin_edges.tolist(), train_pct.tolist(), test_pct.tolist()

    def calculate_all_features_psi(
        self,
        X_train: np.ndarray,
        X_test: np.ndarray,
        feature_names: Optional[List[str]] = None,
        bins: int = 10
    ) -> List[PSIResult]:
        """計算所有特徵的 PSI"""
        if X_train.shape[1] != X_test.shape[1]:
            raise ValueError("X_train 與 X_test 特徵數不一致")

        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(X_train.shape[1])]

        results: List[PSIResult] = []
        for idx, name in enumerate(feature_names):
            psi, bins_list, train_pct, test_pct = self.calculate_psi(
                expected=X_train[:, idx],
                actual=X_test[:, idx],
                bins=bins
            )
            status = self._get_status(psi)
            results.append(
                PSIResult(
                    feature=name,
                    psi=psi,
                    status=status,
                    bins=bins_list,
                    train_pct=train_pct,
                    test_pct=test_pct
                )
            )

        results.sort(key=lambda r: r.psi, reverse=True)
        return results

    def get_drifted_features(self, psi_results: List[PSIResult], threshold: float = 0.1) -> List[str]:
        """取得飄移特徵列表"""
        return [r.feature for r in psi_results if r.psi >= threshold]

    def generate_drift_report(self, psi_results: List[PSIResult]) -> DriftReport:
        """產生飄移報告"""
        return DriftReport(results=psi_results)

    def _build_bins(self, expected: np.ndarray, bins: int) -> np.ndarray:
        """使用訓練分佈建立分箱邊界"""
        unique_vals = np.unique(expected)
        if unique_vals.size <= bins:
            # 類別或離散特徵：使用唯一值分箱
            edges = np.concatenate([unique_vals, [unique_vals[-1] + 1e-6]])
            return edges

        quantiles = np.linspace(0, 1, bins + 1)
        edges = np.quantile(expected, quantiles)
        edges = np.unique(edges)
        if edges.size < 2:
            min_val = float(np.min(expected))
            max_val = float(np.max(expected))
            if min_val == max_val:
                max_val = min_val + 1e-6
            edges = np.linspace(min_val, max_val, bins + 1)
        return edges

    def _calculate_distribution(self, values: np.ndarray, bin_edges: np.ndarray) -> np.ndarray:
        counts, _ = np.histogram(values, bins=bin_edges)
        total = counts.sum()
        if total == 0:
            return np.zeros_like(counts, dtype=float)
        return counts.astype(float) / total

    def _get_status(self, psi: float) -> str:
        if psi < 0.10:
            return "stable"
        if psi < 0.25:
            return "drift_warning"
        return "drift_severe"
