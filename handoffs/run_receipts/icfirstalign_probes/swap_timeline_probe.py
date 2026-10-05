"""ICFIRSTALIGN 改向（使用者 2026-10-05：以前靠換頁跑完者不得卡死）之實測收據：以指定樹之碼跑 pytest 節點，期間每
0.5 秒記錄整個行程樹之 phys_footprint 合計、核心壓力等級、換頁用量（vm.swapusage）與換頁卷剩餘空間，逐筆寫 jsonl；
結束寫摘要（耗時、rc、各量之極值、壓力等級分佈、pytest 結果行）。讀數沿用 `memory_guard._System`（stdlib＋ctypes）。

用法：venv/bin/python handoffs/run_receipts/icfirstalign_probes/swap_timeline_probe.py <樹根> <輸出前綴> <pytest 節點…>
（不受本程式之記憶體預算約束：本探針只觀測，不設上限；外部停損＝換頁卷剩餘 < 4 GiB 即終止受測行程樹）
"""

from __future__ import annotations

import ctypes
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[3]
STOP_SWAP_VOLUME_FREE = 4 << 30


def _guard_module() -> Any:
    spec = importlib.util.spec_from_file_location("icfa_guard", REPO / "momentum/FeatureEngineering/memory_guard.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _XswUsage(ctypes.Structure):
    _fields_ = [("total", ctypes.c_uint64), ("avail", ctypes.c_uint64), ("used", ctypes.c_uint64),
                ("pagesize", ctypes.c_uint32), ("encrypted", ctypes.c_bool)]


def _swapusage(libc: Any) -> Dict[str, int]:
    usage = _XswUsage()
    size = ctypes.c_size_t(ctypes.sizeof(usage))
    if libc.sysctlbyname(b"vm.swapusage", ctypes.byref(usage), ctypes.byref(size), None, 0) != 0:
        return {"swap_total": -1, "swap_used": -1, "swap_avail": -1}
    return {"swap_total": int(usage.total), "swap_used": int(usage.used), "swap_avail": int(usage.avail)}


def main(argv: List[str]) -> int:
    tree, prefix, nodes = Path(argv[0]).resolve(), Path(argv[1]), argv[2:]
    guard = _guard_module()
    system = guard._System()
    env = {**os.environ, "PYTHONPATH": str(tree)}
    cmd = [str(REPO / "venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "log_cli=false",
           "--tb=line", *nodes]
    started = time.monotonic()
    log_path = prefix.with_suffix(".pytest.log")
    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.Popen(cmd, cwd=str(tree), env=env, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)
    series_path = prefix.with_suffix(".jsonl")
    peaks: Dict[str, Any] = {"footprint_max": 0, "pressure_max": 0, "swap_used_max": 0, "swap_total_max": 0,
                             "swap_volume_free_min": None, "pressure_counts": {}}
    stopped_reason = None
    with open(series_path, "w", encoding="utf-8") as series:
        while proc.poll() is None:
            pids = system.tree(proc.pid)
            footprint = sum((system.rusage(pid) or (0, 0))[0] for pid in pids)
            pressure = system.pressure()
            volume_free, _ = system.swap_volume()
            swap = _swapusage(system.libc)
            row = {"t": round(time.monotonic() - started, 2), "footprint": footprint, "pids": len(pids),
                   "pressure": pressure, "swap_volume_free": volume_free, **swap}
            series.write(json.dumps(row) + "\n")
            series.flush()
            peaks["footprint_max"] = max(peaks["footprint_max"], footprint)
            peaks["pressure_max"] = max(peaks["pressure_max"], pressure)
            peaks["pressure_counts"][str(pressure)] = peaks["pressure_counts"].get(str(pressure), 0) + 1
            peaks["swap_used_max"] = max(peaks["swap_used_max"], swap["swap_used"])
            peaks["swap_total_max"] = max(peaks["swap_total_max"], swap["swap_total"])
            low = peaks["swap_volume_free_min"]
            peaks["swap_volume_free_min"] = volume_free if low is None else min(low, volume_free)
            if volume_free < STOP_SWAP_VOLUME_FREE:
                stopped_reason = "swap_volume_free_below_4GiB"
                os.killpg(proc.pid, signal.SIGKILL)
                break
            time.sleep(0.5)
    rc = proc.wait()
    tail = [line.strip() for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()][-6:]
    summary = {"schema_version": 1, "tree": str(tree), "nodes": nodes, "rc": rc,
               "elapsed_seconds": round(time.monotonic() - started, 1), "stopped_reason": stopped_reason,
               "footprint_max_gib": round(peaks["footprint_max"] / (1 << 30), 3),
               "swap_used_max_gib": round(peaks["swap_used_max"] / (1 << 30), 3),
               "swap_total_max_gib": round(peaks["swap_total_max"] / (1 << 30), 3),
               "swap_volume_free_min_gib": None if peaks["swap_volume_free_min"] is None
               else round(peaks["swap_volume_free_min"] / (1 << 30), 3),
               "pressure_max": peaks["pressure_max"], "pressure_counts": peaks["pressure_counts"],
               "pytest_tail": tail}
    prefix.with_suffix(".summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n",
                                                   encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
