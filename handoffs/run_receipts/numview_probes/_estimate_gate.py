"""NUMVIEW 重型跑之機械前置（docs/NUMVIEW_SPEC.md §C「重型跑紀律」、Task 0.4，R2-B）。

`scripts/numview_freeze_baseline.py` 與本目錄每個呼叫生成入口之探針，於主入口內、任何生成呼叫之前呼叫
`require(run_kind, cells)`：估時收據（`handoffs/run_receipts/<date>-numview-estimate.json`）不存在、無
`reported_at`（主委白話報使用者後寫入）、或所請格不在收據該跑別之格清單 ⇒ 拋 `EstimateGateError`（不只 log）。

本檔為 TODO 階段空殼（Task 0.4 實作）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Sequence

REPO: Path = Path(__file__).resolve().parents[3]
RECEIPTS_DIR: Path = REPO / "handoffs" / "run_receipts"
#: 估時收據檔名樣式（恰一份；多份或零份 ⇒ 拒跑）
ESTIMATE_RECEIPT_GLOB = "*-numview-estimate.json"


class EstimateGateError(RuntimeError):
    """估時前置不成立（收據缺、`reported_at` 缺、格不在收據該跑別之格清單）⇒ 拒跑（SPEC Task 0.4 ②）。"""


def load_estimate_receipt(receipts_dir: Optional[Path] = None) -> Dict[str, Any]:
    """讀估時收據（`receipts_dir` 預設 `RECEIPTS_DIR`；恰一份符合 `ESTIMATE_RECEIPT_GLOB`）；缺或多份 ⇒ `EstimateGateError`。"""
    raise NotImplementedError("NUMVIEW Task 0.4")


def require(run_kind: str, cells: Sequence[str], *, receipts_dir: Optional[Path] = None) -> None:
    """重型跑前置（SPEC Task 0.4）：收據存在、含 `reported_at`、且 `cells` 全屬收據 `run_kind` 跑別之格清單，否則拋錯。"""
    raise NotImplementedError("NUMVIEW Task 0.4")
