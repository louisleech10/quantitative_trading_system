#!/usr/bin/env python3
"""FFPROD Task 0.2 一次性：全特徵格 C 之值指紋改群組粒度（不重生成）。

首次凍結（scripts/ffprod_freeze_baseline.py，C 格逐欄指紋）使基準檔約 100 MB、逾版控單檔上限；凍結腳本隨即改為 C 格群組粒度
（`cell_fingerprints`）。本工具以同一 `cell_fingerprints` 對該次凍結之 C 格 run 目錄（生成產物仍在，身分不變）重算指紋並寫回
基準檔，其餘格不動。於凍結 HEAD 之 §G 重生對照（test_ffprod_gate.py::test_gate_regenerated_cells_match_frozen）以重生之 C 格
群組指紋對照本值，即驗本工具之寫回。

用法：venv/bin/python scripts/ffprod_refingerprint_c.py <C 格 run 目錄>
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def main(argv: list) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    run_dir = Path(argv[0])
    spec = importlib.util.spec_from_file_location("ffprod_freeze_for_refp", REPO / "scripts" / "ffprod_freeze_baseline.py")
    assert spec is not None and spec.loader is not None
    fb = importlib.util.module_from_spec(spec)
    sys.modules["ffprod_freeze_for_refp"] = fb
    spec.loader.exec_module(fb)
    golden = json.loads(fb.GOLDEN_PATH.read_text(encoding="utf-8"))
    cell = next(c for c in golden["cell_list"] if c["kind"] == "C")
    if not (run_dir / "feature_manifest.json").is_file():
        raise SystemExit(f"非 run 目錄：{run_dir}")
    golden["cells"][cell["id"]]["fingerprints"] = fb.cell_fingerprints(cell, run_dir)
    golden["cells"][cell["id"]]["refingerprinted_from"] = str(run_dir)
    fb._write_atomic(fb.GOLDEN_PATH, golden)
    print(f"{cell['id']}：群組粒度 {len(golden['cells'][cell['id']]['fingerprints']['columns'])} 群組；"
          f"寫回 {fb.GOLDEN_PATH}（{fb.GOLDEN_PATH.stat().st_size} bytes）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
