"""Timeframe alignment utilities."""

from __future__ import annotations

from typing import Iterable, Tuple

import pandas as pd

from momentum.core.logging import get_logger
from momentum.core.constants import TIMEFRAME_SECONDS
from momentum.FeatureEngineering.feature_config import AlignmentMode, SUPPORTED_TIMEFRAMES


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
