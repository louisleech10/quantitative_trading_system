from __future__ import annotations

from typing import Dict, List

import re

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class RollingAggregator:
    """Layer 3: rolling aggregation with multiple aggregators."""

    AGGREGATORS = {
        "slope": "_compute_slope",
        "std": "_compute_std",
        "mean": "_compute_mean",
        "rank": "_compute_rank",
        "zscore": "_compute_zscore",
        "skew": "_compute_skew",
        "kurt": "_compute_kurt",
        "min": "_compute_min",
        "max": "_compute_max",
        "range": "_compute_range",
    }

    def __init__(self, config: Dict | None) -> None:
        config_dict = self._normalize_config(config)
        self._enabled = config_dict.get("enabled", True)
        self._windows = [int(window) for window in config_dict.get("windows", [5, 13, 21])]
        self._enabled_aggregators = config_dict.get("aggregators", list(self.AGGREGATORS.keys()))
        self._apply_to = config_dict.get("apply_to", "all")

    def compute_all(self, features_df: pd.DataFrame) -> pd.DataFrame:
        if not self._enabled or features_df.empty:
            return pd.DataFrame(index=features_df.index)

        columns = self._select_columns(features_df.columns)
        if not columns:
            return pd.DataFrame(index=features_df.index)

        data = features_df[columns]
        frames: List[pd.DataFrame] = []
        for agg_name in self._enabled_aggregators:
            method_name = self.AGGREGATORS.get(agg_name)
            if not method_name:
                continue
            method = getattr(self, method_name)
            frames.append(self._apply_aggregator(data, method, agg_name))

        frames = [frame for frame in frames if not frame.empty]
        if not frames:
            return pd.DataFrame(index=features_df.index)

        return pd.concat(frames, axis=1)

    def _apply_aggregator(
        self,
        data: pd.DataFrame,
        method: callable,
        agg_name: str,
    ) -> pd.DataFrame:
        if agg_name in {"mean", "std", "min", "max", "skew", "kurt", "range", "zscore"}:
            return self._apply_vectorized_aggregator(data, agg_name)

        frames: List[pd.Series] = []
        agg_label = self._format_agg_label(agg_name)
        for col_index, col in enumerate(data.columns):
            series = data.iloc[:, col_index]
            for window in self._windows:
                result = method(series, window)
                frames.append(result.rename(f"{col}_{agg_label}_W{window}"))
        if not frames:
            return pd.DataFrame(index=data.index)
        return pd.concat(frames, axis=1)

    def _apply_vectorized_aggregator(self, data: pd.DataFrame, agg_name: str) -> pd.DataFrame:
        frames: List[pd.DataFrame] = []
        agg_label = self._format_agg_label(agg_name)
        for window in self._windows:
            if agg_name == "mean":
                result = data.rolling(window).mean()
            elif agg_name == "std":
                result = data.rolling(window).std()
            elif agg_name == "min":
                result = data.rolling(window).min()
            elif agg_name == "max":
                result = data.rolling(window).max()
            elif agg_name == "skew":
                result = data.rolling(window).skew()
            elif agg_name == "kurt":
                result = data.rolling(window).kurt()
            elif agg_name == "range":
                rolling_max = data.rolling(window).max()
                rolling_min = data.rolling(window).min()
                result = rolling_max - rolling_min
            elif agg_name == "zscore":
                mean = data.rolling(window).mean()
                std = data.rolling(window).std().replace(0, np.nan)
                result = (data - mean) / std
            else:
                continue
            frames.append(result.add_suffix(f"_{agg_label}_W{window}"))

        if not frames:
            return pd.DataFrame(index=data.index)
        return pd.concat(frames, axis=1)

    def _compute_slope(self, series: pd.Series, window: int) -> pd.Series:
        x = np.arange(window, dtype=float)
        sum_x = x.sum()
        sum_x2 = np.square(x).sum()
        denom = window * sum_x2 - sum_x ** 2

        def slope(values: np.ndarray) -> float:
            if denom == 0:
                return np.nan
            sum_y = values.sum()
            sum_xy = np.dot(x, values)
            return (window * sum_xy - sum_x * sum_y) / denom

        return series.rolling(window).apply(slope, raw=True)

    def _compute_std(self, series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window).std()

    def _compute_mean(self, series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window).mean()

    def _compute_rank(self, series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False
        )

    def _compute_zscore(self, series: pd.Series, window: int) -> pd.Series:
        mean = series.rolling(window).mean()
        std = series.rolling(window).std()
        return (series - mean) / std.replace(0, np.nan)

    def _compute_skew(self, series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window).skew()

    def _compute_kurt(self, series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window).kurt()

    def _compute_min(self, series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window).min()

    def _compute_max(self, series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window).max()

    def _compute_range(self, series: pd.Series, window: int) -> pd.Series:
        return self._compute_max(series, window) - self._compute_min(series, window)

    def _select_columns(self, columns: List[str]) -> List[str]:
        if self._apply_to == "all" or self._apply_to is None:
            return list(columns)
        if isinstance(self._apply_to, list):
            return [col for col in columns if any(token in col for token in self._apply_to)]
        try:
            pattern = re.compile(self._apply_to)
        except re.error:
            return [col for col in columns if self._apply_to in col]
        return [col for col in columns if pattern.search(col)]

    def _format_agg_label(self, agg_name: str) -> str:
        mapping = {
            "slope": "Slope",
            "std": "Std",
            "mean": "Mean",
            "rank": "Rank",
            "zscore": "ZScore",
            "skew": "Skew",
            "kurt": "Kurt",
            "min": "Min",
            "max": "Max",
            "range": "Range",
        }
        return mapping.get(agg_name, agg_name.title())

    def _normalize_config(self, config: Dict | None) -> Dict:
        if config is None:
            return {}
        if hasattr(config, "model_dump"):
            return config.model_dump(by_alias=True)
        if isinstance(config, dict):
            return config
        return dict(config)
