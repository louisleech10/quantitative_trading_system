from __future__ import annotations

import asyncio
import json
import re
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

import api.services.feature_factory_service as feature_service_module
from api.routes.feature_factory import router as feature_factory_router
from api.models.feature_factory_models import BatchGenerateRequest
from api.services.feature_factory_batch_service import FeatureFactoryBatchService
from api.services.feature_factory_service import FeatureFactoryService, feature_factory_service
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.run_lifecycle import RunLifecycleManager
from momentum.FeatureEngineering.run_locks import RunBusyError, is_run_active


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


def _manager(tmp_path: Path) -> RunLifecycleManager:
    features_root = tmp_path / "features"
    cgsa_root = tmp_path / "cgsa_work"
    return RunLifecycleManager(
        features_root=features_root,
        cgsa_root=cgsa_root,
        locks_dir=features_root / ".locks",
        registry=FeatureRegistry(features_root / "registry.json"),
    )


def _add_run(
    manager: RunLifecycleManager,
    config_hash: str,
    *,
    created_at: object = 1_700_000_000.0,
) -> Path:
    run_dir = manager.features_root / "BTCUSDT" / "12h" / config_hash
    run_dir.mkdir(parents=True)
    (run_dir / "feature_manifest.json").write_text("{}", encoding="utf-8")
    manager.registry.add({
        "symbol": "BTCUSDT",
        "timeframe": "12h",
        "config_hash": config_hash,
        "created_at": created_at,
    })
    return run_dir


def test_lease_sink_holds_until_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    factory = FeatureFactory.__new__(FeatureFactory)
    factory._storage = SimpleNamespace(base_path=tmp_path / "features")
    monkeypatch.setattr(factory, "_resolve_config", lambda _override: object())
    monkeypatch.setattr(factory, "_compute_config_hash", lambda *_args, **_kwargs: "cfg_batch2d")
    monkeypatch.setattr(factory, "_generate_features_impl", lambda *_args, **_kwargs: "result")
    sink: list = []
    assert factory.generate_features("BTCUSDT", "12h", lease_sink=sink) == "result"
    assert is_run_active(tmp_path / "features" / ".locks", "BTCUSDT", "12h", "cfg_batch2d")
    with pytest.raises(RunBusyError, match="busy"):
        factory.generate_features("BTCUSDT", "12h")
    sink.pop().release()
    assert not is_run_active(tmp_path / "features" / ".locks", "BTCUSDT", "12h", "cfg_batch2d")


def test_warmup_coordinator_holds_continuous_lease(tmp_path: Path) -> None:
    from momentum.FeatureEngineering.run_locks import RunLease

    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._lifecycle = lambda: SimpleNamespace(auto_cleanup=lambda *_args: None)
    lease = RunLease.acquire(tmp_path, "BTCUSDT", "12h", "cfg_batch2d")
    entered = threading.Barrier(2)
    finish = threading.Barrier(2)

    def warmup() -> threading.Thread:
        def worker() -> None:
            entered.wait()
            finish.wait()
        thread = threading.Thread(target=worker)
        thread.start()
        return thread

    coordinator = threading.Thread(
        target=service._run_warmups_then_release,
        args=(lease, [warmup], {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_batch2d"}),
    )
    coordinator.start()
    entered.wait()
    assert is_run_active(tmp_path, "BTCUSDT", "12h", "cfg_batch2d")
    finish.wait()
    coordinator.join()
    assert not is_run_active(tmp_path, "BTCUSDT", "12h", "cfg_batch2d")


@pytest.mark.asyncio
async def test_generate_warmup_delete_lease_chain(
    async_client: httpx.AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _manager(tmp_path)
    _add_run(manager, "cfg_batch2d")
    monkeypatch.setattr(feature_factory_service, "_lifecycle", lambda: manager)
    monkeypatch.setattr(feature_factory_service, "_tasks", {})
    monkeypatch.setattr(feature_factory_service, "_lock", threading.Lock())

    factory = FeatureFactory.__new__(FeatureFactory)
    factory._storage = SimpleNamespace(base_path=manager.features_root)
    monkeypatch.setattr(factory, "_resolve_config", lambda _override: object())
    monkeypatch.setattr(factory, "_compute_config_hash", lambda *_args, **_kwargs: "cfg_batch2d")
    monkeypatch.setattr(factory, "_generate_features_impl", lambda *_args, **_kwargs: "result")
    sink: list = []
    assert factory.generate_features("BTCUSDT", "12h", lease_sink=sink) == "result"
    with pytest.raises(RunBusyError, match="busy"):
        factory.generate_features("BTCUSDT", "12h")

    entered = threading.Barrier(2)
    finish = threading.Barrier(2)

    def warmup() -> threading.Thread:
        def worker() -> None:
            entered.wait()
            finish.wait()

        thread = threading.Thread(target=worker)
        thread.start()
        return thread

    coordinator = threading.Thread(
        target=feature_factory_service._run_warmups_then_release,
        args=(
            sink.pop(),
            [warmup],
            {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_batch2d"},
        ),
    )
    coordinator.start()
    entered.wait()
    assert is_run_active(manager.locks_dir, "BTCUSDT", "12h", "cfg_batch2d")
    busy = await async_client.delete("/api/v1/features/runs/BTCUSDT/12h/cfg_batch2d")
    assert busy.status_code == 409
    assert busy.json()["detail"]["code"] == "run_busy"
    assert is_run_active(manager.locks_dir, "BTCUSDT", "12h", "cfg_batch2d")

    finish.wait()
    coordinator.join()
    assert not is_run_active(manager.locks_dir, "BTCUSDT", "12h", "cfg_batch2d")
    deleted = await async_client.delete("/api/v1/features/runs/BTCUSDT/12h/cfg_batch2d")
    assert deleted.status_code == 200
    assert deleted.json()["features_deleted"] is True


def test_register_browse_id_uses_full_hash(tmp_path: Path) -> None:
    manifest = tmp_path / "features" / "BTCUSDT" / "12h" / "cfg_batch2d" / "feature_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"config_hash":"cfg_batch2d"}')
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._tasks = {}
    service._lock = threading.Lock()
    task_id = service.register_hdf5_for_browse("BTCUSDT", "12h", str(manifest))
    assert task_id == "browse_BTCUSDT_12h_cfg_batch2d"


def test_pass2_restores_two_full_hash_browse_tasks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    features_root = tmp_path / "features"
    for config_hash in ("cfg_batch2d", "cfg_batch2e"):
        manifest = features_root / "BTCUSDT" / "12h" / config_hash / "feature_manifest.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"quality_status": "complete"}), encoding="utf-8")
    monkeypatch.setattr(
        feature_service_module,
        "settings",
        SimpleNamespace(data_cache_path=tmp_path),
    )
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._tasks = {}
    service._lock = threading.Lock()
    service._restore_persisted_tasks()
    assert set(service._tasks) == {
        "browse_BTCUSDT_12h_cfg_batch2d",
        "browse_BTCUSDT_12h_cfg_batch2e",
    }


def test_task_status_completion_contract() -> None:
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._lock = threading.Lock()
    service._tasks = {"task": {"task_id": "task", "status": "completed", "progress": 1.0,
        "current_stage": None, "completed_stages": [], "error": None,
        "result": {"metadata": {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_batch2d"}}}}
    payload = service.get_task_status("task")
    assert payload is not None and payload["retention_prompt"] is True
    assert payload["run_identity"] == {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_batch2d"}


def test_resume_hash_resolver_three_branches(tmp_path: Path) -> None:
    run_dir = tmp_path / "features" / "BTCUSDT" / "12h" / "cfg_batch2d"
    run_dir.mkdir(parents=True)
    manifest = run_dir / "feature_manifest.json"
    manifest.write_text("{}")
    by_path = {"symbol": "BTCUSDT", "timeframe": "12h", "output_paths": [str(manifest)]}
    by_browse = {"symbol": "BTCUSDT", "timeframe": "12h", "output_paths": [],
                 "browse_task_id": "browse_BTCUSDT_12h_cfg_batch2d"}
    legacy = {"symbol": "BTCUSDT", "timeframe": "12h", "output_paths": ["BTCUSDT_12h_factory.h5"],
              "browse_task_id": "browse_BTCUSDT_12h"}
    assert FeatureFactoryBatchService._resolve_completed_run_hash(by_path) == "cfg_batch2d"
    assert FeatureFactoryBatchService._completed_manifest_exists(by_path, "cfg_batch2d")
    assert FeatureFactoryBatchService._resolve_completed_run_hash(by_browse) == "cfg_batch2d"
    assert FeatureFactoryBatchService._resolve_completed_run_hash(legacy) is None


@pytest.mark.asyncio
async def test_hdf5_completion_releases_then_auto_cleans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._lock = threading.Lock()
    service._tasks = {"task": {
        "task_id": "task", "status": "running", "progress": 0.0,
        "current_stage": None, "completed_stages": [], "error": None, "result": None,
    }}
    events: list[str] = []

    class Lease:
        def release(self) -> None:
            events.append("release")

    summary = {
        "hdf5_path": "/tmp/features.h5",
        "metadata": {
            "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_batch2d",
        },
    }
    manager = SimpleNamespace(
        auto_cleanup=lambda symbol, timeframe, keep_latest: events.append("cleanup")
    )
    monkeypatch.setattr(service, "_resolve_config_override", lambda value: value)
    monkeypatch.setattr(service, "_merge_fail_open_flags", lambda config, flags: config)
    monkeypatch.setattr(
        service,
        "_invoke_generation_with_lease_sink",
        lambda **kwargs: kwargs["lease_sink"].append(Lease()) or object(),
    )
    monkeypatch.setattr(service, "_summarize_result", lambda _result: summary)
    monkeypatch.setattr(service, "_persist_task_record", lambda *_args: None)
    monkeypatch.setattr(service, "_write_run_size", lambda *_args: None)
    monkeypatch.setattr(service, "_start_stats_cache_warmup", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service, "_notify_callbacks", lambda *_args: None)
    monkeypatch.setattr(service, "_lifecycle", lambda: manager)

    await service._run_task(
        "task",
        SimpleNamespace(
            symbol="BTCUSDT", timeframe="12h", config_override=None, fail_open=None,
            force_regenerate=False, start_date=None, end_date=None,
        ),
    )

    assert events == ["release", "cleanup"]


@pytest.mark.asyncio
async def test_runs_http_error_contracts(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(feature_factory_service, "delete_run", Mock(side_effect=RunBusyError("busy")))
    response = await async_client.delete("/api/v1/features/runs/BTCUSDT/12h/cfg_batch2d")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "run_busy"

    monkeypatch.setattr(feature_factory_service, "delete_run", Mock(side_effect=KeyError("missing")))
    response = await async_client.delete("/api/v1/features/runs/BTCUSDT/12h/missing")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "run_not_found"

    partial = {
        "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_batch2d",
        "features_deleted": False, "cgsa_deleted": False, "registry_removed": False,
        "skipped": [], "errors": ["features: denied"], "total_bytes": 0,
    }
    monkeypatch.setattr(feature_factory_service, "delete_run", Mock(return_value=partial))
    response = await async_client.delete("/api/v1/features/runs/BTCUSDT/12h/cfg_batch2d")
    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "delete_partial"
    assert response.json()["detail"]["errors"] == ["features: denied"]

    monkeypatch.setattr(feature_factory_service, "set_run_alias", Mock(side_effect=ValueError("used")))
    response = await async_client.patch(
        "/api/v1/features/runs/BTCUSDT/12h/cfg_batch2d/alias",
        json={"alias": "alpha"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "alias_conflict"


@pytest.mark.asyncio
async def test_list_runs_created_at_iso_samples(
    async_client: httpx.AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _manager(tmp_path)
    _add_run(manager, "cfg_batch2d", created_at=1_700_000_000.25)
    _add_run(manager, "cfg_batch2e", created_at="2026-06-13T12:34:56+00:00")
    monkeypatch.setattr(feature_factory_service, "_lifecycle", lambda: manager)
    response = await async_client.get("/api/v1/features/runs")
    assert response.status_code == 200
    rows = {row["config_hash"]: row for row in response.json()}
    iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\+00:00|Z)$")
    assert iso_pattern.fullmatch(rows["cfg_batch2d"]["created_at"])
    assert iso_pattern.fullmatch(rows["cfg_batch2e"]["created_at"])
    assert iso_pattern.fullmatch(rows["cfg_batch2d"]["last_generated_at"])
    assert iso_pattern.fullmatch(rows["cfg_batch2e"]["last_generated_at"])


@pytest.mark.asyncio
async def test_list_runs_includes_browse_metadata(
    async_client: httpx.AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _manager(tmp_path)
    _add_run(manager, "cfg_batch2d")
    monkeypatch.setattr(feature_factory_service, "_lifecycle", lambda: manager)
    monkeypatch.setattr(
        feature_service_module,
        "settings",
        SimpleNamespace(data_cache_path=tmp_path),
    )
    response = await async_client.get("/api/v1/features/runs")
    assert response.status_code == 200
    row = next(item for item in response.json() if item["config_hash"] == "cfg_batch2d")
    assert row["browse_task_id"] == "browse_BTCUSDT_12h_cfg_batch2d"
    assert row["browse_ready"] is True
    assert str(row["browse_path"]).endswith("feature_manifest.json")


@pytest.mark.asyncio
async def test_ensure_browse_task_for_run_idempotent(
    async_client: httpx.AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _manager(tmp_path)
    _add_run(manager, "cfg_batch2d")
    monkeypatch.setattr(feature_factory_service, "_lifecycle", lambda: manager)
    monkeypatch.setattr(
        feature_service_module,
        "settings",
        SimpleNamespace(data_cache_path=tmp_path),
    )
    monkeypatch.setattr(feature_factory_service, "_lock", threading.Lock())
    monkeypatch.setattr(feature_factory_service, "_tasks", {})

    url = "/api/v1/features/runs/BTCUSDT/12h/cfg_batch2d/browse"
    first = await async_client.post(url)
    assert first.status_code == 200
    payload = first.json()
    assert payload["browse_task_id"] == "browse_BTCUSDT_12h_cfg_batch2d"
    assert payload["browse_ready"] is True

    second = await async_client.post(url)
    assert second.status_code == 200
    assert second.json()["browse_task_id"] == payload["browse_task_id"]
    assert "browse_BTCUSDT_12h_cfg_batch2d" in feature_factory_service._tasks


@pytest.mark.asyncio
async def test_ensure_browse_task_not_ready_returns_404(
    async_client: httpx.AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _manager(tmp_path)
    manager.registry.add({
        "symbol": "BTCUSDT",
        "timeframe": "12h",
        "config_hash": "cfg_missing",
        "created_at": 1_700_000_000.0,
    })
    monkeypatch.setattr(feature_factory_service, "_lifecycle", lambda: manager)
    monkeypatch.setattr(
        feature_service_module,
        "settings",
        SimpleNamespace(data_cache_path=tmp_path),
    )
    response = await async_client.post("/api/v1/features/runs/BTCUSDT/12h/cfg_missing/browse")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "browse_not_ready"


@pytest.mark.asyncio
async def test_delete_idempotent_artifact_and_browse_reconciliation(
    async_client: httpx.AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _manager(tmp_path)
    run_dir = manager.features_root / "BTCUSDT" / "12h" / "cfg_batch2d"
    run_dir.mkdir(parents=True)
    (run_dir / "feature_manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(feature_factory_service, "_lifecycle", lambda: manager)
    monkeypatch.setattr(feature_factory_service, "_lock", threading.Lock())
    for cache_name in (
        "_df_cache", "_stats_cache", "_stats_name_sorted_cache", "_stats_name_keys_cache",
        "_adf_cache", "_feature_metadata_cache", "_cgsa_catalog_cache",
        "_cgsa_column_path_cache",
    ):
        monkeypatch.setattr(feature_factory_service, cache_name, {})
    for warming_name in (
        "_stats_warming_tasks", "_adf_warming_tasks", "_cgsa_stats_warming_tasks",
        "_cgsa_catalog_warming_tasks",
    ):
        monkeypatch.setattr(feature_factory_service, warming_name, set())
    monkeypatch.setattr(feature_factory_service, "_tasks", {
        "browse_BTCUSDT_12h_cfg_batch2d": {
            "task_id": "browse_BTCUSDT_12h_cfg_batch2d", "status": "completed",
            "created_at": "", "result": {"metadata": {}},
        },
        "generation-task": {
            "task_id": "generation-task", "status": "completed", "created_at": "",
            "result": {"metadata": {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_batch2d"}},
        },
    })

    before = await async_client.get("/api/v1/features/browse/available")
    assert len(before.json()["tasks"]) == 2
    deleted = await async_client.delete("/api/v1/features/runs/BTCUSDT/12h/cfg_batch2d")
    assert deleted.status_code == 200
    assert deleted.json()["features_deleted"] is True
    after = await async_client.get("/api/v1/features/browse/available")
    assert after.json()["tasks"] == []

    # SPEC [B2-6] 冪等語義：磁碟孤兒+registry 有→200；皆無（已完整刪除/從未存在）→404 run_not_found。
    missing = await async_client.delete("/api/v1/features/runs/BTCUSDT/12h/cfg_batch2d")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "run_not_found"


@pytest.mark.asyncio
@pytest.mark.parametrize("identity_source", ["output_path", "browse_task_id"])
async def test_resume_batch_requeues_missing_resolved_run(
    identity_source: str,
    tmp_path: Path,
    batch_service_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = batch_service_factory(tmp_path / "checkpoints")
    request = BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="12h")
    checkpoint = service._build_initial_checkpoint("batch-resume", request)
    missing_manifest = (
        tmp_path / "features" / "BTCUSDT" / "12h" / "cfg_batch2d" /
        "feature_manifest.json"
    )
    item = {
        "symbol": "BTCUSDT",
        "timeframe": "12h",
        "output_paths": [str(missing_manifest)] if identity_source == "output_path" else [],
        "browse_task_id": (
            "browse_BTCUSDT_12h_cfg_batch2d"
            if identity_source == "browse_task_id"
            else None
        ),
    }
    checkpoint["completed_items"] = [item]
    checkpoint["queued_items"] = []
    service._safe_persist_checkpoint(checkpoint)
    monkeypatch.setattr(service, "_ram_gate", lambda: None)
    called = threading.Event()

    async def execute_resume(resumed_checkpoint, lock_reserved=False) -> None:
        assert lock_reserved is True
        assert resumed_checkpoint["completed_items"] == []
        assert resumed_checkpoint["queued_items"] == [
            {"symbol": "BTCUSDT", "timeframe": "12h"}
        ]
        called.set()
        service._release_heavy_batch_slot()

    execute_mock = AsyncMock(side_effect=execute_resume)
    monkeypatch.setattr(service, "execute_resume", execute_mock)
    try:
        response = await service.resume_batch("batch-resume")
        assert response["queued_items"] == 1
        assert response["status"] == "running"
        assert await asyncio.to_thread(called.wait, 2)
        execute_mock.assert_called_once()
    finally:
        service._release_heavy_batch_slot()


@pytest.mark.asyncio
async def test_resume_batch_keeps_legacy_completed_item(
    tmp_path: Path,
    batch_service_factory,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = batch_service_factory(tmp_path / "checkpoints")
    request = BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="12h")
    checkpoint = service._build_initial_checkpoint("batch-legacy", request)
    checkpoint["completed_items"] = [{
        "symbol": "BTCUSDT",
        "timeframe": "12h",
        "output_paths": ["BTCUSDT_12h_factory.h5"],
        "browse_task_id": "browse_BTCUSDT_12h",
    }]
    checkpoint["queued_items"] = []
    service._safe_persist_checkpoint(checkpoint)
    execute_mock = AsyncMock()
    monkeypatch.setattr(service, "execute_resume", execute_mock)

    with caplog.at_level("WARNING", logger="api.feature_factory_batch_service"):
        response = await service.resume_batch("batch-legacy")

    assert response["status"] == "completed"
    assert response["skipped_items"] == 1
    execute_mock.assert_not_called()
    assert "Legacy completed item has no resolvable run hash" in caplog.text


@pytest.mark.asyncio
async def test_resume_batch_retains_completed_item_with_present_manifest(
    tmp_path: Path,
    batch_service_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """manifest-exists 分支整合測：碟上 manifest 存在 → 不 requeue、status completed。"""
    service = batch_service_factory(tmp_path / "checkpoints")
    request = BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="12h")
    checkpoint = service._build_initial_checkpoint("batch-present", request)
    run_dir = tmp_path / "features" / "BTCUSDT" / "12h" / "cfg_batch2d"
    run_dir.mkdir(parents=True)
    manifest = run_dir / "feature_manifest.json"
    manifest.write_text('{"ok": true}', encoding="utf-8")
    checkpoint["completed_items"] = [{
        "symbol": "BTCUSDT",
        "timeframe": "12h",
        "output_paths": [str(manifest)],
        "browse_task_id": "browse_BTCUSDT_12h_cfg_batch2d",
    }]
    checkpoint["queued_items"] = []
    service._safe_persist_checkpoint(checkpoint)
    execute_mock = AsyncMock()
    monkeypatch.setattr(service, "execute_resume", execute_mock)

    response = await service.resume_batch("batch-present")

    assert response["status"] == "completed"
    assert response["queued_items"] == 0
    assert response["skipped_items"] == 1
    execute_mock.assert_not_called()
