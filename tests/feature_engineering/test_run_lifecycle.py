from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from momentum.FeatureEngineering.feature_registry import (
    FeatureRegistry,
    RegistryCorruptError,
    RegistryLockTimeout,
)
from momentum.FeatureEngineering.run_locks import RunBusyError, RunLease, is_run_active
from momentum.FeatureEngineering.run_lifecycle import RunLifecycleManager
from momentum.FeatureEngineering.run_paths import cgsa_work_dir, features_run_dir, safe_token, validate_config_hash


@pytest.fixture(autouse=True)
def _isolate_cgsa_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)


def test_paths_validate_and_preserve_existing_rules(tmp_path: Path) -> None:
    assert validate_config_hash("cfg_batch2d") == "cfg_batch2d"
    for invalid in ("../x", "..", "", "x" * 65):
        with pytest.raises(ValueError):
            validate_config_hash(invalid)
    assert safe_token("BTC/USDT") == "BTC_USDT"
    assert features_run_dir(tmp_path, "BTCUSDT", "12h", "cfg_batch2d") == tmp_path / "BTCUSDT" / "12h" / "cfg_batch2d"
    assert cgsa_work_dir(tmp_path, "BTC/USDT", "12 h", "abcdefgh123") == (tmp_path / "BTC_USDT_12_h_abcdefgh").resolve()


def test_locks_exclusive_release_and_active(tmp_path: Path) -> None:
    lease = RunLease.acquire(tmp_path, "BTCUSDT", "12h", "cfg_batch2d")
    assert is_run_active(tmp_path, "BTCUSDT", "12h", "cfg_batch2d")
    with pytest.raises(RunBusyError):
        RunLease.acquire(tmp_path, "BTCUSDT", "12h", "cfg_batch2d")
    other = RunLease.acquire(tmp_path, "ETHUSDT", "12h", "cfg_batch2d")
    other.release()
    lease.release()
    lease.release()
    assert not is_run_active(tmp_path, "BTCUSDT", "12h", "cfg_batch2d")
    RunLease.acquire(tmp_path, "BTCUSDT", "12h", "cfg_batch2d").release()


def test_locks_thread_barrier_has_exactly_one_winner(tmp_path: Path) -> None:
    start = threading.Barrier(8)
    acquired = threading.Barrier(2)
    winners: list[RunLease] = []

    def compete() -> None:
        start.wait()
        try:
            lease = RunLease.acquire(tmp_path, "BTCUSDT", "12h", "cfg_batch2d")
        except RunBusyError:
            return
        winners.append(lease)
        acquired.wait()

    threads = [threading.Thread(target=compete) for _ in range(8)]
    for thread in threads:
        thread.start()
    acquired.wait()
    for thread in threads:
        thread.join()
    assert len(winners) == 1
    winners[0].release()


def test_locks_subprocess_kill_releases_kernel_lock(tmp_path: Path) -> None:
    code = "\n".join([
        "import pathlib, sys",
        "from momentum.FeatureEngineering.run_locks import RunLease",
        "lease = RunLease.acquire(pathlib.Path(sys.argv[1]), 'BTCUSDT', '12h', 'cfg_batch2d')",
        "print('ready', flush=True)",
        "sys.stdin.read()",
    ])
    proc = subprocess.Popen(
        [sys.executable, "-c", code, str(tmp_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdout is not None
        assert proc.stdout.readline().strip() == "ready"
        with pytest.raises(RunBusyError):
            RunLease.acquire(tmp_path, "BTCUSDT", "12h", "cfg_batch2d")
        os.kill(proc.pid, signal.SIGKILL)
        proc.wait(timeout=1)
        RunLease.acquire(tmp_path, "BTCUSDT", "12h", "cfg_batch2d").release()
    finally:
        if proc.poll() is None:
            proc.kill()


def _entry(config_hash: str = "cfg_batch2d") -> dict[str, object]:
    return {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": config_hash, "created_at": 1.0}


def test_registry_transactions_preserve_fields_and_instances(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    first = FeatureRegistry(path)
    second = FeatureRegistry(path)
    first.add(_entry())
    first.set_alias("BTCUSDT", "12h", "cfg_batch2d", "alpha")
    second.add({**_entry(), "size_bytes": 99})
    saved = FeatureRegistry(path).get("BTCUSDT", "12h", "cfg_batch2d")
    assert saved == {**_entry(), "size_bytes": 99, "alias": "alpha"}
    previous = path.read_bytes()
    second.add({"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_other"})
    assert path.with_name("registry.json.bak").read_bytes() == previous


def test_registry_deleting_alias_and_remove(tmp_path: Path) -> None:
    registry = FeatureRegistry(tmp_path / "registry.json")
    registry.add(_entry())
    assert registry.mark_deleting("BTCUSDT", "12h", "cfg_batch2d")
    with pytest.raises(RunBusyError):
        registry.set_alias("BTCUSDT", "12h", "cfg_batch2d", "alpha")
    assert registry.clear_deleting("BTCUSDT", "12h", "cfg_batch2d")
    registry.set_alias("BTCUSDT", "12h", "cfg_batch2d", " ")
    assert registry.remove("BTCUSDT", "12h", "cfg_batch2d")
    assert not registry.remove("BTCUSDT", "12h", "cfg_batch2d")


def test_registry_corrupt_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    original = b"{broken"
    path.write_bytes(original)
    registry = FeatureRegistry(path)
    with pytest.raises(RegistryCorruptError):
        registry.set_alias("BTCUSDT", "12h", "cfg_batch2d", "alpha")
    registry.add(_entry())
    assert path.read_bytes() == original
    assert len(list(tmp_path.glob("registry.json.corrupt-*"))) == 1


def test_registry_lock_timeout_is_distinct(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "registry.json"
    path.with_name("registry.json.lock").write_text("held")
    registry = FeatureRegistry(path)
    monkeypatch.setattr(registry, "LOCK_TIMEOUT_SECONDS", 0.0)
    with pytest.raises(RegistryLockTimeout):
        registry.add(_entry())


def _manager(tmp_path: Path) -> tuple[RunLifecycleManager, FeatureRegistry]:
    features = tmp_path / "features"
    registry = FeatureRegistry(features / "registry.json")
    return RunLifecycleManager(features, tmp_path / "cgsa_work", features / ".locks", registry), registry


def _create_run(manager: RunLifecycleManager, registry: FeatureRegistry, config_hash: str, created_at: float = 1.0) -> None:
    feature_leaf = features_run_dir(manager.features_root, "BTCUSDT", "12h", config_hash)
    feature_leaf.mkdir(parents=True)
    (feature_leaf / "data.bin").write_bytes(b"features")
    cgsa_leaf = cgsa_work_dir(manager.cgsa_root, "BTCUSDT", "12h", config_hash)
    cgsa_leaf.mkdir(parents=True)
    (cgsa_leaf / "manifest.json").write_text('{"config_hash":"' + config_hash + '"}')
    registry.add({**_entry(config_hash), "created_at": created_at})


def test_delete_removes_owned_leaves_and_registry(tmp_path: Path) -> None:
    manager, registry = _manager(tmp_path)
    _create_run(manager, registry, "cfg_batch2d")
    result = manager.delete_run("BTCUSDT", "12h", "cfg_batch2d")
    assert result.features_deleted and result.cgsa_deleted and result.registry_removed
    assert result.total_bytes > 0 and not result.errors
    assert manager.delete_run("BTCUSDT", "12h", "cfg_batch2d").errors == []


def test_delete_rejects_symlink_and_keeps_registry(tmp_path: Path) -> None:
    manager, registry = _manager(tmp_path)
    outside = tmp_path / "outside"
    (outside / "12h" / "cfg_batch2d").mkdir(parents=True)
    symbol_dir = manager.features_root / "BTCUSDT"
    symbol_dir.parent.mkdir(parents=True, exist_ok=True)
    symbol_dir.symlink_to(outside, target_is_directory=True)
    registry.add(_entry())
    result = manager.delete_run("BTCUSDT", "12h", "cfg_batch2d")
    assert result.errors and registry.get("BTCUSDT", "12h", "cfg_batch2d") is not None
    assert outside.exists()


def test_delete_cgsa_ownership_and_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager, registry = _manager(tmp_path)
    _create_run(manager, registry, "cfg_batch2d")
    cgsa_leaf = cgsa_work_dir(manager.cgsa_root, "BTCUSDT", "12h", "cfg_batch2d")
    (cgsa_leaf / "manifest.json").write_text('{"config_hash":"cfg_other"}')
    result = manager.delete_run("BTCUSDT", "12h", "cfg_batch2d")
    assert "ownership_mismatch" in result.skipped and cgsa_leaf.exists()

    _create_run(manager, registry, "cfg_other")
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "override"))
    override_result = manager.delete_run("BTCUSDT", "12h", "cfg_other")
    assert "work_dir_override" in override_result.skipped


def test_delete_permission_error_keeps_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager, registry = _manager(tmp_path)
    _create_run(manager, registry, "cfg_batch2d")
    original = __import__("shutil").rmtree

    def fail_features(path: Path) -> None:
        if Path(path).is_relative_to(manager.features_root):
            raise PermissionError("denied")
        original(path)

    monkeypatch.setattr("momentum.FeatureEngineering.run_lifecycle.shutil.rmtree", fail_features)
    result = manager.delete_run("BTCUSDT", "12h", "cfg_batch2d")
    assert result.errors and registry.get("BTCUSDT", "12h", "cfg_batch2d") is not None


def test_cleanup_keeps_latest_named_and_busy(tmp_path: Path) -> None:
    manager, registry = _manager(tmp_path)
    for index in range(7):
        _create_run(manager, registry, f"cfg_{index}", float(index))
    registry.set_alias("BTCUSDT", "12h", "cfg_0", "named")
    busy = RunLease.acquire(manager.locks_dir, "BTCUSDT", "12h", "cfg_1")
    try:
        report = manager.auto_cleanup("BTCUSDT", "12h", keep_latest=5)
    finally:
        busy.release()
    assert "cfg_1" in report.skipped_busy
    assert registry.get("BTCUSDT", "12h", "cfg_0") is not None
    assert len(registry.find("BTCUSDT", "12h")) == 7


def test_cleanup_alias_race_is_blocked_after_mark(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager, registry = _manager(tmp_path)
    _create_run(manager, registry, "cfg_old", 0.0)
    _create_run(manager, registry, "cfg_new", 1.0)
    marked = threading.Barrier(2)
    continue_delete = threading.Barrier(2)
    original = manager._delete_run_locked

    def blocked_delete(*args: object, **kwargs: object):
        marked.wait()
        continue_delete.wait()
        return original(*args, **kwargs)

    monkeypatch.setattr(manager, "_delete_run_locked", blocked_delete)
    thread = threading.Thread(target=manager.auto_cleanup, args=("BTCUSDT", "12h", 1))
    thread.start()
    marked.wait()
    with pytest.raises(RunBusyError):
        manager.set_run_alias("BTCUSDT", "12h", "cfg_old", "late")
    continue_delete.wait()
    thread.join()
    assert registry.get("BTCUSDT", "12h", "cfg_old") is None
