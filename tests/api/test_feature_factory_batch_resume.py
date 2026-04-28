"""Task 0.6: Feature Factory batch resume and RAM gate tests."""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.main import app
from api.models.feature_factory_models import BatchGenerateRequest
from api.routes.feature_factory import get_batch_service
from api.services.feature_factory_batch_service import FeatureFactoryBatchService


class _VirtualMemory:
    def __init__(self, available: int) -> None:
        self.available = available


@pytest.fixture(autouse=True)
def reset_heavy_batch_slot(monkeypatch) -> None:
    """Keep the process-wide batch lock isolated across tests."""

    FeatureFactoryBatchService._heavy_batch_reserved = False
    if FeatureFactoryBatchService._heavy_batch_lock.locked():
        FeatureFactoryBatchService._heavy_batch_lock.release()
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.psutil.virtual_memory",
        lambda: _VirtualMemory(available=8 * 1024 ** 3),
    )


async def _wait_until_done(
    service: FeatureFactoryBatchService,
    task_id: str,
    timeout_sec: float = 5.0,
) -> Dict:
    started = time.time()
    while True:
        status = service.get_status(task_id)
        if status and status["status"] in {"completed", "partial", "failed", "paused_ram_gate"}:
            return status
        if time.time() - started > timeout_sec:
            raise TimeoutError(f"Task did not finish in {timeout_sec}s: {task_id}")
        await asyncio.sleep(0.02)


def _compute_success(
    symbol: str,
    timeframe: str,
    _config_override,
    _force_regenerate: bool,
    _cache_dir: Optional[str] = None,
) -> str:
    return f"/tmp/{symbol}_{timeframe}.h5"


@pytest.mark.asyncio
async def test_batch_resume_skips_completed_items(monkeypatch, tmp_path):
    calls: List[str] = []

    def _compute_tracking(
        symbol: str,
        timeframe: str,
        _config_override,
        _force_regenerate: bool,
        _cache_dir: Optional[str] = None,
    ) -> str:
        calls.append(symbol)
        return f"/tmp/{symbol}_{timeframe}.h5"

    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ThreadPoolExecutor,
    )
    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(_compute_tracking))

    service = FeatureFactoryBatchService(checkpoint_dir=tmp_path)
    request = BatchGenerateRequest(symbols=["BTCUSDT", "ETHUSDT"], timeframe="12h")
    checkpoint = service._build_initial_checkpoint("batch-resume", request)
    checkpoint["completed_items"] = [{
        "symbol": "BTCUSDT",
        "timeframe": "12h",
        "output_paths": ["/tmp/BTCUSDT_12h.h5"],
        "rss_peak_item_mb": 100,
        "rss_after_gc_mb": 80,
    }]
    checkpoint["queued_items"] = [{"symbol": "ETHUSDT", "timeframe": "12h"}]
    service._safe_persist_checkpoint(checkpoint)

    response = await service.resume_batch("batch-resume")
    assert response["batch_id"] == "batch-resume"
    assert response["skipped_items"] == 1
    assert response["queued_items"] == 1
    assert response["status"] == "running"

    status = await _wait_until_done(service, "batch-resume")
    assert status["status"] == "completed"
    assert status["completed"] == 2
    assert status["failed"] == 0
    assert calls == ["ETHUSDT"]
    assert status["results"]["BTCUSDT"] == "/tmp/BTCUSDT_12h.h5"
    assert status["results"]["ETHUSDT"] == "/tmp/ETHUSDT_12h.h5"


@pytest.mark.asyncio
async def test_ram_gate(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.psutil.virtual_memory",
        lambda: _VirtualMemory(available=1024 ** 3),
    )

    service = FeatureFactoryBatchService(checkpoint_dir=tmp_path)
    request = BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="12h")

    with pytest.raises(HTTPException) as exc_info:
        await service.start_batch(request)

    assert exc_info.value.status_code == 429
    assert "RAM gate" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_checkpoint_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ThreadPoolExecutor,
    )
    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(_compute_success))

    service = FeatureFactoryBatchService(checkpoint_dir=tmp_path)

    def _raise_os_error(_checkpoint: Dict) -> None:
        raise OSError("simulated checkpoint failure")

    monkeypatch.setattr(service, "_write_checkpoint_atomic", _raise_os_error)
    request = BatchGenerateRequest(symbols=["BTCUSDT", "ETHUSDT"], timeframe="12h")

    task_id = await service.start_batch(request)
    status = await _wait_until_done(service, task_id)

    assert status["status"] == "completed"
    assert status["completed"] == 2
    assert status["failed"] == 0


class _ResumeNotFoundServiceStub:
    async def resume_batch(self, batch_id: str) -> Dict:
        raise FileNotFoundError(batch_id)


def test_resume_not_found():
    app.dependency_overrides[get_batch_service] = lambda: _ResumeNotFoundServiceStub()

    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/features/batch/missing-batch/resume")
        assert response.status_code == 404
        assert response.json()["detail"] == "batch not found"
    finally:
        app.dependency_overrides.pop(get_batch_service, None)
