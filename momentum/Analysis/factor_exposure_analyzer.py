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
        self._neutralization_mode = str(cfg.get("neutralization_mode", "none") or "none")
        self._neutralization_lookback = int(cfg.get("neutralization_lookback", 63) or 63)

    def neutralize_factor_matrix(
        self,
        factor_values: pd.DataFrame,
        market_proxy: pd.Series,
        mode: str | None = None,
        lookback: int | None = None,
    ) -> pd.DataFrame:
        if factor_values is None or factor_values.empty:
            return pd.DataFrame()

        normalized = factor_values.apply(pd.to_numeric, errors="coerce")
        effective_mode = str(mode or self._neutralization_mode or "none")

        if effective_mode == "none":
            return normalized.fillna(0.0)
        if effective_mode == "beta_neutral":
            return self._apply_beta_neutralization(normalized, market_proxy)
        if effective_mode == "vol_neutral":
            effective_lookback = int(lookback or self._neutralization_lookback)
            return self._apply_vol_neutralization(normalized, effective_lookback)

        logger.warning("unknown neutralization mode: %s", effective_mode)
        return normalized.fillna(0.0)

    def _apply_beta_neutralization(
        self,
        factor_values: pd.DataFrame,
        market_proxy: pd.Series,
    ) -> pd.DataFrame:
        proxy = pd.to_numeric(market_proxy, errors="coerce").reindex(factor_values.index)
        if proxy.notna().sum() < 10:
            logger.warning("beta-neutral skipped: insufficient market proxy samples")
            return factor_values.fillna(0.0)

        proxy_var = float(np.nanvar(proxy.to_numpy(dtype=float)))
        if np.isclose(proxy_var, 0.0):
            logger.warning("beta-neutral skipped: market proxy variance near zero")
            return factor_values.fillna(0.0)

        neutralized = pd.DataFrame(index=factor_values.index)
        for column_name in factor_values.columns:
            feature_series = pd.to_numeric(factor_values[column_name], errors="coerce")
            aligned = pd.concat([feature_series.rename("x"), proxy.rename("m")], axis=1).dropna()
            if len(aligned) < 10:
                neutralized[column_name] = feature_series
                continue

            covariance = float(np.cov(aligned["x"].to_numpy(), aligned["m"].to_numpy(), ddof=0)[0, 1])
            beta = covariance / proxy_var if not np.isclose(proxy_var, 0.0) else 0.0
            neutralized[column_name] = feature_series - beta * proxy

        return neutralized.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    def _apply_vol_neutralization(
        self,
        factor_values: pd.DataFrame,
        lookback: int,
    ) -> pd.DataFrame:
        window = max(5, int(lookback))
        rolling_std = factor_values.rolling(window=window, min_periods=max(5, window // 3)).std()
        stabilized = rolling_std.replace(0.0, np.nan)
        neutralized = factor_values / stabilized
        return neutralized.replace([np.inf, -np.inf], np.nan).fillna(0.0)

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
