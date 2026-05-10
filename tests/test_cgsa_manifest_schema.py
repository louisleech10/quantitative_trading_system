"""Phase B Phase 1: CGSA manifest schema v1 → v2 round-trip + back-compat."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

import numpy as np
import pytest

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry


def _make_group(group_id: str, n_rows: int, n_cols: int) -> ColumnGroup:
    return ColumnGroup(
        group_id=group_id,
        layer=LayerSource.L1,
        timeframe="12h",
        data_source="binance",
        indicator="indicator",
        columns=tuple(f"c{i}" for i in range(n_cols)),
        shape=(n_rows, n_cols),
        dtype="float32",
    )


def _data(n_rows: int, n_cols: int, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).standard_normal((n_rows, n_cols)).astype(np.float32)


def test_schema_v2_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """save → manifest v2 → resume: restored registry yields identical loads."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    big = _make_group("12h_L1_big", 8192, 4096)
    big_data = _data(8192, 4096, seed=1)
    registry.save_data(big, big_data)
    small = _make_group("12h_L1_small", 100, 3)
    small_data = _data(100, 3, seed=2)
    registry.save_data(small, small_data)

    manifest_path = tmp_path / "manifest.json"
    assert manifest_path.exists()
    with manifest_path.open() as f:
        payload = json.load(f)
    assert payload.get("schema_version") == 2

    resumed = ColumnGroupRegistry.resume_from_manifest(tmp_path)
    np.testing.assert_array_equal(resumed.load_data("12h_L1_big"), big_data)
    np.testing.assert_array_equal(resumed.load_data("12h_L1_small"), small_data)


def test_schema_v1_legacy_manifest_resumes_as_single_shard(tmp_path: Path) -> None:
    """A handcrafted v1 manifest (with `npy_path`) is treated as a single-shard group."""
    # Set up a real .npy file the legacy manifest can point at.
    n_rows, n_cols = 50, 4
    arr = _data(n_rows, n_cols, seed=3)
    npy_path = tmp_path / "12h_L1_legacy.npy"
    np.save(npy_path, arr)

    legacy_manifest = {
        # No schema_version → resume should fall back to v1 layout.
        "groups": [
            {
                "group_id": "12h_L1_legacy",
                "layer": "L1",
                "timeframe": "12h",
                "data_source": "binance",
                "indicator": "indicator",
                "columns": [f"c{i}" for i in range(n_cols)],
                "shape": [n_rows, n_cols],
                "dtype": "float32",
                "npy_path": str(npy_path),
            }
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(legacy_manifest))

    resumed = ColumnGroupRegistry.resume_from_manifest(tmp_path)
    loaded = resumed.load_data("12h_L1_legacy")
    np.testing.assert_array_equal(loaded, arr)

    group = resumed.get("12h_L1_legacy")
    # Legacy v1 → kept as legacy single-file group; shards remains empty.
    assert group.shards == ()
    assert group.disk_path is not None and group.disk_path.exists()


def test_missing_shard_skips_group_on_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If a shard file goes missing between runs, resume skips that group rather than partial-load."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    group = _make_group("12h_L2_partial", 8192, 4096)
    registry.save_data(group, _data(8192, 4096))

    persisted = registry.get("12h_L2_partial")
    assert len(persisted.shards) >= 2
    persisted.shards[0].disk_path.unlink()  # simulate corruption / disk loss

    resumed = ColumnGroupRegistry.resume_from_manifest(tmp_path)
    # Group must NOT be resumed (avoid silent partial data).
    assert "12h_L2_partial" not in [gid for gid, _ in resumed.iter_all()]
