"""B4 bulk-delete + orphan cleanup — hermetic API tests."""

from __future__ import annotations

import asyncio
import json
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Set
from unittest.mock import Mock

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

import api.services.feature_factory_service as feature_service_module
from api.models.feature_factory_models import BatchGenerateRequest
from api.routes.feature_factory import get_batch_service, router as feature_factory_router
from api.services.feature_factory_batch_service import (
    FeatureFactoryBatchService,
    RetentionState,
)
from api.services.feature_factory_service import FeatureFactoryService
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.run_lifecycle import RunLifecycleManager
from momentum.FeatureEngineering.run_locks import RunBusyError, RunLease, is_run_active
from momentum.FeatureEngineering.run_paths import cgsa_work_dir, features_run_dir


PRODUCTION_DATA_CACHE = Path("data_cache")


def _snapshot_data_cache() -> Set[str]:
    """Record all files under data_cache for hermetic pollution checks."""
    if not PRODUCTION_DATA_CACHE.exists():
        return set()
    return {str(path) for path in PRODUCTION_DATA_CACHE.rglob("*") if path.is_file()}


def _manager(tmp_path: Path) -> RunLifecycleManager:
    features_root = tmp_path / "features"
    cgsa_root = tmp_path / "cgsa_work"
    return RunLifecycleManager(
        features_root=features_root,
        cgsa_root=cgsa_root,
        locks_dir=features_root / ".locks",
        registry=FeatureRegistry(features_root / "registry.json"),
    )


def _create_run(
    manager: RunLifecycleManager,
    config_hash: str,
    *,
    symbol: str = "BTCUSDT",
    timeframe: str = "12h",
    alias: str | None = None,
    batch_alias: str | None = None,
    batch_id: str | None = None,
    with_cgsa: bool = True,
) -> Path:
    feature_leaf = features_run_dir(manager.features_root, symbol, timeframe, config_hash)
    feature_leaf.mkdir(parents=True, exist_ok=True)
    (feature_leaf / "feature_manifest.json").write_text(
        json.dumps({"symbol": symbol, "timeframe": timeframe, "config_hash": config_hash}),
        encoding="utf-8",
    )
    if with_cgsa:
        cgsa_leaf = cgsa_work_dir(manager.cgsa_root, symbol, timeframe, config_hash)
        cgsa_leaf.mkdir(parents=True, exist_ok=True)
        (cgsa_leaf / "manifest.json").write_text(
            json.dumps({
                "symbol": symbol,
                "timeframe": timeframe,
                "config_hash": config_hash,
            }),
            encoding="utf-8",
        )
    entry: Dict[str, Any] = {
        "symbol": symbol,
        "timeframe": timeframe,
        "config_hash": config_hash,
        "created_at": 1_700_000_000.0,
    }
    if alias:
        entry["alias"] = alias
    if batch_alias:
        entry["batch_alias"] = batch_alias
    if batch_id:
        entry["batch_id"] = batch_id
    manager.registry.add(entry)
    return feature_leaf


@pytest.fixture(autouse=True)
def _thread_pool_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ThreadPoolExecutor,
    )


@pytest_asyncio.fixture
async def b4_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """FastAPI client with isolated tmp_path + batch service wired."""
    features_root = tmp_path / "features"
    cgsa_root = tmp_path / "cgsa_work"
    cgsa_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(feature_service_module.settings, "data_cache_path", tmp_path)

    manager = RunLifecycleManager(
        features_root=features_root,
        cgsa_root=cgsa_root,
        locks_dir=features_root / ".locks",
        registry=FeatureRegistry(features_root / "registry.json"),
    )
    ff_service = FeatureFactoryService()
    monkeypatch.setattr(ff_service, "_lifecycle", lambda: manager)
    monkeypatch.setattr(feature_service_module, "feature_factory_service", ff_service)
    monkeypatch.setattr("api.routes.feature_factory.feature_factory_service", ff_service)

    batch_service = FeatureFactoryBatchService(
        checkpoint_dir=tmp_path / "batch_checkpoints",
        browse_registrar=Mock(return_value="browse_mock"),
        quality_computer=Mock(),
        run_deleter=ff_service.delete_run,
    )

    app = FastAPI()
    app.include_router(feature_factory_router)
    app.dependency_overrides[get_batch_service] = lambda: batch_service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, ff_service, manager, batch_service, tmp_path


@pytest.mark.asyncio
async def test_bulk_delete_empty_noop(b4_client) -> None:
    client, *_ = b4_client
    resp = await client.post("/api/v1/features/runs/bulk-delete", json={"runs": []})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload == {"deleted": [], "failed": [], "skipped": []}


@pytest.mark.asyncio
async def test_bulk_delete_equiv_matches_sequential_delete_run(b4_client) -> None:
    """bulk 刪 N run == 逐個 delete_run（registry + artifact 同消失）。"""
    client, ff_service, manager, *_ = b4_client
    hashes = ["cfg_b4_a", "cfg_b4_b", "cfg_b4_c"]
    for config_hash in hashes:
        _create_run(manager, config_hash)

    bulk = await client.post(
        "/api/v1/features/runs/bulk-delete",
        json={
            "runs": [
                {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": h}
                for h in hashes
            ],
        },
    )
    assert bulk.status_code == 200
    body = bulk.json()
    assert len(body["deleted"]) == 3
    assert body["failed"] == []
    assert body["skipped"] == []
    assert ff_service.list_runs() == []
    for config_hash in hashes:
        leaf = features_run_dir(manager.features_root, "BTCUSDT", "12h", config_hash)
        assert not leaf.exists()
        cgsa_leaf = cgsa_work_dir(manager.cgsa_root, "BTCUSDT", "12h", config_hash)
        assert not cgsa_leaf.exists()


@pytest.mark.asyncio
async def test_bulk_delete_removes_cgsa_leaf(b4_client) -> None:
    """bulk delete 真刪 CGSA leaf（不靠 FFACT_CGSA_WORK_DIR skip）。"""
    client, _ff, manager, *_ = b4_client
    config_hash = "cfg_b4_cgsa"
    _create_run(manager, config_hash)
    cgsa_leaf = cgsa_work_dir(manager.cgsa_root, "BTCUSDT", "12h", config_hash)
    assert cgsa_leaf.exists()

    resp = await client.post(
        "/api/v1/features/runs/bulk-delete",
        json={
            "runs": [{"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": config_hash}],
        },
    )
    assert resp.status_code == 200
    assert len(resp.json()["deleted"]) == 1
    assert not cgsa_leaf.exists()


@pytest.mark.asyncio
async def test_bulk_delete_failed_retention_stays_pending_B3CONC(
    b4_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """delete 失敗時 retention 不誤標 DISCARDED。"""
    client, _ff, manager, batch_service, _tmp_path = b4_client
    monkeypatch.setenv("FFACT_BATCH_RETENTION", "1")
    batch_id = "batch-b4-fail-ret"
    config_hash = "cfg_b4_fail_ret"
    manifest = _create_run(manager, config_hash, batch_id=batch_id)
    checkpoint = batch_service._build_initial_checkpoint(
        batch_id,
        BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="12h"),
    )
    checkpoint["retention_items"] = [{
        "symbol": "BTCUSDT",
        "timeframe": "12h",
        "config_hash": config_hash,
        "state": RetentionState.PENDING.value,
        "hdf5_path": str(manifest / "feature_manifest.json"),
        "error": None,
    }]
    batch_service._safe_persist_checkpoint(checkpoint)
    original = shutil.rmtree

    def fail_delete(path: Path) -> None:
        if config_hash in str(path):
            raise OSError("simulated delete failure")
        original(path)

    monkeypatch.setattr("momentum.FeatureEngineering.run_lifecycle.shutil.rmtree", fail_delete)

    resp = await client.post(
        "/api/v1/features/runs/bulk-delete",
        json={
            "runs": [{"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": config_hash}],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["failed"]) == 1
    assert body["failed"][0]["config_hash"] == config_hash
    updated = batch_service._load_checkpoint(batch_id)
    assert updated is not None
    item = batch_service._find_retention_item(updated, "BTCUSDT", "12h", config_hash)
    assert item is not None
    assert item["state"] == RetentionState.PENDING.value


@pytest.mark.asyncio
async def test_ensure_browse_hidden_during_deleting(
    b4_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """deleting 期間 ensure_browse 視為不可用（404）。"""
    client, ff_service, manager, *_ = b4_client
    _create_run(manager, "cfg_browse_hide")
    marked = threading.Barrier(2)
    proceed = threading.Barrier(2)
    original = manager._delete_run_locked

    def slow_delete(*args: object, **kwargs: object):
        marked.wait()
        proceed.wait()
        return original(*args, **kwargs)

    monkeypatch.setattr(manager, "_delete_run_locked", slow_delete)

    def bulk_worker() -> None:
        ff_service.bulk_delete_runs([
            {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_browse_hide"},
        ])

    thread = threading.Thread(target=bulk_worker)
    thread.start()
    marked.wait()
    browse = await client.post("/api/v1/features/runs/BTCUSDT/12h/cfg_browse_hide/browse")
    assert browse.status_code == 404
    assert browse.json()["detail"]["code"] == "run_not_found"
    proceed.wait()
    thread.join()


@pytest.mark.asyncio
async def test_bulk_delete_partial_one_failure_continues(
    b4_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """一失敗其餘照刪 + failed 明列（不靜默/不中斷）。"""
    client, ff_service, manager, *_ = b4_client
    good = "cfg_b4_good"
    bad = "cfg_b4_bad"
    _create_run(manager, good)
    _create_run(manager, bad)
    original = shutil.rmtree

    def fail_one(path: Path) -> None:
        if bad in str(path):
            raise OSError("simulated delete failure")
        original(path)

    monkeypatch.setattr("momentum.FeatureEngineering.run_lifecycle.shutil.rmtree", fail_one)

    resp = await client.post(
        "/api/v1/features/runs/bulk-delete",
        json={
            "runs": [
                {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": bad},
                {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": good},
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["deleted"]) == 1
    assert body["deleted"][0]["config_hash"] == good
    assert len(body["failed"]) == 1
    assert body["failed"][0]["config_hash"] == bad
    assert "simulated delete failure" in body["failed"][0]["error"]
    remaining = {row["config_hash"] for row in ff_service.list_runs()}
    assert remaining == {"cfg_b4_bad"}


@pytest.mark.asyncio
async def test_bulk_delete_named_alias_run_succeeds(b4_client) -> None:
    """alias/batch_alias run 經 bulk(force mark)能刪。"""
    client, ff_service, manager, *_ = b4_client
    _create_run(manager, "cfg_named", alias="alpha")
    _create_run(manager, "cfg_batch_named", batch_alias="batch-alpha", batch_id="batch-1")

    resp = await client.post(
        "/api/v1/features/runs/bulk-delete",
        json={
            "runs": [
                {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_named"},
                {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_batch_named"},
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["deleted"]) == 2
    assert body["failed"] == []
    assert ff_service.list_runs() == []


@pytest.mark.asyncio
async def test_bulk_delete_mark_deleting_hides_from_list(
    b4_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mark-deleting 期間 list_runs 隱藏該 run。"""
    _client, ff_service, manager, *_ = b4_client
    monkeypatch.setattr(ff_service, "_lifecycle", lambda: manager)
    _create_run(manager, "cfg_hide")
    marked = threading.Barrier(2)
    proceed = threading.Barrier(2)
    original = manager._delete_run_locked

    def slow_delete(*args: object, **kwargs: object):
        marked.wait()
        proceed.wait()
        return original(*args, **kwargs)

    monkeypatch.setattr(manager, "_delete_run_locked", slow_delete)

    def bulk_worker() -> Dict[str, Any]:
        return ff_service.bulk_delete_runs([
            {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_hide"},
        ])

    thread = threading.Thread(target=bulk_worker)
    thread.start()
    marked.wait()
    visible = ff_service.list_runs()
    assert not any(row["config_hash"] == "cfg_hide" for row in visible)
    proceed.wait()
    thread.join()
    assert ff_service.list_runs() == []


@pytest.mark.asyncio
async def test_bulk_delete_run_not_found_failed(b4_client) -> None:
    client, *_ = b4_client
    resp = await client.post(
        "/api/v1/features/runs/bulk-delete",
        json={
            "runs": [{"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "missing"}],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["failed"]) == 1
    assert body["failed"][0]["error"] == "run_not_found"


@pytest.mark.asyncio
async def test_bulk_delete_run_busy_skipped(b4_client) -> None:
    client, _ff, manager, *_ = b4_client
    _create_run(manager, "cfg_busy")
    lease = RunLease.acquire(manager.locks_dir, "BTCUSDT", "12h", "cfg_busy")
    try:
        resp = await client.post(
            "/api/v1/features/runs/bulk-delete",
            json={
                "runs": [{"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_busy"}],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["skipped"]) == 1
        assert body["skipped"][0]["config_hash"] == "cfg_busy"
    finally:
        lease.release()


@pytest.mark.asyncio
async def test_bulk_delete_b3_pending_retention_discarded_B3CONC(
    b4_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """bulk 刪 B3 pending-retention run → retention_items 標 DISCARDED。"""
    client, ff_service, manager, batch_service, tmp_path = b4_client
    monkeypatch.setenv("FFACT_BATCH_RETENTION", "1")
    batch_id = "batch-b4-ret"
    config_hash = "cfg_b4_ret"
    manifest = _create_run(manager, config_hash, batch_id=batch_id)
    checkpoint = batch_service._build_initial_checkpoint(
        batch_id,
        BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="12h"),
    )
    checkpoint["retention_items"] = [{
        "symbol": "BTCUSDT",
        "timeframe": "12h",
        "config_hash": config_hash,
        "state": RetentionState.PENDING.value,
        "hdf5_path": str(manifest / "feature_manifest.json"),
        "error": None,
    }]
    batch_service._safe_persist_checkpoint(checkpoint)

    resp = await client.post(
        "/api/v1/features/runs/bulk-delete",
        json={
            "runs": [{"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": config_hash}],
        },
    )
    assert resp.status_code == 200
    assert len(resp.json()["deleted"]) == 1
    updated = batch_service._load_checkpoint(batch_id)
    assert updated is not None
    item = batch_service._find_retention_item(updated, "BTCUSDT", "12h", config_hash)
    assert item is not None
    assert item["state"] == RetentionState.DISCARDED.value


@pytest.mark.asyncio
async def test_bulk_delete_concurrent_same_run_idempotent_B3CONC(b4_client) -> None:
    """同 run 並發 bulk 刪除冪等：一成功其餘 failed/skipped，無雙刪 race。"""
    client, ff_service, manager, *_ = b4_client
    _create_run(manager, "cfg_conc")

    async def _bulk() -> httpx.Response:
        return await client.post(
            "/api/v1/features/runs/bulk-delete",
            json={
                "runs": [{"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_conc"}],
            },
        )

    first, second = await asyncio.gather(_bulk(), _bulk())
    assert first.status_code == 200
    assert second.status_code == 200
    deleted_hashes = {
        item["config_hash"]
        for payload in (first.json(), second.json())
        for item in payload["deleted"]
    }
    assert deleted_hashes == {"cfg_conc"}
    non_deleted = [
        item
        for payload in (first.json(), second.json())
        for bucket in ("failed", "skipped")
        for item in payload[bucket]
        if item["config_hash"] == "cfg_conc"
    ]
    assert len(non_deleted) == 1
    assert ff_service.list_runs() == []


@pytest.mark.asyncio
async def test_orphan_cleanup_registry_without_leaf(b4_client) -> None:
    """孤兒 (a)：registry 有、leaf 無 → 掃出 + 清掉。"""
    client, _ff, manager, *_ = b4_client
    manager.registry.add({
        "symbol": "BTCUSDT",
        "timeframe": "12h",
        "config_hash": "cfg_orphan_reg",
        "created_at": 1.0,
    })

    scan = await client.get("/api/v1/features/runs/orphans")
    assert scan.status_code == 200
    orphans = scan.json()["orphans"]
    assert any(
        o["kind"] == "registry_without_leaf" and o["config_hash"] == "cfg_orphan_reg"
        for o in orphans
    )

    dry = await client.post("/api/v1/features/runs/orphans/clean", json={"dry_run": True})
    assert dry.status_code == 200
    assert dry.json()["cleaned_registry"] == 0

    clean = await client.post("/api/v1/features/runs/orphans/clean", json={"dry_run": False})
    assert clean.status_code == 200
    assert clean.json()["cleaned_registry"] == 1
    assert manager.registry.get("BTCUSDT", "12h", "cfg_orphan_reg") is None


@pytest.mark.asyncio
async def test_orphan_cleanup_leaf_without_registry_features(b4_client) -> None:
    """孤兒 (b)：features leaf 有、registry 無 → 掃出 + 清掉。"""
    client, _ff, manager, *_ = b4_client
    leaf = features_run_dir(manager.features_root, "BTCUSDT", "12h", "cfg_orphan_leaf")
    leaf.mkdir(parents=True)
    (leaf / "feature_manifest.json").write_text("{}", encoding="utf-8")

    scan = await client.get("/api/v1/features/runs/orphans")
    assert any(
        o["kind"] == "leaf_without_registry" and o["leaf_kind"] in ("features", "both")
        for o in scan.json()["orphans"]
    )

    clean = await client.post("/api/v1/features/runs/orphans/clean", json={"dry_run": False})
    assert clean.status_code == 200
    assert clean.json()["cleaned_leaves"] == 1
    assert not leaf.exists()


@pytest.mark.asyncio
async def test_orphan_cleanup_cgsa_only_orphan(b4_client) -> None:
    """CGSA-only 孤兒掃出+清（features/registry 皆無）。"""
    client, _ff, manager, *_ = b4_client
    config_hash = "cfg_cgsa_only"
    cgsa_leaf = cgsa_work_dir(manager.cgsa_root, "BTCUSDT", "12h", config_hash)
    cgsa_leaf.mkdir(parents=True)
    (cgsa_leaf / "manifest.json").write_text(
        json.dumps({
            "symbol": "BTCUSDT",
            "timeframe": "12h",
            "config_hash": config_hash,
        }),
        encoding="utf-8",
    )

    scan = await client.get("/api/v1/features/runs/orphans")
    match = next(
        o for o in scan.json()["orphans"]
        if o["config_hash"] == config_hash and o["leaf_kind"] == "cgsa"
    )
    assert match["kind"] == "leaf_without_registry"

    clean = await client.post("/api/v1/features/runs/orphans/clean", json={"dry_run": False})
    assert clean.status_code == 200
    assert clean.json()["cleaned_leaves"] == 1
    assert not cgsa_leaf.exists()


@pytest.mark.asyncio
async def test_orphan_cleanup_active_run_not_cleaned(b4_client) -> None:
    """active(lease held) run 不誤清為孤兒。"""
    client, _ff, manager, *_ = b4_client
    leaf = features_run_dir(manager.features_root, "BTCUSDT", "12h", "cfg_active_orphan")
    leaf.mkdir(parents=True)
    (leaf / "feature_manifest.json").write_text("{}", encoding="utf-8")
    lease = RunLease.acquire(manager.locks_dir, "BTCUSDT", "12h", "cfg_active_orphan")
    try:
        scan = await client.get("/api/v1/features/runs/orphans")
        assert not any(o["config_hash"] == "cfg_active_orphan" for o in scan.json()["orphans"])
        clean = await client.post("/api/v1/features/runs/orphans/clean", json={"dry_run": False})
        assert clean.json()["cleaned_leaves"] == 0
        assert leaf.exists()
    finally:
        lease.release()


@pytest.mark.asyncio
async def test_b4_hermetic_data_cache_diff_empty(b4_client) -> None:
    """跑前後 data_cache 全量 diff 空（hermetic 自證）。"""
    before = _snapshot_data_cache()
    client, _ff, manager, *_ = b4_client
    _create_run(manager, "cfg_hermetic_a")
    _create_run(manager, "cfg_hermetic_b")

    await client.post(
        "/api/v1/features/runs/bulk-delete",
        json={
            "runs": [
                {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_hermetic_a"},
                {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_hermetic_b"},
            ],
        },
    )

    manager.registry.add({
        "symbol": "BTCUSDT",
        "timeframe": "12h",
        "config_hash": "cfg_orphan_tmp",
        "created_at": 1.0,
    })
    await client.post("/api/v1/features/runs/orphans/clean", json={"dry_run": False})

    after = _snapshot_data_cache()
    assert after == before
