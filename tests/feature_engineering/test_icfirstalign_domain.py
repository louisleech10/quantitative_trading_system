"""ICFIRSTALIGN 乙 Task 4.2 子行程預算域（docs/ICFIRSTALIGN_SPEC.md v27 驗證 (a)–(o)、(t)、(u)）。

以注入讀數與估算之純函式／狀態機為主（秒級）；排程器之 executor 以行程內執行緒池注入，任務以事件控制完成時序。
三入口接線以 AST 與輕量 spy 驗（不跑完整生成）；需真實子行程者限標準庫 spawn 探針（峰值遠低於 1 GB）。
實作前應為紅：`memory_budget` 之域函式與排程器為空殼（NotImplementedError），三入口仍直接建立 `ProcessPoolExecutor`。
數值單位為任意整數（只模擬資源讀數與排程，不涉市場資料）。
"""

from __future__ import annotations

import ast
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pytest

from momentum.FeatureEngineering import memory_budget as mb
from tests.feature_engineering import icfirstalign_helpers as h

pytestmark = pytest.mark.timeout(120)

GiB = 1 << 30


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
    monkeypatch.setattr(mb, "admit", lambda state, e: real(
        mb.AdmissionState(state.budget, state.members, (), state.absorbable, state.pressure_level, state.stop_flag), e))
    state = _state(200, [_m(1, 20, role="root")], slots=[mb.Slot("A", 60)], absorbable=90)
    assert mb.admit(state, 60).ok is True


@pytest.mark.parametrize("pressure,stop,reason", [(4, False, "pressure"), (1, True, "stop_flag")])
def test_pressure_and_stop_flag_are_admission_conjuncts(pressure: int, stop: bool, reason: str) -> None:
    """r27：壓力危急、停止旗標與 B 式同一准入合取（一般並行准入亦受約束）。"""
    state = _state(10 ** 6, [_m(1, 10, role="root")], pressure=pressure, stop=stop)
    assert mb.admit(state, 1) == mb.Admission(ok=False, reason=reason)


def test_members_deduplicated_by_pid_and_start_time() -> None:
    """成員以 (pid, start_time) 去重；pid 重用（start_time 不同）不繼承舊承諾。"""
    dup = [_m(1, 40, role="root"), _m(1, 40, role="root"), _m(7, 6, role="guard")]
    assert mb.measured_total(dup) == 46
    reused = [mb.Member(pid=9, start_time=1.0, footprint=5), mb.Member(pid=9, start_time=2.0, footprint=8)]
    assert mb.measured_total(reused) == 13


def test_guard_tracker_counted_once() -> None:
    """(i) 根 40、worker 50、守護 6、B 100 ⇒ 96 不停。"""
    members = [_m(1, 40, role="root"), _m(2, 50), _m(3, 6, role="guard")]
    assert mb.measured_total(members) == 96
    assert mb.guard_should_stop(members, 100, 1, 75 * GiB, 4 * GiB) is None


def test_mutation_guard_added_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    """(i) mutant「守護另加一次」⇒ 102 > 100 誤停。"""
    real = mb.measured_total
    monkeypatch.setattr(mb, "measured_total",
                        lambda ms: real(ms) + sum(m.footprint for m in ms if m.role == "guard"))
    members = [_m(1, 40, role="root"), _m(2, 50), _m(3, 6, role="guard")]
    assert mb.guard_should_stop(members, 100, 1, 75 * GiB, 4 * GiB) is not None


def test_guard_uses_measured_not_commitment() -> None:
    """(i) Σ U > B 而 Σ F < B ⇒ 不寫旗標（承諾量不是量測值）；Σ F > B ⇒ 停止。"""
    members = [_m(1, 20, role="root"), _m(2, 30, 90)]
    assert sum(mb.commitment(m) for m in members) > 100
    assert mb.guard_should_stop(members, 100, 1, 75 * GiB, 4 * GiB) is None
    assert mb.guard_should_stop([_m(1, 60, role="root"), _m(2, 50, 90)], 100, 1, 75 * GiB, 4 * GiB) is not None


def test_mutation_guard_uses_commitment(monkeypatch: pytest.MonkeyPatch) -> None:
    """(i) mutant「以 U 判」⇒ 同狀態誤停。"""
    monkeypatch.setattr(mb, "measured_total", lambda ms: sum(mb.commitment(m) for m in ms))
    members = [_m(1, 20, role="root"), _m(2, 30, 90)]
    assert mb.guard_should_stop(members, 100, 1, 75 * GiB, 4 * GiB) is not None


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
            read_task_footprint=lambda tid: self.footprints.get(tid, 0), aux_startup_envelope=aux)

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
    """(h) 槽→pid 替換前後承諾不變（不兩份、不零份）。"""
    sched = mb.MemoryBudgetScheduler(100, domain_dir=tmp_path, max_workers=2, executor_factory=ThreadPoolExecutor,
                                     read_system=lambda: (10 ** 9, 1, False, 10, ()),
                                     read_task_footprint=lambda tid: 5, aux_startup_envelope=0)
    sched.mark_starting("A")
    before = sched.snapshot()
    sched.bind_pid("A", 4242, 1.0)
    after = sched.snapshot()

    def total(s: mb.AdmissionState) -> int:
        return sum(mb.commitment(m) for m in s.members) + sum(sl.envelope for sl in s.slots)

    assert [sl.slot_id for sl in before.slots] == ["A"] and not after.slots
    assert total(before) == total(after)


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
                                         read_task_footprint=lambda tid: 1, aux_startup_envelope=0)
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
    calls = {ast.unparse(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)}
    assert not any(c.endswith("ProcessPoolExecutor") for c in calls), f"{func} 仍直接建立 ProcessPoolExecutor"
    assert any("create_memory_budget_scheduler" in c for c in calls)


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

    def on_start(label: str, refs: List[Tuple[str, Any]]) -> None:
        gc.collect()
        alive_at[label] = [lab for lab, r in refs if r() is not None and lab in ("Layer 3", "Layer 4", "Layer 5")]

    out = _run_worker_inprocess(tmp_path, monkeypatch, on_start)
    assert out["record"] == WORKER_GOLD["worker"]
    assert alive_at.get("Layer 4") == [] and alive_at.get("Layer 5") == [] and alive_at.get("Layer 6") == []


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

    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    real = FeatureFactory._persist_layer_output_groups

    def persist_and_hold(self: Any, frame: Any, *a: Any, **k: Any) -> Any:
        keep.append(frame)  # 模擬 r3.data 之殘留持有者
        return real(self, frame, *a, **k)

    monkeypatch.setattr(FeatureFactory, "_persist_layer_output_groups", persist_and_hold)
    _run_worker_inprocess(tmp_path, monkeypatch, on_start)
    assert alive.get("L3") is True
