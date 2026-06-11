"""Phase4 producer fail-closed、品質 gate 與 CGSA rollback 測試。"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import api.services.feature_factory_service as feature_service_module
from api.services.feature_factory_service import FeatureFactoryService
from momentum.core.contracts import LayerExecutionResult, LayerStatus
from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_config import AlignmentMode
from momentum.FeatureEngineering.timeframe import multi_tf_generator as mtf_module
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
from momentum.factories import create_feature_factory
from tests.test_multi_tf_generator import StubFactory


def _config(**runtime_values):
    payload = ConfigManager().get_merged_config().model_dump(by_alias=True)
    payload.update(runtime_values)
    return ConfigManager().get_merged_config().__class__.model_validate(payload)


def _multi_tf_config(*, allow_partial_timeframes: bool = False):
    """FactoryConfig with 12h+1h training，供 parallel CGSA 路徑使用。"""
    payload = ConfigManager().get_merged_config().model_dump(by_alias=True)
    payload.update(
        {
            "allow_partial_timeframes": allow_partial_timeframes,
            "timeframes": {
                "primary": "12h",
                "training": ["12h", "1h"],
                "alignment_mode": "open_minus",
            },
        }
    )
    return ConfigManager().get_merged_config().__class__.model_validate(payload)


def _layer_result(status: LayerStatus) -> LayerExecutionResult:
    return LayerExecutionResult(
        data=pd.DataFrame({"x": np.arange(4, dtype=np.float32)}),
        status=status,
        failed_engines=("required",) if status == LayerStatus.layer_failed else (),
        reason="injected failure" if status == LayerStatus.layer_failed else None,
        configured_engines=2,
        present_engines=1,
        required_engines=1,
        dependency_error=False,
    )


def test_layer_failed_aborts_by_default_and_engine_partial_succeeds() -> None:
    factory = create_feature_factory(validate_continuity=False)
    config = _config()

    with pytest.raises(RuntimeError, match="Layer 3 failed"):
        factory._raise_for_failed_layer(_layer_result(LayerStatus.layer_failed), "Layer 3", config)

    factory._raise_for_failed_layer(_layer_result(LayerStatus.engine_partial), "Layer 1", config)
    partial_config = _config(allow_partial_layers=True)
    factory._raise_for_failed_layer(
        _layer_result(LayerStatus.layer_failed),
        "Layer 3",
        partial_config,
    )


class _MtFTimeframes:
    primary = "12h"
    training = ["12h", "1h"]
    alignment_mode = AlignmentMode.OPEN_MINUS


class _MtFConfig:
    def __init__(self, *, allow_partial_timeframes: bool = False) -> None:
        self.timeframes = _MtFTimeframes()
        self.preprocessing = SimpleNamespace(enabled=False)
        self.allow_partial_timeframes = allow_partial_timeframes


class _CgsaStubFactory(StubFactory):
    """StubFactory + CGSA registry 持久化，走真實 multi-TF CGSA 編排。"""

    def __init__(self, data_by_tf: dict, registry: ColumnGroupRegistry) -> None:
        super().__init__(data_by_tf)
        self._cgsa_registry = registry
        self._current_timeframe = "12h"
        self._adapter_registry = SimpleNamespace(_adapters={})

    @staticmethod
    def _cgsa_enabled() -> bool:
        return True

    def _layer1_atomic_indicators(self, data, config):
        del config
        timeframe = str(self._current_timeframe)
        frame = pd.DataFrame(
            {f"close_{timeframe}_trend_EMA_21": data["value"].values},
            index=data["timestamp"],
        )
        group = ColumnGroup(
            group_id=f"{timeframe}_L1_trend_EMA",
            layer=LayerSource.L1,
            timeframe=timeframe,
            data_source="close",
            indicator="EMA",
            columns=(f"close_{timeframe}_trend_EMA_21",),
            shape=frame.shape,
            dtype="float32",
        )
        self._cgsa_registry.save_data(group, frame.to_numpy(dtype=np.float32))
        return frame

    def _persist_layer_output_groups(self, frame, layer, label) -> None:
        del label
        if frame is None or frame.empty:
            return
        timeframe = str(self._current_timeframe)
        for column in frame.columns:
            group = ColumnGroup(
                group_id=f"{timeframe}_{layer.value}_{column}",
                layer=layer,
                timeframe=timeframe,
                data_source="close",
                indicator=column,
                columns=(column,),
                shape=frame[[column]].shape,
                dtype="float32",
            )
            self._cgsa_registry.save_data(group, frame[[column]].to_numpy(dtype=np.float32))

    def _layer7_raw_from_cgsa_pipeline(
        self,
        symbol,
        timeframe,
        raw_data,
        config,
        elapsed,
        config_hash,
        compute_warnings=None,
        persist: bool = True,
    ):
        del symbol, timeframe, config, compute_warnings, persist
        frames = []
        for group_id, group in self._cgsa_registry.iter_all():
            data = np.asarray(self._cgsa_registry.load_data(group_id), dtype=np.float32)
            frames.append(pd.DataFrame(data, index=raw_data.index, columns=list(group.columns)))
        features_df = (
            pd.concat(frames, axis=1).loc[:, lambda frame: ~frame.columns.duplicated(keep="first")]
            if frames
            else pd.DataFrame(index=raw_data.index)
        )
        return SimpleNamespace(
            features_df=features_df,
            labels_df=pd.DataFrame(index=features_df.index),
            metadata={"config_hash": config_hash, "quality_status": "complete"},
            feature_count=features_df.shape[1],
            generation_time=elapsed,
            layer_counts={},
            config_used={},
            hdf5_path="",
        )


def _primary_only_frames() -> pd.DataFrame:
    primary_ts = [0, 12 * 3600 * 1000]
    return pd.DataFrame({"timestamp": primary_ts, "value": [10, 11]})


class _ThreadPoolAsProcessPool(ThreadPoolExecutor):
    """平行路徑測試：以 ThreadPool 取代 ProcessPool，並吞掉 mp_context。"""

    def __init__(self, max_workers=None, mp_context=None) -> None:
        del mp_context
        super().__init__(max_workers=max_workers)


def _build_mtf_generator(
    factory: object,
    config: _MtFConfig,
) -> MultiTFGenerator:
    return MultiTFGenerator(factory, config)


@pytest.mark.parametrize(
    "generator_path",
    ["legacy", "cgsa_serial", "cgsa_parallel_primary", "cgsa_parallel_worker"],
)
@pytest.mark.parametrize("allow_partial", [False, True])
def test_four_generator_paths_fail_closed_integration(
    generator_path: str,
    allow_partial: bool,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """四條 multi-TF 編排路徑：缺 lower TF / pipeline 失敗時預設 fail-closed，partial flag 則續行。"""
    primary_data = _primary_only_frames()
    config = _MtFConfig(allow_partial_timeframes=allow_partial)
    inject_primary_failure = generator_path == "cgsa_parallel_primary" and not allow_partial
    inject_worker_failure = generator_path.startswith("cgsa_parallel") and (
        generator_path == "cgsa_parallel_worker" or allow_partial
    )

    if generator_path == "legacy":
        monkeypatch.setenv("FFACT_USE_CGSA", "0")
        factory = StubFactory({"12h": primary_data})
        generator = _build_mtf_generator(factory, config)
    elif generator_path == "cgsa_serial":
        monkeypatch.setenv("FFACT_USE_CGSA", "1")
        monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "0")
        registry = ColumnGroupRegistry(tmp_path / "cgsa_serial")
        factory = _CgsaStubFactory({"12h": primary_data}, registry)
        generator = _build_mtf_generator(factory, config)
    else:
        monkeypatch.setenv("FFACT_USE_CGSA", "1")
        monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "1")
        monkeypatch.setattr("concurrent.futures.ProcessPoolExecutor", _ThreadPoolAsProcessPool)
        config = _multi_tf_config(allow_partial_timeframes=allow_partial)
        if inject_worker_failure:

            def _worker_entry(symbol, timeframe, config_payload, start_date, end_date, cache_dir=None):
                del symbol, config_payload, start_date, end_date, cache_dir
                if timeframe == "1h":
                    return {"timeframe": timeframe, "error": "injected worker failure"}
                raise AssertionError(f"unexpected worker timeframe: {timeframe}")

            monkeypatch.setattr(mtf_module, "_tf_worker_entry", _worker_entry)

        registry = ColumnGroupRegistry(tmp_path / generator_path)
        factory = _CgsaStubFactory({"12h": primary_data}, registry)
        generator = _build_mtf_generator(factory, config)

        if inject_primary_failure:
            def _fail_primary_pipeline(raw_data: pd.DataFrame):
                del raw_data
                raise RuntimeError("injected primary pipeline failure")

            monkeypatch.setattr(generator, "_run_tf_l1_l6_results", _fail_primary_pipeline)

    if not allow_partial:
        expected_match = (
            "injected primary pipeline failure"
            if inject_primary_failure
            else "Timeframe 1h failed"
        )
        with pytest.raises(RuntimeError, match=expected_match):
            generator.generate_multi_tf("BTCUSDT")
        return

    result = generator.generate_multi_tf("BTCUSDT")
    assert result.metadata["skipped_timeframes"] == ["1h"]
    assert result.metadata["actual_timeframes"] == ["12h"]
    assert "1h" in result.metadata["failed_timeframes"]


def test_inf_threshold_marks_partial_and_warmup_nan_is_allowed() -> None:
    factory = create_feature_factory(validate_continuity=False)
    config = _config()
    metadata = {"quality_status": "complete", "run_status": "complete", "failure_reasons": []}

    factory._apply_runtime_quality_gate(
        metadata,
        config,
        "BTCUSDT",
        "12h",
        nan_ratio=0.10,
        inf_ratio=0.001,
    )
    assert metadata["quality_status"] == "partial"

    warmup = {"quality_status": "complete", "run_status": "complete", "failure_reasons": []}
    factory._apply_runtime_quality_gate(
        warmup,
        config,
        "BTCUSDT",
        "12h",
        nan_ratio=0.10,
        inf_ratio=0.0,
    )
    assert warmup["quality_status"] == "complete"


def test_nan_threshold_marks_partial() -> None:
    factory = create_feature_factory(validate_continuity=False)
    config = _config(max_nan_ratio=0.01)
    metadata = {"quality_status": "complete", "run_status": "complete", "failure_reasons": []}

    factory._apply_runtime_quality_gate(
        metadata,
        config,
        "BTCUSDT",
        "12h",
        nan_ratio=0.10,
        inf_ratio=0.0,
    )

    assert metadata["quality_status"] == "partial"


def test_runtime_partial_flags_do_not_change_config_hash() -> None:
    factory = create_feature_factory(validate_continuity=False)
    baseline = _config()
    partial = _config(allow_partial_layers=True, allow_partial_timeframes=True)

    baseline_hash = factory._compute_config_hash(baseline, "BTCUSDT", "12h")
    partial_hash = factory._compute_config_hash(partial, "BTCUSDT", "12h")

    assert baseline_hash == partial_hash


def test_l65_failure_records_effective_config_and_continues() -> None:
    factory = create_feature_factory(validate_continuity=False)
    config = _config()
    frame = pd.DataFrame({"x": np.arange(8, dtype=np.float32)})

    def _boom(_frame, _config):
        raise RuntimeError("injected preprocessing failure")

    output = factory._execute_l65_with_degradation("Layer 6.5", _boom, frame, config)
    metadata = {"quality_status": "complete", "run_status": "complete", "failure_reasons": []}
    factory._apply_preprocessing_degradation_metadata(metadata)

    pd.testing.assert_frame_equal(output, frame)
    assert metadata["preprocessing_applied"] is False
    assert metadata["effective_preprocessing_config"]
    assert metadata["quality_status"] == "partial"


def _save_group(registry: ColumnGroupRegistry, group_id: str, timeframe: str) -> None:
    group = ColumnGroup(
        group_id=group_id,
        layer=LayerSource.L1,
        timeframe=timeframe,
        data_source="close",
        indicator="test",
        columns=(f"{group_id}_value",),
        shape=(4, 1),
        dtype="float32",
    )
    registry.save_data(group, np.arange(4, dtype=np.float32).reshape(-1, 1))


def test_rollback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    registry = ColumnGroupRegistry(tmp_path / "cgsa_work")
    _save_group(registry, "l1_1h_keep", "1h")
    _save_group(registry, "l1_4h_drop", "4h")
    _save_group(registry, "l2_4h_drop", "4h")
    expected_set = {"l1_1h_keep"}

    removed = registry.rollback_timeframe("4h")

    assert set(registry._groups) == expected_set
    assert set(removed) == {"l1_4h_drop", "l2_4h_drop"}
    assert not list((tmp_path / "cgsa_work").glob("*4h*.npy"))

    _save_group(registry, "l1_4h_fail", "4h")
    original_replace = __import__("os").replace

    def _fail_staging(source, target):
        if "l1_4h_fail" in str(source):
            raise OSError("injected rollback rename failure")
        return original_replace(source, target)

    monkeypatch.setattr("os.replace", _fail_staging)
    with pytest.raises(OSError, match="injected rollback rename failure"):
        registry.rollback_timeframe("4h")
    assert "l1_4h_fail" in registry._groups

    monkeypatch.setattr("os.replace", original_replace)
    original_unlink = Path.unlink

    def _fail_delete(path: Path, *args, **kwargs):
        if ".rollback-" in path.name:
            raise OSError("injected rollback delete failure")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", _fail_delete)
    with pytest.raises(OSError, match="injected rollback delete failure"):
        registry.rollback_timeframe("4h")


def _build_api_service_for_restore() -> FeatureFactoryService:
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._lock = threading.Lock()
    service._tasks = {}
    service._callbacks = {}
    return service


def test_api_restore_partial_manifest_maps_completed_degraded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """API restart：manifest quality_status=partial → task_status completed_degraded。"""
    monkeypatch.setattr(feature_service_module.settings, "data_cache_path", tmp_path)
    manifest_dir = tmp_path / "features" / "BTCUSDT" / "12h" / "deadbeef"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "feature_manifest.json").write_text(
        json.dumps({"quality_status": "partial", "total_features": 3}),
        encoding="utf-8",
    )

    service = _build_api_service_for_restore()
    service._restore_persisted_tasks()

    task = service._tasks["browse_BTCUSDT_12h"]
    assert task["status"] == "completed_degraded"


@pytest.mark.asyncio
async def test_api_generation_partial_maps_completed_degraded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """生成完成：summary.metadata.quality_status=partial → completed_degraded。"""
    service = _build_api_service_for_restore()
    task_id = "task-partial-quality"
    service._tasks[task_id] = {
        "task_id": task_id,
        "status": "running",
        "progress": 0.0,
        "current_stage": None,
        "completed_stages": [],
        "error": None,
        "result": None,
    }
    service._notify_callbacks = lambda *args, **kwargs: None
    service._persist_task_record = lambda *args, **kwargs: None
    service._start_stats_cache_warmup = lambda *args, **kwargs: None
    service._resolve_config_override = lambda override: override

    partial_result = SimpleNamespace(
        feature_count=1,
        generation_time=1.0,
        layer_counts={},
        metadata={"quality_status": "partial"},
        hdf5_path=str(tmp_path / "BTCUSDT_12h.h5"),
    )
    monkeypatch.setattr(service, "_generate_features_with_phase_d", lambda **kwargs: partial_result)

    request = SimpleNamespace(
        symbol="BTCUSDT",
        timeframe="12h",
        config_override=None,
        force_regenerate=False,
        start_date=None,
        end_date=None,
    )
    await service._run_task(task_id, request)

    assert service._tasks[task_id]["status"] == "completed_degraded"
