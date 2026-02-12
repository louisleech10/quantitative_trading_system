"""Turnover analysis utilities for IC analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class TurnoverAnalyzer:
    """因子換手率分析 — 評估交易可行性。"""

    def __init__(self, config: dict):
        self._config = config or {}
        self._transaction_cost = float(self._config.get("transaction_cost", 0.001))
        self._num_quantiles = int(self._config.get("num_quantiles", 5))

    def compute_quantile_turnover(self, feature: pd.Series, num_quantiles: int = 5) -> float:
        """分位數換手率：頂部分位 (Q5) 的成分每期變化比例。"""

        series = feature.dropna()
        if series.empty or series.size < 2:
            return float("nan")

        num_quantiles = max(int(num_quantiles or self._num_quantiles), 2)
        try:
            quantiles = pd.qcut(series, q=num_quantiles, labels=False, duplicates="drop")
        except ValueError as exc:
            logger.warning("qcut failed for turnover: %s", exc)
            return float("nan")

        top_mask = quantiles == quantiles.max()
        changes = top_mask.astype(int).diff().abs().dropna()
        if changes.empty:
            return 0.0
        return float(changes.mean())

    def compute_rank_change_rate(self, feature: pd.Series) -> float:
        """排名變化率：所有因子排名的平均位移。"""

        series = feature.dropna()
        if series.size < 2:
            return float("nan")

        ranks = series.rank(method="average")
        diffs = ranks.diff().abs().dropna()
        if diffs.empty:
            return 0.0
        return float(diffs.mean())

    def compute_factor_autocorrelation(self, feature: pd.Series) -> float:
        """因子自相關：corr(values_t, values_{t-1})。"""

        series = feature.dropna()
        if series.size < 2:
            return float("nan")
        return float(series.autocorr(lag=1))

    def compute_net_ic_proxy(
        self,
        gross_ic: float,
        turnover_rate: float,
        transaction_cost: float | None = None,
    ) -> float:
        """Net IC ≈ Gross IC - λ × Turnover。"""

        if transaction_cost is None:
            transaction_cost = self._transaction_cost
        if turnover_rate is None or np.isnan(turnover_rate):
            return float("nan")
        return float(gross_ic - transaction_cost * turnover_rate)

    def compute_all(self, features_df: pd.DataFrame, num_quantiles: int = 5) -> dict[str, dict]:
        """批次計算所有特徵的換手率指標。"""

        results: dict[str, dict] = {}
        num_quantiles = num_quantiles or self._num_quantiles
        for feature_name in features_df.columns:
            series = features_df[feature_name]
            turnover = self.compute_quantile_turnover(series, num_quantiles=num_quantiles)
            rank_change = self.compute_rank_change_rate(series)
            autocorr = self.compute_factor_autocorrelation(series)
            results[feature_name] = {
                "quantile_turnover": turnover,
                "rank_change_rate": rank_change,
                "autocorrelation": autocorr,
            }
        return results
