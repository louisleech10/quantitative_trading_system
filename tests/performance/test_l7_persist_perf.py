import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pytest

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering import feature_storage as feature_storage_module


def _build_group(group_id: str, n_rows: int, n_cols: int) -> ColumnGroup:
    columns = tuple(f"{group_id}_col_{index}" for index in range(n_cols))
    return ColumnGroup(
        group_id=group_id,
        layer=LayerSource.L3,
        timeframe="1h",
        data_source="close",
        indicator="mock",
        columns=columns,
        shape=(n_rows, n_cols),
        dtype="float32",
    )


def _make_registry(work_dir: Path, widths: list[int], n_rows: int = 64) -> ColumnGroupRegistry:
    registry = ColumnGroupRegistry(work_dir=work_dir)
    rng = np.random.default_rng(123)
    for index, width in enumerate(widths, start=1):
        group = _build_group(f"group_{index}", n_rows, width)
        registry.save_data(group, rng.normal(size=(n_rows, width)).astype(np.float32))
    return registry


def _make_part_item(base_dir: Path, part_id: str, n_rows: int = 64, n_cols: int = 2):
    rng = np.random.default_rng(abs(hash(part_id)) % (2 ** 32))
    arrays = [pa.array(rng.normal(size=n_rows).astype(np.float16)) for _ in range(n_cols)]
    table = pa.Table.from_arrays(arrays, names=[f"{part_id}_col_{idx}" for idx in range(n_cols)])
    return (part_id, table, base_dir / f"{part_id}.parquet", base_dir / f".{part_id}.staging.parquet")


@pytest.fixture
def storage(tmp_path: Path) -> FeatureStorage:
    """建立 Phase 4 效能驗證共用的 FeatureStorage。"""
    return FeatureStorage(base_path=str(tmp_path / "features"))


def test_l7_parallel_speedup(
    tmp_path: Path,
    storage: FeatureStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試平行 L7 persist：4 workers 應比 1 worker 至少快 2 倍。"""
    serial_dir = tmp_path / "serial_speed"
    parallel_dir = tmp_path / "parallel_speed"
    serial_dir.mkdir()
    parallel_dir.mkdir()

    original_write_table = feature_storage_module.pq.write_table

    def slow_write_table(table, destination, **kwargs):
        time.sleep(0.05)
        original_write_table(table, destination, **kwargs)

    monkeypatch.setattr(feature_storage_module.pq, "write_table", slow_write_table)

    serial_parts = [_make_part_item(serial_dir, f"serial_{index}") for index in range(1, 9)]
    parallel_parts = [_make_part_item(parallel_dir, f"parallel_{index}") for index in range(1, 9)]

    serial_started = time.perf_counter()
    storage._persist_parts_parallel(serial_parts, n_workers=1)
    serial_elapsed = time.perf_counter() - serial_started

    parallel_started = time.perf_counter()
    storage._persist_parts_parallel(parallel_parts, n_workers=4)
    parallel_elapsed = time.perf_counter() - parallel_started

    assert parallel_elapsed > 0
    assert serial_elapsed / parallel_elapsed >= 2.0


def test_async_compactor_controls_file_explosion(
    tmp_path: Path,
    storage: FeatureStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試 Async compactor：8GB tier 下 final parquet 檔數應壓到原始 parts 的 25% 以下。"""
    registry = _make_registry(tmp_path / "compactor_perf", [2] * 12)

    monkeypatch.setattr(
        "momentum.FeatureEngineering.utils.hardware_utils.get_memory_tier",
        lambda: "8gb",
    )
    monkeypatch.setattr(
        "momentum.FeatureEngineering.utils.hardware_utils.get_tier_config",
        lambda tier: {"l65_workers": 4, "cgsa_memory_buffer": 0, "l7_workers": 4, "chunk_bars": 50_000},
    )
    monkeypatch.setenv("FFACT_L7_COMPACTOR_ENABLED", "1")

    persisted_paths = storage.persist_registry_to_parquet("ETHUSDT", "cfg_perf", registry)

    assert len(persisted_paths) <= 3