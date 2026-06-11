from types import SimpleNamespace

import numpy as np
import pandas as pd

from momentum.FeatureEngineering.feature_config import AlignmentMode
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator

from tests._helpers.stub_layer_execute import (
    stub_execute_layer1_6,
    stub_layer_data,
    stub_spill_to_memmap,
)


class _Timeframes:
    primary = "12h"
    training = ["12h", "1h"]
    alignment_mode = AlignmentMode.OPEN_MINUS


class _Config:
    timeframes = _Timeframes()

    class preprocessing:
        enabled = False


class _FactoryStub:
    def __init__(self, data_by_tf):
        self._data_by_tf = data_by_tf

    def _layer0_data_ingestion(self, symbol, timeframe, config, start_date=None, end_date=None):
        del symbol, config, start_date, end_date
        if timeframe not in self._data_by_tf:
            raise FileNotFoundError(timeframe)
        return self._data_by_tf[timeframe]

    def _execute_layer1_6(self, layer_name, func, *args):
        del layer_name
        return stub_execute_layer1_6(func, *args)

    _spill_to_memmap = staticmethod(stub_spill_to_memmap)
    layer_data = stub_layer_data

    def _layer1_atomic_indicators(self, data, config):
        del config
        return pd.DataFrame(
            {
                "close_trend_EMA_21": data["value"].astype(float).values,
                "close_momentum_RSI_14": data["value"].astype(float).values * 0.1,
            },
            index=data["timestamp"],
        )

    def _layer2_derived_features(self, layer1, data, config):
        del data, config
        return pd.DataFrame(
            {"close_ratio": layer1.iloc[:, 0] / (layer1.iloc[:, 1] + 1e-6)},
            index=layer1.index,
        )

    def _layer3_rolling_aggregation(self, layer1, layer2, config):
        del layer2, config
        return pd.DataFrame(
            {"close_roll_mean": layer1.iloc[:, 0].rolling(3, min_periods=1).mean()},
            index=layer1.index,
        )

    def _layer4_lag_features(self, layer1, layer2, layer3, data, config):
        del layer1, layer2, layer3, data, config
        return pd.DataFrame()

    def _layer5_cross_sectional(self, layer1, layer2, config):
        del layer1, layer2, config
        return pd.DataFrame()

    def _layer6_meta_features(self, layer1, layer2, data, config):
        del layer1, layer2, data, config
        return pd.DataFrame()

    def _layer6_5_preprocessing(self, all_features, config):
        del config
        return all_features

    def _combine_layers(self, layers, context="unknown"):
        del context
        valid_layers = [layer for layer in layers if layer is not None and not layer.empty]
        if not valid_layers:
            return pd.DataFrame()
        combined = pd.concat(valid_layers, axis=1)
        if combined.columns.has_duplicates:
            combined = combined.loc[:, ~combined.columns.duplicated(keep="first")]
        return combined

    def _compute_config_hash(self, config, symbol=None, timeframe=None, start_date=None, end_date=None):
        del config, symbol, timeframe, start_date, end_date
        return "dummy_hash"

    def _layer7_validate_and_persist(self, symbol, timeframe, raw_data, layers, config, elapsed, config_hash):
        del symbol, timeframe, config, elapsed, config_hash
        features_df = self._combine_layers(layers).reindex(raw_data.index)
        return SimpleNamespace(
            features_df=features_df,
            labels_df=pd.DataFrame(index=features_df.index),
            metadata={"layer_counts": {}, "skipped_timeframes": [], "actual_timeframes": []},
            feature_count=features_df.shape[1],
            generation_time=0.0,
            layer_counts={},
            config_used={},
        )


def _run_pipeline(use_searchsorted: bool, monkeypatch) -> pd.DataFrame:
    monkeypatch.setenv("FFACT_USE_SEARCHSORTED", "1" if use_searchsorted else "0")

    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000, 36 * 3600 * 1000]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": [10, 11, 12, 13]})
    hourly_ts = [i * 3600 * 1000 for i in range(37)]
    hourly_data = pd.DataFrame({"timestamp": hourly_ts, "value": list(range(37))})

    factory = _FactoryStub({"12h": primary_data, "1h": hourly_data})
    generator = MultiTFGenerator(factory, _Config())
    result = generator.generate_multi_tf("BTCUSDT")
    return result.features_df


def test_multi_tf_golden_output_equivalence(monkeypatch):
    """T1.7: 多時間框完整輸出在 searchsorted/merge_asof 下應等價。"""
    golden_df = _run_pipeline(use_searchsorted=False, monkeypatch=monkeypatch)
    searchsorted_df = _run_pipeline(use_searchsorted=True, monkeypatch=monkeypatch)

    assert list(searchsorted_df.columns) == list(golden_df.columns)
    np.testing.assert_allclose(
        searchsorted_df.to_numpy(dtype=np.float64),
        golden_df.to_numpy(dtype=np.float64),
        atol=1e-6,
        equal_nan=True,
    )