#!/usr/bin/env python3
"""Layer 6.5 benchmark suite.

Task 0.8 introduced the Phase 0 development-gate harness. Task 3.1 extends
the same entry point into a cross-tier, cross-phase benchmark suite while
keeping the original gate modes stable for regression checks.
"""

from __future__ import annotations

import argparse
import copy
import gc
import json
import os
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _ensure_project_venv() -> None:
    venv_python = PROJECT_ROOT / "venv" / "bin" / "python"
    if not venv_python.exists():
        return
    try:
        current_python = Path(sys.executable).absolute()
        target_python = venv_python.absolute()
    except OSError:
        return
    if current_python == target_python:
        return
    os.execv(str(target_python), [str(target_python), str(Path(__file__).resolve())] + sys.argv[1:])


if Path(sys.argv[0]).resolve() == Path(__file__).resolve():
    _ensure_project_venv()

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import psutil  # noqa: E402

from momentum.FeatureEngineering.preprocessing._d_star_cache import (  # noqa: E402
    PreprocessingContext,
    compute_data_fingerprint,
    compute_feature_schema_hash,
    stable_json,
)
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor  # noqa: E402
from momentum.FeatureEngineering.utils.hardware_utils import get_tier_concurrent_symbols  # noqa: E402
from momentum.core.logging import get_logger  # noqa: E402
from scripts.build_l65_golden import (  # noqa: E402
    DEFAULT_GOLDEN_DIR,
    KLINE_CACHE_PATH,
    _atomic_write_json,
    _atomic_write_parquet,
    _build_l1_l2_real_features,
    _l65_full_preprocessing_config,
    _load_hdf5_kline_frame,
    make_synthetic_l65_dataset,
)

logger = get_logger(__name__)

BYTES_PER_MB = 1024 ** 2
RESULT_DIR = PROJECT_ROOT / "benchmark_results" / "l65"
OUTPUT_DIR = RESULT_DIR / "outputs"
CHECKPOINT_DIR = RESULT_DIR / "checkpoints"
DSTAR_CACHE_DIR = PROJECT_ROOT / "data_cache" / "feature_preprocessing"
PHASE0_WALL_LIMIT_SECONDS = 60 * 60
PHASE0_CACHE_HIT_WALL_LIMIT_SECONDS = 10 * 60
PHASE0_SYNTHETIC_WALL_LIMIT_SECONDS = 5 * 60
PHASE1_WALL_LIMIT_SECONDS = 30 * 60
PHASE1_CACHE_HIT_WALL_LIMIT_SECONDS = 5 * 60
PHASE2_WALL_LIMIT_SECONDS = 15 * 60
PHASE0_RSS_LIMIT_MB = 6 * 1024
MULTI_RSS_CUMULATIVE_LIMIT_MB = 1536
RAM_GATE_MIN_AVAILABLE_GB = 4.0
DSTAR_JSON_LIMIT_BYTES = 5 * 1024 * 1024
REGRESSION_LOOKBACK_DAYS = 7
REGRESSION_DEGRADATION_THRESHOLD = 0.20
SUITE_SCHEMA_VERSION = "l65-benchmark-suite-v1"
SMOKE_TIERS = ("8gb", "16gb", "24gb", "32gb")
SMOKE_PHASES = ("0", "1", "2")
SMOKE_DEFAULT_ROWS = 1000
SMOKE_DEFAULT_COLS = 100
FULL_WIDTH_PROXY_MIN_ROWS = 5000
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_BLOCKED = "BLOCKED"


class BenchmarkBlocked(RuntimeError):
    """Raised when a benchmark cannot run because required real data is absent."""


@dataclass
class SingleRunResult:
    gate_id: str
    status: str
    symbol: str
    timeframe: str
    repeat_index: int
    wall_time_seconds: float
    rss_before_mb: int
    peak_rss_mb: int
    rss_after_gc_mb: int
    rows_per_item: int
    input_columns: int
    output_columns: int
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: Optional[float] = None
    output_path: Optional[str] = None
    baseline_path: Optional[str] = None
    dstar_cache_path: Optional[str] = None
    dstar_json_size_bytes: Optional[int] = None
    output_size_delta_pct: Optional[float] = None
    memory_sanity_failed: bool = False
    oom: bool = False
    sigkill: bool = False
    blocking_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "status": self.status,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "repeat_index": self.repeat_index,
            "wall_time_seconds": round(self.wall_time_seconds, 6),
            "rss_before_mb": self.rss_before_mb,
            "peak_rss_mb": self.peak_rss_mb,
            "rss_after_gc_mb": self.rss_after_gc_mb,
            "rows_per_item": self.rows_per_item,
            "input_columns": self.input_columns,
            "output_columns": self.output_columns,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hit_rate,
            "output_path": self.output_path,
            "baseline_path": self.baseline_path,
            "dstar_cache_path": self.dstar_cache_path,
            "dstar_json_size_bytes": self.dstar_json_size_bytes,
            "output_size_delta_pct": self.output_size_delta_pct,
            "memory_sanity_failed": self.memory_sanity_failed,
            "oom": self.oom,
            "sigkill": self.sigkill,
            "blocking_reason": self.blocking_reason,
        }


@dataclass
class BenchmarkSummary:
    gate_id: str
    status: str
    phase: int
    tier_gb: int
    timestamp: str
    wall_time_seconds: float = 0.0
    peak_rss_mb: int = 0
    cache_hit_rate: Optional[float] = None
    n_symbols: int = 0
    n_timeframes: int = 0
    rows_per_item: int = 0
    memory_sanity_failed: bool = False
    oom: bool = False
    sigkill: bool = False
    output_size_delta_pct: Optional[float] = None
    l7_size_mb: Optional[float] = None
    blocking_reason: str = ""
    concurrent_symbols: int = 1
    checkpoint_path: Optional[str] = None
    regression_flag: bool = False
    regression_reasons: List[str] = field(default_factory=list)
    history_sample_count: int = 0
    tier_simulation: Dict[str, Any] = field(default_factory=dict)
    entries: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SUITE_SCHEMA_VERSION,
            "gate_id": self.gate_id,
            "status": self.status,
            "phase": self.phase,
            "tier_gb": self.tier_gb,
            "timestamp": self.timestamp,
            "wall_time_seconds": round(self.wall_time_seconds, 6),
            "peak_rss_mb": self.peak_rss_mb,
            "cache_hit_rate": self.cache_hit_rate,
            "n_symbols": self.n_symbols,
            "n_timeframes": self.n_timeframes,
            "rows_per_item": self.rows_per_item,
            "memory_sanity_failed": self.memory_sanity_failed,
            "oom": self.oom,
            "sigkill": self.sigkill,
            "output_size_delta_pct": self.output_size_delta_pct,
            "l7_size_mb": self.l7_size_mb,
            "blocking_reason": self.blocking_reason,
            "concurrent_symbols": self.concurrent_symbols,
            "checkpoint_path": self.checkpoint_path,
            "regression_flag": self.regression_flag,
            "regression_reasons": self.regression_reasons,
            "history_sample_count": self.history_sample_count,
            "tier_simulation": self.tier_simulation,
            "entries": self.entries,
        }


class PeakRssSampler:
    """Small RSS sampler for single-process benchmark runs."""

    def __init__(self, interval_seconds: float = 0.05) -> None:
        self._process = psutil.Process()
        self._interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._peak_rss = int(self._process.memory_info().rss)

    def __enter__(self) -> "PeakRssSampler":
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._peak_rss = max(self._peak_rss, int(self._process.memory_info().rss))

    @property
    def peak_rss_mb(self) -> int:
        return int(self._peak_rss // BYTES_PER_MB)

    def _sample_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._peak_rss = max(self._peak_rss, int(self._process.memory_info().rss))
            except psutil.Error:
                return
            self._stop_event.wait(self._interval_seconds)


@contextmanager
def _temporary_env(overrides: Dict[str, str]) -> Iterator[None]:
    previous: Dict[str, Optional[str]] = {key: os.environ.get(key) for key in overrides}
    os.environ.update(overrides)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_tier_gb(raw: str) -> int:
    try:
        return int(str(raw).strip().lower().replace("gb", ""))
    except ValueError:
        return 8


def _safe_int(raw: object, default: int) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _parse_csv(raw: str) -> List[str]:
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def _parse_timestamp(raw: object) -> Optional[datetime]:
    if not raw:
        return None
    text = str(raw)
    formats = ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S%fZ")
    for date_format in formats:
        try:
            return datetime.strptime(text, date_format).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@contextmanager
def _tier_memory_limit(tier_gb: int, enabled: bool = True) -> Iterator[Dict[str, Any]]:
    simulation = {
        "enabled": False,
        "requested_tier_gb": int(tier_gb),
        "status": "skipped",
        "reason": "tier simulation disabled",
    }
    if not enabled:
        yield simulation
        return

    try:
        import resource
    except ImportError:
        simulation["reason"] = "resource module unavailable"
        logger.warning("[L6.5] tier simulation skipped: resource module unavailable")
        yield simulation
        return

    if not hasattr(resource, "RLIMIT_AS"):
        simulation["reason"] = "RLIMIT_AS unavailable"
        logger.warning("[L6.5] tier simulation skipped: RLIMIT_AS unavailable")
        yield simulation
        return

    target_bytes = int(tier_gb) * 1024 ** 3
    try:
        current_vms = int(psutil.Process().memory_info().vms)
    except psutil.Error:
        current_vms = 0
    if current_vms and current_vms >= int(target_bytes * 0.90):
        simulation["reason"] = "current process VMS is too close to requested tier limit"
        simulation["current_vms_bytes"] = current_vms
        logger.warning("[L6.5] tier simulation skipped: %s", simulation["reason"])
        yield simulation
        return

    try:
        previous_soft, previous_hard = resource.getrlimit(resource.RLIMIT_AS)
    except (OSError, ValueError) as exc:
        simulation["reason"] = "getrlimit failed: %s" % exc
        logger.warning("[L6.5] tier simulation skipped: %s", simulation["reason"])
        yield simulation
        return

    if previous_hard != resource.RLIM_INFINITY and target_bytes > previous_hard:
        simulation["reason"] = "requested limit exceeds hard limit"
        logger.warning("[L6.5] tier simulation skipped: %s", simulation["reason"])
        yield simulation
        return

    try:
        resource.setrlimit(resource.RLIMIT_AS, (target_bytes, previous_hard))
        simulation.update({
            "enabled": True,
            "status": "applied",
            "reason": "",
            "soft_limit_bytes": target_bytes,
        })
        yield simulation
    except (OSError, ValueError) as exc:
        simulation["reason"] = "setrlimit failed: %s" % exc
        logger.warning("[L6.5] tier simulation failed: %s", simulation["reason"])
        yield simulation
    finally:
        if simulation.get("enabled"):
            try:
                resource.setrlimit(resource.RLIMIT_AS, (previous_soft, previous_hard))
            except (OSError, ValueError) as exc:
                logger.warning("[L6.5] tier simulation restore failed: %s", exc)


def _available_symbols_for_timeframes(timeframes: Sequence[str]) -> List[str]:
    if not KLINE_CACHE_PATH.exists():
        return []

    import h5py

    available: List[str] = []
    with h5py.File(KLINE_CACHE_PATH, "r") as h5_file:
        for symbol in sorted(key for key in h5_file.keys() if not str(key).startswith("_")):
            if all(f"{symbol}/{timeframe}/data" in h5_file for timeframe in timeframes):
                available.append(str(symbol))
    return available


def _resolve_symbols(raw_symbols: str, timeframes: Sequence[str]) -> List[str]:
    raw_symbols = str(raw_symbols).strip()
    if raw_symbols.isdigit():
        requested = int(raw_symbols)
        available = _available_symbols_for_timeframes(timeframes)
        if len(available) < requested:
            raise BenchmarkBlocked(
                "requested real symbols=%d with timeframes=%s, but only %d available in %s: %s"
                % (
                    requested,
                    ",".join(timeframes),
                    len(available),
                    KLINE_CACHE_PATH.relative_to(PROJECT_ROOT),
                    ",".join(available),
                )
            )
        return available[:requested]

    symbols = _parse_csv(raw_symbols)
    missing: List[str] = []
    available = set(_available_symbols_for_timeframes(timeframes))
    for symbol in symbols:
        if symbol not in available:
            missing.append(symbol)
    if missing:
        raise BenchmarkBlocked(
            "missing real symbol/timeframe data in %s: %s"
            % (KLINE_CACHE_PATH.relative_to(PROJECT_ROOT), ",".join(missing))
        )
    return symbols


def _phase0_preprocessing_config() -> Dict[str, Any]:
    config = copy.deepcopy(_l65_full_preprocessing_config())
    config.setdefault("fractional_differencing", {})["precision"] = 0.02
    config.setdefault("fractional_differencing", {})["cache_d_star"] = True
    return config


def _config_hash(config: Dict[str, Any], layers: str, workload_label: str, phase: int) -> str:
    payload = {
        "config": config,
        "fracdiff_layers": layers,
        "workload_label": workload_label,
        "phase": int(phase),
        "benchmark_schema": SUITE_SCHEMA_VERSION,
    }
    import hashlib

    return hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()


def _time_range_from_index(index: pd.Index) -> Optional[Tuple[int, int]]:
    if len(index) == 0:
        return None
    first = index[0]
    last = index[-1]
    try:
        first_ts = pd.Timestamp(first)
        last_ts = pd.Timestamp(last)
        return int(first_ts.timestamp() * 1000), int(last_ts.timestamp() * 1000)
    except (TypeError, ValueError, OSError):
        return 0, int(len(index) - 1)


def _build_context(
    frame: pd.DataFrame,
    *,
    symbol: str,
    timeframe: str,
    config_hash: str,
    source_data_version: str,
) -> PreprocessingContext:
    data_fingerprint, weak = compute_data_fingerprint(frame)
    return PreprocessingContext(
        symbol=symbol,
        timeframe=timeframe,
        config_hash=config_hash,
        data_fingerprint=data_fingerprint,
        feature_schema_hash=compute_feature_schema_hash(frame.columns),
        time_range=_time_range_from_index(frame.index),
        row_count=int(len(frame)),
        source_data_version=source_data_version,
        data_fingerprint_status="weak_fingerprint" if weak else "strong",
    )


def _load_real_feature_frame(symbol: str, timeframe: str, max_rows: int, max_cols: int) -> pd.DataFrame:
    raw_frame = _load_hdf5_kline_frame(symbol, timeframe, KLINE_CACHE_PATH)
    if raw_frame is None:
        raise BenchmarkBlocked(
            "missing HDF5 dataset %s/%s/data in %s"
            % (symbol, timeframe, KLINE_CACHE_PATH.relative_to(PROJECT_ROOT))
        )
    if len(raw_frame) < max(100, min(max_rows, 1500)):
        raise BenchmarkBlocked(
            "insufficient rows for %s/%s: %d available, requested max_rows=%d"
            % (symbol, timeframe, len(raw_frame), max_rows)
        )
    recent = raw_frame.tail(max_rows)
    return _build_l1_l2_real_features(recent, max_cols=max_cols)


def _baseline_path(symbol: str, timeframe: str, max_rows: int, synthetic: bool) -> Optional[Path]:
    if synthetic:
        path = DEFAULT_GOLDEN_DIR / "tier2_reduced" / "synthetic_baseline.parquet"
    else:
        path = DEFAULT_GOLDEN_DIR / "tier2_reduced" / f"{symbol}_{timeframe}_{max_rows}rows.parquet"
    return path if path.exists() else None


def _relative(path: Optional[Path]) -> Optional[str]:
    if path is None:
        return None
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _output_size_delta_pct(output_path: Path, baseline_path: Optional[Path]) -> Optional[float]:
    if baseline_path is None or not baseline_path.exists() or not output_path.exists():
        return None
    baseline_size = baseline_path.stat().st_size
    if baseline_size <= 0:
        return None
    delta = (output_path.stat().st_size - baseline_size) / float(baseline_size) * 100.0
    return round(delta, 6)


def _cache_file_size(path_str: Optional[str]) -> Optional[int]:
    if not path_str:
        return None
    path = PROJECT_ROOT / path_str
    if path.exists():
        return path.stat().st_size
    return None


def _run_l65_transform(
    frame: pd.DataFrame,
    *,
    symbol: str,
    timeframe: str,
    gate_id: str,
    repeat_index: int,
    layers: str,
    synthetic: bool,
    max_rows: int,
    timestamp: str,
    phase: int,
) -> SingleRunResult:
    config = _phase0_preprocessing_config()
    workload_label = "synthetic" if synthetic else "real"
    config_hash = _config_hash(config, layers=layers, workload_label=workload_label, phase=phase)
    context = _build_context(
        frame,
        symbol=symbol,
        timeframe=timeframe,
        config_hash=config_hash,
        source_data_version=SUITE_SCHEMA_VERSION,
    )
    preprocessor = FeaturePreprocessor(config, context=context)
    DSTAR_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    preprocessor._d_star_cache_dir = lambda: DSTAR_CACHE_DIR
    preprocessor._d_star_cache_shared = True

    process = psutil.Process()
    rss_before_mb = int(process.memory_info().rss // BYTES_PER_MB)
    started = time.perf_counter()
    cache_hits = 0
    cache_misses = 0
    dstar_cache_path: Optional[Path] = None

    env_overrides = {
        "FFACT_L65_OPTIMIZATION_PROFILE": "optimized",
        "FFACT_FRACDIFF_APPLY_TO_LAYERS": layers,
    }
    if int(phase) == 1:
        env_overrides["FFACT_L65_SLOWPATH_PARALLEL"] = "1"
    if int(phase) == 2:
        env_overrides["FFACT_L65_SLOWPATH_PARALLEL"] = "1"
        env_overrides["FFACT_USE_FAST_ADF"] = "1"

    with _temporary_env(env_overrides):
        with PeakRssSampler() as sampler:
            processed = preprocessor.transform(frame)
        peak_rss_mb = sampler.peak_rss_mb

    elapsed = time.perf_counter() - started
    cache = preprocessor._d_star_cache
    if cache is not None:
        cache_hits, cache_misses = cache.stats()
        cache.flush_atomic()
        dstar_cache_path = cache.path
    preprocessor._d_star_cache = None
    preprocessor._d_star_cache_shared = False
    gc.collect()
    rss_after_gc_mb = int(process.memory_info().rss // BYTES_PER_MB)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / (
        f"{gate_id.lower()}_{symbol}_{timeframe}_run{repeat_index}_{timestamp}.parquet"
    )
    _atomic_write_parquet(output_path, processed.astype(np.float32, copy=False))

    baseline = _baseline_path(symbol, timeframe, max_rows=max_rows, synthetic=synthetic)
    cache_total = cache_hits + cache_misses
    cache_hit_rate = None if cache_total == 0 else round(cache_hits / float(cache_total), 6)
    dstar_size = dstar_cache_path.stat().st_size if dstar_cache_path and dstar_cache_path.exists() else None

    return SingleRunResult(
        gate_id=gate_id,
        status=STATUS_PASS,
        symbol=symbol,
        timeframe=timeframe,
        repeat_index=repeat_index,
        wall_time_seconds=elapsed,
        rss_before_mb=rss_before_mb,
        peak_rss_mb=peak_rss_mb,
        rss_after_gc_mb=rss_after_gc_mb,
        rows_per_item=int(len(frame)),
        input_columns=int(frame.shape[1]),
        output_columns=int(processed.shape[1]),
        cache_hits=cache_hits,
        cache_misses=cache_misses,
        cache_hit_rate=cache_hit_rate,
        output_path=_relative(output_path),
        baseline_path=_relative(baseline),
        dstar_cache_path=_relative(dstar_cache_path),
        dstar_json_size_bytes=dstar_size,
        output_size_delta_pct=_output_size_delta_pct(output_path, baseline),
    )


def _run_single_real(
    *,
    symbol: str,
    timeframe: str,
    gate_id: str,
    repeat_index: int,
    layers: str,
    max_rows: int,
    max_cols: int,
    timestamp: str,
    phase: int,
) -> SingleRunResult:
    frame = _load_real_feature_frame(symbol, timeframe, max_rows=max_rows, max_cols=max_cols)
    return _run_l65_transform(
        frame,
        symbol=symbol,
        timeframe=timeframe,
        gate_id=gate_id,
        repeat_index=repeat_index,
        layers=layers,
        synthetic=False,
        max_rows=max_rows,
        timestamp=timestamp,
        phase=phase,
    )


def _run_single_synthetic(
    *,
    gate_id: str,
    repeat_index: int,
    layers: str,
    max_rows: int,
    max_cols: int,
    timestamp: str,
    phase: int,
) -> SingleRunResult:
    frame = make_synthetic_l65_dataset(rows=max_rows, cols=max_cols, stationary_ratio=0.6)
    return _run_l65_transform(
        frame,
        symbol="SYNTHETIC",
        timeframe="fixture",
        gate_id=gate_id,
        repeat_index=repeat_index,
        layers=layers,
        synthetic=True,
        max_rows=max_rows,
        timestamp=timestamp,
        phase=phase,
    )


def _available_ram_gb() -> float:
    return psutil.virtual_memory().available / float(1024 ** 3)


def _ram_gate_would_block(min_available_gb: float = RAM_GATE_MIN_AVAILABLE_GB) -> bool:
    return _available_ram_gb() < min_available_gb


def _memory_sanity_failed(entries: Sequence[SingleRunResult]) -> bool:
    for entry in entries:
        single_limit = max(entry.rss_before_mb + 1024, int(entry.peak_rss_mb * 0.75))
        if entry.rss_after_gc_mb > single_limit:
            return True

    if len(entries) >= 20:
        window = [entry.rss_after_gc_mb for entry in entries[-20:]]
        monotonic = all(window[index] <= window[index + 1] for index in range(len(window) - 1))
        if monotonic and (window[-1] - window[0] > MULTI_RSS_CUMULATIVE_LIMIT_MB):
            return True
    return False


def _write_checkpoint(checkpoint: Dict[str, Any], timestamp: str) -> Path:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    path = CHECKPOINT_DIR / f"phase0_gate_checkpoint_{timestamp}.json"
    _atomic_write_json(path, checkpoint)
    return path


def _gate_id_from_args(args: argparse.Namespace) -> str:
    if bool(getattr(args, "smoke", False)):
        return "T3.1"
    phase = int(getattr(args, "phase", 0))
    if phase == 1:
        if bool(args.cache_hit):
            return "T1.P3"
        return "T1.P1"
    if phase == 2:
        return "T2.P1"
    if bool(args.memory_sanity):
        return "T0.P7"
    if bool(args.multi):
        return "T0.P2"
    if bool(args.cache_hit):
        return "T0.P3"
    if bool(args.synthetic):
        return "T0.P5"
    return "T0.P1"


def _entry_passes_limits(entry: SingleRunResult, gate_id: str) -> Tuple[bool, str]:
    if entry.peak_rss_mb > PHASE0_RSS_LIMIT_MB:
        return False, "peak RSS %dMB exceeds %dMB" % (entry.peak_rss_mb, PHASE0_RSS_LIMIT_MB)
    if entry.dstar_json_size_bytes is not None and entry.dstar_json_size_bytes > DSTAR_JSON_LIMIT_BYTES:
        return False, "d_star JSON %d bytes exceeds 5MB" % entry.dstar_json_size_bytes
    if gate_id == "T0.P1" and entry.wall_time_seconds > PHASE0_WALL_LIMIT_SECONDS:
        return False, "wall %.2fs exceeds 60min" % entry.wall_time_seconds
    if gate_id == "T0.P3" and entry.wall_time_seconds > PHASE0_CACHE_HIT_WALL_LIMIT_SECONDS:
        return False, "cache-hit wall %.2fs exceeds 10min" % entry.wall_time_seconds
    if gate_id == "T0.P5" and entry.wall_time_seconds > PHASE0_SYNTHETIC_WALL_LIMIT_SECONDS:
        return False, "synthetic wall %.2fs exceeds 5min" % entry.wall_time_seconds
    if gate_id == "T1.P1" and entry.wall_time_seconds > PHASE1_WALL_LIMIT_SECONDS:
        return False, "phase1 wall %.2fs exceeds 30min" % entry.wall_time_seconds
    if gate_id == "T1.P3" and entry.wall_time_seconds > PHASE1_CACHE_HIT_WALL_LIMIT_SECONDS:
        return False, "phase1 cache-hit wall %.2fs exceeds 5min" % entry.wall_time_seconds
    if gate_id == "T2.P1" and entry.wall_time_seconds > PHASE2_WALL_LIMIT_SECONDS:
        return False, "phase2 wall %.2fs exceeds 15min" % entry.wall_time_seconds
    return True, ""


def _sum_output_size_mb(entries: Sequence[Dict[str, Any]]) -> Optional[float]:
    total_size = 0
    found = False
    for entry in entries:
        raw_path = entry.get("output_path")
        if not raw_path:
            continue
        output_path = PROJECT_ROOT / str(raw_path)
        if output_path.exists():
            total_size += output_path.stat().st_size
            found = True
    if not found:
        return None
    return round(total_size / float(BYTES_PER_MB), 6)


def _load_recent_history(current: Dict[str, Any], result_dir: Path) -> List[Dict[str, Any]]:
    timestamp = _parse_timestamp(current.get("timestamp")) or datetime.now(timezone.utc)
    lookback_start = timestamp - timedelta(days=REGRESSION_LOOKBACK_DAYS)
    history: List[Dict[str, Any]] = []
    for result_file in sorted(result_dir.glob("*.json")):
        try:
            with result_file.open("r", encoding="utf-8") as file_obj:
                candidate = json.load(file_obj)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(candidate, dict):
            continue
        if candidate.get("timestamp") == current.get("timestamp"):
            continue
        if candidate.get("status") != STATUS_PASS:
            continue
        if candidate.get("gate_id") != current.get("gate_id"):
            continue
        if _safe_int(candidate.get("phase"), -1) != _safe_int(current.get("phase"), -2):
            continue
        if _safe_int(candidate.get("tier_gb"), -1) != _safe_int(current.get("tier_gb"), -2):
            continue
        if _safe_int(candidate.get("rows_per_item"), -1) != _safe_int(current.get("rows_per_item"), -2):
            continue
        if _safe_int(candidate.get("n_symbols"), -1) != _safe_int(current.get("n_symbols"), -2):
            continue
        if _safe_int(candidate.get("n_timeframes"), -1) != _safe_int(current.get("n_timeframes"), -2):
            continue
        candidate_time = _parse_timestamp(candidate.get("timestamp"))
        if candidate_time is None or candidate_time < lookback_start or candidate_time > timestamp:
            continue
        history.append(candidate)
    return history


def _regression_reasons(current: Dict[str, Any], history: Sequence[Dict[str, Any]]) -> List[str]:
    if not history or current.get("status") != STATUS_PASS:
        return []

    reasons: List[str] = []
    current_wall = float(current.get("wall_time_seconds") or 0.0)
    history_walls = [
        float(item.get("wall_time_seconds") or 0.0)
        for item in history
        if float(item.get("wall_time_seconds") or 0.0) > 0.0
    ]
    if current_wall > 0.0 and history_walls:
        wall_baseline = median(history_walls)
        if current_wall > wall_baseline * (1.0 + REGRESSION_DEGRADATION_THRESHOLD):
            reasons.append(
                "wall_time_seconds %.3f regressed >20%% vs 7-day median %.3f"
                % (current_wall, wall_baseline)
            )

    current_rss = float(current.get("peak_rss_mb") or 0.0)
    history_rss = [
        float(item.get("peak_rss_mb") or 0.0)
        for item in history
        if float(item.get("peak_rss_mb") or 0.0) > 0.0
    ]
    if current_rss > 0.0 and history_rss:
        rss_baseline = median(history_rss)
        if current_rss > rss_baseline * (1.0 + REGRESSION_DEGRADATION_THRESHOLD):
            reasons.append(
                "peak_rss_mb %.1f regressed >20%% vs 7-day median %.1f"
                % (current_rss, rss_baseline)
            )
    return reasons


def detect_regression(current: Dict[str, Any], history: List[Dict[str, Any]]) -> bool:
    return bool(_regression_reasons(current, history))


def _finalize_summary(summary: BenchmarkSummary) -> BenchmarkSummary:
    payload = summary.to_dict()
    entries = payload.get("entries", [])
    if isinstance(entries, list):
        summary.l7_size_mb = _sum_output_size_mb(entries)
    payload = summary.to_dict()
    history = _load_recent_history(payload, RESULT_DIR)
    reasons = _regression_reasons(payload, history)
    summary.history_sample_count = len(history)
    summary.regression_reasons = reasons
    summary.regression_flag = bool(reasons)
    return summary


def _unique_result_path(directory: Path, file_name: str) -> Path:
    path = directory / file_name
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = directory / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError("Could not allocate unique result path for %s" % file_name)


def _write_benchmark_payload(payload: Dict[str, Any], args: argparse.Namespace) -> List[Path]:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    tier_label = "%dgb" % int(payload.get("tier_gb", _parse_tier_gb(args.tier)))
    phase = int(payload.get("phase", int(args.phase)))
    timestamp = str(payload.get("timestamp", _utc_timestamp()))
    suite_name = "%s_%d_%s.json" % (tier_label, phase, timestamp)
    written_paths = []
    suite_path = _unique_result_path(RESULT_DIR, suite_name)
    _atomic_write_json(suite_path, payload)
    written_paths.append(suite_path)

    if not bool(getattr(args, "_smoke_child", False)):
        gate_id = str(payload.get("gate_id", _gate_id_from_args(args))).replace(".", "_")
        legacy_name = "phase%d_gate_%s_%s.json" % (phase, gate_id, timestamp)
        legacy_path = _unique_result_path(RESULT_DIR, legacy_name)
        _atomic_write_json(legacy_path, payload)
        written_paths.append(legacy_path)
    return written_paths


def _prepare_full_mode_args(args: argparse.Namespace) -> None:
    tier_gb = _parse_tier_gb(args.tier)
    if bool(args.full) and bool(args.full_width_proxy):
        raise BenchmarkBlocked("--full and --full-width-proxy are mutually exclusive")
    if bool(args.full) and tier_gb == 8 and not bool(args.best_effort):
        raise BenchmarkBlocked("8GB --full requires --best-effort")
    if bool(args.full):
        args.symbols = "ETHUSDT,BTCUSDT"
        args.tfs = "1h,12h"
        args.multi = True
    if bool(args.full_width_proxy):
        args.max_rows = max(int(args.max_rows), FULL_WIDTH_PROXY_MIN_ROWS)
        args.symbols = str(args.symbols or "ETHUSDT")
        args.tfs = str(args.tfs or "1h")


def _summarize_single(entries: List[SingleRunResult], args: argparse.Namespace) -> BenchmarkSummary:
    gate_id = _gate_id_from_args(args)
    timestamp = str(args._timestamp)
    tier_gb = _parse_tier_gb(args.tier)
    status = STATUS_PASS
    reasons: List[str] = []

    for entry in entries:
        passed, reason = _entry_passes_limits(entry, gate_id)
        if not passed:
            status = STATUS_FAIL
            reasons.append(reason)

    if gate_id in {"T0.P3", "T1.P3"}:
        final_entry = entries[-1]
        if final_entry.cache_hit_rate is None or final_entry.cache_hit_rate < 0.9:
            status = STATUS_FAIL
            reasons.append("cache hit rate %.3f below 0.90" % (final_entry.cache_hit_rate or 0.0))

    cache_rates = [entry.cache_hit_rate for entry in entries if entry.cache_hit_rate is not None]
    size_deltas = [entry.output_size_delta_pct for entry in entries if entry.output_size_delta_pct is not None]
    return _finalize_summary(BenchmarkSummary(
        gate_id=gate_id,
        status=status,
        phase=int(args.phase),
        tier_gb=tier_gb,
        timestamp=timestamp,
        wall_time_seconds=sum(entry.wall_time_seconds for entry in entries),
        peak_rss_mb=max((entry.peak_rss_mb for entry in entries), default=0),
        cache_hit_rate=cache_rates[-1] if cache_rates else None,
        n_symbols=1,
        n_timeframes=1,
        rows_per_item=max((entry.rows_per_item for entry in entries), default=0),
        memory_sanity_failed=False,
        oom=any(entry.oom for entry in entries),
        sigkill=any(entry.sigkill for entry in entries),
        output_size_delta_pct=max(size_deltas, key=abs) if size_deltas else None,
        blocking_reason="; ".join(reasons),
        concurrent_symbols=1,
        entries=[entry.to_dict() for entry in entries],
    ))


def _run_multi(args: argparse.Namespace) -> BenchmarkSummary:
    timestamp = str(args._timestamp)
    gate_id = _gate_id_from_args(args)
    timeframes = _parse_csv(args.tfs)
    symbols = _resolve_symbols(str(args.symbols), timeframes)
    tier_gb = _parse_tier_gb(args.tier)
    concurrent_symbols = get_tier_concurrent_symbols(tier_gb)
    if tier_gb == 8 and concurrent_symbols != 1:
        raise BenchmarkBlocked("8GB tier requires concurrent_symbols=1, got %d" % concurrent_symbols)

    checkpoint: Dict[str, Any] = {
        "schema_version": 1,
        "gate_id": gate_id,
        "batch_id": "phase0_gate_%s" % timestamp,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_items": [],
        "failed_items": [],
        "queued_items": [
            {"symbol": symbol, "timeframe": timeframe}
            for symbol in symbols
            for timeframe in timeframes
        ],
        "concurrent_symbols": concurrent_symbols,
        "memory_sanity_failed": False,
        "ram_gate_trigger_check": _ram_gate_would_block(_available_ram_gb() + 1.0),
    }
    checkpoint_path = _write_checkpoint(checkpoint, timestamp)

    entries: List[SingleRunResult] = []
    while checkpoint["queued_items"]:
        if _ram_gate_would_block():
            raise BenchmarkBlocked(
                "RAM gate blocked multi benchmark: available %.2fGB < %.2fGB"
                % (_available_ram_gb(), RAM_GATE_MIN_AVAILABLE_GB)
            )

        item = checkpoint["queued_items"].pop(0)
        try:
            result = _run_single_real(
                symbol=str(item["symbol"]),
                timeframe=str(item["timeframe"]),
                gate_id=gate_id,
                repeat_index=len(entries) + 1,
                layers=str(args.layers),
                max_rows=int(args.max_rows),
                max_cols=int(args.max_cols),
                timestamp=timestamp,
                phase=int(args.phase),
            )
            entries.append(result)
            checkpoint["completed_items"].append({
                "symbol": item["symbol"],
                "timeframe": item["timeframe"],
                "output_paths": [result.output_path] if result.output_path else [],
                "rss_peak_item_mb": result.peak_rss_mb,
                "rss_after_gc_mb": result.rss_after_gc_mb,
            })
        except Exception as exc:
            checkpoint["failed_items"].append({
                "symbol": item["symbol"],
                "timeframe": item["timeframe"],
                "reason": str(exc),
                "failure_type": "compute_error",
            })
        checkpoint["memory_sanity_failed"] = _memory_sanity_failed(entries)
        checkpoint["last_updated_at"] = datetime.now(timezone.utc).isoformat()
        _write_checkpoint(checkpoint, timestamp)

    status = STATUS_PASS
    reasons: List[str] = []
    if checkpoint["failed_items"]:
        status = STATUS_FAIL
        reasons.append("failed_items=%d" % len(checkpoint["failed_items"]))
    if checkpoint["memory_sanity_failed"]:
        status = STATUS_FAIL
        reasons.append("memory sanity failed")
    if not checkpoint.get("ram_gate_trigger_check"):
        status = STATUS_FAIL
        reasons.append("RAM gate trigger self-check did not block")

    cache_rates = [entry.cache_hit_rate for entry in entries if entry.cache_hit_rate is not None]
    size_deltas = [entry.output_size_delta_pct for entry in entries if entry.output_size_delta_pct is not None]
    return _finalize_summary(BenchmarkSummary(
        gate_id=gate_id,
        status=status,
        phase=int(args.phase),
        tier_gb=tier_gb,
        timestamp=timestamp,
        wall_time_seconds=sum(entry.wall_time_seconds for entry in entries),
        peak_rss_mb=max((entry.peak_rss_mb for entry in entries), default=0),
        cache_hit_rate=cache_rates[-1] if cache_rates else None,
        n_symbols=len(symbols),
        n_timeframes=len(timeframes),
        rows_per_item=int(args.max_rows),
        memory_sanity_failed=bool(checkpoint["memory_sanity_failed"]),
        output_size_delta_pct=max(size_deltas, key=abs) if size_deltas else None,
        blocking_reason="; ".join(reasons),
        concurrent_symbols=concurrent_symbols,
        checkpoint_path=_relative(checkpoint_path),
        entries=[entry.to_dict() for entry in entries],
    ))


def run_benchmark(args: argparse.Namespace) -> Dict[str, Any]:
    timestamp = _utc_timestamp()
    setattr(args, "_timestamp", timestamp)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    gate_id = _gate_id_from_args(args)
    tier_gb = _parse_tier_gb(args.tier)
    tier_simulation: Dict[str, Any] = {}

    with _tier_memory_limit(tier_gb) as tier_state:
        tier_simulation = dict(tier_state)
        try:
            _prepare_full_mode_args(args)
            if bool(args.multi) or bool(args.memory_sanity):
                summary = _run_multi(args)
            else:
                repeat = int(args.repeat)
                if bool(args.cache_hit):
                    repeat = max(repeat, 2)
                entries: List[SingleRunResult] = []
                for repeat_index in range(1, repeat + 1):
                    if bool(args.synthetic):
                        entry = _run_single_synthetic(
                            gate_id=gate_id,
                            repeat_index=repeat_index,
                            layers=str(args.layers),
                            max_rows=int(args.max_rows),
                            max_cols=int(args.max_cols),
                            timestamp=timestamp,
                            phase=int(args.phase),
                        )
                    else:
                        symbols = _resolve_symbols(str(args.symbols), _parse_csv(args.tfs))
                        timeframes = _parse_csv(args.tfs)
                        entry = _run_single_real(
                            symbol=symbols[0],
                            timeframe=timeframes[0],
                            gate_id=gate_id,
                            repeat_index=repeat_index,
                            layers=str(args.layers),
                            max_rows=int(args.max_rows),
                            max_cols=int(args.max_cols),
                            timestamp=timestamp,
                            phase=int(args.phase),
                        )
                    entries.append(entry)
                summary = _summarize_single(entries, args)
        except BenchmarkBlocked as exc:
            summary = _finalize_summary(BenchmarkSummary(
                gate_id=gate_id,
                status=STATUS_BLOCKED,
                phase=int(args.phase),
                tier_gb=tier_gb,
                timestamp=timestamp,
                blocking_reason=str(exc),
                concurrent_symbols=get_tier_concurrent_symbols(tier_gb),
            ))
        except MemoryError as exc:
            summary = _finalize_summary(BenchmarkSummary(
                gate_id=gate_id,
                status=STATUS_FAIL,
                phase=int(args.phase),
                tier_gb=tier_gb,
                timestamp=timestamp,
                oom=True,
                blocking_reason=str(exc),
                concurrent_symbols=get_tier_concurrent_symbols(tier_gb),
            ))
        except Exception as exc:
            logger.error("[L6.5] benchmark failed: %s", exc, exc_info=True)
            summary = _finalize_summary(BenchmarkSummary(
                gate_id=gate_id,
                status=STATUS_FAIL,
                phase=int(args.phase),
                tier_gb=tier_gb,
                timestamp=timestamp,
                blocking_reason=str(exc),
                concurrent_symbols=get_tier_concurrent_symbols(tier_gb),
            ))

    summary.tier_simulation = tier_simulation
    summary = _finalize_summary(summary)
    payload = summary.to_dict()
    written_paths = _write_benchmark_payload(payload, args)
    payload["result_paths"] = [_relative(path) for path in written_paths]
    for path in written_paths:
        _atomic_write_json(path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return payload


def run_smoke_suite(args: argparse.Namespace) -> Dict[str, Any]:
    timestamp = _utc_timestamp()
    explicit_tier = bool(getattr(args, "_tier_explicit", False))
    tiers = [str(args.tier)] if explicit_tier else list(SMOKE_TIERS)
    rows = min(int(args.max_rows), SMOKE_DEFAULT_ROWS)
    cols = min(int(args.max_cols), SMOKE_DEFAULT_COLS)
    entries: List[Dict[str, Any]] = []

    for tier in tiers:
        for phase in SMOKE_PHASES:
            child_args = argparse.Namespace(**vars(args))
            child_args.smoke = False
            child_args._smoke_child = True
            child_args.tier = tier
            child_args.phase = phase
            child_args.symbols = "SYNTHETIC"
            child_args.tfs = "fixture"
            child_args.repeat = 1
            child_args.max_rows = rows
            child_args.max_cols = cols
            child_args.layers = "L1,L2"
            child_args.multi = False
            child_args.cache_hit = False
            child_args.synthetic = True
            child_args.full_l65 = True
            child_args.memory_sanity = False
            child_args.best_effort = True
            child_args.full = False
            child_args.full_width_proxy = False
            child_payload = run_benchmark(child_args)
            entries.append(child_payload)

    statuses = [str(entry.get("status")) for entry in entries]
    if all(status == STATUS_PASS for status in statuses):
        status = STATUS_PASS
        reason = ""
    elif any(status == STATUS_FAIL for status in statuses):
        status = STATUS_FAIL
        reason = "one or more smoke benchmark entries failed"
    else:
        status = STATUS_BLOCKED
        reason = "one or more smoke benchmark entries were blocked"

    payload = {
        "schema_version": SUITE_SCHEMA_VERSION,
        "gate_id": "T3.1",
        "status": status,
        "timestamp": timestamp,
        "tier_gb": None,
        "phase": None,
        "smoke_tiers": tiers,
        "smoke_phases": list(SMOKE_PHASES),
        "wall_time_seconds": round(sum(float(entry.get("wall_time_seconds") or 0.0) for entry in entries), 6),
        "peak_rss_mb": max((int(entry.get("peak_rss_mb") or 0) for entry in entries), default=0),
        "entries": entries,
        "blocking_reason": reason,
        "regression_flag": any(bool(entry.get("regression_flag")) for entry in entries),
    }
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _unique_result_path(RESULT_DIR, "smoke_%s.json" % timestamp)
    _atomic_write_json(output_path, payload)
    payload["result_paths"] = [_relative(output_path)]
    _atomic_write_json(output_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Layer 6.5 benchmark gates and smoke suite")
    parser.add_argument("--tier", choices=["8gb", "16gb", "24gb", "32gb"], default="8gb")
    parser.add_argument("--phase", choices=["0", "1", "2"], default="0")
    parser.add_argument("--symbols", default="ETHUSDT")
    parser.add_argument("--tfs", default="1h")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--max-rows", type=int, default=2000)
    parser.add_argument("--max-cols", type=int, default=500)
    parser.add_argument("--layers", default="L1,L2")
    parser.add_argument("--multi", action="store_true")
    parser.add_argument("--cache-hit", action="store_true")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--full-l65", action="store_true")
    parser.add_argument("--memory-sanity", action="store_true")
    parser.add_argument("--best-effort", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--full-width-proxy", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(raw_argv)
    setattr(args, "_tier_explicit", any(item == "--tier" or item.startswith("--tier=") for item in raw_argv))
    if int(args.repeat) <= 0:
        raise SystemExit("--repeat must be positive")
    if int(args.max_rows) <= 0 or int(args.max_cols) <= 0:
        raise SystemExit("--max-rows and --max-cols must be positive")

    payload = run_smoke_suite(args) if bool(args.smoke) else run_benchmark(args)
    status = payload.get("status")
    if status == STATUS_PASS:
        return 0
    if status == STATUS_BLOCKED:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
