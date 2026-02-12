"""Population Stability Index calculator."""

from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger

logger = get_logger(__name__)


class PSICalculator:
    """PSI — 檢測 Train/Test 特徵分佈穩定性"""

    def compute_psi(
        self, baseline: pd.Series, comparison: pd.Series, n_bins: int = 10
    ) -> float:
        """
        PSI = Σ (P_i - Q_i) × ln(P_i / Q_i)
        使用等頻分箱
        """

        baseline = baseline.dropna()
        comparison = comparison.dropna()
        if baseline.empty or comparison.empty:
            return np.nan

        n_bins = max(int(n_bins), 2)
        quantiles = np.linspace(0, 1, n_bins + 1)
        try:
            bin_edges = np.unique(baseline.quantile(quantiles).values)
        except Exception as exc:
            logger.warning("PSI 分箱失敗: %s", exc)
            return np.nan

        if len(bin_edges) < 3:
            return 0.0

        baseline_bins = pd.cut(baseline, bins=bin_edges, include_lowest=True)
        comparison_bins = pd.cut(comparison, bins=bin_edges, include_lowest=True)

        baseline_dist = baseline_bins.value_counts(normalize=True, dropna=False)
        comparison_dist = comparison_bins.value_counts(normalize=True, dropna=False)

        eps = 1e-6
        psi_value = 0.0
        for bin_key in baseline_dist.index:
            p = float(baseline_dist.get(bin_key, 0.0))
            q = float(comparison_dist.get(bin_key, 0.0))
            p = max(p, eps)
            q = max(q, eps)
            psi_value += (p - q) * np.log(p / q)

        return float(psi_value)

    def compute_all_features_psi(
        self, X_train: pd.DataFrame, X_test: pd.DataFrame
    ) -> Dict[str, Dict]:
        """
        批次計算所有特徵的 PSI
        Returns: {feature: {"psi": float, "stability": "stable"|"slight_shift"|"significant_shift"}}
        """

        results: Dict[str, Dict] = {}
        for feature in X_train.columns:
            psi_value = self.compute_psi(X_train[feature], X_test[feature])
            results[feature] = {
                "psi": float(psi_value),
                "stability": self.classify_psi(psi_value),
            }
        return results

    @staticmethod
    def classify_psi(psi_value: float) -> str:
        """PSI < 0.1 → stable, 0.1~0.25 → slight_shift, > 0.25 → significant_shift"""

        if not np.isfinite(psi_value):
            return "unknown"
        if psi_value < 0.1:
            return "stable"
        if psi_value <= 0.25:
            return "slight_shift"
        return "significant_shift"
