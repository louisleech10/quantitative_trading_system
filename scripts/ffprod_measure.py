#!/usr/bin/env python3
"""FFPROD Task 2.1：改值候選量測（SPEC `docs/FFPROD_SPEC.md` Task 2.1）。

候選＝Task 0.1 盤點收據之「量測」項。候選以環境或探針切換、不改正式碼；每個選項各一次獨立完整生成（各自 run 目錄），
改後值指紋＝該次落盤輸出之 §G 指紋。L2 選項探針把三取值點（`compute_all_polars` 回傳之公開結果、逐類 `category_frame`、
L5／L6 實收 L2 欄）全部路由至該選項來源並以 `frame_fingerprints` 自證三者相等；改前（未掛選項探針）三者兩兩比照實入收據。
收據 `handoffs/run_receipts/<日期>-ffprod-candidates.json`。

本檔為 TODO 階段之空殼：函式體一律 `raise NotImplementedError("<SPEC Task ID>")`。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
RECEIPT_NAME = "{date}-ffprod-candidates.json"

#: L2 候選之選項值域（同決定紀錄 `canonical_source`）。
L2_OPTIONS = ("polars_public", "pandas_category")


class SourceRoutingError(RuntimeError):
    """L2 選項探針三取值點之 `frame_fingerprints` 不相等或不等於所指來源 ⇒ 該選項收據拒寫（SPEC Task 2.1 改法）。"""


def candidates() -> List[Dict[str, Any]]:
    """自 Task 0.1 盤點收據取「量測」項（每項含 `candidate_id`、`options`、探針路徑）。"""
    raise NotImplementedError("FFPROD Task 2.1")


def measure_option(candidate: Mapping[str, Any], option: str, work: Path) -> Dict[str, Any]:
    """於 `work`（每選項獨立）完整生成一次，回傳 `option`、探針路徑、run 目錄、生成身分、改前／改後逐欄值指紋、
    改值欄集合、值差摘要、IC 正負號翻轉與選欄進出、耗時、峰值 RSS、輸出檔位元組。"""
    raise NotImplementedError("FFPROD Task 2.1")


def l2_pairwise_baseline(work: Path) -> Dict[str, Any]:
    """改前（未掛選項探針）現行碼之 L2 三取值點兩兩值差與各自 `frame_fingerprints`（照實記錄、不拒寫）。"""
    raise NotImplementedError("FFPROD Task 2.1")


def main(argv: Sequence[str] | None = None) -> int:
    """CLI：量全部候選並寫收據；`--estimate` 只估時。"""
    raise NotImplementedError("FFPROD Task 2.1")


if __name__ == "__main__":
    raise SystemExit(main())
