"""Monotonicity testing utilities for IC analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class MonotonicityTester:
    """Stage 5 (部分): 單調性驗證。"""

    def __init__(self, config: dict):
        self._config = config or {}
        self._default_quantiles = int(self._config.get("num_quantiles", 5))
        self._min_group_size = int(self._config.get("min_group_size", 30))

    def compute_quantile_returns(
        self,
        feature: pd.Series,
        label: pd.Series,
        num_quantiles: int = 5,
    ) -> dict:
        """分位數收益分析。"""

        data = self._prepare_data(feature, label)
        if data.empty:
            return self._empty_quantile_result(num_quantiles)

        num_quantiles = self._select_num_quantiles(
            len(data), num_quantiles or self._default_quantiles
        )
        quantile_bins = self._assign_quantiles(data, num_quantiles)
        if quantile_bins is None:
            return self._empty_quantile_result(num_quantiles)

        quantile_mean_returns = {}
        cumulative_returns = {}
        for quantile in sorted(quantile_bins.unique()):
            label_key = f"Q{quantile + 1}"
            mask = quantile_bins == quantile
            values = data.loc[mask, "label"].astype(float)
            if values.empty:
                quantile_mean_returns[label_key] = np.nan
                cumulative_returns[label_key] = []
            else:
                quantile_mean_returns[label_key] = float(values.mean())
                cumulative_returns[label_key] = (
                    values.cumsum().astype(float).tolist()
                )

        long_short = self.compute_long_short_spread(
            feature, label, num_quantiles=num_quantiles
        )

        return {
            "quantile_mean_returns": quantile_mean_returns,
            "long_short_spread": long_short["spread"],
            "long_short_tstat": long_short["tstat"],
            "cumulative_returns": cumulative_returns,
        }

    def compute_monotonicity_score(self, quantile_returns: dict) -> float:
        """單調性評分 (0.0 ~ 1.0)。"""

        mean_returns = quantile_returns.get("quantile_mean_returns", {})
        if not mean_returns:
            return 0.0

        ordered_keys = sorted(mean_returns.keys())
        values = [mean_returns[key] for key in ordered_keys]
        diffs = np.diff(values)
        if diffs.size == 0:
            return 0.0

        score = float(np.mean(diffs > 0))
        return max(0.0, min(1.0, score))

    def compute_long_short_spread(
        self,
        feature: pd.Series,
        label: pd.Series,
        num_quantiles: int = 5,
    ) -> dict:
        """Long-Short Spread + t-test。"""

        data = self._prepare_data(feature, label)
        if data.empty:
            return {
                "spread": np.nan,
                "tstat": np.nan,
                "pvalue": np.nan,
                "sharpe": np.nan,
            }

        num_quantiles = self._select_num_quantiles(
            len(data), num_quantiles or self._default_quantiles
        )
        quantile_bins = self._assign_quantiles(data, num_quantiles)
        if quantile_bins is None:
            return {
                "spread": np.nan,
                "tstat": np.nan,
                "pvalue": np.nan,
                "sharpe": np.nan,
            }

        low_mask = quantile_bins == quantile_bins.min()
        high_mask = quantile_bins == quantile_bins.max()
        low_values = data.loc[low_mask, "label"].astype(float)
        high_values = data.loc[high_mask, "label"].astype(float)

        if low_values.empty or high_values.empty:
            return {
                "spread": np.nan,
                "tstat": np.nan,
                "pvalue": np.nan,
                "sharpe": np.nan,
            }

        spread = float(high_values.mean() - low_values.mean())
        ttest = stats.ttest_ind(
            high_values, low_values, nan_policy="omit"
        )
        tstat = float(ttest.statistic)
        pvalue = float(ttest.pvalue)
        sharpe = self._compute_pooled_sharpe(low_values, high_values, spread)

        return {
            "spread": spread,
            "tstat": tstat,
            "pvalue": pvalue,
            "sharpe": sharpe,
        }

    def compute_all(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        num_quantiles: int = 5,
    ) -> dict[str, dict]:
        """批次計算所有特徵的單調性指標。"""

        results: dict[str, dict] = {}
        for feature in features_df.columns:
            quantile_returns = self.compute_quantile_returns(
                features_df[feature], label, num_quantiles=num_quantiles
            )
            monotonicity_score = self.compute_monotonicity_score(
                quantile_returns
            )
            long_short = self.compute_long_short_spread(
                features_df[feature], label, num_quantiles=num_quantiles
            )
            results[feature] = {
                "quantile_returns": quantile_returns,
                "monotonicity_score": monotonicity_score,
                "long_short": long_short,
            }
        return results

    def _prepare_data(
        self, feature: pd.Series, label: pd.Series
    ) -> pd.DataFrame:
        data = pd.concat(
            [feature.rename("feature"), label.rename("label")], axis=1
        ).dropna()
        return data

    def _select_num_quantiles(self, n_samples: int, requested: int) -> int:
        requested = max(int(requested), 2)
        if requested > 3 and n_samples / requested < self._min_group_size:
            return 3
        return requested

    def _assign_quantiles(
        self, data: pd.DataFrame, num_quantiles: int
    ) -> pd.Series | None:
        try:
            bins = pd.qcut(
                data["feature"], q=num_quantiles, labels=False, duplicates="drop"
            )
        except ValueError as exc:
            logger.warning("qcut failed: %s", exc)
            if num_quantiles > 3:
                return self._assign_quantiles(data, 3)
            return None

        if bins.isna().all():
            return None

        actual_bins = int(bins.max()) + 1
        if actual_bins < num_quantiles and num_quantiles > 3:
            return self._assign_quantiles(data, 3)
        return bins

    @staticmethod
    def _compute_pooled_sharpe(
        low_values: pd.Series, high_values: pd.Series, spread: float
    ) -> float:
        low_values = low_values.astype(float)
        high_values = high_values.astype(float)
        n1 = len(low_values)
        n2 = len(high_values)
        if n1 < 2 or n2 < 2:
            return np.nan
        var1 = float(np.nanvar(low_values, ddof=1))
        var2 = float(np.nanvar(high_values, ddof=1))
        pooled = ((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2)
        if pooled <= 0:
            return np.nan
        return float(spread / np.sqrt(pooled))

    @staticmethod
    def _empty_quantile_result(num_quantiles: int) -> dict:
        quantile_mean_returns = {
            f"Q{i + 1}": np.nan for i in range(num_quantiles)
        }
        cumulative_returns = {f"Q{i + 1}": [] for i in range(num_quantiles)}
        return {
            "quantile_mean_returns": quantile_mean_returns,
            "long_short_spread": np.nan,
            "long_short_tstat": np.nan,
            "cumulative_returns": cumulative_returns,
        }
