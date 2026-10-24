"""NUMVIEW post-IC 單一 pandas 核心擇一（docs/NUMVIEW_SPEC.md Task 1.6，v40）。

使用者 2026-10-24「IC頁與IC-first都改pandas」與常設「小／大資料非線性，不得推測」：於兩個 pandas 計算核心
（`pandas_optimized`／`pandas_legacy`；`feature_preprocessor.py:3379-3380`）以實際規模實測擇一。輸入（不另生成特徵）：
(a) `A:BTCUSDT:1h` 凍結 run 之 raw 與其 IC-first 選欄、全窗列；(b) 全特徵 `C:BTCUSDT:1h` 凍結 run 之 raw，選欄以生產
IC-first 同程序重算。入口＝生產 `transform_selected`（`FFACT_USE_POLARS=0`、`FFACT_L65_OPTIMIZATION_PROFILE`＝optimized／
legacy）。單元＝核心 × {分塊：(a)、(b)；直接（`FFACT_L65_CHUNK_SIZE=0`）：(a)}，每單元子行程經卡死監看；同路徑兩核心輸出
逐位元互比；擇一規則見 SPEC Task 1.6。收據 `handoffs/run_receipts/<date>-numview-postic-core-select.json`，含
`criteria_sha256`。
"""

from __future__ import annotations

from typing import Optional, Sequence


def main(argv: Optional[Sequence[str]] = None) -> int:
    """量測主入口；rc 0＝收據寫出且自我檢查一致（結果為 `choice` 或 `no_choice` 皆合格，見 SPEC Task 1.6 擇一規則）；
    rc≠0＝探針自身失敗或收據自相矛盾。"""
    raise NotImplementedError("NUMVIEW Task 1.6")


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
