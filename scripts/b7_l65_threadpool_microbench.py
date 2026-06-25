#!/usr/bin/env python3
"""Read-only L6.5 native-tf ThreadPool / GIL microbench (hermetic).

Measures serial vs ThreadPool speedup for narrow L3 winsor groups on real
kline (20352×1 col, scaled window ~3024). Does not modify product code or
data_cache.
"""
from __future__ import annotations

import gc
import importlib.util
import os
import sys
import tempfile
import textwrap
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import h5py
import numpy as np
import psutil

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

KLINE_CACHE = PROJECT_ROOT / "data_cache" / "feature_klines" / "kline_cache.h5"
N_ROWS = 20352
N_GROUPS = 12
REPEATS = 3
WORKERS = (2, 4, 6)


def _rss_mb() -> float:
    return psutil.Process().memory_info().rss / (1024.0 * 1024.0)


def _snapshot_data_cache() -> Dict[str, float]:
    root = PROJECT_ROOT / "data_cache"
    if not root.exists():
        return {}
    return {
        str(p.relative_to(root)): p.stat().st_mtime_ns
        for p in root.rglob("*")
        if p.is_file()
    }


def _hermetic_issues(before: Dict[str, float], after: Dict[str, float]) -> List[str]:
    added = set(after) - set(before)
    removed = set(before) - set(after)
    changed = [k for k in before.keys() & after.keys() if before[k] != after[k]]
    issues: List[str] = []
    if added:
        issues.append(f"added={len(added)}")
    if removed:
        issues.append(f"removed={len(removed)}")
    if changed:
        issues.append(f"changed={len(changed)}")
    return issues


def _winsor_only_config() -> Dict[str, Any]:
    return {
        "enabled": True,
        "mode": "replace",
        "winsorization": {
            "enabled": True,
            "method": "quantile",
            "quantile_range": [0.01, 0.99],
            "window": 252,
        },
        "rank_transform": {"enabled": False},
        "adaptive_zscore": {"enabled": False},
        "fractional_differencing": {"enabled": False},
        "adf_differencing": {"enabled": False},
        "gaussian_normalize": {"enabled": False},
    }


def _load_real_kline_groups(symbol: str = "BTCUSDT", n_groups: int = N_GROUPS) -> List[np.ndarray]:
    """Build n_groups independent 20352×1 float32 columns from real 1h kline."""
    if not KLINE_CACHE.exists():
        raise FileNotFoundError(f"missing kline cache: {KLINE_CACHE}")

    with h5py.File(KLINE_CACHE, "r") as handle:
        raw = handle[symbol]["1h"]["data"][:]

    if raw.shape[0] != N_ROWS:
        raise ValueError(f"expected {N_ROWS} rows, got {raw.shape[0]}")

    field_names = [
        "close",
        "open",
        "high",
        "low",
        "volume",
        "taker_buy_volume",
        "taker_ratio",
        "quote_volume",
    ]
    groups: List[np.ndarray] = []
    for name in field_names:
        col = raw[name].astype(np.float32, copy=True)
        groups.append(col.reshape(-1, 1))

    close = raw["close"].astype(np.float64)
    derived: List[np.ndarray] = [
        (close / np.maximum(raw["open"].astype(np.float64), 1e-8)).astype(np.float32),
        (raw["high"].astype(np.float64) - raw["low"].astype(np.float64)).astype(np.float32),
        (raw["close"].astype(np.float64) * raw["volume"].astype(np.float64)).astype(np.float32),
        np.log1p(raw["volume"].astype(np.float64)).astype(np.float32),
    ]
    for arr in derived:
        groups.append(arr.reshape(-1, 1))

    if len(groups) < n_groups:
        raise RuntimeError(f"only built {len(groups)} groups, need {n_groups}")

    return groups[:n_groups]


class _PeakRssMonitor:
    """Background RSS sampler."""

    def __init__(self) -> None:
        self._peak = 0.0
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def __enter__(self) -> "_PeakRssMonitor":
        self._peak = _rss_mb()
        self._stop.clear()

        def _loop() -> None:
            proc = psutil.Process()
            while not self._stop.is_set():
                self._peak = max(self._peak, proc.memory_info().rss / (1024.0 * 1024.0))
                self._stop.wait(0.005)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._peak = max(self._peak, _rss_mb())

    @property
    def peak_mb(self) -> float:
        return self._peak


def _median(values: List[float]) -> float:
    return float(np.median(values))


def _run_serial(fn: Callable[[np.ndarray], Any], groups: List[np.ndarray]) -> float:
    t0 = time.perf_counter()
    for arr in groups:
        fn(arr)
    return time.perf_counter() - t0


def _run_threadpool(
    fn: Callable[[np.ndarray], Any],
    groups: List[np.ndarray],
    workers: int,
) -> float:
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(fn, groups))
    return time.perf_counter() - t0


def _bench_modes(
    label: str,
    fn: Callable[[np.ndarray], Any],
    groups: List[np.ndarray],
    warmup: int = 1,
) -> Dict[str, Any]:
    for _ in range(warmup):
        _run_serial(fn, groups[:2])
    gc.collect()

    serial_times: List[float] = []
    parallel: Dict[int, List[float]] = {w: [] for w in WORKERS}
    peak_serial = 0.0
    peak_parallel: Dict[int, float] = {}

    for _ in range(REPEATS):
        gc.collect()
        with _PeakRssMonitor() as mon:
            serial_times.append(_run_serial(fn, groups))
        peak_serial = max(peak_serial, mon.peak_mb)

        for workers in WORKERS:
            gc.collect()
            with _PeakRssMonitor() as mon:
                parallel[workers].append(_run_threadpool(fn, groups, workers))
            peak_parallel[workers] = max(peak_parallel.get(workers, 0.0), mon.peak_mb)

    serial_med = _median(serial_times)
    row: Dict[str, Any] = {
        "label": label,
        "serial_sec": round(serial_med, 3),
        "rss_peak_serial_mb": round(peak_serial, 1),
    }
    for workers in WORKERS:
        par_med = _median(parallel[workers])
        row[f"tp{workers}_sec"] = round(par_med, 3)
        row[f"tp{workers}_speedup"] = round(serial_med / par_med, 2) if par_med > 0 else 0.0
        row[f"tp{workers}_rss_peak_mb"] = round(peak_parallel[workers], 1)
    return row


def _make_nogil_temp_module(with_nogil: bool) -> Any:
    """Load sliding quantile kernel copy with/without nogil=True."""
    nogil_kw = ", nogil=True" if with_nogil else ""
    source = textwrap.dedent(
        f"""
        import numpy as np
        from numba import njit

        @njit(cache=False{nogil_kw})
        def sliding_quantile(arr, lower_q, upper_q, window, min_periods):
            n_rows, n_cols = arr.shape
            lower = np.empty((n_rows, n_cols), dtype=np.float32)
            upper = np.empty((n_rows, n_cols), dtype=np.float32)
            lower[:] = np.nan
            upper[:] = np.nan
            for c in range(n_cols):
                sorted_vals = np.empty(window + 1, dtype=np.float64)
                count = 0
                for r in range(n_rows):
                    value = arr[r, c]
                    if not np.isnan(value) and np.isfinite(value):
                        left = 0
                        right = count
                        while left < right:
                            mid = (left + right) // 2
                            if value < sorted_vals[mid]:
                                right = mid
                            else:
                                left = mid + 1
                        for k in range(count, left, -1):
                            sorted_vals[k] = sorted_vals[k - 1]
                        sorted_vals[left] = value
                        count += 1
                    if r >= window:
                        outgoing = arr[r - window, c]
                        if not np.isnan(outgoing) and np.isfinite(outgoing):
                            left = 0
                            right = count
                            while left < right:
                                mid = (left + right) // 2
                                if sorted_vals[mid] < outgoing:
                                    left = mid + 1
                                else:
                                    right = mid
                            for k in range(left, count - 1):
                                sorted_vals[k] = sorted_vals[k + 1]
                            count -= 1
                    if count < min_periods:
                        continue
                    for q_idx in range(2):
                        q = lower_q if q_idx == 0 else upper_q
                        pos = q * (count - 1)
                        lo = int(np.floor(pos))
                        hi = min(lo + 1, count - 1)
                        frac = pos - lo
                        quantile = sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])
                        if q_idx == 0:
                            lower[r, c] = np.float32(quantile)
                        else:
                            upper[r, c] = np.float32(quantile)
            return lower, upper
        """
    )
    suffix = "nogil" if with_nogil else "gil"
    path = Path(tempfile.gettempdir()) / f"b7_l65_kernel_{suffix}_{os.getpid()}.py"
    path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(f"b7_kernel_{suffix}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load temp kernel module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # JIT warmup
    dummy = np.random.randn(64, 1).astype(np.float64)
    mod.sliding_quantile(dummy, 0.01, 0.99, 16, 4)
    return mod


def main() -> int:
    from momentum.FeatureEngineering.preprocessing._native_tf_helpers import (
        scale_preprocessing_config_for_native,
    )
    from momentum.FeatureEngineering.preprocessing._numba_transforms import (
        rolling_winsorize_array,
        warmup_numba,
    )
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import (
        FeaturePreprocessor,
    )
    from momentum.FeatureEngineering.utils.winsor_params import resolve_winsor_min_periods

    before = _snapshot_data_cache()
    print(f"Hermetic: kline={KLINE_CACHE} data_cache_files={len(before)}")

    groups = _load_real_kline_groups()
    base_config = _winsor_only_config()
    scaled_config = scale_preprocessing_config_for_native(base_config, "1h", "12h")
    window = int(scaled_config["winsorization"]["window"])
    min_periods = resolve_winsor_min_periods(window)

    print(f"Groups={len(groups)} rows={groups[0].shape[0]} window={window} min_periods={min_periods}")

    warmup_numba()
    # Extra warmup on real-sized slice
    _ = rolling_winsorize_array(
        groups[0].astype(np.float64, copy=True),
        0.01,
        0.99,
        window=window,
        min_periods=min_periods,
    )

    lower_q, upper_q = 0.01, 0.99

    def pure_kernel(arr: np.ndarray) -> np.ndarray:
        data = arr.astype(np.float32, copy=True)
        return rolling_winsorize_array(
            data,
            lower_q,
            upper_q,
            window=window,
            min_periods=min_periods,
        )

    preprocessor = FeaturePreprocessor(scaled_config)

    def transform_single_path(arr: np.ndarray) -> Any:
        import pandas as pd

        df = pd.DataFrame(arr, columns=["feat"], copy=False)
        return preprocessor._transform_single(df, source_layer="L3")

    results: Dict[str, Any] = {
        "symbol": "BTCUSDT",
        "n_rows": N_ROWS,
        "n_groups": len(groups),
        "scaled_window": window,
        "min_periods": min_periods,
        "cpu_count": os.cpu_count(),
        "repeats": REPEATS,
        "benchmarks": [],
    }

    print("\n=== ① Pure kernel (rolling_winsorize_array / sliding quantile) ===")
    bench_kernel = _bench_modes("pure_kernel", pure_kernel, groups, warmup=1)
    results["benchmarks"].append(bench_kernel)
    print(bench_kernel)

    print("\n=== ③ _transform_single (pandas optimized path, production) ===")
    bench_ts = _bench_modes("transform_single", transform_single_path, groups, warmup=1)
    results["benchmarks"].append(bench_ts)
    print(bench_ts)

    print("\n=== ② @njit vs @njit(nogil=True) temp kernel copies ===")
    nogil_rows: List[Dict[str, Any]] = []
    for with_nogil, tag in ((False, "njit_default"), (True, "njit_nogil")):
        mod = _make_nogil_temp_module(with_nogil=with_nogil)

        def make_fn(module: Any) -> Callable[[np.ndarray], Any]:
            def _fn(arr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
                data = arr.astype(np.float64, copy=True)
                return module.sliding_quantile(data, lower_q, upper_q, window, min_periods)

            return _fn

        fn = make_fn(mod)
        row = _bench_modes(tag, fn, groups, warmup=1)
        nogil_rows.append(row)
        print(row)
    results["nogil_isolation"] = nogil_rows

    after = _snapshot_data_cache()
    issues = _hermetic_issues(before, after)
    results["hermetic"] = {"pass": not issues, "issues": issues}

    # Derived conclusions helpers
    k = bench_kernel
    ts = bench_ts
    results["summary"] = {
        "kernel_tp6_speedup": k.get("tp6_speedup"),
        "transform_single_tp6_speedup": ts.get("tp6_speedup"),
        "pandas_overhead_ratio_tp6": round(
            ts.get("tp6_sec", 0) / max(k.get("tp6_sec", 1e-9), 1e-9),
            2,
        ),
        "nogil_tp6_speedup": next(
            (r.get("tp6_speedup") for r in nogil_rows if r["label"] == "njit_nogil"),
            None,
        ),
        "default_njit_tp6_speedup": next(
            (r.get("tp6_speedup") for r in nogil_rows if r["label"] == "njit_default"),
            None,
        ),
    }

    out_json = PROJECT_ROOT / "handoffs" / "b7_microbench_results.json"
    import json

    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nJSON: {out_json}")
    print(f"Hermetic pass={results['hermetic']['pass']} issues={issues}")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
