"""ICFIRSTALIGN 乙 Task 4.2 子行程預算域（docs/ICFIRSTALIGN_SPEC.md v27 驗證 (a)–(o)、(t)、(u)）。

以注入讀數與估算之純函式／狀態機為主（秒級）；排程器之 executor 以行程內執行緒池注入，任務以事件控制完成時序。
三入口接線以 AST 與輕量 spy 驗（不跑完整生成）；需真實子行程者限標準庫 spawn 探針（峰值遠低於 1 GB）。
實作前應為紅：`memory_budget` 之域函式與排程器為空殼（NotImplementedError），三入口仍直接建立 `ProcessPoolExecutor`。
數值單位為任意整數（只模擬資源讀數與排程，不涉市場資料）。
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pytest

from momentum.FeatureEngineering import memory_budget as mb
from tests.feature_engineering import icfirstalign_helpers as h

pytestmark = pytest.mark.timeout(120)

GiB = 1 << 30
MiB = 1 << 20


def _thread_identity() -> Tuple[int, float]:
    """行程內執行緒池測試之任務身分：以執行緒識別代 pid（避免與根同 pid 而被去重）。"""
    return (10 ** 9 + threading.get_ident() % 10 ** 6, 0.0)


def _m(pid: int, footprint: int, envelope: Optional[int] = None, role: str = "task") -> mb.Member:
    return mb.Member(pid=pid, start_time=float(pid), footprint=footprint, envelope=envelope, role=role)


def _state(budget: int, members: Sequence[mb.Member], slots: Sequence[mb.Slot] = (), absorbable: int = 10 ** 12,
           pressure: int = 1, stop: bool = False) -> mb.AdmissionState:
    return mb.AdmissionState(budget=budget, members=tuple(members), slots=tuple(slots), absorbable=absorbable,
                             pressure_level=pressure, stop_flag=stop)


# ---------------------------------------------------------------- 承諾量與准入（純函式）

def test_realized_commitment_not_double_counted() -> None:
    """(d) F 200／E 200 只計 200。"""
    assert mb.commitment(_m(2, 200, 200)) == 200
    assert mb.commitment(_m(2, 150, 200)) == 200
    assert mb.commitment(_m(2, 250, 200)) == 250
    assert mb.commitment(_m(2, 20, None)) == 20


def test_mutation_commitment_f_plus_e(monkeypatch: pytest.MonkeyPatch) -> None:
    """(d) mutant「U＝F＋E」⇒ 已實現之配置雙計，准入誤拒。"""
    monkeypatch.setattr(mb, "commitment", lambda m: m.footprint + (m.envelope or 0))
    state = _state(450, [_m(1, 50, role="root"), _m(2, 200, 200)])
    assert mb.admit(state, 150).ok is False  # 正確應為 50＋200＋150＝400 ≤ 450 放行


def test_completion_releases_envelope_without_next_check() -> None:
    """(c) A 任務完成（envelope 撤銷）而存活 F 20、根 50、新任務 150、B 350 ⇒ 立即准入（r25 兩家誤拒反例）。"""
    state = _state(350, [_m(1, 50, role="root"), _m(2, 20, None)])
    assert mb.admit(state, 150) == mb.Admission(ok=True, reason="ok")


def test_kept_envelope_would_refuse() -> None:
    """(c) 對照：若完成後仍保留 E（v24 殘留型實作）⇒ 400 > 350 誤拒——正確實作須於 completed 撤 E。"""
    state = _state(350, [_m(1, 50, role="root"), _m(2, 20, 200)])
    assert mb.admit(state, 150).ok is False  # 保留 E 之狀態即被拒：正確實作須於完成時撤 E（見 (c) 排程案例）


def test_active_peak_not_stolen() -> None:
    """(e) A 活動中 F 20／E 200 ⇒ 仍計 200；根 50、新 150、B 350 ⇒ 不准入。"""
    state = _state(350, [_m(1, 50, role="root"), _m(2, 20, 200)])
    assert mb.admit(state, 150) == mb.Admission(ok=False, reason="budget")


def test_mutation_active_counts_only_footprint(monkeypatch: pytest.MonkeyPatch) -> None:
    """(e) mutant「活動只計 F」⇒ 同狀態被放行。"""
    monkeypatch.setattr(mb, "commitment", lambda m: m.footprint)
    state = _state(350, [_m(1, 50, role="root"), _m(2, 20, 200)])
    assert mb.admit(state, 150).ok is True


def test_starting_slots_counted_in_absorbable() -> None:
    """(t) 根與輔助 20、B 200、可吸收量 90、A 啟動槽 E 60（尚無 pid）、新任務 E 60 ⇒ 新增量 120 > 90 不准入。"""
    state = _state(200, [_m(1, 20, role="root")], slots=[mb.Slot("A", 60)], absorbable=90)
    assert mb.admit(state, 60) == mb.Admission(ok=False, reason="absorbable")
    assert mb.admit(_state(200, [_m(1, 20, role="root")], absorbable=90), 60).ok is True


def test_mutation_absorbable_ignores_slots(monkeypatch: pytest.MonkeyPatch) -> None:
    """(t) mutant「系統式漏啟動槽」⇒ 放行而紅（以去槽之狀態代入同一判定）。"""
    real = mb.admit
    monkeypatch.setattr(mb, "admit", lambda state, e, d=0: real(
        mb.AdmissionState(state.budget, state.members, (), state.absorbable, state.pressure_level, state.stop_flag), e))
    state = _state(200, [_m(1, 20, role="root")], slots=[mb.Slot("A", 60)], absorbable=90)
    assert mb.admit(state, 60).ok is True


def test_stop_flag_is_admission_conjunct() -> None:
    """r27：停止旗標與 B 式同一准入合取（一般並行准入亦受約束）。"""
    state = _state(10 ** 6, [_m(1, 10, role="root")], stop=True)
    assert mb.admit(state, 1) == mb.Admission(ok=False, reason="stop_flag")


def test_pressure_not_admission_conjunct() -> None:
    """SPEC v36（審碼 r32 composer P1-02）：壓力等級 4 而新增量 ≤ A ⇒ 准入（壓力只記錄）。"""
    state = _state(10 ** 6, [_m(1, 10, role="root")], pressure=4)
    assert mb.admit(state, 1) == mb.Admission(ok=True, reason="ok")


def test_mutation_admission_refuses_on_pressure(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant「准入仍因壓力 4 拒絕」⇒ 上案例紅。"""
    real = mb.admit
    monkeypatch.setattr(mb, "admit", lambda state, e, d=0: mb.Admission(False, "pressure")
                        if state.pressure_level >= 4 else real(state, e, d))
    state = _state(10 ** 6, [_m(1, 10, role="root")], pressure=4)
    assert mb.admit(state, 1).ok is False


def test_disk_admission_counts_concurrent_writers() -> None:
    """SPEC v37（審碼 r33 codex P1-02）：同容器已准入任務之寫入上界 D＋新任務 D＋保留量 ≤ 換頁卷可用空間；兩任務各
    D＝4 GiB、可用 8 GiB、保留 4 GiB ⇒ 第二任務不准入；單任務 ⇒ 准入。"""
    base = dict(budget=10 ** 15, members=(_m(1, 10, role="root"),), slots=(), absorbable=10 ** 15, pressure_level=1,
                stop_flag=False, disk_free=8 * GiB, disk_reserve=4 * GiB)
    assert mb.admit(mb.AdmissionState(**base, disk_committed=0), 1, 4 * GiB).ok is True
    assert mb.admit(mb.AdmissionState(**base, disk_committed=4 * GiB), 1, 4 * GiB) == \
        mb.Admission(ok=False, reason="disk")


def test_mutation_admission_ignores_disk(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant「准入不判 D」⇒ 第二任務准入、合計超額而紅。"""
    real = mb.admit
    monkeypatch.setattr(mb, "admit", lambda state, e, d=0: real(
        mb.AdmissionState(state.budget, state.members, state.slots, state.absorbable, state.pressure_level,
                          state.stop_flag), e))
    state = mb.AdmissionState(budget=10 ** 15, members=(_m(1, 10, role="root"),), slots=(), absorbable=10 ** 15,
                              pressure_level=1, stop_flag=False, disk_free=8 * GiB, disk_reserve=4 * GiB,
                              disk_committed=4 * GiB)
    assert mb.admit(state, 1, 4 * GiB).ok is True


def test_members_deduplicated_by_pid_and_start_time() -> None:
    """成員以 (pid, start_time) 去重；pid 重用（start_time 不同）不繼承舊承諾。"""
    dup = [_m(1, 40, role="root"), _m(1, 40, role="root"), _m(7, 6, role="guard")]
    assert mb.measured_total(dup) == 46
    reused = [mb.Member(pid=9, start_time=1.0, footprint=5), mb.Member(pid=9, start_time=2.0, footprint=8)]
    assert mb.measured_total(reused) == 13


def test_guard_tracker_counted_once() -> None:
    """(i) 根 40、worker 50、守護 6 ⇒ 實測合計 96（以 (pid, start_time) 去重，守護與 tracker 只計一次；收據用）。"""
    members = [_m(1, 40, role="root"), _m(2, 50), _m(3, 6, role="guard")]
    assert mb.measured_total(members) == 96


def test_guard_stop_conditions_are_disk_and_paging_only() -> None:
    """SPEC v35–v39：守護停止條件只看換頁卷剩餘 < 保留量、A < 一頁；footprint 與承諾量不作停止條件（v35 起，原
    「以 F 對 B 判停」之 (i) 案例與其 mutant 隨之取代）。"""
    assert mb.guard_should_stop(75 * GiB, 4 * GiB, available=10 * GiB) is None
    assert mb.guard_should_stop(GiB, 4 * GiB, available=10 * GiB) == "swap_volume_low"
    assert mb.guard_should_stop(75 * GiB, 4 * GiB, available=0) == "paging_exhausted"
    assert mb.guard_should_stop(75 * GiB, 4 * GiB, available=512 * MiB) is None  # 正餘裕（v38）


def test_mutation_guard_paging_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant「A 小於一個換頁檔即停」（v37 前之地板）⇒ 正餘裕 512 MiB 誤停而紅。"""
    monkeypatch.setattr(mb, "guard_should_stop", lambda free, reserve, available=None, page_size=16384:
                        "paging_exhausted" if available is not None and available < GiB else None)
    assert mb.guard_should_stop(75 * GiB, 4 * GiB, available=512 * MiB) == "paging_exhausted"


def test_guard_script_does_not_import_psutil() -> None:
    """(i) 守護腳本只用標準函式庫與 ctypes（libproc 列子行程），不 import psutil。"""
    tree = ast.parse((h.REPO / h.CONTRACT["guard_script"]).read_text(encoding="utf-8"))
    mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    mods |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert "psutil" not in mods


# ---------------------------------------------------------------- worker 配置點（估算低估）

def _descriptor(tmp_path: Path, envelope: int, task_id: str = "T") -> mb.DomainDescriptor:
    return mb.DomainDescriptor(root_pid=os.getpid(), domain_dir=tmp_path, budget=10 ** 12, task_id=task_id,
                               envelope=envelope)


@pytest.mark.parametrize("room", [True, False], ids=["global_room", "no_room"])
def test_worker_estimate_exceeded_refuses_without_wait(tmp_path: Path, room: bool) -> None:
    """(n) 候選 F＋planned > E ⇒ 不論全域有無餘裕，記 `memory_estimate_exceeded` 並具名錯誤（估算低估），不等待、不擴大。"""
    with mb.sampler_override(lambda: {"resident": 100, "phys_footprint": 100}), \
            mb.budget_override(10 ** 12 if room else 300):
        with pytest.raises(mb.GenerationMemoryBudgetExceeded) as info:
            mb.check("L3.numba_multi_callback", [mb.Component("fused_x2", "anon", 200)],
                     domain=_descriptor(tmp_path, envelope=250))
    assert "估算低估" in str(info.value)
    assert isinstance(info.value, mb.MemoryRerouteNeeded)  # SPEC v35：交根於波次 join 後以正式串行臂重試
    assert (tmp_path / h.CONTRACT["guard_files"]["estimate_exceeded_log"]).exists()


def test_two_workers_exceeding_both_refused(tmp_path: Path) -> None:
    """(n) 兩 worker 同時超出各自 E ⇒ 兩者皆具名錯誤；無「有餘裕則擴大」路徑可使終態超 B。"""
    errors = []
    barrier = threading.Barrier(2)

    def worker(task_id: str) -> None:
        barrier.wait()
        try:
            with mb.sampler_override(lambda: {"resident": 10, "phys_footprint": 10}), mb.budget_override(10 ** 12):
                mb.check("L4", [mb.Component("output", "anon", 60)], domain=_descriptor(tmp_path, 50, task_id))
        except mb.GenerationMemoryBudgetExceeded as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(t,)) for t in ("A", "B")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert len(errors) == 2


# ---------------------------------------------------------------- 排程器（行程內執行緒池、事件控制）

class _Harness:
    """注入讀數之排程器測試台：任務 F 由測試設定；任務本體等事件放行。"""

    def __init__(self, budget: int, root: int, *, domain_dir: Path, absorbable: int = 10 ** 12, max_workers: int = 4,
                 aux: Optional[int] = 0, executor_factory: Any = None) -> None:
        self.root = root
        self.absorbable = absorbable
        self.footprints: Dict[str, int] = {}
        self.events: Dict[str, threading.Event] = {}
        self.running: List[str] = []
        self.max_concurrent = 0
        self.serial: List[Any] = []
        self.waves: List[List[Any]] = []
        self.executors = 0
        self._lock = threading.Lock()

        def factory(n: int) -> Any:
            self.executors += 1
            return (executor_factory or ThreadPoolExecutor)(n)

        self.scheduler = mb.MemoryBudgetScheduler(
            budget, domain_dir=domain_dir, max_workers=max_workers, executor_factory=factory,
            read_system=lambda: (self.absorbable, 1, False, self.root, ()),
            read_task_footprint=lambda tid: self.footprints.get(tid, 0), aux_startup_envelope=aux,
            task_identity=_thread_identity)

    def worker(self, domain: mb.DomainDescriptor, payload: Any) -> Any:
        tid = domain.task_id
        with self._lock:
            self.running.append(tid)
            self.max_concurrent = max(self.max_concurrent, len(self.running))
        self.events.setdefault(tid, threading.Event()).wait(10)
        with self._lock:
            self.running.remove(tid)
        return ("parallel", tid)

    def serial_fn(self, payload: Any) -> Any:
        self.serial.append(payload)
        return ("serial", payload)

    def run(self, tasks: Sequence[mb.Task]) -> List[Any]:
        for t in tasks:
            self.events.setdefault(t.task_id, threading.Event())
        return self.scheduler.run(tasks, self.worker, self.serial_fn, lambda results: self.waves.append(list(results)))

    def wave_sizes(self) -> List[int]:
        """由 trace 決定性地取各波准入數（不依執行緒時序）。"""
        sizes, cur = [], 0
        for event, _ in self.scheduler.trace:
            if event == "admitted":
                cur += 1
            elif event == "wave_joined":
                sizes.append(cur)
                cur = 0
        return sizes


def _release_in_order(hz: _Harness, order: Sequence[str], delay: float = 0.2) -> threading.Thread:
    def go() -> None:
        for tid in order:
            threading.Event().wait(delay)
            hz.events[tid].set()
    t = threading.Thread(target=go, daemon=True)
    t.start()
    return t


def test_parallel_shortage_queues_not_rejects(tmp_path: Path) -> None:
    """(a) 兩任務 E 各 60、根 20、B 100 ⇒ 一波只准入一個、另一個 queued 至下一波；全程無拒絕、不走串行臂。"""
    hz = _Harness(100, 20, domain_dir=tmp_path)
    _release_in_order(hz, ["A", "B"])
    results = hz.run([mb.Task("A", 60), mb.Task("B", 60)])
    assert sorted(results) == [("parallel", "A"), ("parallel", "B")]
    assert hz.wave_sizes() == [1, 1]
    events = [e for e, _ in hz.scheduler.trace]
    assert "queued" in events and "refused" not in events and "serial" not in events


def test_no_worker_internal_wait_cycle(tmp_path: Path) -> None:
    """(b) A、B 各持 40 再需 30（任務 E 70）、根 0、B 100 ⇒ 准入端序列化（每波一個），兩者完成。"""
    hz = _Harness(100, 0, domain_dir=tmp_path)
    _release_in_order(hz, ["A", "B"])
    results = hz.run([mb.Task("A", 70), mb.Task("B", 70)])
    assert len(results) == 2 and hz.wave_sizes() == [1, 1]


def test_mutation_admission_by_footprint_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(b) mutant「准入只看當下 F（不計活動 E）」⇒ A、B 同一波准入（其後於配置點互等）。"""
    monkeypatch.setattr(mb, "commitment", lambda m: m.footprint)
    hz = _Harness(100, 0, domain_dir=tmp_path)
    _release_in_order(hz, ["A", "B"])
    hz.run([mb.Task("A", 70), mb.Task("B", 70)])
    assert hz.wave_sizes() == [2]


def test_idle_allocator_reclaimed_before_serial_decision(tmp_path: Path) -> None:
    """(f) 完成之 worker F 仍 200（allocator 未歸還）、根 50、B 350 ⇒ 該波 join 後（成員移除）新任務 150 方准入，無誤拒。"""
    hz = _Harness(350, 50, domain_dir=tmp_path, max_workers=1)
    hz.footprints["A"] = 200
    _release_in_order(hz, ["A", "B"])
    results = hz.run([mb.Task("A", 200), mb.Task("B", 150)])
    assert sorted(results) == [("parallel", "A"), ("parallel", "B")]
    trace = hz.scheduler.trace
    assert trace.index(("joined", "A")) < trace.index(("admitted", "B"))


def test_completed_task_counts_footprint_only_before_join(tmp_path: Path) -> None:
    """(c)(f) 實際生命週期：同波 A（E 200）完成而 B 仍運行時，A 之成員承諾＝其實測 F（200，allocator 未歸還），
    envelope 已撤（None）；join 後 A 移出成員。"""
    hz = _Harness(10 ** 6, 10, domain_dir=tmp_path, max_workers=2)
    hz.footprints["A"] = 200
    hz.footprints["B"] = 30
    seen: Dict[str, Any] = {}

    def observe() -> None:
        hz.events.setdefault("A", threading.Event()).set()
        for _ in range(500):
            if ("completed", "A") in hz.scheduler.trace:
                seen["mid"] = hz.scheduler.snapshot()
                break
            threading.Event().wait(0.01)
        hz.events.setdefault("B", threading.Event()).set()

    threading.Thread(target=observe, daemon=True).start()
    hz.run([mb.Task("A", 200), mb.Task("B", 50)])
    task_members = [m for m in seen["mid"].members if m.role == "task"]
    a = [m for m in task_members if m.footprint == 200]
    assert len(a) == 1 and a[0].envelope is None and mb.commitment(a[0]) == 200
    assert [m.envelope for m in task_members if m.footprint == 30] == [50]
    assert not [m for m in hz.scheduler.snapshot().members if m.role == "task"]


def test_empty_wave_falls_back_to_formal_serial(tmp_path: Path) -> None:
    """(g) 任務 E 100 加根 20 > B 75 ⇒ 根行程內走串行臂、executor 建立 0 次、無拒絕。"""
    hz = _Harness(75, 20, domain_dir=tmp_path)
    results = hz.run([mb.Task("A", 100, payload="A-payload")])
    assert results == [("serial", "A-payload")]
    assert hz.executors == 0
    assert ("serial", "A") in hz.scheduler.trace and ("refused", "A") not in hz.scheduler.trace


def test_task_without_shape_goes_serial(tmp_path: Path) -> None:
    """形狀不可得（envelope None）⇒ 不准入並行、走串行臂。"""
    hz = _Harness(10 ** 6, 1, domain_dir=tmp_path)
    assert hz.run([mb.Task("A", None, payload="p")]) == [("serial", "p")]


def test_start_slot_pid_transition_exactly_once(tmp_path: Path) -> None:
    """(h) 經 `run` 之真實任務生命週期：任務 A（E 100、F 5）於 starting（執行器尚未啟動其本體）時以啟動槽計 E；
    worker 本體開始後（已綁 pid）以成員 max(F, E) 計；兩側承諾皆＝根 10＋100（不兩份、不零份、不以 F 代 E）。"""
    gate = threading.Event()
    seen: Dict[str, Any] = {}

    class DelayedStartExecutor(ThreadPoolExecutor):
        def submit(self, fn: Any, *a: Any, **k: Any) -> Any:
            def delayed() -> Any:
                gate.wait(10)
                return fn(*a, **k)
            return super().submit(delayed)

    sched = mb.MemoryBudgetScheduler(1000, domain_dir=tmp_path, max_workers=1, executor_factory=DelayedStartExecutor,
                                     read_system=lambda: (10 ** 9, 1, False, 10, ()),
                                     read_task_footprint=lambda tid: 5, aux_startup_envelope=0,
                                     task_identity=_thread_identity)

    def total(s: mb.AdmissionState) -> int:
        return sum(mb.commitment(m) for m in s.members) + sum(sl.envelope for sl in s.slots)

    def worker(domain: mb.DomainDescriptor, payload: Any) -> Any:
        seen["after"] = sched.snapshot()
        return domain.task_id

    def observe() -> None:
        for _ in range(200):
            snap = sched.snapshot()
            if any(sl.slot_id == "A" for sl in snap.slots):
                seen["before"] = snap
                break
            threading.Event().wait(0.01)
        gate.set()

    threading.Thread(target=observe, daemon=True).start()
    assert sched.run([mb.Task("A", 100)], worker, lambda p: p, lambda r: None) == ["A"]
    before, after = seen["before"], seen["after"]
    assert [sl.envelope for sl in before.slots if sl.slot_id == "A"] == [100]
    assert not [sl for sl in after.slots if sl.slot_id == "A"]
    assert [m.envelope for m in after.members if m.role == "task"] == [100]
    assert total(before) == total(after) == 10 + 100


def test_root_alignment_after_wave_join(tmp_path: Path) -> None:
    """(m) `on_wave_joined` 於該波全部任務 joined 之後才呼叫（根對齊不與 worker 重疊）。"""
    hz = _Harness(10 ** 6, 1, domain_dir=tmp_path, max_workers=2)
    _release_in_order(hz, ["A", "B"])
    hz.run([mb.Task("A", 10), mb.Task("B", 10)])
    trace = hz.scheduler.trace
    wave = trace.index(("wave_joined", ""))
    assert trace.index(("joined", "A")) < wave and trace.index(("joined", "B")) < wave
    assert hz.waves and sorted(hz.waves[0]) == [("parallel", "A"), ("parallel", "B")]


@pytest.mark.parametrize("gib", [8, 16, 32, 64])
def test_larger_physical_memory_changes_admission(tmp_path: Path, gib: int) -> None:
    """(o) B＝0.75 × 實體記憶體；8 個任務（E 3 GiB、根 1 GiB）之首波准入數＝min(8, ⌊(B−根)/E⌋)，隨記憶體單調不減。"""
    budget = int(0.75 * gib * GiB)
    hz = _Harness(budget, 1 * GiB, domain_dir=tmp_path, max_workers=8)
    _release_in_order(hz, [f"T{i}" for i in range(8)], delay=0.01)
    hz.run([mb.Task(f"T{i}", 3 * GiB) for i in range(8)])
    expected = min(8, (budget - 1 * GiB) // (3 * GiB))
    assert hz.wave_sizes()[0] == expected


def test_aux_tracker_startup_slot(tmp_path: Path) -> None:
    """(u) 首次建立 executor 前登記輔助啟動槽；根 20、worker E 80、tracker 上界 5、B 100 ⇒ 不准入並行、走串行臂。"""
    hz = _Harness(100, 20, domain_dir=tmp_path / "a", aux=5)
    results = hz.run([mb.Task("A", 80, payload="p")])
    assert results == [("serial", "p")] and hz.executors == 0
    hz2 = _Harness(200, 20, domain_dir=tmp_path / "b", aux=5)
    _release_in_order(hz2, ["A"])
    hz2.run([mb.Task("A", 80)])
    trace = hz2.scheduler.trace
    assert trace.index(("aux_slot", "tracker")) < trace.index(("executor_created", ""))


def test_mutation_aux_slot_not_registered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(u) mutant「不登記輔助槽」（輔助上界視為 0）⇒ 同一情境（20＋80＋5 > 100）被准入並行。"""
    hz = _Harness(100, 20, domain_dir=tmp_path, aux=0)
    _release_in_order(hz, ["A"])
    hz.run([mb.Task("A", 80, payload="p")])
    assert hz.executors == 1


def test_aux_without_receipt_goes_serial(tmp_path: Path) -> None:
    """(u) 無輔助啟動上界收據（None）⇒ 並行計畫不可准入、走串行臂。"""
    hz = _Harness(10 ** 9, 1, domain_dir=tmp_path, aux=None)
    assert hz.run([mb.Task("A", 10, payload="p")]) == [("serial", "p")]


def test_real_spawn_tracker_is_separate_pid() -> None:
    """(u) 標準庫 spawn：首個 worker 提交後 resource tracker 為另一 pid（輔助槽之前提）。"""
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import resource_tracker

    ctx = mp.get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=ctx) as pool:
        worker_pid = pool.submit(os.getpid).result(timeout=60)
    tracker_pid = getattr(resource_tracker._resource_tracker, "_pid", None)
    assert tracker_pid is not None and tracker_pid not in (worker_pid, os.getpid())


# ---------------------------------------------------------------- 域描述（請求隔離）與三入口接線

def test_api_domain_descriptor_is_request_local(tmp_path: Path) -> None:
    """(k) 兩排程器並發：worker 收到之域描述屬其排程器（task_id 前綴、root_pid），且全程不寫行程全域環境變數。"""
    seen: Dict[str, List[str]] = {"X": [], "Y": []}
    env_before = dict(os.environ)

    def make(tag: str) -> Any:
        sched = mb.MemoryBudgetScheduler(10 ** 9, domain_dir=tmp_path / tag, max_workers=2,
                                         executor_factory=ThreadPoolExecutor,
                                         read_system=lambda: (10 ** 9, 1, False, 1, ()),
                                         read_task_footprint=lambda tid: 1, aux_startup_envelope=0,
                                         task_identity=_thread_identity)
        return sched.run([mb.Task(f"{tag}{i}", 10) for i in range(3)],
                         lambda d, p: seen[tag].append(d.task_id) or d.task_id, lambda p: p, lambda r: None)

    errors: List[BaseException] = []

    def guarded(tag: str) -> None:
        try:
            make(tag)
        except BaseException as exc:  # noqa: BLE001 — 收集後於主執行緒斷言
            errors.append(exc)

    threads = [threading.Thread(target=guarded, args=(t,)) for t in ("X", "Y")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert errors == []
    assert sorted(seen["X"]) == ["X0", "X1", "X2"] and sorted(seen["Y"]) == ["Y0", "Y1", "Y2"]
    assert dict(os.environ) == env_before


POOL_SITES = {
    "momentum/FeatureEngineering/timeframe/multi_tf_generator.py": "_generate_multi_tf_cgsa_parallel",
    "momentum/FeatureEngineering/feature_factory.py": "run_multi_symbol",
    "api/services/feature_factory_batch_service.py": "_process_item_wave",
}


@pytest.mark.parametrize("path,func", sorted(POOL_SITES.items()))
def test_three_generation_pools_join_same_domain(path: str, func: str) -> None:
    """(j) 三個生成 pool 之函式內不再直接建立 `ProcessPoolExecutor`，改經 `create_memory_budget_scheduler`。"""
    tree = ast.parse((h.REPO / path).read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == func)
    # r29：任何形式之引用皆不准（呼叫、別名賦值、函式內 import），別名繞過即紅；另由執行期案例核建構次數
    refs = [ast.unparse(n) for n in ast.walk(fn)
            if (isinstance(n, ast.Name) and n.id == "ProcessPoolExecutor")
            or (isinstance(n, ast.Attribute) and n.attr == "ProcessPoolExecutor")
            or (isinstance(n, ast.alias) and n.name == "ProcessPoolExecutor")]
    assert refs == [], f"{func} 仍引用 ProcessPoolExecutor：{refs}"
    calls = {ast.unparse(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)}
    assert any("create_memory_budget_scheduler" in c for c in calls)


def test_module_level_pool_alias_not_used_by_entries() -> None:
    """(j) 三入口所在模組之模組層 `ProcessPoolExecutor` 名稱不得被三入口以外之別名間接取用（模組內其他函式之別名指派亦禁）。"""
    for path in POOL_SITES:
        tree = ast.parse((h.REPO / path).read_text(encoding="utf-8"))
        aliases = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Assign)
                   and isinstance(n.value, (ast.Name, ast.Attribute))
                   and ast.unparse(n.value).endswith("ProcessPoolExecutor")]
        assert aliases == [], f"{path} 有 ProcessPoolExecutor 別名：{aliases}"


def test_factory_and_protocol_expose_scheduler() -> None:
    """(j) 排程器經 `momentum.factories.create_memory_budget_scheduler` 暴露、實作 `IMemoryBudgetScheduler`（R3）。"""
    from momentum import factories
    from momentum.core import protocols

    assert hasattr(protocols, "IMemoryBudgetScheduler")
    assert callable(getattr(factories, "create_memory_budget_scheduler"))


def test_api_batch_does_not_touch_domain_files() -> None:
    """解耦：API 批次服務不讀寫域檔、不自實作准入式（只經 factory／Protocol）。"""
    src = (h.REPO / "api/services/feature_factory_batch_service.py").read_text(encoding="utf-8")
    assert not [tok for tok in ("memory_domain", ".admit(", "commitment(", "AdmissionState(") if tok in src]
    assert "from api." not in "".join(p.read_text(encoding="utf-8") for p in (h.REPO / "momentum").rglob("memory_budget.py"))


def test_parallel_search_engine_named_exclusion() -> None:
    """`parallel_search_engine` 之 pool 為樣態搜尋（不呼叫特徵生成）：具名排除之前提——其 worker 不呼叫 `generate_features`。"""
    src = (h.REPO / "momentum/DataExtraction/parallel_search_engine.py").read_text(encoding="utf-8")
    assert "generate_features" not in src and "_tf_worker_entry" not in src


# ---------------------------------------------------------------- (l) worker 層結果之最後持有者（真實 kline、行程內呼叫）

WORKER_GOLD = __import__("json").loads((h.REPO / "tests/_golden/icfirstalign/worker_counts.json").read_text(encoding="utf-8"))


def _run_worker_inprocess(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, on_layer_start: Any) -> Dict[str, Any]:
    """S2m 之 4h worker 於本行程執行（峰值約 0.23 GB，HEAD 收據）；每層開始前呼叫 `on_layer_start(label, results)`。"""
    import weakref

    import scripts.freeze_icfirstalign_baseline as frz
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.timeframe.multi_tf_generator import _tf_worker_entry

    root = h.isolated(monkeypatch, tmp_path)
    monkeypatch.setenv("NUMBA_NUM_THREADS", os.environ.get("NUMBA_NUM_THREADS", "1"))
    refs: List[Tuple[str, Any]] = []
    real = FeatureFactory._execute_layer1_6_preserve_dtype

    def spy(self: Any, label: str, *a: Any, **k: Any) -> Any:
        on_layer_start(label, refs)
        out = real(self, label, *a, **k)
        data = getattr(out, "data", None)
        if data is not None:
            refs.append((label, weakref.ref(data)))
        return out

    monkeypatch.setattr(FeatureFactory, "_execute_layer1_6_preserve_dtype", spy)
    payload = h.make_factory(root)._resolve_config(h.s2_payload(["12h", "4h"])).model_dump(by_alias=True)
    result = _tf_worker_entry(h.SYMBOL, "4h", payload, h.S2_WINDOW[0], h.S2_WINDOW[1], cache_dir=str(h.KLINE_DIR))
    return {"result": result, "record": frz.worker_record(result), "refs": refs}


def test_worker_last_holder_and_metadata_conserved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(l) L3–L6 各層落盤後、下一層開始前，該層資料表已無持有者（weakref 失效）；worker 回傳之 counts／群組摘要與 HEAD 逐值相等。"""
    import gc

    alive_at: Dict[str, List[str]] = {}

    from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator

    holder: Dict[str, Any] = {}

    def on_start(label: str, refs: List[Tuple[str, Any]]) -> None:
        holder["refs"] = refs
        gc.collect()
        alive_at[label] = [lab for lab, r in refs if r() is not None and lab in ("Layer 3", "Layer 4", "Layer 5")]

    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

    tails: List[List[str]] = []

    def checkpoint() -> None:
        # r30：觀測點只在群組 payload 整理階段（`ColumnGroupRegistry.get`；位於 metadata 快照之後），且只以**最後一次**
        # 觀測判定——SPEC 合法順序為「L6 落盤 → 以仍存活之資料保存 counts／status／failed → 清除持有者 → 收集群組
        # metadata」，metadata 快照前之存活不得判紅（r29 版於快照前觀測會誤紅正確實作）。
        refs = holder.get("refs", [])
        if holder.get("l6_persisted"):
            gc.collect()
            tails.append([lab for lab, r in refs if r() is not None
                          and lab in ("Layer 3", "Layer 4", "Layer 5", "Layer 6")])

    real_get = ColumnGroupRegistry.get
    monkeypatch.setattr(ColumnGroupRegistry, "get", lambda self, gid: (checkpoint(), real_get(self, gid))[1])
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    real_persist = FeatureFactory._persist_layer_output_groups

    def persist(self: Any, frame: Any, *a: Any, **k: Any) -> Any:
        out = real_persist(self, frame, *a, **k)
        if "L6_meta" in [str(x) for x in a] + [str(v) for v in k.values()]:
            holder["l6_persisted"] = True
        return out

    monkeypatch.setattr(FeatureFactory, "_persist_layer_output_groups", persist)
    out = _run_worker_inprocess(tmp_path, monkeypatch, on_start)
    assert out["record"] == WORKER_GOLD["worker"]  # counts、failed_layers、layer_statuses、來源時間戳、群組摘要
    assert alive_at.get("Layer 4") == [] and alive_at.get("Layer 5") == [] and alive_at.get("Layer 6") == []
    assert tails, "須於 L6 落盤後觀測到群組 payload 整理點"
    assert tails[-1] == []  # 群組 payload 整理之最後一點：L3–L6 資料表皆已無持有者


def test_mutation_only_del_local_layer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(l) mutant「只 `del layerN`、`LayerResult.data` 仍持有」（HEAD 行為）⇒ Layer 4 開始時 Layer 3 資料仍存活。

    以 HEAD 之 `_tf_worker_entry` 執行即為此 mutant；實作後此測試以 monkeypatch 還原「保留 r3.data」之持有以重現。
    """
    import gc


    alive: Dict[str, bool] = {}
    keep: List[Any] = []

    def on_start(label: str, refs: List[Tuple[str, Any]]) -> None:
        gc.collect()
        if label == "Layer 4":
            alive["L3"] = any(lab == "Layer 3" and r() is not None for lab, r in refs)

    # b3 實作期：S2m 之 4h L3 為串流 offloaded（不經 `_persist_layer_output_groups`），原以「持有落盤之 frame」模擬
    # r3.data 殘留對 L3 無作用；改以實作之最後持有者清除接縫 `_release_layer_result` 還原為恆等（即 HEAD 之
    # 「只 del layerN、LayerResult.data 與 factory.layer_results 仍持有」）
    from momentum.FeatureEngineering.timeframe import multi_tf_generator as mtf

    monkeypatch.setattr(mtf, "_release_layer_result", lambda factory, name, result: result)
    _run_worker_inprocess(tmp_path, monkeypatch, on_start)
    assert alive.get("L3") is True
    assert keep == []


# ---------------------------------------------------------------- 真實入口接線（(g)(j)(q)(s)；精簡真實 kline，單組串行）
# 測試接縫：`ICFA_CHECK_LOG`（測試專用，spawn 子行程繼承）每行 JSON：event（check／admit／start_guard／executor_created／
# serial）、pid、root_pid、task_id、branch、F、planned、U、E、result。呼叫端於呼叫時解析
# `momentum.factories.create_memory_budget_scheduler`（函式內 import 或模組屬性），不得模組層綁名。

def _log_lines(path: Path) -> List[Dict[str, Any]]:
    import json as _json

    return [_json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()] if path.exists() else []


def _pool_constructions(monkeypatch: pytest.MonkeyPatch) -> Dict[str, int]:
    """計 `ProcessPoolExecutor` 之實際建構次數（任何別名皆經此 __init__）。"""
    from concurrent.futures import process as cfp

    count = {"n": 0}
    real_init = cfp.ProcessPoolExecutor.__init__

    def init(self: Any, *a: Any, **k: Any) -> None:
        count["n"] += 1
        real_init(self, *a, **k)

    monkeypatch.setattr(cfp.ProcessPoolExecutor, "__init__", init)
    return count


def _scheduler_spy(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> List[Any]:
    from momentum import factories

    created: List[Any] = []
    real = factories.create_memory_budget_scheduler

    def spy(**kw: Any) -> Any:
        kw.update(overrides)
        sched = real(**kw)
        created.append(sched)
        return sched

    monkeypatch.setattr(factories, "create_memory_budget_scheduler", spy)
    return created


def _raw_digests(root: Path, config_hash: str) -> Dict[str, str]:
    import scripts.freeze_icfirstalign_baseline as frz
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    reader = FeatureReader(str(root))
    manifest = reader.load_manifest_v2(h.SYMBOL, h.PRIMARY, config_hash, artifact_kind="raw")
    cols = sorted(c for g in manifest["artifacts"]["raw"]["groups"].values() for c in g.get("columns", []))
    frame = reader.load_columns_v2(h.SYMBOL, h.PRIMARY, config_hash, cols)
    return {c: frz.column_digest(frame[c].to_numpy()) for c in cols}


def _mtf_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **spy_overrides: Any) -> Dict[str, Any]:
    from momentum.FeatureEngineering import memory_budget as _mb

    root = h.isolated(monkeypatch, tmp_path)
    log = tmp_path / "check_log.jsonl"
    monkeypatch.setenv("ICFA_CHECK_LOG", str(log))
    monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "1")
    monkeypatch.setenv("FFACT_MULTI_TF_MAX_WORKERS", "2")
    pools = _pool_constructions(monkeypatch)
    created = _scheduler_spy(monkeypatch, **spy_overrides)
    guards = {"n": 0}
    real_start = _mb.start_guard
    monkeypatch.setattr(_mb, "start_guard", lambda *a, **k: (guards.__setitem__("n", guards["n"] + 1), real_start(*a, **k))[1])
    _, result = h.generate_s2(root, h.s2_payload(["12h", "4h"]))
    return {"root": root, "config_hash": str(result.metadata["config_hash"]), "log": _log_lines(log),
            "pools": pools["n"], "schedulers": created, "guards": guards["n"]}


def test_mtf_entry_parallel_joins_domain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(j) 多週期入口：經排程器、worker 之 check 帶根 pid、父守護 1 次、worker 0 次、pool 建構次數＝排程器 executor_created 次數。"""
    run = _mtf_run(tmp_path, monkeypatch)
    root_pid = os.getpid()
    assert len(run["schedulers"]) == 1
    worker_checks = [x for x in run["log"] if x["event"] == "check" and x["pid"] != root_pid]
    assert worker_checks and all(x["root_pid"] == root_pid for x in worker_checks)
    assert [x["pid"] for x in run["log"] if x["event"] == "start_guard"] == [root_pid]
    created = [x for x in run["log"] if x["event"] == "executor_created"]
    assert run["pools"] == len(created) and all(x["pid"] == root_pid for x in created)


def _no_room_read_system() -> Any:
    """准入之剩餘可用量 A＝0（SPEC v35：新增量 > A ⇒ 不准入並行、改走正式串行臂）；根 footprint 取實測。"""
    return (0, 1, False, mb.sample_memory_bytes(), ())


_SERIAL_DRIVERS = {"aux_without_receipt": {"aux_startup_envelope": None},
                   "available_insufficient": {"read_system": _no_room_read_system}}


@pytest.mark.parametrize("driver", list(_SERIAL_DRIVERS))
def test_mtf_entry_serial_arm_byte_equal(tmp_path: Path, driver: str) -> None:
    """(g) 多週期入口無可准入（無輔助啟動上界收據；或 v35 剩餘可用量不足）⇒ 根行程內串行臂、pool 建構 0 次；raw 全欄
    與並行逐位元組相等。兩次 run 各自獨立之 monkeypatch context（串行之覆寫不得滲入並行 run）。"""
    with pytest.MonkeyPatch.context() as mp:
        serial = _mtf_run(tmp_path / "serial", mp, **_SERIAL_DRIVERS[driver])
    assert serial["pools"] == 0
    assert any(x["event"] == "serial" for x in serial["log"])
    assert all(x["pid"] == os.getpid() for x in serial["log"] if x["event"] == "check")
    with pytest.MonkeyPatch.context() as mp:
        parallel = _mtf_run(tmp_path / "parallel", mp)
    assert parallel["pools"] >= 1
    assert parallel["config_hash"] == serial["config_hash"]
    assert _raw_digests(serial["root"], serial["config_hash"]) == _raw_digests(parallel["root"], parallel["config_hash"])


def test_mtf_align_index_check_precedes_aligner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(q)／(m) `MTF.align_index` 之 check 於 `build_asof_index_map` 之前：該 check 拒絕 ⇒ aligner 呼叫 0 次、具名錯誤上拋。"""
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    root = h.isolated(monkeypatch, tmp_path)
    monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "1")
    calls = {"aligner": 0}
    real_build = TimeframeAligner.build_asof_index_map
    monkeypatch.setattr(TimeframeAligner, "build_asof_index_map",
                        staticmethod(lambda *a, **k: (calls.__setitem__("aligner", calls["aligner"] + 1), real_build(*a, **k))[1]))
    real_check = mb.check

    def refuse_align(branch_id: str, components: Any, **kw: Any) -> None:
        if branch_id == "MTF.align_index":
            raise mb.GenerationMemoryBudgetExceeded("MTF.align_index", 0, 0, 0, "budget")
        return real_check(branch_id, components, **kw)

    monkeypatch.setattr(mb, "check", refuse_align)
    with pytest.raises(mb.GenerationMemoryBudgetExceeded):
        h.generate_s2(root, h.s2_payload(["12h", "4h"]))
    assert calls["aligner"] == 0


def test_run_multi_symbol_entry_joins_domain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(j) `run_multi_symbol` 兩標的（BTCUSDT、ETHUSDT；精簡 S2m）：父守護 1 次、worker 0 次；worker 之 check 帶根 pid；
    worker 內多週期串行（worker pid 之 executor_created 0 次）。"""
    root = h.isolated(monkeypatch, tmp_path)
    # b3 實作期：prepare_env 於非多週期並行時把 FFACT_CGSA_WORK_DIR 釘為單一目錄 ⇒ 兩標的並行 worker 共用同一
    # CGSA 工作目錄而互刪群組檔（先完成者之 cleanup）；多標的案例改回各 run 依標的分目錄（cwd 已在 tmp）
    monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)
    log = tmp_path / "check_log.jsonl"
    monkeypatch.setenv("ICFA_CHECK_LOG", str(log))
    factory = h.make_factory(root)
    results, errors = factory.run_multi_symbol(["BTCUSDT", "ETHUSDT"], config_override=h.s2_payload(["12h", "4h"]),
                                               max_workers=2, cache_dir=str(h.KLINE_DIR))
    assert errors == {} and sorted(results) == ["BTCUSDT", "ETHUSDT"]  # r30：兩標的皆須生成成功，不得只有入域紀錄
    assert all(results[s].get("config_hash") for s in results)
    lines = _log_lines(log)
    root_pid = os.getpid()
    assert [x["pid"] for x in lines if x["event"] == "start_guard"] == [root_pid]
    worker_checks = [x for x in lines if x["event"] == "check" and x["pid"] != root_pid]
    assert worker_checks and all(x["root_pid"] == root_pid for x in worker_checks)
    assert not [x for x in lines if x["event"] == "executor_created" and x["pid"] != root_pid]


def test_ic_page_single_process_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(s) IC 分析頁路徑：未收到域描述且無受保護 run 時呼叫 `compute_ic_from_l7_raw` ⇒ 其 `IC.group_read` 等 check 以單行程規則執行、
    不啟動守護。"""
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    import pandas as pd

    root = h.isolated(monkeypatch, tmp_path)
    _, result = h.generate_s2(root)  # 正式生成不清 raw（cleanup 屬 run_ic_first）
    config_hash = str(result.metadata["config_hash"])
    guards = {"n": 0}
    monkeypatch.setattr(mb, "start_guard", lambda *a, **k: guards.__setitem__("n", guards["n"] + 1))
    domains: List[Any] = []
    real_check = mb.check

    def check_spy(branch_id: str, components: Any, **kw: Any) -> None:
        domains.append((branch_id, kw.get("domain")))
        return real_check(branch_id, components, **kw)

    monkeypatch.setattr(mb, "check", check_spy)
    reads = {"n": 0}
    real_read = pd.read_parquet
    monkeypatch.setattr(pd, "read_parquet", lambda *a, **k: (reads.__setitem__("n", reads["n"] + 1), real_read(*a, **k))[1])
    footprint = 100 << 20
    snapshot = mb.VMSnapshot(free_bytes=64 << 30, file_backed_bytes=0, swap_free_bytes=0, pressure_level=1,
                             swap_volume_free_bytes=75 << 30, swap_volume_capacity_bytes=228 << 30)

    def run_ic(budget: int) -> Any:
        with mb.sampler_override(lambda: {"resident": footprint, "phys_footprint": footprint}), \
                mb.budget_override(budget), mb.vm_snapshot_override(snapshot), mb.check_recorder() as recorded:
            ICEngine({"methods": ["spearman"]}).compute_ic_from_l7_raw(
                h.SYMBOL, h.PRIMARY, config_hash, h.forward_return_label(), feature_reader=FeatureReader(str(root)),
                ic_threshold=0.02, label_horizon="1",
                selection_window={"start": h.S2_WINDOW[0], "end": h.S2_WINDOW[1]})
        return recorded

    recorded = run_ic(64 << 30)  # 放行：單行程規則 F＋planned ≤ B
    group_reads = [comps for branch, comps in recorded if branch == "IC.group_read"]
    assert group_reads and guards["n"] == 0
    assert all(d is None for b, d in domains if b.startswith("IC."))  # 未收到顯式域描述
    first_planned = mb.planned_bytes(group_reads[0])
    reads["n"] = 0
    with pytest.raises(mb.GenerationMemoryBudgetExceeded):
        run_ic(footprint + first_planned - 1)  # 拒絕：B 介於 F 與 F＋planned 之間 ⇒ 第一個群組讀回前即拒
    assert reads["n"] == 0 and guards["n"] == 0


def _multi_symbol_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **spy_overrides: Any) -> Dict[str, Any]:
    """`run_multi_symbol` 兩標的、精簡單週期（全史，worker 無起訖）；子行程 cwd＝測試根 ⇒ 特徵寫於測試根之 data_cache/features。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    root = h.isolated(monkeypatch, tmp_path)
    # b3 實作期：prepare_env 於非多週期並行時把 FFACT_CGSA_WORK_DIR 釘為單一目錄 ⇒ 兩標的並行 worker 共用同一
    # CGSA 工作目錄而互刪群組檔（先完成者之 cleanup）；多標的案例改回各 run 依標的分目錄（cwd 已在 tmp）
    monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)
    log = tmp_path / "check_log.jsonl"
    monkeypatch.setenv("ICFA_CHECK_LOG", str(log))
    pools = _pool_constructions(monkeypatch)
    _scheduler_spy(monkeypatch, **spy_overrides)
    results, errors = h.make_factory(root).run_multi_symbol(["BTCUSDT", "ETHUSDT"], config_override=h.s2_payload(),
                                                            max_workers=2, cache_dir=str(h.KLINE_DIR))
    store = tmp_path / "data_cache" / "features"
    digests: Dict[str, Dict[str, str]] = {}
    import scripts.freeze_icfirstalign_baseline as frz

    for sym, meta in results.items():
        reader = FeatureReader(str(store))
        manifest = reader.load_manifest_v2(sym, h.PRIMARY, meta["config_hash"], artifact_kind="raw")
        cols = sorted(c for g in manifest["artifacts"]["raw"]["groups"].values() for c in g.get("columns", []))
        frame = reader.load_columns_v2(sym, h.PRIMARY, meta["config_hash"], cols)
        digests[sym] = {c: frz.column_digest(frame[c].to_numpy()) for c in cols}
    return {"results": results, "errors": errors, "log": _log_lines(log), "pools": pools["n"], "digests": digests}


@pytest.mark.parametrize("driver", list(_SERIAL_DRIVERS))
def test_run_multi_symbol_serial_arm_byte_equal(tmp_path: Path, driver: str) -> None:
    """(g) 第三入口：`run_multi_symbol` 無可准入（無輔助啟動上界收據；或 v35 剩餘可用量不足）⇒ 根行程內依序呼叫
    `generate_features`、pool 建構 0 次、兩標的皆成功、check 皆於根 pid；各標的 raw 全欄與並行逐位元組相等。"""
    with pytest.MonkeyPatch.context() as mp:
        serial = _multi_symbol_run(tmp_path / "serial", mp, **_SERIAL_DRIVERS[driver])
    assert serial["errors"] == {} and sorted(serial["results"]) == ["BTCUSDT", "ETHUSDT"]
    assert serial["pools"] == 0 and any(x["event"] == "serial" for x in serial["log"])
    assert all(x["pid"] == os.getpid() for x in serial["log"] if x["event"] == "check")
    with pytest.MonkeyPatch.context() as mp:
        parallel = _multi_symbol_run(tmp_path / "parallel", mp)
    assert parallel["errors"] == {} and parallel["pools"] >= 1
    assert serial["digests"] == parallel["digests"]


_ALIGN_SHAPES: Dict[str, int] = {}


def _aligner_shapes(tmp_path: Path) -> Dict[str, int]:
    """以寬鬆預算實跑一次 S2m，記 `build_asof_index_map` 實際之主列數 n_p 與來源列數 n_s（模組內快取）。"""
    if _ALIGN_SHAPES:
        return _ALIGN_SHAPES
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    with pytest.MonkeyPatch.context() as mp:
        root = h.isolated(mp, tmp_path / "shapes")
        mp.setenv("FFACT_MULTI_TF_PARALLEL", "1")
        real_build = TimeframeAligner.build_asof_index_map

        def spy(primary_s: Any, source_s: Any, *a: Any, **k: Any) -> Any:
            _ALIGN_SHAPES.setdefault("n_p", int(len(primary_s)))
            _ALIGN_SHAPES.setdefault("n_s", int(len(source_s)))
            return real_build(primary_s, source_s, *a, **k)

        mp.setattr(TimeframeAligner, "build_asof_index_map", staticmethod(spy))
        h.generate_s2(root, h.s2_payload(["12h", "4h"]))
    return _ALIGN_SHAPES


def _align_gap_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """`MTF.align_index` 之 check 於注入讀數下判定：F 固定、B＝F＋3 × 主列 × 8 B（介於「只計主列」與完整 aligner 工作區之間）。"""
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    shapes = _aligner_shapes(tmp_path)
    root = h.isolated(monkeypatch, tmp_path / "gap")
    monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "1")
    calls = {"aligner": 0}
    real_build = TimeframeAligner.build_asof_index_map
    monkeypatch.setattr(TimeframeAligner, "build_asof_index_map",
                        staticmethod(lambda *a, **k: (calls.__setitem__("aligner", calls["aligner"] + 1),
                                                      real_build(*a, **k))[1]))
    footprint = 100 << 20
    snapshot = mb.VMSnapshot(free_bytes=64 << 30, file_backed_bytes=0, swap_free_bytes=0, pressure_level=1,
                             swap_volume_free_bytes=75 << 30, swap_volume_capacity_bytes=228 << 30)
    real_check = mb.check

    def gap_check(branch_id: str, components: Any, **kw: Any) -> None:
        if branch_id != "MTF.align_index":
            return real_check(branch_id, components, **kw)
        with mb.sampler_override(lambda: {"resident": footprint, "phys_footprint": footprint}), \
                mb.budget_override(footprint + 3 * 8 * shapes["n_p"]), mb.vm_snapshot_override(snapshot):
            return real_check(branch_id, components, **kw)

    monkeypatch.setattr(mb, "check", gap_check)
    raised = None
    try:
        h.generate_s2(root, h.s2_payload(["12h", "4h"]))
    except mb.GenerationMemoryBudgetExceeded as exc:
        raised = exc
    return {"raised": raised, "aligner": calls["aligner"], "shapes": shapes}


def test_mtf_align_index_budget_gap_refuses_before_aligner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(q) 預算置於「主列 × 8 B」與 `build_asof_index_map` 同時存活工作區之間 ⇒ 於 aligner 呼叫前具名拒絕（aligner 0 次）。"""
    run = _align_gap_run(tmp_path, monkeypatch)
    assert run["shapes"]["n_p"] > 0
    assert run["raised"] is not None and run["aligner"] == 0


def test_mutation_align_index_planned_primary_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(q) mutant「`MTF.align_index` 之 planned 只計主列 × 8 B」⇒ 同一預算間隙放行並呼叫 aligner。"""
    shapes = _aligner_shapes(tmp_path)
    monkeypatch.setitem(mb.BRANCH_TABLE, "MTF.align_index",
                        lambda params: [mb.Component("primary_seconds", "anon", 8 * shapes["n_p"])])
    run = _align_gap_run(tmp_path, monkeypatch)
    assert run["raised"] is None and run["aligner"] >= 1


# ---------------------------------------------------------------- 例外出口與串行臂錯誤語意（SPEC v30；審碼 b3 r1 codex P1-02／P1-03）

def _exception_exit_run(tmp_path: Path, transient_shutdown_failure: bool = False,
                        shutdown_interrupt: bool = False,
                        creation_error: BaseException = OSError("injected second executor creation failure"),
                        expect: Any = OSError) -> Dict[str, Any]:
    """A 已進 worker；B 之 executor 建構拋 `creation_error`（並行合法：兩任務 E 100、根 10、B 1000、輔助槽 1）。
    A 之 worker 於 0.5 秒後自行完成（執行緒無法強殺；排程器須等其退出才返回）。`transient_shutdown_failure` ⇒
    A 之第一次 shutdown 於 join 前拋 OSError（審碼 b3 r2 codex P1-03 之序列）；`shutdown_interrupt` ⇒ 第一次
    shutdown 於 join 前拋 KeyboardInterrupt（回收期間之使用者中斷，審碼 b3 r3 codex P1-01 之序列）。"""
    started, release = threading.Event(), threading.Event()
    executors: List[Any] = []
    shutdowns: List[bool] = []

    class Executor(ThreadPoolExecutor):
        def shutdown(self, *a: Any, **k: Any) -> None:
            shutdowns.append(True)
            if transient_shutdown_failure and len(shutdowns) == 1:
                raise OSError("transient shutdown failure")
            if shutdown_interrupt and len(shutdowns) == 1:
                raise KeyboardInterrupt
            super().shutdown(*a, **k)

    def factory(n: int) -> Any:
        if executors:
            assert started.wait(2)
            raise creation_error
        executor = Executor(n)
        executors.append(executor)
        return executor

    def worker(desc: mb.DomainDescriptor, payload: Any) -> Any:
        started.set()
        release.wait(5)
        return payload

    timer = threading.Timer(0.5, release.set)
    timer.start()
    sched = mb.MemoryBudgetScheduler(1000, domain_dir=tmp_path, max_workers=2, executor_factory=factory,
                                     read_system=lambda: (1000, 1, False, 10, ()),
                                     read_task_footprint=lambda tid: 10, aux_startup_envelope=1,
                                     task_identity=_thread_identity)
    out: Dict[str, Any] = {}
    try:
        with pytest.raises(expect) as raised:
            sched.run([mb.Task("A", 100, 1), mb.Task("B", 100, 2)], worker, lambda p: p, lambda w: None)
        assert raised.value is creation_error, "回收完成後須上拋觸發清理之原例外"
        out = {"shutdowns": len(shutdowns),
               "worker_alive": any(t.is_alive() for ex in executors for t in ex._threads),
               "A_status": sched._tasks["A"].status}
    finally:
        release.set()
        timer.cancel()
        for executor in executors:
            executor.shutdown(wait=True)
    return out


def test_exception_exit_joins_started_executors(tmp_path: Path) -> None:
    """v30：波次中途之 executor 建構失敗 ⇒ 原例外上拋前，已啟動之 A 之 executor 已 shutdown、worker 已退出、
    狀態 joined（外層隨即關閉域與守護，不得留下未受保護之 worker）。"""
    out = _exception_exit_run(tmp_path)
    assert out == {"shutdowns": 1, "worker_alive": False, "A_status": "joined"}


def test_mutation_exception_exit_skips_join(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：例外出口不回收（`_join_unjoined` 無動作）⇒ 返回時 A 之 worker 仍存活而紅。"""
    monkeypatch.setattr(mb.MemoryBudgetScheduler, "_join_unjoined", lambda self: None)
    out = _exception_exit_run(tmp_path)
    assert out["worker_alive"] is True and out["A_status"] != "joined"


def test_transient_join_failure_still_confirms_exit(tmp_path: Path) -> None:
    """v31（審碼 b3 r2 codex P1-03）：例外出口之 shutdown 第一次於 join 前失敗 ⇒ 不吞掉返回，同一 shutdown 再試至
    確認退出；原例外（executor 建構失敗）於回收完成後上拋。改前：suppress 後返回、A 之 worker 仍存活而紅。"""
    out = _exception_exit_run(tmp_path, transient_shutdown_failure=True)
    assert out == {"shutdowns": 2, "worker_alive": False, "A_status": "joined"}


def test_interrupt_during_cleanup_deferred_until_exit_confirmed(tmp_path: Path) -> None:
    """v32（審碼 b3 r3 codex P1-01）：executor 建構失敗之例外出口回收期間收到 KeyboardInterrupt ⇒ 中斷延後，
    A 確認退出、joined 後才上拋原 OSError（外層隨即關閉域與守護）。改前：中斷直穿回收、A 仍存活而紅。"""
    out = _exception_exit_run(tmp_path, shutdown_interrupt=True)
    assert out == {"shutdowns": 2, "worker_alive": False, "A_status": "joined"}


def test_repeated_interrupt_during_cleanup_keeps_first(tmp_path: Path) -> None:
    """v32：首次中斷觸發清理、清理中再次中斷 ⇒ 仍確認 A 退出後才上拋首次之 KeyboardInterrupt。"""
    first = KeyboardInterrupt("first interrupt")
    out = _exception_exit_run(tmp_path, shutdown_interrupt=True, creation_error=first, expect=KeyboardInterrupt)
    assert out == {"shutdowns": 2, "worker_alive": False, "A_status": "joined"}


@pytest.fixture
def default_sigint() -> Any:
    """SIGINT 案例之前提：本行程之 SIGINT 處理器為 Python 預設（KeyboardInterrupt）。全套同一 session 之前序測試
    可能已安裝其他處理器（實測：全套跑時預設行為不成立），故本 fixture 明設預設並於結束還原。"""
    import signal

    previous = signal.signal(signal.SIGINT, signal.default_int_handler)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


def _sigint_run(tmp_path: Path, mode: str) -> Dict[str, Any]:
    """真實 SIGINT（只發給本測試行程自身）於排程器執行中到達（v33，審碼 b3 r4 codex P1-01）：
    - `cleanup_entry`：B 之 executor 建構拋 OSError ⇒ 例外出口；於 `_join_unjoined` 被呼叫之瞬間（任何 try 之前，
      以 `sys.settrace` 固定交錯點）送出 SIGINT。
    - `wave`：A 執行中（max_workers 1、B 排隊）由另一執行緒送出 SIGINT。
    A 之 worker 於 0.5 秒後自行完成。回傳上拋之例外、回收狀態；任何例外皆於此捕捉（不讓中斷穿出測試）。"""
    import signal
    import sys

    started, release = threading.Event(), threading.Event()
    executors: List[Any] = []
    original = OSError("injected second executor creation failure")

    def factory(n: int) -> Any:
        if executors and mode == "cleanup_entry":
            assert started.wait(2)
            raise original
        executor = ThreadPoolExecutor(n)
        executors.append(executor)
        return executor

    def worker(desc: mb.DomainDescriptor, payload: Any) -> Any:
        started.set()
        release.wait(5)
        return payload

    target = mb.MemoryBudgetScheduler._join_unjoined.__code__

    def tracer(frame: Any, event: str, arg: Any) -> Any:
        if event == "call" and frame.f_code is target:
            os.kill(os.getpid(), signal.SIGINT)
        return None

    def kick() -> None:
        assert started.wait(2)
        time.sleep(0.1)
        os.kill(os.getpid(), signal.SIGINT)

    timer = threading.Timer(0.5, release.set)
    timer.start()
    sched = mb.MemoryBudgetScheduler(1000, domain_dir=tmp_path, max_workers=2 if mode == "cleanup_entry" else 1,
                                     executor_factory=factory, read_system=lambda: (1000, 1, False, 10, ()),
                                     read_task_footprint=lambda tid: 10, aux_startup_envelope=1,
                                     task_identity=_thread_identity)
    raised: Optional[BaseException] = None
    kicker = threading.Thread(target=kick) if mode == "wave" else None
    try:
        if kicker is not None:
            kicker.start()
        if mode == "cleanup_entry":
            sys.settrace(tracer)
        try:
            sched.run([mb.Task("A", 100, 1), mb.Task("B", 100, 2)], worker, lambda p: p, lambda w: None)
        except BaseException as exc:  # noqa: BLE001 — 測試自行分類；中斷不得穿出
            raised = exc
        finally:
            sys.settrace(None)
        out = {"raised": raised, "worker_alive": any(t.is_alive() for ex in executors for t in ex._threads),
               "A_status": sched._tasks["A"].status, "B_status": sched._tasks["B"].status,
               "original": original}
    finally:
        release.set()
        timer.cancel()
        if kicker is not None:
            kicker.join(5)
        for executor in executors:
            executor.shutdown(wait=True)
    return out


def test_sigint_at_cleanup_entry_deferred(tmp_path: Path, default_sigint: Any) -> None:
    """v33：例外出口進入回收之瞬間（任何 try 之前）收到 SIGINT ⇒ 訊號層延後，A 確認退出、joined 後才上拋原 OSError。
    改前（只在 try 內延後）：中斷於回收前穿出、A 仍存活而紅。"""
    out = _sigint_run(tmp_path, "cleanup_entry")
    assert out["raised"] is out["original"]
    assert out["worker_alive"] is False and out["A_status"] == "joined"


def test_mutation_sigint_deferral_removed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, default_sigint: Any) -> None:
    """mutant：移除訊號層延後（`_interrupt_deferral` 改為無動作）⇒ 同序列下中斷於回收前穿出、A 未 joined 而紅。"""
    import contextlib

    monkeypatch.setattr(mb.MemoryBudgetScheduler, "_interrupt_deferral", lambda self: contextlib.nullcontext())
    out = _sigint_run(tmp_path, "cleanup_entry")
    assert isinstance(out["raised"], KeyboardInterrupt) and out["A_status"] != "joined"


def test_sigint_during_wave_stops_admission_and_waits(tmp_path: Path, default_sigint: Any) -> None:
    """v33：A 執行中收到 SIGINT ⇒ 停止准入（B 不執行）、A 確認退出並 joined 後才上拋 KeyboardInterrupt。"""
    out = _sigint_run(tmp_path, "wave")
    assert isinstance(out["raised"], KeyboardInterrupt)
    assert out["worker_alive"] is False and out["A_status"] == "joined" and out["B_status"] == "queued"


_REENTRANT_SIGINT_PROBE = """
import os, signal, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from momentum.FeatureEngineering import memory_budget as mb

signal.signal(signal.SIGINT, signal.default_int_handler)
started, release = threading.Event(), threading.Event()
sent = []

def worker(desc, payload):
    started.set()
    release.wait(5)
    return payload

def kick():
    started.wait(2)
    time.sleep(0.1)
    sent.append("first")
    os.kill(os.getpid(), signal.SIGINT)
    time.sleep(0.25)
    release.set()

main = threading.main_thread()

def tracer(frame, event, arg):
    # 主執行緒任一 Condition.notify_all 入口（原實作之處理器內 Event.set 持鎖點）再送第二次 SIGINT
    if event == "call" and frame.f_code is threading.Condition.notify_all.__code__ and sent == ["first"] \\
            and threading.current_thread() is main:
        sent.append("second")
        os.kill(os.getpid(), signal.SIGINT)
    return None

sched = mb.MemoryBudgetScheduler(1000, domain_dir=sys.argv[1], max_workers=1, executor_factory=ThreadPoolExecutor,
                                 read_system=lambda: (1000, 1, False, 10, ()), read_task_footprint=lambda tid: 10,
                                 aux_startup_envelope=1, task_identity=lambda: (10 ** 9 + threading.get_ident() % 10 ** 6, 0.0))
threading.Thread(target=kick).start()
sys.settrace(tracer)
threading.settrace(lambda *a: None)
try:
    sched.run([mb.Task("A", 100, 1), mb.Task("B", 100, 2)], worker, lambda p: p, lambda w: None)
    outcome = "returned"
except KeyboardInterrupt:
    outcome = "KeyboardInterrupt"
finally:
    sys.settrace(None)
print("RESULT", outcome, sched._tasks["A"].status, sched._tasks["B"].status,
      signal.getsignal(signal.SIGINT) is signal.default_int_handler)
"""


def test_double_sigint_during_wave_no_deadlock(tmp_path: Path) -> None:
    """v34（審碼 b3 r5 codex P1-01）：波次中兩次 SIGINT（第二次固定於主執行緒 `Condition.notify_all` 入口——原實作之
    處理器內 `Event.set` 持鎖點）⇒ 不死結：A 確認退出並 joined、B 不執行、上拋 KeyboardInterrupt、處理器還原。
    於新子行程執行（死結時以逾時判紅，不掛住測試行程）。"""
    proc = subprocess.run([sys.executable, "-c", _REENTRANT_SIGINT_PROBE, str(tmp_path)], cwd=str(h.REPO),
                          env={**os.environ, "PYTHONPATH": str(h.REPO)}, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "RESULT KeyboardInterrupt joined queued True" in proc.stdout, proc.stdout[-2000:]


def test_sigint_right_after_handler_install_restores_handler(tmp_path: Path, default_sigint: Any) -> None:
    """v34（審碼 b3 r5 codex P2-02）：處理器安裝後之第一個執行行即收到 SIGINT（無未確認退出者 ⇒ 原處理器拋
    KeyboardInterrupt）⇒ 排程器結束後 SIGINT 處理器仍還原為原處理器。改前：安裝在 try 外 ⇒ 遺留排程器之處理器。"""
    import linecache
    import signal

    code = mb.MemoryBudgetScheduler._interrupt_deferral.__wrapped__.__code__
    state = {"after_install": False, "sent": False}

    def tracer(frame: Any, event: str, arg: Any) -> Any:
        if frame.f_code is not code:
            return tracer if event == "call" and frame.f_code is code else None
        if event == "line" and not state["sent"]:
            if state["after_install"]:
                state["sent"] = True
                os.kill(os.getpid(), signal.SIGINT)
            elif "signal.signal(signal.SIGINT, handler)" in linecache.getline(code.co_filename, frame.f_lineno):
                state["after_install"] = True
        return tracer

    sched = mb.MemoryBudgetScheduler(1000, domain_dir=tmp_path, max_workers=1, executor_factory=ThreadPoolExecutor,
                                     read_system=lambda: (1000, 1, False, 10, ()),
                                     read_task_footprint=lambda tid: 10, aux_startup_envelope=None,
                                     task_identity=_thread_identity)
    raised: Optional[BaseException] = None
    sys.settrace(tracer)
    try:
        sched.run([mb.Task("A", 100, 1)], lambda d, p: p, lambda p: p, lambda w: None)
    except BaseException as exc:  # noqa: BLE001
        raised = exc
    finally:
        sys.settrace(None)
    assert state["sent"] and isinstance(raised, KeyboardInterrupt)
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler


def test_sigint_without_outstanding_worker_raises_promptly(tmp_path: Path, default_sigint: Any) -> None:
    """v33：無未確認退出之 worker（串行臂於根內執行中）⇒ SIGINT 照原處理器即時拋 KeyboardInterrupt（不延後）。"""
    import signal

    def serial(payload: Any) -> Any:
        os.kill(os.getpid(), signal.SIGINT)
        time.sleep(2)
        return payload

    sched = mb.MemoryBudgetScheduler(1000, domain_dir=tmp_path, max_workers=1, executor_factory=ThreadPoolExecutor,
                                     read_system=lambda: (1000, 1, False, 10, ()),
                                     read_task_footprint=lambda tid: 10, aux_startup_envelope=None,
                                     task_identity=_thread_identity)
    began = time.monotonic()
    raised: Optional[BaseException] = None
    try:
        sched.run([mb.Task("A", 100, 1)], lambda d, p: p, serial, lambda w: None)
    except BaseException as exc:  # noqa: BLE001
        raised = exc
    assert isinstance(raised, KeyboardInterrupt) and time.monotonic() - began < 1.5


def test_repeated_interrupts_in_cleanup_keep_retry_spacing(tmp_path: Path) -> None:
    """v33（審碼 b3 r4 codex P2-02）：shutdown 連續 4 次以中斷失敗（第 1 次於正常波次 ⇒ 進例外出口；其後 3 次於回收
    中）⇒ 回收中每次重試前仍有間隔（0.05＋0.10＋0.15 秒）、記 3 次 `interrupt_deferred`，第 5 次成功 joined；不忙迴圈。"""
    attempts: List[float] = []

    class InterruptedShutdown(ThreadPoolExecutor):
        def shutdown(self, *a: Any, **k: Any) -> None:
            attempts.append(time.monotonic())
            if len(attempts) <= 4:
                raise KeyboardInterrupt
            super().shutdown(*a, **k)

    sched = mb.MemoryBudgetScheduler(1000, domain_dir=tmp_path, max_workers=1,
                                     executor_factory=InterruptedShutdown,
                                     read_system=lambda: (1000, 1, False, 10, ()),
                                     read_task_footprint=lambda tid: 10, aux_startup_envelope=1,
                                     task_identity=_thread_identity)
    raised: Optional[BaseException] = None
    try:
        sched.run([mb.Task("A", 100, 1)], lambda d, p: p, lambda p: p, lambda w: None)
    except BaseException as exc:  # noqa: BLE001
        raised = exc
    assert isinstance(raised, KeyboardInterrupt)  # 正常波次之 join 中斷 ⇒ 例外出口回收完成後上拋原中斷
    assert sched._tasks["A"].status == "joined" and len(attempts) == 5
    assert sum(1 for e, _ in sched.trace if e == "interrupt_deferred") == 3
    assert attempts[-1] - attempts[1] >= 0.28


def test_persistent_join_failure_keeps_ownership(tmp_path: Path) -> None:
    """v31：shutdown 持續失敗 ⇒ `run` 不返回（持有者不得回收域與守護）、狀態未 joined；失敗解除後才返回並標
    joined。不以固定逾時放手。"""
    healthy = threading.Event()
    attempts: List[bool] = []

    class FlakyShutdown(ThreadPoolExecutor):
        def shutdown(self, *a: Any, **k: Any) -> None:
            attempts.append(True)
            if not healthy.is_set():
                raise RuntimeError("injected shutdown failure")
            super().shutdown(*a, **k)

    sched = mb.MemoryBudgetScheduler(1000, domain_dir=tmp_path, max_workers=1, executor_factory=FlakyShutdown,
                                     read_system=lambda: (1000, 1, False, 10, ()),
                                     read_task_footprint=lambda tid: 10, aux_startup_envelope=1,
                                     task_identity=_thread_identity)
    done: Dict[str, Any] = {}
    runner = threading.Thread(target=lambda: done.update(
        result=sched.run([mb.Task("A", 100, 1)], lambda d, p: p, lambda p: p, lambda w: None)))
    runner.start()
    try:
        runner.join(1.0)
        assert runner.is_alive() and len(attempts) >= 2 and sched._tasks["A"].status != "joined"
    finally:
        healthy.set()
        runner.join(10)
    assert not runner.is_alive() and done["result"] == [1] and sched._tasks["A"].status == "joined"


@pytest.mark.parametrize("allow_partial", [False, True])
def test_serial_arm_budget_error_not_degraded(allow_partial: bool, tmp_path: Path) -> None:
    """v30：根內串行臂之週期 producer 遇預算具名錯誤 ⇒ rollback／discard 後原樣上拋（同一物件），不論
    `allow_partial_timeframes`；與並行臂之結果處理相同。改前：False ⇒ RuntimeError、True ⇒ 吞掉並記 skipped。"""
    from unittest.mock import MagicMock, patch

    from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator

    factory = h.make_factory(tmp_path / "features")
    raw = h.kline_close().iloc[-800:].to_frame()
    config = factory._resolve_config(h.s2_payload(["12h", "4h"], allow_partial_timeframes=allow_partial))
    gen = MultiTFGenerator(factory, config)
    err = mb.GenerationMemoryBudgetExceeded("Layer 3", 100, 200, 250, "本程式超上限")
    registry = MagicMock()
    registry._groups = {}
    skipped: List[str] = []
    with patch.object(factory, "_layer0_data_ingestion", return_value=raw), \
            patch.object(gen, "_run_tf_l1_l6_results", side_effect=err):
        with pytest.raises(mb.GenerationMemoryBudgetExceeded) as info:
            gen._process_timeframe_inroot(h.SYMBOL, "4h", raw, raw.index, None, None, registry, skipped, {}, {},
                                          {"dual_tf_l1_l6": 0, "alignment": 0})
    assert info.value is err and skipped == []
    registry.rollback_timeframe.assert_called_once_with("4h")
    registry.discard_layer_status.assert_called_once_with("4h")
    with pytest.raises(mb.GenerationMemoryBudgetExceeded) as parallel:
        gen._accept_worker_result(err, registry, raw.index, [], {}, {}, {"alignment": 0})
    assert parallel.value is err


# ---------------------------------------------------------------- 估算低估之根串行重試、可用量不足之串行臂（SPEC v35）

def test_reroute_needed_retried_serially_after_wave_join(tmp_path: Path) -> None:
    """worker 回 `MemoryRerouteNeeded` ⇒ 該波 join 後於根以正式串行臂重試一次；其後佇列任務一律串行（根停止新准入）；
    重試之任務不交 `on_wave_joined`。純狀態反例 root 20／E 40／E 40：兩 worker 各需擴至 60 ⇒ 皆回 reroute、無超額。"""
    serial_calls: List[Any] = []
    waves: List[List[Any]] = []
    executors: List[Any] = []

    def factory(n: int) -> Any:
        executor = ThreadPoolExecutor(n)
        executors.append(executor)
        return executor

    def worker(desc: mb.DomainDescriptor, payload: Any) -> Any:
        raise mb.MemoryRerouteNeeded(desc.task_id, 20, 40, int(desc.envelope), mb.MSG_ESTIMATE_EXCEEDED)

    def serial(payload: Any) -> Any:
        serial_calls.append(payload)
        return ("serial", payload)

    sched = mb.MemoryBudgetScheduler(1000, domain_dir=tmp_path, max_workers=2, executor_factory=factory,
                                     read_system=lambda: (1000, 1, False, 20, ()),
                                     read_task_footprint=lambda tid: 20, aux_startup_envelope=1,
                                     task_identity=_thread_identity)
    out = sched.run([mb.Task("A", 40, 1), mb.Task("B", 40, 2), mb.Task("C", 40, 3)], worker, serial, waves.append)
    assert out == [("serial", 1), ("serial", 2), ("serial", 3)]
    assert serial_calls == [1, 2, 3] and waves == [[]] and len(executors) == 2
    assert [t for e, t in sched.trace if e == "reroute"] == ["A", "B"]


def test_mutation_reroute_not_retried(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant「低估錯誤當一般失敗回傳（不重試）」⇒ 結果為例外物件而紅。"""
    sched = mb.MemoryBudgetScheduler(1000, domain_dir=tmp_path, max_workers=1, executor_factory=ThreadPoolExecutor,
                                     read_system=lambda: (1000, 1, False, 20, ()),
                                     read_task_footprint=lambda tid: 20, aux_startup_envelope=1,
                                     task_identity=_thread_identity)
    monkeypatch.setattr(mb, "MemoryRerouteNeeded", type("NotReroute", (Exception,), {}))
    out = sched.run([mb.Task("A", 40, 1)],
                    lambda d, p: (_ for _ in ()).throw(mb.GenerationMemoryBudgetExceeded("A", 0, 0, 0, "x")),
                    lambda p: ("serial", p), lambda w: None)
    assert isinstance(out[0], mb.GenerationMemoryBudgetExceeded)


def test_available_insufficient_falls_back_to_serial_without_pool(tmp_path: Path) -> None:
    """SPEC v35：新增量 > 剩餘可用量 A（准入之可吸收量）⇒ 不准入並行、於根以正式串行臂執行，executor 建立 0 次
    （多週期、多標的、API 批次三入口共用之排程器）。"""
    created: List[int] = []
    sched = mb.MemoryBudgetScheduler(10 ** 6, domain_dir=tmp_path, max_workers=2,
                                     executor_factory=lambda n: created.append(n) or ThreadPoolExecutor(n),
                                     read_system=lambda: (10, 1, False, 20, ()),
                                     read_task_footprint=lambda tid: 0, aux_startup_envelope=1,
                                     task_identity=_thread_identity)
    out = sched.run([mb.Task("A", 100, 1), mb.Task("B", 100, 2)], lambda d, p: ("parallel", p),
                    lambda p: ("serial", p), lambda w: None)
    assert out == [("serial", 1), ("serial", 2)] and created == []


class _AnyScale(tuple):
    """測試用速度收據：任一規模鍵皆相符。"""

    def __contains__(self, item: object) -> bool:
        return True


def test_l2_speed_receipt_route_byte_equal(tmp_path: Path) -> None:
    """SPEC v35／v36：L2 設定指紋於白名單且有相符速度收據 ⇒ 分派點改走 pandas 臂；raw 全欄與 polars 臂逐位元組相等
    （S2 真實 kline）。容量面 pandas 之 planned 恆 ≥ polars（估算式），故本白名單之切換只經速度收據觸發。"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    chosen: List[str] = []
    real = FeatureFactory._budget_check_l2

    def spy(self: Any, *a: Any, **k: Any) -> str:
        branch = real(self, *a, **k)
        chosen.append(branch)
        return branch

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(FeatureFactory, "_budget_check_l2", spy)
        base_root = h.isolated(mp, tmp_path / "polars")
        _, base = h.generate_s2(base_root)
    polars_choices, chosen[:] = list(chosen), []
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(FeatureFactory, "_budget_check_l2", spy)
        mp.setattr(FeatureFactory, "_l2_route_fingerprint", lambda self, layer1, config: "certified")
        mp.setattr(FeatureFactory, "L2_ROUTE_CERTIFIED", frozenset({"certified"}))
        for alt in ("L2.pandas_serial", "L2.pandas_parallel"):
            mp.setitem(mb.ROUTE_SPEED_RECEIPTS, ("Layer 2", "L2.polars", alt), _AnyScale())
        switched_root = h.isolated(mp, tmp_path / "switched")
        _, switched = h.generate_s2(switched_root)
    assert polars_choices and set(polars_choices) == {"L2.polars"}
    assert chosen and all(c.startswith("L2.pandas") for c in chosen)
    assert base.metadata["config_hash"] == switched.metadata["config_hash"]
    assert _raw_digests(base_root, base.metadata["config_hash"]) == \
        _raw_digests(switched_root, switched.metadata["config_hash"])
