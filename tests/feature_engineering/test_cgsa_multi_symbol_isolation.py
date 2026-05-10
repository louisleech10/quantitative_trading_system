"""Phase B Phase 1 Step 21: multi-symbol / multi-TF shard isolation regression."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry


def _group(group_id: str, layer: LayerSource, tf: str, n_rows: int, n_cols: int) -> ColumnGroup:
    return ColumnGroup(
        group_id=group_id,
        layer=layer,
        timeframe=tf,
        data_source="derived",
        indicator="x",
        columns=tuple(f"{group_id}_c{i}" for i in range(n_cols)),
        shape=(n_rows, n_cols),
        dtype="float32",
    )


def test_shards_isolated_across_symbols(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two symbols with the same group_id must not share or overwrite shard files."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")

    sym_a = ColumnGroupRegistry(tmp_path / "ETHUSDT_1h", memory_buffer_groups=0)
    sym_b = ColumnGroupRegistry(tmp_path / "BTCUSDT_1h", memory_buffer_groups=0)

    n_rows, n_cols = 4096, 2048
    data_a = np.full((n_rows, n_cols), 1.0, np.float32)
    data_b = np.full((n_rows, n_cols), 2.0, np.float32)

    sym_a.save_data(_group("g1", LayerSource.L1, "1h", n_rows, n_cols), data_a)
    sym_b.save_data(_group("g1", LayerSource.L1, "1h", n_rows, n_cols), data_b)

    g_a = sym_a.get("g1")
    g_b = sym_b.get("g1")

    # Shard paths must live under their own per-symbol workdir.
    for s in g_a.shards:
        assert (tmp_path / "ETHUSDT_1h") in s.disk_path.parents
        assert (tmp_path / "BTCUSDT_1h") not in s.disk_path.parents
    for s in g_b.shards:
        assert (tmp_path / "BTCUSDT_1h") in s.disk_path.parents
        assert (tmp_path / "ETHUSDT_1h") not in s.disk_path.parents

    # Loaded data must match the symbol-specific values, no cross-contamination.
    loaded_a = sym_a.load_data("g1")
    loaded_b = sym_b.load_data("g1")
    assert np.array_equal(loaded_a, data_a)
    assert np.array_equal(loaded_b, data_b)


def test_shards_isolated_across_timeframes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Same symbol but two timeframes use isolated workdirs."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")

    tf_1h = ColumnGroupRegistry(tmp_path / "ETHUSDT_1h", memory_buffer_groups=0)
    tf_12h = ColumnGroupRegistry(tmp_path / "ETHUSDT_12h", memory_buffer_groups=0)

    data_1h = np.full((2048, 1024), 0.1, np.float32)
    data_12h = np.full((2048, 1024), 0.9, np.float32)

    tf_1h.save_data(_group("L1_x", LayerSource.L1, "1h", 2048, 1024), data_1h)
    tf_12h.save_data(_group("L1_x", LayerSource.L1, "12h", 2048, 1024), data_12h)

    assert np.array_equal(tf_1h.load_data("L1_x"), data_1h)
    assert np.array_equal(tf_12h.load_data("L1_x"), data_12h)
