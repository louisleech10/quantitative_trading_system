"""Module 3: Trend analyzer."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import linregress

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.core.logging import get_logger


logger = get_logger(__name__)


class TrendAnalyzer:
    def __init__(self, config: dict):
        cfg = config or {}
        self._config = cfg
        self._min_samples = int(cfg.get("min_samples", 20))
        self._significance = float(cfg.get("significance_level", 0.05))
        self._r2_threshold = float(cfg.get("r_squared_threshold", 0.1))

    def analyze_trend(self, time_series: pd.Series, series_name: str = "") -> dict | SkippedResult:
        series = pd.Series(time_series, dtype=float).dropna()
        if len(series) < self._min_samples:
            return SkippedResult(
                module_name="trend_analysis",
                reason=f"{series_name or 'series'} insufficient samples",
                error_type="INSUFFICIENT_DATA",
            )

        if series.nunique(dropna=True) <= 1:
            value = float(series.iloc[0]) if not series.empty else 0.0
            return {
                "slope": 0.0,
                "p_value": 1.0,
                "r_squared": 0.0,
                "tail_estimate": value,
                "trend": "flat",
                "interpretation": "序列近乎常數，趨勢為平坦",
            }

        winsorized = self._winsorize(series)
        x = np.arange(len(winsorized), dtype=float)
        reg = linregress(x, winsorized.values.astype(float))

        slope = float(reg.slope)
        p_value = float(reg.pvalue) if np.isfinite(reg.pvalue) else 1.0
        r_squared = float(reg.rvalue ** 2) if np.isfinite(reg.rvalue) else 0.0

        if (not np.isfinite(slope)) or (not np.isfinite(r_squared)):
            trend = "indeterminate"
        elif p_value <= self._significance and r_squared >= self._r2_threshold:
            trend = "up" if slope > 0 else "down" if slope < 0 else "flat"
        else:
            trend = "flat"

        tail_estimate = float(reg.intercept + reg.slope * (len(winsorized) - 1))
        interpretation = self._interpret_trend(trend)

        return {
            "slope": slope,
            "p_value": p_value,
            "r_squared": r_squared,
            "tail_estimate": tail_estimate,
            "trend": trend,
            "interpretation": interpretation,
        }

    def analyze_multi_dimension(
        self,
        feature_name: str,
        rolling_ic: Optional[pd.Series] = None,
        rolling_centrality: Optional[pd.Series] = None,
        factor_return_cumulative: Optional[pd.Series] = None,
        ls_spread_series: Optional[pd.Series] = None,
        ic_decay_half_life: Optional[float] = None,
    ) -> dict:
        dimensions: dict[str, dict] = {}

        ic_result = self._ensure_trend_dict(self.analyze_trend(rolling_ic, "rolling_ic")) if rolling_ic is not None else None
        centrality_result = (
            self._ensure_trend_dict(self.analyze_trend(rolling_centrality, "rolling_centrality"))
            if rolling_centrality is not None
            else None
        )
        factor_return_result = (
            self._ensure_trend_dict(self.analyze_trend(factor_return_cumulative, "factor_return"))
            if factor_return_cumulative is not None
            else None
        )
        ls_spread_result = (
            self._ensure_trend_dict(self.analyze_trend(ls_spread_series, "ls_spread"))
            if ls_spread_series is not None
            else None
        )

        if ic_result:
            dimensions["ic_trend"] = ic_result
        if centrality_result:
            dimensions["centrality_trend"] = centrality_result
        if factor_return_result:
            dimensions["factor_return_trend"] = factor_return_result
        if ls_spread_result:
            dimensions["ls_spread_trend"] = ls_spread_result

        combined_signal = self._combine_signal(ic_result, centrality_result, ic_decay_half_life)

        return {
            feature_name: {
                **dimensions,
                "combined_signal": combined_signal,
            }
        }

    def batch_analyze(
        self,
        rolling_ic_matrix: pd.DataFrame,
        rolling_centrality_matrix: Optional[pd.DataFrame] = None,
        top_n: int = 30,
    ) -> dict[str, dict]:
        results: dict[str, dict] = {}
        selected = list(rolling_ic_matrix.columns)[: max(1, int(top_n))]

        for feature_name in selected:
            ic_series = rolling_ic_matrix[feature_name]
            centrality_series = None
            if (
                rolling_centrality_matrix is not None
                and feature_name in rolling_centrality_matrix.columns
            ):
                centrality_series = rolling_centrality_matrix[feature_name]

            results.update(
                self.analyze_multi_dimension(
                    feature_name=feature_name,
                    rolling_ic=ic_series,
                    rolling_centrality=centrality_series,
                )
            )

        logger.info("Trend analysis completed: %s features", len(selected))
        return results

    @staticmethod
    def _winsorize(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
        low = float(series.quantile(lower))
        high = float(series.quantile(upper))
        return series.clip(lower=low, upper=high)

    @staticmethod
    def _interpret_trend(trend: str) -> str:
        if trend == "down":
            return "呈現顯著下降趨勢，可能衰減"
        if trend == "up":
            return "呈現顯著上升趨勢"
        if trend == "flat":
            return "趨勢不顯著或近乎持平"
        return "趨勢不確定"

    @staticmethod
    def _ensure_trend_dict(result: dict | SkippedResult) -> dict | None:
        if isinstance(result, SkippedResult):
            return None
        return result

    def _combine_signal(
        self,
        ic_result: Optional[dict],
        centrality_result: Optional[dict],
        ic_decay_half_life: Optional[float],
    ) -> dict:
        ic_trend = ic_result.get("trend") if ic_result else "flat"
        centrality_trend = centrality_result.get("trend") if centrality_result else "flat"

        recommendation = "正常"
        reason = "訊號穩定"
        action = "維持觀察"

        if ic_trend == "down" and centrality_trend == "up":
            recommendation = "危險"
            reason = "IC 下降 + Centrality 上升"
            action = "建議降低配置"
        elif (ic_trend == "down" and centrality_trend == "flat") or (
            ic_trend == "flat" and centrality_trend == "up"
        ):
            recommendation = "警告"
            reason = "存在衰減或擁擠訊號"
            action = "建議提高監控頻率"
        elif ic_trend == "up" and centrality_trend == "down":
            recommendation = "正常"
            reason = "IC 改善且擁擠度降低"
            action = "可維持配置"

        if ic_decay_half_life is not None and np.isfinite(ic_decay_half_life) and ic_decay_half_life < 5:
            if recommendation == "正常":
                recommendation = "警告"
                reason += " + half_life 偏短"
            elif recommendation == "警告":
                recommendation = "危險"
                reason += " + half_life 偏短"

        return {
            "recommendation": recommendation,
            "reason": reason,
            "action": action,
        }
