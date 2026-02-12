"""Coverage analysis utilities for IC analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd


class CoverageAnalyzer:
    """因子覆蓋率分析 — 確保因子在大部分時間點有值。"""

    def compute_time_coverage(self, feature: pd.Series) -> float:
        """時間覆蓋率: count(非NaN) / total_bars。"""

        total = int(len(feature))
        if total == 0:
            return float("nan")
        return float(feature.notna().sum() / total)

    def compute_effective_start(self, feature: pd.Series) -> int:
        """有效起始點: 第一個非 NaN 的 index 位置。"""

        if feature.empty:
            return -1
        mask = feature.notna().to_numpy()
        if not mask.any():
            return -1
        return int(np.argmax(mask))

    def compute_all(self, features_df: pd.DataFrame) -> dict[str, dict]:
        """批次計算覆蓋率。"""

        results: dict[str, dict] = {}
        for feature_name in features_df.columns:
            series = features_df[feature_name]
            coverage = self.compute_time_coverage(series)
            effective_start = self.compute_effective_start(series)
            nan_count = int(series.isna().sum())
            results[feature_name] = {
                "coverage": coverage,
                "effective_start": effective_start,
                "nan_count": nan_count,
            }
        return results

    def flag_low_coverage(self, coverage_results: dict, threshold: float = 0.5) -> list[str]:
        """標記低覆蓋率特徵。"""

        low_features: list[str] = []
        for feature_name, metrics in (coverage_results or {}).items():
            coverage = metrics.get("coverage")
            if coverage is None or (isinstance(coverage, float) and np.isnan(coverage)):
                continue
            if coverage < threshold:
                low_features.append(feature_name)
        return low_features
