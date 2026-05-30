"""CGSA streaming write 路徑的 L7 dead-drop 整合測試。

對應 NAN_REDUCTION_STRATEGY.md §5.3 + plans/misty-booping-sketch.md（CGSA dead-drop）。

驗證 frame-path 不經過的 CGSA 模式下，dead feature drop 在 registry stream write
（`write_raw_from_registry_stream`）正確 per-column 剔除常數/樣本不足/全 NaN 欄，
且整組全 dead 時源頭仍被清理、disable 時 byte-identical no-op。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.utils.dead_feature_filter import find_dead_columns

ROWS = 500
MIN_VALID = 100


def _group(group_id: str, columns: list[str], data: np.ndarray) -> ColumnGroup:
    return ColumnGroup(
        group_id=group_id,
        layer=LayerSource.L2,
        timeframe="1h",
        data_source="derived",
        indicator="mock",
        columns=tuple(columns),
        shape=data.shape,
        dtype="float32",
    )


def _build_columns_and_data() -> tuple[list[str], np.ndarray]:
    """回傳 (column 名稱, 資料) — 含 good / constant / sparse / all-nan。"""
    rng = np.random.default_rng(123)
    good1 = rng.standard_normal(ROWS).astype(np.float32)
    good2 = rng.standard_normal(ROWS).astype(np.float32)
    constant = np.full(ROWS, 42.0, dtype=np.float32)            # dead: 常數
    sparse = np.full(ROWS, np.nan, dtype=np.float32)
    sparse[:50] = rng.standard_normal(50)                       # dead: 50 < 100 valid
    all_nan = np.full(ROWS, np.nan, dtype=np.float32)           # dead: 全 NaN
    cols = ["g_good1", "g_good2", "g_constant", "g_sparse", "g_allnan"]
    data = np.column_stack([good1, good2, constant, sparse, all_nan]).astype(np.float32)
    return cols, data


def _make_registry(tmp_path: Path) -> ColumnGroupRegistry:
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    cols, data = _build_columns_and_data()
    registry.save_data(_group("1h_L2_mixed", cols, data), data)

    # 整組全 dead（兩欄都常數）
    dead_cols = ["d_const_a", "d_const_b"]
    dead_data = np.column_stack([
        np.full(ROWS, 7.0, dtype=np.float32),
        np.full(ROWS, 9.0, dtype=np.float32),
    ]).astype(np.float32)
    registry.save_data(_group("1h_L2_alldead", dead_cols, dead_data), dead_data)
    return registry


def _collect_output_columns(raw_dir: Path) -> set[str]:
    cols: set[str] = set()
    for pq_file in raw_dir.glob("*.parquet"):
        cols.update(pq.read_schema(pq_file).names)
    return cols


def _strip_tf_tag(name: str) -> str:
    # _write_group 會插入 tf 標記：g_good1 → g_1h_good1。還原成可比對的尾段。
    parts = name.split("_", 2)
    if len(parts) == 3 and parts[1] == "1h":
        return f"{parts[0]}_{parts[2]}"
    return name


# ─── 核心：dead-drop 生效 ───────────────────────────────────────


def test_dead_drop_removes_dead_keeps_good(tmp_path) -> None:
    registry = _make_registry(tmp_path)
    storage = FeatureStorage(str(tmp_path / "features"))

    raw_dir, summary = storage.write_raw_from_registry_stream(
        symbol="SYN",
        tf="1h",
        config_hash="cfg_dead",
        registry=registry,
        preprocessor=None,          # Mode-C passthrough：隔離 dead-drop，不做 L6.5 transform
        cleanup_intermediate=True,
        l65_mode="none",
        dead_drop_min_valid=MIN_VALID,
    )

    out_cols = {_strip_tf_tag(c) for c in _collect_output_columns(raw_dir)}

    # good 欄保留
    assert "g_good1" in out_cols
    assert "g_good2" in out_cols
    # dead 欄移除
    assert "g_constant" not in out_cols
    assert "g_sparse" not in out_cols
    assert "g_allnan" not in out_cols
    # 整組全 dead → 完全消失
    assert "d_const_a" not in out_cols
    assert "d_const_b" not in out_cols

    # summary 統計：3（mixed 組）+ 2（alldead 組）= 5 dropped，2 groups affected
    assert summary["dead_dropped_cols"] == 5
    assert summary["dead_affected_groups"] == 2
    assert summary["feature_count"] == 2  # 只剩 g_good1, g_good2


def test_all_dead_group_still_frees_source(tmp_path) -> None:
    """I-6：整組全 dead 時 parquet 不寫，但源頭 npy 仍釋放。"""
    registry = _make_registry(tmp_path)
    alldead_source = registry.get("1h_L2_alldead").disk_path
    storage = FeatureStorage(str(tmp_path / "features"))

    raw_dir, summary = storage.write_raw_from_registry_stream(
        symbol="SYN",
        tf="1h",
        config_hash="cfg_dead",
        registry=registry,
        preprocessor=None,
        cleanup_intermediate=True,
        l65_mode="none",
        dead_drop_min_valid=MIN_VALID,
    )

    # alldead 組無對應 parquet
    assert not (raw_dir / "1h_L2_alldead.parquet").exists()
    # 但源頭被清理 + npy 釋放
    assert alldead_source is not None and not alldead_source.exists()
    assert summary["npy_freed_bytes"] > 0


# ─── disable = no-op ────────────────────────────────────────────


def test_disabled_is_noop(tmp_path) -> None:
    registry = _make_registry(tmp_path)
    storage = FeatureStorage(str(tmp_path / "features"))

    raw_dir, summary = storage.write_raw_from_registry_stream(
        symbol="SYN",
        tf="1h",
        config_hash="cfg_nodrop",
        registry=registry,
        preprocessor=None,
        cleanup_intermediate=True,
        l65_mode="none",
        dead_drop_min_valid=None,   # disable
    )

    out_cols = {_strip_tf_tag(c) for c in _collect_output_columns(raw_dir)}
    # 全部欄位保留（含 dead）
    assert {"g_good1", "g_good2", "g_constant", "g_sparse", "g_allnan"}.issubset(out_cols)
    assert {"d_const_a", "d_const_b"}.issubset(out_cols)
    assert summary["dead_dropped_cols"] == 0
    assert summary["dead_affected_groups"] == 0
    assert summary["feature_count"] == 7


# ─── CGSA 與 frame-path 標準一致契約 ────────────────────────────


def test_cgsa_matches_frame_path_dead_set(tmp_path) -> None:
    """同一份資料：CGSA stream 丟的欄位 == frame-path find_dead_columns 丟的欄位。"""
    cols, data = _build_columns_and_data()

    # frame-path 判定
    df = pd.DataFrame(data, columns=cols)
    frame_dead, _ = find_dead_columns(df, min_valid_samples=MIN_VALID)

    # CGSA stream 判定（透過實際 write 後比對留存欄位）
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    registry.save_data(_group("1h_L2_mixed", cols, data), data)
    storage = FeatureStorage(str(tmp_path / "features"))
    raw_dir, _ = storage.write_raw_from_registry_stream(
        symbol="SYN", tf="1h", config_hash="cfg_contract",
        registry=registry, preprocessor=None,
        cleanup_intermediate=True, l65_mode="none",
        dead_drop_min_valid=MIN_VALID,
    )
    kept = {_strip_tf_tag(c) for c in _collect_output_columns(raw_dir)}
    cgsa_dead = set(cols) - kept

    assert cgsa_dead == set(frame_dead), (
        f"CGSA stream dead set 與 frame-path 不一致: cgsa={cgsa_dead} frame={set(frame_dead)}"
    )
