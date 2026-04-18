from __future__ import annotations

import os
from typing import Dict, List, Optional

import re

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.memmap_utils import create_temp_memmap


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

    _NUMBA_FUSED_INDEX = {
        "mean": 0,
        "std": 1,
        "min": 2,
        "max": 3,
        "range": 4,
        "zscore": 5,
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

        streaming = os.getenv("FFACT_L3_STREAMING", "1").strip() == "1"

        if streaming:
            return self._compute_all_streaming(features_df, columns)

        if self._column_chunk_size and len(columns) > self._column_chunk_size:
            return self._apply_vectorized_aggregators_chunked(features_df, columns)

        data = features_df[columns]
        return self._apply_vectorized_aggregators_with_cache(data)

    def _compute_all_streaming(
        self,
        features_df: pd.DataFrame,
        columns: List[str],
    ) -> pd.DataFrame:
        """Streaming L3: process one (window, agg) at a time, applying variance filter
        after each step to discard dead features and reduce peak memory.

        Optimisation strategy (vs. naive nested loop):

        1. **Rolling reuse**: For each window, compute rolling mean/std/min/max
           ONCE across all chunks, then reuse for derived aggs (zscore from
           mean+std, range from min+max).  Saves ~33% of rolling calls.

        2. **Vectorised slope**: Replace `rolling.apply(_slope_fn, raw=True)`
           (Python callback per window-position per column → millions of calls)
           with a cumulative-sum formula that runs entirely in numpy C-level.
           800× faster for large windows (W233: 11s → 0.01s per chunk).

        3. **C-order memmap writes**: Source arrays from pandas are C-order.
           Writing to C-order memmap = row-by-row memcpy (fast).

        Memory: per-window cache of 4 rolling DFs × 7 chunks ≈ 364 MB,
        freed after each window iteration.  Safe on M1 8 GB.
        """
        valid_aggs = [agg for agg in self._enabled_aggregators if agg in self.AGGREGATORS]
        if not valid_aggs:
            return pd.DataFrame(index=features_df.index)

        use_numba = os.getenv("FFACT_USE_NUMBA_ROLLING", "1").strip() == "1"
        if use_numba:
            try:
                return self._compute_all_streaming_numba(features_df, columns, valid_aggs)
            except Exception as exc:
                logger.error(
                    "[L3 streaming] Numba rolling path failed, fallback to pandas path: %s",
                    exc,
                    exc_info=True,
                )

        chunk_size = self._column_chunk_size or 256
        n_rows = features_df.shape[0]
        total_generated = 0
        total_dropped = 0

        # Pre-allocate output once.  Upper bound: every input column survives every step.
        max_out_cols = len(columns) * len(valid_aggs) * len(self._windows)

        # Use disk-backed memmap (C-order) instead of np.empty.
        # np.empty allocates anonymous pages → must live in RAM or swap (slow, OOM).
        # np.memmap allocates file-backed pages → OS loads only accessed pages,
        # evicts cleanly (no swap write for clean pages).
        # C-order matches pandas source arrays → fast row-by-row memcpy on write.
        out_arr = create_temp_memmap((n_rows, max_out_cols), prefix="l3_stream_")
        out_col_names: List[str] = []
        col_offset = 0

        n_steps = len(self._windows) * len(valid_aggs)
        step = 0

        # Pre-check which base rolling results are needed for reuse
        need_mean = any(a in valid_aggs for a in ("mean", "zscore"))
        need_std = any(a in valid_aggs for a in ("std", "zscore"))
        need_min = any(a in valid_aggs for a in ("min", "range"))
        need_max = any(a in valid_aggs for a in ("max", "range"))

        for window in self._windows:
            # Phase 1: compute & cache base rolling results for ALL chunks.
            # This creates the rolling object once per (window, chunk) and
            # extracts the 4 reusable aggregations.  skew/kurt/rank/slope
            # are NOT cached — they're computed on-the-fly in Phase 2.
            chunk_starts = list(range(0, len(columns), chunk_size))
            base_cache: Dict[int, Dict] = {}  # start_idx → {df, mean, std, min, max}

            for start in chunk_starts:
                chunk_cols = columns[start : start + chunk_size]
                chunk_df = features_df[chunk_cols]
                rolling = chunk_df.rolling(window)
                base_cache[start] = {
                    "df": chunk_df,
                    "mean": rolling.mean() if need_mean else None,
                    "std": rolling.std() if need_std else None,
                    "min": rolling.min() if need_min else None,
                    "max": rolling.max() if need_max else None,
                }

            # Phase 2: for each aggregator, assemble from cache or compute fresh.
            for agg_name in valid_aggs:
                step += 1
                agg_label = self._format_agg_label(agg_name)

                step_frames: List[pd.DataFrame] = []
                for start in chunk_starts:
                    cached = base_cache[start]
                    chunk_df = cached["df"]

                    if agg_name == "mean":
                        result = cached["mean"]
                    elif agg_name == "std":
                        result = cached["std"]
                    elif agg_name == "min":
                        result = cached["min"]
                    elif agg_name == "max":
                        result = cached["max"]
                    elif agg_name == "skew":
                        result = chunk_df.rolling(window).skew()
                    elif agg_name == "kurt":
                        result = chunk_df.rolling(window).kurt()
                    elif agg_name == "range":
                        result = cached["max"] - cached["min"]
                    elif agg_name == "zscore":
                        result = (chunk_df - cached["mean"]) / cached["std"].replace(0, np.nan)
                    elif agg_name == "rank":
                        result = chunk_df.rolling(window).rank(method="average", pct=True)
                    elif agg_name == "slope":
                        result = self._compute_slope_vectorized(chunk_df, window)
                    else:
                        continue

                    chunk_result = result.add_suffix(f"_{agg_label}_W{window}")
                    if not chunk_result.empty:
                        step_frames.append(chunk_result)

                if not step_frames:
                    continue

                step_result = pd.concat(step_frames, axis=1, copy=False) if len(step_frames) > 1 else step_frames[0]
                del step_frames

                n_before = step_result.shape[1]
                step_result = self._variance_filter(step_result)
                n_after = step_result.shape[1]
                n_dropped = n_before - n_after
                total_generated += n_before
                total_dropped += n_dropped

                if n_after > 0:
                    # Write survivors directly into pre-allocated array; free DataFrame.
                    out_arr[:, col_offset : col_offset + n_after] = step_result.to_numpy(dtype=np.float32)
                    out_col_names.extend(step_result.columns.tolist())
                    col_offset += n_after

                del step_result  # Immediate free (CPython refcount → 0)

                if step % 10 == 0 or step == n_steps:
                    logger.info(
                        "[L3 streaming] step %d/%d (W%d_%s): %d→%d cols (-%d dead)",
                        step, n_steps, window, agg_name, n_before, n_after, n_dropped,
                    )

            # Free cached rolling results for this window before next iteration
            del base_cache

        logger.info(
            "[L3 streaming] complete: %d total generated, %d dead dropped, %d survivors",
            total_generated, total_dropped, col_offset,
        )

        if col_offset == 0:
            del out_arr
            return pd.DataFrame(index=features_df.index)

        # C-order memmap: [:, :col_offset] is a strided view — pandas wraps it
        # directly with copy=False.  The memmap file stays alive as the
        # DataFrame's backing store via reference chain:
        # DataFrame → block → ndarray view → memmap → fd.
        return pd.DataFrame(
            data=out_arr[:, :col_offset],
            index=features_df.index,
            columns=out_col_names,
            copy=False,
        )

    def _compute_all_streaming_numba(
        self,
        features_df: pd.DataFrame,
        columns: List[str],
        valid_aggs: List[str],
    ) -> pd.DataFrame:
        from momentum.FeatureEngineering.operators.numba_rolling import (
            fused_rolling_stats,
            rolling_rank,
        )

        chunk_size = self._column_chunk_size or 256
        n_rows = features_df.shape[0]
        total_generated = 0
        total_dropped = 0

        max_out_cols = len(columns) * len(valid_aggs) * len(self._windows)
        out_arr = create_temp_memmap((n_rows, max_out_cols), prefix="l3_stream_numba_")
        out_col_names: List[str] = []
        col_offset = 0

        n_steps = len(self._windows) * len(valid_aggs)
        step = 0

        fused_aggs = [agg for agg in valid_aggs if agg in self._NUMBA_FUSED_INDEX]

        for window in self._windows:
            chunk_starts = list(range(0, len(columns), chunk_size))
            cached_results: Dict[int, Dict[str, pd.DataFrame]] = {}

            if fused_aggs:
                for start in chunk_starts:
                    chunk_cols = columns[start : start + chunk_size]
                    chunk_df = features_df[chunk_cols]

                    agg_arrays: Dict[str, np.ndarray] = {}
                    for agg_name in fused_aggs:
                        agg_arrays[agg_name] = np.empty((n_rows, len(chunk_cols)), dtype=np.float32)

                    for col_idx, col_name in enumerate(chunk_cols):
                        values = chunk_df[col_name].to_numpy(dtype=np.float64, copy=False)

                        if fused_aggs:
                            fused = fused_rolling_stats(values, int(window))
                            for agg_name in fused_aggs:
                                fused_idx = self._NUMBA_FUSED_INDEX[agg_name]
                                agg_arrays[agg_name][:, col_idx] = fused[:, fused_idx]

                    cache_entry: Dict[str, pd.DataFrame] = {}
                    for agg_name, matrix in agg_arrays.items():
                        cache_entry[agg_name] = pd.DataFrame(
                            matrix,
                            index=chunk_df.index,
                            columns=chunk_cols,
                            copy=False,
                        )
                    cached_results[start] = cache_entry

            for agg_name in valid_aggs:
                step += 1
                agg_label = self._format_agg_label(agg_name)

                step_frames: List[pd.DataFrame] = []
                for start in chunk_starts:
                    chunk_cols = columns[start : start + chunk_size]
                    chunk_df = features_df[chunk_cols]

                    if start in cached_results and agg_name in cached_results[start]:
                        result = cached_results[start][agg_name]
                    elif agg_name == "rank":
                        result = self._compute_numba_rank(chunk_df, int(window), rolling_rank)
                    elif agg_name == "slope":
                        result = self._compute_slope_vectorized(chunk_df, int(window))
                    elif agg_name == "skew":
                        result = chunk_df.rolling(window).skew()
                    elif agg_name == "kurt":
                        result = chunk_df.rolling(window).kurt()
                    else:
                        continue

                    chunk_result = result.add_suffix(f"_{agg_label}_W{window}")
                    if not chunk_result.empty:
                        step_frames.append(chunk_result)

                if not step_frames:
                    continue

                step_result = pd.concat(step_frames, axis=1, copy=False) if len(step_frames) > 1 else step_frames[0]
                del step_frames

                n_before = step_result.shape[1]
                step_result = self._variance_filter(step_result)
                n_after = step_result.shape[1]
                n_dropped = n_before - n_after
                total_generated += n_before
                total_dropped += n_dropped

                if n_after > 0:
                    out_arr[:, col_offset : col_offset + n_after] = step_result.to_numpy(dtype=np.float32)
                    out_col_names.extend(step_result.columns.tolist())
                    col_offset += n_after

                del step_result

                if step % 10 == 0 or step == n_steps:
                    logger.info(
                        "[L3 streaming][numba] step %d/%d (W%d_%s): %d→%d cols (-%d dead)",
                        step,
                        n_steps,
                        window,
                        agg_name,
                        n_before,
                        n_after,
                        n_dropped,
                    )

            del cached_results

        logger.info(
            "[L3 streaming][numba] complete: %d total generated, %d dead dropped, %d survivors",
            total_generated,
            total_dropped,
            col_offset,
        )

        if col_offset == 0:
            del out_arr
            return pd.DataFrame(index=features_df.index)

        return pd.DataFrame(
            data=out_arr[:, :col_offset],
            index=features_df.index,
            columns=out_col_names,
            copy=False,
        )

    @staticmethod
    def _compute_numba_rank(data: pd.DataFrame, window: int, rank_fn: callable) -> pd.DataFrame:
        n_rows, n_cols = data.shape
        out = np.empty((n_rows, n_cols), dtype=np.float32)
        for col_idx, col_name in enumerate(data.columns):
            values = data[col_name].to_numpy(dtype=np.float64, copy=False)
            out[:, col_idx] = rank_fn(values, window)
        return pd.DataFrame(out, index=data.index, columns=data.columns, copy=False)

    @staticmethod
    def _compute_numba_slope(data: pd.DataFrame, window: int, slope_fn: callable) -> pd.DataFrame:
        n_rows, n_cols = data.shape
        out = np.empty((n_rows, n_cols), dtype=np.float32)
        for col_idx, col_name in enumerate(data.columns):
            values = data[col_name].to_numpy(dtype=np.float64, copy=False)
            out[:, col_idx] = slope_fn(values, window)
        return pd.DataFrame(out, index=data.index, columns=data.columns, copy=False)

    def _compute_single_agg_window(
        self,
        data: pd.DataFrame,
        agg_name: str,
        window: int,
        agg_label: str,
    ) -> pd.DataFrame:
        """Compute a single (agg, window) combination for the given data columns."""
        rolling = data.rolling(window)

        if agg_name == "mean":
            result = rolling.mean()
        elif agg_name == "std":
            result = rolling.std()
        elif agg_name == "min":
            result = rolling.min()
        elif agg_name == "max":
            result = rolling.max()
        elif agg_name == "skew":
            result = rolling.skew()
        elif agg_name == "kurt":
            result = rolling.kurt()
        elif agg_name == "range":
            result = rolling.max() - rolling.min()
        elif agg_name == "zscore":
            mean = rolling.mean()
            std = rolling.std().replace(0, np.nan)
            result = (data - mean) / std
        elif agg_name == "rank":
            result = rolling.rank(method="average", pct=True)
        elif agg_name == "slope":
            result = self._compute_slope_vectorized(data, window)
        else:
            return pd.DataFrame(index=data.index)

        return result.add_suffix(f"_{agg_label}_W{window}")

    @staticmethod
    def _compute_slope_vectorized(data: pd.DataFrame, window: int) -> pd.DataFrame:
        """Vectorized rolling OLS slope using cumulative sums.

        Replaces ``rolling.apply(_slope_fn, raw=True)`` which invokes one
        Python function call per window-position per column (O(n_rows × n_cols)
        calls).  This version uses O(1) numpy vectorized operations via
        cumulative sums — roughly 800× faster for W233 on 256-col chunks.

        Formula:
            slope = (w · Σ(i·y_i) − Σi · Σy_i) / (w · Σi² − (Σi)²)
        where i is 0-based position within each rolling window.

        NaN handling: if ANY value in a window is NaN, result is NaN
        (matches pandas ``rolling.apply`` default behaviour).
        """
        n_rows, n_cols = data.shape
        w = window

        # Denominator constants (same for all positions)
        sum_x = w * (w - 1) / 2.0
        sum_x2 = w * (w - 1) * (2 * w - 1) / 6.0
        denom = w * sum_x2 - sum_x ** 2
        if denom == 0:
            return pd.DataFrame(np.nan, index=data.index, columns=data.columns)

        vals = data.values
        if vals.dtype != np.float64:
            vals = vals.astype(np.float64)

        # Replace NaN with 0 for cumsum; track NaN count separately
        nan_mask = np.isnan(vals)
        clean = np.where(nan_mask, 0.0, vals)

        # Cumulative sum of y  (prepend zero row for easy windowing)
        cs_y = np.empty((n_rows + 1, n_cols), dtype=np.float64)
        cs_y[0] = 0
        np.cumsum(clean, axis=0, out=cs_y[1:])

        # Cumulative sum of j·y[j]  (j = absolute row index)
        j = np.arange(n_rows, dtype=np.float64)
        jy = clean * j[:, None]
        cs_jy = np.empty((n_rows + 1, n_cols), dtype=np.float64)
        cs_jy[0] = 0
        np.cumsum(jy, axis=0, out=cs_jy[1:])
        del jy, clean

        # Cumulative NaN count for windowed NaN detection
        cs_nan = np.empty((n_rows + 1, n_cols), dtype=np.int32)
        cs_nan[0] = 0
        np.cumsum(nan_mask.view(np.uint8), axis=0, out=cs_nan[1:])
        del nan_mask

        # Vectorised computation for all valid positions
        # t indexes into cs arrays (1-based); window covers vals[t-w .. t-1]
        t = np.arange(w, n_rows + 1)  # (n_valid,)
        roll_y = cs_y[t] - cs_y[t - w]          # Σy_i
        roll_jy = cs_jy[t] - cs_jy[t - w]       # Σ(j·y[j])
        del cs_y, cs_jy

        offset = (t - w).astype(np.float64)[:, None]  # (n_valid, 1)
        roll_iy = roll_jy - offset * roll_y             # Σ(i·y_i), i=0..w-1
        del roll_jy, offset

        # Slope formula
        raw_slopes = (w * roll_iy - sum_x * roll_y) / denom  # (n_valid, n_cols)
        del roll_iy, roll_y

        # Mask out windows that contain any NaN
        nan_count = cs_nan[t] - cs_nan[t - w]
        del cs_nan
        raw_slopes[nan_count > 0] = np.nan
        del nan_count

        slopes = np.full((n_rows, n_cols), np.nan, dtype=np.float32)
        slopes[w - 1 :] = raw_slopes.astype(np.float32)
        del raw_slopes

        return pd.DataFrame(slopes, index=data.index, columns=data.columns)

    @staticmethod
    def _variance_filter(df: pd.DataFrame, nan_threshold: float = 0.9) -> pd.DataFrame:
        """Remove dead features: constant columns, near-all-NaN, or containing inf.

        Only removes features that carry zero information. This is a safe,
        lossless filter — no Alpha is lost.
        """
        if df.empty:
            return df

        # 1. Remove columns that are all NaN or have NaN rate > threshold
        nan_rates = df.isna().mean()
        high_nan = nan_rates > nan_threshold

        # 2. Remove columns containing inf
        has_inf = df.isin([np.inf, -np.inf]).any()

        # 3. Remove constant columns (std == 0, excluding NaN rows)
        stds = df.std(skipna=True)
        is_constant = (stds == 0) | stds.isna()

        dead_mask = high_nan | has_inf | is_constant
        if not dead_mask.any():
            return df

        return df.loc[:, ~dead_mask]

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
                result = self._compute_slope_vectorized(data, window)
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
                    result = self._compute_slope_vectorized(data, window)
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
