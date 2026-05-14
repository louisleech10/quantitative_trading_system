from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from momentum.FeatureEngineering.core.column_group import AlignmentMeta, ColumnGroup, LayerSource, ShardMeta
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_config import AlignmentMode
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator


def _write_idx_map(path: Path, idx_map: np.ndarray) -> Path:
    with path.open("wb") as handle:
        np.save(handle, np.asarray(idx_map, dtype=np.int32), allow_pickle=False)
    return path


def _compact_group(
    tmp_path: Path,
    source: np.ndarray,
    idx_map: np.ndarray,
    group_id: str = "12h_L1_compact",
) -> tuple[ColumnGroupRegistry, np.ndarray]:
    registry = ColumnGroupRegistry(tmp_path / "work")
    source_path = registry.work_dir / f"{group_id}.npy"
    np.save(source_path, source, allow_pickle=False)
    idx_map_path = _write_idx_map(registry.work_dir / ".align_12h_to_1h_close_time.npy", idx_map)
    group = ColumnGroup(
        group_id=group_id,
        layer=LayerSource.L1,
        timeframe="12h",
        data_source="close",
        indicator="TEST",
        columns=("a", "b"),
        shape=(len(idx_map), source.shape[1]),
        dtype="float32",
        disk_path=source_path,
        alignment=AlignmentMeta(
            source_timeframe="12h",
            primary_timeframe="1h",
            source_n_rows=source.shape[0],
            primary_n_rows=len(idx_map),
            idx_map_path=idx_map_path,
            alignment_mode="close_time",
            offset_ns=0,
        ),
    )
    registry.register(group)
    registry.write_manifest()
    expected = MultiTFGenerator._align_group_array(source, idx_map.astype(np.int64), len(idx_map))
    return registry, expected


def test_compact_group_load_data_matches_dense_alignment(tmp_path: Path) -> None:
    source = np.array([[1.0, 10.0], [2.0, 20.0], [np.nan, 30.0]], dtype=np.float32)
    idx_map = np.array([-1, 0, 0, 1, 2], dtype=np.int32)
    registry, expected = _compact_group(tmp_path, source, idx_map)

    loaded = registry.load_data("12h_L1_compact")

    assert registry.get("12h_L1_compact").is_compact_aligned
    np.testing.assert_array_equal(loaded, expected)


def test_compact_iter_shards_yields_logical_rows_with_physical_bytes(tmp_path: Path) -> None:
    source = np.array([[1.0, 10.0], [2.0, 20.0]], dtype=np.float32)
    idx_map = np.array([0, 0, 1, 1], dtype=np.int32)
    registry, expected = _compact_group(tmp_path, source, idx_map)

    [(meta, shard_arr, columns)] = list(registry.iter_shards("12h_L1_compact"))
    group = registry.get("12h_L1_compact")

    assert meta.n_rows == len(idx_map)
    assert group.physical_n_rows == source.shape[0]
    assert group.logical_n_rows == expected.shape[0]
    assert meta.nbytes == group.disk_path.stat().st_size
    assert tuple(columns) == ("a", "b")
    np.testing.assert_array_equal(np.asarray(shard_arr), expected)


def test_parallel_worker_registration_uses_compact_alignment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FFACT_MULTI_TF_COMPACT_ALIGNMENT", "1")
    registry = ColumnGroupRegistry(tmp_path / "main_work", memory_buffer_groups=0)
    worker_dir = tmp_path / "BTCUSDT_12h_worker"
    worker_dir.mkdir()
    worker_npy = worker_dir / "12h_L1_test.npy"
    source = np.array([[1.0, 10.0], [2.0, 20.0], [3.0, 30.0]], dtype=np.float32)
    np.save(worker_npy, source, allow_pickle=False)

    primary_timestamps = pd.date_range("2026-01-01", periods=5, freq="h")
    source_timestamps_ms = np.array(
        [
            int(primary_timestamps[0].value // 1_000_000),
            int(primary_timestamps[2].value // 1_000_000),
            int(primary_timestamps[4].value // 1_000_000),
        ],
        dtype=np.int64,
    )
    groups_data = [
        {
            "group_id": "12h_L1_test",
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
    generator._primary_tf = "1h"
    generator._register_worker_groups(
        registry,
        groups_data,
        "12h",
        primary_timestamps,
        AlignmentMode.CLOSE_TIME,
        source_timestamps_ms=source_timestamps_ms,
    )

    persisted = registry.get("12h_L1_test")
    expected_idx = np.array([0, 0, 1, 1, 2], dtype=np.int64)
    expected = MultiTFGenerator._align_group_array(source, expected_idx, n_primary=5)

    assert persisted.is_compact_aligned
    assert persisted.shape == (5, 2)
    assert persisted.physical_n_rows == 3
    assert not worker_npy.exists()
    assert not worker_dir.exists()
    np.testing.assert_array_equal(registry.load_data("12h_L1_test"), expected)


def test_parallel_worker_registration_compact_sharded_group(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FFACT_MULTI_TF_COMPACT_ALIGNMENT", "1")
    registry = ColumnGroupRegistry(tmp_path / "main_work", memory_buffer_groups=0)
    worker_dir = tmp_path / "ETHUSDT_12h_worker"
    worker_dir.mkdir()
    source = np.array([[1.0, 10.0], [2.0, 20.0]], dtype=np.float32)
    shard0 = worker_dir / "12h_L2_test.shard00.npy"
    shard1 = worker_dir / "12h_L2_test.shard01.npy"
    np.save(shard0, source[:, 0:1], allow_pickle=False)
    np.save(shard1, source[:, 1:2], allow_pickle=False)

    primary_timestamps = pd.date_range("2026-01-01", periods=4, freq="h")
    source_timestamps_ms = np.array(
        [
            int(primary_timestamps[0].value // 1_000_000),
            int(primary_timestamps[2].value // 1_000_000),
        ],
        dtype=np.int64,
    )
    groups_data = [
        {
            "group_id": "12h_L2_test",
            "layer": "L2",
            "timeframe": "12h",
            "data_source": "derived",
            "indicator": "TEST",
            "columns": ["a", "b"],
            "shape": [2, 2],
            "dtype": "float32",
            "shards": [
                {"shard_idx": 0, "col_start": 0, "col_end": 1, "n_rows": 2, "nbytes": source[:, 0:1].nbytes, "path": str(shard0)},
                {"shard_idx": 1, "col_start": 1, "col_end": 2, "n_rows": 2, "nbytes": source[:, 1:2].nbytes, "path": str(shard1)},
            ],
        }
    ]

    generator = MultiTFGenerator.__new__(MultiTFGenerator)
    generator._primary_tf = "1h"
    generator._register_worker_groups(
        registry,
        groups_data,
        "12h",
        primary_timestamps,
        AlignmentMode.CLOSE_TIME,
        source_timestamps_ms=source_timestamps_ms,
    )

    persisted = registry.get("12h_L2_test")
    expected = MultiTFGenerator._align_group_array(source, np.array([0, 0, 1, 1]), n_primary=4)

    assert persisted.is_compact_aligned
    assert len(persisted.shards) == 2
    assert all(shard.disk_path.exists() for shard in persisted.shards)
    np.testing.assert_array_equal(registry.load_data("12h_L2_test"), expected)


def test_resume_skips_compact_group_when_idx_map_missing(tmp_path: Path) -> None:
    source = np.array([[1.0, 2.0]], dtype=np.float32)
    idx_map = np.array([0, 0], dtype=np.int32)
    registry, _expected = _compact_group(tmp_path, source, idx_map)
    idx_map_path = registry.get("12h_L1_compact").alignment.idx_map_path
    idx_map_path.unlink()

    resumed = ColumnGroupRegistry.resume_from_manifest(registry.work_dir)

    assert "12h_L1_compact" not in [group_id for group_id, _group in resumed.iter_all()]


def test_manifest_contains_alignment_metadata(tmp_path: Path) -> None:
    source = np.array([[1.0, 2.0]], dtype=np.float32)
    idx_map = np.array([0, 0], dtype=np.int32)
    registry, _expected = _compact_group(tmp_path, source, idx_map)

    payload = json.loads((registry.work_dir / "manifest.json").read_text())
    alignment = payload["groups"][0]["alignment"]

    assert alignment["source_timeframe"] == "12h"
    assert alignment["primary_timeframe"] == "1h"
    assert alignment["source_n_rows"] == 1
    assert alignment["primary_n_rows"] == 2
    assert alignment["idx_map_path"].startswith(".align_12h_to_1h")


def test_l7_raw_stream_passthrough_compact_matches_dense_alignment(tmp_path: Path) -> None:
    registry = ColumnGroupRegistry(tmp_path / "work")
    source = np.array([[1.0, 10.0], [2.0, 20.0]], dtype=np.float32)
    idx_map = np.array([-1, 0, 0, 1], dtype=np.int32)
    source_path = registry.work_dir / "12h_L1_trend_TEST.npy"
    np.save(source_path, source, allow_pickle=False)
    idx_map_path = _write_idx_map(registry.work_dir / ".align_12h_to_1h_close_time.npy", idx_map)
    group = ColumnGroup(
        group_id="12h_L1_trend_TEST",
        layer=LayerSource.L1,
        timeframe="12h",
        data_source="close",
        indicator="TEST",
        columns=("close_trend_TEST_a", "close_trend_TEST_b"),
        shape=(len(idx_map), 2),
        dtype="float32",
        disk_path=source_path,
        alignment=AlignmentMeta(
            source_timeframe="12h",
            primary_timeframe="1h",
            source_n_rows=source.shape[0],
            primary_n_rows=len(idx_map),
            idx_map_path=idx_map_path,
            alignment_mode="close_time",
            offset_ns=0,
        ),
    )
    registry.register(group)
    registry.write_manifest()

    storage = FeatureStorage(str(tmp_path / "features"))
    raw_path, summary = storage.write_raw_from_registry_stream(
        symbol="BTCUSDT",
        tf="1h",
        config_hash="compacthash",
        registry=registry,
        preprocessor=None,
        cleanup_intermediate=False,
        l65_mode="none",
    )

    parquet_files = sorted(raw_path.glob("*.parquet"))
    assert parquet_files
    frame = pd.concat([pd.read_parquet(path) for path in parquet_files], axis=1)
    expected = MultiTFGenerator._align_group_array(source, idx_map.astype(np.int64), n_primary=len(idx_map))

    assert summary["row_count"] == len(idx_map)
    assert summary["feature_count"] == 2
    assert "close_12h_trend_TEST_a" in frame.columns
    assert "close_12h_trend_TEST_b" in frame.columns
    np.testing.assert_array_equal(frame["close_12h_trend_TEST_a"].to_numpy(dtype=np.float32), expected[:, 0])
    np.testing.assert_array_equal(frame["close_12h_trend_TEST_b"].to_numpy(dtype=np.float32), expected[:, 1])


def test_l65_raw_sink_compact_sharded_matches_dense_alignment(tmp_path: Path) -> None:
    registry = ColumnGroupRegistry(tmp_path / "work")
    source = np.array([[1.0, 10.0], [2.0, 20.0]], dtype=np.float32)
    idx_map = np.array([-1, 0, 0, 1], dtype=np.int32)
    shard0 = registry.work_dir / "12h_L2_compact.shard00.npy"
    shard1 = registry.work_dir / "12h_L2_compact.shard01.npy"
    np.save(shard0, source[:, 0:1], allow_pickle=False)
    np.save(shard1, source[:, 1:2], allow_pickle=False)
    idx_map_path = _write_idx_map(registry.work_dir / ".align_12h_to_1h_close_time.npy", idx_map)

    group = ColumnGroup(
        group_id="12h_L2_compact",
        layer=LayerSource.L2,
        timeframe="12h",
        data_source="derived",
        indicator="TEST",
        columns=("a", "b"),
        shape=(len(idx_map), 2),
        dtype="float32",
        shards=(
            ShardMeta(0, 0, 1, source.shape[0], shard0, int(source[:, 0:1].nbytes)),
            ShardMeta(1, 1, 2, source.shape[0], shard1, int(source[:, 1:2].nbytes)),
        ),
        alignment=AlignmentMeta(
            source_timeframe="12h",
            primary_timeframe="1h",
            source_n_rows=source.shape[0],
            primary_n_rows=len(idx_map),
            idx_map_path=idx_map_path,
            alignment_mode="close_time",
            offset_ns=0,
        ),
    )
    registry.register(group)

    config = {
        "mode": "replace",
        "winsorization": {"enabled": False},
        "rank_transform": {"enabled": False},
        "adaptive_zscore": {"enabled": False},
        "fractional_differencing": {"enabled": False},
        "adf_differencing": {"enabled": False},
        "gaussian_normalize": {"enabled": False},
    }
    preprocessor = FeaturePreprocessor(config)
    outputs: list[tuple[str, list[str], np.ndarray, bool]] = []

    def sink(group_id, columns, data, source_group_id, source_disk_path, cleanup_source):
        del source_group_id, source_disk_path
        outputs.append((group_id, list(columns), np.asarray(data, dtype=np.float32), bool(cleanup_source)))

    completed = preprocessor.transform_registry_groups_to_sink(registry, sink, n_workers=1)
    expected = MultiTFGenerator._align_group_array(source, idx_map.astype(np.int64), n_primary=len(idx_map))

    assert completed == 1
    assert len(outputs) == 2
    assert outputs[0][1] == ["a"]
    assert outputs[1][1] == ["b"]
    assert outputs[0][3] is False
    assert outputs[1][3] is True
    reconstructed = np.column_stack([outputs[0][2], outputs[1][2]])
    np.testing.assert_array_equal(reconstructed, expected)
