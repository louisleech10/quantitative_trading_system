"""獨立文獻 reference：手刻 volume 指標（不得 import 被測模組）。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import talib


def _klinger_cumulative_measurement(dm: np.ndarray, trend: np.ndarray) -> np.ndarray:
    """Klinger cumulative measurement（Investopedia/TradingView canonical）。"""
    n = len(dm)
    cm = np.empty(n, dtype=float)
    cm[0] = dm[0]
    for idx in range(1, n):
        if trend[idx] == trend[idx - 1]:
            cm[idx] = cm[idx - 1] + dm[idx]
        else:
            cm[idx] = dm[idx - 1] + dm[idx]
    return cm


def force_index_canonical_ema13(data: pd.DataFrame, ema_period: int = 13) -> pd.Series:
    """Elder Force Index canonical：EMA(13) of volume * price change."""
    close = data["close"].astype(float)
    volume = data["volume"].astype(float)
    raw = close.diff() * volume
    ema = talib.EMA(raw.values, timeperiod=ema_period)
    return pd.Series(ema, index=data.index, name="force_index_canonical_ema13")


def force_index_simplified(data: pd.DataFrame) -> pd.Series:
    """舊 simplified 版：raw diff(close)*volume（供 v0→v1 差異表）。"""
    close = data["close"].astype(float)
    volume = data["volume"].astype(float)
    return (close.diff() * volume).rename("force_index_simplified")


def klinger_round2_wrong_vf(data: pd.DataFrame, fast: int = 34, slow: int = 55) -> pd.Series:
    """Round-2 錯誤 canonical（缺 abs、括號錯）：僅供 v0→v1→round3 差異表，非 oracle。"""
    high = data["high"].astype(float)
    low = data["low"].astype(float)
    close = data["close"].astype(float)
    volume = data["volume"].astype(float)
    hlc = (high + low + close).values
    trend = np.where(hlc > np.roll(hlc, 1), 1.0, -1.0)
    trend[0] = 1.0
    dm = (high - low).values
    cm = _klinger_cumulative_measurement(dm, trend)
    cm = np.where(cm == 0, np.nan, cm)
    vf = volume.values * (2.0 * (dm / cm) - 1.0) * trend * 100.0
    vf = np.nan_to_num(vf, nan=0.0, posinf=0.0, neginf=0.0)
    ema_fast = talib.EMA(vf.astype(float), timeperiod=fast)
    ema_slow = talib.EMA(vf.astype(float), timeperiod=slow)
    return pd.Series(ema_fast - ema_slow, index=data.index, name="klinger_round2_wrong")


def klinger_simplified_vf(data: pd.DataFrame, fast: int = 34, slow: int = 55) -> pd.Series:
    """舊 simplified VF：volume * (2*close - high - low) / (high-low)（供 v0→v1 差異表）。"""
    high = data["high"].astype(float)
    low = data["low"].astype(float)
    close = data["close"].astype(float)
    volume = data["volume"].astype(float)
    hl_range = (high - low).replace(0, np.nan)
    vf = volume * (2 * close - high - low) / hl_range
    ema_fast = talib.EMA(vf.values.astype(float), timeperiod=fast)
    ema_slow = talib.EMA(vf.values.astype(float), timeperiod=slow)
    return pd.Series(ema_fast - ema_slow, index=data.index, name="klinger_simplified")


def eom_canonical_scaled(data: pd.DataFrame, window: int = 14, scale: float = 1e8) -> pd.Series:
    """Arms EOM canonical：SMA( distance_moved * box_ratio )，含 1e8 縮放。"""
    high = data["high"].astype(float)
    low = data["low"].astype(float)
    volume = data["volume"].astype(float)
    mid = (high + low) / 2.0
    distance_moved = mid.diff()
    box_ratio = (high - low) / volume.replace(0, np.nan)
    raw = distance_moved * box_ratio
    eom = raw.rolling(window).mean() / scale
    return eom.rename("eom_canonical_scaled")


def eom_simplified(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """Production EOM：無 1e8 scale（與 canonical 僅 scale 差，corr≈1）。"""
    high = data["high"].astype(float)
    low = data["low"].astype(float)
    volume = data["volume"].astype(float)
    mid = (high + low) / 2.0
    mid_move = mid.diff()
    box_ratio = (high - low) / volume.replace(0, np.nan)
    return (mid_move * box_ratio).rolling(window).mean().rename("eom_simplified")
