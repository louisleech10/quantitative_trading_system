#!/usr/bin/env python3
"""b3 review-r3: re-check r2 counterexample shapes against 96fd5746 (cancel / owner / join)."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(os.environ.get("PROBE_ROOT", "/tmp/icfa_b3r3_w1"))
BASE = Path(os.environ.get("PROBE_BASE", str(ROOT / "probe_state")))
BASE.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from momentum.FeatureEngineering import memory_budget as mb


def owner_race() -> Dict[str, Any]:
    """r2 P1-02 shape: sweep between mkdtemp return and start must not delete live scope."""
    base = BASE / "owner_race"
    base.mkdir(parents=True, exist_ok=True)
    key = "BTCUSDT/1h/race"
    swept: List[List[str]] = []
    real = tempfile.mkdtemp

    def mkdtemp_then_sweep(*a: Any, **k: Any) -> str:
        path = real(*a, **k)
        if Path(k.get("dir", "")) == base:
            swept.append(mb.recover_orphan_pre_lease_scopes(base, key, BASE / "run_or"))
        return path

    class Handle:
        pid = None
        extra: Dict[str, Any] = {}

        def stop(self) -> None:
            pass

    mb.tempfile.mkdtemp = mkdtemp_then_sweep  # type: ignore[attr-defined]
    try:
        orig_start = mb.start_guard
        mb.start_guard = lambda *a, **k: Handle()  # type: ignore[assignment]
        scope = mb.begin_pre_lease_scope(base, key)
        try:
            alive = scope.run_dir.exists()
            token_in_name = f"{os.getpid()}-" in scope.run_dir.name
        finally:
            scope.close()
        return {"swept": swept, "alive_after_sweep": alive, "token_in_name": token_in_name,
                "closed_clean": not list(base.glob(f"{mb.PRE_LEASE_SCOPE_PREFIX}*"))}
    finally:
        mb.tempfile.mkdtemp = real  # type: ignore[attr-defined]
        mb.start_guard = orig_start  # type: ignore[assignment]


def join_transient() -> Dict[str, Any]:
    """r2 P1-03 shape: first shutdown fails before join, second succeeds."""
    release = threading.Event()
    started = threading.Event()
    shutdowns: List[bool] = []

    class Executor(ThreadPoolExecutor):
        def __init__(self, *a: Any, **k: Any) -> None:
            super().__init__(*a, **k)
            self._fail_once = True

        def shutdown(self, *a: Any, **k: Any) -> None:
            shutdowns.append(True)
            if self._fail_once:
                self._fail_once = False
                raise OSError("transient shutdown failure")
            return super().shutdown(*a, **k)

    executors: List[Any] = []

    def factory(n: int) -> Any:
        if executors:
            assert started.wait(2)
            raise OSError("injected second executor creation failure")
        obj = Executor(n)
        executors.append(obj)
        return obj

    def worker(_d: Any, payload: Any) -> Any:
        started.set()
        release.wait(5)
        return payload

    def identity() -> Any:
        return (threading.get_ident(), 0.0)

    sched = mb.MemoryBudgetScheduler(
        1000, domain_dir=BASE / "join", max_workers=2, executor_factory=factory,
        read_system=lambda: (1000, 1, False, 10, ()), read_task_footprint=lambda tid: 10,
        aux_startup_envelope=1, task_identity=identity,
    )
    timer = threading.Timer(0.4, release.set)
    timer.start()
    err = None
    try:
        try:
            sched.run([mb.Task("A", 100, 1), mb.Task("B", 100, 2)], worker, lambda p: p, lambda w: None)
        except OSError as exc:
            err = str(exc)
    finally:
        release.set()
        timer.cancel()
    return {
        "error": err,
        "shutdowns": len(shutdowns),
        "worker_alive": any(t.is_alive() for ex in executors for t in ex._threads),
        "A_status": sched._tasks["A"].status,
        "join_retry_events": [e for e in sched.trace if e[0] == "join_retry"],
    }


def cancel_stop_keeps_admitted() -> Dict[str, Any]:
    """r2 P1-01 / assumed ②: request_stop leaves admitted result + on_wave_joined."""
    release = threading.Event()
    started = threading.Event()
    joined_waves: List[int] = []

    def worker(_d: Any, payload: Any) -> Any:
        started.set()
        release.wait(5)
        return payload

    def identity() -> Any:
        return (threading.get_ident(), 0.0)

    sched = mb.MemoryBudgetScheduler(
        1000, domain_dir=BASE / "stop", max_workers=1, executor_factory=ThreadPoolExecutor,
        read_system=lambda: (1000, 1, False, 10, ()), read_task_footprint=lambda tid: 10,
        aux_startup_envelope=1, task_identity=identity,
    )

    def run() -> Any:
        return sched.run(
            [mb.Task("A", 100, "ok-a"), mb.Task("B", 100, "ok-b")],
            worker, lambda p: p, lambda wave: joined_waves.append(len(wave)),
        )

    thr = threading.Thread(target=lambda: setattr(run, "out", run()))
    thr.start()
    assert started.wait(3)
    sched.request_stop()
    time.sleep(0.05)
    release.set()
    thr.join(10)
    out = getattr(run, "out")
    return {
        "results": [type(x).__name__ if isinstance(x, BaseException) else x for x in out],
        "statuses": {tid: st.status for tid, st in sched._tasks.items()},
        "joined_waves": joined_waves,
        "thread_alive": thr.is_alive(),
    }


def await_owned_multi_cancel() -> Dict[str, Any]:
    """assumed ①: nested cancel still waits; close only after future done."""
    from api.services import feature_factory_batch_service as svc

    loop = asyncio.new_event_loop()
    done_order: List[str] = []

    async def body() -> None:
        fut: asyncio.Future = loop.create_future()

        def complete() -> None:
            time.sleep(0.25)
            done_order.append("future_done")
            loop.call_soon_threadsafe(fut.set_result, "ok")

        threading.Thread(target=complete, daemon=True).start()
        task = asyncio.create_task(svc._await_owned(fut))

        async def cancel_twice() -> None:
            await asyncio.sleep(0.02)
            task.cancel()
            await asyncio.sleep(0.02)
            task.cancel()

        asyncio.create_task(cancel_twice())
        await task
        done_order.append("await_returned")

    loop.run_until_complete(body())
    loop.close()
    return {"order": done_order, "future_before_return": done_order.index("future_done")
            < done_order.index("await_returned")}


def main() -> int:
    receipt = {
        "commit": "96fd5746",
        "owner_race": owner_race(),
        "join_transient": join_transient(),
        "cancel_stop": cancel_stop_keeps_admitted(),
        "await_owned": await_owned_multi_cancel(),
    }
    o = receipt["owner_race"]
    j = receipt["join_transient"]
    c = receipt["cancel_stop"]
    a = receipt["await_owned"]
    closed = (
        o["swept"] == [[]] and o["alive_after_sweep"] and o["token_in_name"] and o["closed_clean"]
        and j["error"] and "second executor" in (j["error"] or "")
        and j["shutdowns"] >= 2 and j["worker_alive"] is False and j["A_status"] == "joined"
        and c["results"][0] == "ok-a"
        and c["results"][1] == "SchedulerStopped"
        and c["statuses"]["A"] == "joined"
        and c["joined_waves"] == [1]
        and a["future_before_return"] is True
    )
    receipt["all_closed"] = closed
    out = Path(os.environ.get("PROBE_OUT", str(BASE / "b3r3_closure.json")))
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"all_closed": closed, "out": str(out)}, ensure_ascii=False))
    return 0 if closed else 1


if __name__ == "__main__":
    raise SystemExit(main())
