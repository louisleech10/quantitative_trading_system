from types import SimpleNamespace

import numpy as np
import pandas as pd

from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner
from momentum.FeatureEngineering.feature_config import AlignmentMode


class DummyTimeframes:
    primary = "12h"
    training = ["12h", "1h"]
    alignment_mode = AlignmentMode.OPEN_MINUS


class DummyConfig:
    timeframes = DummyTimeframes()

    class preprocessing:
        enabled = False


class StubFactory:
    def __init__(self, data_by_tf):
        self._data_by_tf = data_by_tf

    def _layer0_data_ingestion(self, symbol, timeframe, config, start_date=None, end_date=None):
        if timeframe not in self._data_by_tf:
            raise FileNotFoundError(timeframe)
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

    def _layer6_5_preprocessing(self, all_features, config):
        return all_features

    def _combine_layers(self, layers, context="unknown"):
        valid_layers = [layer for layer in layers if layer is not None and not layer.empty]
        if not valid_layers:
            return pd.DataFrame()
        combined = pd.concat(valid_layers, axis=1)
        if combined.columns.has_duplicates:
            combined = combined.loc[:, ~combined.columns.duplicated(keep="first")]
        return combined

    def _compute_config_hash(self, config, symbol=None, timeframe=None, start_date=None, end_date=None):
        return "dummy_hash"

    def _layer7_validate_and_persist(self, symbol, timeframe, raw_data, layers, config, elapsed, config_hash):
        features_df = self._combine_layers(layers).reindex(raw_data.index)
        return SimpleNamespace(
            features_df=features_df,
            labels_df=pd.DataFrame(index=features_df.index),
            metadata={"config_hash": config_hash, "layer_counts": {}},
            feature_count=features_df.shape[1],
            generation_time=elapsed,
            layer_counts={},
            config_used={},
        )


def test_multi_tf_generator_aligns_and_tags():
    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": [10, 11, 12]})

    hourly_ts = [i * 3600 * 1000 for i in range(25)]
    hourly_data = pd.DataFrame({"timestamp": hourly_ts, "value": list(range(25))})

    factory = StubFactory({"12h": primary_data, "1h": hourly_data})
    generator = MultiTFGenerator(factory, DummyConfig())
    result = generator.generate_multi_tf("BTCUSDT")
    df = result.features_df

    assert len(df) == 3
    assert "close_12h_trend_EMA_21" in df.columns
    assert "close_1h_trend_EMA_21" in df.columns
    assert df.columns.is_unique

    # OPEN_MINUS: for 12h open at 12:00, lower TF uses 11:00 bar (value=11), not 12:00 bar (value=12).
    assert df["close_1h_trend_EMA_21"].iloc[1] == 11

    # MultiTF mode: primary timeframe columns are also tagged for explicit TF identity.
    assert "close_trend_EMA_21" not in df.columns


def test_multi_tf_generator_skips_primary_self_alignment(monkeypatch):
    """測試 primary timeframe 會跳過 self-alignment 呼叫。"""
    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": [10, 11, 12]})

    hourly_ts = [i * 3600 * 1000 for i in range(25)]
    hourly_data = pd.DataFrame({"timestamp": hourly_ts, "value": list(range(25))})

    factory = StubFactory({"12h": primary_data, "1h": hourly_data})
    generator = MultiTFGenerator(factory, DummyConfig())

    original_align = TimeframeAligner.align_to_primary
    called_source_tfs = []

    def _spy_align(source_df, source_tf, primary_timestamps, primary_tf, alignment_mode=AlignmentMode.OPEN_MINUS):
        called_source_tfs.append(source_tf)
        if source_tf == primary_tf:
            raise AssertionError("Primary TF should skip self-alignment")
        return original_align(source_df, source_tf, primary_timestamps, primary_tf, alignment_mode)

    monkeypatch.setattr(TimeframeAligner, "align_to_primary", staticmethod(_spy_align))

    result = generator.generate_multi_tf("BTCUSDT")

    assert result.features_df.shape[0] == 3
    assert called_source_tfs == ["1h"]


def test_apply_timeframe_tag_format_and_skip_prefixes():
    df = pd.DataFrame(
        {
            "close_RSI_14": [1.0],
            "close_RSI_14_Lag_3": [2.0],
            "meta_quality": [3.0],
            "label_return_5": [4.0],
        }
    )
    tagged = MultiTFGenerator._apply_timeframe_tag(df, "1h")

    assert "close_1h_RSI_14" in tagged.columns
    assert "close_1h_RSI_14_Lag_3" in tagged.columns
    assert "meta_1h_quality" in tagged.columns
    assert "label_return_5" in tagged.columns


def test_ensure_primary_appends_and_deduplicates():
    generator = MultiTFGenerator(StubFactory({"12h": pd.DataFrame()}), DummyConfig())
    result = generator._ensure_primary(["12h", "12h", "4h"])
    assert result == ["12h", "4h"]

    result_no_primary = generator._ensure_primary(["4h", "1h", "4h"])
    assert result_no_primary == ["4h", "1h", "12h"]


def test_lower_tf_missing_degrades_but_primary_succeeds():
    primary_ts = [0, 12 * 3600 * 1000]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": [10, 11]})
    factory = StubFactory({"12h": primary_data})

    generator = MultiTFGenerator(factory, DummyConfig())
    result = generator.generate_multi_tf("BTCUSDT")

    assert result.features_df.shape[0] == 2
    assert result.metadata["skipped_timeframes"] == ["1h"]
    assert result.metadata["actual_timeframes"] == ["12h"]


def test_short_primary_data_still_generates():
    primary_ts = [i * 12 * 3600 * 1000 for i in range(10)]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": list(range(10))})
    hourly_ts = [i * 3600 * 1000 for i in range(120)]
    hourly_data = pd.DataFrame({"timestamp": hourly_ts, "value": list(range(120))})

    factory = StubFactory({"12h": primary_data, "1h": hourly_data})
    generator = MultiTFGenerator(factory, DummyConfig())
    result = generator.generate_multi_tf("BTCUSDT")

    assert result.features_df.shape[0] == 10


def test_sparse_lower_tf_alignment_yields_leading_nan_without_error():
    primary_ts = pd.Series([0, 12 * 3600 * 1000, 24 * 3600 * 1000])
    sparse_source_df = pd.DataFrame(
        {"feature": [100.0]},
        index=pd.to_datetime([24 * 3600 * 1000], unit="ms"),
    )

    aligned = TimeframeAligner.align_to_primary(
        source_df=sparse_source_df,
        source_tf="1h",
        primary_timestamps=primary_ts,
        primary_tf="12h",
        alignment_mode=AlignmentMode.OPEN_MINUS,
    )

    assert aligned.shape[0] == 3
    assert aligned["feature"].isna().iloc[0]


def test_primary_missing_raises_error():
    factory = StubFactory({"1h": pd.DataFrame({"timestamp": [0], "value": [1]})})
    generator = MultiTFGenerator(factory, DummyConfig())

    try:
        generator.generate_multi_tf("BTCUSDT")
        assert False, "Expected ValueError for missing primary timeframe"
    except ValueError as exc:
        assert "Primary timeframe data missing" in str(exc)


def test_register_worker_groups_chunked_persist_and_cleanup(tmp_path):
    """Worker TF group registration writes aligned npy and releases worker temp files."""
    registry = ColumnGroupRegistry(tmp_path / "main_work", memory_buffer_groups=0)
    worker_dir = tmp_path / "BTCUSDT_12h_worker"
    worker_dir.mkdir()
    worker_npy = worker_dir / "L1_test.npy"
    source = np.array([[1.0, 10.0], [2.0, 20.0], [3.0, 30.0]], dtype=np.float32)
    np.save(worker_npy, source, allow_pickle=False)

    primary_timestamps = pd.date_range("2026-01-01", periods=3, freq="h")
    groups_data = [
        {
            "group_id": "L1_test",
            "layer": "L1",
            "timeframe": "12h",
            "data_source": "close",
            "indicator": "TEST",
            "columns": ["a", "b"],
            "shape": [3, 2],
            "dtype": "float32",
            "npy_path": str(worker_npy),
        }
    ]

    generator = MultiTFGenerator.__new__(MultiTFGenerator)
    generator._register_worker_groups(
        registry,
        groups_data,
        "12h",
        primary_timestamps,
        AlignmentMode.CLOSE_TIME,
        source_timestamps_ms=None,
    )

    persisted = registry.load_data("L1_test")
    np.testing.assert_allclose(np.asarray(persisted), source)
    assert not worker_npy.exists()
    assert not worker_dir.exists()


def test_register_worker_groups_keeps_worker_npy_when_flag_enabled(monkeypatch, tmp_path):
    """FFACT_MULTI_TF_KEEP_WORKER_NPY=1 must preserve worker .npy + workdir."""
    monkeypatch.setenv("FFACT_MULTI_TF_KEEP_WORKER_NPY", "1")

    registry = ColumnGroupRegistry(tmp_path / "main_work", memory_buffer_groups=0)
    worker_dir = tmp_path / "ETHUSDT_1h_worker"
    worker_dir.mkdir()
    worker_npy = worker_dir / "L1_keep.npy"
    source = np.array([[7.0, 70.0], [8.0, 80.0]], dtype=np.float32)
    np.save(worker_npy, source, allow_pickle=False)

    primary_timestamps = pd.date_range("2026-01-01", periods=2, freq="h")
    groups_data = [
        {
            "group_id": "L1_keep",
            "layer": "L1",
            "timeframe": "1h",
            "data_source": "close",
            "indicator": "TEST",
            "columns": ["x", "y"],
            "shape": [2, 2],
            "dtype": "float32",
            "npy_path": str(worker_npy),
        }
    ]

    generator = MultiTFGenerator.__new__(MultiTFGenerator)
    generator._register_worker_groups(
        registry,
        groups_data,
        "1h",
        primary_timestamps,
        AlignmentMode.CLOSE_TIME,
        source_timestamps_ms=None,
    )

    persisted = registry.load_data("L1_keep")
    np.testing.assert_allclose(np.asarray(persisted), source)
    # Debug flag preserves both the worker .npy and the enclosing workdir.
    assert worker_npy.exists()
    assert worker_dir.exists()


def test_persist_aligned_group_to_npy_reports_insufficient_disk(monkeypatch, tmp_path):
    """Disk guard fails before writing when aligned group cannot fit."""
    monkeypatch.setattr(MultiTFGenerator, "_disk_free_bytes", staticmethod(lambda _path: 1))
    target_path = tmp_path / "aligned.npy"

    try:
        MultiTFGenerator._persist_aligned_group_to_npy(
            np.ones((2, 2), dtype=np.float32),
            target_path,
            n_primary=2,
            n_cols=2,
            idx_map=None,
            group_id="too_big",
        )
        assert False, "Expected disk space guard to fail"
    except OSError as exc:
        assert "Insufficient disk space" in str(exc)
        assert "too_big" in str(exc)
        assert not target_path.exists()


def test_open_minus_no_future_leak_for_lower_tf():
    primary_ts = pd.Series([12 * 3600 * 1000, 24 * 3600 * 1000])
    source_df = pd.DataFrame(
        {"feature": [11, 12, 13]},
        index=pd.to_datetime([11, 12, 24], unit="h"),
    )

    aligned = TimeframeAligner.align_to_primary(
        source_df=source_df,
        source_tf="1h",
        primary_timestamps=primary_ts,
        primary_tf="12h",
        alignment_mode=AlignmentMode.OPEN_MINUS,
    )
    assert TimeframeAligner.validate_no_future_leak(aligned, primary_ts)


def test_close_time_mode_keeps_same_open_bar_for_lower_tf():
    primary_ts = pd.Series([12 * 3600 * 1000, 24 * 3600 * 1000])
    source_df = pd.DataFrame(
        {"feature": [11, 12, 13]},
        index=pd.to_datetime([11, 12, 24], unit="h"),
    )

    aligned = TimeframeAligner.align_to_primary(
        source_df=source_df,
        source_tf="1h",
        primary_timestamps=primary_ts,
        primary_tf="12h",
        alignment_mode=AlignmentMode.CLOSE_TIME,
    )

    assert aligned["feature"].tolist() == [12, 13]


def test_open_minus_cross_day_boundary_alignment_stable():
    # Primary opens at UTC day boundaries; lower TF should align to strictly earlier bar in OPEN_MINUS.
    primary_index = pd.to_datetime(["2026-01-01 00:00:00", "2026-01-02 00:00:00"])
    primary_ts = pd.Series((primary_index.view("int64") // 1_000_000).astype("int64"))

    source_index = pd.to_datetime(
        ["2025-12-31 23:00:00", "2026-01-01 00:00:00", "2026-01-01 23:00:00", "2026-01-02 00:00:00"]
    )
    source_df = pd.DataFrame({"feature": [1.0, 2.0, 3.0, 4.0]}, index=source_index)

    aligned = TimeframeAligner.align_to_primary(
        source_df=source_df,
        source_tf="1h",
        primary_timestamps=primary_ts,
        primary_tf="1d",
        alignment_mode=AlignmentMode.OPEN_MINUS,
    )

    assert aligned["feature"].tolist() == [1.0, 3.0]
    assert not aligned["feature"].isna().any()


def test_open_minus_does_not_shift_primary_self_alignment():
    ts = pd.Series([0, 12 * 3600 * 1000, 24 * 3600 * 1000])
    source_df = pd.DataFrame(
        {"feature": [10, 11, 12]},
        index=pd.to_datetime(ts, unit="ms"),
    )

    aligned = TimeframeAligner.align_to_primary(
        source_df=source_df,
        source_tf="12h",
        primary_timestamps=ts,
        primary_tf="12h",
        alignment_mode=AlignmentMode.OPEN_MINUS,
    )

    assert aligned["feature"].tolist() == [10, 11, 12]


def test_multi_tf_generator_propagates_date_range_to_all_layer0_calls():
    class SpyFactory(StubFactory):
        def __init__(self, data_by_tf):
            super().__init__(data_by_tf)
            self.calls = []

        def _layer0_data_ingestion(self, symbol, timeframe, config, start_date=None, end_date=None):
            self.calls.append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
            return super()._layer0_data_ingestion(
                symbol,
                timeframe,
                config,
                start_date=start_date,
                end_date=end_date,
            )

    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": [10, 11, 12]})
    hourly_ts = [i * 3600 * 1000 for i in range(25)]
    hourly_data = pd.DataFrame({"timestamp": hourly_ts, "value": list(range(25))})

    factory = SpyFactory({"12h": primary_data, "1h": hourly_data})
    generator = MultiTFGenerator(factory, DummyConfig())

    result = generator.generate_multi_tf(
        "BTCUSDT",
        start_date="2024-01-02",
        end_date="2024-01-03",
    )

    assert result.features_df is not None
    assert len(factory.calls) == 2
    assert {call["timeframe"] for call in factory.calls} == {"12h", "1h"}
    assert all(call["start_date"] == "2024-01-02" for call in factory.calls)
    assert all(call["end_date"] == "2024-01-03" for call in factory.calls)
