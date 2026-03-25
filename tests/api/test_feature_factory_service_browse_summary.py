from __future__ import annotations

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