#!/usr/bin/env python3
"""FFPROD Task 0.2：改前基準凍結（SPEC `docs/FFPROD_SPEC.md` §G、Task 0.2）。

格＝覆蓋獨有分支之最少集合（A 單週期 1h、A 12h、B 多週期 1h＋4h、C 全特徵 1h，另依 Task 0.1 盤點收據補 sigma 縮尾開、
fracdiff／ADF 開之單週期格；L2 三臂各一格，以 A 單週期 1h 加環境覆寫）。值指紋沿
`tests/feature_engineering/numview_helpers.py` 之 `fingerprints`（逐欄 dtype、NaN 遮罩、`values_native`、欄集合與欄序雜湊）。
生成之隔離環境與「8 GB 不可跑 ⇒ blocked-by 硬體」處置可沿用 `scripts/numview_freeze_baseline.py`。

本檔為 TODO 階段之空殼：函式體一律 `raise NotImplementedError("<SPEC Task ID>")`。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Sequence, Set

REPO = Path(__file__).resolve().parents[1]
GOLDEN_PATH = REPO / "tests" / "_golden" / "ffprod" / "pre_change_fingerprints.json"
DECISIONS_PATH = REPO / "tests" / "_golden" / "ffprod" / "decisions.json"
RECEIPTS_DIR = REPO / "handoffs" / "run_receipts"
INVENTORY_GLOB = "*-ffprod-inventory.json"

#: L2 三條生產臂（`FeatureFactory._budget_check_l2` 之回傳值）與各格之環境覆寫（SPEC Task 0.2）。
L2_ARM_ENV: Dict[str, Dict[str, str]] = {
    "L2.polars": {},
    "L2.pandas_serial": {"FFACT_USE_POLARS": "0", "FFACT_L2_CATEGORY_WORKERS": "1"},
    "L2.pandas_parallel": {"FFACT_USE_POLARS": "0", "FFACT_L2_CATEGORY_WORKERS": "2"},
}

#: §G 逐位元比對鍵（同 `numview_helpers.BITWISE_COLUMN_KEYS`）。
BITWISE_KEYS = ("dtype", "nan", "values_native")

BLOCKED_BY_HARDWARE = "hardware"


class ArmMismatch(RuntimeError):
    """L2 格以 spy 觀測之 `_budget_check_l2` 回傳臂不等於該格宣告之臂 ⇒ 凍結拒寫該格（SPEC Task 0.2）。"""


def cells() -> List[Dict[str, Any]]:
    """回傳凍結格清單（每格含 `id`、`kind`、`symbol`、`timeframes`、`env`、`covers`〔該格獨有覆蓋之路徑標記，全部格之
    聯集須含 `test_ffprod_gate.REQUIRED_COVERAGE`〕；L2 格另含 `declared_arm`〔亦列入 `covers`，`env` 含 `L2_ARM_ENV` 該臂〕）。
    凍結 CLI 與重生對照皆用本清單。"""
    raise NotImplementedError("FFPROD Task 0.2")


def freeze_cells(cell_list: Sequence[Mapping[str, Any]], out_path: Path, *,
                 generate: Callable[[Mapping[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    """逐格呼叫 `generate(cell)`（回傳 {"fingerprints": ..., "identity": ..., "observed_arm": 可缺}），每完成一格即原子寫入
    `out_path`。邊界①：中途例外 ⇒ 已完成格保留、未完成格不寫入、例外上拋。邊界②：
    `GenerationMemoryBudgetExceeded` ⇒ 該格記 {"status": "blocked", "blocked_by": "hardware"} 並續下一格。
    L2 格之 `observed_arm` ≠ `declared_arm` ⇒ 拋 `ArmMismatch`、該格不寫入。回傳寫入之全部格。"""
    raise NotImplementedError("FFPROD Task 0.2")


def compare(frozen: Mapping[str, Any], actual: Mapping[str, Any], changed_targets: Set[str]) -> List[str]:
    """§G 對照：回傳不符描述清單（空＝通過）。欄集合或欄序不同、非 `changed_targets` 之欄任一 `BITWISE_KEYS` 不等、
    `changed_targets` 之欄實際未改（少一欄）皆為不符。`frozen`／`actual` 為 `fingerprints` 之輸出。"""
    raise NotImplementedError("FFPROD Task 0.2")


def regenerate(cell: Mapping[str, Any]) -> Dict[str, Any]:
    """以現行 HEAD 重生成一格並回傳其值指紋（同 `freeze_cells` 之 `generate` 回傳格式）。"""
    raise NotImplementedError("FFPROD Task 0.2")


def main(argv: Sequence[str] | None = None) -> int:
    """CLI：`--estimate` 只估時（>30 分先白話告知使用者）；無旗標 ⇒ 凍結全部格至 `GOLDEN_PATH`。"""
    raise NotImplementedError("FFPROD Task 0.2")


if __name__ == "__main__":
    raise SystemExit(main())
