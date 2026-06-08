from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from momentum.FeatureEngineering.core.column_group import AlignmentMeta, ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
from momentum.FeatureEngineering.timeframe.tf_aligner import CURRENT_MTF_ALIGN_VERSION


def _write_idx_map(path: Path, idx_map: np.ndarray) -> Path:
    with path.open("wb") as handle:
        np.save(handle, np.asarray(idx_map, dtype=np.int32), allow_pickle=False)
    return path


def test_compact_equals_noncompact(tmp_path: Path) -> None:
    source = np.array([[1.0, 10.0], [2.0, 20.0], [3.0, 30.0]], dtype=np.float32)
    idx_map = np.array([-1, 0, 0, 1, 2], dtype=np.int64)
    expected = MultiTFGenerator._align_group_array(source, idx_map, n_primary=len(idx_map))

    compact = ColumnGroupRegistry(tmp_path / "compact")
    source_path = compact.work_dir / "12h_L1_compact.npy"
    idx_path = _write_idx_map(compact.work_dir / ".align_12h_to_1h_open_minus.npy", idx_map)
    np.save(source_path, source, allow_pickle=False)
    compact.register(
        ColumnGroup(
            group_id="12h_L1_compact",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("a", "b"),
            shape=expected.shape,
            disk_path=source_path,
            alignment=AlignmentMeta(
                source_timeframe="12h",
                primary_timeframe="1h",
                source_n_rows=source.shape[0],
                primary_n_rows=len(idx_map),
                idx_map_path=idx_path,
                alignment_mode="open_minus",
                source_dur_ns=12 * 3600 * 1_000_000_000,
                primary_dur_ns=3600 * 1_000_000_000,
                mode="open_time",
                align_algo_version=CURRENT_MTF_ALIGN_VERSION,
            ),
        )
    )
    compact.write_manifest()

    dense = ColumnGroupRegistry(tmp_path / "dense")
    dense_path = dense.work_dir / "12h_L1_dense.npy"
    np.save(dense_path, expected, allow_pickle=False)
    dense.register(
        ColumnGroup(
            group_id="12h_L1_dense",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("a", "b"),
            shape=expected.shape,
            disk_path=dense_path,
        )
    )

    np.testing.assert_array_equal(compact.load_data("12h_L1_compact"), dense.load_data("12h_L1_dense"))

    manifest = json.loads((compact.work_dir / "manifest.json").read_text())
    alignment = manifest["groups"][0]["alignment"]
    assert alignment["align_algo_version"] == CURRENT_MTF_ALIGN_VERSION
    assert alignment["source_dur_ns"] == 12 * 3600 * 1_000_000_000
    assert alignment["primary_dur_ns"] == 3600 * 1_000_000_000
    assert alignment["mode"] == "open_time"


def test_legacy_offset_loads_without_crash(tmp_path: Path) -> None:
    work_dir = tmp_path / "legacy"
    work_dir.mkdir()
    source_path = work_dir / "12h_L1_legacy.npy"
    idx_path = work_dir / ".align_12h_to_1h_close_time.npy"
    np.save(source_path, np.array([[1.0], [2.0]], dtype=np.float32), allow_pickle=False)
    np.save(idx_path, np.array([0, 0, 1], dtype=np.int32), allow_pickle=False)

    manifest = {
        "schema_version": 2,
        "groups": [
            {
                "group_id": "12h_L1_legacy",
                "layer": "L1",
                "timeframe": "12h",
                "data_source": "close",
                "indicator": "TEST",
                "columns": ["x"],
                "shape": [3, 1],
                "dtype": "float32",
                "npy_path": source_path.name,
                "shards": [],
                "alignment": {
                    "source_timeframe": "12h",
                    "primary_timeframe": "1h",
                    "source_n_rows": 2,
                    "primary_n_rows": 3,
                    "idx_map_path": idx_path.name,
                    "alignment_mode": "close_time",
                    "offset_ns": 0,
                },
                "parquet_path": None,
            }
        ],
    }
    (work_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    resumed = ColumnGroupRegistry.resume_from_manifest(work_dir)
    group = resumed.get("12h_L1_legacy")

    assert group.alignment is not None
    assert group.alignment.align_algo_version == 1
    assert group.alignment.source_dur_ns == 0
    np.testing.assert_array_equal(resumed.load_data("12h_L1_legacy"), np.array([[1.0], [1.0], [2.0]], dtype=np.float32))
