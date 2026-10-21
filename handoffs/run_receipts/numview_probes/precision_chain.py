"""NUMVIEW 精度鏈逐段量測（docs/NUMVIEW_SPEC.md Task 1.2，C6；不重議 2026-09-29 dtype 裁定）。

於格 A／B／C 之生成（共用 Task 0.5 之 run；需變體者另跑，啟動前呼叫 `_estimate_gate.require("precision_chain", cells)`）
以 monkeypatch 擷取檢查點並即時算逐欄統計（不存整表）：S0 float64 鏈（單週期改 `preserve_dtype=True`）、S1 層出口
float32、S2 L6.5 輸出、S3 落盤 dtype 選擇與讀回（含 float16 欄數）、S4 codec（raw BYTE_STREAM_SPLIT 開／關讀回逐位元
相等；processed 有損 int16／uint16 開／關讀回誤差；名稱推斷誤判欄數）、S5 以各檢查點之值跑生產 IC 選欄比較倖存者集合；
另四分岔格（多週期 float64 層間 vs 單週期 float32、memmap 門檻強制兩支、pandas sigma 縮尾回 float64 vs float32、
尾端延伸 N 根之 dtype 只升不降）與 IC 引擎讀入 float16 之 upcast 路徑。
收據 `handoffs/run_receipts/<date>-numview-precision-chain.json`，含 `criteria_sha256`。

本檔為 TODO 階段空殼（Task 1.2 實作）。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

import numpy as np


def checkpoint_stats(values: np.ndarray, reference: np.ndarray) -> Dict[str, Any]:
    """單欄於一檢查點對 S0 float64 鏈之統計：`max_abs`、`max_rel`、`nan_mask_diff`、`float16_ok`（依現行
    `FeatureStorage._select_parquet_storage_array` 判定，只讀）；全 NaN 欄 ⇒ `all_nan=True` 且不計誤差（邊界①）。"""
    raise NotImplementedError("NUMVIEW Task 1.2")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """量測主入口；rc 0＝收據寫出。S4 raw BSS 讀回非逐位元相等 ⇒ 收據標 `lossless_violation`（不改 rc）。"""
    raise NotImplementedError("NUMVIEW Task 1.2")


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
