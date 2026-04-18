"""Feature export API tests for Phase 3.4.1."""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
import pandas as pd
from fastapi import FastAPI

from api.routes.feature_factory import router as feature_factory_router
from api.services.feature_export_service import FeatureExportService
from api.services.feature_factory_service import feature_factory_service


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

    def fake_browse_distribution(task_id, feature, n_bins):
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
