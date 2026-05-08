from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import psutil

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor  # noqa: E402
from momentum.core.logging import get_logger  # noqa: E402

logger = get_logger(__name__)

DEFAULT_GOLDEN_DIR = PROJECT_ROOT / "tests" / "golden" / "l65"
KLINE_CACHE_PATH = PROJECT_ROOT / "data_cache" / "feature_klines" / "kline_cache.h5"
TIER1_DIR = DEFAULT_GOLDEN_DIR / "tier1_structure"
TIER2_DIR = DEFAULT_GOLDEN_DIR / "tier2_reduced"
TIER2_ICFIRST_DIR = DEFAULT_GOLDEN_DIR / "tier2_icfirst"
TEST_INVENTORY_PATH = DEFAULT_GOLDEN_DIR / "test_inventory.txt"
L65_TEST_KEYWORDS = re.compile(
    r"l65|preprocess|feature_preprocessor|fracdiff|adf|d_star",
    re.IGNORECASE,
)
LAYER_RE = re.compile(r"^(L\d+)_")
MIN_TIER2B_ROWS = 1500
STRICT_RAM_GATE_GB = 4.0
MIN_REDUCED_WORKLOAD_GATE_GB = 1.0


class GoldenBuildError(RuntimeError):
    """Raised when a golden baseline cannot be generated safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_stable_json_bytes(payload)).hexdigest()


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp_path.write_text(content, encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _atomic_write_json(path: Path, payload: Any) -> None:
    _atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _atomic_write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        frame.to_parquet(tmp_path)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _ram_gate(min_available_gb: float, label: str) -> bool:
    available_gb = psutil.virtual_memory().available / float(1024**3)
    if available_gb < float(min_available_gb):
        logger.error(
            "[L6.5] %s blocked: available RAM %.2fGB < %.2fGB",
            label,
            available_gb,
            min_available_gb,
        )
        return False
    logger.info(
        "[L6.5] %s RAM gate passed: available %.2fGB >= %.2fGB",
        label,
        available_gb,
        min_available_gb,
    )
    return True


def _estimate_reduced_workload_ram_gate(rows: int, cols: int) -> float:
    dense_float64_gb = (
        max(rows, 1) * max(cols, 1) * np.dtype(np.float64).itemsize / float(1024**3)
    )
    estimated_gb = MIN_REDUCED_WORKLOAD_GATE_GB + dense_float64_gb * 128.0
    return min(STRICT_RAM_GATE_GB, max(MIN_REDUCED_WORKLOAD_GATE_GB, estimated_gb))


def _extract_layer(column_name: str) -> str:
    match = LAYER_RE.match(column_name)
    return match.group(1) if match else "unknown"


def _extract_source(column_name: str) -> str:
    parts = column_name.split("_")
    if len(parts) >= 2 and LAYER_RE.match(column_name):
        return parts[1]
    if parts:
        return parts[0]
    return "unknown"


def make_synthetic_l65_dataset(
    rows: int = 1000,
    cols: int = 100,
    stationary_ratio: float = 0.6,
    seed: int = 42,
) -> pd.DataFrame:
    """Build a deterministic L6.5 fixture with mixed stationary and non-stationary columns."""

    if rows <= 0:
        raise ValueError("rows must be positive")
    if cols <= 0:
        raise ValueError("cols must be positive")
    if not 0.0 <= stationary_ratio <= 1.0:
        raise ValueError("stationary_ratio must be between 0 and 1")

    rng = np.random.default_rng(seed)
    index = pd.date_range("2024-01-01", periods=rows, freq="H", name="timestamp")
    stationary_count = int(round(cols * stationary_ratio))
    layers = ("L1", "L2", "L3", "L4", "L5")
    payload: Dict[str, np.ndarray] = {}

    for col_idx in range(cols):
        layer = layers[col_idx % len(layers)]
        is_stationary = col_idx < stationary_count
        noise = rng.normal(loc=0.0, scale=1.0, size=rows)
        if is_stationary:
            values = np.empty(rows, dtype=np.float64)
            values[0] = noise[0]
            for row_idx in range(1, rows):
                values[row_idx] = 0.35 * values[row_idx - 1] + noise[row_idx]
            kind = "stationary"
        else:
            drift = 0.001 * (1 + (col_idx % 5))
            values = np.cumsum(noise + drift)
            kind = "randomwalk"

        if col_idx % 17 == 0:
            values[:5] = np.nan
        payload[f"{layer}_synthetic_{kind}_{col_idx:03d}"] = values.astype(np.float32)

    return pd.DataFrame(payload, index=index)


def _column_inventory_from_frame(frame: pd.DataFrame) -> List[Dict[str, str]]:
    return [
        {
            "name": str(column),
            "dtype": str(frame[column].dtype),
            "layer": _extract_layer(str(column)),
            "source": _extract_source(str(column)),
        }
        for column in frame.columns
    ]


def build_tier1_structure(out_dir: Path = TIER1_DIR) -> None:
    """Write the Tier 1 structural baseline without running Layer 6.5."""

    structure_frame = make_synthetic_l65_dataset(rows=100, cols=100)
    inventory = _column_inventory_from_frame(structure_frame)
    schema_hash = _sha256_payload(inventory)

    _atomic_write_json(out_dir / "column_inventory.json", inventory)
    _atomic_write_text(out_dir / "schema_hash.txt", f"{schema_hash}\n")
    logger.info("[L6.5] Tier 1 structure baseline written: %d columns", len(inventory))


def _l65_full_preprocessing_config() -> Dict[str, Any]:
    return {
        "enabled": True,
        "mode": "replace",
        "winsorization": {
            "enabled": True,
            "method": "quantile",
            "quantile_range": [0.01, 0.99],
            "apply_to": "all",
        },
        "fractional_differencing": {
            "enabled": True,
            "d_range": [0.0, 1.0],
            "adf_threshold": 0.10,
            "weight_threshold": 1e-5,
            "precision": 0.01,
            "apply_to": "non_stationary",
            "cache_d_star": True,
        },
        "adf_differencing": {
            "enabled": True,
            "adf_threshold": 0.10,
            "max_diff": 1,
            "sample_size": 500,
            "apply_to": "non_stationary",
        },
        "rank_transform": {"enabled": True, "window": 50, "apply_to": "all"},
        "gaussian_normalize": {
            "enabled": True,
            "clip_range": [0.001, 0.999],
            "apply_to": "all",
        },
        "adaptive_zscore": {
            "enabled": True,
            "windows": [50],
            "epsilon": 1e-8,
            "apply_to": "all",
        },
    }


def _run_l65_full_preprocessing(frame: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, float]]:
    preprocessor = FeaturePreprocessor(_l65_full_preprocessing_config())
    preprocessor._d_star_cache = {}
    processed = preprocessor.transform(frame)
    d_star_cache = preprocessor._d_star_cache or {}
    return processed, {str(column): float(value) for column, value in sorted(d_star_cache.items())}


def build_tier2_synthetic(out_dir: Path = TIER2_DIR) -> None:
    """Write the Tier 2A synthetic numeric baseline."""

    dataset = make_synthetic_l65_dataset(rows=1000, cols=100, stationary_ratio=0.6)
    processed, d_star = _run_l65_full_preprocessing(dataset)

    if processed.shape != (1000, 100):
        raise GoldenBuildError(f"Unexpected synthetic baseline shape: {processed.shape}")
    if not d_star:
        raise GoldenBuildError("Synthetic d_star output is empty")

    _atomic_write_parquet(out_dir / "synthetic_baseline.parquet", processed)
    _atomic_write_json(out_dir / "d_star_synthetic.json", d_star)
    logger.info(
        "[L6.5] Tier 2A synthetic baseline written: rows=%d cols=%d d_star=%d",
        processed.shape[0],
        processed.shape[1],
        len(d_star),
    )


def _blocked_marker_path(symbol: str, tf: str, max_rows: int, out_dir: Path) -> Path:
    return out_dir / f"{symbol}_{tf}_{max_rows}rows.BLOCKED"


def _write_blocked_marker(path: Path, reason: str) -> None:
    payload = {
        "status": "blocked-not-pass",
        "reason": reason,
        "generated_at_utc": _utc_now(),
    }
    _atomic_write_json(path, payload)
    logger.warning("[L6.5] Tier 2B blocked: %s", reason)


def _load_hdf5_kline_frame(symbol: str, tf: str, hdf5_path: Path) -> Optional[pd.DataFrame]:
    if not hdf5_path.exists():
        return None

    import h5py

    dataset_key = f"{symbol}/{tf}/data"
    with h5py.File(hdf5_path, "r") as h5_file:
        if dataset_key not in h5_file:
            return None
        records = h5_file[dataset_key][()]

    frame = pd.DataFrame.from_records(records)
    if "timestamp" in frame.columns:
        unit = "ms" if int(frame["timestamp"].max()) > 10**12 else "s"
        frame.index = pd.to_datetime(frame["timestamp"], unit=unit, utc=True)
    return frame


def _build_l1_l2_real_features(raw_frame: pd.DataFrame, max_cols: int) -> pd.DataFrame:
    numeric = raw_frame.select_dtypes(include=[np.number]).copy()
    numeric = numeric.drop(columns=["timestamp"], errors="ignore")
    if numeric.empty:
        raise GoldenBuildError("Real kline frame has no numeric feature columns")

    frames: List[pd.DataFrame] = []
    base_columns = ["open", "high", "low", "close", "volume", "quote_volume", "taker_ratio"]
    for column in base_columns:
        if column in numeric.columns:
            frames.append(pd.DataFrame({f"L1_binance_{column}": numeric[column].astype(np.float32)}))

    close = numeric["close"].astype(float) if "close" in numeric.columns else numeric.iloc[:, 0].astype(float)
    volume = numeric["volume"].astype(float) if "volume" in numeric.columns else close.abs()
    derived: Dict[str, pd.Series] = {
        "L2_derived_close_return_1": close.pct_change(),
        "L2_derived_log_close": np.log(close.replace(0.0, np.nan).abs()),
        "L2_derived_volume_change_1": volume.pct_change(),
    }
    for window in (3, 5, 8, 13, 21, 34, 55, 89):
        derived[f"L2_derived_close_mean_{window}"] = close.rolling(window, min_periods=1).mean()
        derived[f"L2_derived_close_std_{window}"] = close.rolling(window, min_periods=2).std()
        derived[f"L2_derived_volume_mean_{window}"] = volume.rolling(window, min_periods=1).mean()

    frames.append(pd.DataFrame(derived, index=raw_frame.index))
    feature_frame = pd.concat(frames, axis=1).replace([np.inf, -np.inf], np.nan)
    feature_frame = feature_frame.iloc[:, :max_cols]
    return feature_frame.astype(np.float32, copy=False)


def _write_large_artifact_manifest(path: Path) -> None:
    if not path.exists() or path.stat().st_size <= 100 * 1024 * 1024:
        return
    hasher = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    manifest = {
        "artifact": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": digest,
        "note": "local real-market derived artifact exceeds 100MB; do not stage without explicit approval",
        "generated_at_utc": _utc_now(),
    }
    _atomic_write_json(path.with_suffix(".manifest.json"), manifest)


def build_tier2_real_shortwindow(
    symbol: str,
    tf: str,
    max_rows: int,
    max_cols: int,
    out_dir: Path = TIER2_DIR,
) -> None:
    """Write Tier 2B real short-window baseline or a blocked marker."""

    blocked_path = _blocked_marker_path(symbol, tf, max_rows, out_dir)
    parquet_path = out_dir / f"{symbol}_{tf}_{max_rows}rows.parquet"
    d_star_path = out_dir / f"d_star_{symbol}_{tf}_{max_rows}rows.json"
    frame = _load_hdf5_kline_frame(symbol, tf, KLINE_CACHE_PATH)
    if frame is None:
        _remove_stale_real_artifacts(parquet_path, d_star_path)
        _write_blocked_marker(
            blocked_path,
            f"missing HDF5 dataset {symbol}/{tf}/data in {KLINE_CACHE_PATH.relative_to(PROJECT_ROOT)}",
        )
        return
    if len(frame) < MIN_TIER2B_ROWS:
        _remove_stale_real_artifacts(parquet_path, d_star_path)
        _write_blocked_marker(
            blocked_path,
            f"insufficient rows for Tier 2B: {len(frame)} < {MIN_TIER2B_ROWS}",
        )
        return

    recent = frame.tail(max_rows)
    features = _build_l1_l2_real_features(recent, max_cols=max_cols)
    ram_gate_gb = _estimate_reduced_workload_ram_gate(rows=len(recent), cols=features.shape[1])
    if not _ram_gate(ram_gate_gb, label=f"Tier 2B {symbol}/{tf} reduced workload"):
        _remove_stale_real_artifacts(parquet_path, d_star_path)
        _write_blocked_marker(
            blocked_path,
            "RAM gate blocked Tier 2B reduced workload before L6.5 processing: "
            f"source={KLINE_CACHE_PATH.relative_to(PROJECT_ROOT)} rows={len(frame)} "
            f"selected_rows={len(recent)} selected_cols={features.shape[1]} "
            f"required_available_gb={ram_gate_gb:.2f}",
        )
        return
    processed, d_star = _run_l65_full_preprocessing(features)

    _atomic_write_parquet(parquet_path, processed)
    _atomic_write_json(d_star_path, d_star)
    _write_large_artifact_manifest(parquet_path)
    if blocked_path.exists():
        blocked_path.unlink()
    logger.info(
        "[L6.5] Tier 2B real baseline written: %s/%s rows=%d cols=%d d_star=%d",
        symbol,
        tf,
        processed.shape[0],
        processed.shape[1],
        len(d_star),
    )


def _ic_first_raw_config() -> Dict[str, Any]:
    return {
        "enabled": True,
        "mode": "replace",
        "winsorization": {
            "enabled": True,
            "method": "quantile",
            "quantile_range": [0.01, 0.99],
            "apply_to": "all",
        },
    }


def _ic_first_processed_config() -> Dict[str, Any]:
    return {
        "enabled": True,
        "mode": "replace",
        "winsorization": {
            "enabled": True,
            "method": "quantile",
            "quantile_range": [0.01, 0.99],
            "apply_to": "all",
        },
        "rank_transform": {"enabled": True, "window": 50, "apply_to": "all"},
        "gaussian_normalize": {
            "enabled": True,
            "clip_range": [0.001, 0.999],
            "apply_to": "all",
        },
    }


def build_ic_first_golden(
    symbol: str,
    tf: str,
    max_rows: int,
    max_cols: int,
    out_dir: Path = TIER2_ICFIRST_DIR,
    use_real_data: bool = False,
) -> Dict[str, Any]:
    """Write a small IC-First golden scaffold or a blocked marker for missing real data."""

    out_dir.mkdir(parents=True, exist_ok=True)
    blocked_path = out_dir / f"{symbol}_{tf}_{max_rows}rows.BLOCKED"
    source = "synthetic_l65_fixture"
    if use_real_data:
        frame = _load_hdf5_kline_frame(symbol, tf, KLINE_CACHE_PATH)
        if frame is None:
            _write_blocked_marker(
                blocked_path,
                "blocked_missing_data: missing HDF5 dataset "
                f"{symbol}/{tf}/data in {KLINE_CACHE_PATH.relative_to(PROJECT_ROOT)}",
            )
            return {"status": "blocked_missing_data", "path": str(blocked_path)}
        recent = frame.tail(max_rows)
        source_frame = _build_l1_l2_real_features(recent, max_cols=max_cols)
        source = "real_hdf5_shortwindow"
    else:
        source_frame = make_synthetic_l65_dataset(
            rows=min(max_rows, 1000),
            cols=min(max_cols, 100),
            stationary_ratio=0.6,
        )

    raw_frame = FeaturePreprocessor(_ic_first_raw_config()).transform(source_frame)
    selected_features = list(raw_frame.columns[: min(20, len(raw_frame.columns))])
    processed_frame = FeaturePreprocessor(_ic_first_processed_config()).transform(
        raw_frame.loc[:, selected_features]
    )

    raw_path = out_dir / f"{symbol}_{tf}_raw.parquet"
    processed_path = out_dir / f"{symbol}_{tf}_processed.parquet"
    selected_path = out_dir / f"ic_selected_features_{symbol}_{tf}.json"
    metadata_path = out_dir / f"{symbol}_{tf}_metadata.json"

    selected_payload = {
        "status": "PASS",
        "mode": "ic_first_scaffold",
        "symbol": symbol,
        "timeframe": tf,
        "source": source,
        "selected": selected_features,
        "selected_count": len(selected_features),
        "generated_at_utc": _utc_now(),
    }
    metadata = {
        "status": "PASS",
        "mode": "ic_first_scaffold",
        "symbol": symbol,
        "timeframe": tf,
        "source": source,
        "raw_rows": int(raw_frame.shape[0]),
        "raw_columns": int(raw_frame.shape[1]),
        "processed_columns": int(processed_frame.shape[1]),
        "raw_path": raw_path.name,
        "processed_path": processed_path.name,
        "selected_path": selected_path.name,
        "generated_at_utc": _utc_now(),
    }

    _atomic_write_parquet(raw_path, raw_frame.astype(np.float32, copy=False))
    _atomic_write_parquet(processed_path, processed_frame.astype(np.float32, copy=False))
    _atomic_write_json(selected_path, selected_payload)
    _atomic_write_json(metadata_path, metadata)
    if blocked_path.exists():
        blocked_path.unlink()
    logger.info(
        "[L6.5] Tier 2C IC-First scaffold written: %s/%s raw_cols=%d selected=%d",
        symbol,
        tf,
        raw_frame.shape[1],
        len(selected_features),
    )
    return metadata


def _remove_stale_real_artifacts(parquet_path: Path, d_star_path: Path) -> None:
    for artifact_path in (parquet_path, d_star_path, parquet_path.with_suffix(".manifest.json")):
        if artifact_path.exists():
            artifact_path.unlink()


def filter_l65_nodeids(nodeids: Iterable[str]) -> List[str]:
    return sorted({nodeid for nodeid in nodeids if L65_TEST_KEYWORDS.search(nodeid)})


def write_test_inventory_from_nodeids(nodeids: Iterable[str], out_path: Path = TEST_INVENTORY_PATH) -> int:
    filtered = filter_l65_nodeids(nodeids)
    if not filtered:
        _atomic_write_text(out_path, "BLOCKER: no L6.5/preprocessing tests collected\n")
        return 0
    _atomic_write_text(out_path, "\n".join(filtered) + "\n")
    return len(filtered)


def collect_existing_l65_tests(out_path: Path = TEST_INVENTORY_PATH) -> int:
    """Collect existing L6.5-related pytest nodeids into the golden inventory."""

    pytest_bin = PROJECT_ROOT / "venv" / "bin" / "pytest"
    if not pytest_bin.exists():
        message = "BLOCKER: pytest not found at ./venv/bin/pytest"
        _atomic_write_text(out_path, f"{message}\n")
        print(message)
        raise SystemExit(2)

    command = [str(pytest_bin), "--collect-only", "tests", "-q"]
    result = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        _atomic_write_text(out_path, result.stdout + result.stderr)
        raise GoldenBuildError(f"pytest collect-only failed with code {result.returncode}")

    nodeids = [line.strip() for line in result.stdout.splitlines() if "::" in line]
    if nodeids:
        count = write_test_inventory_from_nodeids(nodeids, out_path=out_path)
    elif out_path.exists():
        existing_lines = [
            line.strip()
            for line in out_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("BLOCKER")
        ]
        count = len(existing_lines)
    else:
        count = write_test_inventory_from_nodeids(nodeids, out_path=out_path)
    if count <= 0:
        raise GoldenBuildError("No L6.5/preprocessing pytest nodeids matched inventory filter")
    logger.info("[L6.5] Test inventory written: %d nodeids", count)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Layer 6.5 golden baseline artifacts")
    parser.add_argument("--tier", choices=["1", "2a", "2b", "3"], required=True)
    parser.add_argument("--mode", choices=["legacy", "ic_first"], default="legacy")
    parser.add_argument("--symbol", default="ETHUSDT")
    parser.add_argument("--tf", default="1h")
    parser.add_argument("--max-rows", type=int, default=2000)
    parser.add_argument("--max-cols", type=int, default=500)
    parser.add_argument("--out-dir", default=str(DEFAULT_GOLDEN_DIR))
    parser.add_argument("--collect-tests", action="store_true")
    args = parser.parse_args()

    try:
        golden_dir = Path(args.out_dir)
        if args.mode == "ic_first":
            if args.tier == "1":
                build_tier1_structure(golden_dir / "tier1_structure")
            elif args.tier == "2a":
                build_ic_first_golden(
                    symbol="SYNTHETIC",
                    tf="fixture",
                    max_rows=args.max_rows,
                    max_cols=args.max_cols,
                    out_dir=golden_dir / "tier2_icfirst",
                    use_real_data=False,
                )
            elif args.tier == "2b":
                build_ic_first_golden(
                    symbol=args.symbol,
                    tf=args.tf,
                    max_rows=args.max_rows,
                    max_cols=args.max_cols,
                    out_dir=golden_dir / "tier2_icfirst",
                    use_real_data=True,
                )
            elif args.tier == "3":
                raise SystemExit("Tier 3 不支援 8GB；需 24GB+ 環境")
        elif args.tier == "1":
            if not _ram_gate(
                MIN_REDUCED_WORKLOAD_GATE_GB,
                label="Tier 1 structure reduced workload",
            ):
                return 2
            build_tier1_structure(golden_dir / "tier1_structure")
        elif args.tier == "2a":
            tier2a_gate_gb = _estimate_reduced_workload_ram_gate(rows=1000, cols=100)
            if not _ram_gate(tier2a_gate_gb, label="Tier 2A synthetic reduced workload"):
                return 2
            build_tier2_synthetic(golden_dir / "tier2_reduced")
        elif args.tier == "2b":
            build_tier2_real_shortwindow(
                symbol=args.symbol,
                tf=args.tf,
                max_rows=args.max_rows,
                max_cols=args.max_cols,
                out_dir=golden_dir / "tier2_reduced",
            )
        elif args.tier == "3":
            raise SystemExit("Tier 3 不支援 8GB；需 24GB+ 環境")
        if args.collect_tests:
            collect_existing_l65_tests(golden_dir / "test_inventory.txt")
    except SystemExit:
        raise
    except Exception as exc:
        logger.error("[L6.5] Golden build failed: %s", exc, exc_info=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
