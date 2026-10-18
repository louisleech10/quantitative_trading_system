"""
Time-based meta features — Layer 6 Sub-engine F.

輸出四個欄位：
  - meta_Time_HourOfDay   : 小時（UTC，0~23）
  - meta_Time_DayOfWeek   : 星期幾（0=週一, 6=週日）
  - meta_Time_IsWeekend   : 是否週末（加密貨幣週末流動性低）
  - meta_Time_MonthOfYear : 月份（1~12，月底效應、季節性）

時間框架對各特徵的影響：
  ┌──────────────────┬──────────────────────────────────────────────────┐
  │ 特徵              │ 適用時間框架                                    │
  ├──────────────────┼──────────────────────────────────────────────────┤
  │ HourOfDay        │ 1h / 4h → 兩值（0,12）對 12h 幾乎無資訊         │
  │ DayOfWeek        │ 1h / 4h / 12h / 1d → 均有意義                  │
  │ IsWeekend        │ 同上                                            │
  │ MonthOfYear      │ 1d / 1w → 短時框架雜訊多                        │
  └──────────────────┴──────────────────────────────────────────────────┘

12h 時間框架特別說明：
  Binance 12h K 線 open_time 均為 UTC 整點（00:00 和 12:00）。
  因此 HourOfDay 只有兩個唯一值 {0, 12}，變異數接近 0，
  IC 通常趨近於 0，IC Analysis 執行後應會自動篩除此特徵。
  若要節省特徵空間，可在 scan_config.yaml 設定 time_features: false
  或於未來擴充中支援「按時框架條件啟用」。

TODO(time-features-conditional): 支援依 timeframe 自動停用低資訊量的子特徵
  → 例如 12h/1d 以上時框自動跳過 HourOfDay
  → 需在 MetaFeatureConfig 加入 timeframe_aware: bool 參數
"""

from __future__ import annotations

import pandas as pd

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.feature_naming import build_identity, format_feature_name

logger = get_logger(__name__)

# FF-NAME Task 2.4：L6 meta 欄名＝`meta_meta_<indicator>`（未標記形；落盤 `meta_<tf>_meta_<indicator>`）
_HOUR_OF_DAY = format_feature_name(build_identity("meta", "meta", "time-hour-of-day"))
_DAY_OF_WEEK = format_feature_name(build_identity("meta", "meta", "time-day-of-week"))
_IS_WEEKEND = format_feature_name(build_identity("meta", "meta", "time-is-weekend"))
_MONTH_OF_YEAR = format_feature_name(build_identity("meta", "meta", "time-month-of-year"))


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
        result[_HOUR_OF_DAY] = dt.dt.hour
        result[_DAY_OF_WEEK] = dt.dt.dayofweek
        result[_IS_WEEKEND] = (dt.dt.dayofweek >= 5).astype(int)
        result[_MONTH_OF_YEAR] = dt.dt.month
        return result
