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

CURRENT_MTF_ALIGN_VERSION = 2
_NS_PER_SECOND = np.int64(1_000_000_000)


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

        if source_tf == primary_tf:
            aligned = source_values.copy(deep=False)
            aligned.index = source_index
            aligned = aligned.reindex(primary_index)
            aligned.attrs["source_timestamps"] = pd.DatetimeIndex(aligned.index)
            return aligned

        source_seconds = TimeframeAligner._timeframe_to_seconds(source_tf)
        primary_seconds = TimeframeAligner._timeframe_to_seconds(primary_tf)
        if source_seconds and primary_seconds:
            if source_seconds < primary_seconds:
                logger.info("Aligning higher-frequency %s to %s", source_tf, primary_tf)
            elif source_seconds > primary_seconds:
                logger.info("Aligning lower-frequency %s to %s", source_tf, primary_tf)

        use_searchsorted = os.environ.get("FFACT_USE_SEARCHSORTED", "1").strip() == "1"

        if use_searchsorted:
            aligned = TimeframeAligner._searchsorted_align(
                source_values,
                source_index,
                primary_index,
                source_tf=source_tf,
                primary_tf=primary_tf,
                alignment_mode=alignment_mode,
            )
        else:
            aligned = TimeframeAligner._merge_asof_align(
                source_values,
                source_index,
                primary_index,
                source_tf=source_tf,
                primary_tf=primary_tf,
                alignment_mode=alignment_mode,
            )
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
    def build_asof_index_map(
        primary_ts: np.ndarray,
        source_ts: np.ndarray,
        source_dur_ns: int,
        primary_dur_ns: int,
        mode: str,
    ) -> np.ndarray:
        """Build source-close based index map equivalent to merge_asof backward.

        Parameters
        ----------
        primary_ts : np.ndarray
            Primary timeframe open timestamps in epoch seconds. Must be sorted ascending.
        source_ts : np.ndarray
            Source timeframe open timestamps in epoch seconds. Must be sorted ascending.
        source_dur_ns : int
            Source bar duration in nanoseconds.
        primary_dur_ns : int
            Primary bar duration in nanoseconds.
        mode : str
            ``"open_time"`` for event/open decisions, ``"close_time"`` for
            decisions at primary bar close.

        Returns
        -------
        np.ndarray
            Mapping index array where -1 indicates no valid source row.

        Raises
        ------
        ValueError
            If ``source_ts`` is not sorted in ascending order.
        """
        primary_s = np.asarray(primary_ts, dtype=np.int64)
        source_s = np.asarray(source_ts, dtype=np.int64)

        if source_s.size > 1 and np.any(source_s[1:] < source_s[:-1]):
            raise ValueError("source_ts must be sorted in ascending order")

        if primary_s.size == 0:
            return np.empty(0, dtype=np.int64)

        if source_s.size == 0:
            return np.full(primary_s.shape[0], -1, dtype=np.int64)

        decision_mode = TimeframeAligner._normalize_decision_mode(mode)
        primary_ns = primary_s * _NS_PER_SECOND
        decision_ns = primary_ns + (np.int64(primary_dur_ns) if decision_mode == "close_time" else np.int64(0))
        source_close_ns = source_s * _NS_PER_SECOND + np.int64(source_dur_ns)

        idx = np.searchsorted(source_close_ns, decision_ns, side="right") - 1
        idx = idx.astype(np.int64, copy=False)
        idx[idx < 0] = -1

        valid_positions = np.flatnonzero(idx >= 0)
        if valid_positions.size > 0:
            mismatch_mask = source_close_ns[idx[valid_positions]] > decision_ns[valid_positions]
            if np.any(mismatch_mask):
                idx[valid_positions[mismatch_mask]] = -1

        return idx

    @staticmethod
    def _searchsorted_align(
        source_values: pd.DataFrame,
        source_index: pd.DatetimeIndex,
        primary_index: pd.DatetimeIndex,
        source_tf: str,
        primary_tf: str,
        alignment_mode: AlignmentMode = AlignmentMode.OPEN_MINUS,
    ) -> pd.DataFrame:
        """Align via searchsorted index map with memmap fallback for wide outputs."""
        n_rows = len(primary_index)
        n_cols = source_values.shape[1]

        if n_rows == 0 or n_cols == 0:
            aligned = pd.DataFrame(index=primary_index, columns=source_values.columns, dtype=np.float32)
            aligned.attrs["source_timestamps"] = pd.DatetimeIndex(
                np.full(n_rows, np.datetime64("NaT"), dtype="datetime64[ns]")
            )
            return aligned

        source_s = TimeframeAligner._datetime_index_to_epoch_seconds(source_index)
        primary_s = TimeframeAligner._datetime_index_to_epoch_seconds(primary_index)
        source_dur_ns, primary_dur_ns, mode = TimeframeAligner._alignment_params(
            source_tf, primary_tf, alignment_mode
        )

        idx_map = TimeframeAligner.build_asof_index_map(
            primary_s,
            source_s,
            source_dur_ns=source_dur_ns,
            primary_dur_ns=primary_dur_ns,
            mode=mode,
        )

        est_bytes = n_rows * n_cols * np.dtype(np.float32).itemsize
        if est_bytes >= MEMMAP_THRESHOLD_BYTES:
            out = create_temp_memmap((n_rows, n_cols), prefix="ss_align_")
        else:
            out = np.empty((n_rows, n_cols), dtype=np.float32)

        # Pre-convert source DataFrame to float32 numpy array ONCE.
        # Using iloc in a loop on a wide DF (217K cols) is extremely slow
        # because each iloc call rebuilds a DF object.
        # For 12h TF: 1677 × 217K × 4B = ~1.38 GB — fits in 8GB M1.
        src_np = source_values.to_numpy(dtype=np.float32, na_value=np.nan, copy=False)
        if not src_np.flags["C_CONTIGUOUS"]:
            src_np = np.ascontiguousarray(src_np, dtype=np.float32)

        # Row-block copy: C-order memmap writes are fast when writing full
        # rows (sequential I/O).  Column-block or out.fill(np.nan) causes
        # ~35 GB random I/O on a 17 GB output and triggers page thrashing
        # on 8 GB M1.  Row blocks keep peak temp at ~block_rows × n_cols × 4.
        valid_mask = idx_map >= 0
        row_block = 1024
        for row_start in range(0, n_rows, row_block):
            row_end = min(row_start + row_block, n_rows)
            local_idx = idx_map[row_start:row_end]
            local_valid = local_idx >= 0

            if not np.any(local_valid):
                # Entire block is NaN — write a contiguous NaN slab.
                out[row_start:row_end, :] = np.nan
                continue

            if np.all(local_valid):
                # All rows valid — most common case for 12h→1h.
                # Get unique source rows to minimise reads from src_np.
                unique_src, inverse = np.unique(local_idx, return_inverse=True)
                out[row_start:row_end, :] = src_np[unique_src][inverse]
            else:
                # Mixed block: some valid, some NaN.
                block = np.full((row_end - row_start, n_cols), np.nan, dtype=np.float32)
                valid_in_block = np.where(local_valid)[0]
                src_indices = local_idx[valid_in_block]
                unique_src, inverse = np.unique(src_indices, return_inverse=True)
                block[valid_in_block] = src_np[unique_src][inverse]
                out[row_start:row_end, :] = block
                del block

        del src_np

        aligned = pd.DataFrame(out, index=primary_index, columns=source_values.columns, copy=False)
        source_ts_mapped = np.full(n_rows, np.datetime64("NaT"), dtype="datetime64[ns]")
        if np.any(valid_mask):
            source_close = source_index + pd.to_timedelta(source_dur_ns, unit="ns")
            source_ts_mapped[valid_mask] = source_close.to_numpy()[idx_map[valid_mask]]
        aligned.attrs["source_timestamps"] = pd.DatetimeIndex(source_ts_mapped)
        return aligned

    @staticmethod
    def _merge_asof_align(
        source_values: pd.DataFrame,
        source_index: pd.DatetimeIndex,
        primary_index: pd.DatetimeIndex,
        source_tf: str,
        primary_tf: str,
        alignment_mode: AlignmentMode = AlignmentMode.OPEN_MINUS,
    ) -> pd.DataFrame:
        chunk_size = TimeframeAligner._resolve_merge_chunk_size()
        n_cols = source_values.shape[1]

        if chunk_size > 0 and n_cols > chunk_size:
            return TimeframeAligner._merge_asof_align_chunked(
                source_values, source_index, primary_index, chunk_size,
                source_tf=source_tf, primary_tf=primary_tf, alignment_mode=alignment_mode,
            )
        return TimeframeAligner._merge_asof_align_single(
            source_values, source_index, primary_index,
            source_tf=source_tf, primary_tf=primary_tf, alignment_mode=alignment_mode,
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
        source_tf: str,
        primary_tf: str,
        alignment_mode: AlignmentMode = AlignmentMode.OPEN_MINUS,
    ) -> pd.DataFrame:
        """Original merge_asof path for narrow DataFrames."""
        source_dur_ns, primary_dur_ns, mode = TimeframeAligner._alignment_params(
            source_tf, primary_tf, alignment_mode
        )
        source_close_index = source_index + pd.to_timedelta(source_dur_ns, unit="ns")
        decision_index = TimeframeAligner._decision_index(primary_index, primary_dur_ns, mode)

        source_work = source_values.copy()
        source_work["_source_ts"] = source_close_index.to_numpy()
        source_work = source_work.sort_values("_source_ts")

        primary_df = pd.DataFrame({"_primary_ts": decision_index})
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
        source_tf: str,
        primary_tf: str,
        alignment_mode: AlignmentMode = AlignmentMode.OPEN_MINUS,
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

        source_dur_ns, primary_dur_ns, mode = TimeframeAligner._alignment_params(
            source_tf, primary_tf, alignment_mode
        )
        source_close_index = source_index + pd.to_timedelta(source_dur_ns, unit="ns")
        decision_index = TimeframeAligner._decision_index(primary_index, primary_dur_ns, mode)

        # Pre-compute the sorted source close timestamps once
        source_ts_arr = source_close_index.to_numpy()
        sort_order = source_ts_arr.argsort()

        primary_df = pd.DataFrame({"_primary_ts": decision_index})
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
        series = pd.Series(timestamps)
        if pd.api.types.is_datetime64_any_dtype(series):
            return pd.DatetimeIndex(series)
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().all():
            max_abs = int(numeric.abs().max()) if len(numeric) else 0
            # Modern epoch seconds are ~1.7e9; epoch milliseconds are ~1.7e12.
            # Small relative test axes keep the legacy millisecond convention.
            unit = "s" if 1_000_000_000 <= max_abs < 100_000_000_000 else "ms"
            return pd.to_datetime(numeric.astype("int64"), unit=unit)
        return pd.DatetimeIndex(pd.to_datetime(series))

    @staticmethod
    def _datetime_index_to_epoch_seconds(index: pd.DatetimeIndex) -> np.ndarray:
        return (index.to_numpy(dtype="datetime64[ns]").astype(np.int64) // 1_000_000_000).astype(np.int64)

    @staticmethod
    def _normalize_decision_mode(mode: str) -> str:
        value = str(mode.value if hasattr(mode, "value") else mode)
        if value == "close_time":
            return "close_time"
        if value in {"open_time", "open_minus"}:
            return "open_time"
        raise ValueError(f"Unsupported alignment mode: {mode}")

    @staticmethod
    def _alignment_params(
        source_tf: str,
        primary_tf: str,
        alignment_mode: AlignmentMode,
    ) -> tuple[int, int, str]:
        source_seconds = TimeframeAligner._timeframe_to_seconds(source_tf)
        primary_seconds = TimeframeAligner._timeframe_to_seconds(primary_tf)
        if source_seconds is None or primary_seconds is None:
            raise ValueError(f"Unsupported timeframe for alignment: source={source_tf}, primary={primary_tf}")
        return (
            int(source_seconds) * int(_NS_PER_SECOND),
            int(primary_seconds) * int(_NS_PER_SECOND),
            TimeframeAligner._normalize_decision_mode(alignment_mode),
        )

    @staticmethod
    def _decision_index(
        primary_index: pd.DatetimeIndex,
        primary_dur_ns: int,
        mode: str,
    ) -> pd.DatetimeIndex:
        if TimeframeAligner._normalize_decision_mode(mode) == "close_time":
            return primary_index + pd.to_timedelta(primary_dur_ns, unit="ns")
        return primary_index

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
