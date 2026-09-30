"""探針：同一指標於多個起點所需之最小 K（倍數表判準：評估窗 max|test−gt| < 0.005×max(P75|gt|,std gt)）。
用法：venv/bin/python k_by_start.py <tf> <indicator> <period> [n_starts]"""
import sys
from pathlib import Path

import numpy as np
import talib

REPO = Path("/Users/louis/Desktop/quantitative_trading_system")
sys.path.insert(0, str(REPO))
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402

tf, ind, period = sys.argv[1], sys.argv[2], int(sys.argv[3])
n_starts = int(sys.argv[4]) if len(sys.argv) > 4 else 40
eval_window, thr = 1000, 0.005
out = {}
for sym in ("BTCUSDT", "ETHUSDT"):
    try:
        f = h.kline_frame(symbol=sym, timeframe=tf)
    except Exception as exc:  # noqa: BLE001
        print(sym, "skip", exc)
        continue
    close = f["close"].to_numpy(dtype=np.float64)
    fn = getattr(talib, ind)
    gt = fn(close, timeperiod=period)
    n = len(close)
    lo, hi = 4 * period + 400, n - eval_window - 1
    ks = []
    for s in np.linspace(lo, hi - 30 * period, n_starts).astype(int):
        # 起點 s：test 自 s 起算；求最小 K 使 [s+K, s+K+eval_window) 內誤差 < 門檻
        test = fn(close[s:], timeperiod=period)
        g = gt[s:]
        need = None
        for k in range(period, 30 * period):
            seg_t, seg_g = test[k:k + eval_window], g[k:k + eval_window]
            ok = np.isfinite(seg_g)
            if not np.isfinite(seg_t[ok]).all():
                continue
            scale = max(float(np.percentile(np.abs(seg_g[ok]), 75)), float(np.std(seg_g[ok])), 1e-12)
            if float(np.max(np.abs(seg_t[ok] - seg_g[ok]))) / scale < thr:
                need = k
                break
        ks.append(need if need is not None else -1)
    arr = np.array(ks)
    out[sym] = arr
    print(sym, tf, ind, period, "starts", len(arr), "K min/median/p90/max", arr.min(), int(np.median(arr)),
          int(np.percentile(arr, 90)), arr.max(), "factor_max", round(arr.max() / period, 2))
