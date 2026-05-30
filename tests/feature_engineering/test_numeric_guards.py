"""Tests for Layer A2 (near-zero denominator guard) and Layer B (sanitization).

See plans/kind-questing-newell.md. Root cause: ratio-style operators divide by a
feature value; TA-Lib bounded oscillators return float-noise (~1e-14) near their
bounds, and the old exact-0 guard missed it → (v-ε)/ε → 1e14.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.utils.numeric_guards import (
    safe_denominator,
    sanitize_array_inplace,
    DEFAULT_DENOM_REL_EPS,
)


# ── Layer A2: safe_denominator ────────────────────────────────────────────────

def test_safe_denominator_nulls_exact_zero_and_float_noise():
    """Exact 0 and relative-near-zero (float noise) → NaN; real values kept."""
    # scale (median |nonzero|) ≈ 30 → threshold ≈ 3e-5
    s = pd.Series([0.5, 30.0, 0.0, -1.06e-14, 50.0, 0.3, 20.0])
    out = safe_denominator(s)
    assert np.isnan(out.iloc[2])  # exact 0
    assert np.isnan(out.iloc[3])  # 1e-14 float noise
    # genuine small/large values preserved
    for i in (0, 1, 4, 5, 6):
        assert out.iloc[i] == s.iloc[i]


def test_safe_denominator_prevents_momentum_explosion():
    """(v - shifted) / safe_denominator(shifted) must not explode on a bounded
    oscillator whose lagged value floats to ~1e-14."""
    # oscillator on 0..100 that dips to float-noise near 0
    rng = np.random.default_rng(0)
    v = np.abs(rng.standard_normal(500)) * 30.0
    v[100] = -1.06e-14  # TA-Lib-style noise at the bound
    v[300] = 9.47e-15
    s = pd.Series(v)
    mom = (s - s.shift(5)) / safe_denominator(s.shift(5))
    finite = mom.replace([np.inf, -np.inf], np.nan).dropna()
    assert (finite.abs() < 1e10).all(), "momentum exploded through near-zero denom"


def test_safe_denominator_scale_invariant():
    """A genuinely tiny-scale column keeps its tiny values (threshold scales down)."""
    s = pd.Series([1e-8, 2e-8, 3e-8, 5e-9, 1e-8])  # all genuine, scale ~1e-8
    out = safe_denominator(s)
    # none are float-noise relative to a 1e-8 scale → all preserved
    assert out.notna().all()


def test_safe_denominator_dataframe_per_column():
    """DataFrame path applies the threshold per-column."""
    df = pd.DataFrame({
        "osc": [30.0, 0.0, -1e-14, 50.0],     # scale ~40 → 1e-14 nulled
        "tiny": [1e-8, 2e-8, 3e-8, 4e-8],      # scale ~2.5e-8 → all kept
    })
    out = safe_denominator(df)
    assert np.isnan(out.loc[1, "osc"]) and np.isnan(out.loc[2, "osc"])
    assert out["tiny"].notna().all()


def test_safe_denominator_rel_eps_zero_is_exact_only():
    """rel_eps<=0 → backward-compatible exact-zero-only behaviour."""
    s = pd.Series([30.0, 0.0, -1e-14, 50.0])
    out = safe_denominator(s, rel_eps=0.0)
    assert np.isnan(out.iloc[1])       # exact 0 nulled
    assert out.iloc[2] == -1e-14       # near-zero NOT nulled


# ── Layer B: sanitize_array_inplace ───────────────────────────────────────────

def test_sanitize_nulls_inf_and_overcap():
    arr = np.array([[1.0, np.inf, 3e10], [-np.inf, 1e20, 2.0]], dtype=np.float64)
    n = sanitize_array_inplace(arr, finite_cap=1e18)
    assert n == 3  # +inf, -inf, 1e20
    assert np.isnan(arr[0, 1]) and np.isnan(arr[1, 0]) and np.isnan(arr[1, 1])
    # Class B real-but-large (3e10) is BELOW the cap → preserved
    assert arr[0, 2] == 3e10
    assert arr[1, 2] == 2.0


def test_sanitize_preserves_class_b_large_real_values():
    """Genuinely large real features (e.g. volume VAR ~3e10) must survive."""
    arr = np.array([[3.04e10, 1.5e11, 100.0]], dtype=np.float64)
    sanitize_array_inplace(arr, finite_cap=1e18)
    assert np.isfinite(arr).all()


def test_sanitize_cap_disabled_only_inf():
    arr = np.array([[np.inf, 1e30, 1.0]], dtype=np.float64)
    n = sanitize_array_inplace(arr, finite_cap=0.0)  # cap disabled
    assert n == 1  # only inf
    assert arr[0, 1] == 1e30  # over-cap value kept when cap disabled


def test_sanitize_empty_noop():
    arr = np.empty((0, 0), dtype=np.float64)
    assert sanitize_array_inplace(arr, finite_cap=1e18) == 0
