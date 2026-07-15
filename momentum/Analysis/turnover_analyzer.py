"""Turnover analysis utilities for IC analysis."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from momentum.Analysis.pit_stats import (
    MIN_SAMPLES,
    first_valid_index,
    pit_expanding_qcut_label,
    pit_expanding_rank,
)
from momentum.core.logging import get_logger


logger = get_logger(__name__)


def _jsonable_aligned(
    values: pd.Series,
    *,
    first_valid: Optional[int],
) -> list[Optional[float]]:
    """對齊源 index：warmup [0, first_valid) → JSON null；非有限 → null。"""
    out: list[Optional[float]] = []
    for i, val in enumerate(values.to_numpy(dtype=float, copy=False)):
        if first_valid is None or i < first_valid:
            out.append(None)
            continue
        if val is None or not np.isfinite(val):
            out.append(None)
        else:
            out.append(float(val))
    return out


def _timestamp_list(index: pd.Index) -> list[Any]:
    result: list[Any] = []
    for ts in index.tolist():
        if hasattr(ts, "isoformat"):
            result.append(ts.isoformat())
        elif isinstance(ts, (int, np.integer)):
            result.append(int(ts))
        else:
            result.append(str(ts))
    return result


class TurnoverAnalyzer:
    """因子換手率分析 — 評估交易可行性。"""

    def __init__(self, config: dict):
        self._config = config or {}
        self._transaction_cost = float(self._config.get("transaction_cost", 0.001))
        self._num_quantiles = int(self._config.get("num_quantiles", 5))
        self._min_samples = int(self._config.get("min_samples", MIN_SAMPLES))

    def compute_quantile_turnover(
        self, feature: pd.Series, num_quantiles: int = 5
    ) -> float:
        """分位數換手率：頂部分位成分每期變化比例（PIT qcut，禁 dropna）。"""

        series = feature if isinstance(feature, pd.Series) else pd.Series(feature)
        if series.empty or series.size < 2:
            return float("nan")

        num_quantiles = max(int(num_quantiles or self._num_quantiles), 2)
        try:
            quantiles = pit_expanding_qcut_label(
                series,
                q=num_quantiles,
                min_samples=self._min_samples,
                duplicates="drop",
            )
        except ValueError as exc:
            logger.warning("pit qcut failed for turnover: %s", exc)
            return float("nan")

        if quantiles.notna().sum() == 0:
            return float("nan")

        max_label = quantiles.max(skipna=True)
        if pd.isna(max_label):
            return float("nan")

        top_mask = (quantiles == max_label).astype(float)
        top_mask = top_mask.where(quantiles.notna(), np.nan)
        changes = top_mask.diff().abs()
        finite = changes[np.isfinite(changes.to_numpy(dtype=float))]
        if finite.empty:
            return 0.0
        return float(finite.mean())

    def compute_rank_change_rate(self, feature: pd.Series) -> float:
        """排名變化率：PIT expanding rank 後平均 |Δrank|（禁 dropna）。"""

        series = feature if isinstance(feature, pd.Series) else pd.Series(feature)
        if series.size < 2:
            return float("nan")

        ranks = pit_expanding_rank(
            series, min_samples=self._min_samples, ties="average"
        )
        if ranks.notna().sum() == 0:
            return float("nan")

        diffs = ranks.diff().abs()
        finite = diffs[np.isfinite(diffs.to_numpy(dtype=float))]
        if finite.empty:
            return 0.0
        return float(finite.mean())

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
        """回傳逐 bar turnover / rank change 時序。

        S2/RULING-5：對齊源 raw index 長度 n；warmup ``[0, first_valid)`` = JSON null；
        **禁 dropna**（legacy n-1 → n）。
        """

        series = feature if isinstance(feature, pd.Series) else pd.Series(feature)
        n = int(series.size)
        if n == 0:
            return {
                "quantile_turnovers": [],
                "rank_change_rates": [],
                "timestamps": [],
            }

        num_quantiles = max(int(num_quantiles or self._num_quantiles), 2)
        first_valid = first_valid_index(series, min_samples=self._min_samples)

        try:
            quantiles = pit_expanding_qcut_label(
                series,
                q=num_quantiles,
                min_samples=self._min_samples,
                duplicates="drop",
            )
        except ValueError as exc:
            logger.warning("pit qcut failed for turnover time series: %s", exc)
            # 仍對齊源 n，全 null（不裁成空陣列）
            nulls: list[Optional[float]] = [None] * n
            return {
                "quantile_turnovers": nulls,
                "rank_change_rates": nulls,
                "timestamps": _timestamp_list(series.index),
            }

        ranks = pit_expanding_rank(
            series, min_samples=self._min_samples, ties="average"
        )

        max_label = quantiles.max(skipna=True)
        top_mask = pd.Series(np.nan, index=series.index, dtype=float)
        if pd.notna(max_label):
            top_mask = (quantiles == max_label).astype(float)
            top_mask = top_mask.where(quantiles.notna(), np.nan)

        quantile_turnovers = top_mask.diff().abs()
        rank_change_rates = ranks.diff().abs()

        # RULING-5 / §MS：warmup = [0, first_valid) null；t=first_valid 本身 valid。
        # diff 需前一根 → first_valid 前為 NA 會讓 diff 成 NaN；首個可算 bar 無前態
        # → change 定義為 0.0（causal 只用 [0..first_valid]），後續 bar 照常 diff。
        if first_valid is not None:
            quantile_turnovers.iloc[first_valid] = 0.0
            rank_change_rates.iloc[first_valid] = 0.0

        return {
            "quantile_turnovers": _jsonable_aligned(
                quantile_turnovers, first_valid=first_valid
            ),
            "rank_change_rates": _jsonable_aligned(
                rank_change_rates, first_valid=first_valid
            ),
            "timestamps": _timestamp_list(series.index),
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

    def compute_all(
        self, features_df: pd.DataFrame, num_quantiles: int = 5
    ) -> dict[str, dict]:
        """批次計算所有特徵的換手率指標。"""

        results: dict[str, dict] = {}
        num_quantiles = num_quantiles or self._num_quantiles
        for feature_name in features_df.columns:
            series = features_df[feature_name]
            turnover = self.compute_quantile_turnover(
                series, num_quantiles=num_quantiles
            )
            rank_change = self.compute_rank_change_rate(series)
            autocorr = self.compute_factor_autocorrelation(series)
            turnover_series = self.compute_turnover_time_series(
                series, num_quantiles=num_quantiles
            )
            results[feature_name] = {
                "quantile_turnover": turnover,
                "rank_change_rate": rank_change,
                "autocorrelation": autocorr,
                "time_series": turnover_series,
            }
        return results
