from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from momentum.FeatureEngineering.preprocessing._d_star_cache import DStarCache, PreprocessingContext


BASE_CONTEXT = PreprocessingContext(
    symbol="ETHUSDT",
    timeframe="1h",
    config_hash="c" * 32,
    data_fingerprint="fingerprint-v1",
    feature_schema_hash="schema-v1",
    time_range=(1, 100),
    row_count=100,
    source_data_version="test",
)


def _cache(
    cache_dir: Path,
    context: PreprocessingContext = BASE_CONTEXT,
    *,
    sample_size: int = 500,
    nan_policy: str = "dropna",
) -> DStarCache:
    return DStarCache(
        context,
        cache_dir,
        adf_threshold=0.1,
        precision=0.02,
        max_lag=64,
        weight_threshold=1e-5,
        sample_size=sample_size,
        nan_policy=nan_policy,
    )


def test_d_star_stale_invalidation_for_context_fields(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.set("L1_close", 0.4)
    cache.flush_atomic()

    assert _cache(tmp_path).get("L1_close") == 0.4
    assert _cache(tmp_path, replace(BASE_CONTEXT, data_fingerprint="fingerprint-v2")).get("L1_close") is None
    assert _cache(tmp_path, replace(BASE_CONTEXT, feature_schema_hash="schema-v2")).get("L1_close") == 0.4


def test_d_star_stale_invalidation_for_selection_fields(tmp_path: Path) -> None:
    cache = _cache(tmp_path, sample_size=500, nan_policy="dropna")
    cache.set("L1_close", 0.4)
    cache.flush_atomic()

    assert _cache(tmp_path, sample_size=250, nan_policy="dropna").get("L1_close") is None
    assert _cache(tmp_path, sample_size=500, nan_policy="keepna").get("L1_close") is None
