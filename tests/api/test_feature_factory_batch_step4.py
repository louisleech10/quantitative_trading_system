"""Step 4: Feature Factory 批次多標的計算測試（Service + API）。"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes.feature_factory import get_batch_service
from api.models.feature_factory_models import BatchGenerateRequest
from api.services.feature_factory_batch_service import FeatureFactoryBatchService


def _compute_success(
    symbol: str,
    timeframe: str,
    _config_override,
    _force_regenerate: bool,
    _cache_dir: Optional[str] = None,
) -> str:
    return f"/tmp/{symbol}_{timeframe}.h5"


def _compute_partial(
    symbol: str,
    timeframe: str,
    _config_override,
    _force_regenerate: bool,
    _cache_dir: Optional[str] = None,
) -> str:
    if symbol == "BAD":
        raise RuntimeError("simulated failure")
    return f"/tmp/{symbol}_{timeframe}.h5"


def _compute_fail(
    symbol: str,
    timeframe: str,
    _config_override,
    _force_regenerate: bool,
    _cache_dir: Optional[str] = None,
) -> str:
    raise RuntimeError(f"{symbol}-{timeframe}-failed")


async def _wait_until_done(service: FeatureFactoryBatchService, task_id: str, timeout_sec: float = 5.0) -> Dict:
    started = time.time()
    while True:
        status = service.get_status(task_id)
        if status and status["status"] in {"completed", "partial", "failed"}:
            return status
        if time.time() - started > timeout_sec:
            raise TimeoutError(f"Task did not finish in {timeout_sec}s: {task_id}")
        await asyncio.sleep(0.02)


@pytest.mark.asyncio
async def test_batch_service_completed(monkeypatch):
    monkeypatch.setattr("api.services.feature_factory_batch_service.ProcessPoolExecutor", ThreadPoolExecutor)
    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(_compute_success))

    service = FeatureFactoryBatchService()
    request = BatchGenerateRequest(symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"], timeframe="12h")

    task_id = await service.start_batch(request)
    status = await _wait_until_done(service, task_id)

    assert status["status"] == "completed"
    assert status["completed"] == 3
    assert status["failed"] == 0
    assert len(status["results"]) == 3


@pytest.mark.asyncio
async def test_batch_service_partial(monkeypatch):
    monkeypatch.setattr("api.services.feature_factory_batch_service.ProcessPoolExecutor", ThreadPoolExecutor)
    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(_compute_partial))

    service = FeatureFactoryBatchService()
    request = BatchGenerateRequest(symbols=["BTCUSDT", "BAD", "ETHUSDT"], timeframe="12h")

    task_id = await service.start_batch(request)
    status = await _wait_until_done(service, task_id)

    assert status["status"] == "partial"
    assert status["completed"] == 2
    assert status["failed"] == 1
    assert "BAD" in status["errors"]


@pytest.mark.asyncio
async def test_batch_service_all_failed(monkeypatch):
    monkeypatch.setattr("api.services.feature_factory_batch_service.ProcessPoolExecutor", ThreadPoolExecutor)
    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(_compute_fail))

    service = FeatureFactoryBatchService()
    request = BatchGenerateRequest(symbols=["BTCUSDT", "ETHUSDT"], timeframe="12h")

    task_id = await service.start_batch(request)
    status = await _wait_until_done(service, task_id)

    assert status["status"] == "failed"
    assert status["completed"] == 0
    assert status["failed"] == 2


@pytest.mark.asyncio
async def test_batch_service_concurrent_limit():
    service = FeatureFactoryBatchService()
    service._running_batch_count = service._max_concurrent_batches
    request = BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="12h")

    with pytest.raises(ValueError):
        await service.start_batch(request)


def test_batch_service_ttl_cleanup():
    service = FeatureFactoryBatchService()
    service._task_ttl_seconds = 1
    service._tasks["expired"] = {
        "task_id": "expired",
        "status": "completed",
        "total": 1,
        "completed": 1,
        "failed": 0,
        "current_symbol": "BTCUSDT",
        "results": {"BTCUSDT": "/tmp/BTCUSDT_12h.h5"},
        "errors": {},
        "created_at": time.time() - 10,
        "completed_at": time.time() - 5,
    }

    assert service.get_status("expired") is None


def test_batch_generate_request_deduplicate_and_validate():
    request = BatchGenerateRequest(
        symbols=["BTCUSDT", "ETHUSDT", "BTCUSDT"],
        timeframe="12h",
    )
    assert request.symbols == ["BTCUSDT", "ETHUSDT"]


def test_batch_generate_request_rejects_invalid_symbol():
    with pytest.raises(ValueError):
        BatchGenerateRequest(symbols=["BTC-USDT"], timeframe="12h")


def test_batch_generate_request_rejects_empty_symbols():
    with pytest.raises(ValueError):
        BatchGenerateRequest(symbols=[], timeframe="12h")


def test_batch_generate_request_rejects_invalid_timeframe():
    with pytest.raises(ValueError):
        BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="2h")


class _RouteBatchServiceStub:
    def __init__(self):
        self._status: Dict[str, Dict] = {}

    async def start_batch(self, request: BatchGenerateRequest) -> str:
        task_id = "task-123"
        self._status[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "total": len(request.symbols),
            "completed": 0,
            "failed": 0,
            "progress": 0.0,
            "results": {},
            "errors": {},
        }
        return task_id

    def get_status(self, task_id: str) -> Optional[Dict]:
        return self._status.get(task_id)


def test_batch_routes_start_and_status():
    stub = _RouteBatchServiceStub()
    app.dependency_overrides[get_batch_service] = lambda: stub

    with TestClient(app) as client:
        start_response = client.post(
            "/api/v1/features/batch",
            json={"symbols": ["BTCUSDT", "ETHUSDT"], "timeframe": "12h"},
        )
        assert start_response.status_code == 200
        assert start_response.json()["task_id"] == "task-123"

        status_response = client.get("/api/v1/features/batch/task-123")
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "pending"

        not_found_response = client.get("/api/v1/features/batch/not-exist")
        assert not_found_response.status_code == 404

    app.dependency_overrides.pop(get_batch_service, None)


def test_batch_route_rejects_invalid_timeframe_payload():
    stub = _RouteBatchServiceStub()
    app.dependency_overrides[get_batch_service] = lambda: stub

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/features/batch",
            json={"symbols": ["BTCUSDT"], "timeframe": "2h"},
        )
        assert response.status_code == 422

    app.dependency_overrides.pop(get_batch_service, None)
