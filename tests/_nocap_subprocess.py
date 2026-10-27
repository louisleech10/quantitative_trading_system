"""測試內等候受測子行程之共用入口（NOCAP Task 2.2，docs/NOCAP_SPEC.md）：經共用監看執行——不設牆鐘；卡死以「無 log
亦無 CPU 進度」判定（門檻同判準檔 `cell_rules.watchdog`），終止前留現場（全執行緒堆疊）後以 AssertionError 失敗。

取代測試中帶固定秒數上限之 `subprocess.run(..., capture_output=True, text=True)`：受測運算在慢機或大資料上可能合法地
跑很久，固定秒數會把仍在前進之運算判失敗；真正卡住（死結、等不到的事件）則由進度判定抓到並附堆疊。
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path) -> Any:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _watchdog() -> Any:
    return _load("nocap_tests_watchdog", REPO / "handoffs" / "run_receipts" / "numview_probes" / "_watchdog.py")


def watchdog_config() -> Any:
    """共用監看設定（與 `scripts/run_watched.py` 同源；測試可 monkeypatch 本函式注入小門檻）。"""
    rw = _load("nocap_tests_run_watched", REPO / "scripts" / "run_watched.py")
    return _watchdog().load_config(rw._criteria())


def run_watched_subprocess(cmd: Sequence[str], *, cwd: Optional[str] = None,
                           env: Optional[Mapping[str, str]] = None) -> subprocess.CompletedProcess:
    """經共用監看執行 `cmd`，回與 `subprocess.run(capture_output=True, text=True)` 同形之結果（stdout、stderr 分開）。
    卡死 ⇒ AssertionError（訊息含堆疊檔路徑；依堆疊查因，不得改回固定秒數）。"""
    wd = _watchdog()
    work = Path(tempfile.mkdtemp(prefix="nocap-test-"))
    out, err = work / "stdout.log", work / "stderr.log"
    res = wd.run_watched(list(cmd), log_path=out, config=watchdog_config(), cwd=None if cwd is None else str(cwd),
                         env=None if env is None else dict(env), stderr_path=err)
    stdout = out.read_text(encoding="utf-8", errors="replace") if out.exists() else ""
    stderr = err.read_text(encoding="utf-8", errors="replace") if err.exists() else ""
    if res.status != wd.EXITED:
        stacks = (res.diagnosis or {}).get("stacks_file") or f"{out}.stacks.txt"
        raise AssertionError(f"受測子行程卡死（{res.reason}；原因 {res.cause}）：堆疊 {stacks} ；stderr 尾段 {stderr[-1500:]}")
    return subprocess.CompletedProcess(list(cmd), res.returncode, stdout, stderr)
