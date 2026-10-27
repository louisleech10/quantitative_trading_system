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


def test_normal_exit_during_nap_not_recorded_degraded(tmp_path: Path) -> None:
    """CPU 讀得到、子行程於檢查間隔中途正常結束 ⇒ 不得記 monitor_degraded。`_nap` 偵測結束時之 poll() 已回收行程，
    若續讀 CPU 必得 None（行程已不存在），那是結束而非讀不到；2026-10-27 NOCAP 重型受影響測試全綠之 log 尾即誤記一行降級。"""
    result = wd.run_watched([sys.executable, "-c", "import time\ntime.sleep(1.0)"], log_path=tmp_path / "exit.log",
                            config=_config(check_interval_seconds=0.5), probe_swap=lambda: 0.0)
    assert result.status == wd.EXITED and result.returncode == 0, result
    assert "monitor_degraded" not in result.diagnosis, result
    assert "監看降級" not in (tmp_path / "exit.log").read_text(encoding="utf-8")


def test_exit_while_reading_cpu_not_recorded_degraded(tmp_path: Path) -> None:
    """子行程於讀 CPU 當下結束（迴圈內 poll 時仍存活、讀取回 None 時已結束）⇒ 亦不得記 monitor_degraded。"""
    calls: List[int] = []

    def probe(_pid: int) -> Any:
        calls.append(_pid)
        if len(calls) == 1:  # 迴圈前之基準讀數
            return 0.0
        time.sleep(1.5)  # 讀取期間子行程（睡 0.5 秒）結束
        return None

    result = wd.run_watched([sys.executable, "-c", "import time\ntime.sleep(0.5)"], log_path=tmp_path / "race.log",
                            config=_config(), probe_swap=lambda: 0.0, probe_cpu=probe)
    assert result.status == wd.EXITED and result.returncode == 0, result
    assert len(calls) >= 2, calls
    assert "monitor_degraded" not in result.diagnosis, result


_UNGUARDED_CHAINER = '''\
import importlib.machinery, importlib.util, os, sys
with open(os.environ["CHAIN_COUNT_FILE"], "a") as fh:
    fh.write("x\\n")
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.machinery.PathFinder.find_spec("sitecustomize", [p for p in sys.path if os.path.abspath(p or ".") != here])
if spec is not None and spec.loader is not None:
    spec.loader.exec_module(importlib.util.module_from_spec(spec))
'''


def test_sitecustomize_runs_once_when_another_injection_chains_back(tmp_path: Path) -> None:
    """子行程另有一個「串接下一個 sitecustomize」之注入且自身不防重入（例：覆蓋率／選測工具之 boot）⇒ 共用監看之
    sitecustomize 須同行程只執行一次，否則兩者互相串接至遞迴上限、子行程崩潰（TESTSEL 合入 main 時實測）。"""
    other = tmp_path / "other_site"
    other.mkdir()
    (other / "sitecustomize.py").write_text(_UNGUARDED_CHAINER, encoding="utf-8")
    count = tmp_path / "count.txt"
    env = dict(os.environ, PYTHONPATH=str(other), CHAIN_COUNT_FILE=str(count))
    result = wd.run_watched([sys.executable, "-c", "print('ok')"], log_path=tmp_path / "chain.log",
                            config=_config(), probe_swap=lambda: 0.0, env=env)
    assert result.status == wd.EXITED and result.returncode == 0, (result, (tmp_path / "chain.log").read_text())
    assert count.read_text().count("x") == 1


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


def test_setsid_grandchild_killed_even_if_enumeration_fails_at_termination(tmp_path: Path,
                                                                          monkeypatch: pytest.MonkeyPatch) -> None:
    """終止當下子孫列舉失敗（只得根行程；負載下 psutil 例外之情形）⇒ 仍以監看期間逐輪累積之子孫補殺自行 setsid 之孫行程
    （b3 審碼 r1 CODEX-R1-P1-02）。改壞（不累積、只靠終止當下快照）⇒ 孫行程存活。"""
    pf = tmp_path / "pids.txt"
    code = (
        "import os, subprocess, sys, time\n"
        f"pf = {str(pf)!r}\n"
        "kid = subprocess.Popen([sys.executable, '-c', 'import os, time\\nos.setsid()\\ntime.sleep(60)'])\n"
        "open(pf, 'a').write(f'{os.getpid()} {kid.pid} ')\n"
        "time.sleep(60)\n"
    )
    real_tree, broken = wd._tree, {"on": False}

    def flaky_tree(pid: int) -> Any:
        procs = real_tree(pid)
        return procs[:1] if broken["on"] else procs

    def diagnose_then_break(*a: Any, **k: Any) -> dict:
        broken["on"] = True  # 自留現場起，列舉只回根行程
        return {"cause": wd.CAUSE_HANG}

    monkeypatch.setattr(wd, "_tree", flaky_tree)
    result = wd.run_watched([sys.executable, "-c", code], log_path=tmp_path / "flaky.log", config=_config(),
                            probe_swap=lambda: 0.0, diagnose_fn=diagnose_then_break)
    pids = _pids_from(pf)
    try:
        assert result.status == wd.STALLED, result
        assert len(pids) == 2 and _alive(pids) == [], (pids, result)
    finally:
        _kill_all(pids)


def test_setsid_grandchild_killed_when_psutil_queries_denied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """沙箱／權限下 psutil 之 children、status、create_time 一律 AccessDenied（b3 審碼 r2 CODEX-R2-P1-01 之環境類）⇒
    子孫改由 `ps` 列舉、存活改以 os.kill(pid, 0) 判，自行 setsid 之孫行程仍被終止。"""
    def denied(self: Any, *a: Any, **k: Any) -> Any:
        raise psutil.AccessDenied(self.pid)

    monkeypatch.setattr(psutil.Process, "children", denied)
    monkeypatch.setattr(psutil.Process, "status", denied)
    monkeypatch.setattr(psutil.Process, "create_time", denied)
    pf = tmp_path / "pids.txt"
    code = (
        "import os, subprocess, sys, time\n"
        f"pf = {str(pf)!r}\n"
        "kid = subprocess.Popen([sys.executable, '-c', 'import os, time\\nos.setsid()\\ntime.sleep(60)'])\n"
        "open(pf, 'a').write(f'{os.getpid()} {kid.pid} ')\n"
        "time.sleep(60)\n"
    )
    result = wd.run_watched([sys.executable, "-c", code], log_path=tmp_path / "denied.log", config=_config(),
                            probe_swap=lambda: 0.0)
    pids = _pids_from(pf)
    monkeypatch.undo()
    try:
        assert result.status == wd.STALLED, result
        assert len(pids) == 2 and _alive(pids) == [], (pids, result)
    finally:
        _kill_all(pids)


def _deny_psutil_and_ps(monkeypatch: pytest.MonkeyPatch) -> None:
    """模擬委員沙箱（b3 審碼 r3 實測：sysctl KERN_PROC_ALL 與啟動 ps 皆 PermissionError）。"""
    def denied(self: Any, *a: Any, **k: Any) -> Any:
        raise psutil.AccessDenied(self.pid)

    for name in ("children", "status", "create_time"):
        monkeypatch.setattr(psutil.Process, name, denied)
    real_run = wd.subprocess.run

    def no_ps(argv: Any, *a: Any, **k: Any) -> Any:
        if list(argv)[:1] == ["ps"]:
            raise PermissionError(1, "Operation not permitted", "ps")
        return real_run(argv, *a, **k)

    monkeypatch.setattr(wd.subprocess, "run", no_ps)


def _setsid_program(pf: Path) -> List[str]:
    return [sys.executable, "-c", (
        "import os, subprocess, sys, time\n"
        f"pf = {str(pf)!r}\n"
        "kid = subprocess.Popen([sys.executable, '-c', 'import os, time\\nos.setsid()\\ntime.sleep(60)'])\n"
        "open(pf, 'a').write(f'{os.getpid()} {kid.pid} ')\n"
        "time.sleep(60)\n")]


@pytest.mark.skipif(sys.platform != "darwin", reason="libproc 為 macOS 原生 API")
def test_setsid_grandchild_killed_via_libproc_when_psutil_and_ps_denied(tmp_path: Path,
                                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    """psutil 與 ps 皆被拒（委員沙箱實況）⇒ 以 libproc.proc_listchildpids 列舉子孫，自行 setsid 之孫行程仍被終止。"""
    _deny_psutil_and_ps(monkeypatch)
    pf = tmp_path / "pids.txt"
    result = wd.run_watched(_setsid_program(pf), log_path=tmp_path / "libproc.log", config=_config(),
                            probe_swap=lambda: 0.0)
    pids = _pids_from(pf)
    monkeypatch.undo()
    try:
        assert result.status == wd.STALLED and "descendant_enumeration_unavailable" not in result.diagnosis, result
        assert len(pids) == 2 and _alive(pids) == [], (pids, result)
    finally:
        _kill_all(pids)


def test_enumeration_unavailable_is_reported_not_silent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """psutil、libproc、ps 皆不可用 ⇒ 終止後於 diagnosis 明記 `descendant_enumeration_unavailable`、log 亦寫一行（不靜默）。"""
    _deny_psutil_and_ps(monkeypatch)
    monkeypatch.setattr(wd, "_libproc_descendants", lambda pid: None)
    pf = tmp_path / "pids.txt"
    result = wd.run_watched(_setsid_program(pf), log_path=tmp_path / "none.log", config=_config(),
                            probe_swap=lambda: 0.0)
    pids = _pids_from(pf)
    monkeypatch.undo()
    try:
        assert result.status == wd.STALLED and "descendant_enumeration_unavailable" in result.diagnosis, result
        assert "子孫列舉不可用" in (tmp_path / "none.log").read_text(encoding="utf-8")
    finally:
        _kill_all(pids)


def test_mutation_no_accumulated_descendants_leaves_setsid_grandchild(tmp_path: Path,
                                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞對照：不用逐輪累積之子孫（`_seen_alive` 恆空）且終止當下列舉失敗 ⇒ 自行 setsid 之孫行程存活（上一案之鑑別力）。"""
    pf = tmp_path / "pids.txt"
    code = (
        "import os, subprocess, sys, time\n"
        f"pf = {str(pf)!r}\n"
        "kid = subprocess.Popen([sys.executable, '-c', 'import os, time\\nos.setsid()\\ntime.sleep(60)'])\n"
        "open(pf, 'a').write(f'{os.getpid()} {kid.pid} ')\n"
        "time.sleep(60)\n"
    )
    real_tree, broken = wd._tree, {"on": False}
    monkeypatch.setattr(wd, "_tree", lambda pid: real_tree(pid)[:1] if broken["on"] else real_tree(pid))
    monkeypatch.setattr(wd, "_seen_alive", lambda seen: [])

    def diagnose_then_break(*a: Any, **k: Any) -> dict:
        broken["on"] = True
        return {"cause": wd.CAUSE_HANG}

    wd.run_watched([sys.executable, "-c", code], log_path=tmp_path / "mut.log", config=_config(),
                   probe_swap=lambda: 0.0, diagnose_fn=diagnose_then_break)
    pids = _pids_from(pf)
    try:
        assert len(pids) == 2 and _alive(pids[1:], settle=0.5) == pids[1:]
    finally:
        _kill_all(pids)


def test_progress_wait_stalled_state_without_cpu_fails_with_stacks() -> None:
    """測試內程序內等候：狀態未變且 CPU 無進度達門檻 ⇒ AssertionError，訊息含堆疊檔且檔存在（NOCAP Task 2.2）。"""
    from tests._nocap_wait import ProgressWait

    waiter = ProgressWait("probe", stall=0.3)
    with pytest.raises(AssertionError) as exc:
        for _ in range(100):
            waiter.check("running")
            time.sleep(0.05)
    path = Path(str(exc.value).split("全執行緒堆疊 ", 1)[1].split(" ", 1)[0])
    assert "卡死" in str(exc.value) and path.exists()


def test_progress_wait_busy_cpu_is_not_stalled() -> None:
    """狀態未變但本程序在忙算（CPU 有進度）⇒ 不判卡死。"""
    from tests._nocap_wait import ProgressWait

    waiter = ProgressWait("busy", stall=0.3)
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 1.0:  # noqa: 忙算 1 秒（效能斷言外之受測負載）
        waiter.check("running")


def test_await_progressing_interrupts_synchronously_blocked_coroutine() -> None:
    """受測 coroutine 同步阻塞（未 yield）⇒ 獨立監看執行緒判卡死、留堆疊，只令本測試以 StallError（AssertionError）失敗、
    不中止 pytest 場次（b3 審碼 r1 CODEX-R1-P1-04、r2 CODEX-R2-P1-02）；處理器於等候結束後還原。"""
    import asyncio
    import signal as _signal

    from tests._nocap_wait import StallError, await_progressing

    async def blocked() -> None:
        time.sleep(30)

    before = _signal.getsignal(_signal.SIGUSR2)
    t0 = time.perf_counter()
    loop = asyncio.new_event_loop()  # 獨立 loop：asyncio.run 會清除全域 event loop，污染後續以 get_event_loop 之測試
    try:
        with pytest.raises(StallError, match="堆疊"):
            loop.run_until_complete(await_progressing(blocked(), "blocked", stall=0.3))
    finally:
        loop.close()
    assert time.perf_counter() - t0 < 10.0
    assert _signal.getsignal(_signal.SIGUSR2) is before


def test_run_watched_subprocess_separates_streams_and_fails_on_stall(monkeypatch: pytest.MonkeyPatch) -> None:
    """子行程 helper：stdout／stderr 分開（監看註記不入 stdout）；睡眠卡死 ⇒ AssertionError 附堆疊。"""
    import tests._nocap_subprocess as ns

    ok = ns.run_watched_subprocess([sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr)"])
    assert ok.returncode == 0 and ok.stdout.strip() == "out" and "err" in ok.stderr
    monkeypatch.setattr(ns, "watchdog_config", lambda: _config())
    with pytest.raises(AssertionError, match="卡死"):
        ns.run_watched_subprocess([sys.executable, "-c", "import time; time.sleep(30)"])


def test_short_command_returns_without_waiting_full_check_interval(tmp_path: Path) -> None:
    """判準之檢查間隔 30 秒下，秒級短命令（閘門之 collect-only、hook）結束即返回，不空等滿一個間隔（b3 審碼前實測發現：
    原迴圈固定睡滿間隔 ⇒ 每次 pytest 子行程至少 30 秒）。效能斷言：5 秒內返回、rc 0。"""
    res = wd.run_watched([sys.executable, "-c", "pass"], log_path=tmp_path / "short.log",
                         config=_config(check_interval_seconds=30.0, log_stall_seconds=600.0))
    assert res.status == wd.EXITED and res.returncode == 0 and res.wall_seconds < 5.0, res
