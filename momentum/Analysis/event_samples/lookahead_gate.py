"""GAP-3 UX Task 1.12 — 深度不可證則禁進切分（D-7 之 L3）。

L1（Task 1.10 registry）回答「這個欄看多遠」，L2（Task 1.11）在解析不出時**強制宣告**，
本檔是最後一層：**宣告缺失或與 registry 衝突之批，禁止進入 train/test 切分與條件 IC**，
但**仍可產出事件研究表**（無訓練即無洩漏）。

🔴 兩個設計約束（SPEC Task 1.12「不可做」）：
  1. **不得**以「警告後放行」替代（fail-open）——`split_events` 走 raise、`ic_feed` 走
     `capability_status="unavailable"`，兩者都不是警告字串。
  2. **不得**把 reason 字面硬寫進程式——字面唯一住
     `momentum/Analysis/contracts/event_import_contract.json`，本檔只給**綁定鍵**。

🔴 `gate is None` ＝**平台產生器路徑**（`generator.py`／既有 `run()` 之非匯入呼叫），不開本閘；
與 Task 1.8 之 `enforce_batch_homogeneity` 同一先例：閘由**使用者匯入路徑**顯式開啟。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple

#: 契約 `capability_reason_bindings` 之綁定鍵（**不是** reason 字面本身；字面見契約檔）。
CAPABILITY_BINDING_L3 = "l3_lookahead_unverifiable"


def split_blocked_reason(contract: Optional[Mapping[str, Any]] = None) -> str:
    """L3 拒絕之 capability reason 字面（唯一來源＝契約之具名綁定）。"""
    from momentum.Analysis.event_samples.import_contract import capability_unavailable_reason

    return capability_unavailable_reason(CAPABILITY_BINDING_L3, dict(contract) if contract is not None else None)


class SplitBlockedError(RuntimeError):
    """深度不可證之批被送進切分／條件 IC（fail-closed；`reason` 字面取自契約）。"""

    def __init__(self, detail: str = "", *, contract: Optional[Mapping[str, Any]] = None):
        self.reason = split_blocked_reason(contract)
        self.detail = str(detail)
        super().__init__(f"{self.reason}: {detail}" if detail else self.reason)


@dataclass(frozen=True)
class LookaheadGate:
    """一個批次之 L3 狀態（由 L2 之宣告解析產生；本檔不重做宣告判定）。

    blocked：True ⇒ 禁進切分與條件 IC，只能走 `run_event_study_only()`。
    detail：給使用者看的原因敘述（**不是** reason 字面；字面由 `split_blocked_reason()` 給）。
    unresolved_columns：導致封鎖之欄（診斷用；空 tuple 表示封鎖來自宣告缺失而非特定欄）。
    """

    blocked: bool
    detail: str = ""
    unresolved_columns: Tuple[str, ...] = ()

    @classmethod
    def allowed(cls) -> "LookaheadGate":
        return cls(blocked=False)

    @classmethod
    def blocked_by(cls, detail: str, unresolved_columns: Tuple[str, ...] = ()) -> "LookaheadGate":
        return cls(blocked=True, detail=detail, unresolved_columns=tuple(unresolved_columns))


def is_blocked(gate: Optional[LookaheadGate]) -> bool:
    """未提供 gate ⇒ 平台產生器路徑，不開閘（見檔頭）。"""
    return gate is not None and bool(gate.blocked)


def assert_split_allowed(gate: Optional[LookaheadGate], *, where: str) -> None:
    """切分側之拒絕分支（`split_events`／`run()` 用）：blocked ⇒ raise，**不得**只記 log。"""
    if is_blocked(gate):
        raise SplitBlockedError(f"{where}: {gate.detail}" if gate.detail else where)


def capability_unavailable_block(
    gate: Optional[LookaheadGate],
    contract: Optional[Mapping[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """條件 IC 側之拒絕分支（`ic_feed` 用）：blocked ⇒ 回 capability 區塊，否則 `None`。

    回傳形狀與 `ic_feed` 既有之 unavailable 分支一致（`capability_status`＋`reason`），
    不另造一套。
    """
    if not is_blocked(gate):
        return None
    return {
        "capability_status": "unavailable",
        "reason": split_blocked_reason(contract),
        "detail": gate.detail,
        "unresolved_columns": list(gate.unresolved_columns),
    }


__all__ = [
    "CAPABILITY_BINDING_L3",
    "LookaheadGate",
    "SplitBlockedError",
    "assert_split_allowed",
    "capability_unavailable_block",
    "is_blocked",
    "split_blocked_reason",
]
