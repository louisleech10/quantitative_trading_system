"""NUMVIEW 量測格清單與估時（docs/NUMVIEW_SPEC.md Task 0.4，R2-B；先於一切重型跑）。

自 `data_cache/feature_klines/kline_cache.h5` 列舉 symbol×tf（不寫死清單）：格 A＝每個 symbol×tf 單週期短窗、
格 B＝每個 symbol 之「最細週期主＋其餘週期訓練」多週期格、格 C＝生產預設全特徵（`FactoryConfig()`）於每個 symbol×tf。
各類先實測一格之耗時與峰值記憶體（格 C 12h 可引 `handoffs/run_receipts/20261020-preprov-fullrun-size.md`；4h／1h
各實測一格），外推總量，逐跑別（`run_kind`）列格清單、單格秒數、外推總秒數與不降驗證之省法；
單格實測自行生成後刪除。磁碟 < 30 GB ⇒ rc=1 並列所需空間（邊界②）；格 C 單格實測逾機器上限 ⇒ 該 symbol×tf 之
格 C 全列 blocked-by 硬體、不再逐格試（邊界①）。`reported_at` 由主委白話報告後寫入，本腳本不寫。

收據：`handoffs/run_receipts/<date>-numview-estimate.json`。本檔為 TODO 階段空殼（Task 0.4 實作）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

#: 估時收據須涵蓋之跑別（Task 0.5 之 G1–G3 與 Phase 1 全部生成；`_estimate_gate.require` 之 run_kind 值）
RUN_KINDS = ("freeze_baseline", "postic_branchdiff", "precision_chain", "l2_arm_matrix")
#: 磁碟下限（GB；SPEC §C 重型跑紀律）
MIN_FREE_DISK_GB = 30


def enumerate_cells(kline_path: Path) -> Dict[str, List[Dict[str, Any]]]:
    """自 kline 檔列舉格 A／B／C（鍵 `A`／`B`／`C`；每格含 symbol、tf 或多週期組合）；不寫死 symbol 與週期。"""
    raise NotImplementedError("NUMVIEW Task 0.4")


def disk_free_gb(path: Path) -> float:
    """`path` 所在檔案系統之可用空間（GB）。"""
    raise NotImplementedError("NUMVIEW Task 0.4")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """估時主入口；rc 0＝收據寫出、1＝磁碟不足（列所需空間）或實測失敗、2＝用法錯。"""
    raise NotImplementedError("NUMVIEW Task 0.4")


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
