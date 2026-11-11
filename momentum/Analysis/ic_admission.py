"""IC 分析啟動准入（ICPERF SPEC v5.87 Task 0.6 (h)「⑤ IC 分析啟動准入」；諮詢 r165 收斂檔 C3、審查 r166／r167）。

取代固定欄數上限 `ic_analysis_max_features`：每個任務以估算之新增峰值 P 申請保留量。
- P ＞ 正式預算 R ⇒ `ICMemoryNeedExceedsBudget`（單任務即逾預算；Task 3.2 分塊前之殘留，回報 need／have）。
- 同一把鎖內取即時快照：P ≤ 即時可用量 A − 執行中任務之保留量 ⇒ admitted；否則有執行中任務 ⇒ queued（附等待原因），
  無執行中任務（無可等之釋放）⇒ `ICMemoryNeedExceedsBudget`（have＝即時可用量；活性：排隊不得無限等待）。
  執行中任務之保留量以其全額計（無法逐任務量測已用部分 ⇒ 保守），終態任務仍持有之物件已反映於 A。
- 釋放（worker 真正結束時由服務呼叫，可重複呼叫）後依先進先出重查排隊任務：每次重取快照，第一個放不下者即停
  （不越序），放得下者轉 admitted 並於鎖外呼叫 `on_admit(task_id)` 由服務啟動之。
- 排隊中取消 ⇒ cancelled、不再出隊；執行中取消不釋放（等 worker 結束）。
單一 API 行程之支援邊界：保留量存於本行程記憶體。
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional


class ICMemoryNeedExceedsBudget(RuntimeError):
    """單任務估算峰值逾正式預算（Task 3.2 殘留）：帶 need／have、成分與量測來源。"""

    def __init__(self, need_bytes: int, have_bytes: int, components: List[Dict[str, Any]], source: str) -> None:
        super().__init__(f"IC 分析估算記憶體 {need_bytes} B 超過預算 {have_bytes} B（{source}）")
        self.need_bytes = int(need_bytes)
        self.have_bytes = int(have_bytes)
        self.components = list(components)
        self.source = source


class ICAdmissionController:
    """同鎖准入、排隊（等待原因）、出隊重查即時可用量、worker 結束釋放、取消。"""

    def __init__(self, snapshot: Callable[[], Dict[str, Any]]) -> None:
        self._snapshot = snapshot
        self._lock = threading.Lock()
        self._released = threading.Condition(self._lock)  # 釋放／縮減時喚醒 `extend` 之等待者（事件驅動，無牆鐘）
        self._extending: set = set()  # 正於 `extend` 等待之任務（互等偵測）
        self._states: Dict[str, str] = {}
        self._planned: Dict[str, int] = {}
        self._reserved: Dict[str, int] = {}
        self._queue: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self.on_admit: Optional[Callable[[str], None]] = None
        self.on_reject: Optional[Callable[[str, "ICMemoryNeedExceedsBudget"], None]] = None

    def _free_locked(self, snap: Dict[str, Any]) -> int:
        return int(snap["available_bytes"]) - sum(self._reserved.values())

    def request(self, task_id: str, planned_bytes: int, components: Optional[List[Dict[str, Any]]] = None) -> str:
        """申請保留量；回 `admitted` 或 `queued`；單任務逾正式預算 ⇒ `ICMemoryNeedExceedsBudget`。"""
        planned = int(planned_bytes)
        with self._lock:
            snap = self._snapshot()
            budget = int(snap["budget_bytes"])
            if planned > budget:
                raise ICMemoryNeedExceedsBudget(planned, budget, list(components or []), str(snap.get("source", "")))
            free = self._free_locked(snap)
            if not self._queue and planned <= free:
                self._planned[task_id] = planned
                self._reserved[task_id] = planned
                self._states[task_id] = "admitted"
                return "admitted"
            if not self._reserved:
                # 無執行中任務可釋放 ⇒ 排隊永遠等不到重查（活性）；即時可用量不足即依 SPEC ⑤「仍不足回報 need／have」
                raise ICMemoryNeedExceedsBudget(planned, max(free, 0), list(components or []),
                                                str(snap.get("source", "")))
            self._planned[task_id] = planned
            self._queue[task_id] = {"need_bytes": planned, "have_bytes": max(free, 0),
                                    "measurement_source": str(snap.get("source", ""))}
            self._states[task_id] = "queued"
            return "queued"

    def release(self, task_id: str) -> None:
        """worker 結束時釋放（重複呼叫無作用），並依先進先出重查排隊任務。"""
        admitted: List[str] = []
        rejected: List[ICMemoryNeedExceedsBudget] = []
        rejected_ids: List[str] = []
        with self._lock:
            if self._states.get(task_id) != "admitted":
                return
            self._reserved.pop(task_id, None)
            self._states[task_id] = "released"
            self._released.notify_all()
            while self._queue:
                head, reason = next(iter(self._queue.items()))
                snap = self._snapshot()
                free = self._free_locked(snap)
                need = self._planned[head]
                if need <= free:
                    self._queue.pop(head)
                    self._reserved[head] = need
                    self._states[head] = "admitted"
                    admitted.append(head)
                    continue
                if self._reserved:
                    reason.update(have_bytes=max(free, 0), measurement_source=str(snap.get("source", "")))
                    break
                # 已無執行中任務可再釋放、隊首仍放不下 ⇒ 不得無限等待：回報 need／have（活性）
                self._queue.pop(head)
                self._states[head] = "rejected"
                rejected_ids.append(head)
                rejected.append(ICMemoryNeedExceedsBudget(need, max(free, 0), [], str(snap.get("source", ""))))
        for head in admitted:
            if self.on_admit is not None:
                self.on_admit(head)
        for head, err in zip(rejected_ids, rejected):
            if self.on_reject is not None:
                self.on_reject(head, err)

    def extend(self, task_id: str, extra_bytes: int, components: Optional[List[Dict[str, Any]]] = None) -> None:
        """執行中任務於某階段需額外記憶體（如第 6 段冗餘相關矩陣，審碼 r169 GROK-R169-P1-02）：同一把鎖內以
        「即時可用量 − 全部保留量」判定，足 ⇒ 加入本任務之保留量；不足而有其他執行中任務 ⇒ 等其釋放（事件喚醒）；
        已無其他任務可等 ⇒ `ICMemoryNeedExceedsBudget`（need／have）。"""
        extra = int(extra_bytes)
        with self._released:
            try:
                while True:
                    snap = self._snapshot()
                    free = self._free_locked(snap)
                    if extra <= free:
                        self._reserved[task_id] = self._reserved.get(task_id, 0) + extra
                        return
                    # 可等之對象＝其他執行中且**未在等待額外配置**之任務；全在等待 ⇒ 互等死鎖，即拒（活性）
                    if not any(k != task_id and k not in self._extending for k in self._reserved):
                        raise ICMemoryNeedExceedsBudget(extra, max(free, 0), list(components or []),
                                                        str(snap.get("source", "")))
                    self._extending.add(task_id)
                    self._released.wait()
            finally:
                self._extending.discard(task_id)

    def shrink(self, task_id: str, extra_bytes: int) -> None:
        """歸還 `extend` 之額外保留量（階段結束）；任務已釋放者不作用。"""
        with self._released:
            if task_id in self._reserved:
                self._reserved[task_id] = max(self._reserved[task_id] - int(extra_bytes), 0)
                self._released.notify_all()

    def cancel(self, task_id: str) -> None:
        """排隊中取消 ⇒ cancelled（不再出隊）；執行中不釋放（由 worker 結束時 `release`）。"""
        with self._lock:
            if self._states.get(task_id) == "queued":
                self._queue.pop(task_id, None)
                self._states[task_id] = "cancelled"

    def state(self, task_id: str) -> str:
        with self._lock:
            return self._states.get(task_id, "unknown")

    def wait_reason(self, task_id: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self._queue.get(task_id, {}))

    def reserved_bytes(self) -> int:
        """執行中任務保留量總和（生命週期測試斷言無外漏）。"""
        with self._lock:
            return sum(self._reserved.values())
