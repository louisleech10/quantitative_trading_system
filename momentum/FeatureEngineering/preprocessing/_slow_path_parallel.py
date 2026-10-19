"""Joblib loky helpers for Layer 6.5 slow-path FracDiff work."""

from __future__ import annotations

import os
import sys
import threading
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


#: FFDSTAR Task 1.2、§N FFDSTAR-R3：當次 worker 欄之 statsmodels ADF 例外（例外類別名清單；執行緒區域，
#: 由 `process_fracdiff_column_values` 設定，不改 `_statsmodels_adf_pvalue` 簽名）
_ADF_ERRORS = threading.local()


def _statsmodels_adf_pvalue(values: np.ndarray, sample_size: int) -> float:
    """statsmodels 檢定拋例外時以 p=1.0 續行（行為不變）；例外類別名附加至當次欄之 `_ADF_ERRORS.errors` 供主程序記事件。"""
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
    except Exception as error:
        errors = getattr(_ADF_ERRORS, "errors", None)
        if errors is not None:
            errors.append(type(error).__name__)
        return 1.0


def process_fracdiff_column_values(values: np.ndarray, column_metadata: Dict[str, Any]) -> SlowPathResult:
    """Compute one column's d_star and FracDiff values using only ndarray + metadata.

    FFDSTAR Task 1.2、§N FFDSTAR-R3：結果另帶 `adf_error`（本欄 d* 搜尋中 statsmodels ADF 曾拋例外而以 p=1.0 續行），
    由主程序併為該欄之事件；數值行為不變。"""
    adf_errors: List[str] = []
    previous = getattr(_ADF_ERRORS, "errors", None)
    _ADF_ERRORS.errors = adf_errors
    try:
        result = _process_fracdiff_column_values(values, column_metadata)
    finally:
        _ADF_ERRORS.errors = previous
    result["adf_error"] = bool(adf_errors)
    return result


def _process_fracdiff_column_values(values: np.ndarray, column_metadata: Dict[str, Any]) -> SlowPathResult:
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
            # FFSTAT Task 2.1：判定值只取主程序交付之校準值（輸出起始日前之前史），不取輸出範圍之列
            calibration_values = column_metadata.get("calibration_values")
            if calibration_values is None:
                raise ValueError(f"column {column}: missing calibration_values (calibration_bars={calibration_bars})")
            decision_values = np.asarray(calibration_values, dtype=np.float64)
            d_star = find_min_d_with_prior(
                decision_values,
                precision=precision,
                adf_threshold=adf_threshold,
                adf_fn=adf_fn,
                fracdiff_fn=fracdiff_fn,
                d_range=d_range,
            )
    except Exception as error:
        # FFSTAT Task 3.1：搜尋失敗不再以 d=1.0 產值——回報失敗，由主程序保原值、不寫快取、記事件
        return {
            "column": column,
            "d_star": None,
            "fracdiff_values": None,
            "cache_hit": cache_hit,
            "status": "failed",
            "error": str(error),
        }

    fracdiff_values = fracdiff_fn(values, float(d_star))
    return {
        "column": column,
        "d_star": round(float(d_star), 4),
        "fracdiff_values": fracdiff_values,
        "cache_hit": cache_hit,
        "status": status,
        "error": error_message,
    }
