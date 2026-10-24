"""NUMVIEW Task 3.4 收據（docs/NUMVIEW_SPEC.md Task 3.4 驗證②⑦）：

1. `handoffs/run_receipts/<date>-numview-icpage-arm-lock.json`：§G G1 每格被移除之臂份（非擇定核心之份，含原 Polars 正式臂）
   對改前擇定核心份之差異欄（逐欄比 `dtype`／`nan`／`values_native`，同 `numview_helpers.BITWISE_COLUMN_KEYS`），與擇定核心份
   中因 v41 一律 float32 而改 dtype 之欄（原生 dtype≠float32）；只報告，數字自凍結檔重算。
2. `handoffs/run_receipts/<date>-numview-pandas-arm-callers.json`：post-IC 舊臂相關函式之全部引用（`git ls-files` 之 `.py`，
   AST 屬性存取／名稱載入，定義本身不計）；零引用者標 `deleted`（須已自碼中刪除），其餘標 `kept`。

純讀檔與 AST，秒級；不生成、不跑轉換。用法：`venv/bin/python handoffs/run_receipts/numview_probes/icpage_arm_lock_receipts.py`。
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:  # 以腳本執行時 repo 根不在 sys.path（同 winsor_key_inventory.py）
    sys.path.insert(0, str(REPO))
RECEIPTS_DIR = REPO / "handoffs" / "run_receipts"
FROZEN = REPO / "tests" / "_golden" / "numview" / "pre_change_fingerprints.json"
BITWISE_COLUMN_KEYS = ("dtype", "nan", "values_native")  # 同 tests/feature_engineering/numview_helpers.py:50
#: post-IC 舊臂（Polars 正式臂、落選核心、依環境分派）相關之函式／類別（Task 3.4「post-IC 舊臂之去留」所列）
FUNCTIONS = (
    "FeaturePreprocessor.transform",
    "FeaturePreprocessor._transform_single",
    "FeaturePreprocessor._transform_single_polars",
    "FeaturePreprocessor._transform_single_optimized_df",
    "FeaturePreprocessor._transform_single_legacy",
    "FeaturePreprocessor._transform_chunked",
    "FeaturePreprocessor._transform_single_passthrough",
    "FeaturePreprocessor._can_use_optimized_dataframe_path",
    "polars_adapter.polars_enabled",
    "ic_first_context.PostICArmUnavailableError",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _criteria_path() -> Path:
    """現行事前登記判準檔（每份 numview 收據須記其 sha256；SPEC Task 0.3 ③）。"""
    from tests.feature_engineering import numview_helpers as nh

    return Path(nh.current_criteria_path())


def _differing(before: Mapping[str, Any], after: Mapping[str, Any]) -> List[str]:
    a, b = before.get("columns", {}), after.get("columns", {})
    return sorted(n for n in set(a) | set(b)
                  if n not in a or n not in b or any(a[n].get(k) != b[n].get(k) for k in BITWISE_COLUMN_KEYS))


def arm_lock_receipt(core: str) -> Dict[str, Any]:
    cells: Dict[str, Any] = {}
    for cell_id, cell in sorted(json.loads(FROZEN.read_text(encoding="utf-8"))["cells"].items()):
        g1 = {k: v for k, v in (cell.get("g1") or {}).items() if not str(k).startswith("_")}
        if not g1:
            continue
        if core not in g1:
            raise SystemExit(f"G1 {cell_id} 無擇定核心 {core} 之凍結份")
        core_fp = g1[core]["fingerprint"]
        cells[cell_id] = {
            "core_columns": len(core_fp["columns"]),
            "float32_cast_columns": sorted(n for n, c in core_fp["columns"].items() if c.get("dtype") != "float32"),
            "removed_arms": {arm: {"differing_columns": _differing(core_fp, copy_["fingerprint"])}
                             for arm, copy_ in sorted(g1.items()) if arm != core},
        }
        for arm, row in cells[cell_id]["removed_arms"].items():
            row["count"] = len(row["differing_columns"])
    return {"core": core, "frozen_sha256": _sha(FROZEN), "cells": cells}


def _git_py_files() -> List[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=True).stdout
    return sorted(p for p in out.decode("utf-8").split("\0") if p.endswith(".py"))


def callers_receipt() -> Dict[str, Any]:
    names = {f.rsplit(".", 1)[-1]: f for f in FUNCTIONS}
    refs: Dict[str, List[str]] = {n: [] for n in names}
    for rel in _git_py_files():
        try:
            tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in names and isinstance(node.ctx, ast.Load):
                refs[node.attr].append(f"{rel}:{node.lineno}")
            elif isinstance(node, ast.Name) and node.id in names and isinstance(node.ctx, ast.Load):
                refs[node.id].append(f"{rel}:{node.lineno}")
    functions = [{"name": full, "status": "kept" if refs[short] else "deleted", "callers": sorted(refs[short])}
                 for short, full in names.items()]
    return {"functions": functions}


def main() -> int:
    from momentum.FeatureEngineering import numeric_view as nv

    core = nv.post_ic_arm("ic_first")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    stamp = datetime.now(timezone.utc)
    common = {"schema_version": 1, "generated_at": stamp.isoformat(), "head": head,
              "command": "venv/bin/python handoffs/run_receipts/numview_probes/icpage_arm_lock_receipts.py",
              "probe_sha256": _sha(Path(__file__)), "criteria_sha256": _sha(_criteria_path())}
    day = stamp.strftime("%Y%m%d")
    lock = RECEIPTS_DIR / f"{day}-numview-icpage-arm-lock.json"
    lock.write_text(json.dumps({**common, **arm_lock_receipt(core)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    callers = RECEIPTS_DIR / f"{day}-numview-pandas-arm-callers.json"
    callers.write_text(json.dumps({**common, **callers_receipt()}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(lock.relative_to(REPO), callers.relative_to(REPO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
