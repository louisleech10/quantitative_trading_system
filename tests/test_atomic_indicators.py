from momentum.factories import create_kline_storage_manager
from momentum.FeatureEngineering.atomic.trend_indicators import TrendIndicatorEngine
from momentum.FeatureEngineering.atomic.momentum_indicators import MomentumIndicatorEngine
from momentum.FeatureEngineering.atomic.volatility_indicators import VolatilityIndicatorEngine
from momentum.FeatureEngineering.atomic.volume_indicators import VolumeIndicatorEngine
from momentum.FeatureEngineering.atomic.pattern_indicators import PatternIndicatorEngine


def _load_data():
    storage = create_kline_storage_manager()
    df = storage.read_klines("BTCUSDT", "12h")
    assert df is not None
    return df


def test_trend_indicator_engine():
    df = _load_data()
    engine = TrendIndicatorEngine({"indicators": [{"name": "EMA", "periods": [21]}]}, ["close"])
    result = engine.compute_all(df)
    assert "close_trend_EMA_21" in result.columns


def test_momentum_indicator_engine():
    df = _load_data()
    engine = MomentumIndicatorEngine({"indicators": [{"name": "RSI", "periods": [14]}]}, ["close"])
    result = engine.compute_all(df)
    assert "close_momentum_RSI_14" in result.columns


def test_volatility_indicator_engine():
    df = _load_data()
    engine = VolatilityIndicatorEngine({"indicators": [{"name": "ATR", "periods": [14]}]}, ["close"])
    result = engine.compute_all(df)
    assert any("ATR_14" in col for col in result.columns)


def test_volume_indicator_engine():
    df = _load_data()
    engine = VolumeIndicatorEngine({"indicators": [{"name": "OBV"}]}, ["close"])
    result = engine.compute_all(df)
    assert any("OBV" in col for col in result.columns)


def test_pattern_indicator_engine():
    df = _load_data()
    engine = PatternIndicatorEngine({"indicators": [{"name": "CDLHAMMER"}]}, ["close"])
    result = engine.compute_all(df)
    assert any("CDLHAMMER" in col for col in result.columns)
