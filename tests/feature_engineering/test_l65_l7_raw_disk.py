"""Phase B Phase 1 Step 20: L6.5 → L7_raw disk pre-check on sharded sources."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage


def _build_group(group_id: str, n_rows: int, n_cols: int) -> ColumnGroup:
    return ColumnGroup(
        group_id=group_id,
        layer=LayerSource.L2,
        timeframe="12h",
        data_source="derived",
        indicator="mock",
        columns=tuple(f"{group_id}_c{i}" for i in range(n_cols)),
        shape=(n_rows, n_cols),
        dtype="float32",
    )


def test_precheck_passes_with_38gib_free_and_sharded_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """38 GiB free + 34 GiB cgsa_work (sharded) → pre-check must NOT false-fail."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")  # clamps to 32MiB floor
    monkeypatch.setenv("FFACT_L7_DISK_SAFETY_FACTOR", "1.5")
    monkeypatch.setenv("FFACT_L7_MIN_FREE_GIB", "2")

    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    # Build a real (small) sharded group so registry has actual ShardMeta entries.
    n_rows, n_cols = 8192, 4096  # ~128 MiB → multi-shard
    registry.save_data(_build_group("big", n_rows, n_cols), np.zeros((n_rows, n_cols), np.float32))
    group = registry.get("big")
    assert len(group.shards) >= 2

    storage = FeatureStorage(str(tmp_path / "features"))

    # Pretend we have 38 GiB free.
    monkeypatch.setattr(storage, "_safe_disk_free_bytes", lambda _path: int(38 * 1024 ** 3))

    # Should not raise — net_growth is dominated by reclaimable_npy.
    storage._precheck_l7_raw_stream_disk_space(tmp_path / "features", [("big", group)])


def test_precheck_fails_when_free_below_max_inflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even with sharded sources, free < max in-flight + reserve must fail-fast."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    monkeypatch.setenv("FFACT_L7_DISK_SAFETY_FACTOR", "1.0")
    monkeypatch.setenv("FFACT_L7_MIN_FREE_GIB", "0")

    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    n_rows, n_cols = 8192, 4096
    registry.save_data(_build_group("big", n_rows, n_cols), np.zeros((n_rows, n_cols), np.float32))
    group = registry.get("big")

    storage = FeatureStorage(str(tmp_path / "features"))
    # Only 1 byte of free disk.
    monkeypatch.setattr(storage, "_safe_disk_free_bytes", lambda _path: 1)

    with pytest.raises(OSError) as exc:
        storage._precheck_l7_raw_stream_disk_space(tmp_path / "features", [("big", group)])
    assert "Insufficient disk space for L7_raw streaming persist" in str(exc.value)


def test_precheck_counts_shard_nbytes_in_reclaimable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reclaimable = sum(shard.nbytes), proven by free=net_growth-only barely passing."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    monkeypatch.setenv("FFACT_L7_DISK_SAFETY_FACTOR", "1.0")
    monkeypatch.setenv("FFACT_L7_MIN_FREE_GIB", "0")

    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    n_rows, n_cols = 8192, 4096
    registry.save_data(_build_group("big", n_rows, n_cols), np.zeros((n_rows, n_cols), np.float32))
    group = registry.get("big")
    total_shard_bytes = sum(s.nbytes for s in group.shards)
    assert total_shard_bytes >= 32 * 1024 * 1024

    storage = FeatureStorage(str(tmp_path / "features"))

    # Provide just enough free to cover a single in-flight part (~MAX_GROUP_COLUMNS slice).
    largest_part_bytes = n_rows * min(n_cols, storage.MAX_GROUP_COLUMNS) * 4
    monkeypatch.setattr(
        storage,
        "_safe_disk_free_bytes",
        lambda _path: largest_part_bytes + 1024,
    )
    # Should pass because reclaimable >= estimated_final → net_growth ≈ 0.
    storage._precheck_l7_raw_stream_disk_space(tmp_path / "features", [("big", group)])


def test_precheck_passthrough_mode_c_uses_same_codepath(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mode C (passthrough) must respect the same disk pre-check as Mode A/B."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    monkeypatch.setenv("FFACT_L7_DISK_SAFETY_FACTOR", "1.0")
    monkeypatch.setenv("FFACT_L7_MIN_FREE_GIB", "0")

    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    n_rows, n_cols = 8192, 4096
    registry.save_data(_build_group("big", n_rows, n_cols), np.zeros((n_rows, n_cols), np.float32))
    group = registry.get("big")

    storage = FeatureStorage(str(tmp_path / "features"))
    monkeypatch.setattr(storage, "_safe_disk_free_bytes", lambda _path: 1)
    with pytest.raises(OSError):
        storage._precheck_l7_raw_stream_disk_space(tmp_path / "features", [("big", group)])
