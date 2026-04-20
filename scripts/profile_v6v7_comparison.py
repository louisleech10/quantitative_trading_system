#!/usr/bin/env python3
"""Profile Pre-optimization vs V7 multi-TF baselines with ALL layers including L6.5.

Usage:
    # Pre-optimization mode (ALL optimizations disabled):
    PYTHONPATH="$PWD" ./venv/bin/python scripts/profile_v6v7_comparison.py --mode pre-opt

    # V7 mode (ALL optimizations enabled):
    PYTHONPATH="$PWD" ./venv/bin/python scripts/profile_v6v7_comparison.py --mode v7

Both modes:
  - Use real kline data: ETHUSDT 1h (17,928 rows) + 12h (1,494 rows)
  - Use "full" preset with preprocessing.enabled=True (to run L6.5)
  - Profile all layers: L0, L1, L2, L3, L4, L5, L6, L6.5, L7
  - Record per-layer wall-clock, RSS, tracemalloc, feature count
  - Output JSON report to results/profiled_baselines/
  - V7 storage (float16 + manifest) is always active (code-level, not flag-switchable)

Flag mapping:
  pre-opt: CGSA=0, SEARCHSORTED=0, NUMBA_ROLLING=0, POLARS=0, L3_STREAMING=0
  v7:      CGSA=1, SEARCHSORTED=1, NUMBA_ROLLING=1, POLARS=1, L3_STREAMING=1
"""

from __future__ import annotations

import argparse
import functools
import gc
import hashlib
import json
import os
import platform
import resource
import shutil
import sys
import time
import tracemalloc
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _rss_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return float(value) / (1024.0 * 1024.0)
    return float(value) / 1024.0


def _tracemalloc_mb() -> float:
    current, _peak = tracemalloc.get_traced_memory()
    return float(current) / (1024.0 * 1024.0)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _dir_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return float(total) / (1024.0 * 1024.0)


def _collect_parquet_sizes(base_dir: Path) -> List[Dict[str, Any]]:
    results = []
    if not base_dir.exists():
        return results
    for pq in sorted(base_dir.rglob("*.parquet")):
        results.append({
            "path": str(pq.relative_to(base_dir)),
            "size_mb": round(float(pq.stat().st_size) / (1024.0 * 1024.0), 4),
        })
    return results


def _cleanup_cgsa_temp(factory) -> None:
    registry = getattr(factory, "_cgsa_registry", None)
    if registry is None:
        return
    work_dir = getattr(registry, "_work_dir", None)
    if work_dir and Path(work_dir).exists():
        try:
            shutil.rmtree(work_dir)
            print(f"[cleanup] Removed CGSA temp dir: {work_dir}")
        except OSError as exc:
            print(f"[cleanup] Failed to remove {work_dir}: {exc}")


# ---------------------------------------------------------------------------
# Per-layer profiling data collector
# ---------------------------------------------------------------------------

class LayerProfiler:
    def __init__(self) -> None:
        self.records: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._peak_rss_mb: float = 0.0

    def start(self, layer_name: str) -> None:
        gc.collect()
        self.records[layer_name] = {
            "start_time": time.perf_counter(),
            "rss_before_mb": _rss_mb(),
            "tracemalloc_before_mb": _tracemalloc_mb(),
        }

    def end(self, layer_name: str, feature_count: int = 0) -> None:
        rec = self.records.get(layer_name)
        if rec is None:
            return
        now = time.perf_counter()
        rss_after = _rss_mb()
        rec["elapsed_s"] = round(now - rec["start_time"], 3)
        rec["rss_after_mb"] = round(rss_after, 1)
        rec["rss_delta_mb"] = round(rss_after - rec["rss_before_mb"], 1)
        rec["tracemalloc_after_mb"] = round(_tracemalloc_mb(), 1)
        rec["tracemalloc_before_mb"] = round(rec["tracemalloc_before_mb"], 1)
        rec["rss_before_mb"] = round(rec["rss_before_mb"], 1)
        rec["feature_count"] = feature_count
        del rec["start_time"]
        self._peak_rss_mb = max(self._peak_rss_mb, rss_after)


# ---------------------------------------------------------------------------
# Main profiling run
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Profile Pre-opt vs V7 multi-TF baseline")
    parser.add_argument("--mode", required=True, choices=["pre-opt", "v7"],
                        help="pre-opt = ALL optimizations OFF, v7 = ALL optimizations ON")
    args = parser.parse_args()

    mode = args.mode
    is_v7 = mode == "v7"

    # Set feature flags based on mode
    if is_v7:
        # V7: ALL compute optimizations enabled
        os.environ["FFACT_USE_CGSA"] = "1"
        os.environ["FFACT_USE_SEARCHSORTED"] = "1"
        os.environ["FFACT_USE_NUMBA_ROLLING"] = "1"
        os.environ["FFACT_USE_POLARS"] = "1"
        os.environ["FFACT_L3_STREAMING"] = "1"
        os.environ["FFACT_LAYER1_PARALLEL"] = "0"
    else:
        # Pre-optimization: ALL compute optimizations disabled
        os.environ["FFACT_USE_CGSA"] = "0"
        os.environ["FFACT_USE_SEARCHSORTED"] = "0"
        os.environ["FFACT_USE_NUMBA_ROLLING"] = "0"
        os.environ["FFACT_USE_POLARS"] = "0"
        os.environ["FFACT_L3_STREAMING"] = "0"
        os.environ["FFACT_LAYER1_PARALLEL"] = "0"

    # Feature flag snapshot
    flag_names = [
        "FFACT_USE_SEARCHSORTED", "FFACT_USE_CGSA", "FFACT_USE_NUMBA_ROLLING",
        "FFACT_USE_POLARS", "FFACT_LAYER1_PARALLEL", "FFACT_L3_STREAMING",
        "FFACT_L65_CHUNK_SIZE", "MAX_L2_ESTIMATED_COLS",
    ]
    flag_snapshot = {name: os.environ.get(name, "<unset (code default)>") for name in flag_names}

    print("=" * 70)
    print(f"Feature Factory Multi-TF Profiled Baseline — MODE: {mode.upper()}")
    print("=" * 70)
    print(f"Symbol: ETHUSDT | Primary: 1h | Training: [1h, 12h]")
    print(f"Time:   {datetime.now().isoformat()}")
    print(f"Optimizations: {'ALL ON' if is_v7 else 'ALL OFF'}")
    print()
    print("Feature Flags:")
    for k, v in flag_snapshot.items():
        print(f"  {k} = {v}")
    print()

    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    factory = create_feature_factory(
        cache_dir="data_cache/feature_klines",
        validate_continuity=False,
    )
    profiler = LayerProfiler()

    # Config override: "full" preset + force preprocessing.enabled=True for L6.5
    config_override = {
        "preset": "full",
        "timeframes": {
            "primary": "1h",
            "training": ["1h", "12h"],
        },
        "preprocessing": {
            "enabled": True,
            # Keep mode as "replace" (default from YAML) for fair comparison
            # winsorization + rank_transform are already enabled in base yaml
        },
    }

    # Verify config
    resolved = factory._resolve_config(config_override)
    print(f"Config verification:")
    print(f"  preprocessing.enabled = {resolved.preprocessing.enabled}")
    print(f"  preprocessing.mode = {resolved.preprocessing.mode}")
    print(f"  preprocessing.winsorization.enabled = {resolved.preprocessing.winsorization.enabled}")
    print(f"  preprocessing.rank_transform.enabled = {resolved.preprocessing.rank_transform.enabled}")
    print(f"  preprocessing.adaptive_zscore.enabled = {resolved.preprocessing.adaptive_zscore.enabled}")
    print(f"  preprocessing.gaussian_normalize.enabled = {resolved.preprocessing.gaussian_normalize.enabled}")
    print(f"  preprocessing.adf_differencing.enabled = {resolved.preprocessing.adf_differencing.enabled}")
    print(f"  preprocessing.fractional_differencing.enabled = {resolved.preprocessing.fractional_differencing.enabled}")
    print()

    if not resolved.preprocessing.enabled:
        print("*** ERROR: preprocessing.enabled is still False! Aborting.")
        sys.exit(1)

    print(f"Starting {mode.upper()} generation with per-layer profiling...")
    print("-" * 70)

    tracemalloc.start()
    overall_start = time.perf_counter()

    # Layer methods to intercept
    layer_methods = [
        "_layer0_data_ingestion",
        "_layer1_atomic_indicators",
        "_layer2_derived_features",
        "_layer3_rolling_aggregation",
        "_layer4_lag_features",
        "_layer5_cross_sectional",
        "_layer6_meta_features",
        "_layer6_5_preprocessing",
    ]

    originals = {}
    for method_name in layer_methods:
        if hasattr(factory, method_name):
            originals[method_name] = getattr(factory, method_name)

    current_tf_label = ["init"]

    def make_wrapper(method_name: str, orig_fn):
        @functools.wraps(orig_fn)
        def wrapper(*args, **kwargs):
            layer_key = f"{current_tf_label[0]}/{method_name}"
            profiler.start(layer_key)
            result = orig_fn(*args, **kwargs)
            cols = 0
            if isinstance(result, pd.DataFrame) and not result.empty:
                cols = result.shape[1]
            elif isinstance(result, int):
                # transform_registry_groups returns int (processed count)
                cols = result
            profiler.end(layer_key, feature_count=cols)
            rec = profiler.records[layer_key]
            print(f"  [{current_tf_label[0]}] {method_name}: {cols} cols, "
                  f"{rec['elapsed_s']:.2f}s, "
                  f"RSS={rec['rss_after_mb']:.0f} MB",
                  flush=True)
            return result
        return wrapper

    for method_name, orig_fn in originals.items():
        setattr(factory, method_name, make_wrapper(method_name, orig_fn))

    # Intercept _current_timeframe setter to track TF label
    _orig_setattr = factory.__class__.__setattr__

    def _tracked_setattr(self, name, value):
        _orig_setattr(self, name, value)
        if name == "_current_timeframe" and isinstance(value, str):
            current_tf_label[0] = value

    factory.__class__.__setattr__ = _tracked_setattr

    # Also wrap _layer7_validate_and_persist
    orig_l7 = factory._layer7_validate_and_persist
    @functools.wraps(orig_l7)
    def wrapped_l7(*args, **kwargs):
        layer_key = f"{current_tf_label[0]}/_layer7_validate_and_persist"
        profiler.start(layer_key)
        result = orig_l7(*args, **kwargs)
        profiler.end(layer_key)
        rec = profiler.records[layer_key]
        print(f"  [{current_tf_label[0]}] _layer7_validate_and_persist: "
              f"{rec['elapsed_s']:.2f}s, RSS={rec['rss_after_mb']:.0f} MB",
              flush=True)
        return result
    factory._layer7_validate_and_persist = wrapped_l7

    # Also wrap _spill_to_memmap
    orig_spill = factory._spill_to_memmap
    @functools.wraps(orig_spill)
    def wrapped_spill(df, label):
        layer_key = f"{current_tf_label[0]}/_spill_to_memmap({label})"
        profiler.start(layer_key)
        result = orig_spill(df, label)
        profiler.end(layer_key)
        rec = profiler.records[layer_key]
        print(f"  [{current_tf_label[0]}] _spill_to_memmap({label}): "
              f"{rec['elapsed_s']:.2f}s, RSS={rec['rss_after_mb']:.0f} MB",
              flush=True)
        return result
    factory._spill_to_memmap = wrapped_spill

    # Run generation
    try:
        result = factory.generate_features(
            symbol="ETHUSDT",
            timeframe="1h",
            config_override=config_override,
            force_regenerate=True,
        )
    except Exception as exc:
        print(f"\n*** GENERATION FAILED: {exc}")
        import traceback as tb
        tb.print_exc()
        _cleanup_cgsa_temp(factory)
        sys.exit(1)
    finally:
        factory.__class__.__setattr__ = _orig_setattr
        for method_name, orig_fn in originals.items():
            setattr(factory, method_name, orig_fn)

    overall_elapsed = time.perf_counter() - overall_start
    tm_current, tm_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_rss = _rss_mb()

    print()
    print("=" * 70)
    print(f"GENERATION COMPLETE — {mode.upper()}")
    print("=" * 70)
    print(f"Total elapsed:       {overall_elapsed:.2f}s ({overall_elapsed/60:.1f} min)")
    print(f"Peak RSS:            {peak_rss:.0f} MB")
    print(f"tracemalloc peak:    {tm_peak / (1024*1024):.1f} MB")
    print(f"Feature count:       {result.feature_count}")
    print(f"Generation time:     {result.generation_time:.2f}s")
    print()

    # Load features from CGSA if needed
    features_df = result.features_df
    cgsa_mode = features_df.empty and result.feature_count > 0
    if cgsa_mode:
        config_hash = str(result.metadata.get("config_hash", ""))
        reader = FeatureReader("data_cache/features")
        frames: List[pd.DataFrame] = []
        for _group_name, group_df in reader.stream_groups("ETHUSDT", config_hash):
            frames.append(group_df)
        if frames:
            features_df = pd.concat(frames, axis=1)
        print(f"[CGSA] Loaded {features_df.shape[1]} features from per-group Parquet")

    print(f"Final shape: {features_df.shape[0]} rows × {features_df.shape[1]} cols")
    print()

    # Collect CGSA file sizes
    features_dir = Path("data_cache/features")
    parquet_sizes = _collect_parquet_sizes(features_dir)
    features_total_mb = _dir_size_mb(features_dir)

    # Per-layer summary table
    print("-" * 70)
    print(f"{'Layer':<55} {'Time(s)':>8} {'Cols':>6} {'RSS(MB)':>8} {'ΔRSS':>8}")
    print("-" * 70)
    total_layer_time = 0.0
    for layer_key, rec in profiler.records.items():
        elapsed = rec.get("elapsed_s", 0)
        cols = rec.get("feature_count", 0)
        rss = rec.get("rss_after_mb", 0)
        delta = rec.get("rss_delta_mb", 0)
        total_layer_time += elapsed
        print(f"{layer_key:<55} {elapsed:>8.2f} {cols:>6} {rss:>8.0f} {delta:>+8.0f}")
    print("-" * 70)
    print(f"{'TOTAL layer time':<55} {total_layer_time:>8.2f}")
    print(f"{'Overall wall-clock':<55} {overall_elapsed:>8.2f}")
    print()

    # File sizes
    if parquet_sizes:
        print(f"Parquet files: {len(parquet_sizes)} files, total: {features_total_mb:.2f} MB")
    else:
        print(f"Features dir total: {features_total_mb:.2f} MB")
    print()

    # Layer counts
    layer_counts = result.layer_counts or {}
    print("Layer counts:", json.dumps(layer_counts, indent=2))
    print()

    # Check which layers were profiled
    profiled_layers = set()
    for key in profiler.records:
        parts = key.split("/", 1)
        if len(parts) == 2:
            profiled_layers.add(parts[1])
    expected_layers = {
        "_layer0_data_ingestion", "_layer1_atomic_indicators",
        "_layer2_derived_features", "_layer3_rolling_aggregation",
        "_layer4_lag_features", "_layer5_cross_sectional",
        "_layer6_meta_features", "_layer6_5_preprocessing",
        "_layer7_validate_and_persist",
    }
    missing = expected_layers - profiled_layers
    if missing:
        print(f"⚠️  MISSING LAYERS in profiling: {missing}")
    else:
        print("✅ All expected layers were profiled")
    print()

    # Write full report
    report_dir = Path("results/profiled_baselines")
    report_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ") + f"_{mode.replace('.', '')}_ETHUSDT_1h_multi_tf"
    report_path = report_dir / f"{report_id}.json"

    report = {
        "report_id": report_id,
        "mode": mode,
        "all_optimizations_enabled": is_v7,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "symbol": "ETHUSDT",
        "primary_tf": "1h",
        "training_tfs": ["1h", "12h"],
        "feature_flags": flag_snapshot,
        "preprocessing_config": {
            "enabled": resolved.preprocessing.enabled,
            "mode": resolved.preprocessing.mode,
            "winsorization": resolved.preprocessing.winsorization.enabled,
            "rank_transform": resolved.preprocessing.rank_transform.enabled,
            "adaptive_zscore": resolved.preprocessing.adaptive_zscore.enabled,
            "gaussian_normalize": resolved.preprocessing.gaussian_normalize.enabled,
            "adf_differencing": resolved.preprocessing.adf_differencing.enabled,
            "fractional_differencing": resolved.preprocessing.fractional_differencing.enabled,
        },
        "performance": {
            "overall_elapsed_s": round(overall_elapsed, 3),
            "factory_generation_time_s": round(result.generation_time, 3),
            "peak_rss_mb": round(peak_rss, 1),
            "tracemalloc_current_mb": round(tm_current / (1024 * 1024), 1),
            "tracemalloc_peak_mb": round(tm_peak / (1024 * 1024), 1),
        },
        "features": {
            "feature_count": result.feature_count,
            "rows": features_df.shape[0],
            "columns": features_df.shape[1],
            "cgsa_mode": cgsa_mode,
        },
        "layer_counts": layer_counts,
        "per_layer_profile": dict(profiler.records),
        "file_sizes": {
            "features_dir_total_mb": round(features_total_mb, 2),
            "parquet_file_count": len(parquet_sizes),
            "parquet_files": parquet_sizes,
        },
        "metadata": {
            "skipped_timeframes": result.metadata.get("skipped_timeframes", []),
            "actual_timeframes": result.metadata.get("actual_timeframes", []),
            "config_hash": str(result.metadata.get("config_hash", "")),
        },
        "profiled_layers": sorted(profiled_layers),
        "missing_layers": sorted(missing),
    }

    _write_json(report_path, report)
    print(f"Full report written to: {report_path}")

    _cleanup_cgsa_temp(factory)
    print("Done.")


if __name__ == "__main__":
    main()
