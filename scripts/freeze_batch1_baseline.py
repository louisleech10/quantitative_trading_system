#!/usr/bin/env python3
"""Freeze the Batch1 follow-up behavior baseline from the unmodified HEAD."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.preprocessing._numba_transforms import rolling_winsorize_array


BASELINE_PATH = REPO_ROOT / "tests/_golden/batch1_followup/baseline.json"
PERF_ROWS = 20_000
PERF_COLS = 2_000
PERF_SHARD_ROWS = 4_096


def _hash_array(values: np.ndarray) -> dict[str, str]:
    mask = np.isnan(values)
    normalized = np.where(mask, 0.0, values).astype(np.float64)
    return {
        "value_hash": hashlib.sha256(normalized.tobytes()).hexdigest(),
        "mask_hash": hashlib.sha256(mask.tobytes()).hexdigest(),
    }


def _winsor_fixture() -> np.ndarray:
    rng = np.random.default_rng(20260612)
    values = rng.standard_normal((1_000, 3)).astype(np.float32)
    values[:60, 0] = np.nan
    values[400:405, 1] = np.nan
    values[250, 2] = 8.0 * float(np.nanstd(values[:, 2]))
    values[750, 2] = -8.0 * float(np.nanstd(values[:, 2]))
    return values


def _nan_reference_cases() -> dict[str, np.ndarray]:
    leading = np.arange(50, dtype=np.float64)[:, None]
    leading[:30] = np.nan
    trailing = np.arange(50, dtype=np.float64)[:, None]
    trailing[-30:] = np.nan
    mid_hole = np.arange(50, dtype=np.float64)[:, None]
    mid_hole[20:27] = np.nan
    cross_chunk = np.arange(700, dtype=np.float64)[:, None]
    cross_chunk[333:] = np.nan
    return {
        "empty": np.empty((0, 1), dtype=np.float64),
        "all_nan": np.full((50, 1), np.nan, dtype=np.float64),
        "leading_only": leading,
        "trailing_only": trailing,
        "mid_hole": mid_hole,
        "cross_chunk": cross_chunk,
    }


def _build_perf_registry(root: Path) -> ColumnGroupRegistry:
    registry = ColumnGroupRegistry(root / "registry", memory_buffer_groups=0)
    row_values = np.arange(PERF_ROWS, dtype=np.float32)[:, None]
    col_values = np.arange(PERF_COLS, dtype=np.float32)[None, :]
    values = np.remainder(row_values + col_values, 997.0).astype(np.float32, copy=False)
    group = ColumnGroup(
        group_id="batch1_perf",
        layer=LayerSource.L2,
        timeframe="12h",
        data_source="baseline",
        indicator="stream",
        columns=tuple(f"perf_{index}" for index in range(PERF_COLS)),
        shape=values.shape,
        dtype="float32",
    )
    registry.save_data(group, values)
    return registry


def run_stream_benchmark() -> tuple[float, int]:
    """Run the fixed 2000x20000 single-worker stream-write benchmark."""
    samples: list[tuple[float, int]] = []
    for iteration in range(4):
        root = Path(tempfile.mkdtemp(prefix="batch1-followup-perf-"))
        try:
            registry = _build_perf_registry(root)
            storage = FeatureStorage(str(root / "features"))
            tracemalloc.start()
            started = time.perf_counter()
            storage.write_raw_from_registry_stream(
                symbol="BASELINE",
                tf="12h",
                config_hash=f"run-{iteration}",
                registry=registry,
                preprocessor=None,
                n_workers=1,
                cleanup_intermediate=True,
                l65_mode="none",
            )
            wall = time.perf_counter() - started
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            if iteration > 0:
                samples.append((wall, int(peak)))
        finally:
            if tracemalloc.is_tracing():
                tracemalloc.stop()
            shutil.rmtree(root, ignore_errors=True)
    return float(median(item[0] for item in samples)), int(median(item[1] for item in samples))


def build_baseline() -> dict[str, Any]:
    fixture = _winsor_fixture()
    default_output = rolling_winsorize_array(fixture.copy(), window=252, min_periods=63)
    w100_output = rolling_winsorize_array(fixture.copy(), window=100, min_periods=25)
    default_hashes = _hash_array(default_output)
    w100_hashes = _hash_array(w100_output)
    perf_wall, perf_peak = run_stream_benchmark()
    return {
        "winsor_default_value_hash": default_hashes["value_hash"],
        "winsor_default_mask_hash": default_hashes["mask_hash"],
        "winsor_w100_value_hash": w100_hashes["value_hash"],
        "winsor_w100_mask_hash": w100_hashes["mask_hash"],
        "winsor_w100_min_periods": 25,
        "max_nan_ratio_btc_12h": FeatureFactory._default_max_nan_ratio("BTCUSDT", "12h"),
        "nan_stats_reference": {
            name: FeatureFactory._abnormal_nan_count(values)
            for name, values in _nan_reference_cases().items()
        },
        "perf_wall_seconds": perf_wall,
        "perf_peak_bytes": perf_peak,
        "perf_parameters": {
            "rows": PERF_ROWS,
            "columns": PERF_COLS,
            "shard_rows": PERF_SHARD_ROWS,
            "workers": 1,
            "warmup_runs": 1,
            "measured_runs": 3,
        },
    }


def _stable_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if not key.startswith("perf_")}


def main() -> int:
    payload = build_baseline()
    if BASELINE_PATH.exists():
        try:
            existing = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Existing baseline is unreadable: {exc}", file=sys.stderr)
            return 1
        if _stable_payload(existing) != _stable_payload(payload):
            print("Existing baseline differs from current HEAD behavior", file=sys.stderr)
            print(json.dumps({"existing": existing, "current": payload}, indent=2, sort_keys=True))
            return 1
        print(f"Baseline unchanged: {BASELINE_PATH}")
        return 0

    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Baseline written: {BASELINE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
