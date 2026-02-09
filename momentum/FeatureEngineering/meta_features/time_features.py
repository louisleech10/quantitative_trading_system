"""Time-based meta features."""

from __future__ import annotations

import pandas as pd

from momentum.core.logging import get_logger

logger = get_logger(__name__)


class TimeFeatureEngine:
    """Time-based categorical features."""

    def compute_all(self, timestamps: pd.Series) -> pd.DataFrame:
        """hour_of_day, day_of_week, is_weekend, month_of_year"""
        if timestamps is None or len(timestamps) == 0:
            return pd.DataFrame()

        if pd.api.types.is_datetime64_any_dtype(timestamps):
            dt = pd.to_datetime(timestamps, errors="coerce")
        else:
            dt = pd.to_datetime(timestamps, unit="ms", errors="coerce")
        result = pd.DataFrame(index=timestamps.index)
        result["meta_Time_HourOfDay"] = dt.dt.hour
        result["meta_Time_DayOfWeek"] = dt.dt.dayofweek
        result["meta_Time_IsWeekend"] = (dt.dt.dayofweek >= 5).astype(int)
        result["meta_Time_MonthOfYear"] = dt.dt.month
        return result
