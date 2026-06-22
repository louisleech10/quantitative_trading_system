# 20260622-b7-microbench-codex

## Scope
- Read-only microbench; product code unchanged.
- Temp script/result only: `scripts/tmp/b7_l65_threadpool_microbench.py`, `scripts/tmp/b7_l65_threadpool_microbench_results.json`.
- Real data source opened read-only via h5py: `data_cache/feature_klines/kline_cache.h5`.

## Workload
- 24 independent narrow groups, each `20352 x 1`, from real 1h kline fields (`close`, `volume`, `taker_ratio`) across symbols.
- Winsor quantile config: `window=3024`, `min_periods=756`, `quantile_range=[0.01,0.99]`.
- L6.5 profile observed: `FFACT_L65_OPTIMIZATION_PROFILE=optimized(default)`.
- `NUMBA_NUM_THREADS=1`; outer parallelism only via Python `ThreadPoolExecutor`.

## Results
| bench | N=1 | N=2 | N=4 | N=6 |
|---|---:|---:|---:|---:|
| native_l65_winsor wall | 1.322s | 1.329s | 1.327s | 1.329s |
| native_l65_winsor speedup | 1.00x | 1.00x | 1.00x | 0.99x |
| product_kernel_current speedup | 1.00x | 1.00x | 0.98x | 0.94x |
| copied_kernel_njit speedup | 1.00x | 1.01x | 1.01x | 1.01x |
| copied_kernel_nogil speedup | 1.00x | 1.95x | 3.70x | 4.54x |

## RSS
- native_l65_winsor peak: 276.9MB(N=1), 278.2MB(N=2), 279.8MB(N=4), 281.0MB(N=6).
- native_l65_winsor delta: +0.2MB, +1.3MB, +1.7MB, +1.3MB.
- copied_kernel_nogil peak at N=6: 281.5MB, delta +0.7MB.

## Conclusion
- Current Scheme A ThreadPool does not speed up native L6.5 winsor: measured 0.99-1.00x.
- Product/current `@njit(cache=True)` rolling quantile behaves GIL-bound under ThreadPool.
- Copied `@njit(nogil=True)` kernel unlocks parallel speedup: 4.54x at 6 workers on same workload.
- Recommendation: Scheme A only becomes viable after adding `nogil=True` to relevant kernels plus byte/parity and concurrency regression tests; current Scheme A should not ship as a perf fix.
- Algorithmic Scheme B remains worth evaluating because nogil parallelizes the current O(n*window) sliding algorithm but does not reduce single-worker complexity.

## Hermetic Proof
- `find data_cache -type f -newermt '2026-06-22 19:37:00'` returned no files.
- HDF5 read path uses `h5py.File(path, "r")`; PyTables was unavailable due missing Homebrew HDF5 dylib.
- No product files modified.
