import hashlib
import json
import threading
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from api.services.feature_factory_service import FeatureFactoryService
from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.feature_storage import FeatureStorage

_GOLDEN_DIR = Path(__file__).resolve().parents[1] / "_golden" / "v2_ts"


def _build_group(group_id: str, shape: tuple[int, int], timeframe: str = "1h") -> ColumnGroup:
    columns = tuple(f"{group_id}_col_{index}" for index in range(shape[1]))
    return ColumnGroup(
        group_id=group_id,
        layer=LayerSource.L2,
        timeframe=timeframe,
        data_source="derived",
        indicator="mock",
        columns=columns,
        shape=shape,
        dtype="float32",
    )


def _make_registry(tmp_path: Path, groups: Dict[str, np.ndarray]) -> ColumnGroupRegistry:
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    for group_id, data in groups.items():
        timeframe = group_id.split("_", 1)[0] if "_" in group_id else "1h"
        registry.save_data(_build_group(group_id, data.shape, timeframe=timeframe), data)
    return registry


def _feature_fingerprint(run_dir: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for path in sorted((run_dir / "raw").glob("*.parquet")):
        table = pq.read_table(path)
        df = table.to_pandas()
        columns = [str(column) for column in df.columns]
        stats = {}
        for column in columns:
            series = df[column]
            values = series.to_numpy()
            stats[column] = {
                "mean": None if series.dropna().empty else float(series.mean()),
                "std": None if series.dropna().shape[0] <= 1 else float(series.std()),
                "nan_count": int(series.isna().sum()),
                "value_hash": hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest(),
            }
        result[path.name] = {
            "column_sha256": hashlib.sha256(
                json.dumps(columns, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "stats": stats,
        }
    return result


def _manifest_allowlist(run_dir: Path) -> Dict[str, Any]:
    manifest = json.loads((run_dir / "feature_manifest.json").read_text(encoding="utf-8"))
    raw = manifest["artifacts"]["raw"]
    return {
        "groups": raw["groups"],
        "row_count": raw["row_count"],
        "feature_schema_hash": raw["feature_schema_hash"],
        "total_features": raw["total_features"],
        "dtype": {
            group_id: group_meta.get("dtype")
            for group_id, group_meta in raw["groups"].items()
        },
    }


def _load_g1_baseline() -> Dict[str, Any]:
    return json.loads((_GOLDEN_DIR / "g1_baseline_fingerprint.json").read_text(encoding="utf-8"))


def _build_service_for_run(run_dir: Path) -> FeatureFactoryService:
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._lock = threading.Lock()
    service._df_cache = {}
    service._tasks = {
        "task-v2-ts": {
            "task_id": "task-v2-ts",
            "status": "completed",
            "result": {
                "hdf5_path": str(run_dir / "feature_manifest.json"),
                "metadata": {
                    "symbol": "BTCUSDT",
                    "timeframe": "1h",
                    "config_hash": run_dir.name,
                },
                "generation_time": 1.0,
                "layer_counts": {},
            },
        }
    }
    return service


def test_g1_g2_feature_parquet_and_manifest_allowlist_unchanged(tmp_path) -> None:
    """§G G1/G2: row_index persistence must not mutate feature parquet data.

    The same run is written twice, first without row_index and then with
    row_index.  Group parquet equality is proven by column-name sha256 plus
    per-column mean/std/nan_count/value_hash fingerprints, while manifest
    equality uses the §G G2 allowlist that excludes timestamp sidecar metadata.
    """
    storage = FeatureStorage(str(tmp_path / "features"))
    row_index = pd.date_range("2026-05-01", periods=5, freq="h")
    groups = {
        "g": pd.DataFrame(
            {
                "a": np.array([1.0, 2.0, np.nan, 4.0, 5.0], dtype=np.float32),
                "b": np.array([5.0, 4.0, 3.0, 2.0, 1.0], dtype=np.float32),
            },
            index=row_index,
        )
    }

    baseline_raw = storage.write_raw("BTCUSDT", "1h", "cfg_golden", groups)
    run_dir = baseline_raw.parent
    baseline_features = _feature_fingerprint(run_dir)
    baseline_manifest = _manifest_allowlist(run_dir)
    committed_baseline = _load_g1_baseline()

    assert baseline_features == committed_baseline["feature_fingerprint"]
    assert baseline_manifest == committed_baseline["manifest_allowlist"]

    storage.write_raw("BTCUSDT", "1h", "cfg_golden", groups, row_index=row_index)
    assert _feature_fingerprint(run_dir) == baseline_features
    assert _manifest_allowlist(run_dir) == baseline_manifest
    manifest = json.loads((run_dir / "feature_manifest.json").read_text(encoding="utf-8"))
    assert manifest["row_index"]["path"] == "timestamps.parquet"
    assert (run_dir / "timestamps.parquet").exists()


def test_g3_row_index_matches_source_and_csv_uses_isoformat(tmp_path) -> None:
    storage = FeatureStorage(str(tmp_path / "features"))
    row_index = pd.date_range("2026-05-10", periods=4, freq="h")
    groups = {
        "g": pd.DataFrame(
            {"feat_a": np.array([10.0, 11.0, 12.0, 13.0], dtype=np.float32)},
            index=row_index,
        )
    }
    raw_dir = storage.write_raw("BTCUSDT", "1h", "cfg_csv", groups, row_index=row_index)

    reader = FeatureReader(str(tmp_path / "features"))
    loaded = reader.load_row_index_v2("BTCUSDT", "1h", "cfg_csv")
    assert loaded is not None
    assert loaded.equals(row_index)

    service = _build_service_for_run(raw_dir.parent)
    payload = service.export_csv_stream(
        "task-v2-ts",
        columns=["feat_a"],
        max_rows=1,
        include_metadata_header=False,
    )
    lines = "".join(payload["generator"]).strip().splitlines()
    assert lines[1].split(",", 1)[0] == row_index[0].isoformat()


def test_regression_matrix_multi_tf_date_range_and_ic_first(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FFACT_MULTI_TF_COMPACT_ALIGNMENT", "1")
    row_index = pd.date_range("2026-05-20", periods=4, freq="h")
    registry = _make_registry(
        tmp_path,
        {
            "1h_L2_mock": np.arange(8, dtype=np.float32).reshape(4, 2),
            "12h_L2_mock": np.arange(100, 108, dtype=np.float32).reshape(4, 2),
        },
    )
    stream_storage = FeatureStorage(str(tmp_path / "stream_features"))
    stream_raw_dir, _summary = stream_storage.write_raw_from_registry_stream(
        symbol="BTCUSDT",
        tf="1h",
        config_hash="cfg_multi_tf",
        registry=registry,
        preprocessor=None,
        cleanup_intermediate=False,
        l65_mode="disabled",
        row_index=row_index,
    )
    stream_reader = FeatureReader(str(tmp_path / "stream_features"))
    assert stream_reader.load_row_index_v2("BTCUSDT", "1h", "cfg_multi_tf").equals(row_index)

    service = _build_service_for_run(stream_raw_dir.parent)
    service._tasks["task-v2-ts"]["result"]["metadata"]["config_hash"] = "cfg_multi_tf"
    manifest = json.loads((stream_raw_dir.parent / "feature_manifest.json").read_text(encoding="utf-8"))
    first_feature = next(iter(manifest["artifacts"]["raw"]["groups"].values()))["columns"][0]
    selected = service._load_cgsa_selected_rows(
        service._load_task_context("task-v2-ts"),
        selected_features=[first_feature],
        offset=2,
        limit=1,
    )
    assert selected["rows"][0]["timestamp"] == row_index[2].isoformat()

    ic_storage = FeatureStorage(str(tmp_path / "ic_features"))
    ic_groups = {
        "ic_g": pd.DataFrame(
            {"ic_feat": np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)},
            index=row_index,
        )
    }
    ic_storage.write_raw("BTCUSDT", "1h", "cfg_ic", ic_groups, row_index=row_index)
    ic_reader = FeatureReader(str(tmp_path / "ic_features"))
    assert ic_reader.load_row_index_v2("BTCUSDT", "1h", "cfg_ic").equals(row_index)
