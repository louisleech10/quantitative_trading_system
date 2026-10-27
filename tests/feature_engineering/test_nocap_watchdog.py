"""NOCAP Task 0.1 v4/v5 增修（docs/NOCAP_SPEC.md）：共用監看於 CPU 讀不到時不誤殺、卡死時終止整個行程群組。

秒級、不跑重型：子行程皆為數秒內之 python -c 小程式。施工前為紅（現行 `_watchdog.py` 於 CPU 讀不到時以 log 停滯
判 STALLED、`_terminate` 只對根行程送信號）。
"""

from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path
from typing import Any, List

import psutil
import pytest

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("nocap_watchdog_under_test",
                                               REPO / "handoffs" / "run_receipts" / "numview_probes" / "_watchdog.py")
wd = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = wd  # dataclass 需模組已登記
_spec.loader.exec_module(wd)  # type: ignore[union-attr]


def _config(**overrides: Any) -> Any:
    base = {"check_interval_seconds": 0.05, "log_stall_seconds": 0.4, "swap_growth_fraction_of_ram": 0.125,
            "swap_consecutive_checks": 2, "wall_multiple_of_expected": 3.0, "wall_ceiling_seconds": 30.0}
    return wd.WatchdogConfig(**{**base, **overrides})


_BUSY_SILENT = [sys.executable, "-c", "import time\nt = time.perf_counter()\nwhile time.perf_counter() - t < 2.0:\n    pass"]


def _pids_from(path: Path) -> List[int]:
    return [int(x) for x in path.read_text(encoding="utf-8").split()] if path.is_file() else []


def _alive(pids: List[int], settle: float = 5.0) -> List[int]:
    """`settle` 秒內仍存活（非殭屍）之 pid。"""
    end = time.monotonic() + settle
    alive = list(pids)
    while alive and time.monotonic() < end:
        alive = [p for p in alive if psutil.pid_exists(p) and psutil.Process(p).status() != psutil.STATUS_ZOMBIE]
        time.sleep(0.05)
    return alive


def _kill_all(pids: List[int]) -> None:
    for p in pids:
        try:
            os.kill(p, 9)
        except OSError:
            pass


def _tree_program(pid_file: Path, extra: str = "") -> List[str]:
    code = (
        "import os, signal, subprocess, sys, time\n"
        f"pf = {str(pid_file)!r}\n"
        "kid = subprocess.Popen([sys.executable, '-c', 'import time\\ntime.sleep(60)'])\n"
        "open(pf, 'a').write(f'{os.getpid()} {kid.pid} ')\n"
        f"{extra}"
        "time.sleep(60)\n"
    )
    return [sys.executable, "-c", code]


def test_boundary_01_cpu_unreadable_busy_silent_child_not_stalled(tmp_path: Path) -> None:
    """CPU 讀不到（probe_cpu 回 None）而子行程無輸出忙算 2 秒（逾 log_stall_seconds 0.4 秒）⇒ 不判卡死、正常結束，
    結果記 monitor_degraded（使用者 2026-10-27「講幾千次不準再因為時間上限問題被停掉」）。"""
    result = wd.run_watched(_BUSY_SILENT, log_path=tmp_path / "busy.log", config=_config(),
                            probe_swap=lambda: 0.0, probe_cpu=lambda _pid: None)
    assert result.status == wd.EXITED and result.returncode == 0, result
    assert result.diagnosis.get("monitor_degraded"), result


def test_boundary_02_cpu_unreadable_memory_evidence_still_stalls(tmp_path: Path) -> None:
    """CPU 讀不到、但 swap 連續增長逾門檻 ⇒ 仍判 STALLED 且 cause=memory（記憶體證據不因監看降級而失效）。"""
    used = iter([0.0] + [10_000.0] * 1000)
    result = wd.run_watched(_BUSY_SILENT, log_path=tmp_path / "mem.log", config=_config(),
                            probe_swap=lambda: next(used), probe_ram=lambda: 8_000.0, probe_cpu=lambda _pid: None)
    assert result.status == wd.STALLED and result.cause == wd.CAUSE_MEMORY, result


def test_boundary_03_stall_terminates_whole_tree(tmp_path: Path) -> None:
    """父行程啟動無輸出睡眠子行程、整樹無 log 亦無 CPU ⇒ STALLED 返回時根與子孫皆已結束。"""
    pf = tmp_path / "pids.txt"
    result = wd.run_watched(_tree_program(pf), log_path=tmp_path / "tree.log", config=_config(), probe_swap=lambda: 0.0)
    pids = _pids_from(pf)
    try:
        assert result.status == wd.STALLED, result
        assert len(pids) == 2 and _alive(pids) == [], (pids, result)
    finally:
        _kill_all(pids)


def test_boundary_04_child_forked_on_sigterm_is_also_terminated(tmp_path: Path) -> None:
    """父行程收到 SIGTERM 時再 fork 一個子行程（快照之後才出現）⇒ 該新子行程亦已結束（行程群組終止）。"""
    pf = tmp_path / "pids.txt"
    extra = ("def _on_term(*_):\n"
             "    late = subprocess.Popen([sys.executable, '-c', 'import time\\ntime.sleep(60)'])\n"
             "    open(pf, 'a').write(f'{late.pid} ')\n"
             "    time.sleep(30)\n"
             "signal.signal(signal.SIGTERM, _on_term)\n")
    result = wd.run_watched(_tree_program(pf, extra), log_path=tmp_path / "late.log", config=_config(),
                            probe_swap=lambda: 0.0)
    pids = _pids_from(pf)
    try:
        assert result.status == wd.STALLED, result
        assert len(pids) == 3 and _alive(pids) == [], (pids, result)
    finally:
        _kill_all(pids)


def test_boundary_05_grandchild_that_called_setsid_is_terminated(tmp_path: Path) -> None:
    """子行程自行 setsid 脫離群組 ⇒ 仍被終止（送信號前後各取快照補殺脫離者）。"""
    pf = tmp_path / "pids.txt"
    code = (
        "import os, subprocess, sys, time\n"
        f"pf = {str(pf)!r}\n"
        "kid = subprocess.Popen([sys.executable, '-c', 'import os, time\\nos.setsid()\\ntime.sleep(60)'])\n"
        "open(pf, 'a').write(f'{os.getpid()} {kid.pid} ')\n"
        "time.sleep(60)\n"
    )
    result = wd.run_watched([sys.executable, "-c", code], log_path=tmp_path / "setsid.log", config=_config(),
                            probe_swap=lambda: 0.0)
    pids = _pids_from(pf)
    try:
        assert result.status == wd.STALLED, result
        assert len(pids) == 2 and _alive(pids) == [], (pids, result)
    finally:
        _kill_all(pids)


def test_mutation_root_only_terminate_leaves_child_alive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：終止退回只殺根行程 ⇒ 子行程存活（boundary 03 之鑑別力；施工後之整樹終止函式名須為 `_terminate`）。"""
    def root_only(proc: Any, *a: Any, **k: Any) -> Any:
        proc.kill()
        return proc.wait()

    monkeypatch.setattr(wd, "_terminate", root_only)
    pf = tmp_path / "pids.txt"
    wd.run_watched(_tree_program(pf), log_path=tmp_path / "m.log", config=_config(), probe_swap=lambda: 0.0)
    pids = _pids_from(pf)
    try:
        assert len(pids) == 2 and _alive(pids[1:], settle=0.5) == pids[1:]
    finally:
        _kill_all(pids)


def test_short_command_returns_without_waiting_full_check_interval(tmp_path: Path) -> None:
    """判準之檢查間隔 30 秒下，秒級短命令（閘門之 collect-only、hook）結束即返回，不空等滿一個間隔（b3 審碼前實測發現：
    原迴圈固定睡滿間隔 ⇒ 每次 pytest 子行程至少 30 秒）。效能斷言：5 秒內返回、rc 0。"""
    res = wd.run_watched([sys.executable, "-c", "pass"], log_path=tmp_path / "short.log",
                         config=_config(check_interval_seconds=30.0, log_stall_seconds=600.0))
    assert res.status == wd.EXITED and res.returncode == 0 and res.wall_seconds < 5.0, res
