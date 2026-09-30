"""Slope 新舊耗時對照：真實 BTC 1h close 20,352 列 × 36 欄（同 v50 L3 量測規模），窗 5／21／55／144。"""
import sys
import time
from pathlib import Path

import numba
import numpy as np

REPO = Path("/Users/louis/Desktop/quantitative_trading_system")
sys.path.insert(0, str(REPO))
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402
from momentum.FeatureEngineering.operators.numba_rolling import rolling_slope  # noqa: E402


@numba.njit(cache=False)
def old_slope(data, window):
    n = len(data)
    out = np.full(n, np.nan)
    w = float(window)
    sum_x = w * (w - 1.0) / 2.0
    den = w * (w * (w - 1.0) * (2.0 * w - 1.0) / 6.0) - sum_x * sum_x
    ring = np.empty(window)
    rv = np.zeros(window, dtype=np.uint8)
    sum_y = 0.0
    sum_jy = 0.0
    valid = 0
    for i in range(n):
        s = i % window
        if i >= window and rv[s] == 1:
            sum_y -= ring[s]
            sum_jy -= float(i - window) * ring[s]
            valid -= 1
        v = data[i]
        if np.isnan(v):
            rv[s] = 0
        else:
            rv[s] = 1
            ring[s] = v
            sum_y += v
            sum_jy += float(i) * v
            valid += 1
        if i >= window - 1 and valid >= window and not np.isnan(v):
            out[i] = (w * (sum_jy - float(i - window + 1) * sum_y) - sum_x * sum_y) / den
    return out.astype(np.float32)


close = h.kline_frame(timeframe="1h")["close"].to_numpy(dtype=np.float64)
cols = [np.roll(close, k * 7) for k in range(36)]
for fn in (rolling_slope, old_slope):
    fn(close[:100], 5)
for window in (5, 21, 55, 144):
    res = []
    for fn in (rolling_slope, old_slope):
        t0 = time.perf_counter()
        for c in cols:
            fn(c, window)
        res.append((time.perf_counter() - t0) * 1000)
    print(f"W{window}: new {res[0]:.1f} ms  old {res[1]:.1f} ms  ratio {res[0] / res[1]:.2f}")
