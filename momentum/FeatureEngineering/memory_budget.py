"""生成記憶體預算：取樣、配置前判定、分支表、選擇子正規化、磁碟後援、守護生命週期與強制停止後之恢復
（docs/ICFIRSTALIGN_SPEC.md v29 Task 4.2；取樣與預算判定之唯一實作）。

預算量＝致 OOM 之量：macOS `proc_pid_rusage(RUSAGE_INFO_V0)` 之 `ri_phys_footprint`（本行程＋守護行程）。
檔案映射於已確認磁碟後援時不計入；linux 暫不支援（`MemoryMeasurementUnavailable`）。
`check` 須三條件皆成立方放行：本程式 footprint＋planned ≤ 上限（實體記憶體 × ratio）、核心壓力等級非危急、
planned ≤ 系統可吸收量（free＋file-backed＋現有換頁剩餘；換頁擴充計 0）。

本模組不 import `momentum` 其他模組（producer 以模組屬性呼叫 `check`／`selector`／`layer_end` 等；測試以 monkeypatch 攔截），
亦不 import pandas（numpy 只供映射登記之型別判斷時延遲載入）。
"""

from __future__ import annotations

import contextlib
import contextvars
import ctypes
import hashlib
import json
import os
import plistlib
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Deque, Dict, Iterator, List, Literal, Mapping, Optional, Sequence, Tuple


class GenerationMemoryBudgetExceeded(RuntimeError):
    """配置前判定不通過（機器可用量不足〔選路後新增量 G 仍 > 剩餘可用量 A〕），或守護停止旗標已立。"""

    def __init__(self, label: str, current: int, planned: int, budget: int, reason: str) -> None:
        super().__init__(f"{reason}：{label} 目前 {current} B＋計畫 {planned} B，上限 {budget} B")
        self.label = label
        self.current = current
        self.planned = planned
        self.budget = budget
        self.reason = reason

    def __reduce__(self) -> Any:  # 跨行程（worker → 根）保留具名欄位
        return (GenerationMemoryBudgetExceeded, (self.label, self.current, self.planned, self.budget, self.reason))


class MemoryRerouteNeeded(GenerationMemoryBudgetExceeded):
    """域內 worker 配置前發現 `F_self + planned > E` 且原 E 內無白名單較小臂（SPEC v35）：尚未配置、未發布
    complete；根於該波次 join 後 rollback 並以正式串行 producer 重試一次。為 `GenerationMemoryBudgetExceeded` 之
    子類，使既有「預算錯誤原樣上拋、不降級」之各層路徑一律傳遞之。"""

    def __reduce__(self) -> Any:
        return (MemoryRerouteNeeded, (self.label, self.current, self.planned, self.budget, self.reason))


class MemoryMeasurementUnavailable(RuntimeError):
    """無法取得致 OOM 之量或無法確認磁碟後援（linux、其他平台、API 失敗、`Disk Image`、守護啟動失敗）。"""


class UnknownBudgetBranchError(KeyError):
    """分派點宣告之分支 ID 不在分支表或無估算函式（配置前具名拒絕）。"""


class SchedulerStopped(RuntimeError):
    """呼叫端已要求排程器停止（例：API wave 被取消）；該任務未准入、未執行。"""


ComponentKind = Literal["anon", "mapped"]

GiB = 1 << 30
MiB = 1 << 20

# 契約 tests/_golden/icfirstalign/contract.json 之 budget／budget_messages（同值）
RATIO_DEFAULT = 0.75
DISK_RESERVE_MIN_BYTES = 4 * GiB
# 磁碟保留量之換頁檔數（SPEC v36）：守護自首次觸發至終止之取樣數（旗標 1＋確認 2），每取樣最大磁碟下降實測為
# 一個換頁檔（收據 20261005-icfirstalign-swap-timeline-head.json 之逐筆序列）
DISK_RESERVE_SWAPFILES = 3
PRESSURE_CRITICAL_LEVEL = 4
GUARD_INTERVAL_SECONDS = 0.5
GUARD_CONSECUTIVE_FOR_KILL = 2
MSG_OWN_CAP = "本程式超上限"
MSG_MACHINE_INSUFFICIENT = "機器可用量不足"
MSG_SWAP_VOLUME_LOW = "換頁卷剩餘不足（磁碟將滿）"
MSG_MEASUREMENT_FAILED = "記憶體量測失敗"
MSG_ESTIMATE_EXCEEDED = "任務峰值估算低估"
# 換頁擴充上限之 sysctl（SPEC v35；讀不到 ⇒ 擴充計 0、記 memory_swap_expand_unreadable）
SWAPFILE_SYSCTLS = ("vm.compressor.swapper.swapfile_limit", "vm.compressor.swapper.swapfile_cnt",
                    "vm.compressor.swapper.swapfile_size_max")
REJECTED_BUS_PROTOCOLS = ("Disk Image",)
SWAP_VOLUME = "/System/Volumes/VM"
L2_SPILL_THRESHOLD_BYTES = 500_000_000  # FeatureFactory._spill_to_memmap 之 float64 估計門檻（同值）

# 子行程啟動之已核上界（收據 handoffs/run_receipts/20261005-icfirstalign-runtime-envelope.json：spawn worker 生涯峰值
# 215 MiB〔空 worker／多週期 worker／多標的 worker 三者最大〕、resource tracker 生涯峰值 9 MiB，各 × 1.5 上取整至 MiB）
WORKER_RUNTIME_ENVELOPE_BYTES = 323 * MiB
AUX_TRACKER_STARTUP_ENVELOPE_BYTES = 13 * MiB


@dataclass(frozen=True)
class Component:
    """估算成分：`anon`（不可回收配置）入 planned_bytes；`mapped`（檔案映射，宣告入口）不入。"""

    name: str
    kind: ComponentKind
    nbytes: int
    entry: Optional[str] = None
    count: int = 1
    # mapped 成分之生命期：`segment`＝於下一次 check 前釋放；`run`＝於該 run 之層結束前釋放（例 L2 spill）。
    lifetime: str = "segment"


@dataclass(frozen=True)
class VMSnapshot:
    """同一時點之系統讀數（`host_statistics64`、`vm.swapusage`、壓力等級、換頁卷）。"""

    free_bytes: int
    file_backed_bytes: int
    swap_free_bytes: int
    pressure_level: int
    swap_volume_free_bytes: int
    swap_volume_capacity_bytes: int
    # 換頁擴充上限（SPEC v35）：三者任一為 None ⇒ 讀不到、擴充計 0
    swapfile_limit: Optional[int] = None
    swapfile_count: Optional[int] = None
    swapfile_size_max: Optional[int] = None
    page_size: int = 16384


# 選擇子正規化（唯一一份；Task 4.2）：鍵 → 合法值。workers 為 "auto" 或正整數。
SELECTORS: Dict[str, Any] = {
    "FFACT_USE_POLARS": ("0", "1"),
    "FFACT_LAYER1_PARALLEL": ("0", "1"),
    "FFACT_L2_CATEGORY_WORKERS": "auto|positive_int",
    "FFACT_L3_PERSIST_MODE": ("auto", "streaming", "hybrid", "in_memory"),
    "FFACT_L3_STREAMING": ("0", "1"),
    "FFACT_L3_MULTI_WINDOW": ("0", "1"),
    "FFACT_USE_NUMBA_ROLLING": ("0", "1"),
    "FFACT_MEMORY_TIER": ("auto", "8gb", "16gb", "24gb", "32gb"),
    "FFACT_MULTI_TF_PARALLEL": ("0", "1"),
    "FFACT_MULTI_TF_MAX_WORKERS": "auto|positive_int",
    "FFACT_MULTI_TF_COMPACT_ALIGNMENT": ("0", "1"),
}

# 選擇子未設（或設為空字串）時之值：與各 producer 改前之預設相同。
SELECTOR_DEFAULTS: Dict[str, str] = {
    "FFACT_USE_POLARS": "1",
    "FFACT_LAYER1_PARALLEL": "0",
    "FFACT_L2_CATEGORY_WORKERS": "auto",
    "FFACT_L3_PERSIST_MODE": "auto",
    "FFACT_L3_STREAMING": "1",
    "FFACT_L3_MULTI_WINDOW": "1",
    "FFACT_USE_NUMBA_ROLLING": "1",
    "FFACT_MEMORY_TIER": "auto",
    "FFACT_MULTI_TF_PARALLEL": "1",
    "FFACT_MULTI_TF_MAX_WORKERS": "auto",
    "FFACT_MULTI_TF_COMPACT_ALIGNMENT": "1",
}

# 非臂選擇之 FFACT_ 鍵（具名排除清單；producer 模組 AST 掃描未列於兩清單之任一鍵 ⇒ 紅）。
NON_ARM_FFACT_KEYS: Sequence[str] = (
    "FFACT_USE_CGSA",                   # CGSA 開關（frame 路徑刪除屬 FRAMEPATH）
    "FFACT_CGSA_DISK_PRECHECK",         # 磁碟預檢開關
    "FFACT_CGSA_WORK_DIR",              # 工作目錄
    "FFACT_CGSA_MEMORY_BUFFER",         # registry 緩衝群組數（形狀參數）
    "FFACT_CGSA_SHARD_BYTES",           # 分片目標（形狀參數）
    "FFACT_CGSA_PIPELINE_PER_LAYER",    # 逐層管線開關（不改臂）
    "FFACT_LAYER1_MAX_WORKERS",         # L1 平行之實際 workers（形狀參數）
    "FFACT_LAYER3_CHUNK_SIZE",          # L3 chunk（形狀參數）
    "FFACT_L3_STREAMING_BUFFER_COLS",   # L3 persister 緩衝（形狀參數）
    "FFACT_L65_WORKERS",                # L6.5 workers
    "FFACT_L65_SPLIT_THRESHOLD",        # L6.5 大群組切分
    "FFACT_MULTI_TF_ALIGN_BLOCK_ROWS",  # 對齊區塊列數（形狀參數）
    "FFACT_MULTI_TF_KEEP_WORKER_NPY",   # 除錯
)

STOP_FLAG_NAME = "memory_guard_stop.flag"
ABORT_RECEIPT_NAME = "memory_guard_abort.json"
OWNED_PATHS_NAME = "owned_paths.json"
ESTIMATE_EXCEEDED_LOG_NAME = "memory_estimate_exceeded.jsonl"
MEMBERS_DIR_NAME = "members"
ROUTES_DIR_NAME = "routes"
GUARD_SCRIPT = Path(__file__).with_name("memory_guard.py")
GUARD_READINGS_ENV = "ICFA_GUARD_READINGS_FILE"
CHECK_LOG_ENV = "ICFA_CHECK_LOG"
BUDGET_RATIO_ENV = "FFACT_MEMORY_BUDGET_RATIO"
BUDGET_BYTES_ENV = "FFACT_MEMORY_BUDGET_BYTES"
PHYSICAL_BYTES_ENV = "ICFA_PHYSICAL_BYTES"


# ---------------------------------------------------------------- 執行情境（受保護 run／預算域）

@dataclass
class _RunContext:
    """本執行緒之預算情境。`mode`：`run`（受保護 run，守護＝本 run）／`root`（域根）／`worker`（域內任務）。"""

    mode: str
    stop_dir: Optional[Path]
    guard_pid: Optional[int] = None
    checkpoint_file: Optional[Path] = None
    mapping_root: Optional[Path] = None
    domain: Optional["DomainDescriptor"] = None
    run_dir: Optional[Path] = None
    # 選路紀錄（SPEC v35：切換與理由記入 run metadata `memory_route`）；巢狀情境以 `replace` 共用同一串列
    routes: List[Dict[str, Any]] = field(default_factory=list)


_ACTIVE:"contextvars.ContextVar[Optional[_RunContext]]" = contextvars.ContextVar("icfa_memory_context", default=None)
_SAMPLER_OVERRIDE: "contextvars.ContextVar[Optional[Callable[[], Mapping[str, int]]]]" = contextvars.ContextVar(
    "icfa_sampler_override", default=None)
_BUDGET_OVERRIDE: "contextvars.ContextVar[Optional[int]]" = contextvars.ContextVar("icfa_budget_override", default=None)
_VM_OVERRIDE: "contextvars.ContextVar[Optional[VMSnapshot]]" = contextvars.ContextVar("icfa_vm_override", default=None)
_RECORDERS: List[List[Tuple[str, List[Component]]]] = []
_RECORDERS_LOCK = threading.Lock()


def active_context() -> Optional[_RunContext]:
    """本執行緒目前之預算情境（無 ⇒ 單行程模式）。"""
    return _ACTIVE.get()


def current_mapping_root() -> Optional[Path]:
    """本執行緒受保護 run 之映射根（暫存 memmap 與校準暫存 registry 一律建於此下）；無受保護 run ⇒ None。"""
    ctx = _ACTIVE.get()
    return None if ctx is None else ctx.mapping_root


def current_run_dir() -> Optional[Path]:
    """本執行緒受保護 run 之 run 目錄（登記 owned paths 用）；無 ⇒ None。"""
    ctx = _ACTIVE.get()
    return None if ctx is None else ctx.run_dir


def record_route(entry: Mapping[str, Any]) -> Dict[str, Any]:
    """選路紀錄（SPEC v35「切換與理由記入 run metadata `memory_route`：分派點、臂、理由、G、A、F、R」；審碼 b3 r6
    codex P2-02）：附入本執行緒受保護 run 之紀錄（生成結果 metadata 由 `route_records` 取用），並寫選填診斷 log。"""
    record = {"event": "memory_route", "pid": os.getpid(), "time": time.time(), **dict(entry)}
    ctx = _ACTIVE.get()
    if ctx is not None:
        ctx.routes.append(record)
    _check_log(record)
    return record


def route_records() -> List[Dict[str, Any]]:
    """本執行緒受保護 run 至今之選路紀錄（無受保護 run ⇒ 空）。"""
    ctx = _ACTIVE.get()
    return [] if ctx is None else [dict(r) for r in ctx.routes]


# ---------------------------------------------------------------- 取樣（macOS libproc／mach）

class _RusageInfoV0(ctypes.Structure):
    _fields_ = [("uuid", ctypes.c_uint8 * 16)] + [(f"f{i}", ctypes.c_uint64) for i in range(10)]


class _RusageInfoV4(ctypes.Structure):
    _fields_ = [("uuid", ctypes.c_uint8 * 16)] + [(f"f{i}", ctypes.c_uint64) for i in range(40)]


class _VMStatistics64(ctypes.Structure):
    _fields_ = [("free_count", ctypes.c_uint32), ("active_count", ctypes.c_uint32), ("inactive_count", ctypes.c_uint32),
                ("wire_count", ctypes.c_uint32), ("zero_fill_count", ctypes.c_uint64), ("reactivations", ctypes.c_uint64),
                ("pageins", ctypes.c_uint64), ("pageouts", ctypes.c_uint64), ("faults", ctypes.c_uint64),
                ("cow_faults", ctypes.c_uint64), ("lookups", ctypes.c_uint64), ("hits", ctypes.c_uint64),
                ("purges", ctypes.c_uint64), ("purgeable_count", ctypes.c_uint32), ("speculative_count", ctypes.c_uint32),
                ("decompressions", ctypes.c_uint64), ("compressions", ctypes.c_uint64), ("swapins", ctypes.c_uint64),
                ("swapouts", ctypes.c_uint64), ("compressor_page_count", ctypes.c_uint32),
                ("throttled_count", ctypes.c_uint32), ("external_page_count", ctypes.c_uint32),
                ("internal_page_count", ctypes.c_uint32), ("total_uncompressed_pages_in_compressor", ctypes.c_uint64)]


class _XswUsage(ctypes.Structure):
    _fields_ = [("total", ctypes.c_uint64), ("avail", ctypes.c_uint64), ("used", ctypes.c_uint64),
                ("pagesize", ctypes.c_uint32), ("encrypted", ctypes.c_int)]


_LIBS: Dict[str, Any] = {}
_LIBS_LOCK = threading.Lock()


def _require_darwin() -> None:
    if sys.platform != "darwin":
        raise MemoryMeasurementUnavailable(
            f"生成記憶體預算量（致 OOM 之量）於平台 {sys.platform} 無法取得或核對（linux 暫不支援生成，§N）"
        )


def _lib(name: str) -> Any:
    with _LIBS_LOCK:
        lib = _LIBS.get(name)
        if lib is None:
            path = {"proc": "/usr/lib/libproc.dylib", "system": "/usr/lib/libSystem.B.dylib"}[name]
            try:
                lib = ctypes.CDLL(path, use_errno=True)
            except OSError as exc:
                raise MemoryMeasurementUnavailable(f"無法載入 {path}：{exc}") from exc
            if name == "system":
                lib.mach_host_self.restype = ctypes.c_uint32
            _LIBS[name] = lib
        return lib


def _rusage_v0(pid: int) -> _RusageInfoV0:
    _require_darwin()
    info = _RusageInfoV0()
    rc = _lib("proc").proc_pid_rusage(int(pid), 0, ctypes.byref(info))
    if rc != 0:
        raise MemoryMeasurementUnavailable(f"proc_pid_rusage(pid={pid}) rc={rc} errno={ctypes.get_errno()}")
    return info


def _read_rusage() -> Dict[str, int]:
    """本行程之 resident 與 phys_footprint（`sampler_override` 生效時回注入值）。"""
    override = _SAMPLER_OVERRIDE.get()
    if override is not None:
        values = dict(override())
        return {"resident": int(values["resident"]), "phys_footprint": int(values["phys_footprint"])}
    info = _rusage_v0(os.getpid())
    return {"resident": int(info.f6), "phys_footprint": int(info.f7)}


def sample_memory_bytes() -> int:
    """本行程致 OOM 之量（macOS `ri_phys_footprint`）；linux／其他平台／失敗 ⇒ `MemoryMeasurementUnavailable`。"""
    _require_darwin()
    return int(_read_rusage()["phys_footprint"])


def sample_footprint_of(pid: int) -> int:
    """他行程（同使用者）之 `ri_phys_footprint`；守護與目前用量（本行程＋守護）用。"""
    return int(_rusage_v0(pid).f7)


def process_start_time(pid: int) -> float:
    """行程啟動時刻（`ri_proc_start_abstime`，成員去重鍵之一）；取不到 ⇒ 0.0。"""
    try:
        return float(_rusage_v0(pid).f8)
    except MemoryMeasurementUnavailable:
        return 0.0


def _current_usage_bytes(guard_pid: Optional[int] = None) -> int:
    """目前用量＝本行程 footprint＋守護 footprint（`sampler_override` 生效時，注入值即目前用量之全部讀數）。"""
    if _SAMPLER_OVERRIDE.get() is not None:
        return sample_memory_bytes()
    own = sample_memory_bytes()
    if guard_pid is None:
        ctx = _ACTIVE.get()
        guard_pid = None if ctx is None else ctx.guard_pid
    if guard_pid:
        try:
            own += sample_footprint_of(int(guard_pid))
        except MemoryMeasurementUnavailable:
            if _pid_alive(int(guard_pid)):
                raise
    return own


def _sysctl_int(name: str) -> int:
    value = ctypes.c_int64(0)
    size = ctypes.c_size_t(ctypes.sizeof(value))
    rc = _lib("system").sysctlbyname(name.encode(), ctypes.byref(value), ctypes.byref(size), None, 0)
    if rc != 0:
        raise MemoryMeasurementUnavailable(f"sysctl {name} rc={rc}")
    if size.value == 4:
        return int(ctypes.c_int32(value.value & 0xFFFFFFFF).value)
    return int(value.value)


def sample_vm_snapshot() -> VMSnapshot:
    """同一時點之 VM 讀數；任一取不到 ⇒ `MemoryMeasurementUnavailable`。"""
    override = _VM_OVERRIDE.get()
    if override is not None:
        return override
    _require_darwin()
    system = _lib("system")
    stats = _VMStatistics64()
    count = ctypes.c_uint32(ctypes.sizeof(_VMStatistics64) // 4)
    rc = system.host_statistics64(system.mach_host_self(), 4, ctypes.byref(stats), ctypes.byref(count))
    if rc != 0:
        raise MemoryMeasurementUnavailable(f"host_statistics64 rc={rc}")
    page = _sysctl_int("hw.pagesize")
    swap = _XswUsage()
    size = ctypes.c_size_t(ctypes.sizeof(swap))
    if system.sysctlbyname(b"vm.swapusage", ctypes.byref(swap), ctypes.byref(size), None, 0) != 0:
        raise MemoryMeasurementUnavailable("sysctl vm.swapusage 失敗")
    pressure = _sysctl_int("kern.memorystatus_vm_pressure_level")
    volume = SWAP_VOLUME if os.path.isdir(SWAP_VOLUME) else "/"
    st = os.statvfs(volume)
    free_pages = max(int(stats.free_count) - int(stats.speculative_count), 0)
    limit, count, size_max = _swapfile_params()
    return VMSnapshot(
        free_bytes=free_pages * page,
        file_backed_bytes=int(stats.external_page_count) * page,
        swap_free_bytes=int(swap.avail),
        pressure_level=int(pressure),
        swap_volume_free_bytes=int(st.f_bavail) * int(st.f_frsize),
        swap_volume_capacity_bytes=int(st.f_blocks) * int(st.f_frsize),
        swapfile_limit=limit, swapfile_count=count, swapfile_size_max=size_max, page_size=int(page),
    )


def _swapfile_params() -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """換頁檔數上限、目前檔數、單檔上限（SPEC v35）；任一讀不到 ⇒ 三者皆 None（擴充計 0）。"""
    try:
        return tuple(_sysctl_int(name) for name in SWAPFILE_SYSCTLS)  # type: ignore[return-value]
    except MemoryMeasurementUnavailable:
        return None, None, None


def swap_expansion_readable(snapshot: VMSnapshot) -> bool:
    return None not in (snapshot.swapfile_limit, snapshot.swapfile_count, snapshot.swapfile_size_max)


def disk_reserve_bytes(swapfile_size_max: Optional[int] = None) -> int:
    """磁碟保留量（SPEC v36）＝max(4 GiB, 3 × 換頁檔單檔上限)；單檔上限讀不到 ⇒ 4 GiB。"""
    return max(DISK_RESERVE_MIN_BYTES, DISK_RESERVE_SWAPFILES * int(swapfile_size_max or 0))


def swap_expansion_bytes(snapshot: VMSnapshot) -> int:
    """可證換頁擴充 X＝min（剩餘檔數 × 單檔上限，換頁卷可用 − 磁碟保留量）；讀不到 ⇒ 0（SPEC v35／v36）。"""
    if not swap_expansion_readable(snapshot):
        return 0
    slots = max(int(snapshot.swapfile_limit) - int(snapshot.swapfile_count), 0) * int(snapshot.swapfile_size_max)
    room = max(int(snapshot.swap_volume_free_bytes) - disk_reserve_bytes(snapshot.swapfile_size_max), 0)
    return int(min(slots, room))


def available_bytes(snapshot: VMSnapshot) -> int:
    """剩餘可用量 A（SPEC v35）＝free＋file-backed＋現有換頁剩餘＋可證換頁擴充 X；匿名與壓縮器頁不計。"""
    return (int(snapshot.free_bytes) + int(snapshot.file_backed_bytes) + int(snapshot.swap_free_bytes)
            + swap_expansion_bytes(snapshot))


def system_absorbable_bytes(snapshot: VMSnapshot) -> int:
    """准入之可吸收量＝剩餘可用量 A（SPEC v35 取代「換頁擴充計 0」）。"""
    return available_bytes(snapshot)


def physical_memory_bytes() -> int:
    """實體記憶體（換機自動適用）；`ICFA_PHYSICAL_BYTES` 只供量測探針模擬。"""
    raw = os.environ.get(PHYSICAL_BYTES_ENV, "").strip()
    if raw:
        return int(raw)
    if sys.platform == "darwin":
        return _sysctl_int("hw.memsize")
    import psutil

    return int(psutil.virtual_memory().total)


def budget_bytes(physical_bytes: int, ratio: float = RATIO_DEFAULT, absolute_bytes: Optional[int] = None) -> int:
    """上限＝實體記憶體 × ratio；`absolute_bytes` 給定時以之覆寫。"""
    if absolute_bytes is not None:
        return int(absolute_bytes)
    return int(int(physical_bytes) * float(ratio))


def configured_budget_bytes(*, include_override: bool = True) -> int:
    """目前生效之上限：`budget_override`（測試接縫，只作用於 `check` 之判定）＞ 設定之絕對位元組 ＞
    設定之比例 × 實體記憶體（預設 0.75）。守護行程之上限以 `include_override=False` 取正式設定。"""
    override = _BUDGET_OVERRIDE.get() if include_override else None
    if override is not None:
        return int(override)
    absolute = os.environ.get(BUDGET_BYTES_ENV, "").strip()
    ratio_raw = os.environ.get(BUDGET_RATIO_ENV, "").strip()
    try:
        ratio = float(ratio_raw) if ratio_raw else RATIO_DEFAULT
        absolute_bytes = int(absolute) if absolute else None
    except ValueError as exc:
        raise ValueError(f"記憶體預算設定非法：{BUDGET_RATIO_ENV}={ratio_raw!r} {BUDGET_BYTES_ENV}={absolute!r}") from exc
    if not 0.0 < ratio <= 1.0:
        raise ValueError(f"{BUDGET_RATIO_ENV} 須介於 (0, 1]：{ratio}")
    return budget_bytes(physical_memory_bytes(), ratio, absolute_bytes)


def planned_bytes(components: Sequence[Component]) -> int:
    """planned_bytes 只加總 `anon` 成分（`mapped` 不入）。"""
    return int(sum(int(c.nbytes) * int(c.count) for c in components if c.kind == "anon"))


# ---------------------------------------------------------------- 選擇子

def normalize_selectors(env: Mapping[str, str]) -> Dict[str, str]:
    """選擇子正規化；非法或未知值 ⇒ `ValueError`（不得靜默退預設）。只處理 `SELECTORS` 之鍵；空字串＝未設。"""
    out: Dict[str, str] = {}
    for key, allowed in SELECTORS.items():
        raw = env.get(key)
        value = SELECTOR_DEFAULTS[key] if raw is None or str(raw).strip() == "" else str(raw).strip().lower()
        if allowed == "auto|positive_int":
            if value != "auto":
                try:
                    number = int(value)
                except ValueError:
                    raise ValueError(f"選擇子 {key} 非法值 {raw!r}（合法：auto 或正整數）") from None
                if number < 1:
                    raise ValueError(f"選擇子 {key} 非法值 {raw!r}（合法：auto 或正整數）")
                value = str(number)
        elif value not in tuple(allowed):
            raise ValueError(f"選擇子 {key} 非法值 {raw!r}（合法：{list(allowed)}）")
        out[key] = value
    return out


def selector(name: str) -> str:
    """producer 讀臂選擇子之唯一入口（自環境讀並正規化）。"""
    if name not in SELECTORS:
        raise KeyError(f"{name} 不在選擇子正規化清單")
    return normalize_selectors({name: os.environ.get(name, "")})[name]


def selector_flag(name: str) -> bool:
    """布林選擇子（值域 ("0", "1")）之真值。"""
    return selector(name) == "1"


# ---------------------------------------------------------------- 分支表（唯一一份）

def _i(params: Mapping[str, Any], key: str, default: int = 0) -> int:
    value = params.get(key, default)
    return int(default if value is None else value)


def _anon(name: str, nbytes: int, count: int = 1) -> Component:
    return Component(name=name, kind="anon", nbytes=max(int(nbytes), 0), count=int(count))


def _mapped(name: str, nbytes: int, entry: str, lifetime: str, count: int = 1) -> Component:
    return Component(name=name, kind="mapped", nbytes=max(int(nbytes), 0), entry=entry, count=max(int(count), 0),
                     lifetime=lifetime)


def _l1(params: Mapping[str, Any], *, parallel: bool) -> List[Component]:
    rows, out = _i(params, "rows"), _i(params, "output_cols")
    tables = "engine_tables" if parallel else "indicator_tables"
    return [_anon(tables, rows * out * 8), _anon("merged_return", rows * out * 8), _anon("persist_cast", rows * out * 4)]


def _l2_spill(params: Mapping[str, Any]) -> Component:
    rows, out = _i(params, "rows"), _i(params, "output_cols")
    spills = rows * out * 8 >= L2_SPILL_THRESHOLD_BYTES
    return _mapped("spill", rows * out * 4, "np.memmap", "run", count=1 if spills else 0)


def _l2_polars(params: Mapping[str, Any]) -> List[Component]:
    rows, out, max_cat = _i(params, "rows"), _i(params, "output_cols"), _i(params, "max_category_cols")
    return [_anon("return_table", rows * out * 8), _anon("max_category", rows * max_cat * 8),
            _anon("category_cast", rows * max_cat * 4), _l2_spill(params)]


def _l2_pandas(params: Mapping[str, Any]) -> List[Component]:
    rows, out = _i(params, "rows"), _i(params, "output_cols")
    cat_sum = _i(params, "category_cols_sum", out)
    max_cat = _i(params, "max_category_cols", out)
    return [_anon("category_tables_sum", rows * cat_sum * 8), _anon("merge_return", rows * out * 8),
            _anon("persist_cast", rows * max_cat * 4), _l2_spill(params)]


def _l3_fused(params: Mapping[str, Any]) -> List[Component]:
    rows, windows = _i(params, "rows"), max(_i(params, "windows", 1), 1)
    # numba_rolling.fused_rolling_stats_multi_window：每欄 (列, 窗, 10) float64；跨欄前一欄仍存活 ⇒ 兩份。
    # 核心 scratch：逐窗之 fused (列×6 float64＋float32 回傳)、skew/kurt (列×2)、rank、slope 與其 float64 轉型。
    scratch = rows * (6 * 8 + 6 * 4 + 6 * 8 + 2 * 8 * 2 + 8 * 2 + 8 * 2)
    return [_anon("fused_x2", 2 * rows * windows * 10 * 8), _anon("kernel_scratch", scratch)]


def _l3_multi_callback(params: Mapping[str, Any]) -> List[Component]:
    rows, chunk, steps = _i(params, "rows"), _i(params, "chunk_cols", 64), max(_i(params, "steps", 1), 1)
    buffer_cols = _i(params, "buffer_cols", chunk)
    return _l3_fused(params) + [
        _anon("step_results", rows * chunk * steps * 8 * 2),  # 逐 step 之 float64 統計＋float32 chunk 矩陣
        _anon("step_buffers", steps * rows * buffer_cols * 4),
        _anon("flush_overshoot", rows * (buffer_cols + chunk) * 4 * 2),  # flush 合併＋轉型
    ]


def _l3_multi_nocallback(params: Mapping[str, Any]) -> List[Component]:
    rows, out = _i(params, "rows"), _i(params, "output_cols")
    # 逐 step 累積之 chunk 矩陣與最末合併皆 float32（`np.column_stack(...).astype(float32)`、`pd.concat`）；落盤轉型逐
    # 5000 欄 chunk（`_persist_layer_output_groups`）
    return _l3_fused(params) + [_anon("accumulated_steps", rows * out * 4), _anon("final_concat", rows * out * 4),
                                _anon("persist_cast", rows * min(out, 5000) * 4)]


def _l3_vectorized(params: Mapping[str, Any]) -> List[Component]:
    rows, out = _i(params, "rows"), _i(params, "output_cols")
    chunk, windows = _i(params, "chunk_cols", _i(params, "input_cols")), max(_i(params, "windows", 1), 1)
    return [_anon("chunk_cache", rows * chunk * windows * 4 * 8 * 2), _anon("chunk_outputs", rows * out * 8),
            _anon("final_concat", rows * out * 8), _anon("persist_cast", rows * out * 4)]


def _l3_numba_single(params: Mapping[str, Any]) -> List[Component]:
    rows, out, chunk = _i(params, "rows"), _i(params, "output_cols"), _i(params, "chunk_cols", _i(params, "input_cols"))
    inputs = _i(params, "input_cols", chunk)
    max_out = _i(params, "max_out_cols", out)
    return [_anon("chunk_cache", rows * inputs * 6 * 4 * 2), _anon("current_chunk", rows * chunk * 8),
            _anon("six_stat", rows * 6 * 8), _anon("six_stat_return", rows * 6 * 4),
            _anon("persist_cast", rows * out * 4),
            _mapped("output_memmap", rows * max_out * 4, "np.memmap", "run")]


def _l3_pandas(params: Mapping[str, Any]) -> List[Component]:
    rows, out = _i(params, "rows"), _i(params, "output_cols")
    inputs = _i(params, "input_cols", _i(params, "chunk_cols"))
    max_out = _i(params, "max_out_cols", out)
    # 逐窗之 base_cache：全部 chunk 之 rolling mean／std／min／max（float64）＋chunk 複本；step 結果與其 float32 轉型。
    return [_anon("rolling_intermediate", rows * inputs * 8 * 7 + rows * inputs * 8 * 3),
            _anon("persist_cast", rows * out * 4),
            _mapped("return_table", rows * max_out * 4, "np.memmap", "run")]


def _l4_l6(params: Mapping[str, Any]) -> List[Component]:
    rows, inputs, out = _i(params, "rows"), _i(params, "input_cols"), _i(params, "output_cols")
    return [_anon("input_merge", rows * inputs * 8), _anon("output", rows * out * 8), _anon("persist_cast", rows * out * 4)]


def _read(params: Mapping[str, Any]) -> List[Component]:
    rows, cols = _i(params, "rows"), _i(params, "group_cols", _i(params, "selected_cols"))
    return [_anon("read", rows * cols * 4), _anon("cast", rows * cols * 8)]


def _post_ic(params: Mapping[str, Any]) -> List[Component]:
    rows, selected, group = _i(params, "rows"), _i(params, "selected_cols"), _i(params, "group_cols")
    accumulated = _i(params, "accumulated_cols", selected)
    return [_anon("selected_copy", rows * selected * 8), _anon("group_output", rows * group * 8 * 3),
            _anon("accumulated_processed", rows * accumulated * 8)]


def shard_sizes(rows: int, cols: int, shard_bytes: int, dtype_size: int = 4) -> List[int]:
    """registry 分片之每片位元組（同 `ColumnGroupRegistry._compute_shard_slices`）。"""
    if rows <= 0 or cols <= 0:
        return []
    per_col = rows * dtype_size
    if per_col * cols <= shard_bytes:
        return [per_col * cols]
    per_shard = max(1, shard_bytes // per_col)
    sizes, start = [], 0
    while start < cols:
        end = min(start + per_shard, cols)
        sizes.append(per_col * (end - start))
        start = end
    return sizes


def _grouped_mapped(name: str, sizes: Sequence[int], entry: str, lifetime: str) -> List[Component]:
    counts: Dict[int, int] = {}
    for size in sizes:
        counts[int(size)] = counts.get(int(size), 0) + 1
    if not counts:
        return [_mapped(name, 0, entry, lifetime, count=0)]
    return [_mapped(name, size, entry, lifetime, count=n) for size, n in sorted(counts.items(), key=lambda kv: -kv[1])]


def _calib_reduce(params: Mapping[str, Any]) -> List[Component]:
    rows, cols = _i(params, "rows"), _i(params, "group_cols")
    sizes = params.get("shard_sizes")
    if sizes is None:
        shard_target = _i(params, "shard_bytes", 0) or _default_shard_bytes()
        sizes = shard_sizes(rows, cols, shard_target)
    sizes = [int(s) for s in sizes]
    sharded = len(sizes) > 1
    # 多片 ⇒ load_data 配置 dense（float32）並逐片映射拷貝；單片 ⇒ 映射本身交出（不另配置）
    return [_anon("group", rows * cols * 4 if sharded else 0),
            _anon("winsor_copy", rows * cols * 8 * 3),
            _anon("packet_accumulated", _i(params, "n_calibration") * _i(params, "accumulated_cols") * 8),
            *_grouped_mapped("shard_map", sizes, "np.load(mmap_mode)", "segment")]


def _default_shard_bytes() -> int:
    try:
        from momentum.FeatureEngineering.utils.hardware_utils import get_cgsa_shard_bytes  # noqa: PLC0415

        return int(get_cgsa_shard_bytes())
    except Exception:  # noqa: BLE001 — 估算預設不得因硬體查詢失敗而缺分支
        return 256 * MiB


def _align_index(params: Mapping[str, Any]) -> List[Component]:
    n_p, n_s = _i(params, "primary_rows"), _i(params, "source_rows")
    return [_anon("primary_seconds", n_p * 8), _anon("source_seconds", n_s * 8), _anon("decision_ns", n_p * 8 * 2),
            _anon("source_close_ns", n_s * 8), _anon("idx", n_p * 8), _anon("valid_positions", n_p * 8),
            _anon("mismatch_mask", n_p)]


def _align_compact(params: Mapping[str, Any]) -> List[Component]:
    return [_anon("idx_map_int32", _i(params, "primary_rows") * 4)]


def _align_persist(params: Mapping[str, Any]) -> List[Component]:
    n_p, n_s = _i(params, "primary_rows"), _i(params, "source_rows")
    cols = _i(params, "group_cols", _i(params, "output_cols"))
    block = min(_i(params, "align_block_rows", 1024), max(n_p, 1))
    source_kind = str(params.get("source_kind", "single"))
    source_sizes = [int(s) for s in params.get("source_shard_sizes") or []]
    if not source_sizes and source_kind != "legacy":
        shards = max(_i(params, "source_shards", 1), 1)
        source_sizes = [n_s * cols * 4 // shards] * shards if source_kind == "sharded" else [n_s * cols * 4]
    source_float32 = bool(params.get("source_float32", True))
    # 根行程內 dense 對齊（串列多週期）之輸出為匿名陣列（np.full）；並行 worker 群組之對齊輸出為 open_memmap 映射
    if bool(params.get("aligned_output_anon", False)):
        aligned = _anon("aligned_output", n_p * cols * 4)
    else:
        aligned = _mapped("aligned_output", n_p * cols * 4, "np.lib.format.open_memmap", "segment")
    return [_anon("source_dense", n_s * cols * 4 if source_kind == "sharded" else 0),
            *_grouped_mapped("source_map", source_sizes if source_kind != "legacy" else [], "np.load(mmap_mode)",
                             "segment"),
            _anon("legacy_cast", n_s * cols * 4 if source_kind == "legacy" else 0),
            aligned,
            _anon("block_valid", block), _anon("block_gather_idx", block * 8), _anon("block_gather", block * cols * 4),
            _anon("block_cast", 0 if source_float32 else block * cols * 4)]


BRANCH_TABLE: Dict[str, Callable[[Mapping[str, Any]], List[Component]]] = {
    "L1.serial": lambda p: _l1(p, parallel=False),
    "L1.parallel": lambda p: _l1(p, parallel=True),
    "L2.polars": _l2_polars,
    "L2.pandas_serial": _l2_pandas,
    "L2.pandas_parallel": _l2_pandas,
    "L3.numba_multi_callback": _l3_multi_callback,
    "L3.numba_multi_nocallback": _l3_multi_nocallback,
    "L3.vectorized_chunked": _l3_vectorized,
    "L3.vectorized_unchunked": _l3_vectorized,
    "L3.numba_single": _l3_numba_single,
    "L3.pandas_fallback": _l3_pandas,
    "L4": _l4_l6,
    "L5": _l4_l6,
    "L6": _l4_l6,
    "IC.group_read": _read,
    "IC.selected_read": _read,
    "PostIC.transform_selected": _post_ic,
    "Calib.group_reduce": _calib_reduce,
    "MTF.align_index": _align_index,
    "MTF.align_compact": _align_compact,
    "MTF.align_persist": _align_persist,
}


def estimate(branch_id: str, params: Mapping[str, Any]) -> List[Component]:
    """分支估算（分派點與任務峰值 E 共用之同一估算函式）。"""
    fn = BRANCH_TABLE.get(branch_id)
    if fn is None:
        raise UnknownBudgetBranchError(branch_id)
    return list(fn(params))


# ---------------------------------------------------------------- 配置前判定

def _record(entry: Tuple[str, List[Component]]) -> None:
    with _RECORDERS_LOCK:
        for recorder in _RECORDERS:
            recorder.append(entry)


def _stop_flag_reason(stop_dir: Optional[Path]) -> Optional[str]:
    if stop_dir is None:
        return None
    try:
        return (Path(stop_dir) / STOP_FLAG_NAME).read_text(encoding="utf-8").strip() or "stop"
    except FileNotFoundError:
        return None
    except OSError:
        return "stop"


_TRIGGER_MESSAGES = {"swap_volume_low": MSG_SWAP_VOLUME_LOW, "paging_exhausted": MSG_MACHINE_INSUFFICIENT,
                     "measurement_failed": MSG_MEASUREMENT_FAILED}


def _check_log(event: Dict[str, Any]) -> None:
    path = os.environ.get(CHECK_LOG_ENV, "").strip()
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def check(branch_id: str, components: Sequence[Component], *, label: Optional[str] = None,
          run_dir: Optional[Path] = None, domain: Optional["DomainDescriptor"] = None) -> None:
    """配置前判定（SPEC v35–v39「記憶體上限與選路」）：本段新增量 G（anon planned）≤ 剩餘可用量 A ⇒ 放行；
    不以 `F + planned` 與比例上限比較（R 只管並行准入與選路）、壓力等級只記錄。分支 ID 不在分支表 ⇒
    `UnknownBudgetBranchError`；停止旗標已立 ⇒ 具名停止；G > A ⇒ `GenerationMemoryBudgetExceeded`（機器可用量
    不足；呼叫端可先經 `route` 嘗試白名單等價臂）；域內 worker 之 `F_self + G > E` ⇒ `MemoryRerouteNeeded`。"""
    if branch_id not in BRANCH_TABLE:
        raise UnknownBudgetBranchError(branch_id)
    components = list(components)
    _record((branch_id, components))
    ctx = _ACTIVE.get()
    if domain is None and ctx is not None and ctx.mode == "worker":
        domain = ctx.domain
    stop_dir = Path(run_dir) if run_dir is not None else (
        Path(domain.stop_dir or domain.domain_dir) if domain is not None else (None if ctx is None else ctx.stop_dir))
    name = label or branch_id
    planned = planned_bytes(components)
    if ctx is not None and ctx.checkpoint_file is not None:
        try:  # 只供收據定位（v38：G 不作守護之停止條件）
            ctx.checkpoint_file.write_text(json.dumps({"label": name, "G": planned, "time": time.time()},
                                                      ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
    log: Dict[str, Any] = {"event": "check", "pid": os.getpid(),
                           "root_pid": None if domain is None else domain.root_pid,
                           "task_id": None if domain is None else domain.task_id, "branch": branch_id,
                           "planned": planned, "E": None if domain is None else domain.envelope}
    try:
        trigger = _stop_flag_reason(stop_dir)
        if trigger is not None:
            raise GenerationMemoryBudgetExceeded(name, 0, planned, 0, _TRIGGER_MESSAGES.get(trigger, trigger))
        snapshot = sample_vm_snapshot()
        available = available_bytes(snapshot)
        log.update({"A": available, "pressure": int(snapshot.pressure_level),
                    "swap_expand_readable": swap_expansion_readable(snapshot)})
        current = 0
        if domain is not None:
            current = sample_memory_bytes()
            log.update({"F": current, "U": current + planned})
            if current + planned > int(domain.envelope):
                _record_estimate_exceeded(domain, name, current, planned)
                raise MemoryRerouteNeeded(name, current, planned, int(domain.envelope), MSG_ESTIMATE_EXCEEDED)
        else:
            override = _BUDGET_OVERRIDE.get()
            if override is not None:
                # 測試接縫：以「上限 − 目前用量」作剩餘（只作用於本判定；與 A 取小），驗配置前時點與成分計量
                current = _current_usage_bytes()
                log.update({"F": current, "U": current + planned})
                if current + planned > int(override):
                    raise GenerationMemoryBudgetExceeded(name, current, planned, int(override), MSG_OWN_CAP)
        if planned > available:
            raise GenerationMemoryBudgetExceeded(name, current, planned, available, MSG_MACHINE_INSUFFICIENT)
    except GenerationMemoryBudgetExceeded as exc:
        log["result"] = exc.reason
        _check_log(log)
        raise
    log["result"] = "ok"
    _check_log(log)


# 選路白名單之速度收據（SPEC v35：同規模實測收據證明候選較快才於 G ≤ A 時切換）：
# {(分派點, 原分支, 候選分支): [規模鍵, …]}；預設空（無收據 ⇒ 保留原臂）。
ROUTE_SPEED_RECEIPTS: Dict[Tuple[str, str, str], Sequence[str]] = {}


def _is_capacity_refusal(exc: GenerationMemoryBudgetExceeded) -> bool:
    return exc.reason in (MSG_MACHINE_INSUFFICIENT, MSG_OWN_CAP, MSG_ESTIMATE_EXCEEDED)


def route(point: str, candidates: Sequence[Tuple[str, Mapping[str, Any]]], *, label: Optional[str] = None,
          scale_key: Optional[str] = None) -> str:
    """選路（SPEC v35）：`candidates[0]` 為原臂，其後為該分派點白名單之逐位元等價臂（呼叫端負責只列已登錄者）。
    同規模速度收據證明某候選較快 ⇒ 先試之；否則先試原臂。容量不足（機器可用量不足／worker 估算低估）⇒ 依序
    試其餘候選；皆不可 ⇒ 上拋原臂之錯誤。停止旗標等非容量原因不換路。回傳實際選定之分支 ID，並記入
    `ICFA_CHECK_LOG` 之 `memory_route` 事件。"""
    original = candidates[0][0]
    ordered = list(candidates)
    for index, (branch, _params) in enumerate(candidates[1:], start=1):
        if scale_key is not None and scale_key in ROUTE_SPEED_RECEIPTS.get((point, original, branch), ()):
            ordered.insert(0, ordered.pop(index))
            break
    first_error: Optional[GenerationMemoryBudgetExceeded] = None
    for branch, params in ordered:
        try:
            check_estimate(branch, params, label=f"{label or point}:{branch}")
        except GenerationMemoryBudgetExceeded as exc:
            if not _is_capacity_refusal(exc):
                raise
            first_error = first_error or exc
            continue
        if branch != original:
            reason = "speed_receipt" if branch == ordered[0][0] and first_error is None else "capacity"
            _record_route_switch(point, original, candidates[0][1], branch, params, reason, first_error)
        return branch
    assert first_error is not None
    raise first_error


def _record_route_switch(point: str, original: str, original_params: Mapping[str, Any], branch: str,
                         params: Mapping[str, Any], reason: str,
                         refusal: Optional[GenerationMemoryBudgetExceeded]) -> None:
    """單行程選路之紀錄：G（選定臂）、G_from（原臂）、A、F、R；原臂被拒時附其拒絕理由。量測失敗不改變選路結果。"""
    entry: Dict[str, Any] = {"point": point, "from": original, "to": branch, "reason": reason,
                             "G": planned_bytes(estimate(branch, params)),
                             "G_from": planned_bytes(estimate(original, original_params)),
                             "R": configured_budget_bytes(include_override=False)}
    try:
        entry["A"] = available_bytes(sample_vm_snapshot())
        entry["F"] = _current_usage_bytes()
    except MemoryMeasurementUnavailable:
        entry.setdefault("A", None)
        entry["F"] = None
    if refusal is not None:
        entry["refusal"] = refusal.reason
    record_route(entry)


def check_estimate(branch_id: str, params: Mapping[str, Any], **kwargs: Any) -> List[Component]:
    """以分支表估算並判定（producer 之便利入口；判定經模組屬性 `check`，測試可攔截）。回傳成分供呼叫端記錄。"""
    components = estimate(branch_id, params)
    sys.modules[__name__].check(branch_id, components, **kwargs)
    return components


def _record_estimate_exceeded(domain: "DomainDescriptor", label: str, current: int, planned: int) -> None:
    path = Path(domain.domain_dir) / ESTIMATE_EXCEEDED_LOG_NAME
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"event": "memory_estimate_exceeded", "pid": os.getpid(), "task_id": domain.task_id,
                                     "branch": label, "F": current, "planned": planned, "E": int(domain.envelope),
                                     "excess": current + planned - int(domain.envelope), "time": time.time()},
                                    ensure_ascii=False) + "\n")
    except OSError:
        pass


def reset_interval_peak() -> int:
    """重設本行程之區間峰值（`proc_reset_footprint_interval`）並回傳當下 footprint。"""
    _require_darwin()
    lib = _lib("proc")
    if not hasattr(lib, "proc_reset_footprint_interval"):
        raise MemoryMeasurementUnavailable("proc_reset_footprint_interval 不可用")
    lib.proc_reset_footprint_interval(os.getpid())
    return sample_memory_bytes()


def read_interval_peak() -> int:
    """讀本行程之區間最大 footprint（`RUSAGE_INFO_V4` 之 `ri_interval_max_phys_footprint`，實測第 33 欄）。"""
    _require_darwin()
    info = _RusageInfoV4()
    rc = _lib("proc").proc_pid_rusage(os.getpid(), 4, ctypes.byref(info))
    if rc != 0:
        raise MemoryMeasurementUnavailable(f"proc_pid_rusage v4 rc={rc}")
    return int(info.f33)


# ---------------------------------------------------------------- 磁碟後援

_BUS_CACHE: Dict[int, Optional[str]] = {}
_BUS_LOCK = threading.Lock()


def _existing(path: Path) -> Path:
    path = Path(path).expanduser()
    while not path.exists() and path.parent != path:
        path = path.parent
    return path


def _mount_point(path: Path) -> Path:
    path = _existing(path).resolve()
    dev = os.stat(path).st_dev
    while path.parent != path and os.stat(path.parent).st_dev == dev:
        path = path.parent
    return path


def backing_bus_protocol(path: Path) -> Optional[str]:
    """路徑所在掛載之 `diskutil info -plist` 之 `BusProtocol`（依 st_dev 去重、行程內快取）；取不到 ⇒ None。"""
    try:
        existing = _existing(Path(path))
        dev = os.stat(existing).st_dev
    except OSError:
        return None
    with _BUS_LOCK:
        if dev in _BUS_CACHE:
            return _BUS_CACHE[dev]
    protocol: Optional[str] = None
    try:
        mount = _mount_point(existing)
        proc = subprocess.run(["/usr/sbin/diskutil", "info", "-plist", str(mount)], capture_output=True, timeout=30)
        if proc.returncode == 0:
            protocol = plistlib.loads(proc.stdout).get("BusProtocol")
    except (OSError, subprocess.SubprocessError, ValueError):
        protocol = None
    with _BUS_LOCK:
        _BUS_CACHE[dev] = protocol
    return protocol


def assert_disk_backed(paths: Sequence[Path]) -> None:
    """各路徑之掛載皆非 `Disk Image` 且可取得 ⇒ 通過；否則 `MemoryMeasurementUnavailable`。"""
    for path in paths:
        if path is None:
            continue
        protocol = backing_bus_protocol(Path(path))
        if protocol is None or protocol in REJECTED_BUS_PROTOCOLS:
            raise MemoryMeasurementUnavailable(
                f"映射／成品目錄 {path} 之磁碟後援無法確認（BusProtocol={protocol!r}）；RAM disk 或磁碟映像上拒絕生成"
            )


def mapping_root(run_dir: Path) -> Path:
    """run 之映射根（暫存 memmap 與校準暫存 registry 一律建於此下；與 run 目錄同一掛載，不沿用 TMPDIR）。"""
    return Path(run_dir) / ".icfa_mmap"


# ---------------------------------------------------------------- 守護與恢復

def _pid_alive(pid: int) -> bool:
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@dataclass
class GuardHandle:
    """一次受保護 run 之守護行程控制。"""

    pid: int
    run_dir: Path
    run_id: str
    extra: Dict[str, Any] = field(default_factory=dict)

    def stop(self) -> None:
        """送停止訊號並等待回收。"""
        proc = self.extra.get("process")
        if proc is None:
            return
        if proc.poll() is None:
            try:
                proc.send_signal(signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
        checkpoint = self.extra.get("checkpoint_file")
        if checkpoint is not None:
            with contextlib.suppress(OSError):
                Path(checkpoint).unlink()
        self.extra["process"] = None


def start_guard(run_dir: Path, run_id: str, *, budget: int) -> GuardHandle:
    """以檔案路徑啟動 `memory_guard.py`；首讀失敗 ⇒ `MemoryMeasurementUnavailable`。"""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    fd, checkpoint = tempfile.mkstemp(prefix="icfa_guard_ckpt_", suffix=".txt")
    os.close(fd)
    command = [sys.executable, str(GUARD_SCRIPT), "--pid", str(os.getpid()), "--run-dir", str(run_dir),
               "--run-id", str(run_id), "--budget", str(int(budget)), "--checkpoint-file", checkpoint,
               "--interval", str(GUARD_INTERVAL_SECONDS)]
    try:
        proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                close_fds=True)
    except OSError as exc:
        with contextlib.suppress(OSError):
            os.unlink(checkpoint)
        raise MemoryMeasurementUnavailable(f"守護行程啟動失敗：{exc}") from exc
    import select

    ready, _, _ = select.select([proc.stdout], [], [], 30.0)
    line = proc.stdout.readline().decode("utf-8", "replace").strip() if ready else ""
    if line != "ready":
        err = b""
        if proc.poll() is None:
            proc.kill()
        with contextlib.suppress(Exception):
            _, err = proc.communicate(timeout=5)
        with contextlib.suppress(OSError):
            os.unlink(checkpoint)
        raise MemoryMeasurementUnavailable(f"守護首次讀數失敗：{line!r} {err.decode('utf-8', 'replace')[-500:]}")
    _check_log({"event": "start_guard", "pid": os.getpid(), "root_pid": os.getpid(), "task_id": str(run_id)})
    return GuardHandle(pid=proc.pid, run_dir=run_dir, run_id=str(run_id),
                       extra={"process": proc, "checkpoint_file": Path(checkpoint)})


def stop_flag_set(run_dir: Path) -> bool:
    """守護之停止旗標是否已立（單次 stat）。"""
    return (Path(run_dir) / STOP_FLAG_NAME).exists()


def _write_json_atomic(path: Path, payload: Any) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:6]}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def register_owned_path(run_dir: Path, path: Path) -> None:
    """將本 run 建立之暫存路徑登記於 `owned_paths.json`。"""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    target = run_dir / OWNED_PATHS_NAME
    try:
        current = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(current, list):
            current = []
    except (OSError, ValueError):
        current = []
    if str(path) not in current:
        current.append(str(path))
    _write_json_atomic(target, current)


def recover_aborted_run(run_dir: Path) -> Dict[str, Any]:
    """同 key 下次 run 取得 lease 後：讀前次 abort 收據，刪其登記且仍存在之暫存、清舊停止旗標；回報處理項。"""
    run_dir = Path(run_dir)
    report: Dict[str, Any] = {"run_dir": str(run_dir), "abort_receipt": None, "removed": [], "stop_flag_cleared": False}
    receipt_path = run_dir / ABORT_RECEIPT_NAME
    owned: List[str] = []
    if receipt_path.exists():
        report["abort_receipt"] = str(receipt_path)
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            owned.extend(str(p) for p in receipt.get("owned_paths") or [])
        except (OSError, ValueError):
            pass
    owned_file = run_dir / OWNED_PATHS_NAME
    if owned_file.exists():
        try:
            listed = json.loads(owned_file.read_text(encoding="utf-8"))
            owned.extend(str(p) for p in listed if isinstance(listed, list))
        except (OSError, ValueError):
            pass
    for raw in dict.fromkeys(owned):
        target = Path(raw)
        if not target.exists():
            continue
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target, ignore_errors=True)
        else:
            with contextlib.suppress(OSError):
                target.unlink()
        report["removed"].append(raw)
    with contextlib.suppress(OSError):
        owned_file.unlink()
    flag = run_dir / STOP_FLAG_NAME
    if flag.exists():
        with contextlib.suppress(OSError):
            flag.unlink()
        report["stop_flag_cleared"] = True
    return report


class ProtectedRun:
    """一次受保護 run（run lease 之持有期間）：恢復 → 守護 → 本執行緒情境；`close()` 先停守護、還原情境。

    域內任務（worker）或已在受保護 run／域根內之巢狀呼叫：不另起守護（情境沿用外層）。
    """

    def __init__(self, run_dir: Path, run_id: str) -> None:
        self.run_dir = Path(run_dir)
        self.run_id = str(run_id)
        self.guard: Optional[GuardHandle] = None
        self._token: Optional[contextvars.Token] = None
        self.nested = False
        self.recovery: Dict[str, Any] = {}
        self._ctx: Optional[_RunContext] = None
        self._root_routes: Optional[List[Dict[str, Any]]] = None

    def start(self) -> "ProtectedRun":
        module = sys.modules[__name__]
        outer = _ACTIVE.get()
        self.recovery = module.recover_aborted_run(self.run_dir)
        root = mapping_root(self.run_dir)
        root.mkdir(parents=True, exist_ok=True)
        if outer is not None:
            # 域內任務／域根之串行臂：守護與停止旗標沿用外層（不另起守護、不另建預算）；映射根與 owned paths 屬本 run
            self.nested = True
            # 選路紀錄：自域根進入之一次生成（串行臂）另起一份並改為 run 身分，其內之巢狀（校準前置→正式 run）共用；
            # worker 與單行程 run 之巢狀共用外層（審碼 b3 r7 codex P2-02：避免正式 run 再次清空校準前置之紀錄）
            if outer.mode == "root":
                ctx = replace(outer, mode="run", mapping_root=root, run_dir=self.run_dir, routes=[])
                self._root_routes = outer.routes  # close 時交回域根（成功或失敗皆保留，排程器依任務歸屬）
            else:
                ctx = replace(outer, mapping_root=root, run_dir=self.run_dir)
            self._ctx = ctx
            self._token = _ACTIVE.set(ctx)
            module.register_owned_path(self.run_dir, root)
            return self
        self.guard = module.start_guard(self.run_dir, self.run_id, budget=configured_budget_bytes(include_override=False))
        checkpoint = self.guard.extra.get("checkpoint_file") if self.guard is not None else None
        self._token = _ACTIVE.set(_RunContext(mode="run", stop_dir=self.run_dir,
                                              guard_pid=None if self.guard is None else self.guard.pid,
                                              checkpoint_file=checkpoint, mapping_root=root, run_dir=self.run_dir))
        module.register_owned_path(self.run_dir, root)
        return self

    def close(self) -> None:
        try:
            if self.guard is not None:
                self.guard.stop()
        finally:
            self.guard = None
            if self._token is not None:
                with contextlib.suppress(ValueError):
                    _ACTIVE.reset(self._token)
                self._token = None
            if self._root_routes is not None and self._ctx is not None:
                self._root_routes.extend(self._ctx.routes)  # 自域根進入之一次生成：紀錄交回域根（審碼 b3 r8 codex P2-01）
                self._root_routes = None
            shutil.rmtree(mapping_root(self.run_dir), ignore_errors=True)
            with contextlib.suppress(OSError):
                (self.run_dir / OWNED_PATHS_NAME).unlink()  # 正常結束：暫存皆已刪，登記清單一併移除


def begin_protected_run(run_dir: Path, run_id: str) -> ProtectedRun:
    """受保護 run 之入口（generate_features 於取得 lease 後呼叫）。"""
    return ProtectedRun(run_dir, run_id).start()


PRE_LEASE_SCOPE_PREFIX = ".icfa_prelease_"


def _scope_key(run_id: str) -> str:
    return hashlib.sha256(str(run_id).encode("utf-8")).hexdigest()[:16]


def _owner_token(pid: int) -> str:
    """擁有者身分（pid 與啟動時刻）；寫入目錄名，使目錄可見之第一刻即可驗活（無發布間隙）。"""
    start = int(process_start_time(pid)) if sys.platform == "darwin" else 0
    return f"{pid}-{start}"


class PreLeaseScope(ProtectedRun):
    """FFSTAT 校準前置關卡（先於 run lease、run 目錄零寫入）之受保護情境：同一 `generate_features` 之守護自此
    啟動，lease 後之 run 以巢狀沿用（恰一守護）；根目錄為成品根下之獨立暫存目錄（與 run 目錄同掛載、已核磁碟
    後援；目錄名含擁有者 pid 與啟動時刻），`close()` 連同本身建立之上層目錄全數刪除（校準失敗 ⇒ 樹前後相同）。
    強制終止後之殘留由同 key 下一次 run 取得 lease 後以 `recover_orphan_pre_lease_scopes` 清理（擁有者存活者不動）。"""

    def __init__(self, scope_dir: Path, run_id: str, created: Sequence[Path]) -> None:
        super().__init__(scope_dir, run_id)
        self._created = [Path(p) for p in created]

    def close(self) -> None:
        try:
            super().close()
        finally:
            shutil.rmtree(self.run_dir, ignore_errors=True)
            for parent in self._created:  # 由深至淺；只刪本 scope 為建立而新增且已空之上層
                with contextlib.suppress(OSError):
                    parent.rmdir()


def begin_pre_lease_scope(base_dir: Path, run_id: str) -> PreLeaseScope:
    """校準前置關卡之受保護情境入口（generate_features 於呼叫校準關卡前）。"""
    base_dir = Path(base_dir)
    created: List[Path] = []
    probe = base_dir
    while not probe.exists():
        created.append(probe)
        probe = probe.parent
    base_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"{PRE_LEASE_SCOPE_PREFIX}{_scope_key(run_id)}_{_owner_token(os.getpid())}_"
    scope = PreLeaseScope(Path(tempfile.mkdtemp(prefix=prefix, dir=str(base_dir))), run_id, created)
    try:
        return scope.start()
    except BaseException:
        scope.close()
        raise


def _scope_owner_alive(scope_dir: Path, key: str) -> bool:
    """目錄名之擁有者身分驗活：pid 不存在或啟動時刻不符 ⇒ 已死；名稱無法解析 ⇒ 視為存活（不刪不明者）。"""
    rest = scope_dir.name[len(f"{PRE_LEASE_SCOPE_PREFIX}{key}_"):]
    try:
        pid_text, start_text = rest.split("_", 1)[0].split("-", 1)
        pid, start = int(pid_text), int(start_text)
    except ValueError:
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    if sys.platform != "darwin":
        return True
    try:
        current = int(process_start_time(pid))
        # 啟動時刻未知（建立時或驗活時讀取失敗 ⇒ 0）＝無死亡證據 ⇒ 存活；只有兩個已知身分不同才判 pid 重用
        # （v32，審碼 b3 r3 codex P1-02）
        return start == 0 or current == 0 or current == start
    except Exception:  # noqa: BLE001 — 讀不到起始時間 ⇒ 視為仍存活（不刪他人暫存）
        return True


def recover_orphan_pre_lease_scopes(base_dir: Path, run_id: str, run_dir: Path,
                                    keep: Optional[Path] = None) -> List[str]:
    """同 key 前次被強制終止之校準前置情境殘留：擁有者已不存在者，刪其登記暫存與整個目錄；abort 收據保留至
    run 目錄（`memory_guard_abort.prelease-<目錄名>.json`）。回傳已清理之目錄。"""
    base_dir = Path(base_dir)
    removed: List[str] = []
    if not base_dir.is_dir():
        return removed
    key = _scope_key(run_id)
    for scope_dir in sorted(base_dir.glob(f"{PRE_LEASE_SCOPE_PREFIX}{key}_*")):
        if not scope_dir.is_dir() or (keep is not None and scope_dir.resolve() == Path(keep).resolve()):
            continue
        if _scope_owner_alive(scope_dir, key):
            continue
        receipt = scope_dir / ABORT_RECEIPT_NAME
        if receipt.exists():
            Path(run_dir).mkdir(parents=True, exist_ok=True)
            with contextlib.suppress(OSError):
                shutil.copy2(receipt, Path(run_dir) / f"memory_guard_abort.prelease-{scope_dir.name}.json")
        recover_aborted_run(scope_dir)
        shutil.rmtree(scope_dir, ignore_errors=True)
        removed.append(str(scope_dir))
    return removed


# ---------------------------------------------------------------- 測試接縫（只供驗收測試注入；生產不呼叫）

@contextlib.contextmanager
def _override(var: contextvars.ContextVar, value: Any) -> Iterator[Any]:
    token = var.set(value)
    try:
        yield value
    finally:
        var.reset(token)


def sampler_override(fn: Callable[[], Mapping[str, int]]) -> Any:
    """context manager：以 `fn()` 回傳之 {"resident": B, "phys_footprint": B} 取代 `_read_rusage`（目前用量之全部讀數）。"""
    return _override(_SAMPLER_OVERRIDE, fn)


def budget_override(nbytes: int) -> Any:
    """context manager：本 context 內上限改為 `nbytes`（絕對位元組）。"""
    return _override(_BUDGET_OVERRIDE, int(nbytes))


def vm_snapshot_override(snapshot: VMSnapshot) -> Any:
    """context manager：本 context 內 `sample_vm_snapshot` 回傳 `snapshot`。"""
    return _override(_VM_OVERRIDE, snapshot)


@contextlib.contextmanager
def check_recorder() -> Iterator[List[Tuple[str, List[Component]]]]:
    """context manager：記錄本 context 內每次 `check` 之 (branch_id, components)；回傳 list。"""
    recorded: List[Tuple[str, List[Component]]] = []
    with _RECORDERS_LOCK:
        _RECORDERS.append(recorded)
    try:
        yield recorded
    finally:
        with _RECORDERS_LOCK:
            with contextlib.suppress(ValueError):
                _RECORDERS.remove(recorded)


def layer_end(label: str) -> None:
    """producer 於每層結束（及整個 run 結束，label＝"run"）時呼叫；`check_recorder` 記為 ("LAYER_END:<label>", [])。"""
    _record((f"LAYER_END:{label}", []))


# ---------------------------------------------------------------- 子行程預算域（SPEC v25–v27）

@dataclass(frozen=True)
class DomainDescriptor:
    """顯式、可 pickle 之域描述（作為 worker 入口參數；不經行程全域環境變數）。"""

    root_pid: int
    domain_dir: Path
    budget: int
    task_id: str
    envelope: int  # 本任務峰值 E（worker 配置點以之判估算低估）
    stop_dir: Optional[Path] = None  # 守護停止旗標所在（缺 ⇒ domain_dir）


@dataclass(frozen=True)
class Member:
    """成員：以 (pid, start_time) 去重；envelope＝活動任務／根階段之 E，無則 None。"""

    pid: int
    start_time: float
    footprint: int
    envelope: Optional[int] = None
    role: str = "task"  # task | root | guard | tracker


@dataclass(frozen=True)
class Slot:
    """尚無 pid 之啟動槽（任務槽或輔助槽）。"""

    slot_id: str
    envelope: int
    kind: str = "task"  # task | aux


@dataclass(frozen=True)
class AdmissionState:
    budget: int
    members: Sequence[Member]
    slots: Sequence[Slot]
    absorbable: int
    pressure_level: int  # 只記錄（v36：不再為准入條件）
    stop_flag: bool
    # 同容器檔案寫入（SPEC v37）：換頁卷可用空間、磁碟保留量、已准入未 join 任務之寫入上界總和；None ⇒ 不判
    disk_free: Optional[int] = None
    disk_reserve: int = 0
    disk_committed: int = 0


@dataclass(frozen=True)
class Admission:
    ok: bool
    reason: str  # ok | budget | absorbable | disk | stop_flag


def _dedup(members: Sequence[Member]) -> List[Member]:
    seen: Dict[Tuple[int, float], Member] = {}
    for m in members:
        seen.setdefault((int(m.pid), float(m.start_time)), m)
    return list(seen.values())


def commitment(member: Member) -> int:
    """U＝max(F, E)（有活動承諾）；否則 F。"""
    if member.envelope is None:
        return int(member.footprint)
    return max(int(member.footprint), int(member.envelope))


def admit(state: AdmissionState, new_envelope: int, new_disk: int = 0) -> Admission:
    """准入合取（SPEC v35–v37）：Σ U（去重）＋Σ 槽 E＋E_new ≤ B（＝R，快區），且 Σ max(E−F,0)＋Σ 槽 E＋E_new ≤ 剩餘
    可用量 A，且同容器之已准入寫入上界＋新任務寫入上界＋磁碟保留量 ≤ 換頁卷可用空間，且無停止旗標；壓力只記錄。"""
    module = sys.modules[__name__]
    if state.stop_flag:
        return Admission(False, "stop_flag")
    if state.disk_free is not None and \
            int(state.disk_committed) + int(new_disk) + int(state.disk_reserve) > int(state.disk_free):
        return Admission(False, "disk")
    members = _dedup(state.members)
    slots_total = sum(int(s.envelope) for s in state.slots)
    total = sum(module.commitment(m) for m in members) + slots_total + int(new_envelope)
    if total > int(state.budget):
        return Admission(False, "budget")
    growth = sum(max(int(m.envelope) - int(m.footprint), 0) for m in members if m.envelope is not None)
    if growth + slots_total + int(new_envelope) > int(state.absorbable):
        return Admission(False, "absorbable")
    return Admission(True, "ok")


def measured_total(members: Sequence[Member]) -> int:
    """守護讀數：成員實測 footprint 以 (pid, start_time) 去重求和一次（不用 U／E）。"""
    return int(sum(int(m.footprint) for m in _dedup(members)))


def guard_should_stop(swap_volume_free: int, disk_reserve: int, available: Optional[int] = None,
                      page_size: int = 16384) -> Optional[str]:
    """守護第一段判定（SPEC v35–v39；與 `memory_guard._conditions` 同義之純函式）：換頁卷剩餘 < 磁碟保留量 ⇒
    `swap_volume_low`；剩餘可用量 A < 一頁 ⇒ `paging_exhausted`；壓力等級與 footprint 對上限不再為停止條件。"""
    if int(swap_volume_free) < int(disk_reserve):
        return "swap_volume_low"
    if available is not None and int(available) < int(page_size):
        return "paging_exhausted"
    return None


@dataclass(frozen=True)
class Task:
    task_id: str
    envelope: Optional[int]  # None＝形狀不可得 ⇒ 不准入並行，走串行臂
    payload: Any = None
    disk_bytes: int = 0  # 同容器檔案寫入上界 D（SPEC v37；形狀推導，准入發布、join 撤銷）


def _default_identity() -> Tuple[int, float]:
    return (os.getpid(), process_start_time(os.getpid()))


def _trampoline(descriptor: DomainDescriptor, worker_fn: Callable[[DomainDescriptor, Any], Any], payload: Any,
                identity_fn: Optional[Callable[[], Any]]) -> Any:
    """worker 本體之入口（於 executor 內執行）：先以身分綁定成員（域目錄 members/<task_id>.json），再執行本體。"""
    pid, start_time = (identity_fn or _default_identity)()
    members = Path(descriptor.domain_dir) / MEMBERS_DIR_NAME
    members.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(members / f"{descriptor.task_id}.json", {"pid": int(pid), "start_time": float(start_time),
                                                               "os_pid": os.getpid()})
    ctx = _RunContext(mode="worker", stop_dir=Path(descriptor.stop_dir or descriptor.domain_dir), domain=descriptor)
    token = _ACTIVE.set(ctx)
    try:
        return worker_fn(descriptor, payload)
    finally:
        _ACTIVE.reset(token)
        if ctx.routes:  # worker 內之選路紀錄經域目錄交根（根 join 後併入其 run metadata；審碼 b3 r6 codex P2-02）
            with contextlib.suppress(OSError):
                routes_dir = Path(descriptor.domain_dir) / ROUTES_DIR_NAME
                routes_dir.mkdir(parents=True, exist_ok=True)
                _write_json_atomic(routes_dir / f"{descriptor.task_id}.json", {"routes": ctx.routes})


@dataclass
class _TaskState:
    task: Task
    index: int
    status: str = "queued"
    pid: Optional[int] = None
    start_time: float = 0.0
    future: Any = None
    executor: Any = None


class MemoryBudgetScheduler:
    """有限波次排程器（三個 pool 共用；經 `momentum.factories.create_memory_budget_scheduler` 建立）。

    依賴注入（測試接縫）：`executor_factory(max_workers)` 建立 executor；`read_system()` 回
    (absorbable, pressure_level, stop_flag, root_footprint, aux_members)；`read_task_footprint(task_id)` 回該任務行程之 F；
    `aux_startup_envelope` 為輔助行程（resource tracker）啟動上界（None＝無收據 ⇒ 不准入並行）；
    `task_identity()` 於 worker 本體開始時回 (pid, start_time) 以綁定成員（預設＝作業系統 pid 與行程啟動時間；
    行程內執行緒池之測試注入執行緒識別，避免與根同 pid 而被去重）。
    `trace` 記事件 (event, task_id)：queued／admitted／starting／running／completed／failed／joined／serial／
    wave_joined／aux_slot／executor_created／refused。

    每個准入任務各自一個 executor（`executor_factory(1)`）：一波內逐一准入，送出後等待該任務綁定身分（或已結束）
    再判下一個，使同波先前任務以成員承諾 max(F, E) 計；一波全部完成後逐一 shutdown（join），再呼叫
    `on_wave_joined`，再開下一波（根對齊與 worker 生成因而不重疊）。
    """

    def __init__(self, budget: int, *, domain_dir: Path, max_workers: int,
                 executor_factory: Callable[[int], Any], read_system: Callable[[], Any],
                 read_task_footprint: Callable[[str], int], aux_startup_envelope: Optional[int],
                 task_identity: Optional[Callable[[], Any]] = None, stop_dir: Optional[Path] = None) -> None:
        self.budget = int(budget)
        self.stop_dir = None if stop_dir is None else Path(stop_dir)
        self.domain_dir = Path(domain_dir)
        self.domain_dir.mkdir(parents=True, exist_ok=True)
        (self.domain_dir / MEMBERS_DIR_NAME).mkdir(parents=True, exist_ok=True)
        self.max_workers = max(int(max_workers), 1)
        self._executor_factory = executor_factory
        self._read_system = read_system
        self._read_task_footprint = read_task_footprint
        self.aux_startup_envelope = aux_startup_envelope
        self._task_identity = task_identity
        self.trace: List[Tuple[str, str]] = []
        self._lock = threading.RLock()
        self._tasks: Dict[str, _TaskState] = {}
        self._stop_requested = threading.Event()
        self._interrupt_pending = False
        self._reroute_seen = False
        self._aux_slot: Optional[Slot] = None
        self.degraded: Optional[Dict[str, Any]] = None
        # 本排程器之選路決定（並行→串行；SPEC v35 `memory_route`）；呼叫端併入各任務之 run metadata
        self.routes: List[Dict[str, Any]] = []
        # 各任務生成內之選路紀錄（worker 經域目錄交回、根之串行臂取自根情境；成功或失敗皆保留、各次嘗試依序）
        self.task_routes: Dict[str, List[Dict[str, Any]]] = {}

    def _record_serial(self, state: _TaskState, reason: str, admission: Optional[AdmissionState] = None) -> None:
        """並行→正式串行之選路紀錄（分派點、臂、理由、G＝任務承諾 E、A、F＝成員實測合計、R）。"""
        if admission is None:
            try:
                admission = self.snapshot()
            except Exception:  # noqa: BLE001 — 紀錄不得改變選路結果；讀不到即記 None
                admission = None
        record = record_route({
            "point": "scheduler", "task_id": state.task.task_id, "from": "parallel", "to": "serial", "reason": reason,
            "G": None if state.task.envelope is None else int(state.task.envelope),
            "A": None if admission is None else int(admission.absorbable),
            "F": None if admission is None else measured_total(admission.members),
            "R": self.budget,
        })
        with self._lock:
            self.routes.append(record)

    def _collect_worker_routes(self, state: _TaskState) -> None:
        """worker 內之選路紀錄（`_trampoline` 經域目錄交出）併入根之受保護 run 紀錄。"""
        path = self.domain_dir / ROUTES_DIR_NAME / f"{state.task.task_id}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for entry in payload.get("routes", []):
            record = record_route({**{k: v for k, v in entry.items() if k not in ("event", "pid", "time")},
                                   "task_id": state.task.task_id, "worker_pid": entry.get("pid")})
            with self._lock:
                self.task_routes.setdefault(state.task.task_id, []).append(record)

    # -- 狀態
    def _event(self, event: str, task_id: str = "") -> None:
        with self._lock:
            self.trace.append((event, task_id))
        if event in ("executor_created", "serial", "admitted"):
            _check_log({"event": event, "pid": os.getpid(), "root_pid": os.getpid(), "task_id": task_id})

    def _refresh_bindings(self) -> None:
        members = self.domain_dir / MEMBERS_DIR_NAME
        for state in self._tasks.values():
            if state.status != "starting":
                continue
            path = members / f"{state.task.task_id}.json"
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            self.bind_pid(state.task.task_id, int(payload["pid"]), float(payload.get("start_time", 0.0)))

    def snapshot(self) -> AdmissionState:
        with self._lock:
            self._refresh_bindings()
            reading = tuple(self._read_system())
            absorbable, pressure, stop, root_footprint, aux_members = reading[:5]
            # 第 6、7 項（選填，SPEC v37）：換頁卷可用空間、磁碟保留量 ⇒ 准入判同容器寫入上界
            disk_free = int(reading[5]) if len(reading) > 5 and reading[5] is not None else None
            disk_reserve = int(reading[6]) if len(reading) > 6 else 0
            aux_members = list(aux_members or ())
            members: List[Member] = [Member(pid=os.getpid(), start_time=_root_start_time(), footprint=int(root_footprint),
                                            envelope=None, role="root")]
            members.extend(aux_members)
            slots: List[Slot] = []
            for state in self._tasks.values():
                if state.status == "starting":
                    slots.append(Slot(state.task.task_id, int(state.task.envelope or 0), "task"))
                elif state.status in ("running", "completed", "failed") and state.pid is not None:
                    active = state.status == "running"
                    members.append(Member(pid=int(state.pid), start_time=float(state.start_time),
                                          footprint=int(self._read_task_footprint(state.task.task_id)),
                                          envelope=int(state.task.envelope) if active else None, role="task"))
            if self._aux_slot is not None and not any(m.role == "tracker" for m in aux_members):
                slots.append(self._aux_slot)
            disk_committed = sum(int(state.task.disk_bytes) for state in self._tasks.values()
                                 if state.status in ("starting", "running", "completed", "failed"))
            return AdmissionState(budget=self.budget, members=tuple(members), slots=tuple(slots),
                                  absorbable=int(absorbable), pressure_level=int(pressure), stop_flag=bool(stop),
                                  disk_free=disk_free, disk_reserve=disk_reserve, disk_committed=disk_committed)

    def mark_starting(self, task_id: str) -> None:
        with self._lock:
            self._tasks[task_id].status = "starting"
        self._event("starting", task_id)

    def bind_pid(self, task_id: str, pid: int, start_time: float) -> None:
        with self._lock:
            state = self._tasks[task_id]
            if state.status != "starting":
                return
            state.pid, state.start_time, state.status = int(pid), float(start_time), "running"
            self.trace.append(("running", task_id))

    # -- 排程
    def _register_aux_slot(self) -> None:
        if self._aux_slot is None and self.aux_startup_envelope is not None:
            self._aux_slot = Slot("tracker", int(self.aux_startup_envelope), "aux")
            self._event("aux_slot", "tracker")

    def _wait_bound(self, state: _TaskState) -> None:
        while True:
            with self._lock:
                self._refresh_bindings()
                if state.status != "starting":
                    return
            if state.future is not None and state.future.done():
                return
            time.sleep(0.005)

    def run(self, tasks: Sequence[Task], worker_fn: Callable[[DomainDescriptor, Any], Any],
            serial_fn: Callable[[Any], Any], on_wave_joined: Callable[[List[Any]], None]) -> List[Any]:
        """依序准入有限波次；不足只排隊；無可准入走 `serial_fn`（根行程內）；每波 join 後呼叫 `on_wave_joined`。"""
        results: List[Any] = [None] * len(tasks)
        queue: Deque[_TaskState] = deque()
        for index, task in enumerate(tasks):
            state = _TaskState(task=task, index=index)
            with self._lock:
                self._tasks[task.task_id] = state
            queue.append(state)
            self._event("queued", task.task_id)
        with self._interrupt_deferral():
            try:
                parallel_ever = self._run_waves(queue, results, worker_fn, serial_fn, on_wave_joined)
            except BaseException:
                # 例外出口（executor 建構／submit／量測／結果處理失敗）：已建立之 executor 一律 shutdown 並確認回收後才
                # 返回外層（外層隨即關閉域與守護）；回收失敗者保留其狀態，不標 joined
                self._join_unjoined()
                raise
        if self._interrupt_pending:
            raise KeyboardInterrupt("排程器執行中收到中斷：已停止准入、已啟動之 worker 皆確認退出後上拋")
        if parallel_ever < min(self.max_workers, len(tasks)):
            self.degraded = {"configured": self.max_workers, "actual": parallel_ever,
                             "reason": "memory_budget_admission"}
        return results

    def _has_unjoined(self) -> bool:
        return any(state.executor is not None and state.status != "joined" for state in list(self._tasks.values()))

    @contextlib.contextmanager
    def _interrupt_deferral(self) -> Iterator[None]:
        """（v33，審碼 b3 r4 codex P1-01）中斷於訊號層延後：本排程器於主執行緒執行期間，SIGINT 到達時若仍有未確認
        退出之 executor ⇒ 只記錄並停止准入（不拋例外，任何位元組碼時點皆同）；無未 joined 者 ⇒ 交原處理器（預設即
        KeyboardInterrupt）。結束後還原處理器；期間記錄之中斷於全部回收後由 `run` 上拋（另有原例外者以原例外為準）。
        非主執行緒（API 經 executor 執行緒）不受 SIGINT 例外影響，不安裝。"""
        self._interrupt_pending = False
        if threading.current_thread() is not threading.main_thread():
            yield
            return
        previous = signal.getsignal(signal.SIGINT)
        if not callable(previous):  # SIG_IGN／SIG_DFL／非 Python 安裝者：不介入
            yield
            return

        def handler(signum: int, frame: Any) -> None:
            if self._has_unjoined():
                self._interrupt_pending = True  # 只發布旗標：處理器內不取任何鎖（v34，審碼 b3 r5 codex P1-01）
                return
            previous(signum, frame)

        try:
            signal.signal(signal.SIGINT, handler)  # 安裝於 try 內：安裝後即中斷亦還原（v34，審碼 b3 r5 codex P2-02）
            yield
        finally:
            signal.signal(signal.SIGINT, previous)

    def request_stop(self) -> None:
        """呼叫端取消（可由其他執行緒呼叫）：佇列中未准入之任務不再執行（結果為 `SchedulerStopped`）；已啟動者照常
        確認退出，`run` 於其全部回收後才返回。"""
        self._stop_requested.set()

    def _join_state(self, state: _TaskState) -> None:
        """shutdown(wait=True) 成功（worker 已退出）後才標 joined；失敗原樣上拋、狀態不變。"""
        state.executor.shutdown(wait=True)
        with self._lock:
            state.status = "joined"
        self._event("joined", state.task.task_id)

    def _join_confirmed(self, state: _TaskState) -> None:
        """確認退出才返回（SPEC v30）：shutdown 失敗 ⇒ 狀態保留未 joined、記 `join_retry`，等該任務之 future 完成後
        以同一 shutdown 再試，直到成功。持續失敗即持續等待——持有者（域／守護）不得於確認退出前回收，亦不以固定
        逾時強殺未超上限之 worker；守護於此期間照常監看全樹。"""
        import concurrent.futures as cf

        attempts = 0
        while True:
            try:
                self._join_state(state)
                return
            except Exception:  # noqa: BLE001 — 未確認退出：不標 joined、不交還持有者
                attempts += 1
                self._event("join_retry", state.task.task_id)
                if state.future is not None:
                    cf.wait([state.future])
                time.sleep(min(0.05 * attempts, 1.0))

    def _join_unjoined(self) -> None:
        """例外出口：全部確認退出後，原例外才由呼叫端上拋。回收期間之中斷（KeyboardInterrupt 等，含 shutdown、
        future 等待與重試間隔中）一律延後——未確認退出前不交還持有者（v32，審碼 b3 r3 codex P1-01）。"""
        for state in list(self._tasks.values()):
            deferred = 0
            while state.executor is not None and state.status != "joined":
                try:
                    if deferred:  # 記錄與重試間隔皆在保護區內（v33，審碼 b3 r4 codex P1-01／P2-02）
                        self._event("interrupt_deferred", state.task.task_id)
                        time.sleep(min(0.05 * deferred, 1.0))
                    self._join_confirmed(state)
                except BaseException:  # noqa: BLE001 — 中斷延後：原例外優先，回收完成前不放手；except 體只計數
                    deferred += 1

    def _run_waves(self, queue: "Deque[_TaskState]", results: List[Any],
                   worker_fn: Callable[[DomainDescriptor, Any], Any], serial_fn: Callable[[Any], Any],
                   on_wave_joined: Callable[[List[Any]], None]) -> int:
        import concurrent.futures as cf

        parallel_ever = 0
        while queue:
            wave: List[_TaskState] = []
            while queue and len(wave) < self.max_workers:
                if self._stop_requested.is_set() or self._interrupt_pending:  # 取消或延後之中斷：不再准入／串行執行新任務（已啟動者照常確認退出）
                    for pending_state in queue:
                        results[pending_state.index] = SchedulerStopped(pending_state.task.task_id)
                    queue.clear()
                    break
                head = queue[0]
                if head.task.envelope is None or self.aux_startup_envelope is None or self._reroute_seen:
                    if wave:
                        break
                    queue.popleft()
                    self._record_serial(head, "no_envelope" if head.task.envelope is None else (
                        "no_aux_receipt" if self.aux_startup_envelope is None else "after_reroute"))
                    results[head.index] = self._run_serial(head, serial_fn)
                    continue
                if not wave:
                    self._register_aux_slot()
                admission_state = self.snapshot()
                decision = admit(admission_state, int(head.task.envelope), int(head.task.disk_bytes))
                if not decision.ok:
                    if wave:
                        break
                    queue.popleft()
                    self._record_serial(head, f"admission:{decision.reason}", admission_state)
                    results[head.index] = self._run_serial(head, serial_fn)
                    continue
                queue.popleft()
                self._submit(head, worker_fn)
                wave.append(head)
                self._wait_bound(head)
            if not wave:
                continue
            parallel_ever = max(parallel_ever, len(wave))
            pending = {state.future: state for state in wave}
            while pending:
                done, _ = cf.wait(list(pending), return_when=cf.FIRST_COMPLETED)
                for future in done:
                    state = pending.pop(future)
                    with self._lock:
                        self._refresh_bindings()
                        failed = future.exception() is not None
                        state.status = "failed" if failed else "completed"
                    self._event(state.status, state.task.task_id)
            wave_results: List[Any] = []
            rerouted: List[_TaskState] = []
            for state in wave:
                self._join_confirmed(state)
                self._collect_worker_routes(state)
                exc = state.future.exception()
                if isinstance(exc, MemoryRerouteNeeded):
                    rerouted.append(state)  # SPEC v35：該波 join 後於根之正式串行 producer 重試一次
                    continue
                value = exc if exc is not None else state.future.result()
                results[state.index] = value
                wave_results.append(value)
            self._event("wave_joined", "")
            on_wave_joined(wave_results)
            for state in rerouted:
                self._reroute_seen = True  # 根停止新准入：其後任務一律正式串行臂
                self._event("reroute", state.task.task_id)
                self._record_serial(state, "estimate_exceeded")
                results[state.index] = self._run_serial(state, serial_fn)
        return parallel_ever

    def _submit(self, state: _TaskState, worker_fn: Callable[[DomainDescriptor, Any], Any]) -> None:
        # 本次嘗試前撤同 task_id 之舊 worker 紀錄檔（同一 domain_dir 重跑時不得誤讀前次紀錄；審碼 b3 r9 codex P2-01）
        with contextlib.suppress(FileNotFoundError):
            (self.domain_dir / ROUTES_DIR_NAME / f"{state.task.task_id}.json").unlink()
        executor = self._executor_factory(1)
        self._event("executor_created", "")
        state.executor = executor
        self.mark_starting(state.task.task_id)
        self._event("admitted", state.task.task_id)
        descriptor = DomainDescriptor(root_pid=os.getpid(), domain_dir=self.domain_dir, budget=self.budget,
                                      task_id=state.task.task_id, envelope=int(state.task.envelope or 0),
                                      stop_dir=self.stop_dir)
        state.future = executor.submit(_trampoline, descriptor, worker_fn, state.task.payload, self._task_identity)

    def _run_serial(self, state: _TaskState, serial_fn: Callable[[Any], Any]) -> Any:
        with self._lock:
            state.status = "serial"
        self._event("serial", state.task.task_id)
        ctx = _ACTIVE.get()
        before = 0 if ctx is None else len(ctx.routes)
        try:
            return serial_fn(state.task.payload)
        except Exception as exc:  # noqa: BLE001 — 與並行臂同：失敗以值交呼叫端分類
            return exc
        finally:
            with self._lock:
                state.status = "joined"
                if ctx is not None and len(ctx.routes) > before:  # 根之串行臂：本次生成交回根情境之紀錄
                    self.task_routes.setdefault(state.task.task_id, []).extend(ctx.routes[before:])


_ROOT_START: Dict[int, float] = {}


def _root_start_time() -> float:
    pid = os.getpid()
    if pid not in _ROOT_START:
        _ROOT_START[pid] = process_start_time(pid) if sys.platform == "darwin" else 0.0
    return _ROOT_START[pid]


# ---------------------------------------------------------------- 正式域（三個 pool 之根）

def default_read_system(stop_dir: Path, guard_pid: Optional[int]) -> Callable[[], Any]:
    """正式 read_system：VM 快照、停止旗標（守護寫於 `stop_dir`）、根 footprint、守護與 resource tracker 成員。"""

    def read() -> Any:
        snapshot = sample_vm_snapshot()
        aux: List[Member] = []
        if guard_pid and _pid_alive(guard_pid):
            aux.append(Member(pid=guard_pid, start_time=process_start_time(guard_pid),
                              footprint=sample_footprint_of(guard_pid), role="guard"))
        tracker = _resource_tracker_pid()
        if tracker is not None and _pid_alive(tracker):
            aux.append(Member(pid=tracker, start_time=process_start_time(tracker),
                              footprint=sample_footprint_of(tracker), role="tracker"))
        return (system_absorbable_bytes(snapshot), snapshot.pressure_level, stop_flag_set(stop_dir),
                sample_memory_bytes(), tuple(aux), snapshot.swap_volume_free_bytes,
                disk_reserve_bytes(snapshot.swapfile_size_max))

    return read


def _resource_tracker_pid() -> Optional[int]:
    try:
        from multiprocessing import resource_tracker  # noqa: PLC0415

        pid = getattr(resource_tracker._resource_tracker, "_pid", None)  # noqa: SLF001
        return int(pid) if pid else None
    except Exception:  # noqa: BLE001 — 無 tracker 即無輔助成員
        return None


def default_read_task_footprint(domain_dir: Path) -> Callable[[str], int]:
    def read(task_id: str) -> int:
        path = Path(domain_dir) / MEMBERS_DIR_NAME / f"{task_id}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return 0
        pid = int(payload.get("os_pid") or payload["pid"])
        try:
            return sample_footprint_of(pid)
        except MemoryMeasurementUnavailable:
            if _pid_alive(pid):
                raise
            return 0

    return read


def spawn_executor_factory(max_workers: int) -> Any:
    """正式 executor：spawn 之 ProcessPoolExecutor（三個 pool 唯一之建構處）。"""
    import multiprocessing as mp  # noqa: PLC0415
    from concurrent.futures import ProcessPoolExecutor  # noqa: PLC0415

    return ProcessPoolExecutor(max_workers=max_workers, mp_context=mp.get_context("spawn"))


class BudgetDomain:
    """域根（`run_multi_symbol`／API 批次 wave／多週期並行）：域目錄、恰一守護（外層已有受保護 run 時沿用）。"""

    def __init__(self, domain_dir: Optional[Path] = None, run_id: str = "domain") -> None:
        self.domain_dir = Path(domain_dir) if domain_dir is not None else Path(tempfile.mkdtemp(prefix="icfa_domain_"))
        self.domain_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.guard: Optional[GuardHandle] = None
        self._token: Optional[contextvars.Token] = None
        self._owns_dir = domain_dir is None
        outer = _ACTIVE.get()
        self.outer = outer

    def start(self) -> "BudgetDomain":
        if self.outer is not None:
            # 多週期並行於受保護 run 內：守護沿用該 run（同一域根行程），停止旗標亦同讀
            self.guard = None
            return self
        self.guard = sys.modules[__name__].start_guard(self.domain_dir, self.run_id,
                                                       budget=configured_budget_bytes(include_override=False))
        guard = self.guard if isinstance(self.guard, GuardHandle) else None
        self._token = _ACTIVE.set(_RunContext(mode="root", stop_dir=self.domain_dir,
                                              guard_pid=None if guard is None else guard.pid,
                                              checkpoint_file=None if guard is None else guard.extra.get("checkpoint_file")))
        return self

    @property
    def guard_handle(self) -> Optional[GuardHandle]:
        return self.guard if isinstance(self.guard, GuardHandle) else None

    def close(self) -> None:
        try:
            if isinstance(self.guard, GuardHandle):
                self.guard.stop()
        finally:
            self.guard = None
            if self._token is not None:
                with contextlib.suppress(ValueError):
                    _ACTIVE.reset(self._token)
                self._token = None
            if self._owns_dir:
                shutil.rmtree(self.domain_dir, ignore_errors=True)

    def stop_dir(self) -> Path:
        if self.outer is not None and self.outer.stop_dir is not None:
            return self.outer.stop_dir
        return self.domain_dir

    def guard_pid(self) -> Optional[int]:
        if self.guard is not None:
            return self.guard.pid
        return None if self.outer is None else self.outer.guard_pid


def create_scheduler(*, domain_dir: Path, max_workers: int, executor_factory: Optional[Callable[[int], Any]] = None,
                     aux_startup_envelope: Any = "default", task_identity: Optional[Callable[[], Any]] = None,
                     read_system: Optional[Callable[[], Any]] = None,
                     read_task_footprint: Optional[Callable[[str], int]] = None,
                     guard: Optional[GuardHandle] = None, budget: Optional[int] = None) -> MemoryBudgetScheduler:
    """排程器之正式組裝（`momentum.factories.create_memory_budget_scheduler` 之實作）；未給者取正式預設。

    守護與停止旗標：給定 `guard` 者用之；否則沿用本執行緒受保護 run／域根之守護與停止旗標目錄（多週期並行
    位於受保護 run 內，守護即該 run 之守護、旗標寫於 run 目錄）。"""
    domain_dir = Path(domain_dir)
    ctx = _ACTIVE.get()
    guard_pid = guard.pid if isinstance(guard, GuardHandle) else (None if ctx is None else ctx.guard_pid)
    stop_dir = (ctx.stop_dir if ctx is not None and ctx.stop_dir is not None and not isinstance(guard, GuardHandle)
                else domain_dir)
    return MemoryBudgetScheduler(
        configured_budget_bytes() if budget is None else int(budget), domain_dir=domain_dir, max_workers=max_workers,
        executor_factory=executor_factory or spawn_executor_factory,
        read_system=read_system or default_read_system(stop_dir, guard_pid),
        read_task_footprint=read_task_footprint or default_read_task_footprint(domain_dir),
        aux_startup_envelope=AUX_TRACKER_STARTUP_ENVELOPE_BYTES if aux_startup_envelope == "default" else aux_startup_envelope,
        task_identity=task_identity, stop_dir=stop_dir)


def enter_worker_domain(descriptor: Optional[DomainDescriptor]) -> Optional[contextvars.Token]:
    """worker 入口：以顯式域描述設本執行緒之域情境（無描述 ⇒ 不動）。"""
    if descriptor is None:
        return None
    return _ACTIVE.set(_RunContext(mode="worker", stop_dir=Path(descriptor.stop_dir or descriptor.domain_dir), domain=descriptor))


def exit_worker_domain(token: Optional[contextvars.Token]) -> None:
    if token is not None:
        with contextlib.suppress(ValueError):
            _ACTIVE.reset(token)


def in_domain_worker() -> bool:
    ctx = _ACTIVE.get()
    return ctx is not None and ctx.mode == "worker"


__all__ = [
    "GenerationMemoryBudgetExceeded", "MemoryRerouteNeeded", "MemoryMeasurementUnavailable", "UnknownBudgetBranchError",
    "SchedulerStopped", "Component", "VMSnapshot", "available_bytes", "swap_expansion_bytes", "route",
    "record_route", "route_records",
    "SELECTORS", "NON_ARM_FFACT_KEYS", "BRANCH_TABLE", "STOP_FLAG_NAME", "ABORT_RECEIPT_NAME", "OWNED_PATHS_NAME",
    "sample_memory_bytes", "sample_footprint_of", "sample_vm_snapshot", "system_absorbable_bytes",
    "disk_reserve_bytes", "budget_bytes", "planned_bytes", "normalize_selectors", "selector", "check",
    "reset_interval_peak", "read_interval_peak", "backing_bus_protocol", "assert_disk_backed", "mapping_root",
    "GuardHandle", "start_guard", "stop_flag_set", "register_owned_path", "recover_aborted_run",
    "sampler_override", "budget_override", "vm_snapshot_override", "check_recorder", "layer_end",
    "DomainDescriptor", "Member", "Slot", "AdmissionState", "Admission", "commitment", "admit", "measured_total",
    "guard_should_stop", "Task", "MemoryBudgetScheduler",
]
