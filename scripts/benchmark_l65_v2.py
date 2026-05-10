from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_KLINE_CACHE_PATH = PROJECT_ROOT / "data_cache" / "feature_klines" / "kline_cache.h5"
DEFAULT_FEATURES_ROOT = PROJECT_ROOT / "data_cache" / "features"

STATUS_PASS = "PASS"
STATUS_BLOCKED = "BLOCKED"
STATUS_FAIL = "FAIL"


class BenchmarkBlocked(RuntimeError):
    """Raised when a benchmark cannot run without substituting real market data."""


class PeakRssSampler:
    """Small RSS sampler for CLI benchmark summaries."""

    def __init__(self, interval_seconds: float = 0.05) -> None:
        self.interval_seconds = interval_seconds
        self._process = psutil.Process()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.peak_rss_mb = self._rss_mb()

    def __enter__(self) -> "PeakRssSampler":
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self.peak_rss_mb = max(self.peak_rss_mb, self._rss_mb())

    def _rss_mb(self) -> int:
        return int(round(self._process.memory_info().rss / float(1024**2)))

    def _sample(self) -> None:
        while not self._stop_event.is_set():
            self.peak_rss_mb = max(self.peak_rss_mb, self._rss_mb())
            time.sleep(self.interval_seconds)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_csv(raw: str) -> List[str]:
    values = [item.strip() for item in str(raw).split(",")]
    return [item for item in values if item]


def _available_ram_gb() -> float:
    return round(psutil.virtual_memory().available / float(1024**3), 4)


def _relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _scan_l7_sizes(features_root: Path) -> Dict[str, Any]:
    sizes = {
        "raw_bytes": 0,
        "processed_bytes": 0,
        "all_parquet_bytes": 0,
        "parquet_file_count": 0,
    }
    if not features_root.exists():
        return sizes

    for parquet_path in features_root.rglob("*.parquet"):
        file_size = parquet_path.stat().st_size
        parts = set(parquet_path.parts)
        sizes["all_parquet_bytes"] += file_size
        sizes["parquet_file_count"] += 1
        if "raw" in parts:
            sizes["raw_bytes"] += file_size
        if "processed" in parts:
            sizes["processed_bytes"] += file_size
    return sizes


def _streaming_schema_checks(features_root: Path) -> Dict[str, Any]:
    summary = {
        "streaming_checks_enabled": True,
        "group_count": 0,
        "schema_count": 0,
        "failed_group_count": 0,
        "checksum": "",
    }
    if not features_root.exists():
        summary["checksum"] = hashlib.sha256(b"").hexdigest()
        return summary

    hasher = hashlib.sha256()
    parquet_paths = sorted(features_root.rglob("*.parquet"))
    try:
        import pyarrow.parquet as pq
    except Exception:
        pq = None

    for parquet_path in parquet_paths:
        stat = parquet_path.stat()
        hasher.update(_relative_path(parquet_path).encode("utf-8"))
        hasher.update(str(stat.st_size).encode("ascii"))
        summary["group_count"] += 1
        if pq is None:
            continue
        try:
            metadata = pq.read_metadata(parquet_path)
            summary["schema_count"] += int(metadata.num_columns)
        except Exception:
            summary["failed_group_count"] += 1

    summary["checksum"] = hasher.hexdigest()
    return summary


def _validate_real_kline_data(
    symbols: List[str],
    timeframes: List[str],
    hdf5_path: Path,
    max_rows: int,
) -> Dict[str, Any]:
    if not hdf5_path.exists():
        raise BenchmarkBlocked(
            "blocked_missing_data: missing HDF5 cache "
            f"{_relative_path(hdf5_path)}"
        )

    try:
        import h5py
    except Exception as exc:
        raise BenchmarkBlocked("blocked_missing_data: h5py unavailable") from exc

    pairs: List[Dict[str, Any]] = []
    missing: List[str] = []
    with h5py.File(hdf5_path, "r") as h5_file:
        for symbol in symbols:
            for timeframe in timeframes:
                dataset_key = f"{symbol}/{timeframe}/data"
                if dataset_key not in h5_file:
                    missing.append(dataset_key)
                    continue
                dataset = h5_file[dataset_key]
                row_count = int(dataset.shape[0]) if dataset.shape else 0
                if row_count <= 0:
                    missing.append(dataset_key)
                    continue
                pairs.append(
                    {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "rows_available": row_count,
                        "rows_requested": min(row_count, max_rows),
                    }
                )

    if missing:
        raise BenchmarkBlocked(
            "blocked_missing_data: missing HDF5 dataset(s): " + ",".join(missing)
        )
    return {
        "pairs": pairs,
        "n_symbols": len(symbols),
        "n_timeframes": len(timeframes),
        "rows_per_item": min([item["rows_requested"] for item in pairs], default=0),
    }


def run_l65_v2_benchmark(args: Optional[argparse.Namespace] = None) -> Dict[str, Any]:
    """Run the V2 benchmark scaffold without fabricating market data."""

    parsed_args = args if args is not None else build_parser().parse_args()
    start = time.perf_counter()
    features_root = Path(parsed_args.features_root)
    hdf5_path = Path(parsed_args.hdf5_path)
    symbols = _parse_csv(parsed_args.symbols)
    timeframes = _parse_csv(parsed_args.tfs)

    result: Dict[str, Any] = {
        "schema_version": "l65-benchmark-v2-scaffold",
        "status": STATUS_PASS,
        "blocking_reason": "",
        "phase": str(parsed_args.phase),
        "tier": str(parsed_args.tier),
        "ic_first": bool(parsed_args.ic_first),
        "full_schema": bool(parsed_args.full_schema),
        "streaming_checks": bool(parsed_args.streaming_checks),
        "resume_check": bool(parsed_args.resume_check),
        "check_bss_roi": bool(parsed_args.check_bss_roi),
        "symbols": symbols,
        "timeframes": timeframes,
        "oom": False,
        "sigkill": False,
        "available_ram_gb": _available_ram_gb(),
        "peak_rss_mb": 0,
        "wall_time_seconds": 0.0,
        "l7_sizes": {},
        "schema_count": 0,
        "created_at": _utc_now(),
    }

    try:
        with PeakRssSampler() as sampler:
            data_summary = _validate_real_kline_data(
                symbols=symbols,
                timeframes=timeframes,
                hdf5_path=hdf5_path,
                max_rows=int(parsed_args.max_rows),
            )
            result.update(data_summary)
            result["l7_sizes"] = _scan_l7_sizes(features_root)
            if parsed_args.full_schema or parsed_args.streaming_checks:
                streaming_summary = _streaming_schema_checks(features_root)
                result.update(streaming_summary)
            else:
                result["schema_count"] = len(data_summary["pairs"])
            result["peak_rss_mb"] = sampler.peak_rss_mb
    except BenchmarkBlocked as exc:
        result["status"] = STATUS_BLOCKED
        result["blocking_reason"] = str(exc)
    except MemoryError as exc:
        result["status"] = STATUS_FAIL
        result["blocking_reason"] = str(exc)
        result["oom"] = True
    except Exception as exc:
        result["status"] = STATUS_FAIL
        result["blocking_reason"] = str(exc)

    result["available_ram_gb"] = _available_ram_gb()
    result["peak_rss_mb"] = max(
        int(result.get("peak_rss_mb") or 0),
        int(round(psutil.Process().memory_info().rss / float(1024**2))),
    )
    result["wall_time_seconds"] = round(time.perf_counter() - start, 6)
    return result


def _run_phase3_benchmark(
    tier: str = "8gb",
    dryrun: bool = True,
) -> Dict[str, Any]:
    """Phase 3 Task 3.1 benchmark scaffold: multi-symbol IC-First batch.

    In dryrun=True mode (default for CI / no-data environments) the function
    validates the scaffold structure and returns status='blocked_missing_data'
    without touching real HDF5 data.  Full execution (dryrun=False) requires
    real kline data and a running API service with FFACT_MULTI_SYMBOL_IC_FIRST=1.
    """
    result: Dict[str, Any] = {
        "schema_version": "l65-benchmark-v2-phase3-scaffold",
        "phase": "3",
        "tier": tier,
        "dryrun": dryrun,
        "status": "blocked_missing_data",
        "blocking_reason": "",
        "multi_symbol_ic_first_flag": "FFACT_MULTI_SYMBOL_IC_FIRST",
        "symbols_tested": [],
        "completed_count": 0,
        "failed_count": 0,
        "wall_time_seconds": 0.0,
        "created_at": _utc_now(),
    }

    if dryrun:
        result["blocking_reason"] = (
            "Phase 3 benchmark requires real kline data (HDF5) and a running API service "
            "with FFACT_MULTI_SYMBOL_IC_FIRST=1; skipped in dryrun mode."
        )
        return result

    # Full execution path (non-dryrun) — requires real environment
    start = time.perf_counter()
    try:
        import os

        if os.environ.get("FFACT_MULTI_SYMBOL_IC_FIRST", "0") not in {"1", "true", "yes"}:
            result["blocking_reason"] = (
                "FFACT_MULTI_SYMBOL_IC_FIRST is not enabled; "
                "set FFACT_MULTI_SYMBOL_IC_FIRST=1 before running phase=3 benchmark."
            )
            result["status"] = "blocked_missing_data"
            return result

        result["status"] = "PASS"
    except Exception as exc:
        result["status"] = "FAIL"
        result["blocking_reason"] = str(exc)
    finally:
        result["wall_time_seconds"] = round(time.perf_counter() - start, 6)

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Layer 6.5 V2 benchmark scaffold with real-data blocking checks"
    )
    parser.add_argument("--phase", default="0", choices=["0", "1", "2", "3"])
    parser.add_argument(
        "--tier",
        default="8gb",
        choices=["8gb", "16gb", "24gb", "32gb"],
    )
    parser.add_argument("--symbols", default="ETHUSDT")
    parser.add_argument("--tfs", default="1h")
    parser.add_argument("--max-rows", type=int, default=2000)
    parser.add_argument("--ic-first", action="store_true")
    parser.add_argument("--full-schema", action="store_true")
    parser.add_argument("--streaming-checks", action="store_true")
    parser.add_argument("--resume-check", action="store_true")
    parser.add_argument("--check-bss-roi", action="store_true")
    parser.add_argument("--hdf5-path", default=str(DEFAULT_KLINE_CACHE_PATH))
    parser.add_argument("--features-root", default=str(DEFAULT_FEATURES_ROOT))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.phase == "3":
        result = _run_phase3_benchmark(tier=args.tier, dryrun=True)
    else:
        result = run_l65_v2_benchmark(args)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] in {STATUS_PASS, "PASS"}:
        return 0
    if result["status"] in {STATUS_BLOCKED, "BLOCKED", "blocked_missing_data"}:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
