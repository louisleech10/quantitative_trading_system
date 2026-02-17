"""Feature Factory browse API tests (Phase 3.3.1)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.feature_factory import router as feature_factory_router
from api.services.feature_factory_service import feature_factory_service


app = FastAPI()
app.include_router(feature_factory_router)
client = TestClient(app)


def test_browse_features_success(monkeypatch):
    """/browse/features：分頁+篩選成功。"""

    def fake_browse_features(**kwargs):
        assert kwargs["task_id"] == "task-1"
        assert kwargs["offset"] == 0
        assert kwargs["limit"] == 50
        assert kwargs["category"] == "microstructure"
        assert kwargs["level"] == "L3"
        return {
            "total": 1,
            "offset": 0,
            "limit": 50,
            "filters_applied": {"category": "microstructure", "level": "L3", "search": None},
            "features": [
                {
                    "name": "ms_amihud_illiq_21",
                    "category": "microstructure",
                    "level": "L3",
                    "layer": "layer1",
                    "nan_ratio": 0.01,
                    "mean": 0.1,
                    "std": 0.2,
                    "min": 0.0,
                    "q25": 0.05,
                    "median": 0.1,
                    "q75": 0.12,
                    "max": 0.3,
                    "skewness": 1.2,
                    "kurtosis": 5.1,
                    "is_stationary": True,
                    "adf_pvalue": 0.01,
                }
            ],
        }

    monkeypatch.setattr(feature_factory_service, "browse_features", fake_browse_features)

    response = client.get(
        "/api/v1/features/browse/task-1/features",
        params={"category": "microstructure", "level": "L3"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["features"][0]["name"] == "ms_amihud_illiq_21"


def test_browse_features_invalid_sort_by(monkeypatch):
    """/browse/features：非法排序欄位回傳 400。"""

    def fake_browse_features(**kwargs):
        raise ValueError("Invalid sort_by: bad")

    monkeypatch.setattr(feature_factory_service, "browse_features", fake_browse_features)

    response = client.get(
        "/api/v1/features/browse/task-1/features",
        params={"sort_by": "bad"},
    )

    assert response.status_code == 400


def test_browse_data_feature_limit(monkeypatch):
    """/browse/data：超過 20 個特徵時回傳 400。"""

    def fake_browse_feature_data(**kwargs):
        raise ValueError("features count exceeds limit 20")

    monkeypatch.setattr(feature_factory_service, "browse_feature_data", fake_browse_feature_data)

    features = ",".join([f"f{i}" for i in range(21)])
    response = client.get(
        "/api/v1/features/browse/task-1/data",
        params={"features": features},
    )

    assert response.status_code == 400


def test_browse_correlation_success(monkeypatch):
    """/browse/correlation：回傳 NxN 矩陣。"""

    def fake_browse_correlation(**kwargs):
        assert kwargs["method"] == "pearson"
        return {
            "features": ["a", "b"],
            "method": "pearson",
            "matrix": [[1.0, 0.2], [0.2, 1.0]],
        }

    monkeypatch.setattr(feature_factory_service, "browse_correlation", fake_browse_correlation)

    response = client.get(
        "/api/v1/features/browse/task-1/correlation",
        params={"features": "a,b", "method": "pearson"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["features"] == ["a", "b"]
    assert len(payload["matrix"]) == 2


def test_browse_correlation_feature_limit(monkeypatch):
    """/browse/correlation：超過 50 個特徵時回傳 400。"""

    def fake_browse_correlation(**kwargs):
        raise ValueError("features count exceeds limit 50")

    monkeypatch.setattr(feature_factory_service, "browse_correlation", fake_browse_correlation)

    features = ",".join([f"f{i}" for i in range(51)])
    response = client.get(
        "/api/v1/features/browse/task-1/correlation",
        params={"features": features},
    )

    assert response.status_code == 400


def test_browse_distribution_success(monkeypatch):
    """/browse/distribution：回傳 bins + edges。"""

    def fake_browse_distribution(**kwargs):
        return {
            "feature": kwargs["feature"],
            "n_bins": kwargs["n_bins"],
            "bins": [1, 2, 3],
            "edges": [0.0, 1.0, 2.0, 3.0],
            "stats": {"mean": 1.0},
        }

    monkeypatch.setattr(feature_factory_service, "browse_distribution", fake_browse_distribution)

    response = client.get(
        "/api/v1/features/browse/task-1/distribution",
        params={"feature": "ms_amihud_illiq_21", "n_bins": 50},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["feature"] == "ms_amihud_illiq_21"
    assert payload["n_bins"] == 50


def test_browse_nan_pattern_success(monkeypatch):
    """/browse/nan-pattern：回傳矩陣資料。"""

    def fake_browse_nan_pattern(**kwargs):
        return {
            "features": ["f1", "f2"],
            "timestamps": ["2026-01-01T00:00:00"],
            "matrix": [[False, True]],
            "nan_ratios": [0.0, 1.0],
        }

    monkeypatch.setattr(feature_factory_service, "browse_nan_pattern", fake_browse_nan_pattern)

    response = client.get("/api/v1/features/browse/task-1/nan-pattern")

    assert response.status_code == 200
    payload = response.json()
    assert payload["features"] == ["f1", "f2"]


def test_browse_summary_success(monkeypatch):
    """/browse/summary：回傳 dashboard summary。"""

    def fake_browse_summary(**kwargs):
        return {
            "total_features": 100,
            "total_rows": 200,
            "by_category": {"microstructure": 25},
            "by_level": {"L3": 40},
            "by_layer": {"layer1": 80},
            "quality": {
                "nan_ratio_mean": 0.02,
                "nan_ratio_max": 0.2,
                "nan_ratio_distribution": [0.5, 0.5],
                "constant_features": ["f1"],
                "high_corr_pairs_count": 10,
                "stationary_ratio": 0.8,
            },
            "generation_info": {
                "task_id": "task-1",
                "symbol": "BTCUSDT",
                "timeframe": "12h",
                "generated_at": "2026-02-17T12:00:00",
                "generation_time": 10.0,
                "config_hash": "abc",
            },
        }

    monkeypatch.setattr(feature_factory_service, "browse_summary", fake_browse_summary)

    response = client.get("/api/v1/features/browse/task-1/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_features"] == 100
    assert payload["generation_info"]["task_id"] == "task-1"
