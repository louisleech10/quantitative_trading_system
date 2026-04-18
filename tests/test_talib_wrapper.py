from functools import lru_cache

import pandas as pd
import pytest

from momentum.factories import create_kline_storage_manager
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper


TEST_KLINE_CACHE_DIR = "data_cache/feature_klines"


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
    pytest.skip("missing market data for TA-Lib wrapper tests")


def load_test_data() -> pd.DataFrame:
    symbol, timeframe = _resolve_test_target()
    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    df = storage.read_klines(symbol, timeframe, validate_continuity=False)
    assert df is not None and not df.empty
    return df


def test_indicator_registry_count():
    TALibWrapper.initialize()
    assert len(TALibWrapper.INDICATOR_REGISTRY) == 132


def test_single_series_multi_source():
    TALibWrapper.initialize()
    df = load_test_data()
    result_close = TALibWrapper.compute("RSI", df, {"timeperiod": 14}, "close")
    result_volume = TALibWrapper.compute("RSI", df, {"timeperiod": 14}, "volume")

    assert "close_momentum_RSI_14" in result_close.columns
    assert "volume_momentum_RSI_14" in result_volume.columns
    assert not result_close.iloc[50:].equals(result_volume.iloc[50:])


def test_macd_output_count():
    TALibWrapper.initialize()
    df = load_test_data()
    result = TALibWrapper.compute(
        "MACD", df, {"fastperiod": 12, "slowperiod": 26, "signalperiod": 9}, "close"
    )
    assert result.shape[1] == 3


def test_hlc_input_indicator():
    TALibWrapper.initialize()
    df = load_test_data()
    result = TALibWrapper.compute("ADX", df, {"timeperiod": 14}, "close")
    assert result.shape[1] == 1


def test_pattern_recognition():
    df = load_test_data()
    result = TALibWrapper.compute("CDLHAMMER", df, {}, "close")
    values = result.iloc[:, 0].dropna().unique()
    assert set(values).issubset({-100, 0, 100})
