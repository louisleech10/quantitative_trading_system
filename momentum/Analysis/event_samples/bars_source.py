"""GAP-3 真實 kline bars 來源（Task B5.1）：自 `data_cache/feature_klines/kline_cache.h5` 讀 {symbol: {tf: bars}}。

與 `tests/momentum/event_samples/helpers.load_bars` 同一讀法（timestamp＝epoch 秒、bar open_time、連續網格；
close_time_ms＝open_time_ms＋TF 長度）。服務端經 `EventSamplePipeline.bars_from_kline_cache` 消費；不做任何合成。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd

from momentum.core.constants import TIMEFRAME_SECONDS

_DEFAULT_CACHE = Path(__file__).resolve().parents[3] / "data_cache" / "feature_klines" / "kline_cache.h5"


def load_bars_from_kline_cache(
    symbols: Iterable[str], timeframes: Iterable[str], *, cache_path: Optional[Path] = None,
) -> Dict[str, Dict[str, pd.DataFrame]]:
    """回 {symbol: {tf: DataFrame(open_time_ms/close_time_ms/open/close)}}；缺 symbol/tf ⇒ KeyError loud。"""
    import h5py  # 延後 import（服務啟動不需）

    path = Path(cache_path) if cache_path else _DEFAULT_CACHE
    if not path.is_file():
        raise FileNotFoundError(f"kline cache 不存在：{path}")
    out: Dict[str, Dict[str, pd.DataFrame]] = {}
    with h5py.File(path, "r") as f:
        for symbol in sorted(set(symbols)):
            out[symbol] = {}
            for tf in sorted(set(timeframes)):
                if tf not in TIMEFRAME_SECONDS:
                    raise KeyError(f"timeframe {tf!r} 不在 TIMEFRAME_SECONDS")
                key = f"{symbol}/{tf}/data"
                if key not in f:
                    raise KeyError(f"kline cache 缺 {key}")
                d = f[key][:]
                open_ms = d["timestamp"].astype(np.int64) * 1000
                out[symbol][tf] = pd.DataFrame({
                    "open_time_ms": open_ms,
                    "close_time_ms": open_ms + TIMEFRAME_SECONDS[tf] * 1000,
                    "open": d["open"].astype(np.float64),
                    "close": d["close"].astype(np.float64),
                })
    return out


__all__ = ["load_bars_from_kline_cache"]
