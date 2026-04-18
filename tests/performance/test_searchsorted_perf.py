import gc
import time
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.feature_config import AlignmentMode
from momentum.FeatureEngineering.timeframe import tf_aligner as tf_aligner_module
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner


@pytest.mark.slow
def test_searchsorted_align_speed():
    """T1.P1: searchsorted 對齊速度需在 30 秒內。"""
    rows = 12_888
    cols = 1_000
    source_index = pd.date_range("2026-01-01", periods=rows, freq="1h")
    primary_index = pd.date_range("2026-01-01", periods=max(1, rows // 12), freq="12h")

    rng = np.random.RandomState(7)
    source_values = pd.DataFrame(
        rng.standard_normal((rows, cols)).astype(np.float32),
        index=source_index,
        columns=[f"c_{i}" for i in range(cols)],
    )

    start = time.perf_counter()
    aligned = TimeframeAligner._searchsorted_align(
        source_values=source_values,
        source_index=source_index,
        primary_index=primary_index,
        offset_ns=-1,
    )
    elapsed = time.perf_counter() - start

    assert aligned.shape == (len(primary_index), cols)
    assert elapsed < 30.0


@pytest.mark.slow
def test_searchsorted_align_memory():
    """T1.P2: searchsorted 對齊 RSS 增量應小於 500 MB。"""
    try:
        import psutil
    except Exception:
        pytest.skip("psutil not available")

    process = psutil.Process()
    rows = 8_000
    cols = 800
    source_index = pd.date_range("2026-01-01", periods=rows, freq="1h")
    primary_index = pd.date_range("2026-01-01", periods=max(1, rows // 12), freq="12h")

    rng = np.random.RandomState(11)
    source_values = pd.DataFrame(
        rng.standard_normal((rows, cols)).astype(np.float32),
        index=source_index,
        columns=[f"m_{i}" for i in range(cols)],
    )

    gc.collect()
    rss_before = process.memory_info().rss
    _ = TimeframeAligner._searchsorted_align(
        source_values=source_values,
        source_index=source_index,
        primary_index=primary_index,
        offset_ns=-1,
    )
    gc.collect()
    rss_after = process.memory_info().rss

    delta_mb = max(0.0, (rss_after - rss_before) / (1024 * 1024))
    assert delta_mb < 500.0


class _TimeframesPrimaryOnly:
    primary = "12h"
    training = ["12h"]
    alignment_mode = AlignmentMode.OPEN_MINUS


class _PrimaryOnlyConfig:
    timeframes = _TimeframesPrimaryOnly()

    class preprocessing:
        enabled = False


class _PrimaryOnlyFactory:
    def __init__(self, primary_df: pd.DataFrame, n_cols: int = 256):
        self._primary_df = primary_df
        self._n_cols = n_cols

    def _layer0_data_ingestion(self, symbol, timeframe, config, start_date=None, end_date=None):
        del symbol, config, start_date, end_date
        if timeframe != "12h":
            raise FileNotFoundError(timeframe)
        return self._primary_df

    def _layer1_atomic_indicators(self, data, config):
        del config
        base = data["value"].astype(float).to_numpy(dtype=np.float32)
        matrix = np.tile(base.reshape(-1, 1), (1, self._n_cols))
        return pd.DataFrame(
            matrix,
            index=data["timestamp"],
            columns=[f"close_trend_EMA_{i}" for i in range(self._n_cols)],
        )

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
            metadata={"layer_counts": {}},
            feature_count=features_df.shape[1],
            generation_time=0.0,
            layer_counts={},
            config_used={},
        )


@pytest.mark.slow
def test_self_align_skip_eliminates_memmap(monkeypatch):
    """T1.P3: 只有 primary TF 時，self-align skip 不應建立 searchsorted memmap。"""
    monkeypatch.setenv("FFACT_USE_SEARCHSORTED", "1")

    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000]
    primary_df = pd.DataFrame({"timestamp": primary_ts, "value": [1.0, 2.0, 3.0]})
    factory = _PrimaryOnlyFactory(primary_df=primary_df, n_cols=512)
    generator = MultiTFGenerator(factory, _PrimaryOnlyConfig())

    def _raise_if_called(shape, dtype=np.float32, prefix="ffact_"):
        del shape, dtype, prefix
        raise AssertionError("searchsorted memmap should not be called for primary self-align skip")

    monkeypatch.setattr(tf_aligner_module, "MEMMAP_THRESHOLD_BYTES", 1)
    monkeypatch.setattr(tf_aligner_module, "create_temp_memmap", _raise_if_called)

    result = generator.generate_multi_tf("BTCUSDT")

    assert result.features_df.shape[0] == len(primary_df)


@pytest.mark.slow
def test_phase1_gate_b2_plus_d_under_50s(monkeypatch):
    """Gate 1->2: 以測試場景量測 B2+D，總耗時需小於 50 秒。"""
    monkeypatch.setenv("FFACT_USE_SEARCHSORTED", "1")

    # D: non-primary TF searchsorted alignment
    d_rows = 12_888
    d_cols = 600
    source_index = pd.date_range("2026-01-01", periods=d_rows, freq="1h")
    primary_index = pd.date_range("2026-01-01", periods=max(1, d_rows // 12), freq="12h")
    rng = np.random.RandomState(23)
    source_values = pd.DataFrame(
        rng.standard_normal((d_rows, d_cols)).astype(np.float32),
        index=source_index,
        columns=[f"d_{i}" for i in range(d_cols)],
    )

    d_start = time.perf_counter()
    _ = TimeframeAligner._searchsorted_align(
        source_values=source_values,
        source_index=source_index,
        primary_index=primary_index,
        offset_ns=-1,
    )
    d_elapsed = time.perf_counter() - d_start

    # B2: primary self-alignment skip path
    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000, 36 * 3600 * 1000]
    primary_df = pd.DataFrame({"timestamp": primary_ts, "value": [1.0, 2.0, 3.0, 4.0]})
    factory = _PrimaryOnlyFactory(primary_df=primary_df, n_cols=512)
    generator = MultiTFGenerator(factory, _PrimaryOnlyConfig())

    b2_start = time.perf_counter()
    _ = generator.generate_multi_tf("BTCUSDT")
    b2_elapsed = time.perf_counter() - b2_start

    assert d_elapsed + b2_elapsed < 50.0