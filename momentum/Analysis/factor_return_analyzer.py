"""Module 1: Factor return analysis."""

from __future__ import annotations

from typing import Optional, Any

import numpy as np
import pandas as pd

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.core.logging import get_logger


logger = get_logger(__name__)


class FactorReturnAnalyzer:
    def __init__(self, config: dict):
        cfg = config or {}
        self._config = cfg
        self._num_quantiles = int(cfg.get("num_quantiles", 5))
        self._risk_free_rate = float(cfg.get("risk_free_rate", 0.0))
        self._min_samples = 30

    def compute_factor_returns(
        self,
        feature: pd.Series,
        future_returns: pd.Series,
        num_quantiles: Optional[int] = None,
    ) -> dict | SkippedResult:
        data = pd.concat(
            [feature.rename("feature"), future_returns.rename("future_returns")],
            axis=1,
        ).dropna()

        if len(data) < self._min_samples:
            return SkippedResult(
                module_name="factor_return",
                reason=f"insufficient samples: {len(data)} < {self._min_samples}",
                error_type="INSUFFICIENT_DATA",
            )

        if data["feature"].nunique(dropna=True) <= 1:
            return SkippedResult(
                module_name="factor_return",
                reason="constant feature",
                error_type="INSUFFICIENT_DATA",
            )

        if np.nanstd(data["future_returns"].values.astype(float)) == 0.0:
            return SkippedResult(
                module_name="factor_return",
                reason="zero variance future_returns",
                error_type="INSUFFICIENT_DATA",
            )

        returns_w = self._winsorize_series(data["future_returns"])
        quantiles = int(num_quantiles or self._num_quantiles)
        bins, used_quantiles = self._assign_quantiles_with_fallback(data["feature"], quantiles)
        if bins is None:
            return SkippedResult(
                module_name="factor_return",
                reason="cannot form quantile bins",
                error_type="NUMERICAL_ERROR",
            )

        quantile_summary: dict[str, float] = {}
        cumulative_sampled: dict[str, list[float]] = {}

        low_returns = returns_w[bins == bins.min()].reset_index(drop=True)
        high_returns = returns_w[bins == bins.max()].reset_index(drop=True)
        paired_size = int(min(len(low_returns), len(high_returns)))
        if paired_size == 0:
            return SkippedResult(
                module_name="factor_return",
                reason="empty edge quantile",
                error_type="INSUFFICIENT_DATA",
            )

        for quantile_value in sorted(bins.dropna().unique()):
            label = f"Q{int(quantile_value) + 1}"
            series = returns_w[bins == quantile_value]
            quantile_summary[label] = float(series.mean()) if not series.empty else np.nan
            cumulative = (1.0 + series.astype(float)).cumprod() - 1.0
            cumulative_sampled[label] = self._sample_series(cumulative, max_points=100)

        ls_returns = high_returns.iloc[:paired_size] - low_returns.iloc[:paired_size]
        ls_cumulative = (1.0 + ls_returns).cumprod() - 1.0

        risk_metrics = self.compute_risk_metrics(
            ls_returns,
            risk_free_rate=self._risk_free_rate,
            periods_per_year=self._infer_periods_per_year(feature.index),
        )

        return {
            "quantile_returns_summary": quantile_summary,
            "long_short_mean_return": float(ls_returns.mean()),
            "risk_metrics": risk_metrics,
            "cumulative_returns_sampled": cumulative_sampled,
            "ls_cumulative_sampled": self._sample_series(ls_cumulative, max_points=100),
            "num_quantiles_used": used_quantiles,
            "newey_west_adjusted": False,
        }

    def compute_risk_metrics(
        self,
        returns: pd.Series,
        risk_free_rate: float = 0.0,
        periods_per_year: Optional[int] = None,
    ) -> dict:
        clean = pd.Series(returns, dtype=float).dropna()
        if clean.empty:
            return {
                "sharpe_ratio": np.nan,
                "sortino_ratio": np.nan,
                "calmar_ratio": np.nan,
                "max_drawdown": np.nan,
                "win_rate": np.nan,
                "annualized_return": np.nan,
                "annualized_volatility": np.nan,
            }

        periods = int(periods_per_year or 365)
        mean_return = float(clean.mean())
        std_return = float(clean.std(ddof=1))

        annualized_return = float((1.0 + mean_return) ** periods - 1.0)
        annualized_volatility = float(std_return * np.sqrt(periods)) if std_return > 0 else np.nan

        rf_period = risk_free_rate / periods
        sharpe = (
            float((mean_return - rf_period) / std_return * np.sqrt(periods))
            if std_return > 0
            else np.nan
        )

        downside = clean[clean < 0.0]
        downside_std = float(downside.std(ddof=1)) if len(downside) >= 2 else np.nan
        sortino = (
            float((mean_return - rf_period) / downside_std * np.sqrt(periods))
            if np.isfinite(downside_std) and downside_std > 0
            else np.nan
        )

        equity = (1.0 + clean).cumprod()
        rolling_peak = equity.cummax()
        drawdown = equity / rolling_peak - 1.0
        max_drawdown = float(drawdown.min()) if not drawdown.empty else np.nan
        calmar = (
            float(annualized_return / abs(max_drawdown))
            if np.isfinite(max_drawdown) and max_drawdown < 0
            else np.nan
        )

        return {
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar,
            "max_drawdown": max_drawdown,
            "win_rate": float((clean > 0).mean()),
            "annualized_return": annualized_return,
            "annualized_volatility": annualized_volatility,
        }

    def compute_batch(
        self,
        features_df: pd.DataFrame,
        future_returns: pd.Series,
        top_n: int = 30,
    ) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        selected_columns = list(features_df.columns)[: max(1, int(top_n))]

        for name in selected_columns:
            result = self.compute_factor_returns(features_df[name], future_returns)
            if isinstance(result, SkippedResult):
                results[name] = {
                    "skipped": True,
                    "reason": result.reason,
                    "error_type": result.error_type,
                }
            else:
                results[name] = result

        logger.info(
            "Factor return analysis completed: %s features", len(selected_columns)
        )
        return results

    @staticmethod
    def _winsorize_series(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
        s = pd.Series(series, dtype=float)
        low = float(s.quantile(lower))
        high = float(s.quantile(upper))
        return s.clip(lower=low, upper=high)

    def _assign_quantiles_with_fallback(self, feature: pd.Series, requested: int) -> tuple[pd.Series | None, int]:
        candidates = [requested]
        if requested > 3:
            candidates.append(3)
        if requested > 2:
            candidates.append(2)

        for q in candidates:
            if q < 2:
                continue
            try:
                bins = pd.qcut(feature, q=q, labels=False, duplicates="drop")
            except ValueError:
                continue
            if bins is None or bins.dropna().empty:
                continue
            actual = int(bins.dropna().nunique())
            if actual >= 2:
                return bins, actual
        return None, 0

    @staticmethod
    def _sample_series(series: pd.Series, max_points: int) -> list[float]:
        values = pd.Series(series, dtype=float).dropna().values
        if len(values) <= max_points:
            return values.astype(float).tolist()
        idx = np.linspace(0, len(values) - 1, max_points).astype(int)
        return values[idx].astype(float).tolist()

    @staticmethod
    def _infer_periods_per_year(index: pd.Index) -> int:
        if not isinstance(index, pd.DatetimeIndex) or len(index) < 2:
            return 365
        median_delta_hours = pd.Series(index).diff().dropna().dt.total_seconds().median() / 3600.0
        if not np.isfinite(median_delta_hours) or median_delta_hours <= 0:
            return 365
        return int(round((24.0 * 365.0) / median_delta_hours))
