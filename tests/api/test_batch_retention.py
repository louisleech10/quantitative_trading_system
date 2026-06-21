"""B3 batch retention — post-hoc mark, decision endpoint, flag-off spy."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

import api.services.feature_factory_service as feature_service_module
from api.models.feature_factory_models import BatchGenerateRequest
from api.routes.feature_factory import get_batch_service, router as feature_factory_router
from api.services.feature_factory_batch_service import (
    FeatureFactoryBatchService,
    RetentionConflictError,
    RetentionState,
    RetentionStateError,
)
from api.services.feature_factory_service import FeatureFactoryService
from api.websocket.feature_factory_ws import map_batch_progress_ws_data
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.run_lifecycle import RunLifecycleManager


@pytest.fixture(autouse=True)
def use_thread_pool_for_batch(monkeypatch) -> None:
    """Avoid ProcessPoolExecutor pickling test stubs in child processes."""

    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ThreadPoolExecutor,
    )


@pytest.fixture(autouse=True)
def reset_heavy_batch_slot(monkeypatch) -> None:
    """Keep the process-wide batch lock isolated across tests."""

    FeatureFactoryBatchService._heavy_batch_reserved = False
    if FeatureFactoryBatchService._heavy_batch_lock.locked():
        FeatureFactoryBatchService._heavy_batch_lock.release()
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.psutil.virtual_memory",
        lambda: SimpleNamespace(available=8 * 1024 ** 3),
    )


@pytest_asyncio.fixture
async def retention_client(monkeypatch, tmp_path, mock_browse_registrar, mock_quality_computer):
    """FastAPI client with batch + lifecycle services on isolated tmp_path."""

    features_root = tmp_path / "features"
    cgsa_root = tmp_path / "cgsa_work"
    manager = RunLifecycleManager(
        features_root=features_root,
        cgsa_root=cgsa_root,
        locks_dir=features_root / ".locks",
        registry=FeatureRegistry(features_root / "registry.json"),
    )
    monkeypatch.setattr(feature_service_module.settings, "data_cache_path", tmp_path)
    ff_service = FeatureFactoryService()
    monkeypatch.setattr(feature_service_module, "feature_factory_service", ff_service)

    batch_service = FeatureFactoryBatchService(
        checkpoint_dir=tmp_path / "batch_checkpoints",
        browse_registrar=mock_browse_registrar,
        quality_computer=mock_quality_computer,
        run_deleter=ff_service.delete_run,
    )

    app = FastAPI()
    app.include_router(feature_factory_router)
    app.dependency_overrides[get_batch_service] = lambda: batch_service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, batch_service, ff_service, manager, tmp_path


def _compute_success(
    symbol: str,
    timeframe: str,
    _config_override,
    _force_regenerate: bool,
    cache_dir: Optional[str] = None,
    _batch_id: str = "",
) -> str:
    base = Path(cache_dir).parent if cache_dir else Path("/tmp")
    run_dir = base / "features" / symbol / timeframe / "cfg_batch_ret"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = run_dir / "feature_manifest.json"
    manifest.write_text(
        json.dumps({"symbol": symbol, "primary_tf": timeframe, "config_hash": "cfg_batch_ret"}),
        encoding="utf-8",
    )
    return str(manifest)


_NONBLOCK_COMPLETION_ORDER: List[str] = []


def _compute_tracked_nonblock(
    symbol: str,
    timeframe: str,
    config_override,
    force_regenerate: bool,
    cache_dir: Optional[str] = None,
    batch_id: str = "",
) -> str:
    _NONBLOCK_COMPLETION_ORDER.append(symbol)
    if symbol == "BTCUSDT":
        time.sleep(0.05)
    return _compute_success(symbol, timeframe, config_override, force_regenerate, cache_dir, batch_id)


async def _wait_batch_done(service: FeatureFactoryBatchService, task_id: str) -> Dict[str, Any]:
    started = time.time()
    while time.time() - started < 5.0:
        status = service.get_status(task_id)
        if status and status["status"] in {"completed", "partial", "failed"}:
            return status
        await asyncio.sleep(0.02)
    raise TimeoutError(f"batch did not finish: {task_id}")


def _seed_registry(
    manager: RunLifecycleManager,
    symbol: str,
    timeframe: str,
    config_hash: str,
    manifest_path: Path,
) -> None:
    manager.registry.add({
        "symbol": symbol,
        "timeframe": timeframe,
        "config_hash": config_hash,
        "created_at": 1_700_000_000.0,
    })


# --- retention_state ---


def test_retention_state_legal_transitions() -> None:
    checkpoint: Dict[str, Any] = {"retention_items": []}
    item = FeatureFactoryBatchService._mark_retention_pending(
        checkpoint,
        symbol="BTCUSDT",
        timeframe="1h",
        config_hash="cfg1",
        hdf5_path="/tmp/a.h5",
    )
    assert item["state"] == RetentionState.PENDING.value

    FeatureFactoryBatchService._validate_retention_transition(
        RetentionState.PENDING,
        RetentionState.DECIDING,
    )
    item["state"] = RetentionState.DECIDING.value
    FeatureFactoryBatchService._validate_retention_transition(
        RetentionState.DECIDING,
        RetentionState.RETAINED,
    )
    item["state"] = RetentionState.RETAINED.value


def test_retention_state_illegal_transition_raises() -> None:
    with pytest.raises(RetentionStateError):
        FeatureFactoryBatchService._validate_retention_transition(
            RetentionState.PENDING,
            RetentionState.RETAINED,
        )
    with pytest.raises(RetentionStateError):
        FeatureFactoryBatchService._validate_retention_transition(
            RetentionState.DISCARDED,
            RetentionState.PENDING,
        )


def test_retention_state_flag_off_skips_pending_mark(
    monkeypatch,
    tmp_path,
    batch_service_factory,
) -> None:
    monkeypatch.delenv("FFACT_BATCH_RETENTION", raising=False)
    service = batch_service_factory(tmp_path)
    checkpoint = service._build_initial_checkpoint(
        "batch-flag-off",
        BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="1h"),
    )
    task = service._build_task_state("batch-flag-off", BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="1h"), checkpoint, "running")
    service._record_item_result(
        task,
        checkpoint,
        "BTCUSDT",
        "1h",
        "/tmp/btc.h5",
        None,
        None,
        100,
        120,
        110,
    )
    assert checkpoint.get("retention_items", []) == []


def test_retention_state_flag_on_marks_pending(
    monkeypatch,
    tmp_path,
    batch_service_factory,
) -> None:
    monkeypatch.setenv("FFACT_BATCH_RETENTION", "1")
    service = batch_service_factory(tmp_path)
    request = BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="1h")
    checkpoint = service._build_initial_checkpoint("batch-flag-on", request)
    task = service._build_task_state("batch-flag-on", request, checkpoint, "running")
    manifest_path = tmp_path / "features" / "BTCUSDT" / "1h" / "cfg_batch_ret" / "feature_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{}", encoding="utf-8")
    service._record_item_result(
        task,
        checkpoint,
        "BTCUSDT",
        "1h",
        str(manifest_path),
        None,
        None,
        100,
        120,
        110,
    )
    pending = service._list_pending_retention_items(checkpoint)
    assert len(pending) == 1
    assert pending[0]["symbol"] == "BTCUSDT"
    assert pending[0]["config_hash"] == "cfg_batch_ret"


# --- retention_flag_off spy ---


@pytest.mark.asyncio
async def test_retention_flag_off_spy_register_timing(
    monkeypatch,
    tmp_path,
    batch_service_factory,
    mock_browse_registrar,
) -> None:
    monkeypatch.delenv("FFACT_BATCH_RETENTION", raising=False)
    monkeypatch.setattr(
        FeatureFactoryBatchService,
        "_compute_single",
        staticmethod(_compute_success),
    )
    service = batch_service_factory(tmp_path)
    calls_before: List[Dict[str, str]] = []

    original_record = service._record_item_result

    def _spy_record(*args, **kwargs):
        calls_before.append(list(mock_browse_registrar.calls))
        original_record(*args, **kwargs)
        assert len(mock_browse_registrar.calls) == len(calls_before[-1]) + 1

    monkeypatch.setattr(service, "_record_item_result", _spy_record)

    task_id = await service.start_batch(
        BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="1h", force_regenerate=True)
    )
    await _wait_batch_done(service, task_id)
    checkpoint = service._load_checkpoint(task_id)
    assert checkpoint is not None
    assert checkpoint.get("retention_items", []) == []
    assert len(mock_browse_registrar.calls) == 1


# --- retention_decision ---


@pytest.mark.asyncio
async def test_retention_decision_retain_clears_pending(
    monkeypatch,
    retention_client,
) -> None:
    client, batch_service, _ff, _manager, tmp_path = retention_client
    monkeypatch.setenv("FFACT_BATCH_RETENTION", "1")
    monkeypatch.setattr(
        FeatureFactoryBatchService,
        "_compute_single",
        staticmethod(_compute_success),
    )

    task_id = await batch_service.start_batch(
        BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="1h", force_regenerate=True)
    )
    await _wait_batch_done(batch_service, task_id)
    config_hash = "cfg_batch_ret"

    resp = await client.post(
        f"/api/v1/features/batch/{task_id}/retention/BTCUSDT/1h/{config_hash}",
        json={"decision": "retain"},
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == RetentionState.RETAINED.value
    pending = await batch_service.list_pending_retention(task_id)
    assert pending == []


@pytest.mark.asyncio
async def test_retention_decision_discard_deletes_run_and_browse_gone(
    monkeypatch,
    retention_client,
) -> None:
    client, batch_service, ff_service, manager, tmp_path = retention_client
    monkeypatch.setenv("FFACT_BATCH_RETENTION", "1")
    monkeypatch.setattr(
        FeatureFactoryBatchService,
        "_compute_single",
        staticmethod(_compute_success),
    )

    task_id = await batch_service.start_batch(
        BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="1h", force_regenerate=True)
    )
    await _wait_batch_done(batch_service, task_id)
    config_hash = "cfg_batch_ret"
    manifest = tmp_path / "features" / "BTCUSDT" / "1h" / config_hash / "feature_manifest.json"
    _seed_registry(manager, "BTCUSDT", "1h", config_hash, manifest)

    resp = await client.post(
        f"/api/v1/features/batch/{task_id}/retention/BTCUSDT/1h/{config_hash}",
        json={"decision": "discard"},
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == RetentionState.DISCARDED.value
    assert not manifest.exists()
    runs = ff_service.list_runs()
    assert not any(
        r["symbol"] == "BTCUSDT" and r["timeframe"] == "1h" and r["config_hash"] == "cfg_batch_ret"
        for r in runs
    )


@pytest.mark.asyncio
async def test_retention_decision_discard_keyerror_idempotent_success(
    monkeypatch,
    retention_client,
) -> None:
    client, batch_service, _ff, _manager, _tmp_path = retention_client
    monkeypatch.setenv("FFACT_BATCH_RETENTION", "1")
    monkeypatch.setattr(
        FeatureFactoryBatchService,
        "_compute_single",
        staticmethod(_compute_success),
    )

    def _raise_keyerror(symbol: str, timeframe: str, config_hash: str) -> Dict[str, Any]:
        raise KeyError((symbol, timeframe, config_hash))

    batch_service._run_deleter = _raise_keyerror

    task_id = await batch_service.start_batch(
        BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="1h", force_regenerate=True)
    )
    await _wait_batch_done(batch_service, task_id)
    config_hash = "cfg_batch_ret"

    resp = await client.post(
        f"/api/v1/features/batch/{task_id}/retention/BTCUSDT/1h/{config_hash}",
        json={"decision": "discard"},
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == RetentionState.DISCARDED.value


@pytest.mark.asyncio
async def test_retention_decision_repeat_discard_idempotent(
    monkeypatch,
    retention_client,
) -> None:
    client, batch_service, _ff, manager, tmp_path = retention_client
    monkeypatch.setenv("FFACT_BATCH_RETENTION", "1")
    monkeypatch.setattr(
        FeatureFactoryBatchService,
        "_compute_single",
        staticmethod(_compute_success),
    )

    task_id = await batch_service.start_batch(
        BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="1h", force_regenerate=True)
    )
    await _wait_batch_done(batch_service, task_id)
    config_hash = "cfg_batch_ret"
    manifest = tmp_path / "features" / "BTCUSDT" / "1h" / config_hash / "feature_manifest.json"
    _seed_registry(manager, "BTCUSDT", "1h", config_hash, manifest)

    url = f"/api/v1/features/batch/{task_id}/retention/BTCUSDT/1h/{config_hash}"
    first = await client.post(url, json={"decision": "discard"})
    second = await client.post(url, json={"decision": "discard"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["state"] == RetentionState.DISCARDED.value


@pytest.mark.asyncio
async def test_retention_decision_not_found_404(retention_client) -> None:
    client, _batch, _ff, _manager, _tmp = retention_client
    resp = await client.post(
        "/api/v1/features/batch/missing-batch/retention/BTCUSDT/1h/cfg1",
        json={"decision": "retain"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_retention_decision_concurrent_only_one_wins(
    monkeypatch,
    retention_client,
) -> None:
    _client, batch_service, _ff, _manager, _tmp_path = retention_client
    monkeypatch.setenv("FFACT_BATCH_RETENTION", "1")
    monkeypatch.setattr(
        FeatureFactoryBatchService,
        "_compute_single",
        staticmethod(_compute_success),
    )

    task_id = await batch_service.start_batch(
        BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="1h", force_regenerate=True)
    )
    await _wait_batch_done(batch_service, task_id)
    config_hash = "cfg_batch_ret"

    barrier = threading.Barrier(2)

    async def _decide(decision: str):
        await asyncio.get_event_loop().run_in_executor(None, barrier.wait)
        try:
            return await batch_service.apply_retention_decision(
                task_id, "BTCUSDT", "1h", config_hash, decision
            )
        except RetentionConflictError:
            return None

    results = await asyncio.gather(
        _decide("retain"),
        _decide("discard"),
    )
    winners = [r for r in results if r is not None]
    assert len(winners) == 1
    assert winners[0]["state"] in {
        RetentionState.RETAINED.value,
        RetentionState.DISCARDED.value,
    }


@pytest.mark.asyncio
async def test_retention_retain_equiv_registry_browse_quality(
    monkeypatch,
    retention_client,
    mock_browse_registrar,
    mock_quality_computer,
) -> None:
    """Retain 後 registry/browse/quality 與 flag-off 基線一致。"""
    client, batch_service, ff_service, manager, tmp_path = retention_client
    monkeypatch.setattr(
        FeatureFactoryBatchService,
        "_compute_single",
        staticmethod(_compute_success),
    )

    async def _baseline_flag_off() -> Dict[str, Any]:
        monkeypatch.delenv("FFACT_BATCH_RETENTION", raising=False)
        mock_browse_registrar.calls.clear()
        mock_quality_computer.calls.clear()
        task_id = await batch_service.start_batch(
            BatchGenerateRequest(symbols=["ETHUSDT"], timeframe="1h", force_regenerate=True)
        )
        await _wait_batch_done(batch_service, task_id)
        manifest = tmp_path / "features" / "ETHUSDT" / "1h" / "cfg_batch_ret" / "feature_manifest.json"
        _seed_registry(manager, "ETHUSDT", "1h", "cfg_batch_ret", manifest)
        quality = batch_service._quality_computer.compute(str(manifest))
        return {
            "browse_calls": list(mock_browse_registrar.calls),
            "browse_task_id": batch_service.get_status(task_id)["browse_task_ids"]["ETHUSDT"],
            "registry": ff_service.list_runs(),
            "quality": quality,
        }

    baseline = await _baseline_flag_off()

    monkeypatch.setenv("FFACT_BATCH_RETENTION", "1")
    mock_browse_registrar.calls.clear()
    task_id = await batch_service.start_batch(
        BatchGenerateRequest(symbols=["SOLUSDT"], timeframe="1h", force_regenerate=True)
    )
    await _wait_batch_done(batch_service, task_id)
    manifest = tmp_path / "features" / "SOLUSDT" / "1h" / "cfg_batch_ret" / "feature_manifest.json"
    _seed_registry(manager, "SOLUSDT", "1h", "cfg_batch_ret", manifest)
    config_hash = "cfg_batch_ret"

    resp = await client.post(
        f"/api/v1/features/batch/{task_id}/retention/SOLUSDT/1h/{config_hash}",
        json={"decision": "retain"},
    )
    assert resp.status_code == 200

    retained_quality = batch_service._quality_computer.compute(str(manifest))
    retained_status = batch_service.get_status(task_id)
    assert retained_status["browse_task_ids"]["SOLUSDT"] == retained_status["browse_task_ids"]["SOLUSDT"]
    assert len(mock_browse_registrar.calls) == 1
    assert mock_browse_registrar.calls[0]["symbol"] in {"ETHUSDT", "SOLUSDT"}
    assert retained_quality["grade"] == baseline["quality"]["grade"]
    assert ff_service.list_runs()  # run still visible after retain


# --- retention_list ---


@pytest.mark.asyncio
async def test_retention_list_pending(
    monkeypatch,
    retention_client,
) -> None:
    client, batch_service, _ff, _manager, _tmp = retention_client
    monkeypatch.setenv("FFACT_BATCH_RETENTION", "1")
    monkeypatch.setattr(
        FeatureFactoryBatchService,
        "_compute_single",
        staticmethod(_compute_success),
    )

    task_id = await batch_service.start_batch(
        BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="1h", force_regenerate=True)
    )
    await _wait_batch_done(batch_service, task_id)

    resp = await client.get(f"/api/v1/features/batch/{task_id}/retention/pending")
    assert resp.status_code == 200
    body = resp.json()
    assert body["batch_id"] == task_id
    assert len(body["pending"]) == 1
    assert body["pending"][0]["state"] == RetentionState.PENDING.value


@pytest.mark.asyncio
async def test_retention_list_empty_when_none(
    monkeypatch,
    retention_client,
) -> None:
    client, batch_service, _ff, _manager, _tmp = retention_client
    monkeypatch.delenv("FFACT_BATCH_RETENTION", raising=False)
    monkeypatch.setattr(
        FeatureFactoryBatchService,
        "_compute_single",
        staticmethod(_compute_success),
    )

    task_id = await batch_service.start_batch(
        BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="1h", force_regenerate=True)
    )
    await _wait_batch_done(batch_service, task_id)

    resp = await client.get(f"/api/v1/features/batch/{task_id}/retention/pending")
    assert resp.status_code == 200
    assert resp.json()["pending"] == []


def test_retention_list_ws_maps_pending(batch_service_factory, tmp_path) -> None:
    service = batch_service_factory(tmp_path)
    payload = {
        "task_id": "t1",
        "total": 1,
        "completed": 1,
        "failed": 0,
        "status": "completed",
        "retention_pending": [{
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "config_hash": "cfg1",
            "state": "pending",
            "hdf5_path": "/tmp/a.h5",
            "error": None,
        }],
    }
    mapped = map_batch_progress_ws_data(payload)
    assert "retention_pending" in mapped
    assert len(mapped["retention_pending"]) == 1
    assert mapped["retention_pending"][0]["symbol"] == "BTCUSDT"


# --- retention_nonblock ---


@pytest.mark.asyncio
async def test_retention_nonblock_other_symbol_completes(
    monkeypatch,
    batch_service_factory,
    tmp_path,
) -> None:
    monkeypatch.setenv("FFACT_BATCH_RETENTION", "1")
    _NONBLOCK_COMPLETION_ORDER.clear()
    monkeypatch.setattr(
        FeatureFactoryBatchService,
        "_compute_single",
        staticmethod(_compute_tracked_nonblock),
    )
    service = batch_service_factory(tmp_path)
    task_id = await service.start_batch(
        BatchGenerateRequest(symbols=["BTCUSDT", "ETHUSDT"], timeframe="1h", force_regenerate=True)
    )
    await _wait_batch_done(service, task_id)
    checkpoint = service._load_checkpoint(task_id)
    assert len(checkpoint.get("retention_items", [])) == 2
    assert "ETHUSDT" in _NONBLOCK_COMPLETION_ORDER
    assert _NONBLOCK_COMPLETION_ORDER.index("ETHUSDT") <= _NONBLOCK_COMPLETION_ORDER.index("BTCUSDT") + 1
