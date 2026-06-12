from types import SimpleNamespace

import numpy as np
import pandas as pd

from momentum.FeatureEngineering.feature_config import AlignmentMode
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

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
    def __init__(
        self,
        data_by_tf,
        primary_tf="12h",
        primary_shift_ms=0,
        include_nan=False,
        primary_column_names=None,
    ):
        self._data_by_tf = data_by_tf
        self._primary_tf = primary_tf
        self._primary_shift_ms = primary_shift_ms
        self._include_nan = include_nan
        self._primary_column_names = list(primary_column_names or ["close_trend_EMA_21"])
        self._active_tf = None

    def _layer0_data_ingestion(self, symbol, timeframe, config, start_date=None, end_date=None):
        del symbol, config, start_date, end_date
        self._active_tf = timeframe
        if timeframe not in self._data_by_tf:
            raise FileNotFoundError(timeframe)
        return self._data_by_tf[timeframe]

    def _execute_layer1_6(self, layer_name, func, *args):
        del layer_name
        return stub_execute_layer1_6(func, *args)

    def _execute_layer1_6_preserve_dtype(self, layer_name, func, *args):
        del layer_name
        return stub_execute_layer1_6(func, *args)

    _spill_to_memmap = staticmethod(stub_spill_to_memmap)
    layer_data = stub_layer_data

    def _layer1_atomic_indicators(self, data, config):
        del config
        index_values = data["timestamp"].astype(np.int64).to_numpy()
        if self._active_tf == self._primary_tf:
            index_values = index_values + np.int64(self._primary_shift_ms)

        payload = {}
        columns = self._primary_column_names if self._active_tf == self._primary_tf else ["close_trend_EMA_21"]
        for idx, name in enumerate(columns):
            values = data["value"].astype(float).to_numpy() + idx
            payload[name] = values

        out = pd.DataFrame(payload, index=index_values)
        if self._include_nan and self._active_tf == self._primary_tf and not out.empty:
            first_col = out.columns[0]
            if len(out.index) > 1:
                out.loc[out.index[1], first_col] = np.nan
        return out

    def _layer2_derived_features(self, layer1, data, config):
        del layer1, data, config
        return pd.DataFrame()

    def _layer3_rolling_aggregation(self, layer1, layer2, config):
        del layer1, layer2, config
        return pd.DataFrame()

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


def _manual_multi_tf(factory: _FactoryStub, config: _Config, symbol: str, use_skip: bool) -> pd.DataFrame:
    primary_raw = factory._layer0_data_ingestion(symbol, config.timeframes.primary, config)
    primary_timestamps = TimeframeAligner._to_datetime_index(primary_raw["timestamp"])
    primary_ts_ms = pd.Series(primary_timestamps.astype("int64") // 1_000_000)

    outputs = []
    for timeframe in config.timeframes.training:
        raw = primary_raw if timeframe == config.timeframes.primary else factory._layer0_data_ingestion(symbol, timeframe, config)
        layer1 = factory._layer1_atomic_indicators(raw, config)
        combined = factory._combine_layers([layer1])

        if use_skip and timeframe == config.timeframes.primary:
            aligned = combined.copy(deep=False)
            aligned.index = primary_timestamps
        else:
            aligned = TimeframeAligner.align_to_primary(
                source_df=combined,
                source_tf=timeframe,
                primary_timestamps=primary_ts_ms,
                primary_tf=config.timeframes.primary,
                alignment_mode=config.timeframes.alignment_mode,
            )

        aligned.attrs = {}
        aligned = MultiTFGenerator._apply_timeframe_tag(aligned, timeframe)
        outputs.append(aligned)

    merged = factory._combine_layers(outputs)
    if len(merged.index) == len(primary_raw.index):
        merged.index = primary_raw.index
    return merged


def test_primary_self_align_skip_produces_same_output(monkeypatch):
    """T1.6: self-align skip 與 no-skip 結果應一致。"""
    monkeypatch.setenv("FFACT_USE_SEARCHSORTED", "1")

    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": [10.0, 11.0, 12.0]})
    hourly_ts = [i * 3600 * 1000 for i in range(25)]
    hourly_data = pd.DataFrame({"timestamp": hourly_ts, "value": list(range(25))})

    factory = _FactoryStub({"12h": primary_data, "1h": hourly_data})
    config = _Config()

    skip_df = _manual_multi_tf(factory, config, "BTCUSDT", use_skip=True)
    no_skip_df = _manual_multi_tf(factory, config, "BTCUSDT", use_skip=False)

    assert list(skip_df.columns) == list(no_skip_df.columns)
    np.testing.assert_allclose(
        skip_df.to_numpy(dtype=np.float64),
        no_skip_df.to_numpy(dtype=np.float64),
        atol=1e-7,
        equal_nan=True,
    )


def test_self_align_skip_with_mismatched_index(monkeypatch):
    """T1.B11: primary layer index 值不同時，skip 分支仍需重設為 primary_timestamps。"""
    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": [1.0, 2.0, 3.0]})
    hourly_ts = [i * 3600 * 1000 for i in range(25)]
    hourly_data = pd.DataFrame({"timestamp": hourly_ts, "value": list(range(25))})

    factory = _FactoryStub(
        {"12h": primary_data, "1h": hourly_data},
        primary_shift_ms=60_000,
    )
    generator = MultiTFGenerator(factory, _Config())

    captured = {}
    original_apply_tag = MultiTFGenerator._apply_timeframe_tag

    def _spy_apply_tag(features_df, timeframe, registry=None):
        del registry
        if timeframe == "12h":
            captured["primary_index"] = features_df.index.copy()
        return original_apply_tag(features_df, timeframe)

    monkeypatch.setattr(MultiTFGenerator, "_apply_timeframe_tag", staticmethod(_spy_apply_tag))

    generator.generate_multi_tf("BTCUSDT")

    expected_index = pd.DatetimeIndex(pd.to_datetime(primary_data["timestamp"], unit="ms"))
    assert "primary_index" in captured
    assert isinstance(captured["primary_index"], pd.DatetimeIndex)
    pd.testing.assert_index_equal(captured["primary_index"], expected_index)


def test_self_align_skip_with_nan_in_combined(monkeypatch):
    """T1.B12: self-align skip 不可破壞 combined 內既有 NaN。"""
    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": [1.0, 2.0, 3.0]})
    hourly_ts = [i * 3600 * 1000 for i in range(25)]
    hourly_data = pd.DataFrame({"timestamp": hourly_ts, "value": list(range(25))})

    factory = _FactoryStub(
        {"12h": primary_data, "1h": hourly_data},
        include_nan=True,
    )
    generator = MultiTFGenerator(factory, _Config())

    captured = {}
    original_apply_tag = MultiTFGenerator._apply_timeframe_tag

    def _spy_apply_tag(features_df, timeframe, registry=None):
        del registry
        if timeframe == "12h":
            captured["primary_features"] = features_df.copy()
        return original_apply_tag(features_df, timeframe)

    monkeypatch.setattr(MultiTFGenerator, "_apply_timeframe_tag", staticmethod(_spy_apply_tag))

    generator.generate_multi_tf("BTCUSDT")

    primary_features = captured["primary_features"]
    first_col = primary_features.columns[0]
    assert np.isnan(primary_features[first_col].iloc[1])


def test_self_align_skip_preserves_column_order(monkeypatch):
    """T1.B13: self-align skip 前後 primary 欄位順序需保持一致。"""
    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": [5.0, 6.0, 7.0]})
    hourly_ts = [i * 3600 * 1000 for i in range(25)]
    hourly_data = pd.DataFrame({"timestamp": hourly_ts, "value": list(range(25))})

    ordered_cols = ["b_feature", "a_feature"]
    factory = _FactoryStub(
        {"12h": primary_data, "1h": hourly_data},
        primary_column_names=ordered_cols,
    )
    generator = MultiTFGenerator(factory, _Config())

    captured = {}
    original_apply_tag = MultiTFGenerator._apply_timeframe_tag

    def _spy_apply_tag(features_df, timeframe, registry=None):
        del registry
        if timeframe == "12h":
            captured["primary_columns"] = list(features_df.columns)
        return original_apply_tag(features_df, timeframe)

    monkeypatch.setattr(MultiTFGenerator, "_apply_timeframe_tag", staticmethod(_spy_apply_tag))

    generator.generate_multi_tf("BTCUSDT")

    assert captured["primary_columns"] == ordered_cols