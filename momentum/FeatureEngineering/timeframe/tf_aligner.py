"""Timeframe alignment utilities."""

from __future__ import annotations

import os
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger
from momentum.core.constants import TIMEFRAME_SECONDS
from momentum.FeatureEngineering.feature_config import AlignmentMode, SUPPORTED_TIMEFRAMES
from momentum.FeatureEngineering.memmap_utils import (
    create_temp_memmap,
    MEMMAP_THRESHOLD_BYTES,
)


logger = get_logger(__name__)


class TimeframeAligner:
    """Timeframe aligner to avoid future leakage."""

    @staticmethod
    def align_to_primary(
        source_df: pd.DataFrame,
        source_tf: str,
        primary_timestamps: pd.Series,
        primary_tf: str,
        alignment_mode: AlignmentMode = AlignmentMode.OPEN_MINUS,
    ) -> pd.DataFrame:
        """Align source DataFrame to primary timestamps using point-in-time merge."""
        if source_df is None or source_df.empty:
            primary_index = TimeframeAligner._to_datetime_index(primary_timestamps)
            return pd.DataFrame(index=primary_index)

        primary_index = TimeframeAligner._to_datetime_index(primary_timestamps)
        if primary_index.empty:
            return pd.DataFrame()

        source_index, source_values = TimeframeAligner._split_timestamp_index(source_df)
        if source_index.empty:
            return pd.DataFrame(index=primary_index)

        source_seconds = TimeframeAligner._timeframe_to_seconds(source_tf)
        primary_seconds = TimeframeAligner._timeframe_to_seconds(primary_tf)
        if source_seconds and primary_seconds:
            if source_seconds < primary_seconds:
                logger.info("Aligning higher-frequency %s to %s", source_tf, primary_tf)
            elif source_seconds > primary_seconds:
                logger.info("Aligning lower-frequency %s to %s", source_tf, primary_tf)

        if alignment_mode == AlignmentMode.OPEN_MINUS and source_tf != primary_tf:
            # OPEN_MINUS only shifts anchor for non-primary TFs to avoid same-open bar leakage.
            anchor_index = primary_index - pd.Timedelta(nanoseconds=1)
        else:
            anchor_index = primary_index

        aligned = TimeframeAligner._merge_asof_align(source_values, source_index, anchor_index)
        aligned.index = primary_index
        return aligned

    @staticmethod
    def validate_no_future_leak(
        aligned_df: pd.DataFrame, primary_timestamps: pd.Series
    ) -> bool:
        """Validate aligned data does not use future timestamps."""
        if aligned_df is None or aligned_df.empty:
            return True

        primary_index = TimeframeAligner._to_datetime_index(primary_timestamps)
        source_ts = aligned_df.attrs.get("source_timestamps")
        if source_ts is None:
            if len(primary_index) != len(aligned_df.index):
                return False
            return True

        source_index = pd.DatetimeIndex(source_ts)
        if len(source_index) != len(primary_index):
            return False

        return (source_index <= primary_index).all()

    @staticmethod
    def _merge_asof_align(
        source_values: pd.DataFrame,
        source_index: pd.DatetimeIndex,
        primary_index: pd.DatetimeIndex,
    ) -> pd.DataFrame:
        chunk_size = TimeframeAligner._resolve_merge_chunk_size()
        n_cols = source_values.shape[1]

        if chunk_size > 0 and n_cols > chunk_size:
            return TimeframeAligner._merge_asof_align_chunked(
                source_values, source_index, primary_index, chunk_size,
            )
        return TimeframeAligner._merge_asof_align_single(
            source_values, source_index, primary_index,
        )

    @staticmethod
    def _resolve_merge_chunk_size() -> int:
        """Resolve merge chunk size from env (0 = disabled, default 5000)."""
        raw = os.getenv("FFACT_MERGE_CHUNK_SIZE", "5000").strip()
        try:
            return max(int(raw), 0)
        except ValueError:
            return 5000

    @staticmethod
    def _merge_asof_align_single(
        source_values: pd.DataFrame,
        source_index: pd.DatetimeIndex,
        primary_index: pd.DatetimeIndex,
    ) -> pd.DataFrame:
        """Original merge_asof path for narrow DataFrames."""
        source_work = source_values.copy()
        source_work["_source_ts"] = source_index.to_numpy()
        source_work = source_work.sort_values("_source_ts")

        primary_df = pd.DataFrame({"_primary_ts": primary_index})
        primary_df["_order"] = range(len(primary_df))
        primary_sorted = primary_df.sort_values("_primary_ts")

        merged = pd.merge_asof(
            primary_sorted,
            source_work,
            left_on="_primary_ts",
            right_on="_source_ts",
            direction="backward",
        )
        merged = merged.sort_values("_order")

        aligned = merged.drop(columns=["_primary_ts", "_order"]).set_index(primary_index)
        source_ts = aligned.pop("_source_ts")
        aligned.attrs["source_timestamps"] = pd.DatetimeIndex(source_ts)
        return aligned

    @staticmethod
    def _merge_asof_align_chunked(
        source_values: pd.DataFrame,
        source_index: pd.DatetimeIndex,
        primary_index: pd.DatetimeIndex,
        chunk_size: int,
    ) -> pd.DataFrame:
        """Column-batch merge_asof for wide DataFrames to reduce peak memory.

        Instead of accumulating chunk DataFrames in a list and calling
        ``pd.concat`` (which doubles peak RAM), writes each chunk's result
        directly into a disk-backed ``np.memmap`` (C-order).  The OS loads
        only the pages being written/read, keeping resident memory small.
        """
        all_columns = list(source_values.columns)
        total_cols = len(all_columns)
        n_rows = len(primary_index)
        n_chunks = (total_cols + chunk_size - 1) // chunk_size
        logger.info(
            "[MultiTF] Column-batch merge: %d cols → %d chunks of ≤%d",
            total_cols,
            n_chunks,
            chunk_size,
        )

        # Pre-compute the sorted source timestamps once
        source_ts_arr = source_index.to_numpy()
        sort_order = source_ts_arr.argsort()

        primary_df = pd.DataFrame({"_primary_ts": primary_index})
        primary_df["_order"] = range(len(primary_df))
        primary_sorted = primary_df.sort_values("_primary_ts")

        # Decide: memmap for large outputs, plain array for small
        est_bytes = n_rows * total_cols * 4
        use_memmap = est_bytes >= MEMMAP_THRESHOLD_BYTES
        if use_memmap:
            out_arr = create_temp_memmap((n_rows, total_cols), prefix="tf_merge_")
        else:
            out_arr = np.empty((n_rows, total_cols), dtype=np.float32)

        source_timestamps = None
        col_offset = 0

        for i in range(0, total_cols, chunk_size):
            chunk_cols = all_columns[i : i + chunk_size]
            chunk_idx = i // chunk_size + 1
            n_chunk_cols = len(chunk_cols)

            # Build a small DF: just this chunk's cols + _source_ts
            chunk_work = source_values[chunk_cols].iloc[sort_order].copy()
            chunk_work["_source_ts"] = source_ts_arr[sort_order]

            merged = pd.merge_asof(
                primary_sorted.copy(),
                chunk_work,
                left_on="_primary_ts",
                right_on="_source_ts",
                direction="backward",
            )
            merged = merged.sort_values("_order")
            del chunk_work

            # Extract source_timestamps from first chunk only
            if source_timestamps is None:
                source_timestamps = pd.DatetimeIndex(merged["_source_ts"].values)

            # Write chunk result directly into pre-allocated array (memmap or RAM)
            out_arr[:, col_offset : col_offset + n_chunk_cols] = (
                merged[chunk_cols].values.astype(np.float32, copy=False)
            )
            col_offset += n_chunk_cols
            del merged

            if chunk_idx % 5 == 0 or chunk_idx == n_chunks:
                logger.info("[MultiTF] Merged chunk %d/%d", chunk_idx, n_chunks)

        # Wrap pre-allocated array as DataFrame (zero-copy for memmap)
        aligned = pd.DataFrame(
            data=out_arr, index=primary_index, columns=all_columns, copy=False,
        )

        if source_timestamps is not None:
            aligned.attrs["source_timestamps"] = source_timestamps

        return aligned

    @staticmethod
    def _split_timestamp_index(source_df: pd.DataFrame) -> Tuple[pd.DatetimeIndex, pd.DataFrame]:
        if "timestamp" in source_df.columns:
            timestamps = source_df["timestamp"]
            values = source_df.drop(columns=["timestamp"])
        else:
            timestamps = source_df.index
            values = source_df

        return TimeframeAligner._to_datetime_index(timestamps), values

    @staticmethod
    def _to_datetime_index(timestamps: Iterable) -> pd.DatetimeIndex:
        if isinstance(timestamps, pd.DatetimeIndex):
            return timestamps
        return pd.to_datetime(pd.Series(timestamps), unit="ms")

    @staticmethod
    def _timeframe_to_seconds(timeframe: str) -> int | None:
        if not timeframe:
            return None
        if timeframe in TIMEFRAME_SECONDS:
            return TIMEFRAME_SECONDS[timeframe]
        try:
            value = int(timeframe[:-1])
            unit = timeframe[-1]
            if unit == "m":
                return value * 60
            if unit == "h":
                return value * 3600
            if unit == "d":
                return value * 86400
            if unit == "w":
                return value * 604800
        except ValueError:
            return None
        return None

    @staticmethod
    def _timeframe_seconds_keys() -> list[str]:
        keys = set(TIMEFRAME_SECONDS.keys())
        keys.update(SUPPORTED_TIMEFRAMES)
        return list(keys)
