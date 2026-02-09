# Feature Factory Performance Report

Date: 2026-02-09

## Environment
- OS: macOS
- Python: 3.9.6 (venv)
- Data: BTCUSDT 12h from data_cache/kline_cache.h5

## Profiling Command
```
FORCE_REGENERATE=1 PYTHONPATH=/Users/louis/Desktop/quantitative_trading_system \
  /Users/louis/Desktop/quantitative_trading_system/venv/bin/python \
  /Users/louis/Desktop/quantitative_trading_system/scripts/profile_feature_factory.py
```

## Results (Standard Preset)
- features: 6514
- elapsed_seconds: 13.3706
- tracemalloc_peak_mb: 173.36
- tracemalloc_current_mb: 21.91

### Before/After Snapshot
- Before logging reduction: 61.0747s (same preset, FORCE_REGENERATE=1)
- After logging reduction: 13.3706s
- Improvement: 47.7041s

## Top Hotspots (Cumulative)
1. FeatureValidator.validate_factory_output (winsorize, constant feature scan)
2. RollingAggregator slope (rolling apply)
3. Pandas quantile (winsorize)

## Optimizations Applied
- RollingAggregator: vectorized mean/std/min/max/skew/kurt/range/zscore per window.
- LagProcessor: chunked DataFrame shift per lag, reduce per-column loops.
- FeatureFactory: early float32 cast for layer outputs, concat copy=False.
- FeatureValidator: limit NaN/Inf detail logs to top 20 with summary.

## Memory Optimization Notes
- Layer outputs converted to float32 early to reduce peak memory.
- HDF5 outputs remain compressed on disk.

## Status vs Acceptance
- Profiling completed.
- Vectorization optimization completed.
- Memory optimization completed.
- Acceptance report completed.
- Standard preset <3s: not met in this run (13.37s). See hotspots above.
