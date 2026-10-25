"""Phase B Phase 1 Step 21: multi-symbol / multi-TF shard isolation regression."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.run_paths import cgsa_work_dir


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



def test_shards_isolated_across_production_symbol_tf_workdirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """純增：上列兩支之 4096×2048、2048×1024 float32 皆不超過分片下限（FFACT_CGSA_SHARD_BYTES 1MiB 夾至 32MiB），走單檔
    路徑、shards 為空，分片路徑之迴圈空轉；各 symbol／tf 之工作目錄亦由測試自建。本案以生產端 cgsa_work_dir（由 symbol、
    tf、config_hash 導出目錄）建三個工作目錄（兩 symbol 同 tf、同 symbol 兩 tf），各存同 group_id 之 8192×2048 float32
    （64MiB ⇒ 2 分片；值＝各組常數×10000＋欄號，分片錯置可見）：三目錄互異；每組至少 2 分片且分片檔皆在自身目錄下；
    讀回值為各自之值。"""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1MiB")
    n_rows, n_cols = 8192, 2048
    cases = {("ETHUSDT", "1h"): 1.0, ("BTCUSDT", "1h"): 2.0, ("ETHUSDT", "12h"): 3.0}
    cols = np.arange(n_cols, dtype=np.float32)[None, :]
    dirs = {key: cgsa_work_dir(tmp_path, key[0], key[1], "cfgiso01", "a" * 64) for key in cases}
    assert len(set(dirs.values())) == len(cases)
    regs = {}
    for (sym, tf), value in cases.items():
        regs[(sym, tf)] = ColumnGroupRegistry(dirs[(sym, tf)], memory_buffer_groups=0)
        regs[(sym, tf)].save_data(_group("g1", LayerSource.L1, tf, n_rows, n_cols),
                                  np.full((n_rows, n_cols), value * 10000, np.float32) + cols)
    for key, reg in regs.items():
        shards = reg.get("g1").shards
        assert len(shards) >= 2 and all(dirs[key] in s.disk_path.parents for s in shards), key
    for key, reg in regs.items():
        assert np.array_equal(reg.load_data("g1"), np.full((n_rows, n_cols), cases[key] * 10000, np.float32) + cols), key
