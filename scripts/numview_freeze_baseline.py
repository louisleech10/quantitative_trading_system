"""NUMVIEW 改前基準凍結（docs/NUMVIEW_SPEC.md §G、Task 0.5）。

於任何產品碼改動前之 HEAD 凍結 §G：
- G1 IC 頁第三步輸出：每個格 A 之 IC-first 選欄，以 `ApplyTransformsRequest` 預設請求，分別於每個現行可達之臂各跑
  `_apply_transforms_sync` 之同一轉換：`polars`（`FFACT_USE_POLARS=1`）、`pandas_optimized`（`=0`）、`pandas_legacy`
  （`=0`＋`FFACT_L65_OPTIMIZATION_PROFILE=legacy`）、`pandas_chunked`（`=0`＋`FFACT_L65_CHUNK_SIZE` 小於選欄數之合法
  正整數）；每份記 `last_post_ic_execution()` 所報實際臂，須等於標示臂，否則 rc≠0。可達條件依契約
  `post_ic_arm_reachability` 逐格判定；不可達之臂不凍結、收據記 `arm_unreachable`（臂名＋條件名＋實際選欄數）。
- G2 格 A 之 L6.5 raw 於 `FFACT_USE_POLARS` 0／1 各一份；G3 格 B 之 raw 與 processed。
- 值指紋一律經 `tests/feature_engineering/numview_helpers.py`（`fingerprints`／`frame_fingerprints`）。

啟動即呼叫 `handoffs/run_receipts/numview_probes/_estimate_gate.require("freeze_baseline", cells)`（在任何生成呼叫之前）；
格 A／B 逐格單行程串行；生成之 run 目錄保留至 Phase 1 結束（供 Task 1.1–1.3 讀取）。
輸出：`tests/_golden/numview/pre_change_fingerprints.json`；收據 `handoffs/run_receipts/<date>-numview-freeze-baseline.json`
（含 HEAD、`started_at`、格清單、每格耗時與峰值記憶體、函式庫版本、`arm_unreachable` 條目）。

本檔為 TODO 階段空殼（Task 0.5 實作）。
"""

from __future__ import annotations

from typing import Optional, Sequence


def main(argv: Optional[Sequence[str]] = None) -> int:
    """凍結主入口；rc 0＝凍結檔與收據寫出、非 0＝估時前置不成立、實際臂≠標示臂或生成失敗。"""
    raise NotImplementedError("NUMVIEW Task 0.5")


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
