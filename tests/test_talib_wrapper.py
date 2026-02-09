import pandas as pd

from momentum.factories import create_kline_storage_manager
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper


def load_test_data() -> pd.DataFrame:
    storage = create_kline_storage_manager()
    df = storage.read_klines("BTCUSDT", "12h")
    assert df is not None
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
