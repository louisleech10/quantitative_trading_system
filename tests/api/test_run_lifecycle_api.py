from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from api.services.feature_factory_batch_service import FeatureFactoryBatchService
from api.services.feature_factory_service import FeatureFactoryService
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.run_locks import RunBusyError, is_run_active


def test_lease_sink_holds_until_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    factory = FeatureFactory.__new__(FeatureFactory)
    factory._storage = SimpleNamespace(base_path=tmp_path / "features")
    monkeypatch.setattr(factory, "_resolve_config", lambda _override: object())
    monkeypatch.setattr(factory, "_compute_config_hash", lambda *_args, **_kwargs: "cfg_batch2d")
    monkeypatch.setattr(factory, "_generate_features_impl", lambda *_args, **_kwargs: "result")
    sink: list = []
    assert factory.generate_features("BTCUSDT", "12h", lease_sink=sink) == "result"
    assert is_run_active(tmp_path / "features" / ".locks", "BTCUSDT", "12h", "cfg_batch2d")
    with pytest.raises(RunBusyError):
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

    def warmup():
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


def test_register_browse_id_uses_full_hash(tmp_path: Path) -> None:
    manifest = tmp_path / "features" / "BTCUSDT" / "12h" / "cfg_batch2d" / "feature_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"config_hash":"cfg_batch2d"}')
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._tasks = {}
    service._lock = threading.Lock()
    task_id = service.register_hdf5_for_browse("BTCUSDT", "12h", str(manifest))
    assert task_id == "browse_BTCUSDT_12h_cfg_batch2d"


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
    run = tmp_path / "features" / "BTCUSDT" / "12h" / "cfg_batch2d"
    run.mkdir(parents=True)
    manifest = run / "feature_manifest.json"
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
