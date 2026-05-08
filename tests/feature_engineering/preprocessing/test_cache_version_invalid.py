from __future__ import annotations

import json
from pathlib import Path

from momentum.FeatureEngineering.preprocessing._d_star_cache import DStarCache, PreprocessingContext


def _context() -> PreprocessingContext:
    return PreprocessingContext(
        symbol="ETHUSDT",
        timeframe="1h",
        config_hash="d" * 32,
        data_fingerprint="fingerprint-v2",
        feature_schema_hash="schema-v2",
        time_range=(1, 100),
        row_count=100,
        source_data_version="test",
    )


def _cache(cache_dir: Path) -> DStarCache:
    return DStarCache(
        _context(),
        cache_dir,
        adf_threshold=0.1,
        precision=0.02,
        max_lag=64,
        weight_threshold=1e-5,
        sample_size=500,
        nan_policy="dropna",
    )


def test_cache_version_invalid_rebuilds_v2_payload(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.path.write_text(
        json.dumps(
            {
                "cache_version": "v1",
                "symbol": "ETHUSDT",
                "timeframe": "1h",
                "config_hash": "d" * 32,
                "entries": {"L1_close": {"d_star": 0.9}},
            }
        ),
        encoding="utf-8",
    )

    rebuilt_cache = _cache(tmp_path)
    assert rebuilt_cache.get("L1_close") is None

    rebuilt_cache.set("L1_close", 0.3)
    rebuilt_cache.flush_atomic()
    payload = json.loads(cache.path.read_text(encoding="utf-8"))

    assert payload["cache_version"] == "v3"
    assert payload["entries"]["L1_close"]["d_star"] == 0.3


def test_legacy_default_cache_is_not_direct_hit(tmp_path: Path) -> None:
    legacy_path = tmp_path / "d_star_default_default.json"
    legacy_path.write_text(json.dumps({"entries": {"L1_close": {"d_star": 0.9}}}), encoding="utf-8")

    cache = _cache(tmp_path)

    assert cache.path != legacy_path
    assert cache.get("L1_close") is None
