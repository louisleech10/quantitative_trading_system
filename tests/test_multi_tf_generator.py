import pandas as pd

from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator


class DummyTimeframes:
    primary = "12h"
    training = ["12h", "1h"]


class DummyConfig:
    timeframes = DummyTimeframes()


class StubFactory:
    def __init__(self, data_by_tf):
        self._data_by_tf = data_by_tf

    def _layer0_data_ingestion(self, symbol, timeframe, config):
        return self._data_by_tf[timeframe]

    def _layer1_atomic_indicators(self, data, config):
        return pd.DataFrame(
            {"close_trend_EMA_21": data["value"].values},
            index=data["timestamp"],
        )

    def _layer2_derived_features(self, layer1, data, config):
        return pd.DataFrame()

    def _layer3_rolling_aggregation(self, layer1, layer2, config):
        return pd.DataFrame()

    def _layer4_lag_features(self, layer1, layer2, layer3, data, config):
        return pd.DataFrame()

    def _layer5_cross_sectional(self, layer1, layer2, config):
        return pd.DataFrame()

    def _layer6_meta_features(self, layer1, layer2, data, config):
        return pd.DataFrame()


def test_multi_tf_generator_aligns_and_tags():
    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": [10, 11, 12]})

    hourly_ts = [i * 3600 * 1000 for i in range(25)]
    hourly_data = pd.DataFrame({"timestamp": hourly_ts, "value": list(range(25))})

    factory = StubFactory({"12h": primary_data, "1h": hourly_data})
    generator = MultiTFGenerator(factory, DummyConfig())
    result = generator.generate_multi_tf("BTCUSDT")

    assert len(result) == 3
    assert "close_trend_EMA_21" in result.columns
    assert "close_1h_trend_EMA_21" in result.columns
    assert result["close_1h_trend_EMA_21"].iloc[1] == 12
