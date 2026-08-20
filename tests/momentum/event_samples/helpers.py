"""事件樣本測試共用 helper：真實 kline 載入（sec→ms）＋事件建構。

kline 來源＝`data_cache/feature_klines/kline_cache.h5`（真實資料，禁合成價格；
統計 oracle 之合成僅限事件/label 序列——TEST_DESIGN_CHARTER §F）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import h5py
import numpy as np
import pandas as pd

from momentum.core.constants import TIMEFRAME_SECONDS
from tests.momentum.event_samples.test_import_contract import make_event  # noqa: F401  # 供各測試共用

REPO = Path(__file__).resolve().parents[3]
KLINE_CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"


def load_bars(symbol: str = "ETHUSDT", tfs: Tuple[str, ...] = ("1h", "4h", "12h")) -> Dict[str, Dict[str, pd.DataFrame]]:
    """讀真實 kline → {symbol: {tf: DataFrame(open_time_ms/close_time_ms/open/close)}}。

    kline cache 之 timestamp＝epoch 秒、bar open_time（實測 2026-08-20）；此處 ×1000 轉 ms，
    close_time_ms＝open_time_ms＋TF 長度（連續網格）。
    """
    out: Dict[str, pd.DataFrame] = {}
    with h5py.File(KLINE_CACHE, "r") as f:
        for tf in tfs:
            d = f[f"{symbol}/{tf}/data"][:]
            open_ms = d["timestamp"].astype(np.int64) * 1000
            out[tf] = pd.DataFrame({
                "open_time_ms": open_ms,
                "close_time_ms": open_ms + TIMEFRAME_SECONDS[tf] * 1000,
                "open": d["open"].astype(np.float64),
                "close": d["close"].astype(np.float64),
            })
    return {symbol: out}


def grid(symbol_bars: Dict[str, Dict[str, pd.DataFrame]], symbol: str, tf: str) -> pd.DataFrame:
    return symbol_bars[symbol][tf]
