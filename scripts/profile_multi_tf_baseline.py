#!/usr/bin/env python3
"""Profile a multi-TF (ETHUSDT 1h + 12h) baseline with per-layer timing, memory, and file sizes.

Usage:
    PYTHONPATH="$PWD" ./venv/bin/python scripts/profile_multi_tf_baseline.py

Captures:
  - Per-layer wall-clock time (via monkey-patching _safe_execute + multi_tf layer calls)
  - Per-layer RSS delta and peak RSS
  - Per-layer feature column count
  - CGSA Parquet file sizes per group
  - Overall generation time, peak RSS, tracemalloc peak
  - Feature flag status snapshot
"""

from __future__ import annotations

import functools
import gc
import hashlib
import json
import os
import platform
import resource
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
    """Collect all Parquet file sizes under a directory."""
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
    """Remove CGSA temp work_dir to free disk space."""
    import shutil
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
    """Collect per-layer timing and memory snapshots."""

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

    def summary(self) -> Dict[str, Any]:
        return {
            "layers": dict(self.records),
            "peak_rss_mb": round(self._peak_rss_mb, 1),
        }


# ---------------------------------------------------------------------------
# Monkey-patch wrapper for per-TF layer profiling
# ---------------------------------------------------------------------------

def _wrap_layer_method(factory, method_name: str, profiler: LayerProfiler, tf_label: str):
    """Wrap a factory layer method to record timing in the profiler."""
    original = getattr(factory, method_name)

    @functools.wraps(original)
    def wrapper(*args, **kwargs):
        layer_key = f"{tf_label}/{method_name}"
        profiler.start(layer_key)
        result = original(*args, **kwargs)
        cols = result.shape[1] if isinstance(result, pd.DataFrame) and not result.empty else 0
        profiler.end(layer_key, feature_count=cols)
        return result

    setattr(factory, method_name, wrapper)
    return original  # so we can restore later


# ---------------------------------------------------------------------------
# Main profiling run
# ---------------------------------------------------------------------------

def main() -> None:
    # Feature flag snapshot
    flag_names = [
        "FFACT_USE_SEARCHSORTED", "FFACT_USE_CGSA", "FFACT_USE_NUMBA_ROLLING",
        "FFACT_USE_POLARS", "FFACT_LAYER1_PARALLEL", "FFACT_L3_STREAMING",
        "FFACT_L65_CHUNK_SIZE", "MAX_L2_ESTIMATED_COLS",
    ]
    flag_snapshot = {name: os.environ.get(name, "<unset (code default)>") for name in flag_names}
    print("=" * 70)
    print("Feature Factory Multi-TF Profiled Baseline")
    print("=" * 70)
    print(f"Symbol: ETHUSDT | Primary: 1h | Training: [1h, 12h]")
    print(f"Time:   {datetime.now().isoformat()}")
    print()
    print("Feature Flags:")
    for k, v in flag_snapshot.items():
        print(f"  {k} = {v}")
    print()

    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    # Use feature_klines cache which has full ETHUSDT 1h (17928 rows) + 12h (1494 rows)
    factory = create_feature_factory(
        cache_dir="data_cache/feature_klines",
        validate_continuity=False,
    )
    profiler = LayerProfiler()

    # Config override: primary=1h, training=[1h, 12h]
    config_override = {
        "preset": "full",
        "timeframes": {
            "primary": "1h",
            "training": ["1h", "12h"],
        },
    }

    print("Starting generation with per-layer profiling...")
    print("-" * 70)

    tracemalloc.start()
    overall_start = time.perf_counter()

    # We intercept generate_features to wrap layer methods.
    # Since multi-TF CGSA calls factory layer methods directly,
    # we patch them on the factory instance.
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

    # Save originals
    originals = {}
    for method_name in layer_methods:
        if hasattr(factory, method_name):
            originals[method_name] = getattr(factory, method_name)

    # Dynamic wrapping: We need to know which TF is being processed.
    # We'll wrap using a mutable label reference.
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
            profiler.end(layer_key, feature_count=cols)
            print(f"  [{current_tf_label[0]}] {method_name}: {cols} cols, "
                  f"{profiler.records[layer_key]['elapsed_s']:.2f}s, "
                  f"RSS={profiler.records[layer_key]['rss_after_mb']:.0f} MB")
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
              f"{rec['elapsed_s']:.2f}s, RSS={rec['rss_after_mb']:.0f} MB")
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
              f"{rec['elapsed_s']:.2f}s, RSS={rec['rss_after_mb']:.0f} MB")
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
        import traceback
        traceback.print_exc()
        # Cleanup CGSA temp dir on failure
        _cleanup_cgsa_temp(factory)
        return
    finally:
        # Restore __setattr__
        factory.__class__.__setattr__ = _orig_setattr
        # Restore originals
        for method_name, orig_fn in originals.items():
            setattr(factory, method_name, orig_fn)

    overall_elapsed = time.perf_counter() - overall_start
    tm_current, tm_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_rss = _rss_mb()

    print()
    print("=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)
    print(f"Total elapsed:       {overall_elapsed:.2f}s")
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
    print(f"{'Layer':<50} {'Time(s)':>8} {'Cols':>6} {'RSS(MB)':>8} {'ΔRSS':>8}")
    print("-" * 70)
    total_layer_time = 0.0
    for layer_key, rec in profiler.records.items():
        elapsed = rec.get("elapsed_s", 0)
        cols = rec.get("feature_count", 0)
        rss = rec.get("rss_after_mb", 0)
        delta = rec.get("rss_delta_mb", 0)
        total_layer_time += elapsed
        print(f"{layer_key:<50} {elapsed:>8.2f} {cols:>6} {rss:>8.0f} {delta:>+8.0f}")
    print("-" * 70)
    print(f"{'TOTAL layer time':<50} {total_layer_time:>8.2f}")
    print(f"{'Overall wall-clock':<50} {overall_elapsed:>8.2f}")
    print()

    # File sizes
    print("CGSA Parquet file sizes:")
    if parquet_sizes:
        for pq in parquet_sizes:
            print(f"  {pq['path']}: {pq['size_mb']:.3f} MB")
    print(f"  TOTAL features dir: {features_total_mb:.2f} MB")
    print()

    # Layer counts from result
    layer_counts = result.layer_counts or {}
    print("Layer counts:", json.dumps(layer_counts, indent=2))
    print()

    # Write full report
    report_dir = Path("results/profiled_baselines")
    report_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ") + "_ETHUSDT_1h_multi_tf"
    report_path = report_dir / f"{report_id}.json"

    report = {
        "report_id": report_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "symbol": "ETHUSDT",
        "primary_tf": "1h",
        "training_tfs": ["1h", "12h"],
        "feature_flags": flag_snapshot,
        "code_defaults": {
            "FFACT_USE_SEARCHSORTED": "1",
            "FFACT_USE_CGSA": "1",
            "FFACT_USE_NUMBA_ROLLING": "1",
            "FFACT_USE_POLARS": "1",
            "FFACT_L3_STREAMING": "1",
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
            "parquet_files": parquet_sizes,
        },
        "metadata": {
            "skipped_timeframes": result.metadata.get("skipped_timeframes", []),
            "actual_timeframes": result.metadata.get("actual_timeframes", []),
            "config_hash": str(result.metadata.get("config_hash", "")),
        },
    }

    _write_json(report_path, report)
    print(f"Full report written to: {report_path}")

    # Cleanup CGSA temp dir to free disk space
    _cleanup_cgsa_temp(factory)
    print("Done.")


if __name__ == "__main__":
    main()
