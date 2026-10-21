"""NUMVIEW post-IC 分支差 HEAD 重量與翻轉（docs/NUMVIEW_SPEC.md Task 1.1，C5）。

母集：`tests/_golden/icpostleak/contract.json` 之分支與七組合，另加探針專用候選臂 `polars_float64`（Polars post-IC
轉換全程 Float64：`pandas_to_polars(use_float64=True)`、rank `map_batches` 之 `return_dtype` Float64、rank UDF 緩衝區
與逐值寫入 float64、`_polars_mask_columns` 中間保留 Float64、gaussian 分支與 `_gaussian_2d` 回傳與最終回傳攜帶
compute dtype，輸出於落盤前轉 float32；探針內 monkeypatch，不改產品碼；收據記中間 dtype 以證全程 Float64）。
輸入：(i) ICPOSTLEAK §G 輸入集建法套用於每個 symbol×tf；(ii) 格 A／B 之 IC-first 實際選欄之 raw 欄（Task 0.5 保留之 run）。
參照＝測試端獨立 numpy float64 實作（rank→gaussian→zscore、窗未滿 NaN），另列 legacy 臂。
輸出（欄名依判準檔）：格級 max_abs／p99_abs／max_rel（近零格另列）／NaN 遮罩差；IC 層逐欄 IC、正負號翻轉數、
Kendall τ-b（未定義 ⇒ material）、`material`；速度：各臂轉換牆鐘三次與中位數。生成型輸入啟動前呼叫
`_estimate_gate.require("postic_branchdiff", cells)`。收據 `handoffs/run_receipts/<date>-numview-postic-branchdiff.json`，
含 `criteria_sha256`。

本檔為 TODO 階段空殼（Task 1.1 實作）。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

import numpy as np

#: 探針專用候選臂名（SPEC Task 1.1；非產品臂，不入 post_ic_arm_values）
CANDIDATE_ARM = "polars_float64"


def cell_diff(reference: np.ndarray, output: np.ndarray) -> Dict[str, Any]:
    """格級差（SPEC Task 1.1；邊界①）：`max_abs`、`p99_abs`、`max_rel`（|ref| < float32 tiny 之近零格不計相對差）、
    `near_zero_cells` 與 `near_zero_max_abs`（近零格另列絕對差）、`nan_mask_diff`（兩者 NaN 遮罩不同之格數）。"""
    raise NotImplementedError("NUMVIEW Task 1.1")


def ic_material(ic_reference: Sequence[float], ic_variant: Sequence[float]) -> Dict[str, Any]:
    """IC 層翻轉（SPEC Task 1.1、設計選擇⑥、R2-D）：`tau_b`（只對兩者 IC 皆有限之欄對計算；全 ties、全 NaN、有效對數
    < 2 ⇒ NaN）、`sign_flips`、`material`（任一正負號翻轉、τ-b < 1、或 τ-b 非有限 ⇒ True）、`reason`（判定原因）。
    非有限統計量一律 `material=True`（fail-closed），不得以 `NaN < 1 == False` 判未翻轉。"""
    raise NotImplementedError("NUMVIEW Task 1.1")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """量測主入口；rc 0＝收據寫出；重現檢查（BTCUSDT 1h 輸入 (i) 之 legacy 對 optimized 七組合皆 0 差）不符 ⇒ rc≠0。"""
    raise NotImplementedError("NUMVIEW Task 1.1")


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
