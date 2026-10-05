"""生成記憶體之獨立守護行程（docs/ICFIRSTALIGN_SPEC.md v29 Task 4.2「執行中守護（獨立行程）」與「子行程（預算域）」）。

以檔案路徑執行（`python <本檔> --pid <域根行程> --run-dir <域目錄> --run-id <lease key> --budget <bytes>`），
**只用標準函式庫與 ctypes**，不 import `momentum`、pandas、numpy、psutil（避免載入套件 `__init__`）。
每 0.5 秒讀：核心壓力等級、換頁卷剩餘空間、域成員之實測 footprint 合計——成員＝根＋遞迴子行程
（ctypes 呼叫 libproc `proc_listchildpids`；逐 pid `proc_pid_rusage`；以 (pid, 行程啟動時間) 去重，
守護自身與 resource tracker 已在其中、不另加）。只以實測判定，不以承諾量判終止。
第一段：壓力危急、或換頁卷剩餘 < 磁碟保留量、或全樹 footprint > 上限 ⇒ 於域目錄寫停止旗標。
第二段：旗標寫下後同一條件連續 2 次仍成立 ⇒ 寫 `memory_guard_abort.json`（各 pid 讀數）後，
依序對本域生成子行程、再對根行程 SIGKILL。收到停止訊號或根行程不存在 ⇒ 結束。
啟動後第一次讀數成功即於 stdout 印 `ready`（啟動端據以確認首讀；失敗即非 0 結束）。
測試接縫：環境變數 `ICFA_GUARD_READINGS_FILE`（JSONL；每次取樣依序取一列之 pressure_level／
swap_volume_free_bytes／footprint，用盡沿用末列）取代三項系統讀數。
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import signal
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

STOP_FLAG_NAME = "memory_guard_stop.flag"
ABORT_RECEIPT_NAME = "memory_guard_abort.json"
OWNED_PATHS_NAME = "owned_paths.json"
PRESSURE_CRITICAL_LEVEL = 4
DISK_RESERVE_MIN_BYTES = 4 << 30
DISK_RESERVE_FRACTION = 0.05
CONSECUTIVE_FOR_KILL = 2
SWAP_VOLUME = "/System/Volumes/VM"
READINGS_ENV = "ICFA_GUARD_READINGS_FILE"

_STOP = False


class _RusageInfoV0(ctypes.Structure):
    _fields_ = [("uuid", ctypes.c_uint8 * 16)] + [(f"f{i}", ctypes.c_uint64) for i in range(10)]


def _handle_term(signum: int, frame: Any) -> None:  # noqa: ARG001
    global _STOP
    _STOP = True


class _System:
    """真實讀數（macOS libproc／sysctl／statvfs）。"""

    def __init__(self) -> None:
        self.proc = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
        self.libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)

    def rusage(self, pid: int) -> Optional[Tuple[int, int]]:
        info = _RusageInfoV0()
        rc = self.proc.proc_pid_rusage(int(pid), 0, ctypes.byref(info))
        if rc != 0:
            return None
        return int(info.f7), int(info.f8)  # phys_footprint, start_abstime

    def children(self, pid: int) -> List[int]:
        buf = (ctypes.c_int * 4096)()
        n = self.proc.proc_listchildpids(int(pid), buf, ctypes.sizeof(buf))
        if n <= 0:
            return []
        return [int(buf[i]) for i in range(min(int(n), 4096)) if int(buf[i]) > 0]

    def tree(self, root: int) -> List[int]:
        out, stack, seen = [], [root], set()
        while stack:
            pid = stack.pop()
            if pid in seen:
                continue
            seen.add(pid)
            out.append(pid)
            stack.extend(self.children(pid))
        return out

    def pressure(self) -> int:
        value = ctypes.c_int64(0)
        size = ctypes.c_size_t(ctypes.sizeof(value))
        rc = self.libc.sysctlbyname(b"kern.memorystatus_vm_pressure_level", ctypes.byref(value), ctypes.byref(size),
                                    None, 0)
        if rc != 0:
            raise OSError("sysctl kern.memorystatus_vm_pressure_level 失敗")
        return int(ctypes.c_int32(value.value & 0xFFFFFFFF).value) if size.value == 4 else int(value.value)

    def swap_volume(self) -> Tuple[int, int]:
        st = os.statvfs(SWAP_VOLUME if os.path.isdir(SWAP_VOLUME) else "/")
        return int(st.f_bavail) * int(st.f_frsize), int(st.f_blocks) * int(st.f_frsize)


class _Readings:
    """一次取樣：(pressure, swap_free, swap_capacity, members[(pid, start, footprint)], 失敗 pid)。"""

    def __init__(self, system: _System, root: int) -> None:
        self.system = system
        self.root = root
        self._rows: Optional[List[Dict[str, Any]]] = None
        self._pos = 0
        path = os.environ.get(READINGS_ENV, "").strip()
        if path:
            with open(path, "r", encoding="utf-8") as handle:
                self._rows = [json.loads(line) for line in handle if line.strip()]

    def members(self) -> Tuple[List[Tuple[int, int, int]], List[int]]:
        out: Dict[Tuple[int, int], Tuple[int, int, int]] = {}
        failed: List[int] = []
        for pid in self.system.tree(self.root):
            reading = self.system.rusage(pid)
            if reading is None:
                if _alive(pid):
                    failed.append(pid)
                continue
            footprint, start = reading
            out.setdefault((pid, start), (pid, start, footprint))
        return list(out.values()), failed

    def sample(self) -> Dict[str, Any]:
        members, failed = self.members()
        _, capacity = self.system.swap_volume()
        if self._rows:
            row = self._rows[min(self._pos, len(self._rows) - 1)]
            self._pos += 1
            return {"pressure_level": int(row.get("pressure_level", 1)),
                    "swap_volume_free_bytes": int(row.get("swap_volume_free_bytes", 1 << 60)),
                    "swap_volume_capacity_bytes": capacity, "footprint": int(row.get("footprint", 0)),
                    "members": [], "failed": [], "injected": True}
        free, capacity = self.system.swap_volume()
        return {"pressure_level": self.system.pressure(), "swap_volume_free_bytes": free,
                "swap_volume_capacity_bytes": capacity, "footprint": sum(m[2] for m in members),
                "members": [{"pid": m[0], "start": m[1], "footprint": m[2]} for m in members], "failed": failed}


def _alive(pid: int) -> bool:
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _trigger(reading: Dict[str, Any], budget: int) -> Optional[str]:
    reserve = max(DISK_RESERVE_MIN_BYTES, int(int(reading["swap_volume_capacity_bytes"]) * DISK_RESERVE_FRACTION))
    if int(reading["pressure_level"]) >= PRESSURE_CRITICAL_LEVEL:
        return "pressure_critical"
    if int(reading["swap_volume_free_bytes"]) < reserve:
        return "swap_volume_low"
    if reading.get("failed"):
        return "measurement_failed"
    if int(reading["footprint"]) > int(budget):
        return "footprint_over_budget"
    return None


def _write_atomic(path: str, text: str) -> None:
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _read_text(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip() or None
    except OSError:
        return None


def _owned_paths(run_dir: str) -> List[str]:
    try:
        with open(os.path.join(run_dir, OWNED_PATHS_NAME), "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return [str(p) for p in data] if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _abort(args: argparse.Namespace, system: _System, trigger: str, history: List[Dict[str, Any]]) -> None:
    receipt = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "trigger": trigger, "run_id": args.run_id, "root_pid": args.pid,
        "guard_pid": os.getpid(), "budget": args.budget, "readings": history[-5:],
        "last_checkpoint": _read_text(args.checkpoint_file), "owned_paths": _owned_paths(args.run_dir),
    }
    _write_atomic(os.path.join(args.run_dir, ABORT_RECEIPT_NAME), json.dumps(receipt, ensure_ascii=False, default=str))
    own = os.getpid()
    descendants = [p for p in system.tree(args.pid) if p not in (own, args.pid)]
    for pid in descendants:
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    try:
        os.kill(args.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def main(argv: Optional[List[str]] = None) -> int:
    """守護主迴圈。"""
    parser = argparse.ArgumentParser(description="ICFIRSTALIGN 生成記憶體守護")
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--budget", type=int, required=True)
    parser.add_argument("--checkpoint-file", default=None)
    parser.add_argument("--interval", type=float, default=0.5)
    args = parser.parse_args(argv)
    signal.signal(signal.SIGTERM, _handle_term)
    signal.signal(signal.SIGINT, _handle_term)
    if sys.platform != "darwin":
        print(f"unsupported platform {sys.platform}", file=sys.stderr)
        return 2
    try:
        system = _System()
        readings = _Readings(system, args.pid)
        first = readings.sample()
    except Exception as exc:  # noqa: BLE001 — 首讀失敗即具名結束（啟動端拒絕生成）
        print(f"first reading failed: {exc}", file=sys.stderr)
        return 3
    sys.stdout.write("ready\n")
    sys.stdout.flush()
    history: List[Dict[str, Any]] = []
    flag_written = False
    consecutive = 0
    reading: Optional[Dict[str, Any]] = first
    parent = os.getppid()
    while not _STOP:
        if reading is None:
            try:
                reading = readings.sample()
            except Exception as exc:  # noqa: BLE001 — 讀數失敗以具名原因停止
                reading = {"pressure_level": 0, "swap_volume_free_bytes": 1 << 62, "swap_volume_capacity_bytes": 0,
                           "footprint": 0, "failed": [f"error:{exc}"]}
        history.append(reading)
        history = history[-20:]
        trigger = _trigger(reading, args.budget)
        if trigger is not None:
            if not flag_written:
                _write_atomic(os.path.join(args.run_dir, STOP_FLAG_NAME), trigger)
                flag_written = True
                consecutive = 0
            else:
                consecutive += 1
                if consecutive >= CONSECUTIVE_FOR_KILL:
                    _abort(args, system, trigger, history)
                    return 0
        else:
            consecutive = 0
        reading = None
        deadline = time.monotonic() + max(args.interval, 0.05)
        while not _STOP and time.monotonic() < deadline:
            time.sleep(0.05)
        if not _alive(args.pid) or os.getppid() != parent:
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
