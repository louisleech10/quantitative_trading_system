#!/usr/bin/env python3
"""Read-only L6.5 native-tf per-group profiler (hermetic).

Builds CGSA registry via real kline (L0-L6 + alignment), then times each
native-tf eligible group with perf_counter. Cold + hot passes. Does not
modify product code or production data_cache.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass, replace as dc_replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import psutil

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_CACHE_ROOT = PROJECT_ROOT / "data_cache"
KLINE_CACHE_DIR = "data_cache/feature_klines"
KLINE_CACHE = DATA_CACHE_ROOT / "feature_klines" / "kline_cache.h5"


def _rss_mb() -> float:
    return psutil.Process().memory_info().rss / (1024.0 * 1024.0)


def _snapshot_data_cache_files() -> Dict[str, float]:
    if not DATA_CACHE_ROOT.exists():
        return {}
    return {
        str(p.relative_to(DATA_CACHE_ROOT)): p.stat().st_mtime_ns
        for p in DATA_CACHE_ROOT.rglob("*")
        if p.is_file()
    }


def _assert_hermetic(before: Dict[str, float], after: Dict[str, float]) -> List[str]:
    added = set(after) - set(before)
    removed = set(before) - set(after)
    changed = [
        k for k in set(before) & set(after) if before[k] != after[k]
    ]
    issues = []
    if added:
        issues.append(f"added={len(added)} e.g. {sorted(added)[:3]}")
    if removed:
        issues.append(f"removed={len(removed)} e.g. {sorted(removed)[:3]}")
    if changed:
        issues.append(f"changed={len(changed)} e.g. {sorted(changed)[:3]}")
    return issues


def _winsor_only_preprocessing() -> Dict[str, Any]:
    return {
        "enabled": True,
        "mode": "replace",
        "winsorization": {
            "enabled": True,
            "method": "quantile",
            "lower_q": 0.01,
            "upper_q": 0.99,
            "window": 252,
        },
        "rank_transform": {"enabled": False},
        "adaptive_zscore": {"enabled": False},
        "fractional_differencing": {"enabled": False},
        "adf_differencing": {"enabled": False},
        "gaussian_normalize": {"enabled": False},
    }


def _minimal_three_indicator_override() -> Dict[str, Any]:
    """Keep momentum RSI/MACD/ADX only; disable heavy layers."""
    return {
        "atomic_indicators": {
            "trend": {"enabled": False},
            "momentum": {
                "enabled": True,
                "indicators": [
                    {"name": "RSI", "enabled": True},
                    {"name": "MACD", "enabled": True},
                    {"name": "ADX", "enabled": True},
                    {"name": "CCI", "enabled": False},
                    {"name": "MOM", "enabled": False},
                    {"name": "ROC", "enabled": False},
                    {"name": "STOCH", "enabled": False},
                    {"name": "WILLR", "enabled": False},
                ],
            },
            "volatility": {"enabled": False},
            "volume": {"enabled": False},
            "cycle": {"enabled": False},
            "pattern": {"enabled": False},
            "statistics": {"enabled": False},
            "microstructure": {"enabled": False},
            "entropy": {"enabled": False},
            "tail_risk": {"enabled": False},
        },
        "operators": {
            "worldquant": {"enabled": False},
            "binary_signal": {"enabled": False},
        },
        "rolling_aggregation": {
            "enabled": True,
            "aggregators": {
                "mean": {"enabled": True},
                "std": {"enabled": True},
                "rank": {"enabled": False},
            },
            "windows": [5, 13],
        },
        "lag_features": {"enabled": False},
        "cross_sectional": {"enabled": False},
        "meta_features": {"enabled": False},
        "preprocessing": _winsor_only_preprocessing(),
    }


@dataclass
class GroupTiming:
    group_id: str
    layer: str
    source_tf: str
    primary_tf: str
    native_rows: int
    primary_rows: int
    n_cols: int
    n_shards: int
    load_data_native_sec: float
    config_scale_sec: float
    preprocessor_init_sec: float
    transform_single_sec: float
    idx_map_sec: float
    sink_sec: float
    total_sec: float
    rss_delta_mb: float
    pass_label: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "layer": self.layer,
            "source_tf": self.source_tf,
            "primary_tf": self.primary_tf,
            "native_rows": self.native_rows,
            "primary_rows": self.primary_rows,
            "n_cols": self.n_cols,
            "n_shards": self.n_shards,
            "load_data_native_sec": round(self.load_data_native_sec, 4),
            "config_scale_sec": round(self.config_scale_sec, 4),
            "preprocessor_init_sec": round(self.preprocessor_init_sec, 4),
            "transform_single_sec": round(self.transform_single_sec, 4),
            "idx_map_sec": round(self.idx_map_sec, 4),
            "sink_sec": round(self.sink_sec, 4),
            "total_sec": round(self.total_sec, 4),
            "rss_delta_mb": round(self.rss_delta_mb, 2),
            "pass": self.pass_label,
        }


def _eligible_native_groups(registry) -> List[Any]:
    from momentum.FeatureEngineering.preprocessing._native_tf_helpers import (
        scale_preprocessing_config_for_native,
        should_use_native_path,
    )

    config = _winsor_only_preprocessing()
    groups = []
    for _gid, group in registry.iter_all():
        if group.n_cols <= 0 or group.alignment is None:
            continue
        alignment = group.alignment
        scaled = scale_preprocessing_config_for_native(
            config,
            str(alignment.source_timeframe),
            str(alignment.primary_timeframe),
        )
        ok, _reason = should_use_native_path(
            is_compact_aligned=True,
            source_timeframe=str(alignment.source_timeframe),
            primary_timeframe=str(alignment.primary_timeframe),
            source_n_rows=int(alignment.source_n_rows),
            scaled_config=scaled,
        )
        if ok:
            groups.append(group)
    return groups


def _profile_one_group(
    registry,
    group: Any,
    parent_ctx,
    pass_label: str,
) -> GroupTiming:
    from dataclasses import replace as _dc_replace

    from momentum.FeatureEngineering.preprocessing._native_tf_helpers import (
        apply_idx_map_to_array,
        scale_preprocessing_config_for_native,
    )
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import (
        FeaturePreprocessor,
    )

    config = _winsor_only_preprocessing()
    group_id = str(group.group_id)
    columns = list(group.columns)
    alignment = group.alignment
    source_tf = str(alignment.source_timeframe)
    primary_tf = str(alignment.primary_timeframe)
    source_n_rows = int(alignment.source_n_rows)
    primary_n_rows = int(alignment.primary_n_rows)
    n_shards = len(getattr(group, "shards", ()) or ())
    layer = str(getattr(getattr(group, "layer", None), "value", group.layer))

    rss_before = _rss_mb()
    t_total0 = time.perf_counter()

    t0 = time.perf_counter()
    scaled_config = scale_preprocessing_config_for_native(config, source_tf, primary_tf)
    config_scale_sec = time.perf_counter() - t0

    t0 = time.perf_counter()
    native_arr = np.asarray(registry.load_data_native(group_id), dtype=np.float32)
    load_sec = time.perf_counter() - t0

    t0 = time.perf_counter()
    idx_map = registry.get_alignment_idx_map(group_id)
    idx_fetch_sec = time.perf_counter() - t0

    native_ctx = _dc_replace(
        parent_ctx,
        timeframe=source_tf or parent_ctx.timeframe,
        row_count=source_n_rows,
        time_range=None,
    )

    t0 = time.perf_counter()
    native_pp = FeaturePreprocessor(scaled_config, context=native_ctx)
    pp_init_sec = time.perf_counter() - t0

    native_df = pd.DataFrame(native_arr, columns=columns, copy=False)
    t0 = time.perf_counter()
    processed_df = native_pp._transform_single(
        native_df,
        source_layer=layer,
    )
    transform_sec = time.perf_counter() - t0

    orig_native = processed_df[columns].to_numpy(dtype=np.float32, copy=False)
    t0 = time.perf_counter()
    orig_aligned = apply_idx_map_to_array(orig_native, idx_map, primary_n_rows)
    idx_apply_sec = time.perf_counter() - t0
    idx_map_sec = idx_fetch_sec + idx_apply_sec

    t0 = time.perf_counter()
    # Simulate sink: touch bytes (no disk write)
    _ = int(orig_aligned.nbytes)
    sink_sec = time.perf_counter() - t0

    total_sec = time.perf_counter() - t_total0
    rss_delta = _rss_mb() - rss_before

    del native_df, native_arr, processed_df, orig_native, orig_aligned, native_pp

    return GroupTiming(
        group_id=group_id,
        layer=layer,
        source_tf=source_tf,
        primary_tf=primary_tf,
        native_rows=source_n_rows,
        primary_rows=primary_n_rows,
        n_cols=len(columns),
        n_shards=n_shards,
        load_data_native_sec=load_sec,
        config_scale_sec=config_scale_sec,
        preprocessor_init_sec=pp_init_sec,
        transform_single_sec=transform_sec,
        idx_map_sec=idx_map_sec,
        sink_sec=sink_sec,
        total_sec=total_sec,
        rss_delta_mb=rss_delta,
        pass_label=pass_label,
    )


def _profile_primary_full_groups(
    registry,
    parent_ctx,
    pass_label: str,
) -> List[GroupTiming]:
    """Non-native path: primary-TF groups (same_tf), winsor on primary rows."""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import (
        FeaturePreprocessor,
    )

    config = _winsor_only_preprocessing()
    pp = FeaturePreprocessor(config, context=parent_ctx)
    timings: List[GroupTiming] = []

    for _gid, group in registry.iter_all():
        if group.n_cols <= 0 or group.alignment is not None:
            continue
        if str(getattr(getattr(group, "layer", None), "value", "")) != "L3":
            continue
        group_id = str(group.group_id)
        columns = list(group.columns)
        n_rows = int(group.n_rows)
        n_shards = len(getattr(group, "shards", ()) or ())

        rss_before = _rss_mb()
        t_total0 = time.perf_counter()

        t0 = time.perf_counter()
        arr = np.asarray(registry.load_data(group_id), dtype=np.float32)
        load_sec = time.perf_counter() - t0

        df = pd.DataFrame(arr, columns=columns, copy=False)
        t0 = time.perf_counter()
        processed = pp._transform_single(df, source_layer="L3")
        transform_sec = time.perf_counter() - t0

        t0 = time.perf_counter()
        out = processed[columns].to_numpy(dtype=np.float32, copy=False)
        sink_sec = time.perf_counter() - t0

        timings.append(
            GroupTiming(
                group_id=group_id,
                layer="L3",
                source_tf=str(group.timeframe),
                primary_tf=str(group.timeframe),
                native_rows=n_rows,
                primary_rows=n_rows,
                n_cols=len(columns),
                n_shards=n_shards,
                load_data_native_sec=load_sec,
                config_scale_sec=0.0,
                preprocessor_init_sec=0.0,
                transform_single_sec=transform_sec,
                idx_map_sec=0.0,
                sink_sec=sink_sec,
                total_sec=time.perf_counter() - t_total0,
                rss_delta_mb=_rss_mb() - rss_before,
                pass_label=pass_label,
            )
        )
        del arr, df, processed, out
    return timings


def _build_registry(
    tmp_root: Path,
    symbol: str,
    primary_tf: str,
    training_tfs: List[str],
) -> Tuple[Any, Any, Any, Any]:
    """Run L0-L6 + alignment only; return (factory, registry, raw_primary)."""
    from momentum import factories as momentum_factories
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.FeatureEngineering.feature_factory import FeatureGenerationResult

    cgsa_dir = tmp_root / "cgsa_work"
    features_dir = tmp_root / "features"
    cgsa_dir.mkdir(parents=True, exist_ok=True)
    features_dir.mkdir(parents=True, exist_ok=True)

    os.environ["FFACT_CGSA_WORK_DIR"] = str(cgsa_dir)
    os.environ["FFACT_USE_CGSA"] = "1"
    os.environ["FFACT_MULTI_TF_PARALLEL"] = "0"
    os.environ["FFACT_L65_NATIVE_TF"] = "1"
    os.environ["FFACT_BATCH_SYMBOL_CONCURRENCY"] = "1"

    original_create = momentum_factories.create_feature_factory

    def _create_isolated(cache_dir: Optional[str] = None, validate_continuity: bool = True):
        factory = original_create(
            cache_dir=cache_dir or KLINE_CACHE_DIR,
            validate_continuity=validate_continuity,
        )
        factory._storage = FeatureStorage(str(features_dir))
        return factory

    momentum_factories.create_feature_factory = _create_isolated
    try:
        factory = momentum_factories.create_feature_factory(
            cache_dir=KLINE_CACHE_DIR,
            validate_continuity=False,
        )

        config_override = _minimal_three_indicator_override()
        config_override["timeframes"] = {
            "primary": primary_tf,
            "training": training_tfs,
        }

        captured: Dict[str, Any] = {}

        def _stop_before_l65_l7(self, **kwargs):
            captured["registry"] = self._cgsa_registry
            captured["raw_data"] = kwargs.get("raw_data")
            captured["config"] = kwargs.get("config")
            config_used = kwargs.get("config")
            config_payload = (
                config_used.model_dump(by_alias=True)
                if config_used is not None and hasattr(config_used, "model_dump")
                else {}
            )
            raw = kwargs.get("raw_data")
            return FeatureGenerationResult(
                features_df=pd.DataFrame(),
                labels_df=pd.DataFrame(index=raw.index if raw is not None else None),
                metadata={"profile_stop": True},
                feature_count=int(self._cgsa_registry.total_columns()) if self._cgsa_registry else 0,
                generation_time=0.0,
                layer_counts={},
                config_used=config_payload,
            )

        factory._layer7_raw_from_cgsa_pipeline = _stop_before_l65_l7.__get__(factory, type(factory))

        if not KLINE_CACHE.exists():
            raise FileNotFoundError(f"missing kline cache: {KLINE_CACHE}")

        factory.generate_features(
            symbol=symbol,
            timeframe=primary_tf,
            config_override=config_override,
            force_regenerate=True,
        )

        registry = captured.get("registry")
        if registry is None:
            raise RuntimeError("registry not captured — pipeline did not reach L7 hook")
        return factory, registry, captured.get("raw_data"), captured.get("config")
    finally:
        momentum_factories.create_feature_factory = original_create


def _summarize(timings: List[GroupTiming]) -> Dict[str, Any]:
    if not timings:
        return {"count": 0}

    def _sum(attr: str) -> float:
        return float(sum(getattr(t, attr) for t in timings))

    total_wall = _sum("total_sec")
    load = _sum("load_data_native_sec")
    transform = _sum("transform_single_sec")
    idx = _sum("idx_map_sec")
    overhead = _sum("config_scale_sec") + _sum("preprocessor_init_sec")
    sink = _sum("sink_sec")

    return {
        "count": len(timings),
        "total_wall_sec": round(total_wall, 3),
        "sum_load_sec": round(load, 3),
        "sum_transform_sec": round(transform, 3),
        "sum_idx_map_sec": round(idx, 3),
        "sum_overhead_sec": round(overhead, 3),
        "sum_sink_sec": round(sink, 3),
        "pct_load": round(100.0 * load / total_wall, 1) if total_wall else 0.0,
        "pct_transform": round(100.0 * transform / total_wall, 1) if total_wall else 0.0,
        "pct_idx_map": round(100.0 * idx / total_wall, 1) if total_wall else 0.0,
        "pct_overhead": round(100.0 * overhead / total_wall, 1) if total_wall else 0.0,
        "pct_sink": round(100.0 * sink / total_wall, 1) if total_wall else 0.0,
        "mean_per_group_sec": round(total_wall / len(timings), 4),
        "mean_rss_delta_mb": round(_sum("rss_delta_mb") / len(timings), 2),
        "total_native_rows": timings[0].native_rows if timings else 0,
        "total_primary_rows": timings[0].primary_rows if timings else 0,
    }


def _cold_hot_delta(cold: List[GroupTiming], hot: List[GroupTiming]) -> Dict[str, Any]:
    by_id_cold = {t.group_id: t for t in cold}
    load_drops = []
    transform_ratios = []
    for t in hot:
        c = by_id_cold.get(t.group_id)
        if c is None:
            continue
        if c.load_data_native_sec > 1e-6:
            load_drops.append(1.0 - t.load_data_native_sec / c.load_data_native_sec)
        if c.transform_single_sec > 1e-6:
            transform_ratios.append(t.transform_single_sec / c.transform_single_sec)

    return {
        "load_median_drop_pct": round(100.0 * float(np.median(load_drops)), 1) if load_drops else None,
        "load_mean_drop_pct": round(100.0 * float(np.mean(load_drops)), 1) if load_drops else None,
        "transform_median_ratio": round(float(np.median(transform_ratios)), 3) if transform_ratios else None,
        "io_not_dominant": (
            (float(np.median(load_drops)) > 0.8 if load_drops else False)
            and (0.85 < float(np.median(transform_ratios)) < 1.15 if transform_ratios else True)
        ),
    }


def run_scenario(
    tmp_root: Path,
    symbol: str,
    primary_tf: str,
    training_tfs: List[str],
    label: str,
) -> Dict[str, Any]:
    print(f"\n{'='*72}\nSCENARIO: {label} primary={primary_tf} training={training_tfs}\n{'='*72}")
    t0 = time.perf_counter()
    factory, registry, raw_data, config = _build_registry(tmp_root / label, symbol, primary_tf, training_tfs)
    build_sec = time.perf_counter() - t0
    print(f"Registry build (L0-L6+align): {build_sec:.1f}s groups={len(list(registry.iter_all()))}")

    parent_ctx = factory._build_preprocessing_context(raw_data, config)

    native_groups = _eligible_native_groups(registry)
    l3_native = [g for g in native_groups if str(getattr(getattr(g, "layer", None), "value", "")) == "L3"]
    print(f"Native-eligible groups: {len(native_groups)} (L3={len(l3_native)})")

    cold_native: List[GroupTiming] = []
    hot_native: List[GroupTiming] = []
    for pass_label, bucket in (("cold", cold_native), ("hot", hot_native)):
        gc.collect()
        for group in native_groups:
            cold_native if pass_label == "cold" else hot_native  # silence lint
            bucket.append(_profile_one_group(registry, group, parent_ctx, pass_label))

    cold_primary: List[GroupTiming] = []
    hot_primary: List[GroupTiming] = []
    if primary_tf == "1h":
        for pass_label, bucket in (("cold", cold_primary), ("hot", hot_primary)):
            gc.collect()
            bucket.extend(_profile_primary_full_groups(registry, parent_ctx, pass_label))

    cold_l3 = [t for t in cold_native if t.layer == "L3"]
    hot_l3 = [t for t in hot_native if t.layer == "L3"]

    result = {
        "label": label,
        "primary_tf": primary_tf,
        "training_tfs": training_tfs,
        "registry_build_sec": round(build_sec, 2),
        "native_eligible": len(native_groups),
        "native_l3": len(l3_native),
        "cold_native_summary": _summarize(cold_native),
        "hot_native_summary": _summarize(hot_native),
        "cold_l3_summary": _summarize(cold_l3),
        "hot_l3_summary": _summarize(hot_l3),
        "cold_hot_l3": _cold_hot_delta(cold_l3, hot_l3),
        "cold_primary_l3_summary": _summarize(cold_primary),
        "hot_primary_l3_summary": _summarize(hot_primary),
        "per_group_cold_l3": [t.to_dict() for t in cold_l3],
    }

    if cold_l3 and cold_primary:
        ratio = cold_l3[0].native_rows / max(cold_l3[0].primary_rows, 1)
        result["row_amplification"] = round(ratio, 2)
        result["wall_ratio_l3_native_vs_primary"] = round(
            _summarize(cold_l3)["total_wall_sec"] / max(_summarize(cold_primary)["total_wall_sec"], 1e-6),
            2,
        )

    return result


def _cpu_io_verdict(summary: Dict[str, Any], cold_hot: Dict[str, Any]) -> str:
    pct_load = summary.get("pct_load", 0.0)
    pct_transform = summary.get("pct_transform", 0.0)
    if cold_hot.get("io_not_dominant"):
        return "CPU-bound (load drops >80% hot vs cold; transform stable)"
    if pct_load + summary.get("pct_sink", 0.0) >= 40.0:
        return "I/O-bound (load+sink >= 40% even on hot pass)"
    if pct_transform >= 60.0:
        return "CPU-bound (transform >= 60% wall)"
    return "mixed"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--tmp-root", type=Path, default=None)
    args = parser.parse_args()

    if not KLINE_CACHE.exists():
        print(f"BLOCKED: missing {KLINE_CACHE}")
        return 2

    tmp_root = args.tmp_root or Path("/tmp") / f"l65_native_profile_{int(time.time())}"
    tmp_root.mkdir(parents=True, exist_ok=True)

    before = _snapshot_data_cache_files()
    print(f"Hermetic: tmp_root={tmp_root} data_cache_files_before={len(before)}")

    all_results: Dict[str, Any] = {
        "symbol": args.symbol,
        "kline_cache": str(KLINE_CACHE),
        "tmp_root": str(tmp_root),
        "scenarios": [],
    }

    scenarios = [
        ("12h_primary_1h_secondary", "12h", ["12h", "1h"]),
        ("1h_primary_12h_secondary", "1h", ["1h", "12h"]),
    ]

    for label, primary, training in scenarios:
        all_results["scenarios"].append(
            run_scenario(tmp_root, args.symbol, primary, training, label)
        )

    after = _snapshot_data_cache_files()
    hermetic_issues = _assert_hermetic(before, after)
    all_results["hermetic"] = {
        "before_files": len(before),
        "after_files": len(after),
        "issues": hermetic_issues,
        "pass": not hermetic_issues,
    }

    # Cross-scenario 32x anchor
    s12 = all_results["scenarios"][0]
    s1h = all_results["scenarios"][1]
    cold12_l3 = s12["cold_l3_summary"]
    cold1h_l3 = s1h.get("cold_primary_l3_summary", {})
    if cold12_l3.get("count") and cold1h_l3.get("count"):
        all_results["comparison_32x_anchor"] = {
            "native_l3_wall_sec_12h_primary": cold12_l3["total_wall_sec"],
            "primary_l3_wall_sec_1h_primary": cold1h_l3["total_wall_sec"],
            "ratio": round(
                cold12_l3["total_wall_sec"] / max(cold1h_l3["total_wall_sec"], 1e-6),
                2,
            ),
            "native_rows": cold12_l3.get("total_native_rows"),
            "primary_rows_1h": cold1h_l3.get("total_native_rows"),
            "groups_native_l3": cold12_l3["count"],
            "groups_primary_l3": cold1h_l3["count"],
        }

    for sc in all_results["scenarios"]:
        sc["cpu_io_verdict_l3_cold"] = _cpu_io_verdict(
            sc.get("cold_l3_summary", {}),
            sc.get("cold_hot_l3", {}),
        )

    out_path = tmp_root / "profile_results.json"
    out_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")

    print(f"\n{'='*72}\nSUMMARY\n{'='*72}")
    for sc in all_results["scenarios"]:
        c = sc["cold_l3_summary"]
        ch = sc["cold_hot_l3"]
        print(
            f"{sc['label']}: L3 native groups={c.get('count',0)} "
            f"wall={c.get('total_wall_sec',0):.2f}s "
            f"transform={c.get('pct_transform',0):.1f}% load={c.get('pct_load',0):.1f}% "
            f"overhead={c.get('pct_overhead',0):.1f}% idx={c.get('pct_idx_map',0):.1f}% "
            f"| load_drop_hot={ch.get('load_median_drop_pct')}% "
            f"| {sc['cpu_io_verdict_l3_cold']}"
        )
    if "comparison_32x_anchor" in all_results:
        cmp = all_results["comparison_32x_anchor"]
        print(
            f"\n32x anchor: native_l3={cmp['native_l3_wall_sec_12h_primary']:.2f}s "
            f"vs primary_l3={cmp['primary_l3_wall_sec_1h_primary']:.2f}s "
            f"ratio={cmp['ratio']:.1f}x "
            f"(rows {cmp['native_rows']} native / {cmp['primary_rows_1h']} primary)"
        )
    print(f"Hermetic pass={all_results['hermetic']['pass']} issues={hermetic_issues}")
    print(f"JSON: {out_path}")
    return 0 if all_results["hermetic"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
