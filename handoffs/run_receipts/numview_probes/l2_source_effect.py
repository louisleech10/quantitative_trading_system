"""NUMVIEW Task 3.3 D-L2 mutation 可觀測性實測：L5／L6 實際所吃之 L2（Polars 回傳表）與以公開落盤 L2（逐類別 compute_category
經持久化轉型）重算之 L5／L6 輸出是否逐位元相同（記憶體內 float64；`tests/feature_engineering/test_numview_core.py` 生成觀測器之
`L2Use.recomputed_equal`）。

資料＝b4 碼態之批次共用快取中，核心測試生成時與 run 同存之觀測紀錄（`numview_core_observations.pkl`，A 四格＋B 格；判準
batch_cache）。只讀觀測、不生成。收據 `handoffs/run_receipts/<date>-numview-l2-source-effect.json`：逐格逐次（實例、週期、校準、
層）之 L2 欄數、輸出欄數、公開缺欄／多欄、`recomputed_equal`；彙總每格 L5／L6 吃 L2 之次數與不等次數。
用法：`venv/bin/python handoffs/run_receipts/numview_probes/l2_source_effect.py`（秒級）。
"""

from __future__ import annotations

import hashlib
import json
import pickle
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:  # 以腳本執行時 repo 根不在 sys.path（同 winsor_key_inventory.py）
    sys.path.insert(0, str(REPO))
RECEIPTS_DIR = REPO / "handoffs" / "run_receipts"


def main() -> int:
    import importlib

    from tests.feature_engineering import numview_helpers as nh

    core = importlib.import_module("tests.feature_engineering.test_numview_core")
    sys.modules.setdefault("test_numview_core", core)
    cells: Dict[str, Any] = {}
    for kind in ("A", "B"):
        for cell in core._cells(kind):
            descriptor = {**dict(cell), "kind": kind}
            path = nh.regen_batch_root() / nh.regen_cache_key(descriptor, None) / core.CORE_OBSERVATIONS
            if not path.is_file():
                raise SystemExit(f"缺觀測紀錄（先跑核心測試於現行碼態生成）：{descriptor['id']} {path}")
            run = pickle.loads(path.read_bytes())
            uses: List[Dict[str, Any]] = [
                {"instance": u.instance, "tf": u.tf, "calibration": u.calibration, "layer": u.layer,
                 "l2_columns": u.l2_columns, "output_columns": u.output_columns,
                 "missing_public": len(u.missing_public), "extra_public": len(u.extra_public),
                 "recomputed_equal": bool(u.recomputed_equal)} for u in run.l2_use]
            eating = [u for u in uses if u["l2_columns"]]
            cells[str(descriptor["id"])] = {"l5_l6_calls_eating_l2": len(eating),
                                           "unequal_calls": sum(1 for u in eating if not u["recomputed_equal"]),
                                           "uses": uses}
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    stamp = datetime.now(timezone.utc)
    out = {"schema_version": 1, "generated_at": stamp.isoformat(), "head": head,
           "command": "venv/bin/python handoffs/run_receipts/numview_probes/l2_source_effect.py",
           "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "criteria_sha256": hashlib.sha256(Path(nh.current_criteria_path()).read_bytes()).hexdigest(),
           "code_state_sha256": nh.code_state_sha256(), "cells": cells}
    path = RECEIPTS_DIR / f"{stamp.strftime('%Y%m%d')}-numview-l2-source-effect.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path.relative_to(REPO), json.dumps({k: (v["l5_l6_calls_eating_l2"], v["unequal_calls"]) for k, v in cells.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
