import numpy as np
import pytest
from functools import lru_cache

from momentum.factories import create_kline_storage_manager
from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter
from momentum.FeatureEngineering.adapters.adapter_registry import AdapterRegistry


TEST_KLINE_CACHE_DIR = "data_cache/feature_klines"

pytestmark = pytest.mark.requires_kline


@lru_cache(maxsize=1)
def _resolve_test_target() -> tuple[str, str]:
    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    candidates = [
        ("BTCUSDT", "12h"),
        ("ETHUSDT", "1h"),
        ("ETHUSDT", "12h"),
    ]
    for symbol, timeframe in candidates:
        try:
            df = storage.read_klines(symbol, timeframe, validate_continuity=False)
        except Exception:
            continue
        if df is not None and len(df) >= 100:
            return symbol, timeframe
    pytest.fail("missing market data for adapter tests")


def test_crypto_spot_fetch():
    symbol, timeframe = _resolve_test_target()
    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    adapter = CryptoSpotAdapter(storage, validate_continuity=False)
    df = adapter.fetch(symbol, timeframe)
    assert "close" in df.columns
    assert "taker_ratio" in df.columns
    assert len(df) > 100


def test_synthetic_sources():
    symbol, timeframe = _resolve_test_target()
    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    adapter = CryptoSpotAdapter(storage, validate_continuity=False)
    df = adapter.fetch(symbol, timeframe)

    row = df.iloc[0]
    expected_avg = (row["open"] + row["high"] + row["low"] + row["close"]) / 4.0
    expected_med = (row["high"] + row["low"]) / 2.0
    expected_typ = (row["high"] + row["low"] + row["close"]) / 3.0
    expected_wcl = (row["high"] + row["low"] + row["close"] + row["close"]) / 4.0

    assert np.isclose(row["avg-price"], expected_avg)
    assert np.isclose(row["med-price"], expected_med)
    assert np.isclose(row["typ-price"], expected_typ)
    assert np.isclose(row["wcl-price"], expected_wcl)


def test_adapter_registry():
    symbol, timeframe = _resolve_test_target()
    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    registry = AdapterRegistry()
    registry.register(CryptoSpotAdapter(storage, validate_continuity=False))
    assert "crypto_spot" in registry.list_all()
    aligned = registry.fetch_aligned(symbol, timeframe, ["close", "volume", "taker_ratio"])
    assert "close" in aligned.columns
    assert "volume" in aligned.columns
