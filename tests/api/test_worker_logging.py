"""B1 batch worker logging tests (Task 1.1 + 2.1, Codex adversarial #1-#6)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from api.core.config import settings
from api.core.logging import init_worker_logging
from api.models.feature_factory_models import BatchGenerateRequest
from api.services.feature_factory_batch_service import FeatureFactoryBatchService

_PROBE_MESSAGE = "worker momentum log probe"
_SMOKE_PADDING = "x" * 200


def _expected_api_log_path() -> str:
    date_stamp = datetime.now().strftime("%Y%m%d")
    return str(settings.logs_path / f"case_search_api_{date_stamp}.log")


def _read_log_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _extract_json_payload(line: str) -> Dict[str, Any]:
    """從 formatter 包裝的 log 行取出 JSON message。"""
    message = line.rsplit(" - ", 3)[-1]
    if message.startswith("[pid="):
        bracket_end = message.find("] ")
        if bracket_end != -1:
            message = message[bracket_end + 2 :]
    return json.loads(message)


def _flush_root_handlers() -> None:
    for logger_name in ("momentum", "api", ""):
        for handler in logging.getLogger(logger_name).handlers:
            handler.flush()


def _remove_worker_handlers() -> None:
    for logger_name in ("momentum", "api"):
        target = logging.getLogger(logger_name)
        for handler in list(target.handlers):
            if getattr(handler, "_ffact_worker_log_handler", False):
                target.removeHandler(handler)
                handler.close()


@pytest.fixture(autouse=True)
def _cleanup_worker_handlers():
    yield
    _remove_worker_handlers()


def test_init_worker_logging_idempotent_single_line(tmp_path) -> None:
    """adv#1: 連續 init 兩次只寫一行（無重複 handler）。"""
    log_path = tmp_path / "idempotent.log"
    init_worker_logging(str(log_path), "BTCUSDT", "1h")
    init_worker_logging(str(log_path), "BTCUSDT", "1h")

    logging.getLogger("momentum.test").info(_PROBE_MESSAGE)
    _flush_root_handlers()

    lines = _read_log_lines(log_path)
    probe_lines = [line for line in lines if _PROBE_MESSAGE in line]
    assert len(probe_lines) == 1


def test_init_worker_logging_preserves_existing_handlers(tmp_path) -> None:
    """adv#2: 既有 root StreamHandler/caplog 不被移除，root level 不變。"""
    log_path = tmp_path / "preserve.log"
    root = logging.getLogger()
    original_level = root.level
    stream_handler = logging.StreamHandler()
    root.addHandler(stream_handler)
    root_handlers_before = list(root.handlers)

    try:
        init_worker_logging(str(log_path), "ETHUSDT", "4h")

        assert root.level == original_level
        assert list(root.handlers) == root_handlers_before
        momentum_handlers = logging.getLogger("momentum").handlers
        assert any(getattr(h, "_ffact_worker_log_handler", False) for h in momentum_handlers)
    finally:
        root.removeHandler(stream_handler)
        stream_handler.close()


def test_compute_single_worker_logging_momentum_to_file(tmp_path, monkeypatch) -> None:
    """子進程 momentum logger 經 init_worker_logging 寫入指定檔。"""
    log_path = tmp_path / "worker.log"
    monkeypatch.setenv("FFACT_API_LOG_PATH", str(log_path))

    def fake_generate(**_kwargs):
        logging.getLogger("momentum.test").info(_PROBE_MESSAGE)
        result = MagicMock()
        result.hdf5_path = str(tmp_path / "BTCUSDT_1h.h5")
        return result

    factory_mock = MagicMock()
    factory_mock.generate_features.side_effect = fake_generate

    with patch("momentum.factories.create_feature_factory", return_value=factory_mock):
        path = FeatureFactoryBatchService._compute_single(
            "BTCUSDT",
            "1h",
            None,
            True,
            str(tmp_path),
        ).hdf5_path

    _flush_root_handlers()
    assert path.endswith("BTCUSDT_1h.h5")
    lines = _read_log_lines(log_path)
    assert any(_PROBE_MESSAGE in line for line in lines)
    assert any("[pid=" in line and "sym=BTCUSDT" in line and "tf=1h" in line for line in lines)


def test_compute_single_failopen_when_logging_setup_raises(tmp_path, monkeypatch) -> None:
    """adv#4: logging setup 失敗時 generate_features 仍被呼叫且結果照返。"""
    log_path = tmp_path / "failopen.log"
    monkeypatch.setenv("FFACT_API_LOG_PATH", str(log_path))

    factory_mock = MagicMock()
    factory_mock.generate_features.return_value = MagicMock(
        hdf5_path=str(tmp_path / "BTCUSDT_1h.h5"),
    )

    with patch("momentum.factories.create_feature_factory", return_value=factory_mock):
        with patch("api.core.logging.logging.FileHandler", side_effect=OSError("handler fail")):
            path = FeatureFactoryBatchService._compute_single(
                "BTCUSDT",
                "1h",
                None,
                True,
                str(tmp_path),
            ).hdf5_path

    assert path.endswith("BTCUSDT_1h.h5")
    factory_mock.generate_features.assert_called_once()


def test_compute_single_generate_exception_not_swallowed(tmp_path, monkeypatch) -> None:
    """adv#4: generate_features 例外不被 logging fail-open 吞掉。"""
    log_path = tmp_path / "gen_fail.log"
    monkeypatch.setenv("FFACT_API_LOG_PATH", str(log_path))

    factory_mock = MagicMock()
    factory_mock.generate_features.side_effect = ValueError("generation exploded")

    with patch("momentum.factories.create_feature_factory", return_value=factory_mock):
        with pytest.raises(RuntimeError, match="計算失敗"):
            FeatureFactoryBatchService._compute_single(
                "BTCUSDT",
                "1h",
                None,
                True,
                str(tmp_path),
            )


def _compute_capture_env(
    symbol: str,
    timeframe: str,
    _config_override,
    _force_regenerate: bool,
    _cache_dir: Optional[str] = None,
    _batch_id: str = "",
    _start_date: Optional[str] = None,
    _end_date: Optional[str] = None,
) -> str:
    return json.dumps(
        {
            "FFACT_API_LOG_PATH": os.environ.get("FFACT_API_LOG_PATH"),
            "symbol": symbol,
            "timeframe": timeframe,
        }
    )


async def _run_single_wave(
    service: FeatureFactoryBatchService,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Dict[str, Any]:
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ThreadPoolExecutor,
    )
    monkeypatch.setattr(
        FeatureFactoryBatchService,
        "_compute_single",
        staticmethod(_compute_capture_env),
    )

    task = {
        "task_id": "worker-log-env",
        "concurrent_symbols": 1,
        "total": 1,
        "completed": 0,
        "failed": 0,
        "results": {},
        "errors": {},
    }
    checkpoint = {
        "batch_id": "worker-log-env",
        "queued_items": [{"symbol": "BTCUSDT", "timeframe": "1h"}],
    }
    request = BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="1h")

    await service._process_item_wave(
        task,
        checkpoint,
        [{"symbol": "BTCUSDT", "timeframe": "1h"}],
        request,
        str(tmp_path),
    )
    return json.loads(task["results"]["BTCUSDT"])


@pytest.mark.asyncio
async def test_worker_log_env_sets_api_log_path(
    monkeypatch,
    batch_service_factory,
    tmp_path,
) -> None:
    """wave 期間 FFACT_API_LOG_PATH 指向當日 case_search_api 檔。"""
    monkeypatch.delenv("FFACT_API_LOG_PATH", raising=False)
    service = batch_service_factory(tmp_path)

    captured = await _run_single_wave(service, monkeypatch, tmp_path)
    assert captured["FFACT_API_LOG_PATH"] == _expected_api_log_path()


@pytest.mark.asyncio
async def test_worker_log_env_restores_when_previous_none(
    monkeypatch,
    batch_service_factory,
    tmp_path,
) -> None:
    """adv#6: previous None 時 wave 後還原為未設。"""
    monkeypatch.delenv("FFACT_API_LOG_PATH", raising=False)
    service = batch_service_factory(tmp_path)

    await _run_single_wave(service, monkeypatch, tmp_path)
    assert "FFACT_API_LOG_PATH" not in os.environ


@pytest.mark.asyncio
async def test_worker_log_env_restores_when_previous_value(
    monkeypatch,
    batch_service_factory,
    tmp_path,
) -> None:
    """adv#6: previous 有值時 wave 後還原原值。"""
    previous = "/tmp/previous_api_log.log"
    monkeypatch.setenv("FFACT_API_LOG_PATH", previous)
    service = batch_service_factory(tmp_path)

    await _run_single_wave(service, monkeypatch, tmp_path)
    assert os.environ.get("FFACT_API_LOG_PATH") == previous


@pytest.mark.asyncio
async def test_worker_log_env_restores_on_processpool_init_failure(
    monkeypatch,
    batch_service_factory,
    tmp_path,
) -> None:
    """adv#6: ProcessPool 建構失敗時仍還原 FFACT_API_LOG_PATH。"""
    previous = "/tmp/pool_fail_restore.log"
    monkeypatch.setenv("FFACT_API_LOG_PATH", previous)
    service = batch_service_factory(tmp_path)

    class ExplodingExecutor:
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("executor setup failed")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ExplodingExecutor,
    )

    task = {
        "task_id": "pool-fail-env",
        "concurrent_symbols": 1,
        "total": 1,
        "completed": 0,
        "failed": 0,
        "results": {},
        "errors": {},
    }
    checkpoint = {
        "batch_id": "pool-fail-env",
        "queued_items": [{"symbol": "BTCUSDT", "timeframe": "1h"}],
    }
    request = BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="1h")

    with pytest.raises(RuntimeError, match="executor setup failed"):
        await service._process_item_wave(
            task,
            checkpoint,
            [{"symbol": "BTCUSDT", "timeframe": "1h"}],
            request,
            str(tmp_path),
        )

    assert os.environ.get("FFACT_API_LOG_PATH") == previous



@pytest.mark.parametrize("child_count", [1, 2, 3, 4])
def test_worker_logging_smoke_multiprocess_append(tmp_path, child_count: int) -> None:
    """adv#3 smoke: 父 + N 子真 FileHandler 各寫唯一 JSON line，無 dup/partial。"""
    from tests.api.worker_logging_smoke_worker import smoke_worker

    log_path = tmp_path / "smoke.log"
    init_worker_logging(str(log_path), "PARENT", "1h")
    parent_payload = {
        "id": "parent",
        "pid": os.getpid(),
        "padding": _SMOKE_PADDING,
    }
    logging.getLogger("momentum.smoke").info(json.dumps(parent_payload))
    _flush_root_handlers()

    child_ids = [f"child-{index}" for index in range(child_count)]
    with ProcessPoolExecutor(max_workers=child_count) as executor:
        list(
            executor.map(
                smoke_worker,
                [(str(log_path), worker_id) for worker_id in child_ids],
            )
        )

    lines = _read_log_lines(log_path)
    expected_ids = {"parent", *child_ids}
    assert len(lines) == len(expected_ids)

    parsed_by_id: Dict[str, Dict[str, Any]] = {}
    for line in lines:
        payload = _extract_json_payload(line)
        worker_id = payload["id"]
        assert worker_id not in parsed_by_id, f"duplicate id {worker_id}"
        assert payload["padding"] == _SMOKE_PADDING
        parsed_by_id[worker_id] = payload

    assert set(parsed_by_id) == expected_ids
