"""NOCAP SPEC Task 5.3 共用背景工作紀錄（`api/core/background_jobs.py`）之契約驗收。

首個消費端＝ICPERF SPEC Task 0.6 (h) ⑦（Coverage 端點改任務制，L1c）；契約見 docs/NOCAP_SPEC.md Task 5.3：
- 狀態機 queued→running→{completed, failed, cancelled, interrupted}；running 之取消先進 cancelling，於安全點生效。
- 每次狀態變更、進度與結果原子寫入（同目錄暫存檔＋os.replace）；processed 不減、updated_at 隨推進更新。
- 取消後晚到之結果不覆寫（fn 回傳時已請求取消 ⇒ cancelled、不寫結果檔）。
- 啟動時新實例讀回紀錄，未終態者標 interrupted（附原因），終態者不動。
同步一律以 threading.Event 驅動（無牆鐘逾時、無 sleep）；`store.wait()` 為 Event 等待至終態。
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from api.core.background_jobs import BackgroundJobStore, JobCancelled, JobResultUnavailable

REQUIRED_KEYS = {"task_id", "kind", "state", "progress", "error", "created_at"}
PROGRESS_KEYS = {"phase", "processed", "total", "updated_at"}


def _disk(root: Path, job_id: str) -> Dict[str, Any]:
    """直接讀紀錄檔（不經 store），驗證狀態確實落盤。"""
    return json.loads((root / f"{job_id}.json").read_text(encoding="utf-8"))


def _result_path(root: Path, job_id: str) -> Path:
    return root / f"{job_id}.result.json"


def test_state_machine_queued_running_completed(tmp_path: Path) -> None:
    """create ⇒ queued（落盤）；start ⇒ 於 daemon 執行緒執行、fn 被呼叫前已為 running（落盤）；回傳 ⇒ completed＋結果檔。"""
    store = BackgroundJobStore(tmp_path)
    jid = store.create("coverage_matrix", {"symbols": ["BTCUSDT", "ETHUSDT"], "timeframe": "12h"})
    assert isinstance(jid, str) and jid
    rec = store.get(jid)
    assert rec is not None and REQUIRED_KEYS <= set(rec)
    assert rec["task_id"] == jid and rec["kind"] == "coverage_matrix" and rec["state"] == "queued"
    assert rec["error"] is None
    datetime.fromisoformat(rec["created_at"])
    assert _disk(tmp_path, jid)["state"] == "queued"

    entered, go = threading.Event(), threading.Event()
    seen: Dict[str, Any] = {}

    def fn(ctx: Any) -> Dict[str, Any]:
        seen["daemon"] = threading.current_thread().daemon
        seen["is_main"] = threading.current_thread() is threading.main_thread()
        seen["state_at_entry"] = _disk(tmp_path, jid)["state"]
        entered.set()
        go.wait()
        return {"answer": [1, 2, 3]}

    store.start(jid, fn)
    try:
        entered.wait()
        assert store.get(jid)["state"] == "running"
        assert _disk(tmp_path, jid)["state"] == "running"
        assert not _result_path(tmp_path, jid).exists()
    finally:
        go.set()
    final = store.wait(jid)
    assert final["state"] == "completed"
    assert seen == {"daemon": True, "is_main": False, "state_at_entry": "running"}
    assert store.read_result(jid) == {"answer": [1, 2, 3]}
    assert json.loads(_result_path(tmp_path, jid).read_text(encoding="utf-8")) == {"answer": [1, 2, 3]}
    assert _disk(tmp_path, jid)["state"] == "completed"


def test_progress_monotonic_and_persisted_with_updated_at(tmp_path: Path) -> None:
    """progress 落盤（phase／processed／total／updated_at ISO）；processed 相等允許、減少 ⇒ ValueError 且紀錄不倒退。"""
    store = BackgroundJobStore(tmp_path)
    jid = store.create("group_feature_coverage", {})
    at_step, go = threading.Event(), threading.Event()
    outcome: List[str] = []

    def fn(ctx: Any) -> Dict[str, bool]:
        ctx.progress("load", 1, 4)
        ctx.progress("load", 2, 4)
        ctx.progress("load", 2, 4)  # 相等：不減，允許
        at_step.set()
        go.wait()
        try:
            ctx.progress("load", 1, 4)
        except ValueError:
            outcome.append("decrease_rejected")
        ctx.progress("load", 4, 4)
        return {"ok": True}

    store.start(jid, fn)
    try:
        at_step.wait()
        disk = _disk(tmp_path, jid)
        assert PROGRESS_KEYS <= set(disk["progress"])
        assert (disk["progress"]["phase"], disk["progress"]["processed"], disk["progress"]["total"]) == ("load", 2, 4)
        assert datetime.fromisoformat(disk["progress"]["updated_at"]) >= datetime.fromisoformat(disk["created_at"])
        assert store.get(jid)["progress"]["processed"] == 2
    finally:
        go.set()
    final = store.wait(jid)
    assert outcome == ["decrease_rejected"]
    assert final["state"] == "completed"
    assert (final["progress"]["processed"], final["progress"]["total"]) == (4, 4)
    assert _disk(tmp_path, jid)["progress"]["processed"] == 4


def test_every_write_is_atomic_via_os_replace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """紀錄檔與結果檔一律「同目錄暫存檔寫全 → os.replace」：暫存內容於 replace 前即為完整 JSON、目的檔任何時刻皆完整；
    結果檔先於 completed 紀錄落盤；結束後目錄無殘留暫存檔。"""
    real_replace = os.replace
    calls: List[Tuple[Path, Path, str]] = []

    def spy(src: Any, dst: Any, *args: Any, **kwargs: Any) -> None:
        src_p, dst_p = Path(src), Path(dst)
        content = src_p.read_text(encoding="utf-8")
        json.loads(content)  # 暫存檔已完整（非半寫）
        if dst_p.exists():
            json.loads(dst_p.read_text(encoding="utf-8"))  # 目的檔於覆寫前亦完整
        calls.append((src_p, dst_p, content))
        real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "replace", spy)
    store = BackgroundJobStore(tmp_path)
    jid = store.create("coverage_matrix", {"n": 1})

    def fn(ctx: Any) -> Dict[str, int]:
        ctx.progress("scan", 1, 2)
        ctx.progress("scan", 2, 2)
        return {"rows": 2}

    store.start(jid, fn)
    assert store.wait(jid)["state"] == "completed"

    for src, dst, _ in calls:
        assert src != dst and src.parent == dst.parent, (src, dst)
    record_writes = [json.loads(c) for _, d, c in calls if d.name == f"{jid}.json"]
    states = [r["state"] for r in record_writes]
    assert states[0] == "queued" and states[-1] == "completed" and "running" in states, states
    assert {1, 2} <= {r["progress"]["processed"] for r in record_writes}
    names = [d.name for _, d, _ in calls]
    assert f"{jid}.result.json" in names
    last_completed = max(i for i, (_, d, c) in enumerate(calls)
                         if d.name == f"{jid}.json" and json.loads(c)["state"] == "completed")
    assert names.index(f"{jid}.result.json") < last_completed
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([f"{jid}.json", f"{jid}.result.json"])


def test_cancel_running_takes_effect_at_safe_point(tmp_path: Path) -> None:
    """running 取消 ⇒ 回 "cancelling"、紀錄為 cancelling；fn 到下一安全點 check_cancel 即拋 JobCancelled ⇒ cancelled，不寫結果。"""
    store = BackgroundJobStore(tmp_path)
    jid = store.create("group_feature_coverage", {})
    at_step, go = threading.Event(), threading.Event()
    after: List[str] = []

    def fn(ctx: Any) -> Dict[str, str]:
        ctx.progress("scan", 1, 3)
        at_step.set()
        go.wait()
        ctx.check_cancel()  # 安全點
        after.append("past_safe_point")
        return {"should": "not be saved"}

    store.start(jid, fn)
    try:
        at_step.wait()
        assert store.cancel(jid) == "cancelling"
        assert store.get(jid)["state"] == "cancelling"
        assert _disk(tmp_path, jid)["state"] == "cancelling"
    finally:
        go.set()
    final = store.wait(jid)
    assert final["state"] == "cancelled"
    assert after == []
    assert not _result_path(tmp_path, jid).exists()
    with pytest.raises(JobResultUnavailable):
        store.read_result(jid)
    assert store.cancel(jid) == "already_terminal"
    assert _disk(tmp_path, jid)["state"] == "cancelled"


def test_late_result_after_cancel_is_discarded(tmp_path: Path) -> None:
    """fn 已過最後安全點、回傳前才收到取消：提交結果前已請求取消 ⇒ 晚到結果丟棄、cancelled、無結果檔。"""
    store = BackgroundJobStore(tmp_path)
    jid = store.create("coverage_matrix", {})
    passed, go = threading.Event(), threading.Event()

    def fn(ctx: Any) -> Dict[str, bool]:
        ctx.check_cancel()  # 最後安全點：此時尚未請求取消
        passed.set()
        go.wait()
        return {"late": True}

    store.start(jid, fn)
    try:
        passed.wait()
        assert store.cancel(jid) == "cancelling"
    finally:
        go.set()
    final = store.wait(jid)
    assert final["state"] == "cancelled"
    assert not _result_path(tmp_path, jid).exists()
    with pytest.raises(JobResultUnavailable):
        store.read_result(jid)


def test_cancel_queued_is_immediate_and_unknown_raises(tmp_path: Path) -> None:
    """queued 取消 ⇒ 立即 "cancelled"（落盤）；再取消 ⇒ "already_terminal"；未知 job ⇒ KeyError／get 回 None。"""
    store = BackgroundJobStore(tmp_path)
    jid = store.create("group_coverage", {})
    assert store.cancel(jid) == "cancelled"
    assert store.get(jid)["state"] == "cancelled"
    assert _disk(tmp_path, jid)["state"] == "cancelled"
    assert store.cancel(jid) == "already_terminal"
    assert store.get("no-such-job") is None
    with pytest.raises(KeyError):
        store.cancel("no-such-job")
    with pytest.raises(KeyError):
        store.read_result("no-such-job")


def test_failed_path_records_error(tmp_path: Path) -> None:
    """fn 拋一般例外 ⇒ failed、error 帶訊息、無結果檔、read_result 拒；已終態取消 ⇒ already_terminal。"""
    store = BackgroundJobStore(tmp_path)
    jid = store.create("coverage_matrix", {})

    def fn(ctx: Any) -> None:
        ctx.progress("scan", 1, 2)
        raise RuntimeError("boom-L1c")

    store.start(jid, fn)
    final = store.wait(jid)
    assert final["state"] == "failed"
    assert "boom-L1c" in str(final["error"])
    assert _disk(tmp_path, jid)["state"] == "failed"
    assert not _result_path(tmp_path, jid).exists()
    with pytest.raises(JobResultUnavailable):
        store.read_result(jid)
    assert store.cancel(jid) == "already_terminal"


def test_fn_raising_job_cancelled_is_cancelled(tmp_path: Path) -> None:
    """fn 自行拋 JobCancelled（例：分析器之 on_step 安全點）⇒ cancelled，非 failed。"""
    store = BackgroundJobStore(tmp_path)
    jid = store.create("coverage_matrix", {})

    def fn(ctx: Any) -> None:
        raise JobCancelled("由安全點拋出")

    store.start(jid, fn)
    final = store.wait(jid)
    assert final["state"] == "cancelled"
    assert not _result_path(tmp_path, jid).exists()


def test_startup_marks_non_terminal_as_interrupted(tmp_path: Path) -> None:
    """前一實例留下之 queued／running／cancelling 紀錄，新實例 mark_interrupted_on_startup ⇒ interrupted（error 寫原因、落盤）；
    completed／failed 不動且結果可由新實例讀回；第二次呼叫回 0。"""
    prev = BackgroundJobStore(tmp_path)
    queued = prev.create("k", {})
    running = prev.create("k", {})
    cancelling = prev.create("k", {})
    done = prev.create("k", {})
    failed = prev.create("k", {})

    gate = threading.Event()
    entered_running, entered_cancelling = threading.Event(), threading.Event()

    def hold(entered: threading.Event):
        def fn(ctx: Any) -> None:
            entered.set()
            gate.wait()
            ctx.check_cancel()
        return fn

    def boom(ctx: Any) -> None:
        raise RuntimeError("x")

    try:
        prev.start(running, hold(entered_running))
        prev.start(cancelling, hold(entered_cancelling))
        entered_running.wait()
        entered_cancelling.wait()
        assert prev.cancel(cancelling) == "cancelling"
        prev.start(done, lambda ctx: {"v": 1})
        prev.start(failed, boom)
        assert prev.wait(done)["state"] == "completed"
        assert prev.wait(failed)["state"] == "failed"

        fresh = BackgroundJobStore(tmp_path)  # 模擬 API 重啟：新實例讀回同目錄
        assert fresh.get(running)["state"] == "running"
        assert fresh.mark_interrupted_on_startup() == 3
        for jid in (queued, running, cancelling):
            rec = fresh.get(jid)
            assert rec["state"] == "interrupted", jid
            assert isinstance(rec["error"], str) and rec["error"].strip(), rec
            assert _disk(tmp_path, jid)["state"] == "interrupted"
        assert fresh.get(done)["state"] == "completed"
        assert fresh.read_result(done) == {"v": 1}
        assert fresh.get(failed)["state"] == "failed"
        with pytest.raises(JobResultUnavailable):
            fresh.read_result(running)
        assert fresh.mark_interrupted_on_startup() == 0
    finally:
        gate.set()


def test_read_result_only_for_completed(tmp_path: Path) -> None:
    """queued 與 running 皆不可讀結果（JobResultUnavailable）；completed 可讀。"""
    store = BackgroundJobStore(tmp_path)
    jid = store.create("k", {})
    with pytest.raises(JobResultUnavailable):
        store.read_result(jid)
    entered, go = threading.Event(), threading.Event()

    def fn(ctx: Any) -> List[int]:
        entered.set()
        go.wait()
        return [7]

    store.start(jid, fn)
    try:
        entered.wait()
        with pytest.raises(JobResultUnavailable):
            store.read_result(jid)
    finally:
        go.set()
    store.wait(jid)
    assert store.read_result(jid) == [7]
