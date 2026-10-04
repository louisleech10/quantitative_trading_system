"""生成記憶體預算：取樣、配置前判定、分支表、選擇子正規化、磁碟後援、守護生命週期與強制停止後之恢復
（docs/ICFIRSTALIGN_SPEC.md v17 Task 4.2；取樣與預算判定之唯一實作）。

預算量＝致 OOM 之量：macOS `proc_pid_rusage(RUSAGE_INFO_V0)` 之 `ri_phys_footprint`（本行程＋守護行程）。
檔案映射於已確認磁碟後援時不計入；linux 暫不支援（`MemoryMeasurementUnavailable`）。
`check` 須三條件皆成立方放行：本程式 footprint＋planned ≤ 上限（實體記憶體 × ratio）、核心壓力等級非危急、
planned ≤ 系統可吸收量（free＋file-backed＋現有換頁剩餘；換頁擴充計 0）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Mapping, Optional, Sequence


class GenerationMemoryBudgetExceeded(RuntimeError):
    """配置前預算判定不通過（本程式超上限／壓力危急／系統可用不足），或守護停止旗標已立。"""

    def __init__(self, label: str, current: int, planned: int, budget: int, reason: str) -> None:
        super().__init__(f"{reason}：{label} 目前 {current} B＋計畫 {planned} B，上限 {budget} B")
        self.label = label
        self.current = current
        self.planned = planned
        self.budget = budget
        self.reason = reason


class MemoryMeasurementUnavailable(RuntimeError):
    """無法取得致 OOM 之量或無法確認磁碟後援（linux、其他平台、API 失敗、`Disk Image`、守護啟動失敗）。"""


class UnknownBudgetBranchError(KeyError):
    """分派點宣告之分支 ID 不在分支表或無估算函式（配置前具名拒絕）。"""


ComponentKind = Literal["anon", "mapped"]


@dataclass(frozen=True)
class Component:
    """估算成分：`anon`（不可回收配置）入 planned_bytes；`mapped`（檔案映射，宣告入口）不入。"""

    name: str
    kind: ComponentKind
    nbytes: int
    entry: Optional[str] = None
    count: int = 1


@dataclass(frozen=True)
class VMSnapshot:
    """同一時點之系統讀數（`host_statistics64`、`vm.swapusage`、壓力等級、換頁卷）。"""

    free_bytes: int
    file_backed_bytes: int
    swap_free_bytes: int
    pressure_level: int
    swap_volume_free_bytes: int
    swap_volume_capacity_bytes: int


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

# 非臂選擇之 FFACT_ 鍵（具名排除清單；AST 掃描未列於兩清單之任一鍵 ⇒ 紅）。實作時逐一登記。
NON_ARM_FFACT_KEYS: Sequence[str] = ()

# 分支表（唯一一份）：分支 ID → 估算函式（形狀參數 → 成分列）。實作時登記契約 branch_ids 全部。
BRANCH_TABLE: Dict[str, Callable[[Mapping[str, Any]], List[Component]]] = {}

STOP_FLAG_NAME = "memory_guard_stop.flag"
ABORT_RECEIPT_NAME = "memory_guard_abort.json"
OWNED_PATHS_NAME = "owned_paths.json"


def sample_memory_bytes() -> int:
    """本行程致 OOM 之量（macOS `ri_phys_footprint`）；linux／其他平台／失敗 ⇒ `MemoryMeasurementUnavailable`。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def sample_footprint_of(pid: int) -> int:
    """他行程（同使用者）之 `ri_phys_footprint`；守護與目前用量（本行程＋守護）用。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def sample_vm_snapshot() -> VMSnapshot:
    """同一時點之 VM 讀數；任一取不到 ⇒ `MemoryMeasurementUnavailable`。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def system_absorbable_bytes(snapshot: VMSnapshot) -> int:
    """free＋file-backed＋現有換頁剩餘（換頁擴充計 0；匿名與壓縮器頁不計）。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def disk_reserve_bytes(volume_capacity_bytes: int) -> int:
    """磁碟保留量＝max(4 GiB, 卷容量 × 5%)。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def budget_bytes(physical_bytes: int, ratio: float = 0.75, absolute_bytes: Optional[int] = None) -> int:
    """上限＝實體記憶體 × ratio；`absolute_bytes` 給定時以之覆寫。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def planned_bytes(components: Sequence[Component]) -> int:
    """planned_bytes 只加總 `anon` 成分（`mapped` 不入）。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def normalize_selectors(env: Mapping[str, str]) -> Dict[str, str]:
    """選擇子正規化；非法或未知值 ⇒ `ValueError`（不得靜默退預設）。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def selector(name: str) -> str:
    """producer 讀臂選擇子之唯一入口（自環境讀並正規化）。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def check(branch_id: str, components: Sequence[Component], *, label: Optional[str] = None,
          run_dir: Optional[Path] = None) -> None:
    """配置前判定。分支 ID 不在分支表 ⇒ `UnknownBudgetBranchError`；停止旗標已立或三條件任一不成立 ⇒
    `GenerationMemoryBudgetExceeded`（reason 為契約 budget_messages 之一）。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def reset_interval_peak() -> int:
    """重設本行程之區間峰值（`proc_reset_footprint_interval`）並回傳當下 footprint。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def read_interval_peak() -> int:
    """讀本行程之區間最大 footprint（`RUSAGE_INFO_V4` 之 `ri_interval_max_phys_footprint`）。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def backing_bus_protocol(path: Path) -> Optional[str]:
    """路徑所在掛載之 `diskutil info -plist` 之 `BusProtocol`（依 st_dev 去重、行程內快取）；取不到 ⇒ None。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def assert_disk_backed(paths: Sequence[Path]) -> None:
    """各路徑之掛載皆非 `Disk Image` 且可取得 ⇒ 通過；否則 `MemoryMeasurementUnavailable`。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def mapping_root(run_dir: Path) -> Path:
    """run 之映射根（暫存 memmap 與校準暫存 registry 一律建於此下）。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


@dataclass
class GuardHandle:
    """一次受保護 run 之守護行程控制。"""

    pid: int
    run_dir: Path
    run_id: str
    extra: Dict[str, Any] = field(default_factory=dict)

    def stop(self) -> None:
        """送停止訊號並等待回收。"""
        raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def start_guard(run_dir: Path, run_id: str, *, budget: int) -> GuardHandle:
    """以檔案路徑啟動 `memory_guard.py`；首讀失敗 ⇒ `MemoryMeasurementUnavailable`。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def stop_flag_set(run_dir: Path) -> bool:
    """守護之停止旗標是否已立（單次 stat）。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def register_owned_path(run_dir: Path, path: Path) -> None:
    """將本 run 建立之暫存路徑登記於 `owned_paths.json`。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def recover_aborted_run(run_dir: Path) -> Dict[str, Any]:
    """同 key 下次 run 取得 lease 後：讀前次 abort 收據，刪其登記且仍存在之暫存、清舊停止旗標；回報處理項。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


# ---------------------------------------------------------------- 測試接縫（只供驗收測試注入；生產不呼叫）

def sampler_override(fn: Callable[[], Mapping[str, int]]) -> Any:
    """context manager：以 `fn()` 回傳之 {"resident": B, "phys_footprint": B} 取代 `_read_rusage`。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def budget_override(nbytes: int) -> Any:
    """context manager：本 context 內上限改為 `nbytes`（絕對位元組）。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def vm_snapshot_override(snapshot: VMSnapshot) -> Any:
    """context manager：本 context 內 `sample_vm_snapshot` 回傳 `snapshot`。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


def check_recorder() -> Any:
    """context manager：記錄本 context 內每次 `check` 之 (branch_id, components)；回傳 list。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


__all__ = [
    "GenerationMemoryBudgetExceeded", "MemoryMeasurementUnavailable", "UnknownBudgetBranchError", "Component", "VMSnapshot",
    "SELECTORS", "NON_ARM_FFACT_KEYS", "BRANCH_TABLE", "STOP_FLAG_NAME", "ABORT_RECEIPT_NAME", "OWNED_PATHS_NAME",
    "sample_memory_bytes", "sample_footprint_of", "sample_vm_snapshot", "system_absorbable_bytes",
    "disk_reserve_bytes", "budget_bytes", "planned_bytes", "normalize_selectors", "selector", "check",
    "reset_interval_peak", "read_interval_peak", "backing_bus_protocol", "assert_disk_backed", "mapping_root",
    "GuardHandle", "start_guard", "stop_flag_set", "register_owned_path", "recover_aborted_run",
    "sampler_override", "budget_override", "vm_snapshot_override", "check_recorder",
]
