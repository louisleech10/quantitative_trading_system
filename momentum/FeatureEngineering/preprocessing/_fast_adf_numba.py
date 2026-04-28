"""Numba-backed Augmented Dickey-Fuller p-value helper for L6.5."""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

from momentum.core.logging import get_logger

try:
    from numba import njit
except Exception:  # pragma: no cover - requirements include numba
    def njit(*args, **kwargs):  # type: ignore[no-redef]
        if args and callable(args[0]):
            return args[0]

        def decorator(function):
            return function

        return decorator

try:
    from statsmodels.tsa.adfvalues import mackinnonp
    from statsmodels.tsa.stattools import adfuller

    HAS_STATSMODELS = True
except Exception:  # pragma: no cover - requirements include statsmodels
    mackinnonp = None
    adfuller = None
    HAS_STATSMODELS = False


logger = get_logger(__name__)
MIN_ADF_OBSERVATIONS = 20
SINGULAR_DIAGONAL_EPS = 1e-12
CONDITION_NUMBER_LIMIT = 1e10
THRESHOLD_BAND_LOW = 0.08
THRESHOLD_BAND_HIGH = 0.12
DEFAULT_SAMPLE_SIZE = 500
FAST_ADF_ENGINE_VERSION = "fast-adf-numba-v1"


@njit(cache=True, fastmath=False)
def _adf_ols_core(values: np.ndarray, lag: int) -> Tuple[float, float, int]:
    """Return ADF t-statistic, standard error, and condition flag."""

    row_count = int(values.size)
    regression_rows = row_count - lag - 1
    column_count = lag + 2
    if regression_rows <= column_count:
        return 0.0, 0.0, 1

    delta_values = np.empty(row_count - 1, dtype=np.float64)
    for value_index in range(row_count - 1):
        delta_values[value_index] = values[value_index + 1] - values[value_index]

    design_matrix = np.empty((regression_rows, column_count), dtype=np.float64)
    dependent_values = np.empty(regression_rows, dtype=np.float64)
    for row_index in range(regression_rows):
        source_index = lag + row_index
        design_matrix[row_index, 0] = values[source_index]
        for lag_index in range(lag):
            design_matrix[row_index, lag_index + 1] = delta_values[
                lag + row_index - lag_index - 1
            ]
        design_matrix[row_index, column_count - 1] = 1.0
        dependent_values[row_index] = delta_values[lag + row_index]

    transposed_design = design_matrix.T
    normal_matrix = transposed_design @ design_matrix
    min_diagonal = 1e18
    for diagonal_index in range(column_count):
        diagonal_value = abs(normal_matrix[diagonal_index, diagonal_index])
        if diagonal_value < min_diagonal:
            min_diagonal = diagonal_value
    if min_diagonal < SINGULAR_DIAGONAL_EPS:
        return 0.0, 0.0, 1

    beta_values = np.linalg.solve(normal_matrix, transposed_design @ dependent_values)
    residual_values = dependent_values - design_matrix @ beta_values
    degrees_of_freedom = regression_rows - column_count
    if degrees_of_freedom <= 0:
        return 0.0, 0.0, 1

    residual_variance = (residual_values @ residual_values) / float(degrees_of_freedom)
    inverse_normal = np.linalg.inv(normal_matrix)
    variance_beta = residual_variance * inverse_normal[0, 0]
    if variance_beta <= 0.0 or not np.isfinite(variance_beta):
        return 0.0, 0.0, 1

    standard_error = np.sqrt(variance_beta)
    if standard_error < SINGULAR_DIAGONAL_EPS or not np.isfinite(standard_error):
        return 0.0, 0.0, 1

    t_statistic = beta_values[0] / standard_error
    if not np.isfinite(t_statistic):
        return 0.0, 0.0, 1
    return float(t_statistic), float(standard_error), 0


def _default_lag(row_count: int) -> int:
    return int(round(12.0 * (float(row_count) / 100.0) ** 0.25))


def _resolve_lag(row_count: int, lag: Optional[int]) -> int:
    requested_lag = _default_lag(row_count) if lag is None else int(lag)
    if requested_lag < 0:
        raise ValueError("lag must be non-negative")
    max_lag = max(0, (int(row_count) - 4) // 2)
    return min(requested_lag, max_lag)


def _prepare_values(series: np.ndarray, sample_size: int) -> np.ndarray:
    values = np.asarray(series, dtype=np.float64).reshape(-1)
    if int(sample_size) > 0 and values.size > int(sample_size):
        values = values[-int(sample_size) :]
    return np.ascontiguousarray(values, dtype=np.float64)


def _finite_tail_values(series: np.ndarray, sample_size: int) -> np.ndarray:
    values = np.asarray(series, dtype=np.float64).reshape(-1)
    values = values[np.isfinite(values)]
    if int(sample_size) > 0 and values.size > int(sample_size):
        values = values[-int(sample_size) :]
    return np.ascontiguousarray(values, dtype=np.float64)


def _adf_design_condition_number(values: np.ndarray, lag: int) -> float:
    regression_rows = int(values.size) - int(lag) - 1
    column_count = int(lag) + 2
    if regression_rows <= column_count:
        return float("inf")

    delta_values = values[1:] - values[:-1]
    design_matrix = np.empty((regression_rows, column_count), dtype=np.float64)
    for row_index in range(regression_rows):
        source_index = int(lag) + row_index
        design_matrix[row_index, 0] = values[source_index]
        for lag_index in range(int(lag)):
            design_matrix[row_index, lag_index + 1] = delta_values[
                int(lag) + row_index - lag_index - 1
            ]
        design_matrix[row_index, column_count - 1] = 1.0

    normal_matrix = design_matrix.T @ design_matrix
    diagonal = np.abs(np.diag(normal_matrix))
    if diagonal.size == 0 or float(np.min(diagonal)) < SINGULAR_DIAGONAL_EPS:
        return float("inf")
    try:
        condition_number = float(np.linalg.cond(normal_matrix))
    except np.linalg.LinAlgError:
        return float("inf")
    if not np.isfinite(condition_number):
        return float("inf")
    return condition_number


def _adf_fallback_statsmodels(
    series: np.ndarray,
    *,
    lag: Optional[int] = None,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> float:
    if not HAS_STATSMODELS or adfuller is None:
        logger.warning("[L6.5] statsmodels unavailable; Fast ADF fallback returns p=1.0")
        return 1.0

    values = _finite_tail_values(series, sample_size)
    if values.size < MIN_ADF_OBSERVATIONS:
        return 1.0

    try:
        if lag is None:
            return float(adfuller(values, regression="c", autolag="AIC")[1])
        effective_lag = _resolve_lag(int(values.size), lag)
        return float(
            adfuller(
                values,
                maxlag=effective_lag,
                regression="c",
                autolag=None,
            )[1]
        )
    except Exception:
        return 1.0


def adf_pvalue_fast(
    series: np.ndarray,
    *,
    lag: Optional[int] = None,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> Tuple[float, bool]:
    """Return ADF p-value and whether statsmodels fallback was used."""

    values = _prepare_values(series, sample_size)
    if values.size < MIN_ADF_OBSERVATIONS or not np.isfinite(values).all():
        return _adf_fallback_statsmodels(series, lag=lag, sample_size=sample_size), True

    try:
        effective_lag = _resolve_lag(int(values.size), lag)
    except (TypeError, ValueError):
        return _adf_fallback_statsmodels(series, lag=lag, sample_size=sample_size), True

    condition_number = _adf_design_condition_number(values, effective_lag)
    if condition_number > CONDITION_NUMBER_LIMIT:
        return _adf_fallback_statsmodels(series, lag=lag, sample_size=sample_size), True

    try:
        t_statistic, _, condition_flag = _adf_ols_core(values, effective_lag)
    except Exception:
        return _adf_fallback_statsmodels(series, lag=lag, sample_size=sample_size), True

    if condition_flag != 0 or mackinnonp is None:
        return _adf_fallback_statsmodels(series, lag=lag, sample_size=sample_size), True

    try:
        pvalue = float(mackinnonp(t_statistic, regression="c", N=1))
    except Exception:
        return _adf_fallback_statsmodels(series, lag=lag, sample_size=sample_size), True

    if not np.isfinite(pvalue):
        return _adf_fallback_statsmodels(series, lag=lag, sample_size=sample_size), True
    if THRESHOLD_BAND_LOW <= pvalue <= THRESHOLD_BAND_HIGH:
        return _adf_fallback_statsmodels(series, lag=lag, sample_size=sample_size), True
    return pvalue, False


def warmup_numba() -> None:
    """Compile the Fast ADF kernel before timing or fan-out."""

    sample = np.linspace(1.0, 2.0, 64, dtype=np.float64)
    adf_pvalue_fast(sample, lag=0, sample_size=64)


__all__ = ["FAST_ADF_ENGINE_VERSION", "adf_pvalue_fast", "warmup_numba"]
