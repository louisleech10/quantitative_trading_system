#!/usr/bin/env python3
"""Freeze and compare Phase 4 multi-symbol IC-First golden fingerprints."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "golden" / "multi_symbol_c3"
DEFAULT_CONFIG = FIXTURE_DIR / "config.json"
DEFAULT_BASELINE = FIXTURE_DIR / "baseline.parquet"
DEFAULT_ENV = FIXTURE_DIR / "env_snapshot.json"
DEFAULT_SYMBOL = "BTCUSDT"
DEFAULT_TIMEFRAME = "1h"
SMOKE_SYMBOLS = ("ETHUSDT", "BTCUSDT", "DOGEUSDT")
ABS_TOL = 1e-8
REL_TOL = 1e-6


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _config_hash(config: Dict[str, Any]) -> str:
    payload = dict(config)
    payload.pop("config_hash", None)
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:12]


def _sha_text(values: List[str]) -> str:
    return hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()


def _hash_array(values: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(values)
    return hashlib.sha256(contiguous.view(np.uint8)).hexdigest()


def _canonical_frame(frame: pd.DataFrame) -> pd.DataFrame:
    ordered = frame.sort_index().sort_index(axis=1)
    return ordered.astype("float64", copy=False)


@contextmanager
def _golden_environment() -> Iterator[None]:
    old_cgsa = os.environ.get("FFACT_USE_CGSA")
    old_ic_env = os.environ.get("FFACT_IC_FIRST_PIPELINE")
    os.environ["FFACT_USE_CGSA"] = "0"
    try:
        yield
    finally:
        if old_cgsa is None:
            os.environ.pop("FFACT_USE_CGSA", None)
        else:
            os.environ["FFACT_USE_CGSA"] = old_cgsa
        if old_ic_env is None:
            os.environ.pop("FFACT_IC_FIRST_PIPELINE", None)
        else:
            os.environ["FFACT_IC_FIRST_PIPELINE"] = old_ic_env


def _compute_frame(symbol: str, timeframe: str, config: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry
    from momentum.factories import create_feature_factory

    cache_path = ROOT / "data_cache" / "feature_klines" / "kline_cache.h5"
    if not cache_path.exists():
        raise FileNotFoundError(
            f"Missing real kline cache: {cache_path}. Provide BTCUSDT 1h data; golden must not fake data."
        )

    with tempfile.TemporaryDirectory(prefix="golden_multi_symbol_c3_") as tmp:
        factory = create_feature_factory(cache_dir=str(cache_path.parent), validate_continuity=False)
        factory._registry = FeatureRegistry(Path(tmp) / "registry.json")
        result = factory.generate_features(
            symbol=symbol,
            timeframe=timeframe,
            config_override=config,
            force_regenerate=True,
            persist=False,
        )
    frame = _canonical_frame(result.features_df)
    metadata = {
        "feature_count": int(result.feature_count),
        "layer_counts": result.layer_counts,
        "config_hash": result.metadata.get("config_hash"),
        "data_range": result.metadata.get("data_range"),
    }
    return frame, metadata


def _fingerprint_frame(frame: pd.DataFrame, symbol: str, timeframe: str, config_hash: str) -> pd.DataFrame:
    feature_names = list(frame.columns)
    feature_set_sha256 = _sha_text(feature_names)
    schema = {name: str(frame[name].dtype) for name in feature_names}
    schema_sha256 = hashlib.sha256(_canonical_json(schema).encode("utf-8")).hexdigest()
    rows: List[Dict[str, Any]] = []
    for feature in feature_names:
        series = frame[feature]
        values = series.to_numpy(dtype=np.float64, copy=True)
        nan_mask = np.isnan(values)
        canonical_values = np.nan_to_num(values, nan=0.0, posinf=np.inf, neginf=-np.inf)
        rows.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "config_hash": config_hash,
                "feature_name": feature,
                "feature_count": len(feature_names),
                "row_count": int(len(frame.index)),
                "feature_set_sha256": feature_set_sha256,
                "schema_sha256": schema_sha256,
                "dtype": str(series.dtype),
                "mean": float(np.nanmean(values)) if not np.all(nan_mask) else np.nan,
                "std": float(np.nanstd(values)) if not np.all(nan_mask) else np.nan,
                "nan_ratio": float(nan_mask.mean()) if len(values) else 0.0,
                "value_chunk_sha256": _hash_array(canonical_values),
                "nan_mask_sha256": _hash_array(nan_mask.astype(np.uint8)),
            }
        )
    return pd.DataFrame(rows).sort_values("feature_name").reset_index(drop=True)


def _smoke_symbols(config: Dict[str, Any], timeframe: str, config_hash: str) -> List[Dict[str, Any]]:
    smoke: List[Dict[str, Any]] = []
    for symbol in SMOKE_SYMBOLS:
        frame, _metadata = _compute_frame(symbol, timeframe, config)
        names = list(frame.columns)
        schema = {name: str(frame[name].dtype) for name in names}
        smoke.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "config_hash": config_hash,
                "feature_count": len(names),
                "row_count": int(len(frame.index)),
                "feature_set_sha256": _sha_text(names),
                "schema_sha256": hashlib.sha256(_canonical_json(schema).encode("utf-8")).hexdigest(),
            }
        )
    return smoke


def _env_snapshot(
    config: Dict[str, Any],
    config_hash: str,
    compute_fn: str,
    metadata: Dict[str, Any],
    smoke: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "config_hash": config_hash,
        "config_declared_hash": config.get("config_hash"),
        "compute_fn": compute_fn,
        "metadata": metadata,
        "smoke_symbols": smoke,
        "env": {
            key: os.environ.get(key)
            for key in sorted(os.environ)
            if key.startswith("FFACT_")
        },
        "python": sys.version,
        "platform": platform.platform(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
    }


def freeze(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    baseline_path = Path(args.baseline)
    env_path = Path(args.env)
    config = _load_config(config_path)
    config_hash = _config_hash(config)
    if config.get("config_hash") != config_hash:
        raise ValueError(
            f"config_hash mismatch: config.json has {config.get('config_hash')!r}, expected {config_hash!r}"
        )

    with _golden_environment():
        frame, metadata = _compute_frame(args.symbol, args.tf, config)
        baseline = _fingerprint_frame(frame, args.symbol, args.tf, config_hash)
        smoke = _smoke_symbols(config, args.tf, config_hash)
        snapshot = _env_snapshot(config, config_hash, "_compute_single", metadata, smoke)

    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline.to_parquet(baseline_path, index=False)
    with env_path.open("w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"PASS freeze baseline={baseline_path} rows={len(baseline)}")
    return 0


def _compare_value(name: str, expected: float, actual: float) -> Optional[str]:
    if pd.isna(expected) and pd.isna(actual):
        return None
    abs_diff = abs(float(actual) - float(expected))
    rel_diff = abs_diff / max(abs(float(expected)), 1e-12)
    if abs_diff <= ABS_TOL or rel_diff <= REL_TOL:
        return None
    return f"{name}: expected={expected} actual={actual} abs_diff={abs_diff} rel_diff={rel_diff}"


def compare(args: argparse.Namespace) -> int:
    baseline_path = Path(args.baseline)
    config_path = Path(args.config)
    if not baseline_path.exists():
        raise FileNotFoundError(f"Missing baseline: {baseline_path}. Run freeze first.")
    config = _load_config(config_path)
    config_hash = _config_hash(config)
    baseline = pd.read_parquet(baseline_path).sort_values("feature_name").reset_index(drop=True)

    failures: List[str] = []
    with _golden_environment():
        frame, metadata = _compute_frame(args.symbol, args.tf, config)
        current = _fingerprint_frame(frame, args.symbol, args.tf, config_hash)
        repeat_frame, _repeat_metadata = _compute_frame(args.symbol, args.tf, config)
        repeat = _fingerprint_frame(repeat_frame, args.symbol, args.tf, config_hash)

    if not baseline["feature_name"].equals(current["feature_name"]):
        failures.append("feature_name set/order mismatch")
    comparable = [
        "feature_count",
        "row_count",
        "feature_set_sha256",
        "schema_sha256",
        "dtype",
        "nan_ratio",
        "value_chunk_sha256",
        "nan_mask_sha256",
    ]
    for column in comparable:
        mismatch = baseline[column].astype(str) != current[column].astype(str)
        for idx in list(np.flatnonzero(mismatch.to_numpy()))[:10]:
            failures.append(
                f"{baseline.loc[idx, 'feature_name']} {column}: "
                f"expected={baseline.loc[idx, column]} actual={current.loc[idx, column]}"
            )
    for metric in ("mean", "std"):
        for idx, feature in enumerate(baseline["feature_name"]):
            failure = _compare_value(
                f"{feature} {metric}",
                baseline.loc[idx, metric],
                current.loc[idx, metric],
            )
            if failure:
                failures.append(failure)

    if not current["value_chunk_sha256"].equals(repeat["value_chunk_sha256"]):
        failures.append("single vs multi(1 symbol) repeat value hash mismatch")
    if metadata.get("feature_count") != int(current["feature_count"].iloc[0]):
        failures.append("metadata feature_count mismatch")

    if failures:
        print("FAIL")
        for item in failures[:50]:
            print(item)
        return 1
    print("PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    freeze_parser = subparsers.add_parser("freeze")
    freeze_parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    freeze_parser.add_argument("--tf", default=DEFAULT_TIMEFRAME)
    freeze_parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    freeze_parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    freeze_parser.add_argument("--env", default=str(DEFAULT_ENV))
    freeze_parser.set_defaults(func=freeze)

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    compare_parser.add_argument("--tf", default=DEFAULT_TIMEFRAME)
    compare_parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    compare_parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    compare_parser.set_defaults(func=compare)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
