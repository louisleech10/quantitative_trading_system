import argparse
import gc
import hashlib
import json
import os
import platform
import resource
import signal
import statistics
import subprocess
import threading
import time
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from momentum.factories import create_feature_factory


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _series_checksum(series: pd.Series) -> str:
    arr = np.ascontiguousarray(series.to_numpy(copy=False))
    return _sha256_bytes(arr.tobytes())


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


def _rss_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return float(value) / (1024.0 * 1024.0)
    return float(value) / 1024.0


def _safe_loadavg() -> Optional[Dict[str, float]]:
    try:
        l1, l5, l15 = os.getloadavg()
        return {
            "1m": float(l1),
            "5m": float(l5),
            "15m": float(l15),
        }
    except Exception:
        return None


def _factory_output_paths(symbol: str, timeframe: str) -> Tuple[Path, Path]:
    base = Path("data_cache/features")
    h5_path = base / f"{symbol}_{timeframe}_factory.h5"
    meta_path = base / f"{symbol}_{timeframe}_factory_meta.json"
    return h5_path, meta_path


def _reset_factory_output_files(symbol: str, timeframe: str) -> Dict[str, Any]:
    h5_path, meta_path = _factory_output_paths(symbol, timeframe)
    deleted: List[str] = []
    missing: List[str] = []
    for path in [h5_path, meta_path]:
        if path.exists():
            path.unlink()
            deleted.append(str(path))
        else:
            missing.append(str(path))
    return {
        "deleted": deleted,
        "missing": missing,
    }


def _run_cache_drop_command(command: Optional[str]) -> Dict[str, Any]:
    cmd = (command or "").strip()
    if not cmd:
        return {
            "attempted": False,
            "command": None,
            "success": None,
            "return_code": None,
            "stdout": "",
            "stderr": "",
        }
    proc = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return {
        "attempted": True,
        "command": cmd,
        "success": proc.returncode == 0,
        "return_code": int(proc.returncode),
        "stdout": proc.stdout[-1000:],
        "stderr": proc.stderr[-1000:],
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


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
        self._run_index: Optional[int] = None
        self._run_total: Optional[int] = None
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
                "[status] state=%s run=%s/%s stage=%s progress=%s elapsed=%.1fs hb=%d"
                % (
                    snapshot["state"],
                    snapshot.get("run_index") if snapshot.get("run_index") is not None else "-",
                    snapshot.get("run_total") if snapshot.get("run_total") is not None else "-",
                    snapshot.get("current_stage") or "-",
                    ("%.2f" % snapshot["current_progress"]) if snapshot.get("current_progress") is not None else "-",
                    snapshot["elapsed_seconds"],
                    snapshot["heartbeat_count"],
                )
            )
            self._write_snapshot(snapshot)

    def update_run(self, run_index: int, run_total: int) -> None:
        with self._lock:
            self._run_index = int(run_index)
            self._run_total = int(run_total)
        self._write_snapshot()

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
                "run_index": self._run_index,
                "run_total": self._run_total,
                "current_stage": self._current_stage,
                "current_progress": self._current_progress,
                "current_message": self._current_message,
            }

    def _write_snapshot(self, snapshot: Optional[Dict[str, Any]] = None, extra: Optional[Dict[str, Any]] = None) -> None:
        payload = snapshot or self._build_snapshot()
        if extra:
            payload.update(extra)
        _write_json(self._status_file, payload)


def _compare_feature_names(current: List[str], baseline: List[str]) -> Tuple[bool, Dict[str, Any]]:
    same_order = current == baseline
    current_set = set(current)
    baseline_set = set(baseline)
    only_current = sorted(current_set - baseline_set)
    only_baseline = sorted(baseline_set - current_set)

    return (
        same_order and not only_current and not only_baseline,
        {
            "same_order": same_order,
            "only_in_current_count": len(only_current),
            "only_in_baseline_count": len(only_baseline),
            "only_in_current_sample": only_current[:20],
            "only_in_baseline_sample": only_baseline[:20],
        },
    )


def _compare_column_checksums(current: Dict[str, str], baseline: Dict[str, str]) -> Tuple[bool, Dict[str, Any]]:
    mismatched = []
    for col, checksum in baseline.items():
        if current.get(col) != checksum:
            mismatched.append(col)

    extra = [col for col in current if col not in baseline]
    missing = [col for col in baseline if col not in current]

    ok = (len(mismatched) == 0) and (len(extra) == 0) and (len(missing) == 0)
    return ok, {
        "mismatched_count": len(mismatched),
        "extra_count": len(extra),
        "missing_count": len(missing),
        "mismatched_sample": mismatched[:20],
        "extra_sample": extra[:20],
        "missing_sample": missing[:20],
    }


def _build_stage_timing_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    stage_bounds: Dict[str, Dict[str, Any]] = {}
    ordered_stage_names: List[str] = []

    for event in events:
        stage = str(event.get("stage") or "")
        if not stage:
            continue

        if stage not in stage_bounds:
            stage_bounds[stage] = {
                "stage": stage,
                "start_perf": None,
                "end_perf": None,
                "start_utc": None,
                "end_utc": None,
                "start_message": None,
                "end_message": None,
            }
            ordered_stage_names.append(stage)

        progress = float(event.get("progress", 0.0))
        bucket = stage_bounds[stage]
        if progress <= 0.0 and bucket["start_perf"] is None:
            bucket["start_perf"] = float(event["perf_ts"])
            bucket["start_utc"] = event["utc"]
            bucket["start_message"] = event.get("message")

        if progress >= 1.0:
            bucket["end_perf"] = float(event["perf_ts"])
            bucket["end_utc"] = event["utc"]
            bucket["end_message"] = event.get("message")

    stages: List[Dict[str, Any]] = []
    for name in ordered_stage_names:
        bucket = stage_bounds[name]
        duration_seconds = None
        if bucket["start_perf"] is not None and bucket["end_perf"] is not None:
            duration_seconds = float(bucket["end_perf"] - bucket["start_perf"])
        stages.append(
            {
                "stage": name,
                "start_utc": bucket["start_utc"],
                "end_utc": bucket["end_utc"],
                "duration_seconds": duration_seconds,
                "start_message": bucket["start_message"],
                "end_message": bucket["end_message"],
            }
        )

    completed = [item for item in stages if item.get("duration_seconds") is not None]
    longest = max(completed, key=lambda x: float(x["duration_seconds"])) if completed else None

    return {
        "event_count": len(events),
        "stages": stages,
        "longest_stage": longest,
    }


def _run_generation_once(
    factory: Any,
    symbol: str,
    timeframe: str,
    preset: str,
    config_override: Dict[str, Any],
    force_regenerate: bool,
    status_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    progress_events: List[Dict[str, Any]] = []

    def _progress_callback(payload: Dict[str, Any]) -> None:
        if status_callback:
            status_callback(payload)
        progress_events.append(
            {
                "utc": datetime.utcnow().isoformat() + "Z",
                "perf_ts": float(time.perf_counter()),
                "stage": payload.get("stage"),
                "progress": float(payload.get("progress", 0.0)),
                "message": payload.get("message"),
            }
        )

    tracemalloc.start()
    started_at = time.perf_counter()
    result = factory.generate_features(
        symbol=symbol,
        timeframe=timeframe,
        config_override=config_override,
        force_regenerate=force_regenerate,
        progress_callback=_progress_callback,
    )
    elapsed_seconds = float(time.perf_counter() - started_at)
    tracemalloc_current, tracemalloc_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "result": result,
        "elapsed_seconds": elapsed_seconds,
        "tracemalloc_current_mb": float(tracemalloc_current / (1024.0 * 1024.0)),
        "tracemalloc_peak_mb": float(tracemalloc_peak / (1024.0 * 1024.0)),
        "ru_maxrss_mb": _rss_mb(),
        "generation_time_reported_by_factory": float(result.generation_time),
        "stage_timing_summary": _build_stage_timing_summary(progress_events),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare current run with full golden baseline")
    parser.add_argument("--manifest", required=True, help="Path to baseline manifest.json")
    parser.add_argument("--force-regenerate", action="store_true")
    parser.add_argument("--output", default="results/full_golden_baseline/latest_compare_report.json")
    parser.add_argument(
        "--config-override-file",
        default="",
        help="Optional JSON file merged into {preset: ...} config_override",
    )
    parser.add_argument(
        "--perf-runs",
        type=int,
        default=1,
        help="Number of reruns for performance metric (median is used)",
    )
    parser.add_argument(
        "--max-slowdown-ratio",
        type=float,
        default=0.05,
        help="Allowed slowdown ratio for performance gate in maintain mode (default: 5%)",
    )
    parser.add_argument(
        "--require-speedup",
        action="store_true",
        help="Use strict mode: current runtime must be faster than baseline",
    )
    parser.add_argument(
        "--min-speedup-ratio",
        type=float,
        default=0.10,
        help="Minimum required speedup ratio in speedup mode (default: 0.10 means 10%)",
    )
    parser.add_argument(
        "--performance-metric",
        choices=["elapsed", "factory"],
        default="elapsed",
        help="Metric used in performance gate",
    )
    parser.add_argument(
        "--inter-run-wait-seconds",
        type=float,
        default=0.0,
        help="Sleep between perf runs to sample different execution periods",
    )
    parser.add_argument(
        "--cache-drop-command",
        default="",
        help="Optional system command to drop OS cache before each run (best effort)",
    )
    parser.add_argument(
        "--no-reset-factory-output",
        action="store_true",
        help="Do not delete data_cache/features/{symbol}_{timeframe}_factory outputs before each run",
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
        help="Optional status file path (JSON). Defaults to <output>.status.json",
    )
    args = parser.parse_args()

    if args.perf_runs < 1:
        raise ValueError("--perf-runs must be >= 1")
    if args.min_speedup_ratio < 0:
        raise ValueError("--min-speedup-ratio must be >= 0")
    if args.min_speedup_ratio >= 1:
        raise ValueError("--min-speedup-ratio must be < 1")
    if args.inter_run_wait_seconds < 0:
        raise ValueError("--inter-run-wait-seconds must be >= 0")

    manifest_path = Path(args.manifest)
    manifest = _load_json(manifest_path)
    output_path = Path(args.output)
    status_path = Path(args.status_file) if args.status_file else output_path.with_suffix(output_path.suffix + ".status.json")
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

    symbol = manifest["symbol"]
    timeframe = manifest["timeframe"]
    preset = manifest["preset"]
    config_override: Dict[str, Any] = {"preset": preset}
    if args.config_override_file:
        override_payload = _load_json(Path(args.config_override_file))
        if not isinstance(override_payload, dict):
            raise ValueError("--config-override-file must contain a JSON object")
        config_override = _deep_merge_dict(config_override, override_payload)

    baseline_feature_names = _load_json(Path(manifest["artifacts"]["feature_names"]))
    baseline_checksums = _load_json(Path(manifest["artifacts"]["checksums"]))
    baseline_label_names = []
    label_names_path = manifest.get("artifacts", {}).get("label_names")
    if label_names_path:
        baseline_label_names = _load_json(Path(label_names_path))

    baseline_config_digest = baseline_checksums.get("config_used_sha256")
    baseline_config_hash = baseline_checksums.get("config_hash")
    baseline_config_path = manifest.get("artifacts", {}).get("config_used")
    if (not baseline_config_digest) and baseline_config_path:
        baseline_config_digest = _config_digest(_load_json(Path(baseline_config_path)))

    run_records: List[Dict[str, Any]] = []
    for run_idx in range(args.perf_runs):
        reporter.update_run(run_index=run_idx + 1, run_total=int(args.perf_runs))
        reset_info = {"deleted": [], "missing": []}
        if not args.no_reset_factory_output:
            reset_info = _reset_factory_output_files(symbol, timeframe)

        cache_drop_info = _run_cache_drop_command(args.cache_drop_command)

        gc.collect()
        factory = create_feature_factory()
        run_started_at_utc = datetime.utcnow().isoformat() + "Z"
        record = _run_generation_once(
            factory=factory,
            symbol=symbol,
            timeframe=timeframe,
            preset=preset,
            config_override=config_override,
            force_regenerate=args.force_regenerate,
            status_callback=reporter.on_progress,
        )
        record["run_index"] = run_idx + 1
        record["run_started_at_utc"] = run_started_at_utc
        record["loadavg_before_run"] = _safe_loadavg()
        record["factory_output_reset"] = reset_info
        record["cache_drop"] = cache_drop_info
        run_records.append(record)

        if run_idx < args.perf_runs - 1 and args.inter_run_wait_seconds > 0:
            time.sleep(float(args.inter_run_wait_seconds))

    first_run = run_records[0]
    result = first_run["result"]

    calc_timers: Dict[str, float] = {}

    df = result.features_df.copy()
    labels_df = result.labels_df.copy()
    current_feature_names = [str(col) for col in df.columns]
    current_label_names = [str(col) for col in labels_df.columns]
    current_overall_checksum = _overall_dataframe_checksum(df)
    current_column_checksums = _column_checksums(df)
    current_labels_overall_checksum = _overall_dataframe_checksum(labels_df)
    current_labels_column_checksums = _column_checksums(labels_df)

    _t0 = time.perf_counter()
    feature_name_ok, feature_name_report = _compare_feature_names(current_feature_names, baseline_feature_names)
    calc_timers["feature_name_compare_seconds"] = float(time.perf_counter() - _t0)

    _t0 = time.perf_counter()
    checksum_ok, checksum_report = _compare_column_checksums(
        current=current_column_checksums,
        baseline=baseline_checksums.get("column_sha256", {}),
    )
    calc_timers["feature_column_checksum_compare_seconds"] = float(time.perf_counter() - _t0)

    label_name_ok = True
    label_name_report: Dict[str, Any] = {
        "evaluated": bool(baseline_label_names),
        "same_order": True,
        "only_in_current_count": 0,
        "only_in_baseline_count": 0,
        "only_in_current_sample": [],
        "only_in_baseline_sample": [],
    }
    if baseline_label_names:
        _t0 = time.perf_counter()
        label_name_ok, label_name_report = _compare_feature_names(current_label_names, baseline_label_names)
        calc_timers["label_name_compare_seconds"] = float(time.perf_counter() - _t0)

    baseline_labels_column = baseline_checksums.get("labels_column_sha256")
    label_checksum_ok = True
    label_checksum_report: Dict[str, Any] = {
        "evaluated": bool(baseline_labels_column),
        "mismatched_count": 0,
        "extra_count": 0,
        "missing_count": 0,
        "mismatched_sample": [],
        "extra_sample": [],
        "missing_sample": [],
    }
    if baseline_labels_column:
        _t0 = time.perf_counter()
        label_checksum_ok, label_checksum_report = _compare_column_checksums(
            current=current_labels_column_checksums,
            baseline=baseline_labels_column,
        )
        calc_timers["label_column_checksum_compare_seconds"] = float(time.perf_counter() - _t0)

    _t0 = time.perf_counter()
    overall_checksum_ok = current_overall_checksum == baseline_checksums.get("overall_dataframe_sha256")
    labels_overall_checksum_ok = (
        current_labels_overall_checksum == baseline_checksums.get("labels_overall_dataframe_sha256")
        if baseline_checksums.get("labels_overall_dataframe_sha256")
        else True
    )
    calc_timers["overall_checksum_gate_seconds"] = float(time.perf_counter() - _t0)

    current_config_digest = _config_digest(result.config_used)
    current_config_hash = str(result.metadata.get("config_hash", "")) if isinstance(result.metadata, dict) else ""
    _t0 = time.perf_counter()
    config_digest_ok = True if not baseline_config_digest else (current_config_digest == baseline_config_digest)
    config_hash_ok = True if not baseline_config_hash else (current_config_hash == baseline_config_hash)
    config_ok = config_digest_ok and config_hash_ok
    calc_timers["config_gate_seconds"] = float(time.perf_counter() - _t0)

    elapsed_samples = [float(item["elapsed_seconds"]) for item in run_records]
    factory_samples = [float(item["generation_time_reported_by_factory"]) for item in run_records]
    current_perf_elapsed_median = float(statistics.median(elapsed_samples))
    current_perf_factory_median = float(statistics.median(factory_samples))

    baseline_elapsed = float(manifest.get("performance", {}).get("elapsed_seconds", float("inf")))
    baseline_factory = float(
        manifest.get("performance", {}).get("generation_time_reported_by_factory", float("inf"))
    )

    _t0 = time.perf_counter()
    if args.performance_metric == "factory":
        baseline_metric = baseline_factory
        current_metric = current_perf_factory_median
    else:
        baseline_metric = baseline_elapsed
        current_metric = current_perf_elapsed_median

    if args.require_speedup:
        required_threshold = baseline_metric * (1.0 - float(args.min_speedup_ratio))
        performance_ok = current_metric <= required_threshold
        perf_mode = "speedup"
    else:
        performance_ok = current_metric <= baseline_metric * (1.0 + float(args.max_slowdown_ratio))
        perf_mode = "maintain"
    calc_timers["performance_gate_seconds"] = float(time.perf_counter() - _t0)

    shape_ok = (
        int(df.shape[0]) == int(manifest.get("shape", {}).get("rows", -1))
        and int(df.shape[1]) == int(manifest.get("shape", {}).get("columns", -1))
    )

    labels_shape_ok = True
    baseline_label_count = manifest.get("checksums", {}).get("label_name_count")
    if baseline_label_count is not None:
        labels_shape_ok = int(labels_df.shape[1]) == int(baseline_label_count)

    quality_gates_passed = bool(
        feature_name_ok
        and checksum_ok
        and overall_checksum_ok
        and shape_ok
        and label_name_ok
        and label_checksum_ok
        and labels_overall_checksum_ok
        and labels_shape_ok
        and config_ok
    )
    all_gates_passed = bool(quality_gates_passed and performance_ok)

    calc_timers_sorted = sorted(calc_timers.items(), key=lambda item: item[1], reverse=True)

    report = {
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "manifest": str(manifest_path),
        "target": {
            "symbol": symbol,
            "timeframe": timeframe,
            "preset": preset,
        },
        "current": {
            "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
            "labels_shape": {"rows": int(labels_df.shape[0]), "columns": int(labels_df.shape[1])},
            "overall_dataframe_sha256": current_overall_checksum,
            "labels_overall_dataframe_sha256": current_labels_overall_checksum,
            "performance": {
                "samples": {
                    "elapsed_seconds": elapsed_samples,
                    "generation_time_reported_by_factory": factory_samples,
                },
                "run_details": [
                    {
                        "run_index": int(item.get("run_index", idx + 1)),
                        "run_started_at_utc": item.get("run_started_at_utc"),
                        "elapsed_seconds": float(item["elapsed_seconds"]),
                        "generation_time_reported_by_factory": float(item["generation_time_reported_by_factory"]),
                        "tracemalloc_current_mb": float(item["tracemalloc_current_mb"]),
                        "tracemalloc_peak_mb": float(item["tracemalloc_peak_mb"]),
                        "ru_maxrss_mb": float(item["ru_maxrss_mb"]),
                        "loadavg_before_run": item.get("loadavg_before_run"),
                        "factory_output_reset": item.get("factory_output_reset"),
                        "cache_drop": item.get("cache_drop"),
                        "stage_timing_summary": item.get("stage_timing_summary"),
                    }
                    for idx, item in enumerate(run_records)
                ],
                "elapsed_seconds_median": current_perf_elapsed_median,
                "generation_time_reported_by_factory_median": current_perf_factory_median,
                "tracemalloc_current_mb": float(first_run["tracemalloc_current_mb"]),
                "tracemalloc_peak_mb": float(first_run["tracemalloc_peak_mb"]),
                "ru_maxrss_mb": float(first_run["ru_maxrss_mb"]),
            },
            "config_used_sha256": current_config_digest,
            "config_hash": current_config_hash,
        },
        "baseline": {
            "shape": manifest.get("shape", {}),
            "overall_dataframe_sha256": baseline_checksums.get("overall_dataframe_sha256"),
            "labels_overall_dataframe_sha256": baseline_checksums.get("labels_overall_dataframe_sha256"),
            "elapsed_seconds": baseline_elapsed,
            "generation_time_reported_by_factory": baseline_factory,
            "config_used_sha256": baseline_config_digest,
            "config_hash": baseline_config_hash,
        },
        "comparison": {
            "feature_names": feature_name_report,
            "column_checksums": checksum_report,
            "label_names": label_name_report,
            "label_column_checksums": label_checksum_report,
            "overall_checksum_ok": overall_checksum_ok,
            "labels_overall_checksum_ok": labels_overall_checksum_ok,
            "shape_ok": shape_ok,
            "labels_shape_ok": labels_shape_ok,
            "config_ok": config_ok,
            "config_digest_ok": config_digest_ok,
            "config_hash_ok": config_hash_ok,
            "performance": {
                "mode": perf_mode,
                "metric": args.performance_metric,
                "perf_runs": int(args.perf_runs),
                "inter_run_wait_seconds": float(args.inter_run_wait_seconds),
                "factory_output_reset_enabled": (not args.no_reset_factory_output),
                "cache_drop_command": (args.cache_drop_command.strip() or None),
                "baseline_metric_value": baseline_metric,
                "current_metric_value": current_metric,
                "delta_seconds": current_metric - baseline_metric,
                "delta_ratio": (
                    (current_metric - baseline_metric) / baseline_metric
                    if baseline_metric > 0
                    else 0.0
                ),
                "max_slowdown_ratio": float(args.max_slowdown_ratio),
                "require_speedup": bool(args.require_speedup),
                "min_speedup_ratio": float(args.min_speedup_ratio),
                "required_threshold": (
                    baseline_metric * (1.0 - float(args.min_speedup_ratio))
                    if args.require_speedup
                    else None
                ),
                "ok": performance_ok,
            },
            "calculation_timings_seconds": {
                "steps": {k: float(v) for k, v in calc_timers.items()},
                "sorted_desc": [
                    {"step": name, "seconds": float(value)}
                    for name, value in calc_timers_sorted
                ],
                "slowest_step": (
                    {
                        "step": calc_timers_sorted[0][0],
                        "seconds": float(calc_timers_sorted[0][1]),
                    }
                    if calc_timers_sorted
                    else None
                ),
            },
        },
        "gates": {
            "feature_name_gate": feature_name_ok,
            "checksum_gate": checksum_ok,
            "overall_checksum_gate": overall_checksum_ok,
            "shape_gate": shape_ok,
            "label_name_gate": label_name_ok,
            "label_checksum_gate": label_checksum_ok,
            "label_overall_checksum_gate": labels_overall_checksum_ok,
            "labels_shape_gate": labels_shape_ok,
            "config_gate": config_ok,
            "performance_gate": performance_ok,
            "quality_gates_passed": quality_gates_passed,
            "all_passed": all_gates_passed,
        },
    }

    _write_json(output_path, report)

    print(f"report={output_path}")
    print(f"all_passed={all_gates_passed}")

    if not all_gates_passed:
        reporter.finish(state="failed", extra={"report": str(output_path), "all_passed": bool(all_gates_passed)})
        raise SystemExit(2)

    reporter.finish(state="completed", extra={"report": str(output_path), "all_passed": bool(all_gates_passed)})


if __name__ == "__main__":
    main()
