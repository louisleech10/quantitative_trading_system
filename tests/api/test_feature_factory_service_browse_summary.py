from __future__ import annotations

import json
import threading
from types import SimpleNamespace

import pandas as pd

from api.services.feature_factory_service import FeatureFactoryService


def _build_service_for_unit() -> FeatureFactoryService:
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._stats_cache = {}
    service._stats_name_sorted_cache = {}
    service._stats_name_keys_cache = {}
    service._adf_cache = {}
    service._export_service = SimpleNamespace(
        _infer_category=lambda _name: "other",
        _infer_layer=lambda _name: "layer1",
        _infer_level=lambda _cat: "L1",
    )
    return service


def test_build_stats_rows_with_no_columns_returns_empty_rows(monkeypatch):
    service = _build_service_for_unit()

    monkeypatch.setattr(
        service,
        "_load_task_features",
        lambda _task_id: (pd.DataFrame(index=[1, 2, 3]), {}),
    )

    rows = service._build_stats_rows("task-empty-columns")

    assert rows == []
    assert service._stats_cache["task-empty-columns"] == []
    assert service._stats_name_sorted_cache["task-empty-columns"] == []
    assert service._stats_name_keys_cache["task-empty-columns"] == []


def test_browse_summary_with_no_columns_has_json_safe_quality(monkeypatch):
    service = _build_service_for_unit()

    monkeypatch.setattr(
        service,
        "_load_task_features",
        lambda _task_id: (
            pd.DataFrame(index=[1, 2, 3]),
            {"symbol": "ETHUSDT", "timeframe": "12h", "metadata": {}},
        ),
    )
    monkeypatch.setattr(service, "_start_stats_cache_warmup", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service, "_start_adf_cache_warmup", lambda *_args, **_kwargs: None)

    result = service.browse_summary("task-empty-columns")

    assert result["total_features"] == 0
    assert result["quality"]["nan_ratio_mean"] == 0.0
    assert result["quality"]["nan_ratio_max"] == 0.0


def test_cgsa_catalog_disk_cache_roundtrip(tmp_path):
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._cgsa_catalog_cache = {}
    service._cgsa_column_path_cache = {}

    context = {
        "manifest_dir": tmp_path,
        "file_path": tmp_path / "manifest.json",
        "manifest": {"feature_schema_hash": "schema-1"},
    }
    fast = {
        "columns": ["L1_close_A", "L2_close_B"],
        "total_rows": 12,
        "column_to_path": {
            "L1_close_A": tmp_path / "a.parquet",
            "L2_close_B": tmp_path / "b.parquet",
        },
    }
    rows = [
        {"name": "L1_close_A", "category": "trend", "level": "basic", "layer": "layer1", "nan_ratio": 0.0},
        {"name": "L2_close_B", "category": "momentum", "level": "derived", "layer": "layer2", "nan_ratio": 0.1},
    ]

    service._persist_cgsa_catalog_cache(context, fast, rows)
    loaded = service._load_cgsa_catalog_disk_cache("task-catalog", context, fast)

    assert loaded == rows
    assert (tmp_path / FeatureFactoryService._CGSA_CATALOG_CACHE_NAME).exists()
    meta = json.loads((tmp_path / FeatureFactoryService._CGSA_CATALOG_CACHE_META_NAME).read_text())
    assert meta["feature_schema_hash"] == "schema-1"
    assert service._cgsa_column_path_cache["task-catalog"] == fast["column_to_path"]


def test_cgsa_stats_persist_uses_incremental_parts(tmp_path):
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._lock = threading.Lock()
    service._cgsa_stats_mem_cache = {}
    context = {"manifest_dir": tmp_path}

    first = pd.DataFrame({"mean": [1.0]}, index=pd.Index(["feature_a"], name="name"))
    second = pd.DataFrame({"mean": [2.0]}, index=pd.Index(["feature_b"], name="name"))

    service._persist_cgsa_stats("task-stats", context, first)
    service._persist_cgsa_stats("task-stats", context, second)

    parts_dir = tmp_path / FeatureFactoryService._CGSA_STATS_PARTS_DIR_NAME
    assert len(list(parts_dir.glob("*.parquet"))) == 2
    assert not (tmp_path / FeatureFactoryService._CGSA_STATS_CACHE_NAME).exists()

    reloaded = FeatureFactoryService.__new__(FeatureFactoryService)
    reloaded._lock = threading.Lock()
    reloaded._cgsa_stats_mem_cache = {}
    loaded = reloaded._load_cgsa_stats_mem("task-stats", context)

    assert list(loaded.index) == ["feature_a", "feature_b"]
    assert loaded.loc["feature_a", "mean"] == 1.0
    assert loaded.loc["feature_b", "mean"] == 2.0