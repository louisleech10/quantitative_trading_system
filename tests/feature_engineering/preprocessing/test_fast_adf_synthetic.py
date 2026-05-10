from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import pytest
from statsmodels.tsa.stattools import adfuller

import momentum.FeatureEngineering.preprocessing.feature_preprocessor as fp_mod
import momentum.FeatureEngineering.preprocessing._fast_adf_numba as fast_adf
from momentum.FeatureEngineering.preprocessing._fast_adf_numba import adf_pvalue_fast
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from momentum.core.config import get_fast_adf_enabled


ADF_THRESHOLD = 0.10


def _ar1_series(rng: np.random.Generator, row_count: int, phi: float) -> np.ndarray:
    noise = rng.normal(0.0, 1.0, size=row_count)
    values = np.empty(row_count, dtype=np.float64)
    values[0] = noise[0]
    for row_index in range(1, row_count):
        values[row_index] = phi * values[row_index - 1] + noise[row_index]
    return values


def _random_walk_series(rng: np.random.Generator, row_count: int) -> np.ndarray:
    return np.cumsum(rng.normal(0.0, 1.0, size=row_count)).astype(np.float64)


def _statsmodels_fixed_lag_pvalue(
    values: np.ndarray,
    *,
    lag: Optional[int] = None,
    sample_size: int = 500,
) -> float:
    sample = np.asarray(values, dtype=np.float64)
    sample = sample[np.isfinite(sample)]
    if sample.size > sample_size:
        sample = sample[-sample_size:]
    if sample.size < fast_adf.MIN_ADF_OBSERVATIONS:
        return 1.0
    effective_lag = fast_adf._resolve_lag(int(sample.size), lag)
    try:
        return float(adfuller(sample, maxlag=effective_lag, regression="c", autolag=None)[1])
    except Exception:
        return 1.0


def test_fast_adf_synthetic_classification_matches_statsmodels() -> None:
    rng = np.random.default_rng(20260428)
    mismatches: List[int] = []
    samples: List[np.ndarray] = []

    for _ in range(50):
        samples.append(_ar1_series(rng, 640, phi=0.35))
    for _ in range(50):
        samples.append(_random_walk_series(rng, 640))

    for sample_index, sample in enumerate(samples):
        fast_pvalue, _ = adf_pvalue_fast(sample, lag=0)
        reference_pvalue = _statsmodels_fixed_lag_pvalue(sample, lag=0)
        if (fast_pvalue <= ADF_THRESHOLD) != (reference_pvalue <= ADF_THRESHOLD):
            mismatches.append(sample_index)

    assert mismatches == []


def test_fast_adf_singular_matrix_falls_back() -> None:
    pvalue, used_fallback = adf_pvalue_fast(np.ones(500, dtype=np.float64), lag=0)

    assert used_fallback is True
    assert pvalue == 1.0


def test_fast_adf_threshold_band_forces_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    sample = _ar1_series(np.random.default_rng(7), 500, phi=0.4)

    monkeypatch.setattr(fast_adf, "mackinnonp", lambda *args, **kwargs: 0.1)
    monkeypatch.setattr(
        fast_adf,
        "_adf_fallback_statsmodels",
        lambda *args, **kwargs: 0.03125,
    )

    pvalue, used_fallback = adf_pvalue_fast(sample, lag=0)

    assert used_fallback is True
    assert pvalue == 0.03125


def test_fast_adf_nan_series_falls_back() -> None:
    sample = _ar1_series(np.random.default_rng(17), 500, phi=0.4)
    sample[10] = np.nan

    pvalue, used_fallback = adf_pvalue_fast(sample, lag=0)

    assert used_fallback is True
    assert np.isfinite(pvalue)


def test_fast_adf_config_default_on(monkeypatch: pytest.MonkeyPatch) -> None:
    # Default is now ON ("1") — Numba JIT ADF enabled out of the box
    monkeypatch.delenv("FFACT_USE_FAST_ADF", raising=False)
    assert get_fast_adf_enabled() is True

    monkeypatch.setenv("FFACT_USE_FAST_ADF", "0")
    assert get_fast_adf_enabled() is False

    monkeypatch.setenv("FFACT_USE_FAST_ADF", "1")
    assert get_fast_adf_enabled() is True

    monkeypatch.setenv("FFACT_USE_FAST_ADF", "invalid")
    assert get_fast_adf_enabled() is True


def test_feature_preprocessor_uses_fast_adf_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"fast_adf": 0}

    def fake_fast_adf(
        values: np.ndarray,
        *,
        lag: Optional[int] = None,
        sample_size: int = 500,
    ) -> Tuple[float, bool]:
        del values, lag, sample_size
        calls["fast_adf"] += 1
        return 0.2, False

    monkeypatch.setenv("FFACT_USE_FAST_ADF", "1")
    monkeypatch.setattr(fp_mod, "HAS_STATSMODELS", True)
    monkeypatch.setattr(fp_mod, "adf_pvalue_fast", fake_fast_adf)

    frame = pd.DataFrame({"L1_alpha": np.arange(100.0)})
    preprocessor = FeaturePreprocessor(
        {"adf_differencing": {"adf_threshold": 0.1, "sample_size": 80}}
    )

    assert preprocessor._get_non_stationary_columns(frame) == ["L1_alpha"]
    assert calls["fast_adf"] == 1
