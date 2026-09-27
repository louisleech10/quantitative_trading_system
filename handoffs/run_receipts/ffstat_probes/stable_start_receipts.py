"""FF-STAT Task 2.3／§G⑦ 收據產生器（實作後執行；每種收據只由本腳本產生）。

子命令：
  inventory      NaN 傳遞盤點：AST 列舉 L2–L6.5 與多週期對齊之步驟函式（與 test_ffstat_stable_start 之列舉同一實作），
                 併入 tests/_golden/ffstat/nan_propagation_classes.json 之逐步驟分類與碼證；有未分類者 rc=1。
  output-points  12h 逐 L1 輸出點：真實 BTC 12h、預設全設定，逐欄驗首個有效值＝origin＋K；列已驗與未驗。
  dual-start     §G⑦：1h、4h（kline_cache）與 12h（長歷史快取）以 ffstat_helpers.dual_start_report 實跑並記數字。
  column-delta   欄集合差異：凍結基準之欄集合對本次 run 之欄集合，逐欄原因取自死欄純函式判定；寫 delta 與 sha256。
用法：venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py <子命令> --out <收據路徑>
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
CLASSES = REPO / "tests/_golden/ffstat/nan_propagation_classes.json"


def inventory() -> Dict[str, Any]:
    from tests.feature_engineering.test_ffstat_stable_start import _ast_step_functions

    classes = json.loads(CLASSES.read_text(encoding="utf-8"))["steps"]
    steps, unclassified = [], []
    for name in sorted(_ast_step_functions()):
        row = classes.get(name)
        if row is None:
            unclassified.append(name)
            continue
        steps.append({"function": name, **row})
    return {"schema_version": 1, "command": "venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py inventory",
            "exit_code": 1 if unclassified else 0, "steps": steps, "unclassified": unclassified}


def output_points() -> Dict[str, Any]:
    import numpy as np

    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.config_manager import ConfigManager
    from momentum.FeatureEngineering.preprocessing import stable_mask as sm

    specs: Dict[str, Any] = {}
    original = sm.instance_k

    def spy(spec, table, upstream_k=None):
        k = original(spec, table, upstream_k)
        specs[spec.column] = k
        return k

    sm.instance_k = spy
    try:
        factory = create_feature_factory(cache_dir=str(REPO / "data_cache/feature_klines_longhist"), validate_continuity=False)
        config = ConfigManager().get_merged_config()
        raw = factory._layer0_data_ingestion("BTCUSDT", "12h", config)
        layer1 = factory._layer1_atomic_indicators(raw, config).data
    finally:
        sm.instance_k = original
    verified, unverified = [], []
    for column in layer1.columns:
        values = layer1[column].to_numpy(dtype=np.float64)
        k = specs.get(column)
        first = sm.first_finite_index(values)
        if k is None or first is None or first < k:
            unverified.append(column)
        else:
            verified.append(column)
    return {"timeframe": "12h", "verified": verified, "unverified": unverified}


def dual_start() -> Dict[str, Any]:
    from tests.feature_engineering import ffstat_helpers as h

    out = {}
    for tf, src in h.CONTRACT["dual_start"]["timeframes"].items():
        with tempfile.TemporaryDirectory(prefix="ffstat_dual_") as tmp:
            report = h.dual_start_report(Path(tmp), tf, {}, str(REPO / src))
        report["max_error"] = dict(sorted(report["max_error"].items(), key=lambda kv: -kv[1])[:20])
        out[tf] = report
    return out


def column_delta() -> Dict[str, Any]:
    from momentum.FeatureEngineering.preprocessing import stable_mask as sm
    from tests.feature_engineering import ffstat_helpers as h

    baseline = json.loads(h.BASELINE_PATH.read_text(encoding="utf-8"))
    before = sorted(baseline["base"])
    with tempfile.TemporaryDirectory(prefix="ffstat_delta_") as tmp:
        root, factory, result = h.run_stat(Path(tmp), h.stat_payload())
        after = sorted(h.base_fingerprints(root))
        reasons = dict(result.metadata.get("column_set_reasons", {}))
    delta = sm.column_set_delta(before, after, reasons)
    return {"before_sha256": sm.column_set_sha256(before), "after_sha256": sm.column_set_sha256(after),
            "delta": delta, "delta_sha256": sm.delta_sha256(delta)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["inventory", "output-points", "dual-start", "column-delta"])
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    doc = {"inventory": inventory, "output-points": output_points, "dual-start": dual_start,
           "column-delta": column_delta}[args.command]()
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    bad = doc.get("unclassified") or doc.get("unverified")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
