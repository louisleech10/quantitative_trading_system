import json
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_config import PreprocessingConfig
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


def _build_group(group_id: str, shape: tuple[int, int], layer: LayerSource = LayerSource.L2) -> ColumnGroup:
    columns = tuple(f"{group_id}_col_{index}" for index in range(shape[1]))
    return ColumnGroup(
        group_id=group_id,
        layer=layer,
        timeframe="1h",
        data_source="derived",
        indicator="mock",
        columns=columns,
        shape=shape,
        dtype="float32",
    )


def _make_registry(tmp_path: Path, group_id: str = "group_1") -> ColumnGroupRegistry:
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    data = np.array(
        [
            [1.0, 10.0, 100.0],
            [2.0, 20.0, 200.0],
            [3.0, 30.0, 300.0],
            [1000.0, 40.0, 400.0],
        ],
        dtype=np.float32,
    )
    registry.save_data(_build_group(group_id, data.shape), data)
    return registry


def _preprocessor_config(*, ic_first: bool = False) -> dict:
    config = PreprocessingConfig(
        enabled=True,
        mode="replace",
        ic_first_pipeline=ic_first,
        winsorization={
            "enabled": True,
            "method": "quantile",
            "quantile_range": [0.0, 0.75],
            "apply_to": "all",
        },
        fractional_differencing={"enabled": False},
        adf_differencing={"enabled": False},
        rank_transform={"enabled": False, "window": 3, "apply_to": "all"},
        adaptive_zscore={"enabled": False, "windows": [3], "apply_to": "all"},
        gaussian_normalize={"enabled": False, "apply_to": "all"},
    )
    return config.model_dump()


def test_raw_streaming_transforms_without_registry_overwrite(tmp_path, monkeypatch) -> None:
    registry = _make_registry(tmp_path)
    source_path = registry.get("group_1").disk_path
    storage = FeatureStorage(str(tmp_path / "features"))
    preprocessor = FeaturePreprocessor(_preprocessor_config())

    def fail_overwrite(*args, **kwargs):
        raise AssertionError("raw streaming path must not overwrite registry .npy")

    monkeypatch.setattr(registry, "overwrite_data", fail_overwrite)

    raw_dir, summary = storage.write_raw_from_registry_stream(
        symbol="SYNTHETIC",
        tf="1h",
        config_hash="cfg_stream",
        registry=registry,
        preprocessor=preprocessor,
        cleanup_intermediate=True,
        l65_mode="legacy",
    )

    assert raw_dir == tmp_path / "features" / "SYNTHETIC" / "1h" / "cfg_stream" / "raw"
    assert raw_dir.exists()
    assert source_path is not None and not source_path.exists()
    assert summary["feature_count"] == 3
    assert summary["npy_freed_bytes"] > 0
    assert not (raw_dir.parent / "processed").exists()

    manifest = json.loads((raw_dir.parent / "feature_manifest.json").read_text(encoding="utf-8"))
    assert manifest["complete"] is True
    assert manifest["artifacts"]["raw"]["schema_version"] == "raw_v1"
    assert manifest["generation_metadata"]["l65_mode"] == "legacy"
    assert manifest["generation_metadata"]["cleanup_intermediate"] is True

    schema = pq.read_schema(raw_dir / "group_1.parquet")
    assert schema.metadata[b"schema_version"] == b"raw_v1"
    assert schema.metadata[b"artifact_kind"] == b"raw"


def test_raw_streaming_logs_start_and_task_heartbeat(tmp_path, caplog) -> None:
    registry = _make_registry(tmp_path)
    preprocessor = FeaturePreprocessor(_preprocessor_config())
    captured_outputs = []

    def sink(output_group_id, columns, data, source_group_id, source_disk_path, cleanup_source):
        captured_outputs.append(
            {
                "output_group_id": output_group_id,
                "columns": list(columns),
                "shape": tuple(data.shape),
                "source_group_id": source_group_id,
                "source_disk_path": source_disk_path,
                "cleanup_source": cleanup_source,
            }
        )

    logger_name = "momentum.FeatureEngineering.preprocessing.feature_preprocessor"
    with caplog.at_level(logging.INFO, logger=logger_name):
        completed = preprocessor.transform_registry_groups_to_sink(registry, sink, n_workers=2)

    assert completed == 1
    assert len(captured_outputs) == 1
    assert captured_outputs[0]["shape"] == (4, 3)
    assert captured_outputs[0]["cleanup_source"] is True

    log_text = caplog.text
    assert "[L6.5] raw-sink path uses serial group streaming" in log_text
    assert "Registry raw-sink config: groups=1 requested_workers=2 effective_workers=1" in log_text
    assert "use_fast=" in log_text
    assert "fracdiff_apply_to=" in log_text
    assert "[L6.5] Raw-sink start:" in log_text
    assert "sub-tasks" in log_text
    assert "[L6.5] raw-sink heartbeat: tasks 1/1 (100.0%), groups 1/1" in log_text
    assert "rate=" in log_text
    assert "ETA=" in log_text
    assert "last=group_1 (full)" in log_text


def test_raw_streaming_slow_chunked_groups_stream_chunks(tmp_path, monkeypatch, caplog) -> None:
    registry = _make_registry(tmp_path, group_id="wide_group")
    preprocessor = FeaturePreprocessor(_preprocessor_config())
    captured_outputs = []

    def sink(output_group_id, columns, data, source_group_id, source_disk_path, cleanup_source):
        captured_outputs.append(
            {
                "group_id": output_group_id,
                "columns": list(columns),
                "shape": tuple(data.shape),
                "source_group_id": source_group_id,
                "source_disk_path": source_disk_path,
                "cleanup_source": cleanup_source,
            }
        )

    def fail_old_chunk_concat(*args, **kwargs):
        raise AssertionError("raw-sink must stream chunk outputs instead of concatenating them")

    from momentum.FeatureEngineering.utils import hardware_utils

    monkeypatch.setattr(hardware_utils, "get_l65_split_threshold", lambda: 2)
    monkeypatch.setattr(preprocessor, "_group_requires_slow_transform", lambda _group, _context: True)
    monkeypatch.setattr(preprocessor, "_transform_single_group_chunked_to_arrays", fail_old_chunk_concat)

    logger_name = "momentum.FeatureEngineering.preprocessing.feature_preprocessor"
    with caplog.at_level(logging.INFO, logger=logger_name):
        completed = preprocessor.transform_registry_groups_to_sink(registry, sink, n_workers=1)

    assert completed == 1
    assert [output["group_id"] for output in captured_outputs] == [
        "wide_group_chunk1",
        "wide_group_chunk2",
    ]
    assert [output["shape"] for output in captured_outputs] == [(4, 2), (4, 1)]
    assert [output["cleanup_source"] for output in captured_outputs] == [False, True]
    assert all(output["source_group_id"] == "wide_group" for output in captured_outputs)

    log_text = caplog.text
    assert "raw-sink chunk stream start: group=wide_group" in log_text
    assert "raw-sink chunk stream complete: group=wide_group chunks=2 outputs=2" in log_text
    assert "last=wide_group (slow-chunked, parts=2)" in log_text


def test_raw_streaming_schedules_largest_sources_first(tmp_path, monkeypatch) -> None:
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    registry.save_data(_build_group("a_small", (4, 1)), np.ones((4, 1), dtype=np.float32))
    registry.save_data(_build_group("z_large", (4, 4)), np.ones((4, 4), dtype=np.float32))
    preprocessor = FeaturePreprocessor(_preprocessor_config())
    output_order = []

    def sink(output_group_id, columns, data, source_group_id, source_disk_path, cleanup_source):
        output_order.append(output_group_id)

    monkeypatch.setenv("FFACT_L65_RAW_SINK_LARGEST_FIRST", "1")

    completed = preprocessor.transform_registry_groups_to_sink(registry, sink, n_workers=1)

    assert completed == 2
    assert output_order == ["z_large", "a_small"]


class _FakeDiskPath:
    def __init__(self, size: int) -> None:
        self._size = size

    def exists(self) -> bool:
        return True

    def stat(self) -> SimpleNamespace:
        return SimpleNamespace(st_size=self._size)


def test_raw_streaming_disk_precheck_uses_largest_part_not_largest_group(monkeypatch, tmp_path) -> None:
    storage = FeatureStorage(str(tmp_path / "features"))
    monkeypatch.setattr(storage, "MAX_GROUP_COLUMNS", 2)
    monkeypatch.setenv("FFACT_L7_DISK_SAFETY_FACTOR", "1.0")
    monkeypatch.setenv("FFACT_L7_MIN_FREE_GIB", "0")

    group = SimpleNamespace(
        shape=(100, 10),
        disk_path=_FakeDiskPath(4_000),
    )
    groups = [("wide_group", group)]

    monkeypatch.setattr(storage, "_safe_disk_free_bytes", lambda _path: 900)
    storage._precheck_l7_raw_stream_disk_space(tmp_path / "features", groups)

    monkeypatch.setattr(storage, "_safe_disk_free_bytes", lambda _path: 100)
    try:
        storage._precheck_l7_raw_stream_disk_space(tmp_path / "features", groups)
        assert False, "Expected raw streaming disk precheck to fail"
    except OSError as exc:
        message = str(exc)
        assert "Insufficient disk space for L7_raw streaming persist" in message
        assert "max_inflight_part" in message


def test_raw_streaming_disk_precheck_enforces_min_free_floor(monkeypatch, tmp_path) -> None:
    storage = FeatureStorage(str(tmp_path / "features"))
    monkeypatch.setenv("FFACT_L7_DISK_SAFETY_FACTOR", "1.0")
    monkeypatch.setenv("FFACT_L7_MIN_FREE_GIB", "1")

    group = SimpleNamespace(
        shape=(10, 2),
        disk_path=_FakeDiskPath(4_000),
    )
    groups = [("small_group", group)]

    monkeypatch.setattr(storage, "_safe_disk_free_bytes", lambda _path: 512 * 1024 ** 2)
    try:
        storage._precheck_l7_raw_stream_disk_space(tmp_path / "features", groups)
        assert False, "Expected raw streaming disk precheck to enforce the reserve floor"
    except OSError as exc:
        message = str(exc)
        assert "reserve_floor=1.00 GiB" in message


def test_raw_streaming_part_disk_guard_enforces_min_free_floor(monkeypatch, tmp_path) -> None:
    storage = FeatureStorage(str(tmp_path / "features"))
    monkeypatch.setenv("FFACT_L7_DISK_SAFETY_FACTOR", "1.0")
    monkeypatch.setenv("FFACT_L7_MIN_FREE_GIB", "1")
    monkeypatch.setattr(storage, "_safe_disk_free_bytes", lambda _path: 512 * 1024 ** 2)

    try:
        storage._ensure_l7_raw_part_disk_space(
            tmp_path / "features",
            part_id="part_1",
            source_group_id="wide_group",
            part_estimate_bytes=128,
        )
        assert False, "Expected raw streaming part guard to fail"
    except OSError as exc:
        message = str(exc)
        assert "Insufficient disk space for L7_raw parquet part" in message
        assert "part_id=part_1" in message
        assert "source_group_id=wide_group" in message


def test_feature_factory_cgsa_generation_routes_to_l7_raw_writer(tmp_path) -> None:
    registry = _make_registry(tmp_path)
    raw_path = tmp_path / "features" / "SYNTHETIC" / "1h" / "cfg_raw" / "raw"
    storage = Mock(spec=FeatureStorage)
    storage.write_raw_from_registry_stream.return_value = (
        raw_path,
        {
            "raw_path": str(raw_path),
            "manifest_path": str(raw_path.parent / "feature_manifest.json"),
            "feature_count": 3,
            "row_count": 4,
            "group_count": 1,
            "npy_freed_bytes": 128,
            "storage_dtype": "float16",
            "dtype_summary": {"counts": {"float16": 1}},
            "validation": {
                "has_nan": False,
                "has_inf": False,
                "coverage": 1.0,
                "inf_count": 0,
                "inf_ratio": 0.0,
                "groups_with_inf": 0,
                "warnings": [],
            },
            "l65_mode": "ic_first_pre",
        },
    )
    storage.persist_registry_to_parquet.side_effect = AssertionError("legacy L7 persist must not run")

    preprocessing = PreprocessingConfig(
        enabled=True,
        mode="replace",
        ic_first_pipeline=True,
        winsorization={"enabled": True},
        fractional_differencing={"enabled": True},
        adf_differencing={"enabled": True},
        rank_transform={"enabled": True},
        adaptive_zscore={"enabled": True},
        gaussian_normalize={"enabled": True},
    )

    class _Config(SimpleNamespace):
        def model_dump(self, by_alias: bool = False):
            return {
                "preprocessing": self.preprocessing.model_dump(),
                "timeframes": {"training": ["1h"], "primary": "1h"},
                "labels": {},
            }

    config = _Config(
        preprocessing=preprocessing,
        labels=SimpleNamespace(model_dump=lambda: {}),
        timeframes=SimpleNamespace(training=["1h"], primary="1h"),
    )

    factory = FeatureFactory.__new__(FeatureFactory)
    factory._cgsa_registry = registry
    factory._storage = storage
    factory._registry = Mock()
    factory._current_symbol = "SYNTHETIC"
    factory._current_timeframe = "1h"
    factory._current_config_hash = "cfg_raw"
    factory._current_raw_data = None
    factory._reference_data_cache = {}
    factory._progress_callback = None

    raw_data = pd.DataFrame({"close": np.array([10.0, 11.0, 12.0, 13.0], dtype=np.float32)})

    result = factory._layer7_raw_from_cgsa_pipeline(
        symbol="SYNTHETIC",
        timeframe="1h",
        raw_data=raw_data,
        config=config,
        elapsed=1.25,
        config_hash="cfg_raw",
    )

    storage.write_raw_from_registry_stream.assert_called_once()
    storage.persist_registry_to_parquet.assert_not_called()
    # hdf5_path now stores the manifest JSON path (not the raw directory) so
    # that service-layer routing detects the .json suffix and loads CGSA format.
    assert result.hdf5_path == str(raw_path.parent / "feature_manifest.json")
    assert result.metadata["artifact_kind"] == "raw"
    assert result.metadata["schema_version"] == "raw_v1"
    assert result.metadata["l65_mode"] == "ic_first_pre"
    assert result.metadata["npy_freed_bytes"] == 128


# ---------------------------------------------------------------------------
# Phase B Phase 1 Step 19: sharded source raw-sink integration tests.
# ---------------------------------------------------------------------------


def _build_sharded_registry(
    tmp_path: Path,
    *,
    group_id: str,
    n_rows: int,
    n_cols: int,
    seed: int = 0,
) -> tuple[ColumnGroupRegistry, np.ndarray, list[Path]]:
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    rng = np.random.default_rng(seed)
    data = rng.standard_normal((n_rows, n_cols)).astype(np.float32)
    registry.save_data(_build_group(group_id, (n_rows, n_cols)), data)
    persisted = registry.get(group_id)
    shard_paths = [s.disk_path for s in persisted.shards]
    return registry, data, shard_paths


def test_raw_streaming_sharded_source_writes_per_shard_part_and_frees(
    tmp_path: Path, monkeypatch
) -> None:
    """Sharded source should write one parquet per shard and immediately free shards."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")  # clamps up to floor 32MiB
    registry, _, shard_paths = _build_sharded_registry(
        tmp_path, group_id="big_group", n_rows=8192, n_cols=4096, seed=11
    )
    assert len(shard_paths) >= 2, "expected sharded layout for this test"

    storage = FeatureStorage(str(tmp_path / "features"))
    preprocessor = FeaturePreprocessor(_preprocessor_config())

    raw_dir, summary = storage.write_raw_from_registry_stream(
        symbol="SYM",
        tf="1h",
        config_hash="cfg_shard",
        registry=registry,
        preprocessor=preprocessor,
        cleanup_intermediate=True,
        l65_mode="legacy",
    )

    # All shard files must be gone by the time write returns.
    for path in shard_paths:
        assert not path.exists(), f"shard {path} should have been freed"
    # The registry should keep the group entry but with empty shards / no disk_path
    # (so parquet path binding still works post-write).
    persisted = registry.get("big_group")
    assert persisted.shards == ()
    assert persisted.disk_path is None

    # We expect one parquet part per shard (for shard-streamed groups).
    parquet_files = sorted((raw_dir).glob("big_group*.parquet"))
    assert len(parquet_files) == len(shard_paths)
    # Total feature_count must equal original n_cols.
    assert summary["feature_count"] == 4096
    # npy_freed_bytes must be > 0 to confirm shard cleanup was accounted for.
    assert summary["npy_freed_bytes"] > 0


def test_raw_streaming_sharded_per_cell_equivalence_with_legacy_concat(
    tmp_path: Path, monkeypatch
) -> None:
    """Per-shard transform output must equal full-concat transform output (column-independent kernels)."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")

    # Sharded run.
    sharded_registry, raw_data, _ = _build_sharded_registry(
        tmp_path / "sharded", group_id="g", n_rows=4096, n_cols=4096, seed=42
    )
    assert len(sharded_registry.get("g").shards) >= 2

    sharded_storage = FeatureStorage(str(tmp_path / "sharded_out"))
    sharded_storage.write_raw_from_registry_stream(
        symbol="S",
        tf="1h",
        config_hash="cfg",
        registry=sharded_registry,
        preprocessor=FeaturePreprocessor(_preprocessor_config()),
        cleanup_intermediate=False,
        l65_mode="legacy",
    )

    # Single-shard run by raising target_shard_bytes large enough to fit whole group.
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "512MiB")
    single_registry = ColumnGroupRegistry(tmp_path / "single_work", memory_buffer_groups=0)
    single_registry.save_data(_build_group("g", raw_data.shape), raw_data)
    assert single_registry.get("g").shards == ()  # truly single

    single_storage = FeatureStorage(str(tmp_path / "single_out"))
    single_storage.write_raw_from_registry_stream(
        symbol="S",
        tf="1h",
        config_hash="cfg",
        registry=single_registry,
        preprocessor=FeaturePreprocessor(_preprocessor_config()),
        cleanup_intermediate=False,
        l65_mode="legacy",
    )

    # Read the sharded outputs in shard order and concatenate; compare to single.
    sharded_dir = tmp_path / "sharded_out" / "S" / "1h" / "cfg" / "raw"
    single_dir = tmp_path / "single_out" / "S" / "1h" / "cfg" / "raw"

    sharded_files = sorted(sharded_dir.glob("g*.parquet"))
    single_files = sorted(single_dir.glob("g*.parquet"))
    assert len(sharded_files) >= 1 and len(single_files) >= 1

    sharded_dfs = [pq.read_table(p).to_pandas() for p in sharded_files]
    single_dfs = [pq.read_table(p).to_pandas() for p in single_files]

    sharded_full = pd.concat(sharded_dfs, axis=1)
    single_full = pd.concat(single_dfs, axis=1)

    # Order columns deterministically before compare.
    sharded_full = sharded_full[sorted(sharded_full.columns)]
    single_full = single_full[sorted(single_full.columns)]

    assert list(sharded_full.columns) == list(single_full.columns)
    # parquet roundtrip can use float16 storage; allow that exact storage step.
    np.testing.assert_array_equal(
        sharded_full.values.astype(np.float32),
        single_full.values.astype(np.float32),
    )


def test_raw_streaming_passthrough_mode_c_sharded_per_cell_equivalence(
    tmp_path: Path, monkeypatch
) -> None:
    """Mode C (preprocessor=None) sharded passthrough must yield original values per-cell."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    registry, raw_data, shard_paths = _build_sharded_registry(
        tmp_path, group_id="passthrough_g", n_rows=4096, n_cols=4096, seed=7
    )
    assert len(shard_paths) >= 2

    storage = FeatureStorage(str(tmp_path / "features"))

    raw_dir, summary = storage.write_raw_from_registry_stream(
        symbol="S",
        tf="1h",
        config_hash="cfg_modec",
        registry=registry,
        preprocessor=None,  # Mode C
        cleanup_intermediate=True,
        l65_mode="disabled",
    )

    # All shards freed.
    for path in shard_paths:
        assert not path.exists()

    # Re-read parquet parts and confirm per-cell match (allowing float16 storage roundtrip).
    parquet_files = sorted(raw_dir.glob("passthrough_g*.parquet"))
    assert len(parquet_files) == len(shard_paths)
    dfs = [pq.read_table(p).to_pandas() for p in parquet_files]
    full = pd.concat(dfs, axis=1)
    full = full[[c for c in full.columns if c.startswith("passthrough_g_col_")]]
    full = full[sorted(full.columns, key=lambda c: int(c.rsplit("_", 1)[-1]))]

    # parquet codec may store as float16 — confirm allclose at float16 precision.
    np.testing.assert_allclose(
        full.values.astype(np.float32),
        raw_data,
        rtol=0,
        atol=1e-2,  # float16 ulp ≈ 1e-3 for values ~1
    )
    assert summary["feature_count"] == raw_data.shape[1]


def test_raw_streaming_sharded_largest_first_uses_total_shard_bytes(
    tmp_path: Path, monkeypatch
) -> None:
    """largest-first ordering must use total_shard_bytes for sharded groups."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    monkeypatch.setenv("FFACT_L65_RAW_SINK_LARGEST_FIRST", "1")

    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    # Small single-shard group.
    small_data = np.zeros((10, 4), dtype=np.float32)
    registry.save_data(_build_group("a_small_single", small_data.shape), small_data)
    # Big sharded group (must be > 32MiB to actually shard).
    big_data = np.zeros((8192, 4096), dtype=np.float32)
    registry.save_data(_build_group("z_big_sharded", big_data.shape), big_data)
    assert len(registry.get("z_big_sharded").shards) >= 2
    assert registry.get("a_small_single").shards == ()

    preprocessor = FeaturePreprocessor(_preprocessor_config())
    output_order: list[str] = []

    def sink(output_group_id, columns, data, source_group_id, source_disk_path, cleanup_source):
        # Track the FIRST output id per source so we know group dispatch order.
        if source_group_id not in [oid.split("_shard")[0] for oid in output_order]:
            output_order.append(output_group_id)

    completed = preprocessor.transform_registry_groups_to_sink(registry, sink, n_workers=1)
    assert completed == 2
    # Big sharded group (z_big_sharded) total bytes >> small single → must come first.
    assert output_order[0].startswith("z_big_sharded")
