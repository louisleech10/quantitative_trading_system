from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner
from momentum.FeatureEngineering.feature_config import AlignmentMode

from tests._helpers.stub_layer_execute import (
    stub_execute_layer1_6,
    stub_layer_data,
    stub_spill_to_memmap,
)


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

    def _execute_layer1_6(self, layer_name, func, *args):
        del layer_name
        return stub_execute_layer1_6(func, *args)

    def _execute_layer1_6_preserve_dtype(self, layer_name, func, *args):
        del layer_name
        return stub_execute_layer1_6(func, *args)

    _spill_to_memmap = staticmethod(stub_spill_to_memmap)
    layer_data = stub_layer_data

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

    def _layer7_validate_and_persist(self, symbol, timeframe, raw_data, layers, config, elapsed, config_hash, batch_id=None):
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


def test_lower_tf_missing_fails_closed_unless_partial_enabled():
    primary_ts = [0, 12 * 3600 * 1000]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": [10, 11]})
    factory = StubFactory({"12h": primary_data})

    generator = MultiTFGenerator(factory, DummyConfig())
    with pytest.raises(RuntimeError, match="Timeframe 1h failed"):
        generator.generate_multi_tf("BTCUSDT")

    partial_config = DummyConfig()
    partial_config.allow_partial_timeframes = True
    result = MultiTFGenerator(factory, partial_config).generate_multi_tf("BTCUSDT")

    assert result.features_df.shape[0] == 2
    assert result.metadata["skipped_timeframes"] == ["1h"]
    assert result.metadata["present_timeframes"] == ["12h"]


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


# ---------------------------------------------------------------------------
# FF-TFMETA（docs/FFTFMETA_SPEC.md）Task 3.1／3.2：真實 kline 小窗 run（輕量設定，單次約 5–10 秒）
# ---------------------------------------------------------------------------

import dataclasses  # noqa: E402

from momentum.core.contracts import LayerStatus  # noqa: E402
from momentum.FeatureEngineering import feature_storage as fs_module  # noqa: E402
from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource  # noqa: E402
from momentum.FeatureEngineering.feature_factory import FeatureFactory  # noqa: E402
from tests.feature_engineering import fftfmeta_golden_helpers as fg  # noqa: E402

_TF_KEYS = ("expected_timeframes", "present_timeframes", "failed_timeframes")
_PATH_ENV = {
    "cgsa_serial": {"FFACT_USE_CGSA": "1", "FFACT_MULTI_TF_PARALLEL": "0"},
    "cgsa_parallel": {"FFACT_USE_CGSA": "1", "FFACT_MULTI_TF_PARALLEL": "1"},
    "legacy": {"FFACT_USE_CGSA": "0", "FFACT_MULTI_TF_PARALLEL": "0"},
}
_CASES = {
    "healthy": (["1h", "12h"], (["1h", "12h"], ["1h", "12h"], []), "complete"),
    "skip": (["1h", "12h"], (["1h", "12h"], ["1h"], ["12h"]), "partial"),
    "failed": (["1h", "12h"], (["1h", "12h"], ["1h"], ["12h"]), "partial"),
    "single": (["1h"], (["1h"], ["1h"], []), "complete"),
}


def _thread_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.feature_engineering.test_failopen_producer import _ThreadPoolAsProcessPool
    monkeypatch.setattr("concurrent.futures.ProcessPoolExecutor", _ThreadPoolAsProcessPool)


def _inject_12h_load(monkeypatch: pytest.MonkeyPatch, exc: Exception) -> None:
    real = FeatureFactory._layer0_data_ingestion

    def patched(self, symbol, timeframe, config, *args, **kwargs):
        if timeframe == "12h":
            raise exc
        return real(self, symbol, timeframe, config, *args, **kwargs)

    monkeypatch.setattr(FeatureFactory, "_layer0_data_ingestion", patched)


def _inject_layer_status(monkeypatch: pytest.MonkeyPatch, timeframe: str, layer_name: str, status: LayerStatus) -> None:
    real = FeatureFactory._execute_layer1_6_preserve_dtype

    def patched(self, name, func, *args):
        result = real(self, name, func, *args)
        if name == layer_name and str(getattr(self, "_current_timeframe", "")) == timeframe:
            return dataclasses.replace(result, status=status, reason=None)
        return result

    monkeypatch.setattr(FeatureFactory, "_execute_layer1_6_preserve_dtype", patched)


def _artifact(path: str, root, primary_tf: str, result) -> dict:
    return fg.meta_json(root, primary_tf) if path == "legacy" else fg.l7_manifest(root, primary_tf, result)


def _run_case(tmp_path, monkeypatch, path: str, case: str, **overrides):
    fg.prepare_env(monkeypatch, tmp_path, **_PATH_ENV[path])
    if path == "cgsa_parallel":
        _thread_pool(monkeypatch)
    if case == "skip":
        _inject_12h_load(monkeypatch, FileNotFoundError("12h"))
    elif case == "failed":
        _inject_12h_load(monkeypatch, RuntimeError("injected 12h load failure"))
    training = _CASES[case][0]
    payload = fg.fast_payload(training, **fg.HEALTHY, allow_partial_timeframes=True, **overrides)
    root, _factory, result = fg.generate(tmp_path, payload)
    return root, result


def _assert_canonical_case(tmp_path, monkeypatch, path: str, case: str) -> None:
    root, result = _run_case(tmp_path, monkeypatch, path, case)
    artifact = _artifact(path, root, "1h", result)
    _training, expected_tfs, quality = _CASES[case]
    for key, expected in zip(_TF_KEYS, expected_tfs):
        assert result.metadata.get(key) == expected, (path, case, key, result.metadata.get(key))
        assert artifact.get(key) == expected, (path, case, key, artifact.get(key))
    assert result.metadata["quality_status"] == artifact["quality_status"] == quality, (path, case)
    if case in ("skip", "failed"):
        assert "timeframe:12h" in result.metadata["failure_reasons"]
        assert artifact["failure_reasons"] == result.metadata["failure_reasons"]
        assert result.metadata["skipped_timeframes"] == result.metadata["failed_timeframes"]


@pytest.mark.requires_kline
@pytest.mark.parametrize("case", list(_CASES))
@pytest.mark.parametrize("path", list(_PATH_ENV))
def test_canonical_completeness_three_paths_four_cases(path, case, tmp_path, monkeypatch) -> None:
    """Task 3.1 驗證：三路徑 × 四情況，manifest（legacy 為 meta.json）與 result.metadata 之週期三欄與 quality_status
    皆等於預期且兩兩相等。"""
    _assert_canonical_case(tmp_path, monkeypatch, path, case)


@pytest.mark.requires_kline
@pytest.mark.parametrize("path", ["cgsa_serial", "cgsa_parallel"])
def test_canonical_completeness_dependency_failed_on_12h_reaches_manifest(path, tmp_path, monkeypatch) -> None:
    """Task 3.1 改法（§V mutant ④）：非 primary 週期之 dependency_failed ⇒ manifest 與 metadata 之 failed_layers 含 L3:12h、partial。"""
    fg.prepare_env(monkeypatch, tmp_path, **_PATH_ENV[path])
    if path == "cgsa_parallel":
        _thread_pool(monkeypatch)
    _inject_layer_status(monkeypatch, "12h", "Layer 3", LayerStatus.dependency_failed)
    payload = fg.fast_payload(["1h", "12h"], **fg.HEALTHY, allow_partial_layers=True)
    root, _factory, result = fg.generate(tmp_path, payload)
    manifest = fg.l7_manifest(root, "1h", result)
    for source in (manifest, result.metadata):
        assert "L3:12h" in source["failed_layers"], source["failed_layers"]
        assert any(r.startswith("L3:12h:") for r in source["failure_reasons"]), source["failure_reasons"]
        assert source["quality_status"] == "partial"
    assert manifest["failed_layers"] == result.metadata["failed_layers"]


@pytest.mark.requires_kline
def test_boundary_17_canonical_completeness_primary_missing_raises(tmp_path, monkeypatch) -> None:
    """Task 3.1 邊界①：primary 週期失敗（其 L1 layer_failed ⇒ 該週期 rollback 並記入 skip）⇒ 既有
    ValueError("Primary timeframe data missing…") 不變。"""
    fg.prepare_env(monkeypatch, tmp_path, **_PATH_ENV["cgsa_serial"])
    _inject_layer_status(monkeypatch, "1h", "Layer 1", LayerStatus.layer_failed)
    payload = fg.fast_payload(["1h", "12h"], **fg.HEALTHY, allow_partial_timeframes=True)
    with pytest.raises(ValueError, match="Primary timeframe data missing"):
        fg.generate(tmp_path, payload)


@pytest.mark.requires_kline
def test_boundary_18_canonical_completeness_training_order_kept(tmp_path, monkeypatch) -> None:
    """Task 3.1 邊界②：training 序 ["12h","1h"]（primary 12h）⇒ expected 依 training 序。"""
    fg.prepare_env(monkeypatch, tmp_path, **_PATH_ENV["cgsa_serial"])
    payload = fg.fast_payload(["12h", "1h"], **fg.HEALTHY)
    payload["timeframes"]["primary"] = "12h"
    root, _factory, result = fg.generate(tmp_path, payload, primary_tf="12h")
    manifest = fg.l7_manifest(root, "12h", result)
    assert manifest["expected_timeframes"] == result.metadata["expected_timeframes"] == ["12h", "1h"]


@pytest.mark.requires_kline
def test_boundary_19_canonical_completeness_parallel_error_fail_closed(tmp_path, monkeypatch) -> None:
    """Task 3.1 邊界③：parallel worker 回報 error 且 allow_partial_timeframes=False ⇒ 既有拋錯不變。"""
    fg.prepare_env(monkeypatch, tmp_path, **_PATH_ENV["cgsa_parallel"])
    _thread_pool(monkeypatch)
    _inject_12h_load(monkeypatch, RuntimeError("injected 12h load failure"))
    payload = fg.fast_payload(["1h", "12h"], **fg.HEALTHY)
    with pytest.raises(RuntimeError, match="Timeframe 12h failed"):
        fg.generate(tmp_path, payload)


@pytest.mark.requires_kline
def test_mutation_canonical_completeness_single_tf_timeframes_is_caught(tmp_path, monkeypatch) -> None:
    """§V mutant ①②：週期物件退回只含 primary（storage 改回 [timeframe]）⇒ 健康多週期案例必紅。"""
    from momentum.FeatureEngineering.timeframe import multi_tf_generator as mtf_module
    real = fs_module.build_timeframe_completeness

    def mutant(expected, failed):
        return real(list(expected)[:1], [])

    monkeypatch.setattr(fs_module, "build_timeframe_completeness", mutant)
    monkeypatch.setattr(mtf_module, "build_timeframe_completeness", mutant, raising=False)  # 若以 from-import 綁名
    with pytest.raises(AssertionError):
        _assert_canonical_case(tmp_path, monkeypatch, "cgsa_serial", "healthy")


# --- Task 3.2 ---------------------------------------------------------------

def _crosscheck():
    return getattr(MultiTFGenerator, "_crosscheck_present_timeframes")


def _register(registry: ColumnGroupRegistry, timeframe: str) -> None:
    arr = np.zeros((4, 1), dtype=np.float32)
    group = ColumnGroup(
        group_id=f"{timeframe}_L1_probe", layer=LayerSource.L1, timeframe=timeframe, data_source="close",
        indicator="probe", columns=(f"close_{timeframe}_probe",), shape=arr.shape, dtype="float32",
    )
    registry.save_data(group, arr)


def test_crosscheck_present_timeframes_missing_group_raises(tmp_path) -> None:
    """Task 3.2 驗證：真實 registry 中 12h 無群組而 present 含 12h ⇒ RuntimeError；健康 ⇒ 不拋。"""
    registry = ColumnGroupRegistry(tmp_path / "w")
    _register(registry, "1h")
    with pytest.raises(RuntimeError):
        _crosscheck()(registry, ["1h", "12h"])
    _register(registry, "12h")
    _crosscheck()(registry, ["1h", "12h"])


@pytest.mark.requires_kline
def test_boundary_20_crosscheck_present_timeframes_before_l7_dead_drop(tmp_path, monkeypatch) -> None:
    """Task 3.2 邊界①：cross-check 於 L7 persist（dead-drop 在其中）之前；dead-drop 開啟之真實 run 不拋。"""
    fg.prepare_env(monkeypatch, tmp_path, **_PATH_ENV["cgsa_serial"])
    order: list = []
    real_check = _crosscheck()
    real_persist = FeatureFactory._layer7_raw_from_cgsa_pipeline

    def check(registry, present):
        order.append("crosscheck")
        return real_check(registry, present)

    def persist(self, *args, **kwargs):
        order.append("persist")
        return real_persist(self, *args, **kwargs)

    monkeypatch.setattr(MultiTFGenerator, "_crosscheck_present_timeframes", staticmethod(check))
    monkeypatch.setattr(FeatureFactory, "_layer7_raw_from_cgsa_pipeline", persist)
    payload = fg.fast_payload(["1h", "12h"], **fg.HEALTHY)
    payload["nan_strategy"] = {"l7_dead_feature_drop": {"enabled": True, "min_valid_samples": 100}}
    fg.generate(tmp_path, payload)
    assert order == ["crosscheck", "persist"]


def test_boundary_21_crosscheck_present_timeframes_counts_resumed_groups(tmp_path) -> None:
    """Task 3.2 邊界②：resume 讀回之週期群組亦計入。"""
    registry = ColumnGroupRegistry(tmp_path / "w")
    _register(registry, "1h")
    _register(registry, "12h")
    registry.write_manifest()
    resumed = ColumnGroupRegistry.resume_from_manifest(tmp_path / "w")
    _crosscheck()(resumed, ["1h", "12h"])
    with pytest.raises(RuntimeError):
        _crosscheck()(resumed, ["1h", "4h", "12h"])


def test_mutation_crosscheck_ignoring_registry_is_caught(tmp_path, monkeypatch) -> None:
    """改壞：cross-check 恆不拋 ⇒ 缺群組之驗收必紅。"""
    monkeypatch.setattr(MultiTFGenerator, "_crosscheck_present_timeframes", staticmethod(lambda registry, present: None),
                        raising=False)
    with pytest.raises(pytest.fail.Exception):
        test_crosscheck_present_timeframes_missing_group_raises(tmp_path)
