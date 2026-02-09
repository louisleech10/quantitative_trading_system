import numpy as np
import pandas as pd

from momentum.factories import create_kline_storage_manager
from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter
from momentum.FeatureEngineering.atomic.parameter_generator import ParameterGenerator
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper
from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine
from momentum.FeatureEngineering.operators.lag_processor import LagProcessor
from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator


def _load_btcusdt_12h():
    storage = create_kline_storage_manager()
    adapter = CryptoSpotAdapter(storage)
    return adapter.fetch("BTCUSDT", "12h")


def test_derived_operators_distance_cross_ratio_momentum_binary():
    raw = _load_btcusdt_12h()
    TALibWrapper.initialize()

    ema_8 = TALibWrapper.compute("EMA", raw, {"timeperiod": 8}, "close")
    ema_21 = TALibWrapper.compute("EMA", raw, {"timeperiod": 21}, "close")
    rsi_14 = TALibWrapper.compute("RSI", raw, {"timeperiod": 14}, "close")

    layer1 = pd.concat([ema_8, ema_21, rsi_14], axis=1)

    config = ConfigManager().get_merged_config().operators
    engine = DerivedOperatorEngine(config)
    derived = engine.compute_all(layer1, raw)

    distance_col = "close_trend_EMA_21_Distance"
    cross_col = "close_trend_EMA_8_21_Cross"
    ratio_col = "close_trend_EMA_8_21_Ratio"
    momentum_col = "close_momentum_RSI_14_Momentum_L3"
    binary_overbought = "close_momentum_RSI_14_BinarySignal_Overbought"
    binary_oversold = "close_momentum_RSI_14_BinarySignal_Oversold"

    assert distance_col in derived.columns
    assert cross_col in derived.columns
    assert ratio_col in derived.columns
    assert momentum_col in derived.columns
    assert binary_overbought in derived.columns
    assert binary_oversold in derived.columns

    idx = 50
    ema21_series = ema_21.iloc[:, 0]
    ema8_series = ema_8.iloc[:, 0]
    rsi_series = rsi_14.iloc[:, 0]

    expected_distance = (raw["close"].iloc[idx] - ema21_series.iloc[idx]) / ema21_series.iloc[idx]
    assert np.isclose(derived[distance_col].iloc[idx], expected_distance, equal_nan=True)

    expected_cross = ema8_series.iloc[idx] - ema21_series.iloc[idx]
    expected_ratio = ema8_series.iloc[idx] / ema21_series.iloc[idx]
    assert np.isclose(derived[cross_col].iloc[idx], expected_cross, equal_nan=True)
    assert np.isclose(derived[ratio_col].iloc[idx], expected_ratio, equal_nan=True)

    expected_momentum = (rsi_series.iloc[idx] - rsi_series.iloc[idx - 3]) / rsi_series.iloc[idx - 3]
    assert np.isclose(derived[momentum_col].iloc[idx], expected_momentum, equal_nan=True)

    assert set(derived[binary_overbought].dropna().unique()).issubset({0, 1})
    assert set(derived[binary_oversold].dropna().unique()).issubset({0, 1})


def test_rolling_aggregator_slope_rank_zscore():
    raw = _load_btcusdt_12h()
    features = raw[["close"]].copy()

    agg = RollingAggregator({"windows": [5], "aggregators": ["slope", "rank", "zscore"]})
    rolled = agg.compute_all(features)

    slope_col = "close_Slope_W5"
    rank_col = "close_Rank_W5"
    zscore_col = "close_ZScore_W5"

    assert slope_col in rolled.columns
    assert rank_col in rolled.columns
    assert zscore_col in rolled.columns

    idx = 10
    window = 5
    values = features["close"].iloc[idx - window + 1 : idx + 1].to_numpy()
    x = np.arange(window, dtype=float)
    sum_x = x.sum()
    sum_x2 = np.square(x).sum()
    denom = window * sum_x2 - sum_x ** 2
    expected_slope = (window * np.dot(x, values) - sum_x * values.sum()) / denom
    assert np.isclose(rolled[slope_col].iloc[idx], expected_slope, equal_nan=True)

    assert 0.0 <= rolled[rank_col].iloc[idx] <= 1.0
    mean = values.mean()
    std = values.std(ddof=1)
    expected_zscore = (values[-1] - mean) / std if std != 0 else np.nan
    assert np.isclose(rolled[zscore_col].iloc[idx], expected_zscore, equal_nan=True)


def test_lag_processor_layer1_and_raw():
    raw = _load_btcusdt_12h()
    ema_21 = TALibWrapper.compute("EMA", raw, {"timeperiod": 21}, "close")

    base = pd.concat([raw[["close"]], ema_21], axis=1)
    base["close_trend_EMA_21_Slope_W5"] = raw["close"].rolling(5).mean()

    config = ConfigManager().get_merged_config()
    processor = LagProcessor(config)
    lagged = processor.compute_all(base)

    lag_steps = ParameterGenerator.generate_lag_sequence(
        config.global_settings.sequence_length,
        config.global_settings.max_lag_ratio,
        config.global_settings.lag_strategy,
        config.global_settings.custom_lags,
    )
    if config.global_settings.lag_strategy == "adaptive":
        max_lag = max(1, int(config.global_settings.sequence_length * config.global_settings.max_lag_ratio))
        lag_steps = sorted(set(lag_steps + [lag for lag in [1, 2, 3] if lag <= max_lag]))

    assert any(col.startswith("close_Lag_") for col in lagged.columns)
    assert not any("Slope_W5_Lag" in col for col in lagged.columns)

    lag = lag_steps[0]
    lag_col = f"close_Lag_{lag}"
    assert lag_col in lagged.columns
    idx = max(lag + 1, 10)
    assert np.isclose(lagged[lag_col].iloc[idx], raw["close"].iloc[idx - lag], equal_nan=True)
