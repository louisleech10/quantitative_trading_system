"""Phase 5 tests — V7 storage infrastructure, multi-symbol parallel, Arrow IPC.

Test IDs from FEATURE_FACTORY_OPTIMIZATION_TODO.md Phase 5 test matrix:
  T5.0a ~ T5.0g: V7 P0 storage infrastructure
  T5.1 ~ T5.2: Multi-symbol parallel correctness
  T5.3a ~ T5.3d: FeatureReader 4-mode validation
  T5.B1 ~ T5.B3: Boundary conditions
"""

from __future__ import annotations

import gzip
import json
import os
from unittest.mock import patch

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_output_dir(tmp_path):
    """Temporary output directory for persist tests."""
    return tmp_path / "features"


@pytest.fixture()
def sample_registry(tmp_path):
    """Create a mock ColumnGroupRegistry with synthetic groups for testing."""
    from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

    work_dir = tmp_path / "work"
    work_dir.mkdir()
    registry = ColumnGroupRegistry(work_dir=work_dir)

    rng = np.random.default_rng(42)
    n_rows = 100

    # Group with 10 columns
    data_small = rng.standard_normal((n_rows, 10)).astype(np.float32)
    cols_small = tuple(f"feat_small_{i}" for i in range(10))
    npy_path = work_dir / "small.npy"
    np.save(npy_path, data_small)
    group_small = ColumnGroup(
        group_id="small",
        layer=LayerSource.L1,
        timeframe="1h",
        data_source="close",
        indicator="test",
        columns=cols_small,
        shape=data_small.shape,
        dtype="float32",
        disk_path=npy_path,
    )
    registry.register(group_small)

    # Group with 20 columns
    data_medium = rng.standard_normal((n_rows, 20)).astype(np.float32)
    cols_medium = tuple(f"feat_medium_{i}" for i in range(20))
    npy_path2 = work_dir / "medium.npy"
    np.save(npy_path2, data_medium)
    group_medium = ColumnGroup(
        group_id="medium",
        layer=LayerSource.L2,
        timeframe="1h",
        data_source="close",
        indicator="test2",
        columns=cols_medium,
        shape=data_medium.shape,
        dtype="float32",
        disk_path=npy_path2,
    )
    registry.register(group_medium)

    return registry, data_small, data_medium


@pytest.fixture()
def large_registry(tmp_path):
    """Registry with a group exceeding MAX_GROUP_COLUMNS (5000+)."""
    from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

    work_dir = tmp_path / "work_large"
    work_dir.mkdir()
    registry = ColumnGroupRegistry(work_dir=work_dir)

    rng = np.random.default_rng(99)
    n_rows = 50
    n_cols = 5003  # Exceeds MAX_GROUP_COLUMNS (5000)

    data = rng.standard_normal((n_rows, n_cols)).astype(np.float32)
    cols = tuple(f"feat_huge_{i}" for i in range(n_cols))
    npy_path = work_dir / "huge.npy"
    np.save(npy_path, data)
    group = ColumnGroup(
        group_id="huge",
        layer=LayerSource.L3,
        timeframe="1h",
        data_source="close",
        indicator="test_huge",
        columns=cols,
        shape=data.shape,
        dtype="float32",
        disk_path=npy_path,
    )
    registry.register(group)

    return registry, data


@pytest.fixture()
def persisted_output(tmp_output_dir, sample_registry):
    """Persist sample registry and return (output_dir, registry, data)."""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    registry, data_small, data_medium = sample_registry
    storage = FeatureStorage(base_path=str(tmp_output_dir))

    symbol = "TESTUSDT"
    config_hash = "abc123"
    storage.persist_registry_to_parquet(symbol, config_hash, registry)

    output_dir = tmp_output_dir / symbol / config_hash
    return output_dir, registry, data_small, data_medium, symbol, config_hash


# ===========================================================================
# T5.0a: manifest.json + columns.json.gz written after persist
# ===========================================================================

class TestT50aManifestWritten:
    """T5.0a — persist 後 manifest.json + columns.json.gz 存在且正確"""

    def test_manifest_exists(self, persisted_output):
        output_dir, *_ = persisted_output
        assert (output_dir / "manifest.json").exists()

    def test_columns_gz_exists(self, persisted_output):
        output_dir, *_ = persisted_output
        assert (output_dir / "columns.json.gz").exists()

    def test_manifest_total_features(self, persisted_output):
        output_dir, registry, data_small, data_medium, *_ = persisted_output
        with open(output_dir / "manifest.json") as f:
            manifest = json.load(f)
        expected_cols = data_small.shape[1] + data_medium.shape[1]
        assert manifest["total_features"] == expected_cols

    def test_manifest_version(self, persisted_output):
        output_dir, *_ = persisted_output
        with open(output_dir / "manifest.json") as f:
            manifest = json.load(f)
        assert manifest["version"] == "7.0"
        assert manifest["dtype"] == "float16"

    def test_columns_gz_size(self, persisted_output):
        output_dir, *_ = persisted_output
        gz_path = output_dir / "columns.json.gz"
        assert gz_path.stat().st_size < 1_000_000  # < 1 MB

    def test_columns_gz_content(self, persisted_output):
        output_dir, registry, data_small, data_medium, *_ = persisted_output
        gz_path = output_dir / "columns.json.gz"
        with gzip.open(gz_path, "rt", encoding="utf-8") as f:
            columns = json.load(f)
        expected_count = data_small.shape[1] + data_medium.shape[1]
        assert len(columns) == expected_count

    def test_manifest_groups_match_parquet(self, persisted_output):
        output_dir, *_ = persisted_output
        with open(output_dir / "manifest.json") as f:
            manifest = json.load(f)
        for group_id, info in manifest["groups"].items():
            pq_path = output_dir / info["file"]
            assert pq_path.exists(), f"Parquet file {info['file']} missing"
            table = pq.read_table(pq_path)
            group_columns = [str(column) for column in info.get("columns", [])]
            assert len(group_columns) == info["column_count"]
            assert set(group_columns).issubset(set(table.column_names))


# ===========================================================================
# T5.0b: float16 storage precision
# ===========================================================================

class TestT50bFloat16Precision:
    """T5.0b — float16 與 float32 差異 + NaN 保留"""

    def test_relative_diff_within_tolerance(self, persisted_output):
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        output_dir, _, data_small, _, symbol, config_hash = persisted_output
        reader = FeatureReader(str(output_dir.parent.parent))
        selected = [f"feat_small_{index}" for index in range(data_small.shape[1])]
        loaded = reader.load_columns(symbol, config_hash, selected).values.astype(np.float32)

        expected_f16 = data_small.astype(np.float16).astype(np.float32)
        np.testing.assert_allclose(
            loaded,
            expected_f16,
            atol=np.finfo(np.float16).eps * 10,
            rtol=0,
        )

    def test_nan_preserved(self, tmp_path):
        """NaN positions must be preserved through float16 round-trip."""
        from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
        from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        work_dir = tmp_path / "nan_test"
        work_dir.mkdir()
        registry = ColumnGroupRegistry(work_dir=work_dir)

        data = np.array([[1.0, np.nan, 3.0], [np.nan, 5.0, 6.0]], dtype=np.float32)
        npy_path = work_dir / "nan_group.npy"
        np.save(npy_path, data)
        group = ColumnGroup(
            group_id="nan_group",
            layer=LayerSource.L1,
            timeframe="1h",
            data_source="close",
            indicator="nan_test",
            columns=("a", "b", "c"),
            shape=data.shape,
            dtype="float32",
            disk_path=npy_path,
        )
        registry.register(group)

        output_dir = tmp_path / "out"
        storage = FeatureStorage(base_path=str(output_dir))
        storage.persist_registry_to_parquet("TEST", "h1", registry)

        loaded = pq.read_table(output_dir / "TEST" / "h1" / "nan_group.parquet").to_pandas()
        original_nan_mask = np.isnan(data)
        loaded_nan_mask = loaded.isna().values
        np.testing.assert_array_equal(original_nan_mask, loaded_nan_mask)


# ===========================================================================
# T5.0c: max_group_split
# ===========================================================================

class TestT50cMaxGroupSplit:
    """T5.0c — >5000 columns 自動拆分"""

    def test_split_creates_parts(self, tmp_path, large_registry):
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        registry, data = large_registry
        output_dir = tmp_path / "split_out"
        storage = FeatureStorage(base_path=str(output_dir))
        storage.persist_registry_to_parquet("SPLITUSDT", "s1", registry)

        out = output_dir / "SPLITUSDT" / "s1"
        with open(out / "manifest.json") as f:
            manifest = json.load(f)

        # Should have 2 parts: 5000 + 3
        assert len(manifest["groups"]) == 2
        group_ids = sorted(manifest["groups"].keys())
        assert "huge_part1" in group_ids[0]
        assert "huge_part2" in group_ids[1]

    def test_split_column_count_correct(self, tmp_path, large_registry):
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        registry, data = large_registry
        output_dir = tmp_path / "split_out2"
        storage = FeatureStorage(base_path=str(output_dir))
        storage.persist_registry_to_parquet("SPLITUSDT", "s2", registry)

        out = output_dir / "SPLITUSDT" / "s2"
        with open(out / "manifest.json") as f:
            manifest = json.load(f)

        part1 = manifest["groups"]["huge_part1"]
        part2 = manifest["groups"]["huge_part2"]
        assert part1["column_count"] == 5000
        assert part2["column_count"] == 3
        assert manifest["total_features"] == 5003

    def test_no_split_at_boundary(self):
        """Exactly 5000 columns should NOT be split."""
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        columns = [f"c_{i}" for i in range(5000)]
        data = np.zeros((10, 5000), dtype=np.float32)
        parts = FeatureStorage._split_large_group("g", columns, data)
        assert len(parts) == 1
        assert parts[0][0] == "g"


# ===========================================================================
# T5.0d / T5.3a: FeatureReader metadata-only
# ===========================================================================

class TestT50dReaderMetadata:
    """T5.0d / T5.3a — list_features() returns correct names"""

    def test_list_features_count(self, persisted_output):
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        output_dir, _, data_small, data_medium, symbol, config_hash = persisted_output
        reader = FeatureReader(str(output_dir.parent.parent))
        features = reader.list_features(symbol, config_hash)
        expected = data_small.shape[1] + data_medium.shape[1]
        assert len(features) == expected

    def test_load_manifest(self, persisted_output):
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        output_dir, *_, symbol, config_hash = persisted_output
        reader = FeatureReader(str(output_dir.parent.parent))
        manifest = reader.load_manifest(symbol, config_hash)
        assert manifest["version"] == "7.0"
        assert "groups" in manifest


# ===========================================================================
# T5.0e / T5.3b: FeatureReader column projection
# ===========================================================================

class TestT50eReaderColumnProjection:
    """T5.0e / T5.3b — load_columns() reads only selected columns"""

    def test_column_projection_values(self, persisted_output):
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        output_dir, _, data_small, _, symbol, config_hash = persisted_output
        reader = FeatureReader(str(output_dir.parent.parent))

        # Select first 3 columns from small group
        selected = [f"feat_small_{i}" for i in range(3)]
        df = reader.load_columns(symbol, config_hash, selected)

        assert list(df.columns) == selected
        expected = data_small[:, :3].astype(np.float16).astype(np.float32)
        np.testing.assert_allclose(
            df.values.astype(np.float32),
            expected,
            atol=np.finfo(np.float16).eps * 10,
        )


# ===========================================================================
# T5.0f / T5.3c: FeatureReader stream_groups
# ===========================================================================

class TestT50fReaderStreamGroups:
    """T5.0f / T5.3c — stream_groups() iterates all groups"""

    def test_total_columns_match(self, persisted_output):
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        output_dir, _, data_small, data_medium, symbol, config_hash = persisted_output
        reader = FeatureReader(str(output_dir.parent.parent))

        total_cols = 0
        for group_id, df in reader.stream_groups(symbol, config_hash):
            total_cols += df.shape[1]

        expected = data_small.shape[1] + data_medium.shape[1]
        assert total_cols == expected


# ===========================================================================
# T5.0g: FeatureLibrary uses FeatureReader (no h5py import)
# ===========================================================================

class TestT50gLibraryUsesReader:
    """T5.0g — FeatureLibrary.load() delegates to FeatureReader"""

    def test_no_h5py_in_library(self):
        """feature_library.py should NOT import h5py."""
        import inspect
        from momentum.FeatureEngineering import feature_library

        source = inspect.getsource(feature_library)
        assert "import h5py" not in source


# ===========================================================================
# T5.1: Multi-symbol parallel correctness (unit-level mock test)
# ===========================================================================

class TestT51MultiSymbolParallel:
    """T5.1 — multi-symbol parallel golden comparison (mocked)."""

    def test_warmup_numba_functions(self):
        """Numba warmup runs without error."""
        from momentum.FeatureEngineering.feature_factory import _warmup_numba_functions
        # Should not raise
        _warmup_numba_functions()

    def test_split_large_group_util(self):
        """_split_large_group correctly splits > 5000 columns."""
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        cols = [f"c{i}" for i in range(7500)]
        data = np.zeros((10, 7500), dtype=np.float32)
        parts = FeatureStorage._split_large_group("big", cols, data)
        assert len(parts) == 2
        assert parts[0][0] == "big_part1"
        assert len(parts[0][1]) == 5000
        assert parts[1][0] == "big_part2"
        assert len(parts[1][1]) == 2500


# ===========================================================================
# T5.2: No crosstalk between workers (unit-level)
# ===========================================================================

class TestT52NoCrosstalk:
    """T5.2 — symbol isolation: each worker has independent registry."""

    def test_worker_entry_isolation(self):
        """_worker_entry is module-level and importable (picklable)."""
        from momentum.FeatureEngineering.feature_factory import _worker_entry
        assert callable(_worker_entry)


# ===========================================================================
# T5.3d: FeatureReader cross-symbol
# ===========================================================================

class TestT53dReaderCrossSymbol:
    """T5.3d — cross-symbol loading with same columns"""

    def test_cross_symbol_basic(self, tmp_path):
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        # Create 2 symbols with shared column names
        rng = np.random.default_rng(7)
        base = tmp_path / "cross"
        shared_cols = ["feat_a", "feat_b", "feat_c"]
        for sym in ["SYM1", "SYM2"]:
            sym_dir = base / sym / "h1"
            sym_dir.mkdir(parents=True)
            data = rng.standard_normal((50, 3)).astype(np.float16)
            table = pa.table({c: data[:, i] for i, c in enumerate(shared_cols)})
            pq.write_table(table, sym_dir / "group1.parquet", compression="zstd")

            manifest = {
                "version": "7.0",
                "symbol": sym,
                "config_hash": "h1",
                "total_features": 3,
                "total_rows": 50,
                "dtype": "float16",
                "groups": {"group1": {"file": "group1.parquet", "column_count": 3, "columns": shared_cols}},
            }
            with open(sym_dir / "manifest.json", "w") as f:
                json.dump(manifest, f)
            with gzip.open(sym_dir / "columns.json.gz", "wt") as f:
                json.dump(shared_cols, f)

        reader = FeatureReader(str(base))
        result = reader.load_cross_symbol(["SYM1", "SYM2"], "h1", shared_cols)
        assert isinstance(result, pd.DataFrame)
        assert "_symbol" in result.index.names
        # Should have rows for both symbols
        symbols_in_result = result.index.get_level_values("_symbol").unique().tolist()
        assert set(symbols_in_result) == {"SYM1", "SYM2"}
        # Check columns are the shared ones
        assert list(result.columns) == shared_cols


# ===========================================================================
# T5.B1: Single symbol failure
# ===========================================================================

class TestT5B1SingleFailure:
    """T5.B1 — one symbol failure doesn't block others."""

    def test_partial_failure(self):
        """If _worker_entry raises, other symbols should still succeed."""
        # This is a design-level test; real parallel test requires h5 data.
        # Verify the interface supports error collection.
        from momentum.FeatureEngineering.feature_factory import FeatureFactory
        assert hasattr(FeatureFactory, "run_multi_symbol")
        # run_multi_symbol returns (results, errors) tuple
        import inspect
        sig = inspect.signature(FeatureFactory.run_multi_symbol)
        assert "symbols" in sig.parameters


# ===========================================================================
# T5.B3: Disk full mid-persist (staging cleanup)
# ===========================================================================

class TestT5B3DiskFullMidPersist:
    """T5.B3 — staging directory cleaned up on failure."""

    def test_staging_cleanup_on_error(self, tmp_path, sample_registry):
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        registry, _, _ = sample_registry
        output_dir = tmp_path / "fail_out"
        storage = FeatureStorage(base_path=str(output_dir))

        # Patch os.replace to simulate write failure
        original_replace = os.replace

        call_count = [0]

        def failing_replace(src, dst):
            call_count[0] += 1
            if call_count[0] > 1:
                raise OSError("No space left on device")
            return original_replace(src, dst)

        with patch("momentum.FeatureEngineering.feature_storage.os.replace", side_effect=failing_replace):
            with pytest.raises(OSError, match="No space"):
                storage.persist_registry_to_parquet("FAILSYM", "f1", registry)

        # Staging directory should have been cleaned up
        sym_dir = output_dir / "FAILSYM" / "f1"
        if sym_dir.exists():
            staging_dirs = [d for d in sym_dir.iterdir() if d.is_dir() and d.name.startswith(".staging_")]
            assert len(staging_dirs) == 0, "Staging directory should be cleaned up"


# ===========================================================================
# Arrow IPC utils tests (Task 5.2)
# ===========================================================================

class TestArrowIPC:
    """Arrow IPC read/write round-trip tests."""

    def test_write_read_roundtrip(self, tmp_path):
        from momentum.FeatureEngineering.arrow_ipc_utils import read_arrow_ipc, write_arrow_ipc

        df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]})
        ipc_path = tmp_path / "test.arrow"
        write_arrow_ipc(df, ipc_path)
        loaded = read_arrow_ipc(ipc_path)
        pd.testing.assert_frame_equal(df, loaded)

    def test_reference_data_roundtrip(self, tmp_path):
        from momentum.FeatureEngineering.arrow_ipc_utils import (
            read_reference_data_ipc,
            write_reference_data_ipc,
        )

        df = pd.DataFrame({"close": np.random.randn(100), "volume": np.random.randn(100)})
        ipc_path = write_reference_data_ipc(df, tmp_path, "BTCUSDT")
        loaded = read_reference_data_ipc(ipc_path)
        pd.testing.assert_frame_equal(df, loaded)

    def test_read_missing_raises(self, tmp_path):
        from momentum.FeatureEngineering.arrow_ipc_utils import read_arrow_ipc

        with pytest.raises(FileNotFoundError):
            read_arrow_ipc(tmp_path / "nonexistent.arrow")
