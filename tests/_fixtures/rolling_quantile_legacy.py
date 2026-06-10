"""Vendored 凍結副本:現行(改前)rolling_quantile_2d winsor kernel。

來源:momentum/FeatureEngineering/preprocessing/_numba_transforms.py(commit eccca5f,
L173-255 的 _rolling_quantile_numba numba/fallback 兩路 + rolling_quantile_2d wrapper)。

用途:FF_CAUSAL_PERF_FIX P0 的 byte-identical reference oracle。**完全獨立,不得 import
production 模組**;P0.1 改 production kernel 時此檔不可動(CI 守 hash)。逐位元保真。
"""
from __future__ import annotations

import numpy as np

try:  # 與 production 同樣偵測 numba
    from numba import njit  # type: ignore

    _HAS_NUMBA = True
except Exception:  # pragma: no cover - numba 缺失 fallback
    _HAS_NUMBA = False


if _HAS_NUMBA:

    @njit(cache=True)
    def _rolling_quantile_legacy_numba(
        arr: np.ndarray,
        lower_q: float,
        upper_q: float,
        window: int,
        min_periods: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        n_rows, n_cols = arr.shape
        lower = np.empty((n_rows, n_cols), dtype=np.float32)
        upper = np.empty((n_rows, n_cols), dtype=np.float32)
        lower[:] = np.nan
        upper[:] = np.nan

        for c in range(n_cols):
            scratch = np.empty(window, dtype=np.float64)
            for r in range(n_rows):
                start = max(0, r - window + 1)
                count = 0
                for k in range(start, r + 1):
                    v = arr[k, c]
                    if not np.isnan(v) and np.isfinite(v):
                        scratch[count] = v
                        count += 1
                if count < min_periods:
                    continue
                sorted_vals = np.sort(scratch[:count])
                for q_idx in range(2):
                    q = lower_q if q_idx == 0 else upper_q
                    pos = q * (count - 1)
                    lo = int(np.floor(pos))
                    hi = min(lo + 1, count - 1)
                    frac = pos - lo
                    value = sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])
                    if q_idx == 0:
                        lower[r, c] = np.float32(value)
                    else:
                        upper[r, c] = np.float32(value)
        return lower, upper

else:

    def _rolling_quantile_legacy_numba(
        arr: np.ndarray,
        lower_q: float,
        upper_q: float,
        window: int,
        min_periods: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        n_rows, n_cols = arr.shape
        lower = np.full((n_rows, n_cols), np.nan, dtype=np.float32)
        upper = np.full((n_rows, n_cols), np.nan, dtype=np.float32)
        for c in range(n_cols):
            for r in range(n_rows):
                start = max(0, r - window + 1)
                values = arr[start : r + 1, c]
                values = values[np.isfinite(values)]
                if len(values) < min_periods:
                    continue
                bounds = np.nanquantile(values, [lower_q, upper_q]).astype(np.float32)
                lower[r, c] = bounds[0]
                upper[r, c] = bounds[1]
        return lower, upper


def rolling_quantile_2d_legacy(
    arr: np.ndarray,
    lower_q: float,
    upper_q: float,
    window: int,
    min_periods: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Vendored 改前基準:row-wise causal quantile bounds(lower, upper)。"""
    if window <= 0:
        raise ValueError("rolling quantile window must be positive")
    if min_periods <= 0:
        raise ValueError("rolling quantile min_periods must be positive")
    data = np.asarray(arr, dtype=np.float64)
    if data.ndim != 2:
        raise ValueError("rolling quantile input must be 2D")
    return _rolling_quantile_legacy_numba(
        data, float(lower_q), float(upper_q), int(window), int(min_periods)
    )
