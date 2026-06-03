from __future__ import annotations

import json
import threading
from types import SimpleNamespace

import numpy as np
import pandas as pd

from api.services.feature_factory_service import FeatureFactoryService


def _build_service_for_unit() -> FeatureFactoryService:
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._stats_cache = {}
    service._stats_name_sorted_cache = {}
    service._stats_name_keys_cache = {}
    service._stats_warming_tasks = set()
    service._cgsa_stats_mem_cache = {}
    service._cgsa_stats_warming_tasks = set()
    service._adf_cache = {}
    service._lock = threading.Lock()
    service._coalesce_browse = lambda _fp, fn: fn()
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
    assert result["quality"]["nan_ratio_quantiles"] == {
        "min": 0.0,
        "q1": 0.0,
        "median": 0.0,
        "q3": 0.0,
        "max": 0.0,
    }


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


def test_browse_summary_exposes_stats_warmup(monkeypatch):
    """browse_summary 須含 stats_warmup 結構化進度欄位。"""
    service = _build_service_for_unit()
    service._stats_warming_tasks = set()
    service._cgsa_stats_mem_cache = {}
    service._cgsa_stats_warming_tasks = set()
    service._lock = threading.Lock()
    service._coalesce_browse = lambda _fp, fn: fn()

    monkeypatch.setattr(
        service,
        "_load_task_features",
        lambda _task_id: (
            pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]}),
            {"symbol": "BTCUSDT", "timeframe": "1h", "metadata": {}},
        ),
    )
    monkeypatch.setattr(service, "_start_stats_cache_warmup", lambda *_a, **_k: None)
    monkeypatch.setattr(service, "_start_adf_cache_warmup", lambda *_a, **_k: None)
    monkeypatch.setattr(
        service,
        "_get_stats_warmup_progress",
        lambda *_a, **_k: {
            "computed": 1,
            "total": 2,
            "pct": 50.0,
            "complete": False,
        },
    )

    result = service.browse_summary("task-stats-warmup")

    warmup = result.get("stats_warmup")
    assert warmup is not None
    assert warmup["computed"] == 1
    assert warmup["total"] == 2
    assert warmup["pct"] == 50.0
    assert warmup["complete"] is False


def test_get_stats_warmup_progress_complete_when_cache_full(monkeypatch):
    """stats 全快取時 complete=True、pct=100。"""
    service = _build_service_for_unit()
    service._stats_cache = {
        "task-full": [{"name": "a"}, {"name": "b"}],
    }
    service._lock = threading.Lock()

    progress = service._get_stats_warmup_progress("task-full", total_features=2)

    assert progress["computed"] == 2
    assert progress["total"] == 2
    assert progress["pct"] == 100.0
    assert progress["complete"] is True


def test_assemble_data_quality_report_includes_nan_ratio_fields():
    """dq report 須含 nan_ratio_mean/max（供 batch adapter 取用）。"""
    service = _build_service_for_unit()
    columns = ["feat_a", "feat_b"]
    nan_ratios = pd.Series({"feat_a": 0.8, "feat_b": 0.1})

    report = service._assemble_data_quality_report(
        total_rows=100,
        columns=columns,
        nan_ratios=nan_ratios,
        first_valid_map={"feat_a": 80, "feat_b": 0},
        last_valid_map={"feat_a": 99, "feat_b": 99},
        row_nan_count=np.zeros(100, dtype=np.int64),
        timestamps=[str(i) for i in range(100)],
    )

    assert report["schema_version"] == "dq_v6"
    assert abs(report["nan_ratio_mean"] - 0.45) <= 0.01
    assert abs(report["nan_ratio_max"] - 0.8) <= 0.01
    independent = np.percentile(nan_ratios.values, [0, 25, 50, 75, 100])
    quantiles = report["nan_ratio_quantiles"]
    for key, idx in [("min", 0), ("q1", 1), ("median", 2), ("q3", 3), ("max", 4)]:
        assert abs(quantiles[key] - float(independent[idx])) <= 0.01


def test_browse_summary_nan_quantiles_match_percentile(monkeypatch):
    """browse_summary quality 須含真實 NaN 五數摘要，與 np.percentile 一致。"""
    service = _build_service_for_unit()

    frame = pd.DataFrame(
        {
            "feat_low": [1.0, 2.0, 3.0, 4.0, 5.0],
            "feat_mid": [np.nan, np.nan, 3.0, 4.0, 5.0],
            "feat_high": [np.nan, np.nan, np.nan, np.nan, 5.0],
        }
    )
    monkeypatch.setattr(
        service,
        "_load_task_features",
        lambda _task_id: (
            frame,
            {"symbol": "BTCUSDT", "timeframe": "1h", "metadata": {}},
        ),
    )
    monkeypatch.setattr(service, "_start_stats_cache_warmup", lambda *_a, **_k: None)
    monkeypatch.setattr(service, "_start_adf_cache_warmup", lambda *_a, **_k: None)
    monkeypatch.setattr(
        service,
        "_get_stats_warmup_progress",
        lambda *_a, **_k: {"computed": 3, "total": 3, "pct": 100.0, "complete": True},
    )

    result = service.browse_summary("task-nan-quantiles")
    quantiles = result["quality"]["nan_ratio_quantiles"]
    expected = np.percentile(frame.isna().mean().values, [0, 25, 50, 75, 100])

    assert result["quality"]["nan_ratio_mean"] > 0.0
    assert quantiles["median"] > 0.0
    for key, idx in [("min", 0), ("q1", 1), ("median", 2), ("q3", 3), ("max", 4)]:
        assert abs(quantiles[key] - float(expected[idx])) <= 0.01


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