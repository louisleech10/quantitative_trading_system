"""Module 2: Factor centrality analyzer."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.core.logging import get_logger


logger = get_logger(__name__)


class FactorCentralityAnalyzer:
    def __init__(self, config: dict):
        cfg = config or {}
        self._config = cfg
        self._n_components = int(cfg.get("n_components", 5))
        self._rolling_window = int(cfg.get("rolling_window", 60))
        self._crowded_threshold = float(cfg.get("crowded_threshold", 0.3))
        self._min_samples = int(cfg.get("min_samples_for_pca", 30))

    def compute_centrality(self, ic_matrix: pd.DataFrame) -> dict | SkippedResult:
        if ic_matrix is None or ic_matrix.empty:
            return SkippedResult("factor_centrality", "empty ic matrix", "INSUFFICIENT_DATA")

        normalized = self._normalize_ic_matrix(ic_matrix)
        normalized = normalized.dropna(axis=1, how="all").dropna(axis=0, how="all")
        if normalized.shape[1] < 3:
            return SkippedResult(
                "factor_centrality",
                f"n_features({normalized.shape[1]}) < min_required(3)",
                "INSUFFICIENT_DATA",
            )
        if normalized.shape[0] < self._min_samples:
            return SkippedResult(
                "factor_centrality",
                f"n_samples({normalized.shape[0]}) < min_required({self._min_samples})",
                "INSUFFICIENT_DATA",
            )

        non_constant_cols = [c for c in normalized.columns if normalized[c].nunique(dropna=True) > 1]
        normalized = normalized[non_constant_cols]
        if normalized.shape[1] < 2:
            return SkippedResult("factor_centrality", "all features are constant", "INSUFFICIENT_DATA")

        try:
            n_components = min(self._n_components, normalized.shape[1] - 1, normalized.shape[0] - 1)
            n_components = max(1, n_components)
            scaler = StandardScaler()
            scaled = scaler.fit_transform(normalized.fillna(0.0))
            pca = PCA(n_components=n_components, svd_solver="auto")
            pca.fit(scaled)

            loadings = pca.components_.T
            evr = pca.explained_variance_ratio_
            centrality_values = (loadings * loadings) @ evr
            centrality = pd.Series(centrality_values, index=normalized.columns, dtype=float)
            rank_pct = centrality.rank(pct=True) * 100.0

            features = {}
            crowded_features: list[str] = []
            independent_features: list[str] = []
            for name, value in centrality.items():
                crowded = bool(value >= self._crowded_threshold)
                if crowded:
                    crowded_features.append(name)
                else:
                    independent_features.append(name)
                features[name] = {
                    "centrality": float(value),
                    "crowded": crowded,
                    "risk_level": "high" if crowded else "low",
                    "percentile_rank": float(rank_pct[name]),
                    "trend": "flat",
                }

            eigenvalues = pca.explained_variance_
            effective_rank = float((eigenvalues.sum() ** 2) / np.sum(eigenvalues ** 2)) if np.sum(eigenvalues ** 2) > 0 else 1.0

            return {
                "pca_summary": {
                    "explained_variance_ratio": evr.astype(float).tolist(),
                    "total_variance_explained": float(np.sum(evr)),
                    "effective_rank": effective_rank,
                    "n_components_used": int(n_components),
                },
                "features": features,
                "crowded_features": crowded_features,
                "independent_features": independent_features,
            }
        except Exception as exc:
            logger.warning("PCA centrality fallback due to: %s", exc)
            corr = normalized.corr(method="spearman").abs()
            corr = corr.replace([np.inf, -np.inf], np.nan).dropna(axis=0, how="all").dropna(axis=1, how="all")
            if corr.empty:
                return SkippedResult("factor_centrality", "correlation fallback failed", "NUMERICAL_ERROR")
            centrality = corr.mean(axis=1)
            if centrality.dropna().empty:
                return SkippedResult("factor_centrality", "correlation fallback empty", "NUMERICAL_ERROR")
            features = {
                name: {
                    "centrality": float(value),
                    "crowded": bool(value >= self._crowded_threshold),
                    "risk_level": "high" if value >= self._crowded_threshold else "low",
                    "percentile_rank": float((centrality.rank(pct=True) * 100.0)[name]),
                    "trend": "flat",
                }
                for name, value in centrality.items()
            }
            return {
                "pca_summary": {
                    "explained_variance_ratio": [],
                    "total_variance_explained": np.nan,
                    "effective_rank": np.nan,
                    "n_components_used": 0,
                    "fallback": "correlation_based",
                },
                "features": features,
                "crowded_features": [name for name, value in centrality.items() if value >= self._crowded_threshold],
                "independent_features": [name for name, value in centrality.items() if value < self._crowded_threshold],
            }

    def compute_rolling_centrality(
        self,
        ic_matrix: pd.DataFrame,
        window: Optional[int] = None,
    ) -> pd.DataFrame:
        if ic_matrix is None or ic_matrix.empty:
            return pd.DataFrame()

        n_rows = len(ic_matrix)
        use_window = int(window or self._rolling_window)
        use_window = min(use_window, n_rows)
        if use_window < 5:
            return pd.DataFrame()

        outputs: list[pd.Series] = []
        output_index: list[pd.Timestamp | int] = []
        for end in range(use_window, n_rows + 1):
            segment = ic_matrix.iloc[end - use_window : end]
            result = self.compute_centrality(segment)
            if isinstance(result, SkippedResult):
                continue
            features = result.get("features", {})
            if not features:
                continue
            outputs.append(pd.Series({k: float(v["centrality"]) for k, v in features.items()}))
            output_index.append(ic_matrix.index[end - 1])

        if not outputs:
            return pd.DataFrame()
        return pd.DataFrame(outputs, index=output_index).sort_index(axis=1)

    def detect_crowding_regime(
        self,
        rolling_centrality: pd.DataFrame,
        feature_name: str,
    ) -> dict:
        if rolling_centrality is None or rolling_centrality.empty or feature_name not in rolling_centrality.columns:
            return {
                "feature": feature_name,
                "regime": "unknown",
                "crowding_ratio": np.nan,
                "trend": "indeterminate",
            }

        series = rolling_centrality[feature_name].dropna()
        if series.empty:
            return {
                "feature": feature_name,
                "regime": "unknown",
                "crowding_ratio": np.nan,
                "trend": "indeterminate",
            }

        crowding_ratio = float((series >= self._crowded_threshold).mean())
        x = np.arange(len(series), dtype=float)
        slope = float(np.polyfit(x, series.values.astype(float), 1)[0]) if len(series) >= 3 else 0.0
        trend = "rising" if slope > 0 else "falling" if slope < 0 else "flat"
        regime = "crowded" if crowding_ratio >= 0.5 else "normal"
        return {
            "feature": feature_name,
            "regime": regime,
            "crowding_ratio": crowding_ratio,
            "trend": trend,
            "latest": float(series.iloc[-1]),
        }

    @staticmethod
    def _normalize_ic_matrix(ic_matrix: pd.DataFrame) -> pd.DataFrame:
        matrix = ic_matrix.copy()
        matrix = matrix.apply(pd.to_numeric, errors="coerce")
        matrix = matrix.replace([np.inf, -np.inf], np.nan)
        matrix = matrix.fillna(matrix.mean())
        return matrix
