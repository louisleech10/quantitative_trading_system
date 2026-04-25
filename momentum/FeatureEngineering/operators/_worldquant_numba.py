"""Numba-accelerated kernels for WorldQuant L2 derived operators.

Replaces slow pandas `rolling.apply(...)` Python callbacks for:
- ts_argmax  (replaces rolling.apply(np.argmax, raw=True))
- ts_argmin  (replaces rolling.apply(np.argmin, raw=True))
- decay_linear (replaces rolling.apply(weighted_dot, raw=True))

Semantics: pandas rolling.apply default min_periods=window → if any value in
window is NaN, output is NaN. Otherwise:
- ts_argmax/ts_argmin: returns int index 0..(window-1) of first max/min in window.
- decay_linear: weighted dot-product with weights = arange(1, w+1) / sum.

Parity verified bit-exact for argmax/argmin and within float epsilon (~2.2e-16)
for decay_linear; differences vanish after float16 storage cast.
"""
from __future__ import annotations

import numpy as np
from momentum.core.logging import get_logger

logger = get_logger(__name__)

_HAS_NUMBA = False
try:
    from numba import njit, prange  # type: ignore[import-not-found]

    _HAS_NUMBA = True
except ImportError:  # pragma: no cover - numba is a hard dep but stay safe
    logger.warning("numba unavailable; WorldQuant L2 fast path disabled")


if _HAS_NUMBA:

    @njit(parallel=True, cache=True, fastmath=False)
    def _ts_argmax_2d(arr: np.ndarray, window: int) -> np.ndarray:
        n_rows, n_cols = arr.shape
        out = np.full((n_rows, n_cols), np.nan, dtype=np.float64)
        for c in prange(n_cols):
            for i in range(window - 1, n_rows):
                base = i - window + 1
                best_val = arr[base, c]
                best_idx = 0
                saw_nan = best_val != best_val
                if not saw_nan:
                    for k in range(1, window):
                        v = arr[base + k, c]
                        if v != v:
                            saw_nan = True
                            break
                        if v > best_val:
                            best_val = v
                            best_idx = k
                if not saw_nan:
                    out[i, c] = best_idx
        return out

    @njit(parallel=True, cache=True, fastmath=False)
    def _ts_argmin_2d(arr: np.ndarray, window: int) -> np.ndarray:
        n_rows, n_cols = arr.shape
        out = np.full((n_rows, n_cols), np.nan, dtype=np.float64)
        for c in prange(n_cols):
            for i in range(window - 1, n_rows):
                base = i - window + 1
                best_val = arr[base, c]
                best_idx = 0
                saw_nan = best_val != best_val
                if not saw_nan:
                    for k in range(1, window):
                        v = arr[base + k, c]
                        if v != v:
                            saw_nan = True
                            break
                        if v < best_val:
                            best_val = v
                            best_idx = k
                if not saw_nan:
                    out[i, c] = best_idx
        return out

    @njit(parallel=True, cache=True, fastmath=False)
    def _decay_linear_2d(arr: np.ndarray, weights: np.ndarray) -> np.ndarray:
        n_rows, n_cols = arr.shape
        window = weights.shape[0]
        out = np.full((n_rows, n_cols), np.nan, dtype=np.float64)
        for c in prange(n_cols):
            for i in range(window - 1, n_rows):
                base = i - window + 1
                s = 0.0
                saw_nan = False
                for k in range(window):
                    v = arr[base + k, c]
                    if v != v:
                        saw_nan = True
                        break
                    s += v * weights[k]
                if not saw_nan:
                    out[i, c] = s
        return out


def ts_argmax(arr: np.ndarray, window: int) -> np.ndarray:
    """Return rolling argmax 2-D output (float64) matching pandas semantics."""
    if not _HAS_NUMBA:
        raise RuntimeError("numba unavailable; cannot run WorldQuant fast path")
    if arr.dtype != np.float64:
        arr = arr.astype(np.float64, copy=False)
    return _ts_argmax_2d(arr, int(window))


def ts_argmin(arr: np.ndarray, window: int) -> np.ndarray:
    if not _HAS_NUMBA:
        raise RuntimeError("numba unavailable; cannot run WorldQuant fast path")
    if arr.dtype != np.float64:
        arr = arr.astype(np.float64, copy=False)
    return _ts_argmin_2d(arr, int(window))


def decay_linear(arr: np.ndarray, window: int) -> np.ndarray:
    if not _HAS_NUMBA:
        raise RuntimeError("numba unavailable; cannot run WorldQuant fast path")
    if arr.dtype != np.float64:
        arr = arr.astype(np.float64, copy=False)
    weights = np.arange(1, window + 1, dtype=np.float64)
    weights /= weights.sum()
    return _decay_linear_2d(arr, weights)


HAS_NUMBA = _HAS_NUMBA
