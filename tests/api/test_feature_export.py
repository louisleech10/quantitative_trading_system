"""Feature export API tests for Phase 3.4.1."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import h5py
import httpx
import numpy as np
import pytest
import pytest_asyncio
import pandas as pd
from fastapi import FastAPI

from api.routes.feature_factory import router as feature_factory_router
from api.services.feature_export_service import FeatureExportService
from api.services.feature_factory_service import FeatureFactoryService, feature_factory_service
import api.services.feature_factory_service as feature_service_module
from momentum.FeatureEngineering.feature_storage import FeatureStorage


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(feature_factory_router)
    return test_app


@pytest_asyncio.fixture
async def async_client(app: FastAPI):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ==================== CSV 匯出（5） ====================


@pytest.mark.asyncio
async def test_export_csv_stream_success(async_client, monkeypatch):
    """CSV 匯出：串流成功回傳。"""

    def fake_export_csv_stream(task_id, columns, max_rows, include_metadata_header, include_datasource=False):
        assert task_id == "task-123"
        assert columns is None
        assert max_rows is None
        assert include_metadata_header is True
        assert include_datasource is False

        def generator():
            yield "# task_id: task-123\n"
            yield "timestamp,feature_a\n"
            yield "2026-01-01,1.23\n"

        return {
            "generator": generator(),
            "filename": "BTCUSDT_12h_features_task-123.csv",
            "feature_count": 1,
            "row_count": 1,
        }

    monkeypatch.setattr(feature_factory_service, "export_csv_stream", fake_export_csv_stream)

    async with async_client.stream("GET", "/api/v1/features/export/task-123/csv") as response:
        assert response.status_code == 200
        assert "attachment; filename=BTCUSDT_12h_features_task-123.csv" in response.headers.get(
            "content-disposition", ""
        )
        assert response.headers.get("x-export-task-id") == "task-123"
        content = ""
        async for chunk in response.aiter_text():
            content += chunk

    assert "timestamp,feature_a" in content


@pytest.mark.asyncio
async def test_export_csv_columns_filter(async_client, monkeypatch):
    """CSV 匯出：欄位篩選轉換正確。"""

    def fake_export_csv_stream(task_id, columns, max_rows, include_metadata_header, include_datasource=False):
        assert columns == ["a", "b", "c"]
        assert include_datasource is False

        def generator():
            yield "timestamp,a,b,c\n"

        return {
            "generator": generator(),
            "filename": "x.csv",
            "feature_count": 3,
            "row_count": 0,
        }

    monkeypatch.setattr(feature_factory_service, "export_csv_stream", fake_export_csv_stream)

    response = await async_client.get(
        "/api/v1/features/export/task-1/csv",
        params={"columns": "a,b,c"},
    )

    assert response.status_code == 200
    assert "timestamp,a,b,c" in response.text


@pytest.mark.asyncio
async def test_export_csv_max_rows(async_client, monkeypatch):
    """CSV 匯出：行數限制參數轉發正確。"""

    def fake_export_csv_stream(task_id, columns, max_rows, include_metadata_header, include_datasource=False):
        assert max_rows == 10
        assert include_datasource is False

        def generator():
            yield "timestamp,a\n"
            yield "t,1\n"

        return {
            "generator": generator(),
            "filename": "x.csv",
            "feature_count": 1,
            "row_count": 1,
        }

    monkeypatch.setattr(feature_factory_service, "export_csv_stream", fake_export_csv_stream)

    response = await async_client.get(
        "/api/v1/features/export/task-1/csv",
        params={"max_rows": 10},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_export_csv_metadata_header_flag(async_client, monkeypatch):
    """CSV 匯出：metadata header 開關參數轉發正確。"""

    def fake_export_csv_stream(task_id, columns, max_rows, include_metadata_header, include_datasource=False):
        assert include_metadata_header is False
        assert include_datasource is False

        def generator():
            yield "timestamp,a\n"
            yield "t,1\n"

        return {
            "generator": generator(),
            "filename": "x.csv",
            "feature_count": 1,
            "row_count": 1,
        }

    monkeypatch.setattr(feature_factory_service, "export_csv_stream", fake_export_csv_stream)

    response = await async_client.get(
        "/api/v1/features/export/task-1/csv",
        params={"include_metadata_header": False},
    )

    assert response.status_code == 200
    assert not response.text.startswith("#")


@pytest.mark.asyncio
async def test_export_csv_not_found(async_client, monkeypatch):
    """CSV 匯出：task 不存在時回傳 404。"""

    def fake_export_csv_stream(*args, **kwargs):
        raise FileNotFoundError("Result not found")

    monkeypatch.setattr(feature_factory_service, "export_csv_stream", fake_export_csv_stream)

    response = await async_client.get("/api/v1/features/export/missing/csv")

    assert response.status_code == 404


def _build_cgsa_v2_service(tmp_path):
    storage = FeatureStorage(str(tmp_path / "features"))
    row_index = pd.date_range("2026-04-01", periods=4, freq="h")
    groups = {
        "g": pd.DataFrame(
            {
                "feat_a": np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32),
                "feat_b": np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32),
            },
            index=row_index,
        )
    }
    raw_dir = storage.write_raw("BTCUSDT", "1h", "cfg_ts", groups, row_index=row_index)
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._lock = threading.Lock()
    service._df_cache = {}
    service._tasks = {
        "task-ts": {
            "task_id": "task-ts",
            "status": "completed",
            "result": {
                "hdf5_path": str(raw_dir.parent / "feature_manifest.json"),
                "metadata": {
                    "symbol": "BTCUSDT",
                    "timeframe": "1h",
                    "config_hash": "cfg_ts",
                },
                "generation_time": 1.0,
                "layer_counts": {},
            },
        }
    }
    return service, row_index, raw_dir.parent


def _write_full_kline_cache(cache_root, symbol: str, timeframe: str, row_count: int) -> None:
    h5_path = cache_root / "feature_klines" / "kline_cache.h5"
    h5_path.parent.mkdir(parents=True, exist_ok=True)
    dtype = np.dtype(
        [
            ("timestamp", "i8"),
            ("open", "f4"),
            ("high", "f4"),
            ("low", "f4"),
            ("close", "f4"),
            ("volume", "f4"),
            ("taker_buy_volume", "f4"),
            ("taker_ratio", "f4"),
            ("quote_volume", "f4"),
            ("number_of_trades", "i4"),
        ]
    )
    data = np.zeros(row_count, dtype=dtype)
    data["timestamp"] = (
        pd.date_range("2023-01-01", periods=row_count, freq="h").view("int64")
        // 1_000_000_000
    )
    data["open"] = np.arange(row_count, dtype=np.float32)
    data["high"] = data["open"] + 1
    data["low"] = data["open"] - 1
    data["close"] = data["open"] + 0.5
    data["volume"] = 1.0

    with h5py.File(h5_path, "w") as h5_file:
        h5_file.create_dataset(f"{symbol}/{timeframe}/data", data=data)


def _build_date_subset_cgsa_service(
    tmp_path,
    *,
    config_hash: str,
    with_row_index: bool,
    feature_rows: int = 121,
) -> tuple[FeatureFactoryService, pd.DatetimeIndex, Path]:
    storage = FeatureStorage(str(tmp_path / "features"))
    row_index = pd.date_range("2024-12-01", periods=feature_rows, freq="h")
    groups = {
        "g": pd.DataFrame(
            {
                "feat_a": np.linspace(1.0, 2.0, feature_rows, dtype=np.float32),
                "feat_b": np.linspace(10.0, 20.0, feature_rows, dtype=np.float32),
            },
            index=row_index,
        )
    }
    raw_dir = storage.write_raw(
        "BTCUSDT",
        "1h",
        config_hash,
        groups,
        row_index=row_index if with_row_index else None,
    )
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._lock = threading.Lock()
    service._df_cache = {}
    service._tasks = {
        f"task-{config_hash}": {
            "task_id": f"task-{config_hash}",
            "status": "completed",
            "result": {
                "hdf5_path": str(raw_dir.parent / "feature_manifest.json"),
                "metadata": {
                    "symbol": "BTCUSDT",
                    "timeframe": "1h",
                    "config_hash": config_hash,
                },
                "generation_time": 1.0,
                "layer_counts": {},
            },
        }
    }
    return service, row_index, raw_dir.parent


def test_cgsa_csv_has_real_timestamps_on_date_range(tmp_path) -> None:
    service, row_index, _run_dir = _build_cgsa_v2_service(tmp_path)

    payload = service.export_csv_stream(
        "task-ts",
        columns=["feat_a"],
        max_rows=2,
        include_metadata_header=False,
    )
    csv_text = "".join(payload["generator"])

    lines = csv_text.strip().splitlines()
    assert lines[0] == "timestamp,feat_a"
    assert lines[1].split(",", 1)[0] == row_index[0].isoformat()
    assert lines[2].split(",", 1)[0] == row_index[1].isoformat()
    assert [line.split(",", 1)[0] for line in lines[1:]] != ["0", "1"]


def test_cgsa_preview_rows_have_timestamps(tmp_path) -> None:
    service, row_index, _run_dir = _build_cgsa_v2_service(tmp_path)
    context = service._load_task_context("task-ts")

    payload = service._load_cgsa_selected_rows(
        context,
        selected_features=["feat_a"],
        offset=1,
        limit=2,
    )

    assert [row["timestamp"] for row in payload["rows"]] == [
        row_index[1].isoformat(),
        row_index[2].isoformat(),
    ]


def test_cgsa_row_index_mismatch_does_not_fallback_to_integer(tmp_path) -> None:
    service, _row_index, run_dir = _build_cgsa_v2_service(tmp_path)
    manifest_path = run_dir / "feature_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["row_index"]["count"] = 3
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="row_index length mismatch"):
        payload = service.export_csv_stream(
            "task-ts",
            columns=["feat_a"],
            max_rows=2,
            include_metadata_header=False,
        )
        "".join(payload["generator"])


def test_cgsa_csv_date_subset_uses_sidecar_not_full_kline_cache(
    tmp_path,
    monkeypatch,
    caplog,
) -> None:
    """Reproduce the original 121 feature rows vs 20352 kline rows bug.

    A V2 run with row_index sidecar must export ISO timestamps from the sidecar
    and must not touch the old kline fallback path that length-mismatches.
    """
    monkeypatch.setattr(feature_service_module.settings, "data_cache_path", tmp_path)
    _write_full_kline_cache(tmp_path, "BTCUSDT", "1h", row_count=20352)
    service, row_index, _run_dir = _build_date_subset_cgsa_service(
        tmp_path,
        config_hash="cfg_subset_sidecar",
        with_row_index=True,
        feature_rows=121,
    )

    kline_called = False

    def fail_if_kline_called(*args, **kwargs):
        nonlocal kline_called
        kline_called = True
        raise AssertionError("sidecar run must not call kline fallback")

    monkeypatch.setattr(service, "_load_cgsa_kline_timestamps", fail_if_kline_called)

    with caplog.at_level("WARNING", logger="api.feature_factory_service"):
        payload = service.export_csv_stream(
            "task-cfg_subset_sidecar",
            columns=["feat_a"],
            max_rows=3,
            include_metadata_header=False,
        )
        csv_text = "".join(payload["generator"])

    lines = csv_text.strip().splitlines()
    assert lines[0] == "timestamp,feat_a"
    assert [line.split(",", 1)[0] for line in lines[1:]] == [
        row_index[0].isoformat(),
        row_index[1].isoformat(),
        row_index[2].isoformat(),
    ]
    assert not kline_called
    assert "Kline timestamp length mismatch" not in caplog.text


def test_cgsa_csv_legacy_without_row_index_falls_back_to_integer_on_full_kline_mismatch(
    tmp_path,
    monkeypatch,
    caplog,
) -> None:
    """Control case: old runs without row_index still use kline fallback.

    The same 121 vs 20352 layout falls back to integer rows, proving the sidecar
    is what fixes the real date-range subset bug.
    """
    monkeypatch.setattr(feature_service_module.settings, "data_cache_path", tmp_path)
    _write_full_kline_cache(tmp_path, "BTCUSDT", "1h", row_count=20352)
    service, _row_index, _run_dir = _build_date_subset_cgsa_service(
        tmp_path,
        config_hash="cfg_subset_legacy",
        with_row_index=False,
        feature_rows=121,
    )

    with caplog.at_level("WARNING", logger="api.feature_factory_service"):
        payload = service.export_csv_stream(
            "task-cfg_subset_legacy",
            columns=["feat_a"],
            max_rows=3,
            include_metadata_header=False,
        )
        csv_text = "".join(payload["generator"])

    lines = csv_text.strip().splitlines()
    assert lines[0] == "timestamp,feat_a"
    assert [line.split(",", 1)[0] for line in lines[1:]] == ["0", "1", "2"]
    assert "Kline timestamp length mismatch for BTCUSDT/1h/data: 20352 != 121" in caplog.text


# ==================== JSON 匯出（5） ====================


@pytest.mark.asyncio
async def test_export_json_schema_structure(async_client, monkeypatch):
    """JSON 匯出：主結構符合 schema。"""

    def fake_export_json_report(**kwargs):
        return {
            "version": "1.0",
            "type": "feature_factory_report",
            "metadata": {"task_id": "task-1"},
            "feature_catalog": {"by_category": {}, "by_level": {}, "by_layer": {}},
            "statistics": {"summary": {}, "per_feature": []},
            "sample_data": {"columns": [], "rows": []},
            "quality_alerts": [],
            "correlation_hotspots": [],
        }

    monkeypatch.setattr(feature_factory_service, "export_json_report", fake_export_json_report)

    response = await async_client.get("/api/v1/features/export/task-1/json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "feature_factory_report"
    assert "feature_catalog" in payload
    assert "statistics" in payload


@pytest.mark.asyncio
async def test_export_json_level_catalog(async_client, monkeypatch):
    """JSON 匯出：分級統計欄位存在。"""

    def fake_export_json_report(**kwargs):
        return {
            "version": "1.0",
            "type": "feature_factory_report",
            "metadata": {},
            "feature_catalog": {
                "by_category": {},
                "by_level": {
                    "L1_basic": {"count": 10},
                    "L2_intermediate": {"count": 8},
                    "L3_advanced": {"count": 4},
                },
                "by_layer": {},
            },
            "statistics": {"summary": {}, "per_feature": []},
            "sample_data": {"columns": [], "rows": []},
            "quality_alerts": [],
            "correlation_hotspots": [],
        }

    monkeypatch.setattr(feature_factory_service, "export_json_report", fake_export_json_report)

    response = await async_client.get("/api/v1/features/export/task-1/json")

    assert response.status_code == 200
    levels = response.json()["feature_catalog"]["by_level"]
    assert set(levels.keys()) == {"L1_basic", "L2_intermediate", "L3_advanced"}


@pytest.mark.asyncio
async def test_export_json_per_feature_statistics(async_client, monkeypatch):
    """JSON 匯出：per_feature 統計存在。"""

    def fake_export_json_report(**kwargs):
        return {
            "version": "1.0",
            "type": "feature_factory_report",
            "metadata": {},
            "feature_catalog": {"by_category": {}, "by_level": {}, "by_layer": {}},
            "statistics": {
                "summary": {"nan_ratio_mean": 0.01},
                "per_feature": [{"name": "ms_a", "std": 0.1}],
            },
            "sample_data": {"columns": [], "rows": []},
            "quality_alerts": [],
            "correlation_hotspots": [],
        }

    monkeypatch.setattr(feature_factory_service, "export_json_report", fake_export_json_report)

    response = await async_client.get("/api/v1/features/export/task-1/json")

    assert response.status_code == 200
    per_feature = response.json()["statistics"]["per_feature"]
    assert len(per_feature) == 1
    assert per_feature[0]["name"] == "ms_a"


@pytest.mark.asyncio
async def test_export_json_quality_alerts(async_client, monkeypatch):
    """JSON 匯出：quality_alerts 欄位存在且可讀。"""

    def fake_export_json_report(**kwargs):
        return {
            "version": "1.0",
            "type": "feature_factory_report",
            "metadata": {},
            "feature_catalog": {"by_category": {}, "by_level": {}, "by_layer": {}},
            "statistics": {"summary": {}, "per_feature": []},
            "sample_data": {"columns": [], "rows": []},
            "quality_alerts": [{"severity": "warning", "feature": "ent_x"}],
            "correlation_hotspots": [],
        }

    monkeypatch.setattr(feature_factory_service, "export_json_report", fake_export_json_report)

    response = await async_client.get("/api/v1/features/export/task-1/json")

    assert response.status_code == 200
    alerts = response.json()["quality_alerts"]
    assert alerts[0]["severity"] == "warning"


@pytest.mark.asyncio
async def test_export_json_correlation_hotspots(async_client, monkeypatch):
    """JSON 匯出：correlation_hotspots 欄位存在。"""

    def fake_export_json_report(**kwargs):
        return {
            "version": "1.0",
            "type": "feature_factory_report",
            "metadata": {},
            "feature_catalog": {"by_category": {}, "by_level": {}, "by_layer": {}},
            "statistics": {"summary": {}, "per_feature": []},
            "sample_data": {"columns": [], "rows": []},
            "quality_alerts": [],
            "correlation_hotspots": [{"feature_a": "a", "feature_b": "b", "correlation": 0.9}],
        }

    monkeypatch.setattr(feature_factory_service, "export_json_report", fake_export_json_report)

    response = await async_client.get("/api/v1/features/export/task-1/json")

    assert response.status_code == 200
    hotspots = response.json()["correlation_hotspots"]
    assert hotspots[0]["feature_a"] == "a"


# ==================== Markdown 匯出（4） ====================


@pytest.mark.asyncio
async def test_export_markdown_token_budget(async_client, monkeypatch):
    """Markdown 匯出：token 預算參數轉發正確。"""

    def fake_export_markdown_report(task_id, max_token_budget, sections, language):
        assert max_token_budget == 2048
        return "# Report\n\n內容"

    monkeypatch.setattr(feature_factory_service, "export_markdown_report", fake_export_markdown_report)

    response = await async_client.get(
        "/api/v1/features/export/task-1/markdown",
        params={"max_token_budget": 2048},
    )

    assert response.status_code == 200
    assert "# Report" in response.text


@pytest.mark.asyncio
async def test_export_markdown_sections_filter(async_client, monkeypatch):
    """Markdown 匯出：sections 篩選參數轉發正確。"""

    def fake_export_markdown_report(task_id, max_token_budget, sections, language):
        assert sections == ["header", "quality"]
        return "# Report"

    monkeypatch.setattr(feature_factory_service, "export_markdown_report", fake_export_markdown_report)

    response = await async_client.get(
        "/api/v1/features/export/task-1/markdown",
        params={"sections": "header,quality"},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_export_markdown_language_switch(async_client, monkeypatch):
    """Markdown 匯出：語言參數轉發正確。"""

    def fake_export_markdown_report(task_id, max_token_budget, sections, language):
        assert language == "en"
        return "# Feature Factory Report"

    monkeypatch.setattr(feature_factory_service, "export_markdown_report", fake_export_markdown_report)

    response = await async_client.get(
        "/api/v1/features/export/task-1/markdown",
        params={"language": "en"},
    )

    assert response.status_code == 200
    assert "Feature Factory Report" in response.text


@pytest.mark.asyncio
async def test_export_markdown_xss_protection(async_client, monkeypatch):
    """Markdown 匯出：HTML entity 已轉義。"""

    service = FeatureExportService()
    df = pd.DataFrame({"ms_test": [1.0, 2.0, 3.0]})
    markdown = service.build_markdown_report(
        task_id="task-1",
        features_df=df,
        export_meta={
            "symbol": "<script>alert(1)</script>",
            "timeframe": "12h",
            "generated_at": "2026-02-17T00:00:00",
            "generation_time": 1.0,
            "metadata": {},
        },
        max_token_budget=4000,
        sections=["header"],
        language="zh-TW",
    )

    assert "<script>" not in markdown
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in markdown


# ==================== Browse API（8） ====================


@pytest.mark.asyncio
async def test_browse_features_pagination(async_client, monkeypatch):
    """Browse：分頁回傳。"""

    def fake_browse_features(**kwargs):
        return {
            "total": 2,
            "offset": kwargs["offset"],
            "limit": kwargs["limit"],
            "filters_applied": {},
            "features": [{"name": "a"}, {"name": "b"}],
        }

    monkeypatch.setattr(feature_factory_service, "browse_features", fake_browse_features)

    response = await async_client.get("/api/v1/features/browse/task-1/features", params={"offset": 0, "limit": 2})

    assert response.status_code == 200
    assert response.json()["limit"] == 2


@pytest.mark.asyncio
async def test_browse_features_sorting(async_client, monkeypatch):
    """Browse：排序參數轉發。"""

    def fake_browse_features(**kwargs):
        assert kwargs["sort_by"] == "std"
        assert kwargs["sort_order"] == "desc"
        return {"total": 0, "offset": 0, "limit": 50, "filters_applied": {}, "features": []}

    monkeypatch.setattr(feature_factory_service, "browse_features", fake_browse_features)

    response = await async_client.get(
        "/api/v1/features/browse/task-1/features",
        params={"sort_by": "std", "sort_order": "desc"},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_browse_features_filtering(async_client, monkeypatch):
    """Browse：category / level / search 篩選參數轉發。"""

    def fake_browse_features(**kwargs):
        assert kwargs["category"] == "microstructure"
        assert kwargs["level"] == "L3"
        assert kwargs["search"] == "ms_"
        return {"total": 0, "offset": 0, "limit": 50, "filters_applied": kwargs, "features": []}

    monkeypatch.setattr(feature_factory_service, "browse_features", fake_browse_features)

    response = await async_client.get(
        "/api/v1/features/browse/task-1/features",
        params={"category": "microstructure", "level": "L3", "search": "ms_"},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_browse_correlation_success(async_client, monkeypatch):
    """Browse correlation：成功回傳矩陣。"""

    def fake_browse_correlation(task_id, features, method):
        assert method == "pearson"
        return {"features": features, "method": method, "matrix": [[1.0]]}

    monkeypatch.setattr(feature_factory_service, "browse_correlation", fake_browse_correlation)

    response = await async_client.get(
        "/api/v1/features/browse/task-1/correlation",
        params={"features": "ms_a", "method": "pearson"},
    )

    assert response.status_code == 200
    assert response.json()["method"] == "pearson"


@pytest.mark.asyncio
async def test_browse_distribution_success(async_client, monkeypatch):
    """Browse distribution：成功回傳 histogram。"""

    def fake_browse_distribution(task_id, feature, n_bins, **kwargs):
        assert feature == "ent_a"
        return {"feature": feature, "n_bins": n_bins, "bins": [1, 2], "edges": [0.0, 1.0, 2.0], "stats": {}}

    monkeypatch.setattr(feature_factory_service, "browse_distribution", fake_browse_distribution)

    response = await async_client.get(
        "/api/v1/features/browse/task-1/distribution",
        params={"feature": "ent_a", "n_bins": 20},
    )

    assert response.status_code == 200
    assert response.json()["n_bins"] == 20


@pytest.mark.asyncio
async def test_browse_nan_pattern_success(async_client, monkeypatch):
    """Browse NaN pattern：成功回傳矩陣。"""

    def fake_browse_nan_pattern(task_id, sample_features):
        return {"features": ["a"], "timestamps": ["t1"], "matrix": [[True]], "nan_ratios": [0.1]}

    monkeypatch.setattr(feature_factory_service, "browse_nan_pattern", fake_browse_nan_pattern)

    response = await async_client.get(
        "/api/v1/features/browse/task-1/nan-pattern",
        params={"sample_features": 10},
    )

    assert response.status_code == 200
    assert response.json()["features"] == ["a"]


@pytest.mark.asyncio
async def test_browse_summary_success(async_client, monkeypatch):
    """Browse summary：成功回傳 Dashboard 摘要。"""

    def fake_browse_summary(task_id):
        return {
            "total_features": 100,
            "total_rows": 500,
            "by_category": {"microstructure": 25},
            "by_level": {"L1": 70, "L2": 20, "L3": 10},
            "by_layer": {"layer1": 80},
            "quality": {"nan_ratio_mean": 0.01},
            "generation_info": {"task_id": task_id},
        }

    monkeypatch.setattr(feature_factory_service, "browse_summary", fake_browse_summary)

    response = await async_client.get("/api/v1/features/browse/task-1/summary")

    assert response.status_code == 200
    assert response.json()["total_features"] == 100


@pytest.mark.asyncio
async def test_browse_invalid_task_returns_404(async_client, monkeypatch):
    """Browse：不存在 task_id 回傳 404（邊界路徑）。"""

    def fake_browse_features(**kwargs):
        raise FileNotFoundError("Result not found")

    monkeypatch.setattr(feature_factory_service, "browse_features", fake_browse_features)

    response = await async_client.get("/api/v1/features/browse/missing/features")

    assert response.status_code == 404
