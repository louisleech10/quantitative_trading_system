import numpy as np
import pandas as pd
import pytest
from functools import lru_cache

from momentum.factories import create_kline_storage_manager
from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter
from momentum.FeatureEngineering.atomic.parameter_generator import ParameterGenerator
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper
from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine
from momentum.FeatureEngineering.operators.lag_processor import LagProcessor
from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator
from momentum.FeatureEngineering.feature_naming import tscorr_op


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
    pytest.fail("missing market data for feature factory operator tests")


def _load_market_data():
    symbol, timeframe = _resolve_test_target()
    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    adapter = CryptoSpotAdapter(storage, validate_continuity=False)
    return adapter.fetch(symbol, timeframe)


def test_derived_operators_distance_cross_ratio_momentum_binary():
    raw = _load_market_data()
    TALibWrapper.initialize()

    ema_8 = TALibWrapper.compute("EMA", raw, {"timeperiod": 8}, "close")
    ema_21 = TALibWrapper.compute("EMA", raw, {"timeperiod": 21}, "close")
    ema_40 = TALibWrapper.compute("EMA", raw, {"timeperiod": 40}, "close")
    rsi_14 = TALibWrapper.compute("RSI", raw, {"timeperiod": 14}, "close")

    layer1 = pd.concat([ema_8, ema_21, ema_40, rsi_14], axis=1)

    config = ConfigManager().get_merged_config().operators
    engine = DerivedOperatorEngine(config)
    derived = engine.compute_all(layer1, raw)

    distance_col = "close_trend_EMA_21_Distance"
    cross_col = "close_trend_EMA_8~40_Cross"  # FF-NAME：配對雙成員以 `~` 分隔
    ratio_col = "close_trend_EMA_8~40_Ratio"
    momentum_col = "close_momentum_RSI_14_Momentum-L3"
    binary_overbought = "close_momentum_RSI_14_BinarySignal-Overbought"
    binary_oversold = "close_momentum_RSI_14_BinarySignal-Oversold"

    assert distance_col in derived.columns
    assert cross_col in derived.columns
    assert ratio_col in derived.columns
    assert momentum_col in derived.columns
    assert binary_overbought in derived.columns
    assert binary_oversold in derived.columns

    # FFSTAT v53：比值類分母之近零尺度取前 252 列（因果），分母首個有限值起未滿窗之列為 NaN ⇒ 公式比對取窗滿後之列，
    # 並斷言窗未滿之列為 NaN（改前以全欄中位數為尺度＝未來洩漏）
    from momentum.FeatureEngineering.utils.numeric_guards import DEFAULT_DENOM_SCALE_WINDOW

    assert np.isnan(derived[distance_col].iloc[50]) and np.isnan(derived[ratio_col].iloc[50])
    idx = 40 + DEFAULT_DENOM_SCALE_WINDOW + 10
    assert len(raw) > idx
    ema21_series = ema_21.iloc[:, 0]
    ema8_series = ema_8.iloc[:, 0]
    ema40_series = ema_40.iloc[:, 0]
    rsi_series = rsi_14.iloc[:, 0]

    expected_distance = (raw["close"].iloc[idx] - ema21_series.iloc[idx]) / ema21_series.iloc[idx]
    assert np.isclose(derived[distance_col].iloc[idx], expected_distance, equal_nan=True)

    expected_cross = ema8_series.iloc[idx] - ema40_series.iloc[idx]
    expected_ratio = ema8_series.iloc[idx] / ema40_series.iloc[idx]
    assert np.isclose(derived[cross_col].iloc[idx], expected_cross, equal_nan=True)
    assert np.isclose(derived[ratio_col].iloc[idx], expected_ratio, equal_nan=True)

    expected_momentum = (rsi_series.iloc[idx] - rsi_series.iloc[idx - 3]) / rsi_series.iloc[idx - 3]
    assert np.isclose(derived[momentum_col].iloc[idx], expected_momentum, equal_nan=True)

    assert set(derived[binary_overbought].dropna().unique()).issubset({0, 1})
    assert set(derived[binary_oversold].dropna().unique()).issubset({0, 1})


def test_rolling_aggregator_slope_rank_zscore():
    raw = _load_market_data()
    features = raw[["close"]].copy()

    agg = RollingAggregator({"windows": [5], "aggregators": ["slope", "rank", "zscore"]})
    rolled = agg.compute_all(features)

    slope_col = "close_Slope-W5"  # FF-NAME：L3 op 段 `<Agg>-W<w>`
    rank_col = "close_Rank-W5"
    zscore_col = "close_ZScore-W5"

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
    assert np.isclose(rolled[slope_col].iloc[idx], expected_slope, equal_nan=True, atol=1e-2)

    assert 0.0 <= rolled[rank_col].iloc[idx] <= 1.0
    mean = values.mean()
    std = values.std(ddof=1)
    expected_zscore = (values[-1] - mean) / std if std != 0 else np.nan
    assert np.isclose(rolled[zscore_col].iloc[idx], expected_zscore, equal_nan=True, atol=1e-5)


@pytest.mark.xfail(
    strict=True,
    raises=ValueError,
    reason=(
        "生產缺陷：RollingAggregator 遇重複欄名時 features_df[chunk_cols] 每個重名各選出全部同名欄，"
        "產出欄數倍增超過預配置 memmap（rolling_aggregator.py:343 ValueError: could not broadcast "
        "(200,4) into (200,2)）；numba 路徑亦於 numba_rolling.py:263 typing 失敗後退回 pandas；"
        "見 白話說明/還沒做的事.md"
    ),
)
def test_rolling_aggregator_handles_duplicate_columns():
    # 非線性（隨機漫步，固定種子）且列數足夠：線性輸入之 slope 為常數、20 列有效樣本不足，
    # 兩者皆會被 L3 死欄過濾合法剔除（唯一欄名亦得 0 欄），無法驗到「重複欄名」本身。
    rng = np.random.default_rng(0)
    base = pd.Series(np.cumsum(rng.normal(size=200)))
    features = pd.concat([base.rename("dup"), (base * 2).rename("dup")], axis=1)

    agg = RollingAggregator({"windows": [5], "aggregators": ["slope"]})
    rolled = agg.compute_all(features)

    assert rolled.shape[1] >= 2
    assert all(col == "dup_Slope-W5" for col in rolled.columns)
    assert np.isfinite(rolled.iloc[-1, 0])
    assert np.isfinite(rolled.iloc[-1, 1])


def test_talib_wrapper_midpoint_registered_and_computable():
    raw = _load_market_data()
    TALibWrapper.initialize()

    result = TALibWrapper.compute("MIDPOINT", raw, {"timeperiod": 14}, "close")

    assert "close_trend_MIDPOINT_14" in result.columns
    assert result.iloc[20:, 0].notna().any()


def test_talib_wrapper_midprice_and_plus_dm_computable():
    raw = _load_market_data()
    TALibWrapper.initialize()

    midprice = TALibWrapper.compute("MIDPRICE", raw, {"timeperiod": 14}, "close")
    plus_dm = TALibWrapper.compute("PLUS_DM", raw, {"timeperiod": 14}, "close")

    assert "hl_trend_MIDPRICE_14" in midprice.columns
    assert "hl_momentum_PLUS-DM_14" in plus_dm.columns
    assert midprice.iloc[20:, 0].notna().any()
    assert plus_dm.iloc[20:, 0].notna().any()


def test_lag_processor_layer1_and_raw():
    raw = _load_market_data()
    ema_21 = TALibWrapper.compute("EMA", raw, {"timeperiod": 21}, "close")

    base = pd.concat([raw[["close"]], ema_21], axis=1)
    base["close_trend_EMA_21_Slope-W5"] = raw["close"].rolling(5).mean()  # FF-NAME 文法之 L3 欄

    config = ConfigManager().get_merged_config()
    processor = LagProcessor(config)
    # FF-NAME Task 3.2：layer1_and_raw 以呼叫端提供之來源層選欄（不讀欄名）
    column_layers = {"close": "raw", "close_trend_EMA_21_Slope-W5": "L3"}
    column_layers.update({str(c): "L1" for c in ema_21.columns})
    lagged = processor.compute_all(base, column_layers=column_layers)

    lag_steps = ParameterGenerator.generate_lag_sequence(
        config.global_settings.sequence_length,
        config.global_settings.max_lag_ratio,
        config.global_settings.lag_strategy,
        config.global_settings.custom_lags,
    )
    if config.global_settings.lag_strategy == "adaptive":
        max_lag = max(1, int(config.global_settings.sequence_length * config.global_settings.max_lag_ratio))
        lag_steps = sorted(set(lag_steps + [lag for lag in [1, 2, 3] if lag <= max_lag]))

    assert any(col.startswith("close_raw_value_Lag-") for col in lagged.columns)  # FF-NAME：raw lag 身分
    assert not any("Slope-W5_Lag" in col for col in lagged.columns)

    lag = lag_steps[0]
    lag_col = f"close_raw_value_Lag-{lag}"
    assert lag_col in lagged.columns
    idx = max(lag + 1, 10)
    assert np.isclose(lagged[lag_col].iloc[idx], raw["close"].iloc[idx - lag], equal_nan=True)


def test_derived_distance_handles_duplicate_raw_index():
    # FFSTAT v53：分母近零尺度需前 252 列（因果窗）⇒ fixture 延長至窗滿後，重複時間戳置於窗滿後之 ts=300
    from momentum.FeatureEngineering.utils.numeric_guards import DEFAULT_DENOM_SCALE_WINDOW

    n = DEFAULT_DENOM_SCALE_WINDOW + 60
    ts = list(range(1, n + 1))
    ema = [10.0 + 0.01 * i for i in range(n)]
    layer1 = pd.DataFrame({"close_trend_EMA_3": ema}, index=pd.Index(ts, name="ts"))
    closes = [e + 0.5 for e in ema]
    dup_at = ts.index(300)
    raw_data = pd.DataFrame(
        {"close": closes[: dup_at + 1] + [closes[dup_at] + 0.25] + closes[dup_at + 1:]},
        index=pd.Index(ts[: dup_at + 1] + [300] + ts[dup_at + 1:], name="ts"),
    )

    engine = DerivedOperatorEngine(
        {
            "distance": {"enabled": True, "apply_to": "all"},
            "cross": {"enabled": False},
            "ratio": {"enabled": False},
            "momentum": {"enabled": False},
            "binary_signal": {"enabled": False},
            "signed_strength": {"enabled": False},
            "worldquant": {"enabled": False},
        }
    )
    derived = engine.compute_all(layer1, raw_data)

    distance_col = "close_trend_EMA_3_Distance"
    assert distance_col in derived.columns
    assert derived.index.equals(layer1.index)
    last_close = closes[dup_at] + 0.25  # duplicate ts=300 should keep last raw value
    expected = (last_close - ema[dup_at]) / ema[dup_at]
    assert np.isfinite(derived.loc[300, distance_col])
    assert np.isclose(derived.loc[300, distance_col], expected)


def test_derived_worldquant_tscorr_handles_duplicate_corr_index():
    layer1 = pd.DataFrame(
        {"close_momentum_RSI_3": [1.0, 2.0, 3.0, 4.0]},
        index=pd.Index([1, 2, 3, 4], name="ts"),
    )
    raw_data = pd.DataFrame(
        {"close": [2.0, 2.2, 2.4, 2.6, 2.8]},
        index=pd.Index([1, 2, 2, 3, 4], name="ts"),
    )

    engine = DerivedOperatorEngine(
        {
            "distance": {"enabled": False},
            "cross": {"enabled": False},
            "ratio": {"enabled": False},
            "momentum": {"enabled": False},
            "binary_signal": {"enabled": False},
            "signed_strength": {"enabled": False},
            "worldquant": {
                "enabled": True,
                "apply_to": "all",
                "windows": [2],
                "operators": ["ts_corr"],
                "transforms": [],
                "corr_with": "close",
            },
        }
    )
    derived = engine.compute_all(layer1, raw_data)

    corr_col = f"close_momentum_RSI_3_{tscorr_op('close', 2)}"  # FF-NAME：TsCorr 嵌目標摘要
    assert corr_col in derived.columns
    assert derived.index.equals(layer1.index)
    assert derived[corr_col].notna().sum() >= 1
