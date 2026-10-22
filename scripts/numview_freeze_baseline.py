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
格 A／B 逐格單行程串行；生成之 run 目錄保留至 Phase 1 結束（供 Task 1.1–1.3 讀取）。FeatureFactory 之連續性設定依判準檔
`cell_rules.continuity`（同估時器 `estimate.continuity_plan`／`window_gap_violations`）：來源全序列無缺口 ⇒ 生產設定
`validate_continuity=True`；有缺口（長歷史檔 12h 於生成窗外）⇒ False＋生成窗內零缺口判定，窗內缺口 ⇒ 該格 failed（data_gap）。Task 1.3 之 L2 兩臂 spy 掛於
凍結之生成（格 A_BTCUSDT_1h 兩個 FFACT_USE_POLARS 生成、格 B／C／A_BTCUSDT_12h 之預設生成），l2_arm_matrix 讀其紀錄、
不另生成（判準檔 run_coverage.l2_arm_matrix）。
輸出：`tests/_golden/numview/pre_change_fingerprints.json`；收據 `handoffs/run_receipts/<date>-numview-freeze-baseline.json`
（含 HEAD、`started_at`、格清單、每格耗時與峰值記憶體、函式庫版本、`arm_unreachable` 條目）。

本檔為 TODO 階段空殼（Task 0.5 實作）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

REPO: Path = Path(__file__).resolve().parents[1]
#: 估時收據目錄（呼叫時讀模組屬性，傳給 `_estimate_gate.require(receipts_dir=)`；測試以 monkeypatch 改指）
RECEIPTS_DIR: Path = REPO / "handoffs" / "run_receipts"


def reachable_arms(selected_count: int) -> List[str]:
    """依契約 `post_ic_arm_reachability.<臂>.min_selected_columns` 回傳選欄數（ratio-unsafe 剔除後）為
    `selected_count` 時可達之 post-IC 臂（契約 `post_ic_arm_values` 之順序）；SPEC Task 0.5、R3-D。"""
    raise NotImplementedError("NUMVIEW Task 0.5")


def generate_cell(root: Path, cell: Mapping[str, Any], *, run_kind: str,
                  env: Optional[Mapping[str, str]] = None) -> Any:
    """格之真實生成（SPEC Task 0.5、R15-A）：`cell`＝全票唯一格描述子 `{id, kind, symbol, timeframes}`；與凍結同一生成程序、
    同行程、寫入隔離於 `root`、raw 與 processed 皆保留；`env` 覆寫生成環境；回 `preprov_helpers.RunHandle`。
    🔴 首個陳述式級呼叫須為 `_estimate_gate.require(run_kind, [cell["id"]], receipts_dir=RECEIPTS_DIR)`，先於任何生成呼叫
    （`run_kind`＝呼叫端所屬之估時跑別：凍結為 `freeze_baseline`，Phase 2–4 驗收重產為批次生成跑別 `regen_b3`／`regen_b4`／
    `regen_b5`〔經 `numview_helpers.regen_batch_kind`〕）；估時收據未涵蓋該格 ⇒ `EstimateGateError` 原樣上拋、不生成。
    批次共用生成（判準檔 `cell_rules.batch_cache`）：`root` 恰為 `numview_helpers.regen_batch_root()` 時，run 落於
    `root / numview_helpers.regen_cache_key(cell, env)`（格描述子、env、碼態 sha256），已存在完整 run 即於前置閘後直接回傳、
    不重生；其他 `root`（凍結、Phase 1、mutant 之暫存根）不讀寫該快取。須觀測生成內中間值之檢查（Task 1.3 L2 spy、
    Task 3.1–3.3 核心 spy）之觀測器掛於該唯一生成，觀測紀錄與 run 同存，快取命中時由紀錄回填（不得因命中而重生）。"""
    raise NotImplementedError("NUMVIEW Task 0.5")


def freeze_cell(cell: Mapping[str, Any], work_root: Path, *, arms: Sequence[str], run_kind: str) -> Dict[str, Any]:
    """以現行碼依凍結檔格紀錄重生該格，回與凍結檔同形之 `{"g1": {臂: {env, actual_arm, fingerprint}}, "g2": {...},
    "g3": {...}}`（G1 只跑 `arms`）；生成一律經 `generate_cell(..., run_kind=run_kind)`（故同受估時前置閘；SPEC §G、R15-A）。"""
    raise NotImplementedError("NUMVIEW Task 0.5")


def ic_page_output(handle: Any, work: Path) -> Tuple[Any, Dict[str, Any]]:
    """以 `ApplyTransformsRequest` 預設請求對該格 IC-first 選欄跑 IC 頁第三步（`_apply_transforms_sync`，cwd 隔離於
    `work`），回（h5 讀回之 DataFrame, 回應 dict）；不生成特徵（只讀 `handle` 之 run）。`handle` 屬批次共用快取時
    （判準檔 `cell_rules.batch_cache`），各臂輸出（含臂 spy 紀錄）每 (格描述子, env, 碼態, 臂環境) 只算一次、存於該生成之快取
    目錄，t21／t22／§G 等檢查讀取，不各自重算。"""
    raise NotImplementedError("NUMVIEW Task 0.5")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """凍結主入口；rc 0＝凍結檔與收據寫出、非 0＝實際臂≠標示臂或生成失敗；估時前置不成立 ⇒ `EstimateGateError` 原樣上拋。
    啟動即 `_estimate_gate.require("freeze_baseline", cells, receipts_dir=RECEIPTS_DIR)`，生成一律經 `generate_cell`。"""
    raise NotImplementedError("NUMVIEW Task 0.5")


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
