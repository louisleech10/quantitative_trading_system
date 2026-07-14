"""Hardware API tests for Phase 5."""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.core.config import settings
from api.routes import config as config_route
from api.services import hardware_info_service
from momentum.FeatureEngineering.utils.hardware_utils import get_tier_config as real_tier_config


@pytest.fixture
def client() -> TestClient:
    """建立只掛載 config router 的測試 client。"""
    app = FastAPI()
    app.include_router(config_route.router, prefix="/api/v1")
    return TestClient(app)


class FakePsutil:
    """提供穩定硬體資料的測試替身。"""

    @staticmethod
    def virtual_memory() -> SimpleNamespace:
        return SimpleNamespace(total=16 * 1024 ** 3, available=6 * 1024 ** 3, percent=62.5)

    @staticmethod
    def cpu_count(logical: bool = True) -> int:
        return 8 if logical else 4

    @staticmethod
    def cpu_percent(interval: float = 0.1) -> float:
        assert interval == 0.1
        return 23.0


def _tier_config(tier: str, **overrides: object) -> dict:
    return {**real_tier_config(tier), **overrides}


def test_hardware_endpoint_returns_valid_json(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """測試硬體 endpoint 回傳正確 JSON 結構與建議設定。"""
    monkeypatch.setattr(hardware_info_service, "psutil", FakePsutil)
    monkeypatch.setattr(hardware_info_service, "get_memory_tier", lambda: "16gb")
    monkeypatch.setattr(
        hardware_info_service,
        "get_tier_config",
        lambda tier: _tier_config(
            tier,
            l65_workers=6,
            cgsa_memory_buffer=0,
            l7_workers=6,
            chunk_bars=100_000,
        ),
    )
    monkeypatch.setattr(settings, "data_cache_path", tmp_path)

    response = client.get("/api/v1/config/hardware")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {
        "memory_tier", "cpu", "memory", "disk", "recommended_settings",
        "applied_settings", "tier_table", "tier_thresholds_gb",
    }
    assert payload["memory_tier"] == "16gb"
    assert payload["cpu"] == {
        "logical_cores": 8,
        "physical_cores": 4,
        "usage_pct": 23.0,
    }
    assert payload["memory"] == {
        "total_gb": 16.0,
        "available_gb": 6.0,
        "used_pct": 62.5,
    }
    assert payload["disk"]["path"] == str(tmp_path.resolve())
    assert payload["recommended_settings"] == {
        "FFACT_L65_WORKERS": 6,
        "FFACT_CGSA_MEMORY_BUFFER": 0,
        "FFACT_L7_WORKERS": 6,
        "FFACT_L7_COMPACTOR_ENABLED": 1,
        "FFACT_MULTI_TF_MAX_WORKERS": 2,
        "FFACT_LAYER3_CHUNK_SIZE": 512,
    }
    assert payload["applied_settings"]["l65_workers"]["value"] == 6
    assert set(payload["tier_table"]) == {"8gb", "16gb", "24gb", "32gb"}


def test_hardware_endpoint_tier_matches_util(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """測試 endpoint 的 memory tier 與工具函式回傳一致。"""
    monkeypatch.setattr(hardware_info_service, "psutil", FakePsutil)
    monkeypatch.setattr(hardware_info_service, "get_memory_tier", lambda: "24gb")
    monkeypatch.setattr(
        hardware_info_service,
        "get_tier_config",
        lambda tier: _tier_config(
            tier,
            l65_workers=8,
            cgsa_memory_buffer=32,
            l7_workers=8,
            chunk_bars=250_000,
        ),
    )
    monkeypatch.setattr(settings, "data_cache_path", tmp_path)

    response = client.get("/api/v1/config/hardware")

    assert response.status_code == 200
    assert response.json()["memory_tier"] == "24gb"


def test_hardware_endpoint_missing_data_cache(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """測試 data_cache 缺失時 disk 資訊回傳 0 而非 crash。"""
    missing_path = tmp_path / "missing" / "data_cache"
    monkeypatch.setattr(hardware_info_service, "psutil", FakePsutil)
    monkeypatch.setattr(hardware_info_service, "get_memory_tier", lambda: "8gb")
    monkeypatch.setattr(
        hardware_info_service,
        "get_tier_config",
        lambda tier: _tier_config(
            tier,
            l65_workers=4,
            cgsa_memory_buffer=0,
            l7_workers=4,
            chunk_bars=50_000,
        ),
    )
    monkeypatch.setattr(settings, "data_cache_path", missing_path)

    response = client.get("/api/v1/config/hardware")

    assert response.status_code == 200
    disk = response.json()["disk"]
    assert disk == {
        "path": str(missing_path.resolve()),
        "free_gb": 0.0,
        "total_gb": 0.0,
        "used_pct": 0.0,
    }
