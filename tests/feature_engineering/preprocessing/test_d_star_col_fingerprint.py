"""Tests for per-column value fingerprint behaviour in DStarCache v3.

These tests verify the core v3 invariant: a cache entry is reused if and only if
the column's actual numeric values are unchanged, regardless of whether other
context fields (feature_schema_hash, config_hash) have changed.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from momentum.FeatureEngineering.preprocessing._d_star_cache import (
    DStarCache,
    PreprocessingContext,
    _col_value_fingerprint,
    _strong_col_value_fingerprint,
)

BASE_CONTEXT = PreprocessingContext(
    symbol="ETHUSDT",
    timeframe="1h",
    config_hash="a" * 32,
    data_fingerprint="fp-v1",
    feature_schema_hash="schema-v1",
    time_range=(1, 200),
    row_count=200,
    source_data_version="test",
)

_COL_VALUES = np.linspace(100.0, 200.0, 200)
_COL_VALUES_CHANGED = np.linspace(100.0, 210.0, 200)  # different tail → different fp


def _cache(
    cache_dir: Path,
    context: PreprocessingContext = BASE_CONTEXT,
) -> DStarCache:
    return DStarCache(
        context,
        cache_dir,
        adf_threshold=0.05,
        precision=0.02,
        max_lag=64,
        weight_threshold=1e-5,
        sample_size=500,
        nan_policy="dropna",
    )


# ---------------------------------------------------------------------------
# col_value_fingerprint unit tests
# ---------------------------------------------------------------------------


def test_col_value_fingerprint_same_values_same_fp() -> None:
    arr = np.linspace(1.0, 100.0, 300)
    assert _col_value_fingerprint(arr) == _col_value_fingerprint(arr.copy())


def test_col_value_fingerprint_different_values_different_fp() -> None:
    arr1 = np.linspace(1.0, 100.0, 300)
    arr2 = np.linspace(1.0, 101.0, 300)
    assert _col_value_fingerprint(arr1) != _col_value_fingerprint(arr2)


def test_col_value_fingerprint_empty_returns_sentinel() -> None:
    assert _col_value_fingerprint(np.array([])) == "empty"


def test_strong_col_value_fingerprint_tracks_nan_mask() -> None:
    arr1 = np.array([1.0, np.nan, 3.0], dtype=np.float64)
    arr2 = np.array([1.0, 2.0, np.nan], dtype=np.float64)
    assert _strong_col_value_fingerprint(arr1) != _strong_col_value_fingerprint(arr2)


# ---------------------------------------------------------------------------
# Integration: col_values path — partial schema hit
# ---------------------------------------------------------------------------


def test_partial_schema_hit(tmp_path: Path) -> None:
    """Adding new features (feature_schema_hash changes) must NOT invalidate
    entries for columns whose values are unchanged.
    """
    cache1 = _cache(tmp_path, BASE_CONTEXT)
    cache1.set("col_A", 0.35, _COL_VALUES)
    cache1.flush_atomic()

    # Simulate schema growth: feature_schema_hash changed, values identical
    ctx_new_schema = replace(BASE_CONTEXT, feature_schema_hash="schema-v2")
    cache2 = _cache(tmp_path, ctx_new_schema)
    assert cache2.get("col_A", _COL_VALUES) == 0.35


def test_partial_config_hash_hit(tmp_path: Path) -> None:
    """Changing config_hash (e.g. adding L1 indicator) must NOT invalidate
    entries for columns whose values are unchanged.
    """
    cache1 = _cache(tmp_path, BASE_CONTEXT)
    cache1.set("col_B", 0.42, _COL_VALUES)
    cache1.flush_atomic()

    ctx_new_config = replace(BASE_CONTEXT, config_hash="b" * 32)
    cache2 = _cache(tmp_path, ctx_new_config)
    assert cache2.get("col_B", _COL_VALUES) == 0.42


# ---------------------------------------------------------------------------
# Integration: col_values path — value mismatch → miss
# ---------------------------------------------------------------------------


def test_col_values_mismatch_miss(tmp_path: Path) -> None:
    """If a column's values change, the cache must return None even when
    all other context fields are identical.
    """
    cache1 = _cache(tmp_path)
    cache1.set("col_A", 0.35, _COL_VALUES)
    cache1.flush_atomic()

    cache2 = _cache(tmp_path)
    assert cache2.get("col_A", _COL_VALUES_CHANGED) is None


def test_col_values_match_hit(tmp_path: Path) -> None:
    """Unchanged column values must produce a cache hit."""
    cache1 = _cache(tmp_path)
    cache1.set("col_A", 0.35, _COL_VALUES)
    cache1.flush_atomic()

    cache2 = _cache(tmp_path)
    assert cache2.get("col_A", _COL_VALUES) == 0.35


def test_exact_value_alias_hit_for_different_column_name(tmp_path: Path) -> None:
    """Identical values under a different name should reuse the same d-star."""
    cache1 = _cache(tmp_path)
    cache1.set("col_A", 0.35, _COL_VALUES)
    cache1.flush_atomic()

    cache2 = _cache(tmp_path)
    assert cache2.get("col_B", _COL_VALUES.copy()) == 0.35
    assert cache2.get("col_B", _COL_VALUES_CHANGED) is None


# ---------------------------------------------------------------------------
# Integration: fracdiff params change → different file → cold start
# ---------------------------------------------------------------------------


def test_fracdiff_params_change_miss(tmp_path: Path) -> None:
    """Changing fracdiff params (adf_threshold) produces a different file path
    and therefore a cold-start miss.
    """
    cache_a = DStarCache(
        BASE_CONTEXT, tmp_path,
        adf_threshold=0.05, precision=0.02, max_lag=64,
        weight_threshold=1e-5, sample_size=500, nan_policy="dropna",
    )
    cache_a.set("col_A", 0.35, _COL_VALUES)
    cache_a.flush_atomic()

    cache_b = DStarCache(
        BASE_CONTEXT, tmp_path,
        adf_threshold=0.10,  # changed
        precision=0.02, max_lag=64,
        weight_threshold=1e-5, sample_size=500, nan_policy="dropna",
    )
    assert cache_a.path != cache_b.path, "Different fracdiff params must produce different file paths"
    assert cache_b.get("col_A", _COL_VALUES) is None


# ---------------------------------------------------------------------------
# Backward compat: no col_values supplied → falls back to data_fingerprint
# ---------------------------------------------------------------------------


def test_backward_compat_data_fingerprint_miss(tmp_path: Path) -> None:
    """When col_values is not supplied, the old input_fingerprint check applies."""
    cache1 = _cache(tmp_path, BASE_CONTEXT)
    cache1.set("col_A", 0.35)  # no col_values → stores input_fingerprint
    cache1.flush_atomic()

    ctx_new_fp = replace(BASE_CONTEXT, data_fingerprint="fp-v2")
    cache2 = _cache(tmp_path, ctx_new_fp)
    assert cache2.get("col_A") is None  # data_fingerprint mismatch


def test_backward_compat_data_fingerprint_hit(tmp_path: Path) -> None:
    """Old-style set (no col_values) → hit when data_fingerprint is unchanged."""
    cache1 = _cache(tmp_path, BASE_CONTEXT)
    cache1.set("col_A", 0.35)
    cache1.flush_atomic()

    cache2 = _cache(tmp_path, BASE_CONTEXT)
    assert cache2.get("col_A") == 0.35
