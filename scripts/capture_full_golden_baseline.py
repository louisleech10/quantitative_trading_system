import argparse
import hashlib
import json
import platform
import resource
import signal
import shutil
import threading
import time
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from momentum.factories import create_feature_factory
from momentum.FeatureEngineering.feature_reader import FeatureReader


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _sha256_file(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _series_checksum(series: pd.Series) -> str:
    arr = series.to_numpy(copy=False)
    contiguous = np.ascontiguousarray(arr)
    return _sha256_bytes(contiguous.tobytes())


def _overall_dataframe_checksum(df: pd.DataFrame) -> str:
    arr = np.ascontiguousarray(df.to_numpy(copy=False))
    return _sha256_bytes(arr.tobytes())


def _column_checksums(df: pd.DataFrame) -> Dict[str, str]:
    checksums: Dict[str, str] = {}
    for col in df.columns:
        checksums[str(col)] = _series_checksum(df[col])
    return checksums


def _config_digest(config_payload: Any) -> str:
    canonical = json.dumps(config_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256_text(canonical)


def _column_stats(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    stats: Dict[str, Dict[str, float]] = {}
    nan_ratio = df.isna().mean()
    means = df.mean(numeric_only=True)
    stds = df.std(numeric_only=True)
    mins = df.min(numeric_only=True)
    maxs = df.max(numeric_only=True)

    for col in df.columns:
        key = str(col)
        stats[key] = {
            "nan_ratio": float(nan_ratio.get(col, 0.0)),
            "mean": float(means.get(col, np.nan)),
            "std": float(stds.get(col, np.nan)),
            "min": float(mins.get(col, np.nan)),
            "max": float(maxs.get(col, np.nan)),
        }
    return stats


def _rss_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return float(value) / (1024.0 * 1024.0)
    return float(value) / 1024.0


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class StatusReporter:
    def __init__(self, status_file: Path, interval_seconds: float) -> None:
        self._status_file = status_file
        self._interval_seconds = max(1.0, float(interval_seconds))
        self._started_perf = time.perf_counter()
        self._started_utc = datetime.utcnow().isoformat() + "Z"
        self._heartbeat_count = 0
        self._current_stage: Optional[str] = None
        self._current_progress: Optional[float] = None
        self._current_message: Optional[str] = None
        self._state = "running"
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._write_snapshot()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop_event.wait(self._interval_seconds):
            self._heartbeat_count += 1
            snapshot = self._build_snapshot()
            print(
                "[status] state=%s stage=%s progress=%s elapsed=%.1fs hb=%d"
                % (
                    snapshot["state"],
                    snapshot.get("current_stage") or "-",
                    ("%.2f" % snapshot["current_progress"]) if snapshot.get("current_progress") is not None else "-",
                    snapshot["elapsed_seconds"],
                    snapshot["heartbeat_count"],
                )
            )
            self._write_snapshot(snapshot)

    def on_progress(self, payload: Dict[str, Any]) -> None:
        with self._lock:
            self._current_stage = str(payload.get("stage") or "") or None
            self._current_progress = float(payload.get("progress", 0.0))
            self._current_message = str(payload.get("message") or "") or None

    def finish(self, state: str, extra: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            self._state = state
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._write_snapshot(extra=extra)

    def _build_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "state": self._state,
                "started_at_utc": self._started_utc,
                "updated_at_utc": datetime.utcnow().isoformat() + "Z",
                "elapsed_seconds": float(time.perf_counter() - self._started_perf),
                "heartbeat_count": int(self._heartbeat_count),
                "current_stage": self._current_stage,
                "current_progress": self._current_progress,
                "current_message": self._current_message,
            }

    def _write_snapshot(self, snapshot: Optional[Dict[str, Any]] = None, extra: Optional[Dict[str, Any]] = None) -> None:
        payload = snapshot or self._build_snapshot()
        if extra:
            payload.update(extra)
        _write_json(self._status_file, payload)


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _resolve_meta_path(hdf5_path: Path, symbol: str, timeframe: str) -> Path:
    candidate = hdf5_path.parent / f"{symbol}_{timeframe}_factory_meta.json"
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture full golden baseline artifacts")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--timeframe", default="12h")
    parser.add_argument("--preset", default="full")
    parser.add_argument("--force-regenerate", action="store_true")
    parser.add_argument("--no-validate-continuity", action="store_true",
                        help="Skip kline data continuity validation")
    parser.add_argument("--baseline-root", default="results/full_golden_baseline")
    parser.add_argument(
        "--config-override-file",
        default="",
        help="Optional JSON file merged into {preset: ...} config_override",
    )
    parser.add_argument(
        "--status-interval-seconds",
        type=float,
        default=10.0,
        help="Heartbeat interval for status updates",
    )
    parser.add_argument(
        "--status-file",
        default="",
        help="Optional status file path (JSON). Defaults to <baseline_dir>/run_status.json",
    )
    args = parser.parse_args()

    baseline_root = Path(args.baseline_root)
    baseline_root.mkdir(parents=True, exist_ok=True)

    baseline_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ") + f"_{args.symbol}_{args.timeframe}_{args.preset}"
    baseline_dir = baseline_root / baseline_id
    artifacts_dir = baseline_dir / "artifacts"
    reports_dir = baseline_dir / "reports"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    status_path = Path(args.status_file) if args.status_file else (baseline_dir / "run_status.json")
    reporter = StatusReporter(status_file=status_path, interval_seconds=float(args.status_interval_seconds))

    def _signal_handler(signum: int, _frame: Any) -> None:
        reporter.finish(
            state="interrupted",
            extra={
                "reason": "signal",
                "signal": int(signum),
            },
        )
        raise SystemExit(130)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    reporter.start()

    factory = create_feature_factory(validate_continuity=not args.no_validate_continuity)

    config_override: Dict[str, Any] = {"preset": args.preset}
    if args.config_override_file:
        override_payload = _load_json(Path(args.config_override_file))
        if not isinstance(override_payload, dict):
            raise ValueError("--config-override-file must contain a JSON object")
        config_override = _deep_merge_dict(config_override, override_payload)

    tracemalloc.start()
    started_at = time.perf_counter()
    result = factory.generate_features(
        symbol=args.symbol,
        timeframe=args.timeframe,
        config_override=config_override,
        force_regenerate=args.force_regenerate,
        progress_callback=reporter.on_progress,
    )
    elapsed_seconds = float(time.perf_counter() - started_at)
    tracemalloc_current, tracemalloc_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    features_df = result.features_df.copy()
    labels_df = result.labels_df.copy()
    metadata = dict(result.metadata)
    config_used = dict(result.config_used)

    # CGSA mode: features_df is empty but features stored in per-group Parquet
    cgsa_mode = features_df.empty and result.feature_count > 0
    if cgsa_mode:
        config_hash = str(metadata.get("config_hash", ""))
        reader = FeatureReader("data_cache/features")
        frames: List[pd.DataFrame] = []
        for _group_name, group_df in reader.stream_groups(args.symbol, config_hash):
            frames.append(group_df)
        if frames:
            features_df = pd.concat(frames, axis=1)
        print(f"[CGSA] Loaded {features_df.shape[1]} features from per-group Parquet")

    # Copy source artifacts
    hdf5_path = Path(result.hdf5_path or "")
    copied_hdf5_path = artifacts_dir / "features_factory.h5"
    copied_meta_path = None

    if cgsa_mode:
        # In CGSA mode, hdf5_path points to CGSA manifest, not HDF5
        # Save a placeholder and copy the CGSA manifest instead
        copied_hdf5_path.write_bytes(b"")  # empty placeholder
        cgsa_manifest_src = hdf5_path
        if cgsa_manifest_src.exists():
            shutil.copy2(cgsa_manifest_src, artifacts_dir / "cgsa_manifest.json")
    else:
        if not hdf5_path.exists():
            raise FileNotFoundError(f"HDF5 output not found: {hdf5_path}")
        meta_path = _resolve_meta_path(hdf5_path, args.symbol, args.timeframe)
        shutil.copy2(hdf5_path, copied_hdf5_path)
        if meta_path.exists():
            copied_meta_path = artifacts_dir / "features_factory_meta.json"
            shutil.copy2(meta_path, copied_meta_path)

    feature_names = [str(col) for col in features_df.columns]
    label_names = [str(col) for col in labels_df.columns]
    layer_counts = dict(result.layer_counts)

    column_checksums = _column_checksums(features_df)
    overall_checksum = _overall_dataframe_checksum(features_df)
    labels_column_checksums = _column_checksums(labels_df)
    labels_overall_checksum = _overall_dataframe_checksum(labels_df)
    column_stats = _column_stats(features_df)
    config_used_sha256 = _config_digest(config_used)
    metadata_config_hash = str(metadata.get("config_hash", ""))

    feature_names_file = artifacts_dir / "feature_names.json"
    _write_json(feature_names_file, feature_names)

    label_names_file = artifacts_dir / "label_names.json"
    _write_json(label_names_file, label_names)

    checksums_file = artifacts_dir / "checksums.json"
    _write_json(
        checksums_file,
        {
            "overall_dataframe_sha256": overall_checksum,
            "labels_overall_dataframe_sha256": labels_overall_checksum,
            "hdf5_file_sha256": _sha256_file(copied_hdf5_path),
            "column_sha256": column_checksums,
            "labels_column_sha256": labels_column_checksums,
            "config_used_sha256": config_used_sha256,
            "config_hash": metadata_config_hash,
        },
    )

    stats_file = reports_dir / "column_stats.json"
    _write_json(stats_file, column_stats)

    metadata_file = artifacts_dir / "metadata_runtime.json"
    _write_json(metadata_file, metadata)

    config_file = artifacts_dir / "config_used.json"
    _write_json(config_file, config_used)

    manifest = {
        "baseline_id": baseline_id,
        "created_at_utc": datetime.utcnow().isoformat() + "Z",
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "preset": args.preset,
        "force_regenerate": bool(args.force_regenerate),
        "config_override_file": (str(args.config_override_file) if args.config_override_file else None),
        "artifacts": {
            "hdf5": str(copied_hdf5_path),
            "meta_json": str(copied_meta_path) if copied_meta_path else None,
            "feature_names": str(feature_names_file),
            "label_names": str(label_names_file),
            "checksums": str(checksums_file),
            "column_stats": str(stats_file),
            "metadata_runtime": str(metadata_file),
            "config_used": str(config_file),
        },
        "shape": {
            "rows": int(features_df.shape[0]),
            "columns": int(features_df.shape[1]),
        },
        "layer_counts": layer_counts,
        "performance": {
            "elapsed_seconds": elapsed_seconds,
            "tracemalloc_current_mb": float(tracemalloc_current / (1024.0 * 1024.0)),
            "tracemalloc_peak_mb": float(tracemalloc_peak / (1024.0 * 1024.0)),
            "ru_maxrss_mb": _rss_mb(),
            "generation_time_reported_by_factory": float(result.generation_time),
        },
        "checksums": {
            "overall_dataframe_sha256": overall_checksum,
            "labels_overall_dataframe_sha256": labels_overall_checksum,
            "hdf5_file_sha256": _sha256_file(copied_hdf5_path),
            "feature_name_count": len(feature_names),
            "label_name_count": len(label_names),
            "config_used_sha256": config_used_sha256,
            "config_hash": metadata_config_hash,
        },
    }

    manifest_path = baseline_dir / "manifest.json"
    _write_json(manifest_path, manifest)

    registry_path = baseline_root / "registry.json"
    registry = _load_json(registry_path)
    if not isinstance(registry, list):
        registry = []
    registry.append(
        {
            "baseline_id": baseline_id,
            "created_at_utc": manifest["created_at_utc"],
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "preset": args.preset,
            "manifest": str(manifest_path),
            "overall_dataframe_sha256": overall_checksum,
            "hdf5_file_sha256": manifest["checksums"]["hdf5_file_sha256"],
        }
    )
    _write_json(registry_path, registry)

    print(f"baseline_id={baseline_id}")
    print(f"manifest={manifest_path}")
    print(f"elapsed_seconds={elapsed_seconds:.4f}")
    reporter.finish(state="completed", extra={"manifest": str(manifest_path), "elapsed_seconds": float(elapsed_seconds)})


if __name__ == "__main__":
    main()
