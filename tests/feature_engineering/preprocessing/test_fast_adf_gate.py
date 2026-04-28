from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest
from statsmodels.tsa.stattools import adfuller

from momentum.FeatureEngineering.preprocessing._fast_adf_numba import adf_pvalue_fast
from momentum.FeatureEngineering.preprocessing._hurst_prior import (
    find_min_d_with_prior,
    fractional_difference_values,
)
from scripts.build_l65_golden import (
    DEFAULT_GOLDEN_DIR,
    KLINE_CACHE_PATH,
    _build_l1_l2_real_features,
    _load_hdf5_kline_frame,
)

SYMBOLS = ("ETHUSDT", "BTCUSDT", "BNBUSDT", "SOLUSDT")
TIMEFRAMES = ("1h", "12h")
WINDOW_SIZE = 500
WINDOW_STRIDE = 250
MAX_WINDOWS_PER_COLUMN = 3
MAX_GATE_SAMPLES = 1200
MIN_GATE_SAMPLES = 1000
ADF_THRESHOLD = 0.10
REPORT_PATH = DEFAULT_GOLDEN_DIR / "fast_adf_gate_report.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(".%s.%d.tmp" % (path.name, os.getpid()))
    try:
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _feature_kind(column: str) -> str:
    lowered = column.lower()
    if "rank" in lowered:
        return "rank"
    if "zscore" in lowered:
        return "zscore"
    if "return" in lowered or "change" in lowered:
        return "return"
    return "price_like"


def _layer(column: str) -> str:
    return column.split("_", 1)[0] if "_" in column else "unknown"


def _augment_l3_features(frame: pd.DataFrame) -> pd.DataFrame:
    numeric = frame.select_dtypes(include=[np.number]).copy()
    additions: Dict[str, pd.Series] = {}
    for column in list(numeric.columns)[:20]:
        series = numeric[column].astype(float)
        rolling_mean = series.rolling(50, min_periods=10).mean()
        rolling_std = series.rolling(50, min_periods=10).std()
        additions["L3_rank_%s" % column] = series.rank(pct=True)
        additions["L3_zscore_%s" % column] = (series - rolling_mean) / rolling_std.replace(0.0, np.nan)

    if not additions:
        return numeric
    augmented = pd.concat([numeric, pd.DataFrame(additions, index=frame.index)], axis=1)
    return augmented.replace([np.inf, -np.inf], np.nan)


def _load_gate_feature_frame(symbol: str, timeframe: str) -> pd.DataFrame:
    raw_frame = _load_hdf5_kline_frame(symbol, timeframe, KLINE_CACHE_PATH)
    if raw_frame is None:
        raise FileNotFoundError("missing HDF5 dataset %s/%s/data" % (symbol, timeframe))
    if len(raw_frame) < WINDOW_SIZE:
        raise ValueError("insufficient rows for %s/%s: %d" % (symbol, timeframe, len(raw_frame)))
    base_frame = _build_l1_l2_real_features(raw_frame.tail(2000), max_cols=80)
    return _augment_l3_features(base_frame)


def _windowed_values(values: np.ndarray) -> List[np.ndarray]:
    finite_values = np.asarray(values, dtype=np.float64)
    finite_values = finite_values[np.isfinite(finite_values)]
    if finite_values.size < WINDOW_SIZE:
        return []

    windows: List[np.ndarray] = []
    end_position = int(finite_values.size)
    while end_position >= WINDOW_SIZE and len(windows) < MAX_WINDOWS_PER_COLUMN:
        start_position = end_position - WINDOW_SIZE
        window = np.ascontiguousarray(finite_values[start_position:end_position], dtype=np.float64)
        if window.size == WINDOW_SIZE and np.isfinite(window).all():
            windows.append(window)
        end_position -= WINDOW_STRIDE
    return windows


def _downsample_samples(samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if len(samples) <= MAX_GATE_SAMPLES:
        return samples
    indices = np.linspace(0, len(samples) - 1, MAX_GATE_SAMPLES, dtype=int)
    return [samples[int(index)] for index in indices]


def collect_gate_samples() -> List[Dict[str, Any]]:
    samples: List[Dict[str, Any]] = []
    blockers: List[str] = []
    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            try:
                frame = _load_gate_feature_frame(symbol, timeframe)
            except (FileNotFoundError, ValueError) as error:
                blockers.append(str(error))
                continue

            for column in frame.columns:
                for window_index, window_values in enumerate(_windowed_values(frame[column].to_numpy())):
                    samples.append(
                        {
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "column": str(column),
                            "layer": _layer(str(column)),
                            "kind": _feature_kind(str(column)),
                            "window_index": window_index,
                            "values": window_values,
                        }
                    )

    if blockers:
        report = {
            "status": "BLOCKED",
            "generated_at_utc": _utc_now(),
            "sample_count": len(samples),
            "blockers": blockers,
        }
        _atomic_write_json(REPORT_PATH, report)
        pytest.skip("Fast ADF gate blocked by missing real data: %s" % "; ".join(blockers))

    samples = _downsample_samples(samples)
    if len(samples) < MIN_GATE_SAMPLES:
        report = {
            "status": "BLOCKED",
            "generated_at_utc": _utc_now(),
            "sample_count": len(samples),
            "required_sample_count": MIN_GATE_SAMPLES,
        }
        _atomic_write_json(REPORT_PATH, report)
        pytest.skip("Fast ADF gate blocked: sample size %d < %d" % (len(samples), MIN_GATE_SAMPLES))
    return samples


def _statsmodels_fixed_lag_pvalue(values: np.ndarray, lag: int = 0) -> float:
    sample = np.asarray(values, dtype=np.float64)
    sample = sample[np.isfinite(sample)]
    if sample.size < 20:
        return 1.0
    try:
        return float(adfuller(sample, maxlag=lag, regression="c", autolag=None)[1])
    except Exception:
        return 1.0


def _d_star(values: np.ndarray, *, use_fast: bool) -> float:
    def fracdiff_fn(raw_values: np.ndarray, d_value: float) -> np.ndarray:
        return fractional_difference_values(
            raw_values,
            d_value,
            threshold=1e-5,
            max_width=64,
        )

    def adf_fn(candidate_values: np.ndarray) -> float:
        if use_fast:
            return adf_pvalue_fast(candidate_values, lag=0, sample_size=WINDOW_SIZE)[0]
        return _statsmodels_fixed_lag_pvalue(candidate_values, lag=0)

    return find_min_d_with_prior(
        values,
        precision=0.05,
        adf_threshold=ADF_THRESHOLD,
        adf_fn=adf_fn,
        fracdiff_fn=fracdiff_fn,
        min_adf_observations=20,
    )


def _safe_corr(left_values: List[float], right_values: List[float]) -> float:
    left_array = np.asarray(left_values, dtype=np.float64)
    right_array = np.asarray(right_values, dtype=np.float64)
    if left_array.size == 0 or right_array.size == 0:
        return 0.0
    if np.allclose(left_array, right_array, atol=1e-12, rtol=1e-12):
        return 1.0
    if float(np.std(left_array)) == 0.0 or float(np.std(right_array)) == 0.0:
        return 0.0
    correlation = float(np.corrcoef(left_array, right_array)[0, 1])
    return correlation if np.isfinite(correlation) else 0.0


def evaluate_gate(samples: List[Dict[str, Any]]) -> Dict[str, float]:
    agreements: List[bool] = []
    d_star_diffs: List[float] = []
    d_star_fast_values: List[float] = []
    d_star_reference_values: List[float] = []
    threshold_band_violations = 0
    fallback_count = 0

    for sample in samples:
        values = np.asarray(sample["values"], dtype=np.float64)
        fast_pvalue, used_fallback = adf_pvalue_fast(values, lag=0, sample_size=WINDOW_SIZE)
        reference_pvalue = _statsmodels_fixed_lag_pvalue(values, lag=0)
        agreements.append((fast_pvalue <= ADF_THRESHOLD) == (reference_pvalue <= ADF_THRESHOLD))
        fallback_count += int(used_fallback)
        if 0.08 <= reference_pvalue <= 0.12 and not used_fallback:
            threshold_band_violations += 1

        fast_d_star = _d_star(values, use_fast=True)
        reference_d_star = _d_star(values, use_fast=False)
        d_star_fast_values.append(fast_d_star)
        d_star_reference_values.append(reference_d_star)
        d_star_diffs.append(abs(fast_d_star - reference_d_star))

    return {
        "classification_agreement": float(np.mean(agreements)),
        "d_star_median_diff": float(np.median(d_star_diffs)),
        "d_star_p95_diff": float(np.percentile(d_star_diffs, 95)),
        "threshold_band_violations": float(threshold_band_violations),
        "fallback_count": float(fallback_count),
        "final_dstar_corr_vs_baseline": _safe_corr(d_star_fast_values, d_star_reference_values),
        "sample_count": float(len(samples)),
    }


def _strata_counts(samples: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for sample in samples:
        key = "%s/%s/%s/%s" % (
            sample["symbol"],
            sample["timeframe"],
            sample["layer"],
            sample["kind"],
        )
        counts[key] = counts.get(key, 0) + 1
    return counts


def test_fast_adf_1000_sample_gate() -> None:
    samples = collect_gate_samples()
    metrics = evaluate_gate(samples)
    report: Dict[str, Any] = {
        "status": "PASS",
        "generated_at_utc": _utc_now(),
        "metrics": metrics,
        "strata_counts": _strata_counts(samples),
        "thresholds": {
            "classification_agreement_min": 0.99,
            "d_star_median_diff_max": 0.02,
            "d_star_p95_diff_max": 0.05,
            "threshold_band_violations_max": 0,
            "final_dstar_corr_vs_baseline_min": 0.99,
            "sample_count_min": MIN_GATE_SAMPLES,
        },
    }

    failures: List[str] = []
    if metrics["classification_agreement"] <= 0.99:
        failures.append("classification_agreement")
    if metrics["d_star_median_diff"] >= 0.02:
        failures.append("d_star_median_diff")
    if metrics["d_star_p95_diff"] >= 0.05:
        failures.append("d_star_p95_diff")
    if metrics["threshold_band_violations"] != 0.0:
        failures.append("threshold_band_violations")
    if metrics["final_dstar_corr_vs_baseline"] <= 0.99:
        failures.append("final_dstar_corr_vs_baseline")

    if failures:
        report["status"] = "FAIL"
        report["failures"] = failures
    _atomic_write_json(REPORT_PATH, report)

    assert failures == []
