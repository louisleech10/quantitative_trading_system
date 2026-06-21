"""Task 0.6: Feature Factory batch resume and RAM gate tests."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import api.services.feature_factory_batch_service as batch_service_module
import api.services.feature_factory_service as feature_service_module
from api.models.feature_factory_models import BatchGenerateRequest
from api.routes.feature_factory import get_batch_service
from api.services.feature_factory_batch_service import (
    FeatureFactoryBatchService,
    RAM_GATE_BASE_PER_SYMBOL_GB,
    RAM_GATE_SEQUENTIAL_GB,
)
from api.services.feature_factory_batch_adapters import FeatureFactoryQualityAdapter
from api.services.feature_factory_service import FeatureFactoryService


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
    _batch_id: str = "",
    _start_date: Optional[str] = None,
    _end_date: Optional[str] = None,
) -> str:
    return f"/tmp/{symbol}_{timeframe}.h5"


def _read_child_metrics(path) -> List[Dict]:
    rows = []
    with path.open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            rows.append(json.loads(line))
    return rows


def test_resolve_ram_gate_min_gb_scales_with_concurrency(monkeypatch, tmp_path, batch_service_factory):
    service = batch_service_factory(tmp_path)
    monkeypatch.delenv("FFACT_RAM_GATE_MIN_GB", raising=False)

    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.get_current_tier_gb",
        lambda: 8.0,
    )
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.get_tier_concurrent_symbols",
        lambda _tier_gb: 1,
    )
    assert service._resolve_ram_gate_min_gb() == RAM_GATE_SEQUENTIAL_GB

    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.get_tier_concurrent_symbols",
        lambda _tier_gb: 2,
    )
    assert service._resolve_ram_gate_min_gb() == 4.0

    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.get_tier_concurrent_symbols",
        lambda _tier_gb: 3,
    )
    assert service._resolve_ram_gate_min_gb() == 6.0


def test_resolve_ram_gate_min_gb_env_override(monkeypatch, tmp_path, batch_service_factory):
    service = batch_service_factory(tmp_path)
    monkeypatch.setenv("FFACT_RAM_GATE_MIN_GB", "1.2")
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.get_current_tier_gb",
        lambda: 32.0,
    )
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.get_tier_concurrent_symbols",
        lambda _tier_gb: 3,
    )

    assert service._resolve_ram_gate_min_gb() == 1.2


def test_resolve_ram_gate_min_gb_invalid_env_falls_back(monkeypatch, tmp_path, batch_service_factory):
    service = batch_service_factory(tmp_path)
    monkeypatch.setenv("FFACT_RAM_GATE_MIN_GB", "abc")
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.get_current_tier_gb",
        lambda: 8.0,
    )
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.get_tier_concurrent_symbols",
        lambda _tier_gb: 1,
    )

    assert service._resolve_ram_gate_min_gb() == RAM_GATE_SEQUENTIAL_GB


def test_resolve_ram_gate_min_gb_zero_env_is_valid(monkeypatch, tmp_path, batch_service_factory):
    service = batch_service_factory(tmp_path)
    monkeypatch.setenv("FFACT_RAM_GATE_MIN_GB", "0")
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.get_tier_concurrent_symbols",
        lambda _tier_gb: 3,
    )

    assert service._resolve_ram_gate_min_gb() == 0.0


def test_ram_gate_uses_resolved_required_gb(monkeypatch, tmp_path, batch_service_factory):
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.psutil.virtual_memory",
        lambda: _VirtualMemory(available=1 * 1024 ** 3),
    )
    service = batch_service_factory(tmp_path)
    monkeypatch.setattr(service, "_resolve_ram_gate_min_gb", lambda: 2.0)

    with pytest.raises(HTTPException) as exc_info:
        service._ram_gate()

    assert exc_info.value.status_code == 429
    assert "RAM gate" in str(exc_info.value.detail)
    assert "required=2.00GB" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_batch_resume_skips_completed_items(monkeypatch, tmp_path, batch_service_factory):
    calls: List[str] = []

    def _compute_tracking(
        symbol: str,
        timeframe: str,
        _config_override,
        _force_regenerate: bool,
        _cache_dir: Optional[str] = None,
        _batch_id: str = "",
        _start_date: Optional[str] = None,
        _end_date: Optional[str] = None,
    ) -> str:
        calls.append(symbol)
        return f"/tmp/{symbol}_{timeframe}.h5"

    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ThreadPoolExecutor,
    )
    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(_compute_tracking))

    service = batch_service_factory(tmp_path)
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
async def test_current_symbol_updates_on_submit_before_item_completes(monkeypatch, tmp_path, batch_service_factory):
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ThreadPoolExecutor,
    )
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.get_tier_concurrent_symbols",
        lambda _tier_gb: 1,
    )

    second_started = threading.Event()
    release_second = threading.Event()
    notifications: List[Dict] = []

    def _compute_block_second(
        symbol: str,
        timeframe: str,
        _config_override,
        _force_regenerate: bool,
        _cache_dir: Optional[str] = None,
        _batch_id: str = "",
        _start_date: Optional[str] = None,
        _end_date: Optional[str] = None,
    ) -> str:
        if symbol == "ETHUSDT":
            second_started.set()
            release_second.wait(timeout=2)
        return f"/tmp/{symbol}_{timeframe}.h5"

    monkeypatch.setattr(
        FeatureFactoryBatchService,
        "_compute_single",
        staticmethod(_compute_block_second),
    )

    service = batch_service_factory(tmp_path)
    original_notify = service._notify_progress

    def _capture_notify(task_id: str) -> None:
        status = service.get_status(task_id)
        if status:
            notifications.append(status)
        original_notify(task_id)

    monkeypatch.setattr(service, "_notify_progress", _capture_notify)

    request = BatchGenerateRequest(symbols=["BTCUSDT", "ETHUSDT"], timeframe="12h")
    task_id = await service.start_batch(request)
    assert await asyncio.to_thread(second_started.wait, 2)

    status = service.get_status(task_id)
    assert status is not None
    assert status["current_symbol"] == "ETHUSDT"
    assert status["current_timeframe"] == "12h"
    assert any(item.get("current_symbol") == "ETHUSDT" for item in notifications)

    release_second.set()
    final_status = await _wait_until_done(service, task_id)
    assert final_status["status"] == "completed"


@pytest.mark.asyncio
async def test_child_metrics_jsonl_records_each_symbol(
    monkeypatch,
    tmp_path,
    batch_service_factory,
    mock_browse_registrar,
):
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ThreadPoolExecutor,
    )
    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(_compute_success))

    service = batch_service_factory(tmp_path)
    request = BatchGenerateRequest(symbols=["BTCUSDT", "ETHUSDT"], timeframe="12h")

    task_id = await service.start_batch(request)
    status = await _wait_until_done(service, task_id)

    assert status["status"] == "completed"
    assert status["results"] == {
        "BTCUSDT": "/tmp/BTCUSDT_12h.h5",
        "ETHUSDT": "/tmp/ETHUSDT_12h.h5",
    }
    assert status["browse_task_ids"] == {
        "BTCUSDT": "browse_BTCUSDT_12h",
        "ETHUSDT": "browse_ETHUSDT_12h",
    }
    checkpoint = service._load_checkpoint(task_id)
    assert checkpoint is not None
    completed = checkpoint["completed_items"]
    assert {item["browse_task_id"] for item in completed} == {
        "browse_BTCUSDT_12h",
        "browse_ETHUSDT_12h",
    }
    assert len(mock_browse_registrar.calls) == 2
    metrics_path = tmp_path / task_id / "child_metrics.jsonl"
    rows = _read_child_metrics(metrics_path)
    by_symbol = {row["symbol"]: row for row in rows}
    assert set(by_symbol) == {"BTCUSDT", "ETHUSDT"}
    for row in rows:
        assert row["timeframe"] == "12h"
        assert isinstance(row["pid"], int)
        assert isinstance(row["peak_rss_mb"], int)
        assert isinstance(row["duration_s"], (int, float))
        assert row["status"] in {"ok", "failed"}


@pytest.mark.asyncio
async def test_parent_records_failed_child_metrics_when_compute_raises(monkeypatch, tmp_path, batch_service_factory):
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ThreadPoolExecutor,
    )

    def _compute_fail(
        symbol: str,
        timeframe: str,
        _config_override,
        _force_regenerate: bool,
        _cache_dir: Optional[str] = None,
        _batch_id: str = "",
        _start_date: Optional[str] = None,
        _end_date: Optional[str] = None,
    ) -> str:
        raise RuntimeError(f"{symbol} failed")

    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(_compute_fail))

    service = batch_service_factory(tmp_path)
    request = BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="12h")

    task_id = await service.start_batch(request)
    status = await _wait_until_done(service, task_id)

    assert status["status"] == "failed"
    metrics_path = tmp_path / task_id / "child_metrics.jsonl"
    rows = _read_child_metrics(metrics_path)
    assert len(rows) == 1
    assert rows[0]["symbol"] == "BTCUSDT"
    assert rows[0]["timeframe"] == "12h"
    assert rows[0]["status"] == "failed"


@pytest.mark.asyncio
async def test_rss_soft_limit_downgrades_future_waves(
    monkeypatch,
    tmp_path,
    batch_service_factory,
):
    monkeypatch.setenv("FFACT_PARALLEL_BUDGET", "1")
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ThreadPoolExecutor,
    )
    monkeypatch.setattr(
        FeatureFactoryBatchService,
        "_compute_single",
        staticmethod(_compute_success),
    )
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.get_current_tier_gb",
        lambda: 16,
    )
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.get_tier_concurrent_symbols",
        lambda _tier_gb: 2,
    )

    rss_calls = {"count": 0}

    def _rss_mb() -> int:
        rss_calls["count"] += 1
        if rss_calls["count"] >= 4:
            return 12000
        return 100

    monkeypatch.setattr(FeatureFactoryBatchService, "_rss_mb", staticmethod(_rss_mb))

    service = batch_service_factory(tmp_path)
    request = BatchGenerateRequest(
        symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"],
        timeframe="12h",
    )
    task_id = await service.start_batch(request)
    status = await _wait_until_done(service, task_id)

    assert status["status"] == "completed"
    checkpoint = service._load_checkpoint(task_id)
    assert checkpoint is not None
    assert checkpoint.get("concurrent_symbols") == 1
    assert checkpoint.get("rss_soft_limit_exceeded") is True


@pytest.mark.asyncio
async def test_ram_gate(monkeypatch, tmp_path, batch_service_factory):
    # 0.5GB：明確低於最低 tier 的 gate（concurrent=1 → 1.0GB），確保各 tier 都觸發
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.psutil.virtual_memory",
        lambda: _VirtualMemory(available=1024 ** 3 // 2),
    )

    service = batch_service_factory(tmp_path)
    request = BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="12h")

    with pytest.raises(HTTPException) as exc_info:
        await service.start_batch(request)

    assert exc_info.value.status_code == 429
    assert "RAM gate" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_checkpoint_failure(monkeypatch, tmp_path, batch_service_factory):
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ThreadPoolExecutor,
    )
    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(_compute_success))

    service = batch_service_factory(tmp_path)

    def _raise_os_error(_checkpoint: Dict) -> None:
        raise OSError("simulated checkpoint failure")

    monkeypatch.setattr(service, "_write_checkpoint_atomic", _raise_os_error)
    request = BatchGenerateRequest(symbols=["BTCUSDT", "ETHUSDT"], timeframe="12h")

    task_id = await service.start_batch(request)
    status = await _wait_until_done(service, task_id)

    assert status["status"] == "completed"
    assert status["completed"] == 2
    assert status["failed"] == 0


def test_get_feature_factory_batch_service_requires_lifespan_injection(monkeypatch):
    monkeypatch.setattr(batch_service_module, "_feature_factory_batch_service", None)

    with pytest.raises(RuntimeError, match="not been initialized"):
        batch_service_module.get_feature_factory_batch_service()


def test_compute_symbol_quality_uses_injected_manifest_computer(
    tmp_path,
    batch_service_factory,
    mock_quality_computer,
):
    manifest_path = tmp_path / "feature_manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    service = batch_service_factory(tmp_path)

    result = service._compute_symbol_quality("BTCUSDT", str(manifest_path))

    assert result is not None
    assert result["symbol"] == "BTCUSDT"
    assert result["grade"] == "pass"
    assert mock_quality_computer.calls == [str(manifest_path)]


def test_restore_persisted_manifest_uses_full_hash_browse_id(monkeypatch, tmp_path):
    manifest_dir = tmp_path / "features" / "BTCUSDT" / "1h" / "abcdef1234567890"
    manifest_dir.mkdir(parents=True)
    manifest_path = manifest_dir / "feature_manifest.json"
    manifest_path.write_text(
        json.dumps({
            "symbol": "BTCUSDT",
            "primary_tf": "1h",
            "total_features": 3,
            "created_at": "2026-06-02T00:00:00",
            "groups": [],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(feature_service_module.settings, "data_cache_path", tmp_path)

    service = FeatureFactoryService()

    task = service.get_task_status("browse_BTCUSDT_1h_abcdef1234567890")
    assert task is not None
    assert task["status"] == "completed"
    assert service.get_task_status("browse_BTCUSDT_1h") is None
    result = service.get_result("browse_BTCUSDT_1h_abcdef1234567890")
    assert result is not None
    assert result["hdf5_path"] == str(manifest_path)


def test_quality_adapter_computes_from_real_parquet_manifest(monkeypatch, tmp_path):
    import numpy as np
    import pandas as pd

    monkeypatch.setattr(feature_service_module.settings, "data_cache_path", tmp_path)
    service = FeatureFactoryService()
    manifest_dir = tmp_path / "features" / "ETHUSDT" / "1h" / "cfg_adapter"
    manifest_dir.mkdir(parents=True)
    parquet_path = manifest_dir / "features.parquet"
    pd.DataFrame({
        "feature_a": np.arange(500, dtype=float),
        "feature_b": np.arange(500, dtype=float) + 1.0,
    }).to_parquet(parquet_path, index=False)
    manifest_path = manifest_dir / "feature_manifest.json"
    manifest_path.write_text(
        json.dumps({
            "symbol": "ETHUSDT",
            "primary_tf": "1h",
            "config_hash": "cfg_adapter",
            "total_features": 2,
            "groups": [{
                "group_id": "1h_L1_adapter",
                "parquet_path": str(parquet_path),
                "columns": ["feature_a", "feature_b"],
            }],
        }),
        encoding="utf-8",
    )

    result = FeatureFactoryQualityAdapter(service).compute(str(manifest_path))

    assert result["symbol"] == "ETHUSDT"
    assert result["bar_count"] == 500
    assert result["feature_count"] == 2
    assert result["constant_feature_count"] == 0
    assert result["grade"] == "pass"


class _ResumeNotFoundServiceStub:
    async def resume_batch(self, batch_id: str) -> Dict:
        raise FileNotFoundError(batch_id)


def test_resume_not_found():
    class _ProviderStub:
        pass

    class _RegistryStub:
        def register(self, _name: str, _provider: object) -> None:
            return None

    class _DownloadServiceStub:
        registry = _RegistryStub()

    monkeypatch_context = pytest.MonkeyPatch()
    monkeypatch_context.setattr(
        "momentum.factories.create_binance_provider",
        lambda: _ProviderStub(),
    )
    monkeypatch_context.setattr(
        "momentum.factories.create_kline_download_service",
        lambda storage_manager=None: _DownloadServiceStub(),
    )
    try:
        from api.main import app
    finally:
        monkeypatch_context.undo()

    app.dependency_overrides[get_batch_service] = lambda: _ResumeNotFoundServiceStub()

    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/features/batch/missing-batch/resume")
        assert response.status_code == 404
        assert response.json()["detail"] == "batch not found"
    finally:
        app.dependency_overrides.pop(get_batch_service, None)
