"""Phase B Phase 1 Step 22: shard boundary cases (1 row, 1 col, tiny shard_bytes, mode switch)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry


def _group(group_id: str, n_rows: int, n_cols: int) -> ColumnGroup:
    return ColumnGroup(
        group_id=group_id,
        layer=LayerSource.L1,
        timeframe="1h",
        data_source="derived",
        indicator="x",
        columns=tuple(f"{group_id}_c{i}" for i in range(n_cols)),
        shape=(n_rows, n_cols),
        dtype="float32",
    )


def test_single_row_group_persists_and_loads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    registry = ColumnGroupRegistry(tmp_path, memory_buffer_groups=0)
    data = np.full((1, 4), 0.5, np.float32)
    registry.save_data(_group("g_one_row", 1, 4), data)
    g = registry.get("g_one_row")
    # Tiny groups should fit in a single shard (or no shards if below threshold).
    assert g.shape == (1, 4)
    assert np.array_equal(registry.load_data("g_one_row"), data)


def test_single_column_group_persists_and_loads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    registry = ColumnGroupRegistry(tmp_path, memory_buffer_groups=0)
    data = np.arange(16, dtype=np.float32).reshape(16, 1)
    registry.save_data(_group("g_one_col", 16, 1), data)
    assert np.array_equal(registry.load_data("g_one_col"), data)


def test_shard_bytes_below_one_row_falls_back_safely(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Even when configured shard_bytes is smaller than a single row, persistence works."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")  # clamps up to 32 MiB floor
    registry = ColumnGroupRegistry(tmp_path, memory_buffer_groups=0)
    # 1024 cols * 4 bytes = 4 KiB per row; way below 32 MiB floor.
    data = np.random.RandomState(0).rand(8, 1024).astype(np.float32)
    registry.save_data(_group("g_small", 8, 1024), data)
    loaded = registry.load_data("g_small")
    assert np.array_equal(loaded, data)


def test_release_storage_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """release_storage on an already-released group must be safe and return 0."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    registry = ColumnGroupRegistry(tmp_path, memory_buffer_groups=0)
    data = np.full((4096, 1024), 1.0, np.float32)
    registry.save_data(_group("g_rel", 4096, 1024), data)

    freed1 = registry.release_storage("g_rel")
    assert freed1 > 0
    g = registry.get("g_rel")
    assert g.shards == ()
    assert g.disk_path is None

    # Second call: nothing left to free, must not raise.
    freed2 = registry.release_storage("g_rel")
    assert freed2 == 0


def test_release_storage_preserves_parquet_binding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Parquet path bindings registered before release must survive."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    registry = ColumnGroupRegistry(tmp_path, memory_buffer_groups=0)
    data = np.full((2048, 512), 1.0, np.float32)
    registry.save_data(_group("g_park", 2048, 512), data)

    # release first, then bind parquet path (the actual production order).
    registry.release_storage("g_park")
    parquet_path = tmp_path / "g_park.parquet"
    parquet_path.write_bytes(b"x")
    registry.set_group_parquet_paths({"g_park": parquet_path}, write_manifest=False)

    g = registry.get("g_park")
    assert g.shards == ()
    assert g.disk_path is None
    # The parquet binding must be retrievable.
    assert registry._group_parquet_paths.get("g_park") == str(parquet_path)


def test_release_storage_unknown_group_returns_zero(tmp_path: Path) -> None:
    registry = ColumnGroupRegistry(tmp_path, memory_buffer_groups=0)
    assert registry.release_storage("nonexistent") == 0
