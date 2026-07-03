"""Hurst-prior bounded d* search helpers for Layer 6.5 FracDiff."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np


def _convolve_1d(signal: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """1-D fracdiff convolution (mode='valid') with prefix-stable direct math.

    MRFAIL-RECONCILE: FFT tail roundoff leaks into prefix bins, so fracdiff
    must stay on direct convolution.
    """
    return np.convolve(signal, weights, mode="valid")


AdfFunction = Callable[[np.ndarray], float]
FracDiffFunction = Callable[[np.ndarray, float], np.ndarray]
FullSearchFunction = Callable[[], float]


def estimate_hurst_rs(series: np.ndarray) -> float:
    """Estimate the Hurst exponent with a lightweight R/S slope prior."""

    values = np.asarray(series, dtype=np.float64)
    values = values[np.isfinite(values)]
    row_count = int(values.size)
    if row_count < 100:
        return float("nan")

    window_sizes = sorted({row_count // 8, row_count // 4, row_count // 2})
    rs_values: List[Tuple[int, float]] = []
    for window_size in window_sizes:
        if window_size < 8:
            continue
        chunk_values: List[float] = []
        for start_index in range(0, row_count - window_size + 1, window_size):
            chunk = values[start_index : start_index + window_size]
            if chunk.size < 8:
                continue
            chunk_mean = float(np.mean(chunk))
            cumulative_deviation = np.cumsum(chunk - chunk_mean)
            range_value = float(np.max(cumulative_deviation) - np.min(cumulative_deviation))
            std_value = float(np.std(chunk, ddof=1))
            if std_value > 1e-12 and np.isfinite(range_value):
                chunk_values.append(range_value / std_value)
        if chunk_values:
            mean_rs = float(np.mean(chunk_values))
            if mean_rs > 0.0 and np.isfinite(mean_rs):
                rs_values.append((window_size, mean_rs))

    if len(rs_values) < 2:
        return float("nan")

    log_windows = np.log(np.asarray([entry[0] for entry in rs_values], dtype=np.float64))
    log_rs = np.log(np.asarray([entry[1] for entry in rs_values], dtype=np.float64))
    if not np.isfinite(log_windows).all() or not np.isfinite(log_rs).all():
        return float("nan")

    slope, _ = np.polyfit(log_windows, log_rs, 1)
    if not np.isfinite(slope):
        return float("nan")
    return float(slope)


def get_weights_ffd_values(d_value: float, threshold: float = 1e-5, max_width: int = 0) -> np.ndarray:
    """Return fixed-width fractional differencing weights as a numpy array."""

    weights = [1.0]
    coefficient_index = 1
    while True:
        next_weight = -weights[-1] * (float(d_value) - coefficient_index + 1) / coefficient_index
        if abs(next_weight) < threshold:
            break
        if max_width > 0 and len(weights) >= max_width:
            break
        weights.append(next_weight)
        coefficient_index += 1
    return np.asarray(weights[::-1], dtype=np.float64)


def fractional_difference_values(
    series: np.ndarray,
    d_value: float,
    *,
    threshold: float = 1e-5,
    max_width: int = 0,
) -> np.ndarray:
    """Fixed-width fractional differencing that preserves initial NaN warmup."""

    values = np.asarray(series, dtype=np.float64)
    weights = get_weights_ffd_values(d_value, threshold=threshold, max_width=max_width)
    width = int(weights.size)
    output = np.full(values.shape[0], np.nan, dtype=np.float64)

    finite_mask = np.isfinite(values)
    if int(finite_mask.sum()) < width:
        return output

    first_valid = int(np.argmax(finite_mask))
    valid_slice = values[first_valid:].astype(np.float64, copy=True)
    finite_slice_mask = np.isfinite(valid_slice)
    if int(finite_slice_mask.sum()) < width:
        return output

    positions = np.arange(valid_slice.size)
    last_valid_positions = np.maximum.accumulate(np.where(finite_slice_mask, positions, 0))
    filled_slice = valid_slice[last_valid_positions]

    if filled_slice.size < width:
        return output

    convolution = _convolve_1d(filled_slice, weights)
    output_start = first_valid + width - 1
    output[output_start : first_valid + filled_slice.size] = convolution
    return output


def _default_fracdiff_fn(series: np.ndarray, d_value: float) -> np.ndarray:
    return fractional_difference_values(series, d_value)


def _finite_values(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    return array[np.isfinite(array)]


def _evaluate_adf_pvalue(
    values: np.ndarray,
    d_value: float,
    *,
    adf_fn: AdfFunction,
    fracdiff_fn: FracDiffFunction,
    min_adf_observations: int,
    pvalue_cache: Dict[float, float],
) -> float:
    cache_key = round(float(d_value), 8)
    cached = pvalue_cache.get(cache_key)
    if cached is not None:
        return cached

    fracdiff_values = fracdiff_fn(values, float(d_value))
    clean_values = _finite_values(fracdiff_values)
    if clean_values.size < min_adf_observations:
        pvalue = float("inf")
    else:
        try:
            pvalue = float(adf_fn(clean_values))
        except Exception:
            pvalue = float("inf")
    pvalue_cache[cache_key] = pvalue
    return pvalue


def find_min_d_full_bisection(
    series: np.ndarray,
    *,
    precision: float,
    adf_threshold: float,
    adf_fn: AdfFunction,
    fracdiff_fn: Optional[FracDiffFunction] = None,
    d_range: Tuple[float, float] = (0.0, 1.0),
    min_adf_observations: int = 20,
    pvalue_cache: Optional[Dict[float, float]] = None,
) -> float:
    """Full [left, right] binary d* search used as the safe fallback path."""

    values = np.asarray(series, dtype=np.float64)
    left = float(d_range[0])
    right = float(d_range[1])
    best = right
    effective_precision = max(float(precision), 1e-9)
    pvalues = pvalue_cache if pvalue_cache is not None else {}
    differencer = fracdiff_fn or _default_fracdiff_fn

    while right - left > effective_precision:
        midpoint = (left + right) / 2.0
        pvalue = _evaluate_adf_pvalue(
            values,
            midpoint,
            adf_fn=adf_fn,
            fracdiff_fn=differencer,
            min_adf_observations=min_adf_observations,
            pvalue_cache=pvalues,
        )
        if pvalue <= adf_threshold:
            best = midpoint
            right = midpoint
        else:
            left = midpoint

    return round(float(best), 4)


def find_min_d_with_prior(
    series: np.ndarray,
    *,
    precision: float,
    adf_threshold: float,
    adf_fn: AdfFunction,
    fracdiff_fn: Optional[FracDiffFunction] = None,
    full_search_fn: Optional[FullSearchFunction] = None,
    d_range: Tuple[float, float] = (0.0, 1.0),
    min_adf_observations: int = 20,
) -> float:
    """Find d* using Hurst only as a bounded-search prior, never as a decision."""

    values = np.asarray(series, dtype=np.float64)
    clean_values = _finite_values(values)
    effective_precision = max(float(precision), 1e-9)
    differencer = fracdiff_fn or _default_fracdiff_fn
    pvalue_cache: Dict[float, float] = {}

    def fallback_full_search() -> float:
        if full_search_fn is not None:
            return float(full_search_fn())
        return find_min_d_full_bisection(
            values,
            precision=effective_precision,
            adf_threshold=adf_threshold,
            adf_fn=adf_fn,
            fracdiff_fn=differencer,
            d_range=d_range,
            min_adf_observations=min_adf_observations,
            pvalue_cache=pvalue_cache,
        )

    if clean_values.size < 100:
        return fallback_full_search()

    hurst_value = estimate_hurst_rs(clean_values)
    if not np.isfinite(hurst_value) or hurst_value < 0.0 or hurst_value > 1.0:
        return fallback_full_search()

    left = float(d_range[0])
    right = float(d_range[1])
    if right <= left:
        return round(right, 4)

    p_left = _evaluate_adf_pvalue(
        values,
        left,
        adf_fn=adf_fn,
        fracdiff_fn=differencer,
        min_adf_observations=min_adf_observations,
        pvalue_cache=pvalue_cache,
    )
    if p_left <= adf_threshold:
        return round(left, 4)

    p_right = _evaluate_adf_pvalue(
        values,
        right,
        adf_fn=adf_fn,
        fracdiff_fn=differencer,
        min_adf_observations=min_adf_observations,
        pvalue_cache=pvalue_cache,
    )
    if p_right > adf_threshold:
        return fallback_full_search()

    predicted_d = hurst_value - 0.5
    prior_left = max(left, predicted_d - 0.2)
    prior_right = min(right, predicted_d + 0.2)
    if prior_right <= prior_left:
        return fallback_full_search()

    p_prior_left = _evaluate_adf_pvalue(
        values,
        prior_left,
        adf_fn=adf_fn,
        fracdiff_fn=differencer,
        min_adf_observations=min_adf_observations,
        pvalue_cache=pvalue_cache,
    )
    p_prior_right = _evaluate_adf_pvalue(
        values,
        prior_right,
        adf_fn=adf_fn,
        fracdiff_fn=differencer,
        min_adf_observations=min_adf_observations,
        pvalue_cache=pvalue_cache,
    )
    if p_prior_right > adf_threshold:
        return fallback_full_search()

    if p_prior_left <= adf_threshold:
        search_left = left
        search_right = prior_left
    else:
        search_left = prior_left
        search_right = prior_right

    while search_right - search_left > effective_precision:
        midpoint = (search_left + search_right) / 2.0
        p_midpoint = _evaluate_adf_pvalue(
            values,
            midpoint,
            adf_fn=adf_fn,
            fracdiff_fn=differencer,
            min_adf_observations=min_adf_observations,
            pvalue_cache=pvalue_cache,
        )
        if p_midpoint <= adf_threshold:
            search_right = midpoint
        else:
            search_left = midpoint

    return round(float(search_right), 4)


def compare_hurst_estimators(
    samples: List[np.ndarray],
    reference_estimators: Optional[Sequence[Callable[[np.ndarray], float]]] = None,
) -> Dict[str, float]:
    """Compare this lightweight prior against explicit reference estimators.

    Without externally supplied Mansukhani R/S or DFA references, the review gate
    remains blocked-not-pass by design.
    """

    if not reference_estimators:
        return {
            "sample_count": float(len(samples)),
            "reference_count": 0.0,
            "blocked_not_pass": 1.0,
        }

    deltas: List[float] = []
    bucket_matches = 0
    comparable_count = 0
    for sample in samples:
        candidate = estimate_hurst_rs(sample)
        references = [float(reference(sample)) for reference in reference_estimators]
        references = [value for value in references if np.isfinite(value)]
        if not np.isfinite(candidate) or not references:
            continue
        reference_value = float(np.mean(references))
        deltas.append(abs(candidate - reference_value))
        bucket_matches += int(_hurst_bucket(candidate) == _hurst_bucket(reference_value))
        comparable_count += 1

    if not deltas:
        return {
            "sample_count": float(len(samples)),
            "reference_count": float(len(reference_estimators)),
            "blocked_not_pass": 1.0,
        }

    return {
        "sample_count": float(len(samples)),
        "reference_count": float(len(reference_estimators)),
        "median_abs_delta_h_vs_reference": float(np.median(deltas)),
        "p95_abs_delta_h_vs_reference": float(np.percentile(deltas, 95)),
        "d_prior_bucket_agreement": float(bucket_matches / max(comparable_count, 1)),
        "blocked_not_pass": 0.0,
    }


def _hurst_bucket(value: float) -> str:
    if value < 0.45:
        return "mean_reverting"
    if value > 0.55:
        return "persistent"
    return "neutral"
