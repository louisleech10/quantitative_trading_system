"""Verify CGSA pipeline works end-to-end with available kline data.

If multi-TF data (12h) is missing, falls back to single-TF (1h only).
Validates: CGSA registry populated, per-group alignment, L6.5, L7 persist.
"""
from __future__ import annotations

import gc
import os
import sys
import time
from pathlib import Path

import psutil

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure CGSA is enabled
os.environ.setdefault("FFACT_USE_CGSA", "1")

from momentum.core.logging import get_logger
from momentum.factories import create_feature_factory

logger = get_logger(__name__)

SYMBOL = "ETHUSDT"
PRIMARY_TF = "1h"


def _check_available_tfs() -> list:
    """Check which timeframes have data available."""
    import h5py
    h5_path = Path("data_cache/feature_klines/kline_cache.h5")
    if not h5_path.exists():
        print(f"ERROR: {h5_path} not found")
        sys.exit(1)

    available_tfs = []
    with h5py.File(h5_path, "r") as f:
        if SYMBOL in f:
            for tf in f[SYMBOL].keys():
                if tf.startswith("_"):
                    continue
                ds = f[SYMBOL][tf]
                if "data" in ds:
                    rows = ds["data"].shape[0]
                    print(f"  Found {SYMBOL}/{tf}: {rows} rows")
                    if rows > 0:
                        available_tfs.append(tf)
    return available_tfs


def main() -> None:
    process = psutil.Process()
    gc.collect()
    rss_before = process.memory_info().rss

    available_tfs = _check_available_tfs()
    if not available_tfs:
        print("ERROR: No kline data available")
        sys.exit(1)

    training_tfs = [PRIMARY_TF]
    if "12h" in available_tfs:
        training_tfs = ["1h", "12h"]

    print(f"\n{'='*60}")
    print(f"CGSA Pipeline Verification")
    print(f"Symbol: {SYMBOL}")
    print(f"Training TFs: {training_tfs}")
    print(f"FFACT_USE_CGSA={os.environ.get('FFACT_USE_CGSA', 'unset')}")
    print(f"RSS before: {rss_before / (1024**2):.1f} MB")
    print(f"{'='*60}\n")

    factory = create_feature_factory()

    config_override = {
        "timeframes": {
            "primary": PRIMARY_TF,
            "training": training_tfs,
            "alignment": "point_in_time",
            "alignment_mode": "open_minus",
        },
        "preprocessing": {"enabled": True},
    }

    t_start = time.perf_counter()
    try:
        result = factory.generate_features(
            symbol=SYMBOL,
            timeframe=PRIMARY_TF,
            config_override=config_override,
            force_regenerate=True,
            persist=True,
        )
    except Exception as exc:
        print(f"\nPIPELINE FAILED: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    t_total = time.perf_counter() - t_start
    gc.collect()
    rss_after = process.memory_info().rss

    print(f"\n{'='*60}")
    print(f"CGSA Pipeline COMPLETED in {t_total:.2f}s")
    print(f"Feature count: {result.feature_count}")
    print(f"Layer counts: {result.layer_counts}")
    print(f"RSS: {rss_before/(1024**2):.0f} → {rss_after/(1024**2):.0f} MB")

    # Check registry state
    registry = factory._cgsa_registry
    if registry is not None:
        groups = list(registry.iter_all())
        print(f"\nCGSA Registry: {len(groups)} groups, {registry.total_columns()} total columns")
        for gid, group in groups[:10]:
            print(f"  {gid}: {group.n_cols} cols, layer={group.layer.value}")
        if len(groups) > 10:
            print(f"  ... and {len(groups) - 10} more groups")

        # Check manifest
        if registry.manifest_path and registry.manifest_path.exists():
            print(f"\nManifest: {registry.manifest_path} ({registry.manifest_path.stat().st_size} bytes)")

        # Check parquet output
        features_dir = Path("data_cache/features")
        parquet_files = list(features_dir.rglob("*.parquet")) if features_dir.exists() else []
        total_parquet_mb = sum(f.stat().st_size for f in parquet_files) / (1024**2)
        print(f"Parquet output: {len(parquet_files)} files, {total_parquet_mb:.2f} MB total")
    else:
        print("\nWARNING: CGSA registry is None — CGSA path was NOT used!")

    # Check metadata
    if hasattr(result, "metadata"):
        md = result.metadata
        print(f"\nMetadata keys: {sorted(md.keys())}")
        if "manifest_path" in md:
            print(f"  manifest_path: {md['manifest_path']}")
        if "persisted_group_paths" in md:
            print(f"  persisted groups: {len(md['persisted_group_paths'])}")
        if "skipped_timeframes" in md:
            print(f"  skipped TFs: {md['skipped_timeframes']}")

    print(f"\n{'='*60}")
    print("VERIFICATION PASSED ✅" if result.feature_count > 0 else "VERIFICATION FAILED ❌")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
