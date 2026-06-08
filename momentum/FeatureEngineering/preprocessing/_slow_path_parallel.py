"""Joblib loky helpers for Layer 6.5 slow-path FracDiff work."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import numpy as np

from momentum.FeatureEngineering.preprocessing._fast_adf_numba import adf_pvalue_fast
from momentum.FeatureEngineering.preprocessing._hurst_prior import (
    find_min_d_with_prior,
    fractional_difference_values,
)
from momentum.core.config import get_fast_adf_enabled
from momentum.core.logging import get_logger

try:
    from joblib import Parallel, delayed, parallel_backend
except Exception:
    Parallel = None
    delayed = None
    parallel_backend = None


logger = get_logger(__name__)
SlowPathItem = Tuple[np.ndarray, Dict[str, Any]]
SlowPathResult = Dict[str, Any]
SlowPathWorker = Callable[[np.ndarray, Dict[str, Any]], SlowPathResult]


@contextmanager
def _single_thread_blas_environment() -> Iterator[None]:
    previous: Dict[str, Optional[str]] = {
        "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
        "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS"),
    }
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    try:
        yield
    finally:
        for env_name, env_value in previous.items():
            if env_value is None:
                os.environ.pop(env_name, None)
            else:
                os.environ[env_name] = env_value


def _is_oom_like_error(error: BaseException) -> bool:
    message = str(error).lower()
    return any(
        token in message
        for token in (
            "memoryerror",
            "out of memory",
            "oom",
            "sigkill",
            "killed",
            "terminatedworkererror",
        )
    )


class ParallelSlowPath:
    """Small wrapper around joblib loky for FracDiff/ADF slow-path columns."""

    def __init__(self, n_jobs: int) -> None:
        self.n_jobs = max(1, int(n_jobs))

    def map(self, items: List[SlowPathItem], worker_function: SlowPathWorker) -> List[SlowPathResult]:
        if not items:
            return []
        if self.n_jobs <= 1:
            return [worker_function(values, metadata) for values, metadata in items]
        if sys.platform.startswith("win"):
            logger.warning("[L6.5] joblib slow path disabled on Windows; fallback to serial")
            return [worker_function(values, metadata) for values, metadata in items]
        if Parallel is None or delayed is None or parallel_backend is None:
            raise RuntimeError("joblib is required for L6.5 slow-path parallel execution")

        try:
            with _single_thread_blas_environment():
                with parallel_backend("loky", n_jobs=self.n_jobs, inner_max_num_threads=1):
                    return Parallel(
                        n_jobs=self.n_jobs,
                        backend="loky",
                        mmap_mode="r",
                        max_nbytes="1M",
                    )(
                        delayed(worker_function)(
                            np.asarray(values, dtype=np.float64),
                            dict(metadata),
                        )
                        for values, metadata in items
                    )
        except MemoryError:
            raise
        except BaseException as error:
            if _is_oom_like_error(error):
                raise MemoryError(str(error)) from error
            raise


def _statsmodels_adf_pvalue(values: np.ndarray, sample_size: int) -> float:
    from statsmodels.tsa.stattools import adfuller

    clean_values = np.asarray(values, dtype=np.float64)
    clean_values = clean_values[np.isfinite(clean_values)]
    if clean_values.size < 20:
        return 1.0
    sample = clean_values[-max(1, int(sample_size)) :]
    if get_fast_adf_enabled():
        return float(adf_pvalue_fast(sample, sample_size=sample_size)[0])
    try:
        return float(adfuller(sample, autolag="AIC")[1])
    except Exception:
        return 1.0


def process_fracdiff_column_values(values: np.ndarray, column_metadata: Dict[str, Any]) -> SlowPathResult:
    """Compute one column's d_star and FracDiff values using only ndarray + metadata."""

    column = str(column_metadata.get("column", ""))
    weight_threshold = float(column_metadata.get("weight_threshold", 1e-5))
    max_lag = int(column_metadata.get("max_lag", 0))
    precision = float(column_metadata.get("precision", 0.02))
    adf_threshold = float(column_metadata.get("adf_threshold", 0.05))
    sample_size = int(column_metadata.get("sample_size", 500))
    calibration_bars = int(column_metadata.get("calibration_bars", 0))
    d_range_raw = column_metadata.get("d_range", (0.0, 1.0))
    d_range = (float(d_range_raw[0]), float(d_range_raw[1]))
    cached_d_star = column_metadata.get("cached_d_star")
    cache_hit = cached_d_star is not None
    status = "ok"
    error_message = ""

    def fracdiff_fn(raw_values: np.ndarray, d_value: float) -> np.ndarray:
        return fractional_difference_values(
            raw_values,
            d_value,
            threshold=weight_threshold,
            max_width=max_lag,
        )

    def adf_fn(fracdiff_values: np.ndarray) -> float:
        return _statsmodels_adf_pvalue(fracdiff_values, sample_size=sample_size)

    try:
        if cache_hit:
            d_star = float(cached_d_star)
        else:
            decision_values = values
            if calibration_bars > 0:
                decision_values = values[: min(len(values), calibration_bars)]
            d_star = find_min_d_with_prior(
                decision_values,
                precision=precision,
                adf_threshold=adf_threshold,
                adf_fn=adf_fn,
                fracdiff_fn=fracdiff_fn,
                d_range=d_range,
            )
    except Exception as error:
        status = "fallback"
        error_message = str(error)
        d_star = 1.0

    fracdiff_values = fracdiff_fn(values, float(d_star))
    return {
        "column": column,
        "d_star": round(float(d_star), 4),
        "fracdiff_values": fracdiff_values,
        "cache_hit": cache_hit,
        "status": status,
        "error": error_message,
    }
