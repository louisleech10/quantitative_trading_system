#!/usr/bin/env python3
"""Read-only L6.5 native-tf profiling harness.

This script intentionally monkeypatches runtime methods instead of changing
product code. It reads real kline_cache.h5, writes feature artifacts only under
the supplied tmp output root, and emits per native-tf group timing JSON/CSV.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

import numpy as np
import psutil


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--primary", default="12h")
    parser.add_argument("--secondary", default="1h")
    parser.add_argument("--cache-dir", default="data_cache/feature_klines")
    parser.add_argument("--out-root", default="/tmp/l65_profile_native_tf")
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--disable-rolling", action="store_true")
    return parser.parse_args()


def _minimal_three_indicator_config(
    primary: str,
    secondary: str,
    *,
    rolling_enabled: bool,
) -> Dict[str, Any]:
    return {
        "preset": "minimal",
        "timeframes": {
            "primary": primary,
            "training": [primary, secondary],
        },
        "data_sources": {"enabled_sources": ["close"]},
        "atomic_indicators": {
            "trend": {
                "enabled": True,
                "indicators": [
                    {"name": "EMA", "periods": [21]},
                    {"name": "SMA", "periods": [21]},
                ],
            },
            "momentum": {
                "enabled": True,
                "indicators": [
                    {"name": "RSI", "periods": [14]},
                ],
            },
            "volatility": {"enabled": False, "indicators": []},
            "volume": {"enabled": False, "indicators": []},
            "cycle": {"enabled": False, "indicators": []},
            "pattern": {"enabled": False, "indicators": []},
            "statistics": {"enabled": False, "indicators": []},
            "microstructure": {"enabled": False, "features": {}},
            "entropy": {"enabled": False, "features": {}},
            "tail_risk": {"enabled": False, "features": {}},
        },
        "operators": {
            "enabled": False,
            "distance": {"enabled": False},
            "cross": {"enabled": False},
            "momentum": {"enabled": False},
            "ratio": {"enabled": False},
            "binary_signal": {"enabled": False},
            "worldquant": {"enabled": False},
        },
        "rolling_aggregation": {
            "enabled": bool(rolling_enabled),
            "windows": [5, 13, 21],
            "aggregators": {
                name: {"enabled": True}
                for name in [
                    "slope",
                    "std",
                    "mean",
                    "rank",
                    "zscore",
                    "skew",
                    "kurt",
                    "min",
                    "max",
                    "range",
                ]
            },
            "apply_to": "all",
        },
        "lag_features": {"enabled": False},
        "cross_sectional": {"enabled": False},
        "meta_features": {"enabled": False},
        "preprocessing": {
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
            "gaussian_normalize": {"enabled": False},
            "fractional_differencing": {"enabled": False},
            "adf_differencing": {"enabled": False},
        },
    }


@contextmanager
def _profile_native_tf() -> Iterator[Dict[str, Any]]:
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
    from momentum.FeatureEngineering.preprocessing import _native_tf_helpers
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    proc = psutil.Process()
    state: Dict[str, Any] = {
        "groups": [],
        "current_group": None,
        "current_stage": None,
        "sink_calls": {},
    }

    orig_native = FeaturePreprocessor._maybe_run_native_l65_to_sink
    orig_load = ColumnGroupRegistry.load_data_native
    orig_idx = ColumnGroupRegistry.get_alignment_idx_map
    orig_transform = FeaturePreprocessor._transform_single
    orig_apply = _native_tf_helpers.apply_idx_map_to_array

    def ensure_group(group_id: str) -> Dict[str, Any]:
        current = state.get("current_group")
        if current is not None and current.get("group_id") == group_id:
            return current
        rec = {
            "group_id": group_id,
            "source_tf": "",
            "primary_tf": "",
            "source_rows": 0,
            "primary_rows": 0,
            "cols": 0,
            "shards": 0,
            "load_data_native_sec": 0.0,
            "transform_single_sec": 0.0,
            "idx_map_sec": 0.0,
            "sink_sec": 0.0,
            "wall_sec": 0.0,
            "rss_start_mb": 0.0,
            "rss_end_mb": 0.0,
            "rss_delta_mb": 0.0,
            "outputs": 0,
            "native": False,
            "fallback": False,
        }
        state["groups"].append(rec)
        state["current_group"] = rec
        return rec

    def patched_load(self: Any, group_id: str) -> np.ndarray:
        rec = ensure_group(str(group_id))
        t0 = time.perf_counter()
        arr = orig_load(self, group_id)
        rec["load_data_native_sec"] += time.perf_counter() - t0
        return arr

    def patched_idx(self: Any, group_id: str) -> Optional[np.ndarray]:
        rec = ensure_group(str(group_id))
        t0 = time.perf_counter()
        idx = orig_idx(self, group_id)
        rec["idx_map_sec"] += time.perf_counter() - t0
        return idx

    def patched_transform(self: Any, *args: Any, **kwargs: Any) -> Any:
        rec = state.get("current_group")
        t0 = time.perf_counter()
        result = orig_transform(self, *args, **kwargs)
        if rec is not None:
            rec["transform_single_sec"] += time.perf_counter() - t0
        return result

    def patched_apply(*args: Any, **kwargs: Any) -> np.ndarray:
        rec = state.get("current_group")
        t0 = time.perf_counter()
        result = orig_apply(*args, **kwargs)
        if rec is not None:
            rec["idx_map_sec"] += time.perf_counter() - t0
        return result

    def patched_native(self: Any, registry: Any, group: Any, sink: Callable[..., None]) -> Optional[int]:
        group_id = str(getattr(group, "group_id"))
        rec = ensure_group(group_id)
        alignment = getattr(group, "alignment", None)
        rec["source_tf"] = str(getattr(alignment, "source_timeframe", "") or "")
        rec["primary_tf"] = str(getattr(alignment, "primary_timeframe", "") or "")
        rec["source_rows"] = int(getattr(alignment, "source_n_rows", 0) or 0)
        rec["primary_rows"] = int(getattr(alignment, "primary_n_rows", 0) or 0)
        rec["cols"] = int(getattr(group, "n_cols", len(getattr(group, "columns", ()) or ())) or 0)
        rec["shards"] = len(getattr(group, "shards", ()) or ())
        rec["rss_start_mb"] = proc.memory_info().rss / (1024 * 1024)

        def timed_sink(*sink_args: Any, **sink_kwargs: Any) -> None:
            t0 = time.perf_counter()
            try:
                return sink(*sink_args, **sink_kwargs)
            finally:
                rec["sink_sec"] += time.perf_counter() - t0

        state["current_group"] = rec
        t0 = time.perf_counter()
        try:
            result = orig_native(self, registry, group, timed_sink)
            rec["native"] = result is not None
            rec["fallback"] = result is None
            rec["outputs"] = int(result or 0)
            return result
        finally:
            rec["wall_sec"] += time.perf_counter() - t0
            rec["rss_end_mb"] = proc.memory_info().rss / (1024 * 1024)
            rec["rss_delta_mb"] = rec["rss_end_mb"] - rec["rss_start_mb"]
            state["current_group"] = None

    ColumnGroupRegistry.load_data_native = patched_load
    ColumnGroupRegistry.get_alignment_idx_map = patched_idx
    FeaturePreprocessor._transform_single = patched_transform
    FeaturePreprocessor._maybe_run_native_l65_to_sink = patched_native
    _native_tf_helpers.apply_idx_map_to_array = patched_apply
    try:
        yield state
    finally:
        ColumnGroupRegistry.load_data_native = orig_load
        ColumnGroupRegistry.get_alignment_idx_map = orig_idx
        FeaturePreprocessor._transform_single = orig_transform
        FeaturePreprocessor._maybe_run_native_l65_to_sink = orig_native
        _native_tf_helpers.apply_idx_map_to_array = orig_apply


def _summarize(groups: List[Dict[str, Any]], wall_sec: float) -> Dict[str, Any]:
    native = [g for g in groups if g.get("native")]
    load = sum(float(g["load_data_native_sec"]) for g in native)
    transform = sum(float(g["transform_single_sec"]) for g in native)
    idx = sum(float(g["idx_map_sec"]) for g in native)
    sink = sum(float(g["sink_sec"]) for g in native)
    accounted = load + transform + idx + sink
    native_wall = sum(float(g["wall_sec"]) for g in native)
    return {
        "total_wall_sec": wall_sec,
        "native_group_count": len(native),
        "attempted_group_count": len(groups),
        "native_wall_sec_sum": native_wall,
        "load_data_native_sec_sum": load,
        "transform_single_sec_sum": transform,
        "idx_map_sec_sum": idx,
        "sink_sec_sum": sink,
        "accounted_sec_sum": accounted,
        "load_sink_ratio_of_accounted": (load + sink) / accounted if accounted else 0.0,
        "transform_ratio_of_accounted": transform / accounted if accounted else 0.0,
        "idx_ratio_of_accounted": idx / accounted if accounted else 0.0,
        "per_group_overhead_sec_sum": max(0.0, native_wall - accounted),
        "per_group_overhead_ratio_of_native_wall": (
            max(0.0, native_wall - accounted) / native_wall if native_wall else 0.0
        ),
    }


def main() -> None:
    args = _parse_args()
    out_root = Path(args.out_root).resolve()
    features_root = out_root / "features"
    cgsa_root = out_root / "cgsa_work"
    registry_path = out_root / "feature_registry.json"
    out_root.mkdir(parents=True, exist_ok=True)
    features_root.mkdir(parents=True, exist_ok=True)
    cgsa_root.mkdir(parents=True, exist_ok=True)

    os.environ["FFACT_USE_CGSA"] = "1"
    os.environ["FFACT_L65_NATIVE_TF"] = "1"
    os.environ["FFACT_MULTI_TF_COMPACT_ALIGNMENT"] = "1"
    os.environ["FFACT_MULTI_TF_PARALLEL"] = "0"
    os.environ["FFACT_CGSA_WORK_DIR"] = str(cgsa_root)
    os.environ["FFACT_FEATURE_REGISTRY_PATH"] = str(registry_path)
    os.environ["FFACT_L65_WORKERS"] = "1"

    from momentum.factories import create_feature_factory

    factory = create_feature_factory(cache_dir=args.cache_dir, validate_continuity=False)
    factory._storage.base_path = features_root

    config = _minimal_three_indicator_config(
        args.primary,
        args.secondary,
        rolling_enabled=not args.disable_rolling,
    )
    started = time.perf_counter()
    with _profile_native_tf() as state:
        result = factory.generate_features(
            args.symbol,
            args.primary,
            config_override=config,
            force_regenerate=True,
            persist=True,
            start_date=args.start_date,
            end_date=args.end_date,
        )
        wall_sec = time.perf_counter() - started

    groups = state["groups"]
    summary = _summarize(groups, wall_sec)
    summary.update(
        {
            "symbol": args.symbol,
            "primary": args.primary,
            "secondary": args.secondary,
            "feature_count": int(result.feature_count),
            "result_hdf5_path": str(result.hdf5_path),
            "out_root": str(out_root),
            "cgsa_work_dir": str(cgsa_root),
            "features_root": str(features_root),
            "config_hash": str(result.metadata.get("config_hash", "")),
            "multi_tf_stage_seconds": result.metadata.get("multi_tf_stage_seconds", {}),
            "layer_counts": result.layer_counts,
        }
    )

    json_path = out_root / "l65_native_tf_profile.json"
    csv_path = out_root / "l65_native_tf_profile_groups.csv"
    summary_path = out_root / "l65_native_tf_profile_summary.json"
    json_path.write_text(json.dumps({"summary": summary, "groups": groups}, indent=2), encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    fieldnames = list(groups[0].keys()) if groups else []
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(groups)

    print(json.dumps(summary, indent=2))
    print(f"PROFILE_JSON={json_path}")
    print(f"PROFILE_CSV={csv_path}")


if __name__ == "__main__":
    main()
