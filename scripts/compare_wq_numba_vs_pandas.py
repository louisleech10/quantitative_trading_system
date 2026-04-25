"""Compare pandas rolling.apply vs Numba kernels on REAL ETHUSDT data.

Identifies if any production WorldQuant call produces float16-level differences.
"""
from __future__ import annotations

import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/louis/Desktop/quantitative_trading_system")
from momentum.FeatureEngineering.operators._worldquant_numba import (
    _ts_argmax_2d,
    _ts_argmin_2d,
    _decay_linear_2d,
)

# Load real ETHUSDT 1h klines
import h5py

H5 = "/Users/louis/Desktop/quantitative_trading_system/data_cache/kline_cache.h5"
with h5py.File(H5, "r") as f:
    print("Keys:", list(f.keys())[:5])
    # Find ETHUSDT 1h dataset
    if "ETHUSDT" in f:
        sym = f["ETHUSDT"]
        print("ETHUSDT timeframes:", list(sym.keys()))
        if "1h" in sym:
            ds = sym["1h"]
            print("1h dataset:", list(ds.keys()) if hasattr(ds, "keys") else ds.shape)


def compare(name: str, pd_out: pd.DataFrame, nb_out: np.ndarray) -> None:
    pd_arr = pd_out.to_numpy(dtype=np.float64)
    diff = np.abs(pd_arr - nb_out)
    diff[np.isnan(pd_arr) & np.isnan(nb_out)] = 0
    nan_mismatch = np.isnan(pd_arr) ^ np.isnan(nb_out)
    print(
        f"  {name}: max_diff_f64={np.nanmax(diff):.6g} "
        f"nan_mismatch={int(nan_mismatch.sum())}"
    )
    # float16 cast diff
    pd_f16 = pd_arr.astype(np.float16).astype(np.float64)
    nb_f16 = nb_out.astype(np.float16).astype(np.float64)
    diff_f16 = np.abs(pd_f16 - nb_f16)
    diff_f16[np.isnan(pd_f16) & np.isnan(nb_f16)] = 0
    print(
        f"    f16-cast diff: max={np.nanmax(diff_f16):.6g} "
        f"nonzero_count={int((diff_f16 > 0).sum())}"
    )


# Use random data with similar characteristics to L1 features
# (1611 cols, 17928 rows, with NaN at start of each series due to indicator warmup)
np.random.seed(42)
N_ROWS, N_COLS = 17928, 200  # smaller subset for quick test
data = np.random.randn(N_ROWS, N_COLS).astype(np.float32) * 100
# NaN warmup: first 100-300 rows of each col (varies by col)
for c in range(N_COLS):
    warmup = np.random.randint(50, 300)
    data[:warmup, c] = np.nan
# Sparse mid-series NaN
data[np.random.rand(*data.shape) < 0.001] = np.nan
# Some columns with extreme values (e.g., RSI bounded 0-100, or very large)
data[:, :20] *= 1e6  # large magnitude
data[:, 20:40] *= 1e-6  # tiny magnitude

df = pd.DataFrame(data, columns=[f"f{i}" for i in range(N_COLS)])
print(f"\nReal-like data: {df.shape}, NaN ratio: {df.isna().sum().sum() / df.size:.4f}")

for w in [5, 13, 21]:
    print(f"\nWindow={w}")
    rolling = df.rolling(w)

    pd_argmax = rolling.apply(np.argmax, raw=True)
    arr64 = np.ascontiguousarray(df.to_numpy(dtype=np.float64, copy=False))
    nb_argmax = _ts_argmax_2d(arr64, w)
    compare("ts_argmax", pd_argmax, nb_argmax)

    pd_argmin = rolling.apply(np.argmin, raw=True)
    nb_argmin = _ts_argmin_2d(arr64, w)
    compare("ts_argmin", pd_argmin, nb_argmin)

    weights = np.arange(1, w + 1, dtype=np.float64)
    weights /= weights.sum()
    pd_decay = rolling.apply(lambda x, ww=weights: float(np.dot(x, ww)), raw=True)
    nb_decay = _decay_linear_2d(arr64, weights)
    compare("decay_linear", pd_decay, nb_decay)
