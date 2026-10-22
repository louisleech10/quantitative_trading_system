"""NUMVIEW L2 兩臂矩陣（docs/NUMVIEW_SPEC.md Task 1.3，C7）。

承 `handoffs/run_receipts/icfirstalign_probes/l2_arm_pipeline_probe.py`，參數化至格 A＋格 B 全部格：每格記 L1 輸入
dtype、兩臂（L5／L6 所吃之 `compute_all_polars` 表 vs 公開落盤之 `compute_category`）之欄集合、NaN 遮罩、float32
有限值差格數（`f32diff`）、max_abs、max_rel，及 `FFACT_USE_POLARS=0` 時 pandas 臂之同表。某類別 `compute_category`
拋錯 ⇒ 記錯誤，不以缺欄計 0 差（邊界②）。啟動前呼叫 `_estimate_gate.require("l2_arm_matrix", cells)`。
格與生成依判準檔 `run_coverage.l2_arm_matrix`（路徑覆蓋）：凍結已生成之 (格, 環境) 一律讀凍結生成所掛 L2 spy 之紀錄、
不重生；只有凍結無該環境之生成（格 B、格 C 之 `FFACT_USE_POLARS=0`）才生成。
BTCUSDT 12h 格須重現 freeze-baselines 收據之 f32diff=0（不符 ⇒ rc≠0，停下歸因）。
收據 `handoffs/run_receipts/<date>-numview-l2-arm-matrix.json`，含 `criteria_sha256`。

本檔為 TODO 階段空殼（Task 1.3 實作）。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

import pandas as pd


def compare_l2_arms(returned: pd.DataFrame, category: pd.DataFrame) -> Dict[str, Any]:
    """兩臂比較：`common_cols`、`only_returned`、`only_category`、`nan_mask_diff`、`f64diff`、`f32diff`、`max_abs`、
    `max_rel`；只比兩者皆有限之格之值差，NaN 遮罩差另列。"""
    raise NotImplementedError("NUMVIEW Task 1.3")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """量測主入口；rc 0＝收據寫出；BTCUSDT 12h 重現檢查不符 ⇒ rc≠0。"""
    raise NotImplementedError("NUMVIEW Task 1.3")


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
