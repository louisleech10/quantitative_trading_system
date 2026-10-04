"""ICFIRSTALIGN 乙 Task 4.2：API 批次 wave pool 加入子行程預算域（docs/ICFIRSTALIGN_SPEC.md v27 驗證 (g)(j)(k)）。

`_process_item_wave` 經 `momentum.factories.create_memory_budget_scheduler`（呼叫時解析）取得排程器；worker 本體
`_compute_single` 以關鍵字 `domain`（`DomainDescriptor`）接收顯式域描述；串行臂於根行程內依序呼叫同一本體。
本檔以排程器 spy 注入行程內執行緒池與執行緒身分（不起真實子行程、不生成特徵），`_compute_single` 以 capture 取代。
實作前應為紅：wave 仍直接建立 `ProcessPoolExecutor`、排程器為空殼、`_compute_single` 無 `domain`。
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

from api.models.feature_factory_models import BatchGenerateRequest
from api.services.feature_factory_batch_service import FeatureFactoryBatchService
from momentum.FeatureEngineering import memory_budget as mb

ITEMS = [{"symbol": "BTCUSDT", "timeframe": "12h"}, {"symbol": "ETHUSDT", "timeframe": "12h"}]


def _thread_identity() -> Tuple[int, float]:
    return (10 ** 9 + threading.get_ident() % 10 ** 6, 0.0)


def _capture(record: List[Dict[str, Any]], delay: float = 0.3):
    def compute(symbol: str, timeframe: str, _config_override: Any, _force_regenerate: bool,
                _cache_dir: Optional[str] = None, _batch_id: str = "", _start_date: Optional[str] = None,
                _end_date: Optional[str] = None, *, domain: Optional[mb.DomainDescriptor] = None) -> str:
        time.sleep(delay)
        record.append({"symbol": symbol, "domain": domain, "pid": os.getpid(), "thread": threading.get_ident()})
        return json.dumps({"symbol": symbol})
    return compute


def _spy(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> List[Any]:
    from momentum import factories

    created: List[Any] = []
    real = factories.create_memory_budget_scheduler

    def spy(**kw: Any) -> Any:
        kw.setdefault("executor_factory", ThreadPoolExecutor)
        kw.setdefault("task_identity", _thread_identity)
        kw.update(overrides)
        sched = real(**kw)
        created.append(sched)
        return sched

    monkeypatch.setattr(factories, "create_memory_budget_scheduler", spy)
    return created


async def _run_wave(service: FeatureFactoryBatchService, tmp_path: Path) -> Dict[str, Any]:
    task = {"task_id": "icfa-domain", "concurrent_symbols": 2, "total": 2, "completed": 0, "failed": 0,
            "results": {}, "errors": {}}
    checkpoint = {"batch_id": "icfa-domain", "queued_items": list(ITEMS)}
    request = BatchGenerateRequest(symbols=["BTCUSDT", "ETHUSDT"], timeframe="12h")
    beats = {"n": 0}
    stop = asyncio.Event()

    async def heartbeat() -> None:
        while not stop.is_set():
            beats["n"] += 1
            await asyncio.sleep(0.05)

    hb = asyncio.create_task(heartbeat())
    try:
        await service._process_item_wave(task, checkpoint, list(ITEMS), request, str(tmp_path))
    finally:
        stop.set()
        await hb
    return {"task": task, "beats": beats["n"]}


@pytest.mark.asyncio
async def test_api_wave_joins_domain_with_explicit_descriptor(monkeypatch, batch_service_factory, tmp_path) -> None:
    """(j)(k) wave 經排程器一次；兩 worker 收到同一域（root_pid、domain_dir、budget）之顯式描述、task_id 互異；
    父 `start_guard` 恰 1 次；全程不寫行程全域環境變數；事件迴圈心跳持續前進（join 不阻塞迴圈）。"""
    record: List[Dict[str, Any]] = []
    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(_capture(record)))
    created = _spy(monkeypatch)
    guards = {"n": 0}
    monkeypatch.setattr(mb, "start_guard", lambda *a, **k: guards.__setitem__("n", guards["n"] + 1))
    env_before = dict(os.environ)
    out = await _run_wave(batch_service_factory(tmp_path), tmp_path)
    assert len(created) == 1 and guards["n"] == 1
    domains = [r["domain"] for r in record]
    assert len(domains) == 2 and all(isinstance(d, mb.DomainDescriptor) for d in domains)
    assert {(d.root_pid, str(d.domain_dir), d.budget) for d in domains} == {(os.getpid(), str(domains[0].domain_dir),
                                                                             domains[0].budget)}
    assert len({d.task_id for d in domains}) == 2
    assert {k: v for k, v in os.environ.items() if k.startswith("ICFA_")} == \
        {k: v for k, v in env_before.items() if k.startswith("ICFA_")}
    assert out["beats"] >= 4


@pytest.mark.asyncio
async def test_api_wave_serial_arm_in_root_without_pool(monkeypatch, batch_service_factory, tmp_path) -> None:
    """(g) 無可准入（無輔助啟動上界收據）⇒ 根行程內依序呼叫同一 `_compute_single` 本體、`ProcessPoolExecutor` 建構 0 次、
    兩項皆完成；串行亦不阻塞事件迴圈。"""
    from concurrent.futures import process as cfp

    record: List[Dict[str, Any]] = []
    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(_capture(record)))
    _spy(monkeypatch, aux_startup_envelope=None)
    pools = {"n": 0}
    real_init = cfp.ProcessPoolExecutor.__init__
    monkeypatch.setattr(cfp.ProcessPoolExecutor, "__init__",
                        lambda self, *a, **k: (pools.__setitem__("n", pools["n"] + 1), real_init(self, *a, **k))[1])
    out = await _run_wave(batch_service_factory(tmp_path), tmp_path)
    assert pools["n"] == 0
    assert sorted(r["symbol"] for r in record) == ["BTCUSDT", "ETHUSDT"]
    assert all(r["pid"] == os.getpid() for r in record)
    assert json.loads(out["task"]["results"]["BTCUSDT"]) == {"symbol": "BTCUSDT"}
    assert out["beats"] >= 4


@pytest.mark.asyncio
async def test_mutation_api_worker_without_descriptor(monkeypatch, batch_service_factory, tmp_path) -> None:
    """mutant「經排程器但不把域描述交給 worker」（排程器 run 以 domain＝None 呼叫 worker 本體）⇒ worker 收到之描述非
    `DomainDescriptor`，正常案例之描述斷言翻轉。"""
    record: List[Dict[str, Any]] = []
    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(_capture(record, delay=0.0)))
    _spy(monkeypatch)
    real_run = mb.MemoryBudgetScheduler.run

    def run_without_descriptor(self: Any, tasks: Any, worker_fn: Any, serial_fn: Any, on_wave_joined: Any) -> Any:
        return real_run(self, tasks, lambda domain, payload: worker_fn(None, payload), serial_fn, on_wave_joined)

    monkeypatch.setattr(mb.MemoryBudgetScheduler, "run", run_without_descriptor)
    await _run_wave(batch_service_factory(tmp_path), tmp_path)
    assert record and not all(isinstance(r["domain"], mb.DomainDescriptor) for r in record)
