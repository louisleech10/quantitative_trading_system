from __future__ import annotations

from pathlib import Path

from momentum.FeatureEngineering.preprocessing._d_star_cache import DStarCache, PreprocessingContext


def _context(symbol: str, timeframe: str = "1h") -> PreprocessingContext:
    return PreprocessingContext(
        symbol=symbol,
        timeframe=timeframe,
        config_hash="a" * 32,
        data_fingerprint=f"fingerprint-{symbol}-{timeframe}",
        feature_schema_hash="schema-v1",
        time_range=(1, 100),
        row_count=100,
        source_data_version="test",
    )


def _cache(cache_dir: Path, context: PreprocessingContext) -> DStarCache:
    return DStarCache(
        context,
        cache_dir,
        adf_threshold=0.1,
        precision=0.02,
        max_lag=64,
        weight_threshold=1e-5,
        sample_size=500,
        nan_policy="dropna",
    )


def test_d_star_isolation_between_symbols(tmp_path: Path) -> None:
    eth_cache = _cache(tmp_path, _context("ETHUSDT"))
    btc_cache = _cache(tmp_path, _context("BTCUSDT"))

    eth_cache.set("L1_close", 0.25)
    btc_cache.set("L1_close", 0.75)
    eth_cache.flush_atomic()
    btc_cache.flush_atomic()

    assert eth_cache.path != btc_cache.path
    assert _cache(tmp_path, _context("ETHUSDT")).get("L1_close") == 0.25
    assert _cache(tmp_path, _context("BTCUSDT")).get("L1_close") == 0.75


def test_d_star_isolation_between_timeframes(tmp_path: Path) -> None:
    cache_1h = _cache(tmp_path, _context("ETHUSDT", "1h"))
    cache_12h = _cache(tmp_path, _context("ETHUSDT", "12h"))

    cache_1h.set("L1_close", 0.2)
    cache_12h.set("L1_close", 0.8)
    cache_1h.flush_atomic()
    cache_12h.flush_atomic()

    assert cache_1h.path != cache_12h.path
    assert _cache(tmp_path, _context("ETHUSDT", "1h")).get("L1_close") == 0.2
    assert _cache(tmp_path, _context("ETHUSDT", "12h")).get("L1_close") == 0.8
