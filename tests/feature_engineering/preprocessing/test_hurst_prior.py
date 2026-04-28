from __future__ import annotations

from typing import List

import numpy as np
import pytest

import momentum.FeatureEngineering.preprocessing._hurst_prior as hurst_prior


def _series() -> np.ndarray:
    rng = np.random.default_rng(19)
    return np.cumsum(rng.normal(0.0, 1.0, size=180))


def test_hurst_prior_accelerates_with_bounded_search(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: List[float] = []

    def fracdiff_fn(values: np.ndarray, d_value: float) -> np.ndarray:
        return np.full(25, d_value, dtype=np.float64)

    def adf_fn(values: np.ndarray) -> float:
        d_value = float(values[0])
        calls.append(round(d_value, 8))
        return 0.2 if d_value < 0.3 else 0.01

    monkeypatch.setattr(hurst_prior, "estimate_hurst_rs", lambda values: 0.7)

    d_star = hurst_prior.find_min_d_with_prior(
        _series(),
        precision=0.1,
        adf_threshold=0.1,
        adf_fn=adf_fn,
        fracdiff_fn=fracdiff_fn,
        min_adf_observations=1,
    )

    assert abs(d_star - 0.3) < 1e-9
    assert len(set(calls)) <= 5


def test_hurst_prior_bounded_fail_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    fallback_called = {"value": False}

    def fracdiff_fn(values: np.ndarray, d_value: float) -> np.ndarray:
        return np.full(25, d_value, dtype=np.float64)

    def adf_fn(values: np.ndarray) -> float:
        d_value = float(values[0])
        return 0.2 if d_value < 0.8 else 0.01

    def full_search() -> float:
        fallback_called["value"] = True
        return 0.8125

    monkeypatch.setattr(hurst_prior, "estimate_hurst_rs", lambda values: 0.7)

    d_star = hurst_prior.find_min_d_with_prior(
        _series(),
        precision=0.1,
        adf_threshold=0.1,
        adf_fn=adf_fn,
        fracdiff_fn=fracdiff_fn,
        full_search_fn=full_search,
        min_adf_observations=1,
    )

    assert fallback_called["value"] is True
    assert d_star == 0.8125


def test_hurst_degenerate_falls_back_to_full_search() -> None:
    fallback_called = {"value": False}

    def full_search() -> float:
        fallback_called["value"] = True
        return 0.625

    d_star = hurst_prior.find_min_d_with_prior(
        np.ones(180, dtype=np.float64),
        precision=0.02,
        adf_threshold=0.1,
        adf_fn=lambda values: 0.01,
        full_search_fn=full_search,
    )

    assert fallback_called["value"] is True
    assert d_star == 0.625


def test_short_series_bypass_prior() -> None:
    fallback_called = {"value": False}

    def full_search() -> float:
        fallback_called["value"] = True
        return 0.75

    d_star = hurst_prior.find_min_d_with_prior(
        np.arange(50.0),
        precision=0.02,
        adf_threshold=0.1,
        adf_fn=lambda values: 0.01,
        full_search_fn=full_search,
    )

    assert fallback_called["value"] is True
    assert d_star == 0.75


def test_hurst_reference_gate_blocks_without_reference() -> None:
    report = hurst_prior.compare_hurst_estimators([_series()])

    assert report["blocked_not_pass"] == 1.0
    assert report["reference_count"] == 0.0
