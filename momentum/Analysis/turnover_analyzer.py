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

    def compute_turnover_time_series(
        self,
        feature: pd.Series,
        num_quantiles: int = 5,
    ) -> dict[str, list]:
        """回傳逐 bar turnover / rank change 時序。"""

        series = feature.dropna()
        if series.empty or series.size < 2:
            return {
                "quantile_turnovers": [],
                "rank_change_rates": [],
                "timestamps": [],
            }

        num_quantiles = max(int(num_quantiles or self._num_quantiles), 2)
        try:
            quantiles = pd.qcut(series, q=num_quantiles, labels=False, duplicates="drop")
        except ValueError as exc:
            logger.warning("qcut failed for turnover time series: %s", exc)
            return {
                "quantile_turnovers": [],
                "rank_change_rates": [],
                "timestamps": [],
            }

        top_mask = (quantiles == quantiles.max()).astype(float)
        quantile_turnovers = top_mask.diff().abs().dropna().astype(float)

        ranks = series.rank(method="average")
        rank_change_rates = ranks.diff().abs().dropna().astype(float)

        if quantile_turnovers.empty or rank_change_rates.empty:
            return {
                "quantile_turnovers": [],
                "rank_change_rates": [],
                "timestamps": [],
            }

        common_index = quantile_turnovers.index.intersection(rank_change_rates.index)
        if common_index.empty:
            return {
                "quantile_turnovers": [],
                "rank_change_rates": [],
                "timestamps": [],
            }

        return {
            "quantile_turnovers": [
                float(value)
                for value in quantile_turnovers.loc[common_index].tolist()
            ],
            "rank_change_rates": [
                float(value)
                for value in rank_change_rates.loc[common_index].tolist()
            ],
            "timestamps": [
                ts.isoformat() if hasattr(ts, "isoformat") else int(ts) if isinstance(ts, (int, np.integer)) else str(ts)
                for ts in common_index.tolist()
            ],
        }

    def compute_cost_drag_proxy(
        self,
        turnover_rate: float,
        cost_bps: float,
    ) -> float:
        """成本拖累(報酬空間)=(cost_bps/10000)×turnover;無 ×2、禁混減 IC。

        負/非有限 turnover → raise ValueError(禁 clamp;對齊 SPEC v1.1)。
        """
        try:
            t = float(turnover_rate)
            bps = float(cost_bps)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"cost_drag_proxy requires finite cost_bps and non-negative finite turnover; "
                f"got cost_bps={cost_bps!r}, turnover_rate={turnover_rate!r}"
            ) from exc
        if not np.isfinite(t) or t < 0.0:
            raise ValueError(
                f"turnover_rate must be finite and >= 0, got {turnover_rate!r}"
            )
        if not np.isfinite(bps) or not (0.0 < bps <= 1000.0):
            raise ValueError(
                f"cost_bps must be finite and in (0, 1000], got {cost_bps!r}"
            )
        return float((bps / 10000.0) * t)

    def compute_all(self, features_df: pd.DataFrame, num_quantiles: int = 5) -> dict[str, dict]:
        """批次計算所有特徵的換手率指標。"""

        results: dict[str, dict] = {}
        num_quantiles = num_quantiles or self._num_quantiles
        for feature_name in features_df.columns:
            series = features_df[feature_name]
            turnover = self.compute_quantile_turnover(series, num_quantiles=num_quantiles)
            rank_change = self.compute_rank_change_rate(series)
            autocorr = self.compute_factor_autocorrelation(series)
            turnover_series = self.compute_turnover_time_series(series, num_quantiles=num_quantiles)
            results[feature_name] = {
                "quantile_turnover": turnover,
                "rank_change_rate": rank_change,
                "autocorrelation": autocorr,
                "time_series": turnover_series,
            }
        return results
