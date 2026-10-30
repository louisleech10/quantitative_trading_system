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
        # ICPERF Task 0.4 ⑲（CT-10）：擁擠 ⟺ centrality_i ≥ τ·mean_j(centrality_j)（主路徑、退回路徑、逐窗同一定義）。
        # 舊絕對門檻 `crowded_threshold` 已不再使用（0.3 於 p ≥ 4 恆不觸發）；SPEC 原定 τ／p 亦恆不觸發
        # （標準化後 centrality_i＝共同性 h_i²／p ≤ 1／p），主委裁定改 τ·mean。
        self._tau = float(cfg.get("crowding_threshold_relative", 1.5))
        self._min_samples = int(cfg.get("min_samples_for_pca", 30))

    def _crowded_cut(self, values: np.ndarray) -> float:
        """擁擠門檻：τ × 有限值之平均；無有限值或平均 ≤ 0（含非有限）⇒ +inf（無人擁擠）。"""
        arr = np.asarray(values, dtype=float)
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            return float("inf")
        mean = float(arr.mean())
        if not np.isfinite(mean) or mean <= 0.0:
            return float("inf")
        return self._tau * mean

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
            # ICPERF Task 0.4 ⑱（CT-3、CT-4）：精確全 SVD（不走 randomized，可重現），取全部成分以供有效秩，
            # 中心性只用前 n_components 個成分
            pca = PCA(n_components=None, svd_solver="full")
            pca.fit(scaled)

            loadings = pca.components_[:n_components].T
            evr = pca.explained_variance_ratio_[:n_components]
            centrality_values = (loadings * loadings) @ evr
            centrality = pd.Series(centrality_values, index=normalized.columns, dtype=float)
            rank_pct = centrality.rank(pct=True) * 100.0
            crowded_cut = self._crowded_cut(centrality.to_numpy())

            features = {}
            crowded_features: list[str] = []
            independent_features: list[str] = []
            for name, value in centrality.items():
                crowded = bool(value >= crowded_cut)
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

            # CT-3：有效秩（參與率 (Σλ)²／Σλ²）以全部特徵值計
            eigenvalues = np.clip(np.asarray(pca.explained_variance_, dtype=float), 0.0, None)
            effective_rank = float((eigenvalues.sum() ** 2) / np.sum(eigenvalues ** 2)) if np.sum(eigenvalues ** 2) > 0 else 1.0

            return {
                "pca_summary": {
                    "explained_variance_ratio": evr.astype(float).tolist(),
                    "total_variance_explained": float(np.sum(evr)),
                    "effective_rank": effective_rank,
                    "n_components_used": int(n_components),
                    # ⑲：實際擁擠門檻（τ × 跨特徵平均）供前端畫參考線；不判擁擠（+inf）⇒ None
                    "crowded_threshold": float(crowded_cut) if np.isfinite(crowded_cut) else None,
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
            # ICPERF Task 0.4 ⑱（CT-8）：平均絕對相關不含自身（去對角線）
            arr = corr.to_numpy(dtype=float, copy=True)
            np.fill_diagonal(arr, np.nan)
            finite = np.isfinite(arr)
            counts = finite.sum(axis=1)
            sums = np.where(finite, arr, 0.0).sum(axis=1)
            with np.errstate(invalid="ignore", divide="ignore"):
                centrality = pd.Series(np.where(counts > 0, sums / np.maximum(counts, 1), np.nan),
                                       index=corr.index, dtype=float)
            if centrality.dropna().empty:
                return SkippedResult("factor_centrality", "correlation fallback empty", "NUMERICAL_ERROR")
            # ⑲：與主路徑同一定義（τ × 跨特徵平均）
            fallback_cut = self._crowded_cut(centrality.to_numpy())
            rank_pct = centrality.rank(pct=True) * 100.0
            features = {
                name: {
                    "centrality": float(value),
                    "crowded": bool(value >= fallback_cut),
                    "risk_level": "high" if value >= fallback_cut else "low",
                    "percentile_rank": float(rank_pct[name]),
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
                    "crowded_threshold": float(fallback_cut) if np.isfinite(fallback_cut) else None,
                    "fallback": "correlation_based",
                },
                "features": features,
                "crowded_features": [name for name, value in centrality.items() if value >= fallback_cut],
                "independent_features": [name for name, value in centrality.items() if not value >= fallback_cut],
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

        # ICPERF Task 0.4 ⑱（CT-7）：每一窗終點恆留一列（略過之窗為全 NaN），索引為輸入矩陣之窗終點
        # （輸入帶時間戳即帶時間戳）——序列與滾動 IC 之時間軸逐位置對應
        outputs: list[dict] = []
        output_index: list[pd.Timestamp | int] = []
        any_valid = False
        for end in range(use_window, n_rows + 1):
            segment = ic_matrix.iloc[end - use_window : end]
            result = self.compute_centrality(segment)
            row: dict = {}
            if not isinstance(result, SkippedResult):
                features = result.get("features", {})
                row = {k: float(v["centrality"]) for k, v in features.items()}
            any_valid = any_valid or bool(row)
            outputs.append(row)
            output_index.append(ic_matrix.index[end - 1])

        if not any_valid:
            return pd.DataFrame()
        return pd.DataFrame(outputs, index=output_index, dtype=float).sort_index(axis=1)

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

        column = rolling_centrality[feature_name].to_numpy(dtype=float)
        mask = ~np.isnan(column)
        if not mask.any():
            return {
                "feature": feature_name,
                "regime": "unknown",
                "crowding_ratio": np.nan,
                "trend": "indeterminate",
            }

        series = pd.Series(column[mask])
        # ⑲（CT-10）：逐窗門檻＝τ × 該窗（同列）有限值之平均
        rows = rolling_centrality.to_numpy(dtype=float)[mask]
        cuts = np.array([self._crowded_cut(row) for row in rows], dtype=float)
        crowding_ratio = float(np.mean(series.to_numpy() >= cuts))
        # ⑱（CT-6、CT-7）：x＝原始窗位置（略過之窗不壓縮時間軸）；常數序列斜率依定義為 0
        x = np.flatnonzero(mask).astype(float)
        if len(series) >= 3 and series.nunique() > 1:
            slope = float(np.polyfit(x, series.to_numpy(dtype=float), 1)[0])
        else:
            slope = 0.0
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
