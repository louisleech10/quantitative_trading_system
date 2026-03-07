from __future__ import annotations

import os
from typing import Dict, List, Optional

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
        self._column_chunk_size = self._resolve_chunk_size()

    def compute_all(self, features_df: pd.DataFrame) -> pd.DataFrame:
        if not self._enabled or features_df.empty:
            return pd.DataFrame(index=features_df.index)

        columns = self._select_columns(features_df.columns)
        if not columns:
            return pd.DataFrame(index=features_df.index)

        if self._column_chunk_size and len(columns) > self._column_chunk_size:
            return self._apply_vectorized_aggregators_chunked(features_df, columns)

        data = features_df[columns]
        return self._apply_vectorized_aggregators_with_cache(data)

    def _apply_vectorized_aggregators_chunked(
        self,
        features_df: pd.DataFrame,
        columns: List[str],
    ) -> pd.DataFrame:
        valid_aggs = [agg for agg in self._enabled_aggregators if agg in self.AGGREGATORS]
        if not valid_aggs:
            return pd.DataFrame(index=features_df.index)

        bucket: Dict[tuple, List[pd.DataFrame]] = {
            (agg_name, window): []
            for agg_name in valid_aggs
            for window in self._windows
        }

        chunk_size = int(self._column_chunk_size)
        for start in range(0, len(columns), chunk_size):
            chunk_cols = columns[start : start + chunk_size]
            chunk_df = features_df[chunk_cols]
            chunk_result = self._apply_vectorized_aggregators_with_cache(chunk_df)
            if chunk_result.empty:
                continue

            for agg_name in valid_aggs:
                agg_label = self._format_agg_label(agg_name)
                for window in self._windows:
                    suffix = f"_{agg_label}_W{window}"
                    selected_cols = [name for name in chunk_result.columns if name.endswith(suffix)]
                    if selected_cols:
                        bucket[(agg_name, window)].append(chunk_result[selected_cols])

        ordered_frames: List[pd.DataFrame] = []
        for agg_name in valid_aggs:
            for window in self._windows:
                parts = bucket.get((agg_name, window), [])
                if parts:
                    ordered_frames.append(pd.concat(parts, axis=1, copy=False))

        if not ordered_frames:
            return pd.DataFrame(index=features_df.index)
        return pd.concat(ordered_frames, axis=1, copy=False)

    def _apply_aggregator(
        self,
        data: pd.DataFrame,
        method: callable,
        agg_name: str,
    ) -> pd.DataFrame:
        # All aggregators are routed through the vectorized path.
        # "rank" and "slope" are handled inside _apply_vectorized_aggregator
        # using raw=True callbacks, which avoids per-row Python object creation.
        return self._apply_vectorized_aggregator(data, agg_name)

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
            elif agg_name == "rank":
                # raw=True passes a numpy array to the lambda — no pd.Series construction.
                # rankdata runs in C via scipy, giving ~100-1000× speedup over raw=False.
                n = window

                def _rank_pct(arr: np.ndarray, _n: int = n) -> float:
                    return rankdata(arr)[-1] / _n

                result = data.rolling(window).apply(_rank_pct, raw=True)
            elif agg_name == "slope":
                # Pre-compute OLS constants once per window; apply as raw=True lambda.
                x = np.arange(window, dtype=float)
                sum_x = float(x.sum())
                sum_x2 = float(np.dot(x, x))
                denom = window * sum_x2 - sum_x ** 2
                if denom == 0:
                    result = pd.DataFrame(
                        np.nan, index=data.index, columns=data.columns
                    )
                else:
                    def _slope_fn(
                        arr: np.ndarray,
                        _w: int = window,
                        _sum_x: float = sum_x,
                        _denom: float = denom,
                        _x: np.ndarray = x,
                    ) -> float:
                        return (_w * float(np.dot(_x, arr)) - _sum_x * arr.sum()) / _denom

                    result = data.rolling(window).apply(_slope_fn, raw=True)
            else:
                continue
            frames.append(result.add_suffix(f"_{agg_label}_W{window}"))

        if not frames:
            return pd.DataFrame(index=data.index)
        return pd.concat(frames, axis=1)

    def _apply_vectorized_aggregators_with_cache(self, data: pd.DataFrame) -> pd.DataFrame:
        valid_aggs = [agg for agg in self._enabled_aggregators if agg in self.AGGREGATORS]
        if not valid_aggs:
            return pd.DataFrame(index=data.index)

        result_map: Dict[str, List[pd.DataFrame]] = {agg: [] for agg in valid_aggs}

        for window in self._windows:
            rolling = data.rolling(window)

            mean_df: Optional[pd.DataFrame] = None
            std_df: Optional[pd.DataFrame] = None
            min_df: Optional[pd.DataFrame] = None
            max_df: Optional[pd.DataFrame] = None
            skew_df: Optional[pd.DataFrame] = None
            kurt_df: Optional[pd.DataFrame] = None

            if any(agg in {"mean", "zscore"} for agg in valid_aggs):
                mean_df = rolling.mean()
            if any(agg in {"std", "zscore"} for agg in valid_aggs):
                std_df = rolling.std()
            if any(agg in {"min", "range"} for agg in valid_aggs):
                min_df = rolling.min()
            if any(agg in {"max", "range"} for agg in valid_aggs):
                max_df = rolling.max()
            if "skew" in valid_aggs:
                skew_df = rolling.skew()
            if "kurt" in valid_aggs:
                kurt_df = rolling.kurt()

            for agg_name in valid_aggs:
                agg_label = self._format_agg_label(agg_name)
                if agg_name == "mean" and mean_df is not None:
                    result = mean_df
                elif agg_name == "std" and std_df is not None:
                    result = std_df
                elif agg_name == "min" and min_df is not None:
                    result = min_df
                elif agg_name == "max" and max_df is not None:
                    result = max_df
                elif agg_name == "skew" and skew_df is not None:
                    result = skew_df
                elif agg_name == "kurt" and kurt_df is not None:
                    result = kurt_df
                elif agg_name == "range" and min_df is not None and max_df is not None:
                    result = max_df - min_df
                elif agg_name == "zscore" and mean_df is not None and std_df is not None:
                    result = (data - mean_df) / std_df.replace(0, np.nan)
                elif agg_name == "rank":
                    # Use pandas vectorized rolling.rank for the current-row percentile rank.
                    result = rolling.rank(method="average", pct=True)
                elif agg_name == "slope":
                    x = np.arange(window, dtype=float)
                    sum_x = float(x.sum())
                    sum_x2 = float(np.dot(x, x))
                    denom = window * sum_x2 - sum_x ** 2
                    if denom == 0:
                        result = pd.DataFrame(np.nan, index=data.index, columns=data.columns)
                    else:
                        def _slope_fn(
                            arr: np.ndarray,
                            _w: int = window,
                            _sum_x: float = sum_x,
                            _denom: float = denom,
                            _x: np.ndarray = x,
                        ) -> float:
                            return (_w * float(np.dot(_x, arr)) - _sum_x * arr.sum()) / _denom

                        result = rolling.apply(_slope_fn, raw=True)
                else:
                    continue

                result_map[agg_name].append(result.add_suffix(f"_{agg_label}_W{window}"))

        frames: List[pd.DataFrame] = []
        for agg_name in valid_aggs:
            frames.extend(result_map.get(agg_name, []))

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
        return series.rolling(window).rank(method="average", pct=True)

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

    @staticmethod
    def _resolve_chunk_size() -> Optional[int]:
        raw = os.getenv("FFACT_LAYER3_CHUNK_SIZE", "256").strip()
        try:
            size = int(raw)
        except ValueError:
            size = 256
        if size <= 0:
            return None
        return size

    def _rolling_last_rank_pct(self, values: np.ndarray) -> float:
        """Return pandas-equivalent percentile rank of the last value in the rolling window."""
        last = values[-1]
        if np.isnan(last):
            return np.nan

        valid_mask = ~np.isnan(values)
        valid_count = int(valid_mask.sum())
        if valid_count == 0:
            return np.nan

        valid_values = values[valid_mask]
        less_count = int(np.sum(valid_values < last))
        equal_count = int(np.sum(valid_values == last))

        # Equivalent to rank(method='average', pct=True) for the last value.
        average_rank = less_count + (equal_count + 1) / 2.0
        return average_rank / float(valid_count)
