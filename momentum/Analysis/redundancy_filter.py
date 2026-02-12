"""Redundancy filter utilities for IC analysis."""

from __future__ import annotations

from typing import Optional, Protocol

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.linear_model import LinearRegression

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class IRedundancyFilter(Protocol):
    """Redundancy filter protocol (module-local)."""

    def filter(
        self,
        features_df: pd.DataFrame,
        ic_scores: dict,
        method: str = "greedy",
    ) -> tuple[pd.DataFrame, dict]:
        ...

    def compute_correlation_matrix(self, features_df: pd.DataFrame) -> pd.DataFrame:
        ...

    def greedy_dedup(
        self,
        corr_matrix: pd.DataFrame,
        ic_scores: dict,
        threshold: float = 0.7,
        tiebreaker: str = "icir",
    ) -> list[str]:
        ...

    def hierarchical_clustering(
        self,
        corr_matrix: pd.DataFrame,
        ic_scores: dict,
        linkage_method: str = "average",
    ) -> list[str]:
        ...

    def vif_filter(
        self,
        features_df: pd.DataFrame,
        max_vif: float = 10.0,
        ic_scores: Optional[dict] = None,
    ) -> list[str]:
        ...

    def compute_diversification_metrics(
        self,
        selected_features: list[str],
        corr_matrix: pd.DataFrame,
        metadata: dict,
    ) -> dict:
        ...


class RedundancyFilter:
    """Stage 6: 冗餘剔除 — 相關性矩陣 + 階層聚類 + VIF。"""

    def __init__(self, config: dict):
        self._config = config or {}
        self._method = self._config.get("method", "greedy")
        self._corr_threshold = float(self._config.get("correlation_threshold", 0.7))
        self._tiebreaker = self._config.get("tiebreaker", "icir")
        hierarchical = self._config.get("hierarchical", {}) or {}
        self._linkage_method = hierarchical.get("linkage_method", "average")
        vif_cfg = self._config.get("vif", {}) or {}
        self._max_vif = float(vif_cfg.get("max_vif", 10.0))

    def filter(
        self,
        features_df: pd.DataFrame,
        ic_scores: dict,
        method: str = "greedy",
    ) -> tuple[pd.DataFrame, dict]:
        """冗餘剔除主入口。"""

        if features_df is None:
            raise ValueError("features_df is required")
        if features_df.empty:
            return features_df.copy(), {
                "method": method,
                "input_features": 0,
                "output_features": 0,
                "removed_features": [],
            }

        method = method or self._method
        corr_matrix: Optional[pd.DataFrame] = None

        if method in {"greedy", "hierarchical"}:
            corr_matrix = self.compute_correlation_matrix(features_df)
            if method == "greedy":
                selected = self.greedy_dedup(
                    corr_matrix,
                    ic_scores,
                    threshold=self._corr_threshold,
                    tiebreaker=self._tiebreaker,
                )
            else:
                selected = self.hierarchical_clustering(
                    corr_matrix,
                    ic_scores,
                    linkage_method=self._linkage_method,
                )
        elif method == "vif":
            selected = self.vif_filter(
                features_df,
                max_vif=self._max_vif,
                ic_scores=ic_scores,
            )
        else:
            raise ValueError(f"unsupported redundancy method: {method}")

        selected = [name for name in features_df.columns if name in selected]
        removed = [name for name in features_df.columns if name not in selected]
        filtered_df = features_df[selected].copy()

        if corr_matrix is None:
            corr_matrix = (
                self.compute_correlation_matrix(filtered_df)
                if len(selected) > 1
                else pd.DataFrame(index=selected, columns=selected, data=1.0)
            )

        log = {
            "method": method,
            "input_features": int(len(features_df.columns)),
            "output_features": int(len(selected)),
            "removed_features": removed,
            "correlation_threshold": self._corr_threshold,
        }

        logger.info(
            "Redundancy filter completed: method=%s input=%s output=%s",
            method,
            len(features_df.columns),
            len(selected),
        )

        return filtered_df, log

    def compute_correlation_matrix(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """計算特徵間 Pearson 相關性矩陣。"""

        if features_df.empty:
            return pd.DataFrame()

        numeric_df = features_df.apply(pd.to_numeric, errors="coerce")
        values = numeric_df.to_numpy(dtype=float)
        if np.isnan(values).any():
            return numeric_df.corr(method="pearson")

        mean = values.mean(axis=0)
        values = values - mean
        std = values.std(axis=0, ddof=1)
        std[std == 0] = np.nan
        values = values / std
        corr = (values.T @ values) / (values.shape[0] - 1)
        corr = np.clip(corr, -1.0, 1.0)
        return pd.DataFrame(corr, index=numeric_df.columns, columns=numeric_df.columns)

    def greedy_dedup(
        self,
        corr_matrix: pd.DataFrame,
        ic_scores: dict,
        threshold: float = 0.7,
        tiebreaker: str = "icir",
    ) -> list[str]:
        """貪婪去重：按 ICIR 排序，逐一檢查相關性。"""

        if corr_matrix.empty:
            return []

        features = list(corr_matrix.columns)
        ordered = sorted(
            features,
            key=lambda name: self._score_value(ic_scores, name, tiebreaker),
            reverse=True,
        )

        selected: list[str] = []
        for feature in ordered:
            if not selected:
                selected.append(feature)
                continue

            correlations = corr_matrix.loc[feature, selected].abs()
            if correlations.isna().all():
                selected.append(feature)
                continue

            if (correlations > threshold).any():
                continue

            selected.append(feature)

        return selected

    def hierarchical_clustering(
        self,
        corr_matrix: pd.DataFrame,
        ic_scores: dict,
        linkage_method: str = "average",
    ) -> list[str]:
        """階層聚類：每個 cluster 保留 ICIR 最高的特徵。"""

        if corr_matrix.empty:
            return []

        features = list(corr_matrix.columns)
        if len(features) <= 1:
            return features

        abs_corr = corr_matrix.abs().fillna(0.0)
        distance = 1.0 - abs_corr
        np.fill_diagonal(distance.values, 0.0)

        condensed = squareform(distance.values, checks=False)
        linkage_matrix = linkage(condensed, method=linkage_method)
        threshold = 1.0 - float(self._corr_threshold)
        clusters = fcluster(linkage_matrix, t=threshold, criterion="distance")

        cluster_map: dict[int, list[str]] = {}
        for feature, cluster_id in zip(features, clusters):
            cluster_map.setdefault(int(cluster_id), []).append(feature)

        selected: list[str] = []
        for members in cluster_map.values():
            best = max(
                members,
                key=lambda name: self._score_value(ic_scores, name, self._tiebreaker),
            )
            selected.append(best)

        return selected

    def vif_filter(
        self,
        features_df: pd.DataFrame,
        max_vif: float = 10.0,
        ic_scores: Optional[dict] = None,
    ) -> list[str]:
        """VIF 篩選：逐步移除 VIF > threshold 的特徵。"""

        if features_df.empty:
            return []

        features = list(features_df.columns)
        data = features_df[features].apply(pd.to_numeric, errors="coerce").dropna()
        if data.empty or data.shape[1] <= 1:
            return features

        while True:
            vifs = self._compute_vif_scores(data)
            if not vifs:
                break

            max_feature, max_value = max(vifs.items(), key=lambda item: item[1])
            if max_value <= max_vif or len(features) <= 1:
                return features

            candidates = [name for name, value in vifs.items() if value == max_value]
            if len(candidates) > 1 and ic_scores:
                max_feature = min(
                    candidates,
                    key=lambda name: self._score_value(ic_scores, name, self._tiebreaker),
                )

            features.remove(max_feature)
            data = data[features]
            if data.shape[1] <= 1:
                break

        return features

    def compute_diversification_metrics(
        self,
        selected_features: list[str],
        corr_matrix: pd.DataFrame,
        metadata: dict,
    ) -> dict:
        """多元化指標。"""

        if not selected_features:
            return {
                "avg_abs_correlation": float("nan"),
                "max_correlation": float("nan"),
                "effective_independent_features": 0.0,
                "category_coverage": 0.0,
                "data_source_coverage": 0.0,
                "layer_coverage": 0.0,
            }

        if corr_matrix.empty or not set(selected_features).issubset(
            set(corr_matrix.index)
        ):
            sub_corr = pd.DataFrame(
                np.eye(len(selected_features)),
                index=selected_features,
                columns=selected_features,
            )
        else:
            sub_corr = corr_matrix.loc[selected_features, selected_features]
        abs_corr = sub_corr.abs().fillna(0.0)
        upper = abs_corr.where(
            np.triu(np.ones(abs_corr.shape), k=1).astype(bool)
        )
        values = upper.stack().to_numpy()
        if values.size == 0:
            avg_abs = 0.0
            max_corr = 0.0
        else:
            avg_abs = float(np.mean(values))
            max_corr = float(np.max(values))

        n_features = len(selected_features)
        if n_features <= 1:
            effective = 1.0
        else:
            effective = float(n_features / (1.0 + avg_abs * (n_features - 1)))

        category_coverage = self._compute_coverage(
            metadata, selected_features, "category"
        )
        data_source_coverage = self._compute_coverage(
            metadata, selected_features, "data_source"
        )
        layer_coverage = self._compute_coverage(metadata, selected_features, "layer")

        return {
            "avg_abs_correlation": avg_abs,
            "max_correlation": max_corr,
            "effective_independent_features": effective,
            "category_coverage": category_coverage,
            "data_source_coverage": data_source_coverage,
            "layer_coverage": layer_coverage,
        }

    def _compute_vif_scores(self, data: pd.DataFrame) -> dict[str, float]:
        vifs: dict[str, float] = {}
        matrix = data.to_numpy(dtype=float)
        for idx, feature in enumerate(data.columns):
            y = matrix[:, idx]
            x = np.delete(matrix, idx, axis=1)
            if x.size == 0:
                vifs[feature] = 1.0
                continue
            if np.nanstd(y) == 0:
                vifs[feature] = float("inf")
                continue
            try:
                model = LinearRegression()
                model.fit(x, y)
                r2 = model.score(x, y)
            except Exception as exc:  # noqa: BLE001
                logger.warning("VIF regression failed for %s: %s", feature, exc)
                vifs[feature] = float("inf")
                continue

            if r2 >= 0.999999:
                vifs[feature] = float("inf")
            else:
                vifs[feature] = float(1.0 / (1.0 - r2))
        return vifs

    @staticmethod
    def _score_value(ic_scores: dict, name: str, tiebreaker: str) -> float:
        if not ic_scores:
            return float("-inf")
        value = ic_scores.get(name)
        if isinstance(value, dict):
            score = value.get(tiebreaker)
            if score is None:
                score = value.get("icir", float("nan"))
            score_value = float(score)
            return score_value if np.isfinite(score_value) else float("-inf")
        if isinstance(value, (int, float)):
            score_value = float(value)
            return score_value if np.isfinite(score_value) else float("-inf")
        return float("-inf")

    @staticmethod
    def _compute_coverage(metadata: dict, selected: list[str], key: str) -> float:
        if not metadata:
            return 0.0

        total_values = {info.get(key) for info in metadata.values() if info}
        total_values.discard(None)
        if not total_values:
            return 0.0

        selected_values = set()
        for name in selected:
            info = metadata.get(name, {}) if metadata else {}
            value = info.get(key)
            if value is not None:
                selected_values.add(value)

        return float(len(selected_values) / len(total_values))
