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
    # b3 實作期：任務峰值 E 依 kline 形狀估算（`factories.estimate_symbol_envelope`）；本檔不生成特徵、批次 cache 為
    # 空暫存目錄（形狀不可得 ⇒ 依 SPEC 走串行臂），故注入固定 E 使准入判定可驗（串行臂案例另以無輔助上界驅動）
    monkeypatch.setattr(factories, "estimate_symbol_envelope", lambda **kw: 64 << 20)
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
    return {"task": task, "beats": beats["n"], "checkpoint": checkpoint, "request": request}


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


_SERIAL_DRIVERS = {"aux_without_receipt": {"aux_startup_envelope": None},
                   "available_insufficient": {"read_system": lambda: (0, 1, False, 0, ())}}


@pytest.mark.asyncio
@pytest.mark.parametrize("driver", list(_SERIAL_DRIVERS))
async def test_api_wave_serial_arm_in_root_without_pool(monkeypatch, batch_service_factory, tmp_path,
                                                        driver) -> None:
    """(g) 無可准入（無輔助啟動上界收據；或 SPEC v35 剩餘可用量 A 不足）⇒ 根行程內依序呼叫同一 `_compute_single` 本體、
    `ProcessPoolExecutor` 建構 0 次、兩項皆完成；串行亦不阻塞事件迴圈。"""
    from concurrent.futures import process as cfp

    record: List[Dict[str, Any]] = []
    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(_capture(record)))
    _spy(monkeypatch, **_SERIAL_DRIVERS[driver])
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
    # 審碼 b3 r6 codex P2-02：並行→串行之決定記入批次任務 metadata `memory_route`（每項一筆、含 G、A、F、R）
    routes = out["task"]["memory_route"]
    assert sorted(r["task_id"].split("|")[0] for r in routes) == ["BTCUSDT", "ETHUSDT"]
    assert all(r["point"] == "scheduler" and r["to"] == "serial" and r["reason"] == _SERIAL_ROUTE_REASON[driver]
               and {"G", "A", "F", "R"} <= set(r) for r in routes)
    # 審碼 b3 r7 codex P2-01：紀錄隨各完成項存入 checkpoint；恢復重建 task 狀態時原樣取回（不遺失、不重加）
    completed = out["checkpoint"]["completed_items"]
    assert sorted(len(item["memory_route"]) for item in completed) == [1, 1]
    service = batch_service_factory(tmp_path / "resume")
    resumed = service._build_task_state("icfa-domain", out["request"], out["checkpoint"], "paused")
    assert resumed["memory_route"] == routes


def _routing_compute(fail: bool):
    """生成內記一筆選路（`record_route`，同正式 producer）後回傳或拋錯。"""
    def compute(symbol: str, timeframe: str, *a: Any, domain: Optional[mb.DomainDescriptor] = None) -> Any:
        mb.record_route({"point": "Layer 2", "from": "L2.polars", "to": "L2.pandas_serial", "symbol": symbol})
        if fail:
            raise ValueError("after route")
        return json.dumps({"symbol": symbol})
    return compute


_ROUTE_CASES = {"worker_ok": ({}, False, "completed_items"), "worker_failed": ({}, True, "failed_items"),
                "serial_failed": ({"aux_startup_envelope": None}, True, "failed_items")}


@pytest.mark.asyncio
@pytest.mark.parametrize("case", list(_ROUTE_CASES))
async def test_api_wave_generation_route_records_reach_task(monkeypatch, batch_service_factory, tmp_path,
                                                            case: str) -> None:
    """審碼 b3 r7／r8 codex P2-01：各項生成內之選路紀錄——並行 worker（經域目錄交回）與根之串行臂（經根情境），
    成功或生成後失敗——皆併入批次任務與其 checkpoint completed／failed 項，恢復重建不遺失；串行臂另含排程器決定在前。"""
    overrides, fail, bucket = _ROUTE_CASES[case]
    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(_routing_compute(fail)))
    _spy(monkeypatch, **overrides)
    out = await _run_wave(batch_service_factory(tmp_path), tmp_path)
    items = out["checkpoint"][bucket]
    assert sorted(item["symbol"] for item in items) == ["BTCUSDT", "ETHUSDT"]
    for item in items:
        points = [r["point"] for r in item["memory_route"]]
        expected = (["scheduler"] if case.startswith("serial") else []) + ["Layer 2"]
        assert points == expected, item
        assert item["memory_route"][-1]["symbol"] == item["symbol"]
    assert sorted(r["symbol"] for r in out["task"]["memory_route"] if r["point"] == "Layer 2") == ["BTCUSDT", "ETHUSDT"]
    resumed = batch_service_factory(tmp_path / "resume")._build_task_state("icfa-domain", out["request"],
                                                                           out["checkpoint"], "paused")
    assert resumed["memory_route"] == out["task"]["memory_route"]


@pytest.mark.asyncio
async def test_mutation_api_route_records_only_from_success_result(monkeypatch, batch_service_factory,
                                                                   tmp_path) -> None:
    """mutant「只取成功結果之紀錄、不取排程器之各任務紀錄」（r7 修補）⇒ 生成後失敗之項無紀錄 ⇒ 上案斷言紅。"""
    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(_routing_compute(True)))
    created = _spy(monkeypatch)
    real_run = mb.MemoryBudgetScheduler.run

    def run_dropping_task_routes(self: Any, *a: Any, **k: Any) -> Any:
        out = real_run(self, *a, **k)
        self.task_routes = {}
        return out

    monkeypatch.setattr(mb.MemoryBudgetScheduler, "run", run_dropping_task_routes)
    out = await _run_wave(batch_service_factory(tmp_path), tmp_path)
    assert created and all("memory_route" not in item for item in out["checkpoint"]["failed_items"])


_SERIAL_ROUTE_REASON = {"aux_without_receipt": "no_aux_receipt", "available_insufficient": "admission:absorbable"}


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


@pytest.mark.asyncio
async def test_api_wave_cancel_waits_for_started_workers(monkeypatch, batch_service_factory, tmp_path) -> None:
    """v31（審碼 b3 r2 codex P1-01）：wave 之 asyncio 取消只作用於等待者 ⇒ 排程器停止准入新任務（佇列中之
    ETHUSDT 不執行）、已啟動之 BTCUSDT worker 完成並 joined 後，域（與守護）才關閉，再傳遞取消。改前：取消即進
    finally 關閉域，worker 仍在執行而紅。"""
    started, release = threading.Event(), threading.Event()
    finished: List[str] = []

    def compute(symbol: str, timeframe: str, *_a: Any, domain: Optional[mb.DomainDescriptor] = None) -> str:
        started.set()
        release.wait(5)
        finished.append(symbol)
        return json.dumps({"symbol": symbol})

    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(compute))
    created = _spy(monkeypatch, max_workers=1)
    monkeypatch.setattr(mb, "start_guard", lambda *a, **k: None)
    closes: List[List[str]] = []
    real_close = mb.BudgetDomain.close

    def close(self: Any) -> None:
        closes.append(list(finished))
        real_close(self)

    monkeypatch.setattr(mb.BudgetDomain, "close", close)
    task = {"task_id": "icfa-cancel", "concurrent_symbols": 2, "total": 2, "completed": 0, "failed": 0,
            "results": {}, "errors": {}}
    checkpoint = {"batch_id": "icfa-cancel", "queued_items": list(ITEMS)}
    request = BatchGenerateRequest(symbols=["BTCUSDT", "ETHUSDT"], timeframe="12h")
    service = batch_service_factory(tmp_path)
    wave = asyncio.create_task(service._process_item_wave(task, checkpoint, list(ITEMS), request, str(tmp_path)))
    assert await asyncio.get_running_loop().run_in_executor(None, started.wait, 5)
    wave.cancel()
    timer = threading.Timer(0.3, release.set)
    timer.start()
    try:
        with pytest.raises(asyncio.CancelledError):
            await wave
    finally:
        release.set()
        timer.cancel()
    assert closes == [["BTCUSDT"]], "域須於已啟動之 worker 完成後才關閉"
    assert finished == ["BTCUSDT"]
    statuses = {tid: st.status for tid, st in created[0]._tasks.items()}
    assert statuses == {"BTCUSDT|12h": "joined", "ETHUSDT|12h": "queued"}


@pytest.mark.parametrize("error,passthrough", [(mb.MemoryRerouteNeeded("L1", 20, 40, 50, mb.MSG_ESTIMATE_EXCEEDED), True),
                                               (RuntimeError("boom"), False)])
def test_compute_single_passes_reroute_through(monkeypatch, error, passthrough) -> None:
    """SPEC v35：worker 本體遇 `MemoryRerouteNeeded` ⇒ 原樣上拋（交排程器於波次 join 後改走根之正式串行臂），不包裝
    為一般「計算失敗」；其他例外照舊包裝。"""
    import momentum.factories as factories_module

    class _Factory:
        def generate_features(self, **_kw: Any) -> Any:
            raise error

    monkeypatch.setattr(factories_module, "create_feature_factory", lambda **_kw: _Factory())
    with pytest.raises(Exception) as info:
        FeatureFactoryBatchService._compute_single_body("BTCUSDT", "12h", None, False)
    if passthrough:
        assert info.value is error
    else:
        assert isinstance(info.value, RuntimeError) and "計算失敗" in str(info.value)
