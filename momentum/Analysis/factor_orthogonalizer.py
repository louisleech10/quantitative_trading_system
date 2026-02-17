"""Module 6: Factor orthogonalization analyzer."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from scipy.linalg import qr
from sklearn.decomposition import PCA

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class FactorOrthogonalizer:
    def __init__(self, config: dict):
        cfg = config or {}
        self._config = cfg
        self._degenerate_threshold = float(cfg.get("degenerate_threshold", 1e-10))
        self._icir_scores = cfg.get("icir_scores", {}) if isinstance(cfg.get("icir_scores", {}), dict) else {}

    def gram_schmidt(
        self,
        factors: pd.DataFrame,
        priority_order: Optional[list[str]] = None,
    ) -> tuple[pd.DataFrame, dict]:
        clean = factors.apply(pd.to_numeric, errors="coerce").dropna(axis=0, how="any")
        if clean.shape[1] < 2:
            return pd.DataFrame(index=clean.index), {
                "module_name": "factor_orthogonalization",
                "skipped": True,
                "reason": "n_features < 2",
                "error_type": "INSUFFICIENT_DATA",
            }

        order = self._resolve_priority_order(clean, priority_order)
        ordered = clean[order]

        matrix = ordered.values.astype(float)
        q_matrix, _ = qr(matrix, mode="economic")
        orth = pd.DataFrame(q_matrix, index=ordered.index, columns=order)

        features_meta: dict[str, dict] = {}
        degenerate_features: list[str] = []
        for idx, feature_name in enumerate(order):
            target = matrix[:, idx]
            if idx == 0:
                residual = target
            else:
                basis = q_matrix[:, :idx]
                projection = basis @ (basis.T @ target)
                residual = target - projection
            residual_variance = float(np.var(residual))
            degenerate = bool(residual_variance <= self._degenerate_threshold)
            if degenerate:
                degenerate_features.append(feature_name)
            features_meta[feature_name] = {
                "residual_variance": residual_variance,
                "degenerate": degenerate,
            }

        corr_before = ordered.corr().abs()
        corr_after = orth.corr().abs()

        return orth, {
            "method": "gram_schmidt",
            "priority_order": order,
            "correlation_before": self._mean_off_diagonal(corr_before),
            "correlation_after": self._mean_off_diagonal(corr_after),
            "features": features_meta,
            "degenerate_features": degenerate_features,
        }

    def pca_orthogonalize(
        self,
        factors: pd.DataFrame,
        n_components: Optional[int] = None,
    ) -> tuple[pd.DataFrame, dict]:
        clean = factors.apply(pd.to_numeric, errors="coerce").dropna(axis=0, how="any")
        n_samples, n_features = clean.shape
        if n_features < 2:
            return pd.DataFrame(index=clean.index), {
                "module_name": "factor_orthogonalization",
                "skipped": True,
                "reason": "n_features < 2",
                "error_type": "INSUFFICIENT_DATA",
            }
        if n_samples < n_features:
            return pd.DataFrame(index=clean.index), {
                "module_name": "factor_orthogonalization",
                "skipped": True,
                "reason": f"n_samples({n_samples}) < n_features({n_features})",
                "error_type": "INSUFFICIENT_DATA",
            }

        max_components = min(n_samples - 1, n_features)
        use_components = int(n_components or max_components)
        use_components = max(1, min(use_components, max_components))

        pca = PCA(n_components=use_components)
        transformed = pca.fit_transform(clean.values.astype(float))
        pc_names = [f"PC{i + 1}" for i in range(use_components)]
        transformed_df = pd.DataFrame(transformed, index=clean.index, columns=pc_names)

        loadings = pd.DataFrame(
            pca.components_.T,
            index=clean.columns,
            columns=pc_names,
        )

        return transformed_df, {
            "method": "pca",
            "n_components": use_components,
            "explained_variance_ratio": pca.explained_variance_ratio_.astype(float).tolist(),
            "loadings": loadings.to_dict(orient="index"),
            "principal_components": pc_names,
        }

    def _resolve_priority_order(
        self,
        factors: pd.DataFrame,
        priority_order: Optional[list[str]],
    ) -> list[str]:
        if priority_order:
            valid = [name for name in priority_order if name in factors.columns]
            remain = [name for name in factors.columns if name not in valid]
            return valid + remain

        if self._icir_scores:
            order = sorted(
                list(factors.columns),
                key=lambda name: float(self._icir_scores.get(name, -np.inf)),
                reverse=True,
            )
            if all(np.isfinite(float(self._icir_scores.get(name, np.nan))) for name in order):
                return order

        proxy = factors.abs().mean().sort_values(ascending=False)
        return list(proxy.index)

    @staticmethod
    def _mean_off_diagonal(corr_matrix: pd.DataFrame) -> float:
        if corr_matrix.empty or corr_matrix.shape[0] < 2:
            return 0.0
        values = corr_matrix.values.astype(float)
        mask = ~np.eye(values.shape[0], dtype=bool)
        selected = values[mask]
        if selected.size == 0:
            return 0.0
        return float(np.nanmean(selected))
