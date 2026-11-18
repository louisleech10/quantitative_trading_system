import numpy as np
import pandas as pd

from momentum.FeatureEngineering.feature_naming import build_identity, format_feature_name
from momentum.FeatureEngineering.meta_features.consensus_features import ConsensusFeatureEngine
from momentum.FeatureEngineering.meta_features.time_features import TimeFeatureEngine
from momentum.FeatureEngineering.meta_features.interaction_features import InteractionFeatureEngine


def _meta(indicator: str) -> str:
    """L6 meta 欄名（FF-NAME Task 2.4，docs/FFNAME_SPEC.md：`meta_<tf>_meta_<indicator>`，未標記週期形去第 2 段）：
    由產品 formatter 自身分（source＝meta、category＝meta、indicator＝SPEC 所列詞）導出，不寫死欄名字面。"""
    return format_feature_name(build_identity("meta", "meta", indicator))


def test_consensus_features_basic():
    index = pd.RangeIndex(5)
    layer1 = pd.DataFrame(
        {
            "close_trend_EMA_8": [1, 2, 3, 4, 5],
            "close_trend_EMA_21": [2, 2, 2, 2, 2],
            "close_momentum_MACD_Hist_12_26_9": [0.5, -0.1, 0.0, 0.3, -0.2],
            "hlc_momentum_ADX_14": [30, 10, 26, 20, 40],
        },
        index=index,
    )

    engine = ConsensusFeatureEngine()
    consensus = engine.compute_trend_consensus(layer1)
    assert consensus.name == _meta("trend-consensus")
    assert consensus.min() >= -1.0
    assert consensus.max() <= 1.0


def test_time_features():
    timestamps = pd.Series([0, 3600 * 1000, 2 * 3600 * 1000])
    engine = TimeFeatureEngine()
    result = engine.compute_all(timestamps)
    assert list(result.columns) == [
        _meta("time-hour-of-day"),
        _meta("time-day-of-week"),
        _meta("time-is-weekend"),
        _meta("time-month-of-year"),
    ]
    assert result[_meta("time-hour-of-day")].iloc[1] == 1


def test_interaction_features():
    index = pd.RangeIndex(4)
    layer1 = pd.DataFrame(
        {
            "close_trend_EMA_8": [1, 2, 3, 4],
            "close_trend_EMA_21": [1, 1, 1, 1],
            "close_momentum_RSI_14": [40, 50, 60, 70],
            "hlc_volatility_ATR_14": [1.0, 1.0, 1.0, 1.0],
        },
        index=index,
    )
    raw = pd.DataFrame(
        {
            "close": [1, 1.1, 1.2, 1.0],
            "volume": [10, 12, 11, 15],
        },
        index=index,
    )

    engine = InteractionFeatureEngine()
    result = engine.compute_all(layer1, raw)
    assert _meta("trend-momentum") in result.columns
    assert _meta("volatility-direction") in result.columns
    assert _meta("volume-price-change") in result.columns
