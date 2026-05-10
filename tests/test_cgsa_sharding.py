"""Phase B Phase 1: CGSA shard storage / load / cleanup behavior."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pytest

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry


def _make_group(
    group_id: str,
    columns: Tuple[str, ...],
    shape: Tuple[int, int],
) -> ColumnGroup:
    return ColumnGroup(
        group_id=group_id,
        layer=LayerSource.L2,
        timeframe="12h",
        data_source="derived",
        indicator="test",
        columns=columns,
        shape=shape,
        dtype="float32",
    )


def _make_data(shape: Tuple[int, int], seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal(shape).astype(np.float32)


def test_save_data_single_shard_fast_path_for_small_group(tmp_path: Path) -> None:
    """Small group (< target shard bytes) stays as single legacy file (no shards)."""
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    columns = tuple(f"c{i}" for i in range(4))
    shape = (100, 4)
    group = _make_group("12h_L1_small", columns, shape)
    data = _make_data(shape)

    registry.save_data(group, data)

    persisted = registry.get("12h_L1_small")
    # Small group: shards tuple empty, single disk_path is set.
    assert persisted.shards == ()
    assert persisted.disk_path is not None
    assert persisted.disk_path.exists()


def test_save_data_creates_multiple_shards_when_above_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Large group splits into >1 shards under the configured target bytes."""
    # 1 MiB target so a 4 MiB group → 4 shards.
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    # Floor in hardware_utils is 32 MiB → env clamps up to 32 MiB.
    # Group sized 8192 x 4096 ≈ 128 MiB → must split into >=4 shards.
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    n_rows = 8192
    n_cols = 4096  # 8192 * 4096 * 4 bytes = 128 MiB
    columns = tuple(f"c{i}" for i in range(n_cols))
    shape = (n_rows, n_cols)
    group = _make_group("12h_L2_big", columns, shape)
    data = _make_data(shape, seed=1)

    registry.save_data(group, data)

    persisted = registry.get("12h_L2_big")
    assert len(persisted.shards) >= 2, f"expected >=2 shards, got {len(persisted.shards)}"
    # Coverage: shards together span all columns exactly once.
    covered = sum(s.n_cols for s in persisted.shards)
    assert covered == n_cols
    # All shard files exist.
    for shard in persisted.shards:
        assert shard.disk_path.exists()


def test_load_data_concat_matches_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """load_data returns a concatenated array bit-equivalent to the input."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    n_rows, n_cols = 8192, 4096  # ~128 MiB → multi-shard
    columns = tuple(f"c{i}" for i in range(n_cols))
    group = _make_group("12h_L2_concat", columns, (n_rows, n_cols))
    data = _make_data((n_rows, n_cols), seed=7)

    registry.save_data(group, data)
    loaded = registry.load_data("12h_L2_concat")

    assert loaded.shape == data.shape
    assert loaded.dtype == np.float32
    np.testing.assert_array_equal(loaded, data)


def test_iter_shards_in_order_with_correct_slices(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """iter_shards yields shards in shard_idx order with matching col slices."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    n_rows, n_cols = 8192, 4096
    columns = tuple(f"c{i}" for i in range(n_cols))
    group = _make_group("12h_L2_iter", columns, (n_rows, n_cols))
    data = _make_data((n_rows, n_cols), seed=3)
    registry.save_data(group, data)

    last_idx = -1
    seen_cols = 0
    for meta, arr, cols in registry.iter_shards("12h_L2_iter"):
        assert meta.shard_idx > last_idx
        last_idx = meta.shard_idx
        assert arr.shape == (n_rows, meta.n_cols)
        assert len(cols) == meta.n_cols
        np.testing.assert_array_equal(
            np.asarray(arr), data[:, meta.col_start : meta.col_end]
        )
        seen_cols += meta.n_cols
    assert seen_cols == n_cols


def test_unlink_shard_removes_only_target_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    n_rows, n_cols = 8192, 4096
    group = _make_group(
        "12h_L2_unlink",
        tuple(f"c{i}" for i in range(n_cols)),
        (n_rows, n_cols),
    )
    registry.save_data(group, _make_data((n_rows, n_cols)))
    persisted = registry.get("12h_L2_unlink")
    assert len(persisted.shards) >= 2

    target_idx = persisted.shards[0].shard_idx
    target_path = persisted.shards[0].disk_path
    other_paths = [s.disk_path for s in persisted.shards[1:]]

    registry.unlink_shard("12h_L2_unlink", target_idx)
    assert not target_path.exists()
    for other in other_paths:
        assert other.exists()


def test_unregister_group_clears_all_shards_and_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    n_rows, n_cols = 8192, 4096
    group = _make_group(
        "12h_L2_unreg",
        tuple(f"c{i}" for i in range(n_cols)),
        (n_rows, n_cols),
    )
    registry.save_data(group, _make_data((n_rows, n_cols)))
    persisted = registry.get("12h_L2_unreg")
    shard_paths = [s.disk_path for s in persisted.shards]

    registry.unregister_group("12h_L2_unreg")

    assert "12h_L2_unreg" not in [gid for gid, _ in registry.iter_all()]
    for path in shard_paths:
        assert not path.exists()


def test_overwrite_data_replaces_old_shards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """overwrite_data deletes old shards and writes fresh layout."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    n_rows, n_cols = 8192, 4096
    group = _make_group(
        "12h_L2_overwrite",
        tuple(f"c{i}" for i in range(n_cols)),
        (n_rows, n_cols),
    )
    registry.save_data(group, _make_data((n_rows, n_cols), seed=1))
    old_paths = [s.disk_path for s in registry.get("12h_L2_overwrite").shards]

    new_data = _make_data((n_rows, n_cols), seed=99)
    registry.overwrite_data("12h_L2_overwrite", new_data)
    loaded = registry.load_data("12h_L2_overwrite")
    np.testing.assert_array_equal(loaded, new_data)

    # Stale shard files (from prior shard layout) must be gone.
    new_paths = {s.disk_path for s in registry.get("12h_L2_overwrite").shards}
    for old in old_paths:
        if old not in new_paths:
            assert not old.exists()


def test_cleanup_removes_all_shard_and_legacy_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    big_group = _make_group(
        "12h_L2_big",
        tuple(f"c{i}" for i in range(4096)),
        (8192, 4096),
    )
    registry.save_data(big_group, _make_data((8192, 4096)))

    small_group = _make_group("12h_L1_small", ("a", "b"), (10, 2))
    registry.save_data(small_group, _make_data((10, 2)))

    all_paths = []
    for gid, group in list(registry.iter_all()):
        if group.disk_path is not None:
            all_paths.append(group.disk_path)
        for shard in group.shards:
            all_paths.append(shard.disk_path)

    registry.cleanup()

    for path in all_paths:
        assert not path.exists(), f"cleanup left behind {path}"


def test_temp_file_swept_on_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stale .tmp left from a crash mid-write is removed at resume."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    group = _make_group("12h_L1_tmp", ("a",), (10, 1))
    registry.save_data(group, _make_data((10, 1)))

    stale_tmp = tmp_path / "12h_L2_orphan.shard00.npy.tmp"
    stale_tmp.write_bytes(b"\x00" * 16)
    assert stale_tmp.exists()

    ColumnGroupRegistry.resume_from_manifest(tmp_path)
    assert not stale_tmp.exists()
