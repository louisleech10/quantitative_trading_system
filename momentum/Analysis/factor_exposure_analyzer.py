"""Module 7: Factor exposure analyzer."""

from __future__ import annotations

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class FactorExposureAnalyzer:
    def __init__(self, config: dict):
        cfg = config or {}
        self._config = cfg
        self._max_single_exposure = float(cfg.get("max_single_exposure", 0.4))

    def calculate_portfolio_exposure(
        self,
        positions: pd.Series,
        factor_values: pd.DataFrame,
    ) -> pd.Series:
        if factor_values is None or factor_values.empty:
            return pd.Series(dtype=float)

        weights = pd.Series(positions, dtype=float).reindex(factor_values.index).fillna(0.0)
        abs_sum = float(weights.abs().sum())
        if abs_sum == 0.0:
            return pd.Series(0.0, index=factor_values.columns, dtype=float)
        if not np.isclose(abs_sum, 1.0):
            weights = weights / abs_sum

        exposure = factor_values.apply(pd.to_numeric, errors="coerce").fillna(0.0).T @ weights
        return exposure.astype(float)

    def calculate_factor_attribution(
        self,
        portfolio_returns: pd.Series,
        factor_returns: pd.DataFrame,
    ) -> dict:
        aligned = pd.concat(
            [portfolio_returns.rename("portfolio"), factor_returns],
            axis=1,
        ).dropna()

        if aligned.shape[0] < 10 or aligned.shape[1] < 2:
            return {
                "factor_betas": {},
                "alpha": np.nan,
                "r_squared": np.nan,
                "attribution": {},
                "unexplained": np.nan,
            }

        y = aligned["portfolio"].values.astype(float)
        x = aligned.drop(columns=["portfolio"]).values.astype(float)
        x = np.column_stack([np.ones(len(x)), x])

        beta, *_ = np.linalg.lstsq(x, y, rcond=None)
        y_pred = x @ beta
        residual = y - y_pred

        ss_res = float(np.sum(residual ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0

        factor_names = list(aligned.drop(columns=["portfolio"]).columns)
        factor_betas = {name: float(beta[idx + 1]) for idx, name in enumerate(factor_names)}
        factor_means = aligned[factor_names].mean()
        attribution = {
            name: float(factor_betas[name] * factor_means[name]) for name in factor_names
        }

        return {
            "factor_betas": factor_betas,
            "alpha": float(beta[0]),
            "r_squared": r_squared,
            "attribution": attribution,
            "unexplained": float(beta[0]),
        }

    def monitor_exposure_concentration(
        self,
        exposures: pd.Series,
        max_single_exposure: float = 0.4,
    ) -> dict:
        values = pd.Series(exposures, dtype=float).fillna(0.0)
        abs_values = values.abs()
        total = float(abs_values.sum())
        if total == 0.0:
            return {
                "max_exposure_factor": None,
                "max_exposure_value": 0.0,
                "hhi": 0.0,
                "concentrated": False,
                "warnings": ["near_zero_exposures"],
            }

        normalized = abs_values / total
        hhi = float(np.sum(np.square(normalized.values.astype(float))))
        max_factor = str(normalized.idxmax())
        max_value = float(normalized.loc[max_factor])

        threshold = float(max_single_exposure or self._max_single_exposure)
        warnings: list[str] = []
        if max_value > threshold:
            warnings.append("single_factor_exposure_too_high")
        if np.all(normalized.values < 0.05):
            warnings.append("near_zero_exposures")

        return {
            "max_exposure_factor": max_factor,
            "max_exposure_value": max_value,
            "hhi": hhi,
            "concentrated": bool(max_value > threshold),
            "warnings": warnings,
        }
