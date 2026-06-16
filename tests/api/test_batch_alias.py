from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from api.routes.feature_factory import router as feature_factory_router
import api.services.feature_factory_service as feature_service_module
from api.services.feature_factory_service import feature_factory_service
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.run_lifecycle import RunLifecycleManager
from momentum.FeatureEngineering.run_locks import RunBusyError
from momentum.FeatureEngineering.run_paths import cgsa_work_dir, features_run_dir
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator


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


def _entry(
    config_hash: str = "cfg_a",
    *,
    symbol: str = "BTCUSDT",
    batch_id: str | None = None,
    batch_alias: str | None = None,
    alias: str | None = None,
    created_at: float = 1.0,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "symbol": symbol,
        "timeframe": "12h",
        "config_hash": config_hash,
        "created_at": created_at,
        "last_generated_at": created_at,
    }
    if batch_id is not None:
        payload["batch_id"] = batch_id
    if batch_alias is not None:
        payload["batch_alias"] = batch_alias
    if alias is not None:
        payload["alias"] = alias
    return payload


def _manager(tmp_path: Path) -> tuple[RunLifecycleManager, FeatureRegistry]:
    features = tmp_path / "features"
    registry = FeatureRegistry(features / "registry.json")
    return RunLifecycleManager(features, tmp_path / "cgsa_work", features / ".locks", registry), registry


def _create_run(
    manager: RunLifecycleManager,
    registry: FeatureRegistry,
    config_hash: str,
    *,
    created_at: float = 1.0,
    batch_id: str | None = None,
    batch_alias: str | None = None,
    alias: str | None = None,
) -> None:
    feature_leaf = features_run_dir(manager.features_root, "BTCUSDT", "12h", config_hash)
    feature_leaf.mkdir(parents=True)
    (feature_leaf / "feature_manifest.json").write_text("{}", encoding="utf-8")
    cgsa_leaf = cgsa_work_dir(manager.cgsa_root, "BTCUSDT", "12h", config_hash)
    cgsa_leaf.mkdir(parents=True)
    (cgsa_leaf / "manifest.json").write_text(
        '{"config_hash":"' + config_hash + '"}',
        encoding="utf-8",
    )
    registry.add(
        _entry(
            config_hash,
            batch_id=batch_id,
            batch_alias=batch_alias,
            alias=alias,
            created_at=created_at,
        )
    )


# --- registry ---


def test_registry_add_writes_batch_id(tmp_path: Path) -> None:
    registry = FeatureRegistry(tmp_path / "registry.json")
    registry.add({**_entry(), "batch_id": "batch-1"})
    saved = registry.get("BTCUSDT", "12h", "cfg_a")
    assert saved is not None
    assert saved.get("batch_id") == "batch-1"


def test_registry_same_batch_id_regen_preserves_batch_alias(tmp_path: Path) -> None:
    registry = FeatureRegistry(tmp_path / "registry.json")
    registry.add({**_entry(), "batch_id": "batch-1"})
    registry.set_batch_alias("batch-1", "wave-a")
    registry.add({**_entry(), "batch_id": "batch-1", "feature_count": 9})
    saved = registry.get("BTCUSDT", "12h", "cfg_a")
    assert saved is not None
    assert saved.get("batch_id") == "batch-1"
    assert saved.get("batch_alias") == "wave-a"
    assert saved.get("feature_count") == 9


def test_registry_different_batch_id_resets_batch_alias(tmp_path: Path) -> None:
    registry = FeatureRegistry(tmp_path / "registry.json")
    registry.add({**_entry(), "batch_id": "batch-1"})
    registry.set_batch_alias("batch-1", "wave-a")
    registry.add({**_entry(), "batch_id": "batch-2"})
    saved = registry.get("BTCUSDT", "12h", "cfg_a")
    assert saved is not None
    assert saved.get("batch_id") == "batch-2"
    assert "batch_alias" not in saved


def test_registry_none_batch_id_merge_preserves_batch_fields(tmp_path: Path) -> None:
    registry = FeatureRegistry(tmp_path / "registry.json")
    registry.add({**_entry(), "batch_id": "batch-1"})
    registry.set_batch_alias("batch-1", "wave-a")
    registry.add({**_entry(), "feature_count": 11})
    saved = registry.get("BTCUSDT", "12h", "cfg_a")
    assert saved is not None
    assert saved.get("batch_id") == "batch-1"
    assert saved.get("batch_alias") == "wave-a"


def test_registry_set_batch_alias_updates_all_entries(tmp_path: Path) -> None:
    registry = FeatureRegistry(tmp_path / "registry.json")
    registry.add({**_entry("cfg_a"), "batch_id": "batch-1"})
    registry.add({**_entry("cfg_b", symbol="ETHUSDT"), "batch_id": "batch-1"})
    affected = registry.set_batch_alias("batch-1", "wave-a")
    assert affected == 2
    assert registry.get("BTCUSDT", "12h", "cfg_a")["batch_alias"] == "wave-a"
    assert registry.get("ETHUSDT", "12h", "cfg_b")["batch_alias"] == "wave-a"


def test_registry_set_batch_alias_does_not_touch_per_run_alias(tmp_path: Path) -> None:
    registry = FeatureRegistry(tmp_path / "registry.json")
    registry.add({**_entry(), "batch_id": "batch-1", "alias": "per-run"})
    registry.set_batch_alias("batch-1", "wave-a")
    saved = registry.get("BTCUSDT", "12h", "cfg_a")
    assert saved is not None
    assert saved.get("alias") == "per-run"
    assert saved.get("batch_alias") == "wave-a"


def test_registry_per_run_alias_survives_batch_id_reset(tmp_path: Path) -> None:
    registry = FeatureRegistry(tmp_path / "registry.json")
    registry.add({**_entry(), "batch_id": "batch-1", "alias": "per-run"})
    registry.set_batch_alias("batch-1", "wave-a")
    registry.add({**_entry(), "batch_id": "batch-2"})
    saved = registry.get("BTCUSDT", "12h", "cfg_a")
    assert saved is not None
    assert saved.get("alias") == "per-run"
    assert saved.get("batch_id") == "batch-2"
    assert "batch_alias" not in saved


def test_registry_set_batch_alias_deleting_raises_without_update(tmp_path: Path) -> None:
    registry = FeatureRegistry(tmp_path / "registry.json")
    registry.add({**_entry("cfg_a"), "batch_id": "batch-1"})
    registry.add({**_entry("cfg_b"), "batch_id": "batch-1"})
    registry.mark_deleting("BTCUSDT", "12h", "cfg_a")
    with pytest.raises(RunBusyError):
        registry.set_batch_alias("batch-1", "wave-a")
    assert registry.get("BTCUSDT", "12h", "cfg_b") is not None
    assert "batch_alias" not in registry.get("BTCUSDT", "12h", "cfg_b")


def test_registry_set_batch_alias_unknown_batch_raises_key_error(tmp_path: Path) -> None:
    registry = FeatureRegistry(tmp_path / "registry.json")
    with pytest.raises(KeyError):
        registry.set_batch_alias("missing-batch", "wave-a")


def test_registry_legacy_entry_loads_without_batch_fields(tmp_path: Path) -> None:
    registry = FeatureRegistry(tmp_path / "registry.json")
    registry.add(_entry())
    saved = registry.get("BTCUSDT", "12h", "cfg_a")
    assert saved is not None
    assert saved.get("batch_id") is None
    assert saved.get("batch_alias") is None


def test_multi_tf_generate_forwards_batch_id() -> None:
    captured: dict[str, object] = {}
    factory = MagicMock()
    factory._cgsa_registry = object()
    config = SimpleNamespace(
        timeframes=SimpleNamespace(primary="12h", training=["12h"]),
        preprocessing=SimpleNamespace(enabled=False),
    )
    generator = MultiTFGenerator(factory, config)

    def fake_cgsa(*_args, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            generation_time=1.0,
            metadata={},
        )

    generator._generate_multi_tf_cgsa = fake_cgsa  # type: ignore[method-assign]

    import pandas as pd

    factory._layer0_data_ingestion.return_value = pd.DataFrame(
        {"close": [1.0, 2.0]},
        index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
    )
    generator.generate_multi_tf("BTCUSDT", batch_id="batch-mtf")
    assert captured.get("batch_id") == "batch-mtf"


# --- api + cleanup ---


@pytest.mark.asyncio
async def test_patch_batch_alias_updates_all(
    async_client: httpx.AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, registry = _manager(tmp_path)
    _create_run(manager, registry, "cfg_a", batch_id="batch-1")
    _create_run(manager, registry, "cfg_b", batch_id="batch-1")
    monkeypatch.setattr(feature_factory_service, "_lifecycle", lambda: manager)
    response = await async_client.patch(
        "/api/v1/features/batch/batch-1/alias",
        json={"batch_alias": "wave-a"},
    )
    assert response.status_code == 200
    assert response.json()["affected"] == 2
    assert registry.get("BTCUSDT", "12h", "cfg_a")["batch_alias"] == "wave-a"


@pytest.mark.asyncio
async def test_patch_batch_alias_unknown_returns_404(
    async_client: httpx.AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, _registry = _manager(tmp_path)
    monkeypatch.setattr(feature_factory_service, "_lifecycle", lambda: manager)
    response = await async_client.patch(
        "/api/v1/features/batch/missing/alias",
        json={"batch_alias": "wave-a"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "batch_not_found"


@pytest.mark.asyncio
async def test_patch_batch_alias_deleting_returns_409(
    async_client: httpx.AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, registry = _manager(tmp_path)
    _create_run(manager, registry, "cfg_a", batch_id="batch-1")
    registry.mark_deleting("BTCUSDT", "12h", "cfg_a")
    monkeypatch.setattr(feature_factory_service, "_lifecycle", lambda: manager)
    response = await async_client.patch(
        "/api/v1/features/batch/batch-1/alias",
        json={"batch_alias": "wave-a"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "run_busy"
    assert "batch_alias" not in registry.get("BTCUSDT", "12h", "cfg_a")


@pytest.mark.asyncio
async def test_list_runs_includes_batch_fields(
    async_client: httpx.AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, registry = _manager(tmp_path)
    _create_run(manager, registry, "cfg_a", batch_id="batch-1")
    registry.set_batch_alias("batch-1", "wave-a")
    monkeypatch.setattr(feature_factory_service, "_lifecycle", lambda: manager)
    monkeypatch.setattr(
        feature_service_module,
        "settings",
        SimpleNamespace(data_cache_path=tmp_path),
    )
    response = await async_client.get("/api/v1/features/runs")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["batch_id"] == "batch-1"
    assert rows[0]["batch_alias"] == "wave-a"


def test_auto_cleanup_keeps_batch_alias_runs(tmp_path: Path) -> None:
    manager, registry = _manager(tmp_path)
    for index in range(5):
        _create_run(manager, registry, f"cfg_{index}", created_at=float(index))
    _create_run(
        manager,
        registry,
        "cfg_named",
        created_at=99.0,
        batch_id="batch-1",
        batch_alias="wave-a",
    )
    report = manager.auto_cleanup("BTCUSDT", "12h", keep_latest=0)
    remaining_hashes = {entry["config_hash"] for entry in registry.find("BTCUSDT", "12h")}
    assert "cfg_named" in remaining_hashes
    assert len(remaining_hashes) == 1
    assert len(report.deleted) == 5


def test_mark_deleting_skips_batch_alias_runs(tmp_path: Path) -> None:
    registry = FeatureRegistry(tmp_path / "registry.json")
    registry.add({**_entry(), "batch_id": "batch-1", "batch_alias": "wave-a"})
    assert not registry.mark_deleting("BTCUSDT", "12h", "cfg_a")
    assert registry.get("BTCUSDT", "12h", "cfg_a") is not None
