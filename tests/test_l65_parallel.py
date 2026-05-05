from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.preprocessing import feature_preprocessor as feature_preprocessor_module
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


def _build_group(
    group_id: str,
    n_rows: int,
    n_cols: int,
    layer: LayerSource = LayerSource.L2,
) -> ColumnGroup:
    columns = tuple(f"{group_id}_col_{index}" for index in range(n_cols))
    return ColumnGroup(
        group_id=group_id,
        layer=layer,
        timeframe="1h",
        data_source="close",
        indicator="mock",
        columns=columns,
        shape=(n_rows, n_cols),
        dtype="float32",
    )


def _make_registry_from_arrays(work_dir: Path, arrays: list[np.ndarray]) -> ColumnGroupRegistry:
    registry = ColumnGroupRegistry(work_dir=work_dir)
    for index, array in enumerate(arrays, start=1):
        group = _build_group(f"group_{index}", array.shape[0], array.shape[1])
        registry.save_data(group, array)
    return registry


def _make_registry_with_registered_groups(work_dir: Path, widths: list[int]) -> ColumnGroupRegistry:
    registry = ColumnGroupRegistry(work_dir=work_dir)
    for index, width in enumerate(widths, start=1):
        registry.register(_build_group(f"group_{index}", 16, width))
    return registry


def _make_registry_with_layers(work_dir: Path, specs: list[tuple[int, LayerSource]]) -> ColumnGroupRegistry:
    registry = ColumnGroupRegistry(work_dir=work_dir)
    for index, (width, layer) in enumerate(specs, start=1):
        data = np.ones((8, width), dtype=np.float32)
        registry.save_data(_build_group(f"group_{index}", 8, width, layer=layer), data)
    return registry


@pytest.fixture
def l65_config() -> dict:
    """建立 Batch 2 測試共用的 L6.5 設定。"""
    return {
        "mode": "replace",
        "winsorization": {
            "enabled": True,
            "method": "quantile",
            "quantile_range": [0.05, 0.95],
        },
        "rank_transform": {"enabled": True, "window": 5},
        "adaptive_zscore": {"enabled": True, "windows": [5], "epsilon": 1e-8},
        "fractional_differencing": {"enabled": False},
        "adf_differencing": {"enabled": False},
        "gaussian_normalize": {"enabled": False},
    }


@pytest.fixture
def feature_factory() -> FeatureFactory:
    """建立最小 FeatureFactory 實例供 Layer 6.5 接線測試使用。"""
    factory = FeatureFactory.__new__(FeatureFactory)
    factory._config_manager = Mock()
    factory._adapter_registry = Mock()
    factory._progress_callback = None
    factory._storage = Mock()
    factory._registry = Mock()
    factory._validator = Mock()
    factory._current_symbol = None
    factory._current_timeframe = None
    factory._current_config_hash = None
    factory._current_raw_data = None
    factory._reference_data_cache = {}
    factory._cgsa_registry = None
    return factory


def test_parallel_transform_matches_serial(tmp_path: Path, l65_config: dict) -> None:
    """測試平行 L6.5：4 workers 結果應與串行完全一致。"""
    rng = np.random.default_rng(7)
    arrays = [
        rng.normal(size=(24, 2)).astype(np.float32),
        rng.normal(size=(24, 4)).astype(np.float32),
        rng.normal(size=(24, 3)).astype(np.float32),
    ]
    arrays[0][0, 0] = np.nan
    arrays[1][1, 2] = np.nan

    serial_registry = _make_registry_from_arrays(tmp_path / "serial", arrays)
    parallel_registry = _make_registry_from_arrays(tmp_path / "parallel", arrays)

    serial_preprocessor = FeaturePreprocessor(l65_config)
    parallel_preprocessor = FeaturePreprocessor(l65_config)

    serial_completed = serial_preprocessor.transform_registry_groups(serial_registry, n_workers=1)
    parallel_completed = parallel_preprocessor.transform_registry_groups(parallel_registry, n_workers=4)

    assert serial_completed == len(arrays)
    assert parallel_completed == len(arrays)

    for index in range(1, len(arrays) + 1):
        group_id = f"group_{index}"
        serial_array = np.asarray(serial_registry.load_data(group_id), dtype=np.float32)
        parallel_array = np.asarray(parallel_registry.load_data(group_id), dtype=np.float32)
        assert np.allclose(serial_array, parallel_array, atol=1e-4, equal_nan=True)


def test_parallel_transform_all_groups_complete(tmp_path: Path, l65_config: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    """測試平行 L6.5：所有 groups 都應被處理完成。"""
    registry = _make_registry_with_registered_groups(tmp_path / "all_groups", [2, 4, 3, 5])
    preprocessor = FeaturePreprocessor(l65_config)

    monkeypatch.setattr(preprocessor, "_build_registry_transform_context", lambda: {"use_fast": False})
    monkeypatch.setattr(preprocessor, "_transform_single_group", lambda registry, group, context: None)

    completed = preprocessor.transform_registry_groups(registry, n_workers=4)

    assert completed == 4


def test_parallel_slow_path_chunks_only_large_groups(
    tmp_path: Path,
    l65_config: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試 slow path routing：只有超過 threshold 的 group 才走 chunked。"""
    registry = _make_registry_with_registered_groups(tmp_path / "slow_route", [2, 5])
    preprocessor = FeaturePreprocessor(l65_config)
    full_groups: list[str] = []
    chunked_groups: list[str] = []

    class _ImmediateFuture:
        def __init__(self, group_id: str) -> None:
            self._group_id = group_id

        def result(self) -> None:
            return None

    class _Executor:
        def __init__(self, max_workers: int) -> None:
            self.max_workers = max_workers

        def __enter__(self) -> "_Executor":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def submit(self, func, registry, group, context):
            full_groups.append(group.group_id)
            return _ImmediateFuture(group.group_id)

    monkeypatch.setattr(preprocessor, "_build_registry_transform_context", lambda: {"use_fast": False})
    monkeypatch.setattr(
        "momentum.FeatureEngineering.utils.hardware_utils.get_l65_split_threshold",
        lambda: 3,
    )
    monkeypatch.setattr(feature_preprocessor_module, "ThreadPoolExecutor", _Executor)
    monkeypatch.setattr(feature_preprocessor_module, "as_completed", lambda futures: list(futures))
    monkeypatch.setattr(preprocessor, "_transform_single_group", lambda registry, group, context: None)

    def fake_chunked(registry: ColumnGroupRegistry, group: ColumnGroup, chunk_size: int) -> None:
        chunked_groups.append(group.group_id)

    monkeypatch.setattr(preprocessor, "_transform_single_group_chunked", fake_chunked)

    completed = preprocessor.transform_registry_groups(registry, n_workers=2)

    assert completed == 2
    assert full_groups == ["group_1"]
    assert chunked_groups == ["group_2"]


def test_fracdiff_layer_parse_warning_is_aggregated(
    l65_config: dict,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """測試 FracDiff layer parse warning：不可 per-column 洗版。"""
    config = dict(l65_config)
    config["fractional_differencing"] = {"enabled": True}
    preprocessor = FeaturePreprocessor(config)
    preprocessor._fracdiff_apply_to_layers = frozenset({"L1"})

    with caplog.at_level("WARNING"):
        selected = preprocessor._filter_fracdiff_target_columns(
            ["close_1h_trend_EMA_5", "volume_1h_volume_OBV", "L1_valid_feature"]
        )

    warning_messages = [record.getMessage() for record in caplog.records]
    parse_warnings = [message for message in warning_messages if "Layer parse failed" in message]

    assert selected == ["L1_valid_feature"]
    assert len(parse_warnings) == 1
    assert "unparsed_columns=2/3" in parse_warnings[0]


def test_fracdiff_registry_layer_filter_uses_group_metadata(l65_config: dict) -> None:
    """測試 registry layer metadata 可直接決定 FracDiff 目標層。"""
    config = dict(l65_config)
    config["fractional_differencing"] = {"enabled": True}
    preprocessor = FeaturePreprocessor(config)
    preprocessor._fracdiff_apply_to_layers = frozenset({"L1", "L2"})

    assert preprocessor._filter_fracdiff_target_columns(
        ["unparseable_a", "unparseable_b"],
        source_layer="L2",
    ) == ["unparseable_a", "unparseable_b"]
    assert preprocessor._filter_fracdiff_target_columns(
        ["unparseable_a", "unparseable_b"],
        source_layer="L3",
    ) == []


def test_fracdiff_non_target_registry_group_stays_on_fast_path(
    tmp_path: Path,
    l65_config: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試 P2 mixed routing：FracDiff 非 target layer 仍可走 Numba fast path。"""
    registry = _make_registry_with_layers(
        tmp_path / "mixed_fast_slow",
        [(2, LayerSource.L1), (2, LayerSource.L3)],
    )
    preprocessor = FeaturePreprocessor(l65_config)
    preprocessor._fracdiff_apply_to_layers = frozenset({"L1"})
    fast_calls: list[tuple[int, int]] = []
    slow_layers: list[str] = []

    def fake_fast(array: np.ndarray, **kwargs) -> np.ndarray:
        del kwargs
        fast_calls.append(tuple(array.shape))
        return np.asarray(array, dtype=np.float32)

    monkeypatch.setattr(
        preprocessor,
        "_build_registry_transform_context",
        lambda: {
            "use_fast": False,
            "can_use_numba_fast": True,
            "transform_array_fast": fake_fast,
            "do_winsorize": False,
            "do_rank": False,
            "do_zscore": False,
            "do_fracdiff": True,
            "do_adf": False,
            "do_gaussian": False,
        },
    )
    monkeypatch.setattr(
        "momentum.FeatureEngineering.utils.hardware_utils.get_l65_split_threshold",
        lambda: 2000,
    )

    def fake_slow(frame: pd.DataFrame, source_layer=None) -> pd.DataFrame:
        slow_layers.append(str(source_layer))
        return frame

    monkeypatch.setattr(preprocessor, "_transform_single", fake_slow)

    completed = preprocessor.transform_registry_groups(registry, n_workers=2)

    assert completed == 2
    assert fast_calls == [(8, 2)]
    assert slow_layers == ["L1"]


def test_l65_transform_defers_manifest_rewrites(
    tmp_path: Path,
    l65_config: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試 P2 manifest batching：L6.5 多 group overwrite 只 flush manifest 一次。"""
    registry = _make_registry_with_registered_groups(tmp_path / "defer_manifest", [2, 3, 4])
    preprocessor = FeaturePreprocessor(l65_config)
    manifest_writes: list[str] = []

    monkeypatch.setattr(preprocessor, "_build_registry_transform_context", lambda: {"use_fast": False})
    monkeypatch.setattr(registry, "_write_manifest", lambda: manifest_writes.append("write"))

    def fake_transform(registry: ColumnGroupRegistry, group: ColumnGroup, context: dict) -> None:
        del context
        registry.overwrite_data(
            group.group_id,
            np.ones((group.n_rows, group.n_cols), dtype=np.float32),
        )

    monkeypatch.setattr(preprocessor, "_transform_single_group", fake_transform)

    completed = preprocessor.transform_registry_groups(registry, n_workers=1)

    assert completed == 3
    assert manifest_writes == ["write"]
    stats = registry.io_stats()
    assert stats["manifest_deferred_count"] == 3.0
    assert stats["manifest_write_count"] == 1.0


def test_tier_auto_selects_workers(
    feature_factory: FeatureFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試 Layer 6.5 呼叫端：8GB tier 應自動選擇 4 workers。"""
    captured: dict[str, int] = {}
    feature_factory._cgsa_registry = Mock(
        finalize=Mock(),
        all_column_names=Mock(return_value=[]),
    )
    config = SimpleNamespace(preprocessing=SimpleNamespace(model_dump=lambda: {}))

    monkeypatch.delenv("FFACT_L65_WORKERS", raising=False)
    monkeypatch.setattr(
        "momentum.FeatureEngineering.utils.hardware_utils.get_memory_tier",
        lambda: "8gb",
    )
    monkeypatch.setattr(
        "momentum.FeatureEngineering.utils.hardware_utils.get_tier_config",
        lambda tier: {"l65_workers": 4, "cgsa_memory_buffer": 0, "l7_workers": 4, "chunk_bars": 50_000},
    )

    def fake_transform_registry_groups(self: FeaturePreprocessor, registry: ColumnGroupRegistry, n_workers: int = 1) -> int:
        captured["n_workers"] = n_workers
        return 0

    monkeypatch.setattr(FeaturePreprocessor, "transform_registry_groups", fake_transform_registry_groups)

    feature_factory._layer6_5_preprocessing(pd.DataFrame(index=range(4)), config)

    assert captured["n_workers"] == 4
    feature_factory._cgsa_registry.finalize.assert_called_once()


def test_cgsa_buffer_batch_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """測試 CGSA buffer：buffer=4 時累積四組後才批次 flush。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path / "buffer_batch", memory_buffer_groups=4)
    saved_paths: list[object] = []

    monkeypatch.setattr(
        feature_preprocessor_module.np,
        "save",
        getattr(feature_preprocessor_module.np, "save"),
        raising=False,
    )
    monkeypatch.setattr(
        "momentum.FeatureEngineering.core.column_group_registry.np.save",
        lambda path, data, allow_pickle=False: saved_paths.append(path),
    )
    monkeypatch.setattr(registry, "_write_manifest_thread_safe", lambda: None)

    for index in range(3):
        registry.save_data(_build_group(f"buffer_{index}", 8, 2), np.ones((8, 2), dtype=np.float32))

    assert saved_paths == []

    registry.save_data(_build_group("buffer_4", 8, 2), np.ones((8, 2), dtype=np.float32))

    assert len(saved_paths) == 4
    assert len(registry._memory_buffer) == 0


def test_cgsa_buffer_finalize_flushes_remaining(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """測試 finalize：應 flush 剩餘 buffer 並清空暫存。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path / "buffer_finalize", memory_buffer_groups=4)
    saved_paths: list[object] = []

    monkeypatch.setattr(
        "momentum.FeatureEngineering.core.column_group_registry.np.save",
        lambda path, data, allow_pickle=False: saved_paths.append(path),
    )
    monkeypatch.setattr(registry, "_write_manifest_thread_safe", lambda: None)

    registry.save_data(_build_group("buffer_a", 8, 2), np.ones((8, 2), dtype=np.float32))
    registry.save_data(_build_group("buffer_b", 8, 2), np.ones((8, 2), dtype=np.float32))

    assert len(registry._memory_buffer) == 2

    registry.finalize()

    assert len(saved_paths) == 2
    assert len(registry._memory_buffer) == 0


def test_parallel_greedy_scheduling_largest_groups_first(
    tmp_path: Path,
    l65_config: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試 greedy scheduling：最大 group 應最先提交到 pool。"""
    registry = _make_registry_with_registered_groups(tmp_path / "greedy", [2, 7, 4, 5])
    preprocessor = FeaturePreprocessor(l65_config)
    submission_order: list[str] = []

    class _ImmediateFuture:
        def __init__(self, group_id: str) -> None:
            self._group_id = group_id

        def result(self) -> None:
            return None

    class _Executor:
        def __init__(self, max_workers: int) -> None:
            self.max_workers = max_workers

        def __enter__(self) -> "_Executor":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def submit(self, func, registry, group, context):
            submission_order.append(group.group_id)
            return _ImmediateFuture(group.group_id)

    monkeypatch.setattr(preprocessor, "_build_registry_transform_context", lambda: {"use_fast": False})
    monkeypatch.setattr(preprocessor, "_transform_single_group", lambda registry, group, context: None)
    monkeypatch.setattr(feature_preprocessor_module, "ThreadPoolExecutor", _Executor)
    monkeypatch.setattr(feature_preprocessor_module, "as_completed", lambda futures: list(futures))

    completed = preprocessor.transform_registry_groups(registry, n_workers=3)

    assert completed == 4
    assert submission_order == ["group_2", "group_4", "group_3", "group_1"]


def test_parallel_zero_groups(tmp_path: Path, l65_config: dict) -> None:
    """測試空 groups：應直接回傳 0，不得 crash。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path / "empty")
    preprocessor = FeaturePreprocessor(l65_config)

    assert preprocessor.transform_registry_groups(registry, n_workers=4) == 0


def test_parallel_single_group(tmp_path: Path, l65_config: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    """測試單一 group：平行路徑也應正常完成。"""
    registry = _make_registry_with_registered_groups(tmp_path / "single", [3])
    preprocessor = FeaturePreprocessor(l65_config)

    monkeypatch.setattr(preprocessor, "_build_registry_transform_context", lambda: {"use_fast": False})
    monkeypatch.setattr(preprocessor, "_transform_single_group", lambda registry, group, context: None)

    assert preprocessor.transform_registry_groups(registry, n_workers=4) == 1


def test_parallel_one_group_fails(tmp_path: Path, l65_config: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    """測試單一 group 失敗：其他 groups 應持續完成。"""
    registry = _make_registry_with_registered_groups(tmp_path / "fail_one", [2, 3, 4])
    preprocessor = FeaturePreprocessor(l65_config)

    monkeypatch.setattr(preprocessor, "_build_registry_transform_context", lambda: {"use_fast": False})

    def fake_transform(registry: ColumnGroupRegistry, group: ColumnGroup, context: dict) -> None:
        if group.group_id == "group_2":
            raise RuntimeError("boom")

    monkeypatch.setattr(preprocessor, "_transform_single_group", fake_transform)

    assert preprocessor.transform_registry_groups(registry, n_workers=3) == 2


def test_parallel_workers_1_is_serial(tmp_path: Path, l65_config: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    """測試 workers=1：必須走串行 fallback 路徑。"""
    registry = _make_registry_with_registered_groups(tmp_path / "serial_fallback", [2, 3])
    preprocessor = FeaturePreprocessor(l65_config)
    captured: dict[str, int] = {}

    monkeypatch.setattr(preprocessor, "_build_registry_transform_context", lambda: {"use_fast": False})

    def fake_serial(registry: ColumnGroupRegistry, groups: list[ColumnGroup], context: dict) -> int:
        captured["count"] = len(groups)
        return len(groups)

    monkeypatch.setattr(preprocessor, "_transform_registry_serial", fake_serial)

    assert preprocessor.transform_registry_groups(registry, n_workers=1) == 2
    assert captured["count"] == 2


def test_cgsa_buffer_zero_is_immediate_flush(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """測試 buffer=0：應保持立即寫入的舊行為。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path / "buffer_zero", memory_buffer_groups=0)
    saved_paths: list[object] = []

    monkeypatch.setattr(
        "momentum.FeatureEngineering.core.column_group_registry.np.save",
        lambda path, data, allow_pickle=False: saved_paths.append(path),
    )
    monkeypatch.setattr(registry, "_write_manifest_thread_safe", lambda: None)

    registry.save_data(_build_group("immediate", 8, 2), np.ones((8, 2), dtype=np.float32))

    assert len(saved_paths) == 1
    assert len(registry._memory_buffer) == 0


def test_cgsa_buffer_crash_loses_unflushed(tmp_path: Path) -> None:
    """測試未 finalize 即中斷：未 flush 的資料應僅停留在記憶體。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path / "buffer_crash", memory_buffer_groups=4)

    registry.save_data(_build_group("pending_a", 8, 2), np.ones((8, 2), dtype=np.float32))
    registry.save_data(_build_group("pending_b", 8, 2), np.ones((8, 2), dtype=np.float32))

    assert len(registry._memory_buffer) == 2
    assert not (registry.work_dir / "pending_a.npy").exists()
    assert not (registry.work_dir / "pending_b.npy").exists()


def test_numba_warmup_runs_before_process_pool_fanout(
    tmp_path: Path,
    l65_config: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試 warmup 順序：主執行緒 warmup 必須先於 worker 提交。"""
    registry = _make_registry_with_registered_groups(tmp_path / "warmup", [2, 3])
    preprocessor = FeaturePreprocessor(l65_config)
    call_order: list[str] = []

    class _ImmediateFuture:
        def result(self) -> None:
            return None

    class _Executor:
        def __init__(self, max_workers: int) -> None:
            self.max_workers = max_workers

        def __enter__(self) -> "_Executor":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def submit(self, func, registry, group, context):
            call_order.append("submit")
            return _ImmediateFuture()

    def fake_build_context() -> dict:
        preprocessor._warmup_numba_if_needed()
        return {"use_fast": False}

    monkeypatch.setattr(preprocessor, "_warmup_numba_if_needed", lambda: call_order.append("warmup"))
    monkeypatch.setattr(preprocessor, "_build_registry_transform_context", fake_build_context)
    monkeypatch.setattr(preprocessor, "_transform_single_group", lambda registry, group, context: None)
    monkeypatch.setattr(feature_preprocessor_module, "ThreadPoolExecutor", _Executor)
    monkeypatch.setattr(feature_preprocessor_module, "as_completed", lambda futures: list(futures))

    completed = preprocessor.transform_registry_groups(registry, n_workers=2)

    assert completed == 2
    assert call_order[0] == "warmup"
    assert call_order[1:] == ["submit", "submit"]