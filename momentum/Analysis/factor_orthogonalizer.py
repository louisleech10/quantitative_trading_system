"""Module 6: Factor orthogonalization analyzer."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
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

        n_samples, n_features = clean.shape
        # ICPERF Task 0.4 ㉑：同 PCA 之樣本數守門（:91-97）；n < p 時 QR 經濟形狀與欄名不符
        if n_samples < n_features:
            return pd.DataFrame(index=clean.index), {
                "module_name": "factor_orthogonalization",
                "skipped": True,
                "reason": f"n_samples({n_samples}) < n_features({n_features})",
                "error_type": "INSUFFICIENT_DATA",
            }

        order = self._resolve_priority_order(clean, priority_order)
        ordered = clean[order]

        # ICPERF Task 0.4 ㉑：對去均值、標準化欄做 Gram–Schmidt（含截距之逐步 OLS 殘差）；
        # 退化欄（殘差變異 ≤ 門檻 × 原變異，或原變異為 0）不入正交基、輸出零欄，
        # 避免數值零殘差之捨入方向污染其後各欄與 correlation_after。
        matrix = ordered.to_numpy(dtype=float)
        means = matrix.mean(axis=0)
        variances = matrix.var(axis=0)
        stds = np.sqrt(variances)
        centered = matrix - means
        standardized = np.zeros_like(centered)
        nonconstant = stds > 0
        standardized[:, nonconstant] = centered[:, nonconstant] / stds[nonconstant]

        orth_values = np.zeros_like(standardized)
        basis_cols: list[np.ndarray] = []
        features_meta: dict[str, dict] = {}
        degenerate_features: list[str] = []
        for idx, feature_name in enumerate(order):
            residual = standardized[:, idx].copy()
            if basis_cols:
                basis = np.column_stack(basis_cols)
                # 再正交化一次（"twice is enough"）以抑制古典 GS 之正交性流失
                residual -= basis @ (basis.T @ residual)
                residual -= basis @ (basis.T @ residual)
            original_variance = float(variances[idx])
            relative_variance = float(np.var(residual)) if nonconstant[idx] else 0.0
            residual_variance = relative_variance * original_variance
            degenerate = bool(
                (not nonconstant[idx]) or relative_variance <= self._degenerate_threshold
            )
            if degenerate:
                degenerate_features.append(feature_name)
            else:
                unit = residual / float(np.linalg.norm(residual))
                basis_cols.append(unit)
                orth_values[:, idx] = unit
            features_meta[feature_name] = {
                "residual_variance": residual_variance,
                "degenerate": degenerate,
            }
        orth = pd.DataFrame(orth_values, index=ordered.index, columns=order)

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
            # ICPERF Task 0.4 ㉑：值可為 float 或 compute_icir 之 dict（取 "icir"，ic_engine.py:488-493）；
            # 強度以 |ICIR| 降序（反向因子同強度同名次；同值依原欄序，穩定排序）
            strengths = {
                name: abs(self._icir_value(self._icir_scores[name]))
                if name in self._icir_scores
                else np.nan
                for name in factors.columns
            }
            if all(np.isfinite(value) for value in strengths.values()):
                return sorted(list(factors.columns), key=lambda name: strengths[name], reverse=True)

        proxy = factors.abs().mean().sort_values(ascending=False)
        return list(proxy.index)

    @staticmethod
    def _icir_value(value: object) -> float:
        """ICIR 分數：dict（compute_icir 輸出形狀）取 "icir"；無法讀為數值 ⇒ NaN（退回代理排序）。"""
        if isinstance(value, dict):
            value = value.get("icir", np.nan)
        try:
            return float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return float("nan")

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
