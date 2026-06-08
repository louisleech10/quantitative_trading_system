import json

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.feature_storage import FeatureStorage


def test_load_row_index_v2(tmp_path) -> None:
    storage = FeatureStorage(str(tmp_path / "features"))
    reader = FeatureReader(str(tmp_path / "features"))
    row_index = pd.date_range("2026-03-01", periods=4, freq="h")
    groups = {
        "g": pd.DataFrame(
            {"a": np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)},
            index=row_index,
        )
    }

    storage.write_raw("SYNTHETIC", "1h", "cfg_new", groups, row_index=row_index)
    loaded = reader.load_row_index_v2("SYNTHETIC", "1h", "cfg_new")
    assert loaded is not None
    assert loaded.equals(row_index)

    storage.write_raw("SYNTHETIC", "1h", "cfg_old", groups)
    assert reader.load_row_index_v2("SYNTHETIC", "1h", "cfg_old") is None

    missing_dir = storage.feature_run_dir("SYNTHETIC", "1h", "cfg_missing")
    storage.write_raw("SYNTHETIC", "1h", "cfg_missing", groups, row_index=row_index)
    (missing_dir / "timestamps.parquet").unlink()
    with pytest.raises(ValueError, match="row_index declared but file missing"):
        reader.load_row_index_v2("SYNTHETIC", "1h", "cfg_missing")

    mismatch_dir = storage.feature_run_dir("SYNTHETIC", "1h", "cfg_mismatch")
    storage.write_raw("SYNTHETIC", "1h", "cfg_mismatch", groups, row_index=row_index)
    manifest_path = mismatch_dir / "feature_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["row_index"]["count"] = 3
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="row_index length mismatch"):
        reader.load_row_index_v2("SYNTHETIC", "1h", "cfg_mismatch")

    null_count_dir = storage.feature_run_dir("SYNTHETIC", "1h", "cfg_null_count")
    storage.write_raw("SYNTHETIC", "1h", "cfg_null_count", groups, row_index=row_index)
    manifest_path = null_count_dir / "feature_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["row_index"]["count"] = None
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="row_index count must be a non-null integer"):
        reader.load_row_index_v2("SYNTHETIC", "1h", "cfg_null_count")
