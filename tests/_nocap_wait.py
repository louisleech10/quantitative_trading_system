"""測試內等候程序內背景工作（服務任務、回呼）之共用判定（NOCAP Task 2.2，docs/NOCAP_SPEC.md）：不設秒數上限；
卡死＝「被等候之狀態未變、且本程序 CPU 亦無進度（< 0.05 核）」持續達判準檔 `cell_rules.watchdog.log_stall_seconds`，
判定當下先寫全執行緒堆疊（faulthandler）再以 AssertionError 失敗——與共用監看（子行程）同一判準。

業界依據：批次運算之卡死以進度判定、不以固定牆鐘終止；固定秒數會把慢機或大資料上仍在前進之運算判失敗。
"""

from __future__ import annotations

import asyncio
import faulthandler
import tempfile
import time
from pathlib import Path
from typing import Any, Awaitable, Optional

from tests._nocap_subprocess import watchdog_config

CPU_PROGRESS_FRACTION = 0.05  # 同共用監看（handoffs/run_receipts/numview_probes/_watchdog.py）
_UNSET = object()


def stall_seconds() -> float:
    return float(watchdog_config().log_stall_seconds)


class ProgressWait:
    """每次輪詢呼叫 `check(state)`：state 改變或本程序 CPU 有進度即重新計時；無進度達 `stall` 秒 ⇒ 留堆疊後失敗。"""

    def __init__(self, label: str, stall: Optional[float] = None) -> None:
        self.label, self.stall = label, stall_seconds() if stall is None else float(stall)
        now = time.monotonic()
        self._state: Any = _UNSET
        self._last_change, self._prev_t, self._prev_cpu = now, now, time.process_time()

    def check(self, state: Any = None) -> None:
        now, cpu = time.monotonic(), time.process_time()
        if state != self._state or (now > self._prev_t and cpu - self._prev_cpu >= CPU_PROGRESS_FRACTION * (now - self._prev_t)):
            self._state, self._last_change = state, now
        self._prev_t, self._prev_cpu = now, cpu
        if now - self._last_change >= self.stall:
            stacks = Path(tempfile.mkstemp(prefix="nocap-wait-", suffix=".stacks.txt")[1])
            with stacks.open("w", encoding="utf-8") as fh:
                faulthandler.dump_traceback(file=fh, all_threads=True)
            raise AssertionError(f"{self.label} 卡死：狀態 {self._state!r} 未變且本程序 CPU 無進度達 {self.stall:g} 秒；"
                                 f"全執行緒堆疊 {stacks} （依堆疊查因，不得改回固定秒數）")


async def await_progressing(awaitable: Awaitable[Any], label: str, stall: Optional[float] = None,
                            poll: float = 0.05) -> Any:
    """等候 awaitable 完成（取代帶固定秒數上限之 asyncio 等候）；卡死判定同 `ProgressWait`（狀態恆為未完成，只看 CPU）。"""
    task = asyncio.ensure_future(awaitable)
    waiter = ProgressWait(label, stall)
    try:
        while not task.done():
            waiter.check(None)
            await asyncio.sleep(poll)
    except BaseException:
        task.cancel()
        raise
    return task.result()
