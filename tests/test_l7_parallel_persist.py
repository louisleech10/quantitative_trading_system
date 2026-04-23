import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_storage import AsyncParquetCompactor, FeatureStorage
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


def _make_registry(work_dir: Path, widths: list[int], n_rows: int = 16) -> ColumnGroupRegistry:
    registry = ColumnGroupRegistry(work_dir=work_dir)
    rng = np.random.default_rng(42)
    for index, width in enumerate(widths, start=1):
        group = _build_group(f"group_{index}", n_rows, width)
        data = rng.normal(size=(n_rows, width)).astype(np.float32)
        registry.save_data(group, data)
    return registry


def _make_part_item(base_dir: Path, part_id: str, n_rows: int = 8, n_cols: int = 2):
    rng = np.random.default_rng(abs(hash(part_id)) % (2 ** 32))
    arrays = [pa.array(rng.normal(size=n_rows).astype(np.float16)) for _ in range(n_cols)]
    table = pa.Table.from_arrays(arrays, names=[f"{part_id}_col_{idx}" for idx in range(n_cols)])
    final_path = base_dir / f"{part_id}.parquet"
    staging_path = base_dir / f".{part_id}.staging.parquet"
    return (part_id, table, final_path, staging_path)


@pytest.fixture
def storage(tmp_path: Path) -> FeatureStorage:
    """建立 Phase 4 測試共用的 FeatureStorage。"""
    return FeatureStorage(base_path=str(tmp_path / "features"))


def test_parallel_persist_matches_serial(tmp_path: Path, storage: FeatureStorage) -> None:
    """測試平行 L7 persist：4 workers 的 parquet 內容應與串行一致。"""
    serial_dir = tmp_path / "serial"
    parallel_dir = tmp_path / "parallel"
    serial_dir.mkdir()
    parallel_dir.mkdir()

    serial_parts = [_make_part_item(serial_dir, f"part_{index}") for index in range(1, 5)]
    parallel_parts = [_make_part_item(parallel_dir, f"part_{index}") for index in range(1, 5)]

    serial_paths = storage._persist_parts_parallel(serial_parts, n_workers=1)
    parallel_paths = storage._persist_parts_parallel(parallel_parts, n_workers=4)

    assert len(serial_paths) == len(parallel_paths) == 4
    for serial_path, parallel_path in zip(sorted(serial_paths), sorted(parallel_paths)):
        serial_table = pq.read_table(serial_path)
        parallel_table = pq.read_table(parallel_path)
        assert serial_table.column_names == parallel_table.column_names
        assert serial_table.equals(parallel_table)


def test_parallel_persist_atomic_write(tmp_path: Path, storage: FeatureStorage, monkeypatch: pytest.MonkeyPatch) -> None:
    """測試平行 L7 persist：完成後只能留下 final 檔，不可殘留 staging 檔。"""
    part = _make_part_item(tmp_path, "atomic")
    observed: dict[str, bool] = {"saw_staging": False}
    original_write_table = feature_storage_module.pq.write_table

    def wrapped_write_table(table, destination, **kwargs):
        original_write_table(table, destination, **kwargs)
        observed["saw_staging"] = Path(destination).exists()

    monkeypatch.setattr(feature_storage_module.pq, "write_table", wrapped_write_table)

    results = storage._persist_parts_parallel([part], n_workers=1)

    assert len(results) == 1
    assert observed["saw_staging"] is True
    assert Path(results[0]).exists()
    assert not part[3].exists()


def test_tier_auto_selects_l7_workers(
    tmp_path: Path,
    storage: FeatureStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試 Layer 7 呼叫端：8GB tier 應自動選擇 4 workers。"""
    registry = _make_registry(tmp_path / "tier_workers", [2, 2, 2])
    captured: dict[str, int] = {}

    monkeypatch.delenv("FFACT_L7_WORKERS", raising=False)
    monkeypatch.setenv("FFACT_L7_COMPACTOR_ENABLED", "0")
    monkeypatch.setattr(
        "momentum.FeatureEngineering.utils.hardware_utils.get_memory_tier",
        lambda: "8gb",
    )
    monkeypatch.setattr(
        "momentum.FeatureEngineering.utils.hardware_utils.get_tier_config",
        lambda tier: {"l65_workers": 4, "cgsa_memory_buffer": 0, "l7_workers": 4, "chunk_bars": 50_000},
    )

    def fake_persist(parts_queue, n_workers, compactor=None):
        captured["n_workers"] = n_workers
        results = []
        for _part_id, table, final_path, staging_path in parts_queue:
            pq.write_table(table, str(staging_path), compression="zstd", compression_level=1)
            if compactor is None:
                final_path.parent.mkdir(parents=True, exist_ok=True)
                Path(staging_path).replace(final_path)
            results.append(str(final_path.resolve()))
        return results

    monkeypatch.setattr(storage, "_persist_parts_parallel", fake_persist)

    storage.persist_registry_to_parquet("ETHUSDT", "cfg_tier", registry)

    assert captured["n_workers"] == 4


def test_async_compactor_merges_small_files_into_large_parts(tmp_path: Path) -> None:
    """測試 Async compactor：多個小 parquet 應被合併成較少的 final 檔案。"""
    staging_dir = tmp_path / "staging"
    final_dir = tmp_path / "final"
    staging_dir.mkdir()
    final_dir.mkdir()
    compactor = AsyncParquetCompactor(staging_dir=staging_dir, final_dir=final_dir, min_files_to_compact=4)
    compactor.start()

    for index in range(1, 9):
        table = pa.Table.from_arrays(
            [pa.array(np.arange(16, dtype=np.float32))],
            names=[f"feature_{index}"],
        )
        staging_path = staging_dir / f"part_{index}.parquet"
        pq.write_table(table, str(staging_path), compression="zstd", compression_level=1)
        compactor.enqueue((f"part_{index}", staging_path))

    merged_paths = compactor.finalize()

    assert len(merged_paths) < 8
    assert not any(staging_dir.iterdir())


def test_async_compactor_manifest_tracks_sources(
    tmp_path: Path,
    storage: FeatureStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試 Async compactor：manifest 應記錄 merged parquet 與來源 part 對應。"""
    registry = _make_registry(tmp_path / "manifest_registry", [2] * 8)

    monkeypatch.setattr(
        "momentum.FeatureEngineering.utils.hardware_utils.get_memory_tier",
        lambda: "8gb",
    )
    monkeypatch.setattr(
        "momentum.FeatureEngineering.utils.hardware_utils.get_tier_config",
        lambda tier: {"l65_workers": 4, "cgsa_memory_buffer": 0, "l7_workers": 4, "chunk_bars": 50_000},
    )
    monkeypatch.setenv("FFACT_L7_COMPACTOR_ENABLED", "1")

    storage.persist_registry_to_parquet("ETHUSDT", "cfg_manifest", registry)
    manifest_path = Path(storage.base_path) / "ETHUSDT" / "cfg_manifest" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert "compaction" in manifest
    merged_files = manifest["compaction"]["merged_files"]
    assert merged_files
    source_parts = sorted(part_id for values in merged_files.values() for part_id in values)
    assert source_parts == [f"group_{index}" for index in range(1, 9)]


def test_parallel_persist_empty_queue(tmp_path: Path, storage: FeatureStorage) -> None:
    """測試空 queue：應直接回傳空列表。"""
    assert storage._persist_parts_parallel([], n_workers=4) == []


def test_parallel_persist_single_part(
    tmp_path: Path,
    storage: FeatureStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試單一 part：不得建立 ThreadPool，應走串行寫入。"""
    part = _make_part_item(tmp_path, "single")

    class FailIfConstructed:
        def __init__(self, max_workers: int) -> None:
            raise AssertionError("ThreadPoolExecutor should not be used for a single part")

    monkeypatch.setattr(feature_storage_module, "ThreadPoolExecutor", FailIfConstructed)

    results = storage._persist_parts_parallel([part], n_workers=4)

    assert len(results) == 1
    assert Path(results[0]).exists()


def test_parallel_persist_disk_full(
    tmp_path: Path,
    storage: FeatureStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試磁碟滿：應直接 raise OSError，不可 silent fail。"""
    part = _make_part_item(tmp_path, "disk_full")

    monkeypatch.setattr(
        feature_storage_module.pq,
        "write_table",
        lambda table, destination, **kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    with pytest.raises(OSError, match="disk full"):
        storage._persist_parts_parallel([part], n_workers=2)


def test_l7_workers_env_override(
    tmp_path: Path,
    storage: FeatureStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試 L7 workers env override：應優先使用環境變數設定值。"""
    registry = _make_registry(tmp_path / "workers_override", [2, 2, 2])
    captured: dict[str, int] = {}

    monkeypatch.setenv("FFACT_L7_WORKERS", "2")
    monkeypatch.setenv("FFACT_L7_COMPACTOR_ENABLED", "0")
    monkeypatch.setattr(
        "momentum.FeatureEngineering.utils.hardware_utils.get_memory_tier",
        lambda: "32gb",
    )
    monkeypatch.setattr(
        "momentum.FeatureEngineering.utils.hardware_utils.get_tier_config",
        lambda tier: {"l65_workers": 4, "cgsa_memory_buffer": 0, "l7_workers": 8, "chunk_bars": 50_000},
    )

    def fake_persist(parts_queue, n_workers, compactor=None):
        captured["n_workers"] = n_workers
        return []

    monkeypatch.setattr(storage, "_persist_parts_parallel", fake_persist)

    storage.persist_registry_to_parquet("ETHUSDT", "cfg_workers_override", registry)

    assert captured["n_workers"] == 2


def test_async_compactor_disabled_bypasses_merge(
    tmp_path: Path,
    storage: FeatureStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試停用 compactor：不得建立背景 compactor，應直接輸出 parquet parts。"""
    registry = _make_registry(tmp_path / "compactor_disabled", [2, 2, 2])
    created = {"called": False}

    def fail_compactor(*args, **kwargs):
        created["called"] = True
        raise AssertionError("Compactor should be bypassed when disabled")

    monkeypatch.setattr(feature_storage_module, "AsyncParquetCompactor", fail_compactor)
    monkeypatch.setenv("FFACT_L7_COMPACTOR_ENABLED", "0")

    storage.persist_registry_to_parquet("ETHUSDT", "cfg_compactor_disabled", registry)

    parquet_files = list((Path(storage.base_path) / "ETHUSDT" / "cfg_compactor_disabled").glob("*.parquet"))
    assert created["called"] is False
    assert len(parquet_files) == 3


def test_async_compactor_finalize_flushes_remaining_files(tmp_path: Path) -> None:
    """測試 finalize：未達 batch 門檻的 staging 檔也必須被排空。"""
    staging_dir = tmp_path / "flush_staging"
    final_dir = tmp_path / "flush_final"
    staging_dir.mkdir()
    final_dir.mkdir()
    compactor = AsyncParquetCompactor(staging_dir=staging_dir, final_dir=final_dir, min_files_to_compact=8)
    compactor.start()

    for index in range(1, 3):
        table = pa.Table.from_arrays(
            [pa.array(np.arange(16, dtype=np.float32))],
            names=[f"flush_{index}"],
        )
        staging_path = staging_dir / f"flush_{index}.parquet"
        pq.write_table(table, str(staging_path), compression="zstd", compression_level=1)
        compactor.enqueue((f"flush_{index}", staging_path))

    merged_paths = compactor.finalize()

    assert merged_paths
    assert not any(staging_dir.iterdir())


def test_async_compactor_crash_preserves_staging_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """測試 compactor merge crash：staging 檔必須保留，final 不可部分覆寫。"""
    staging_dir = tmp_path / "crash_staging"
    final_dir = tmp_path / "crash_final"
    staging_dir.mkdir()
    final_dir.mkdir()
    compactor = AsyncParquetCompactor(staging_dir=staging_dir, final_dir=final_dir, min_files_to_compact=2)
    compactor.start()

    for index in range(1, 3):
        table = pa.Table.from_arrays(
            [pa.array(np.arange(8, dtype=np.float32))],
            names=[f"crash_{index}"],
        )
        staging_path = staging_dir / f"crash_{index}.parquet"
        pq.write_table(table, str(staging_path), compression="zstd", compression_level=1)
        compactor.enqueue((f"crash_{index}", staging_path))

    monkeypatch.setattr(
        compactor,
        "_merge_batch",
        lambda batch: (_ for _ in ()).throw(OSError("merge failed")),
    )

    with pytest.raises(RuntimeError, match="failed"):
        compactor.finalize()

    assert len(list(staging_dir.glob("*.parquet"))) == 2
    assert list(final_dir.glob("*.parquet")) == []
