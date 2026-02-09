import numpy as np

from momentum.factories import create_kline_storage_manager
from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter
from momentum.FeatureEngineering.adapters.adapter_registry import AdapterRegistry


def test_crypto_spot_fetch():
    storage = create_kline_storage_manager()
    adapter = CryptoSpotAdapter(storage)
    df = adapter.fetch("BTCUSDT", "12h")
    assert "close" in df.columns
    assert "taker_ratio" in df.columns
    assert len(df) > 100


def test_synthetic_sources():
    storage = create_kline_storage_manager()
    adapter = CryptoSpotAdapter(storage)
    df = adapter.fetch("BTCUSDT", "12h")

    row = df.iloc[0]
    expected_avg = (row["open"] + row["high"] + row["low"] + row["close"]) / 4.0
    expected_med = (row["high"] + row["low"]) / 2.0
    expected_typ = (row["high"] + row["low"] + row["close"]) / 3.0
    expected_wcl = (row["high"] + row["low"] + row["close"] + row["close"]) / 4.0

    assert np.isclose(row["avg_price"], expected_avg)
    assert np.isclose(row["med_price"], expected_med)
    assert np.isclose(row["typ_price"], expected_typ)
    assert np.isclose(row["wcl_price"], expected_wcl)


def test_adapter_registry():
    storage = create_kline_storage_manager()
    registry = AdapterRegistry()
    registry.register(CryptoSpotAdapter(storage))
    assert "crypto_spot" in registry.list_all()
    aligned = registry.fetch_aligned("BTCUSDT", "12h", ["close", "volume", "taker_ratio"])
    assert "close" in aligned.columns
    assert "volume" in aligned.columns
