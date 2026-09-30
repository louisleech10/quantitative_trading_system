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
from typing import Any, Dict, Optional

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


DEAD_DROPS_PATH = REPO / "tests" / "_golden" / "ffstat" / "baseline_dead_drops.json"


def leading_caused(rec: Dict[str, Any]) -> bool:
    """SPEC v49：改前 L3 剔除是否因開頭過長（全無有限值，或非常數且開頭非有限值 > 0.9 或其後不足 30 列）；含 inf 者否。"""
    if rec["has_inf"]:
        return False
    rows, lead = int(rec["rows"]), int(rec["leading_nan"])
    if lead >= rows:
        return True
    if rec.get("low_cardinality_skip"):
        return False  # 改前低基數閘所剔（統計取自輸入欄）：只有輸入全無有限值時屬開頭過長
    # 改前過濾器為各條件之 OR：開頭段本身即足以判死（其後樣本過少時之常數判定不另計）
    return lead / rows > 0.9 or rows - lead < 30


def classify_added(rec: Optional[Dict[str, Any]], new_values: Any, restored_by_start: bool) -> Optional[str]:
    """新增欄之原因（SPEC v50，審查 r33 codex P1-01 因果配對）：
    - 凍結檔無此欄或改前剔除非開頭過長（`leading_caused` 假）⇒ None（無合法原因、blocked）；
    - `warmup_restored` 須同時成立：改後公開輸出於改前開頭非有限值段（前 `leading_nan` 列）內已有有限值（證明新增
      之有效值正是預熱填回之開頭段），且改後 `stable_start` ≤ 起始日（`restored_by_start`）；
    - 改前因開頭過長被剔、而改後未於起始日前穩定 ⇒ `nan_rate_rule`（改由新分母保留）；
    - 改前因開頭過長被剔、改後 stable_start ≤ 起始日但開頭段內仍無有限值 ⇒ None（因果不成立，不得標 restored）。"""
    import numpy as np

    if rec is None or not leading_caused(rec):
        return None
    if not restored_by_start:
        return "nan_rate_rule"
    values = np.asarray(new_values, dtype=np.float64)
    lead = min(int(rec["leading_nan"]), len(values))
    return "warmup_restored" if bool(np.isfinite(values[:lead]).any()) else None


def column_delta() -> Dict[str, Any]:
    from momentum.FeatureEngineering.preprocessing import stable_mask as sm
    from tests.feature_engineering import ffstat_helpers as h

    import pandas as pd

    baseline = json.loads(h.BASELINE_PATH.read_text(encoding="utf-8"))
    before = sorted(baseline["base"])
    import pytest

    with tempfile.TemporaryDirectory(prefix="ffstat_delta_") as tmp:
        # 同測試之隔離（d* 快取、cwd、系統暫存皆導向 tmp；不寫專案 data_cache）
        mp = pytest.MonkeyPatch()
        try:
            h.prepare_stat_env(mp, Path(tmp))
            root, factory, result = h.run_stat(Path(tmp), h.stat_payload())
        finally:
            mp.undo()  # 還原 cwd 等；產物仍在 tmp 內，下方讀取以絕對路徑進行
        after = sorted(h.base_fingerprints(root))
        dropped = dict(result.metadata.get("column_set_reasons", {}))
        stable_start = dict(result.metadata.get("stable_start", {}))
        added_values = h.base_column_values(root, set(after) - set(before))
    # 移除欄：本次 L3／L7 死欄過濾之原因（只收封閉集合內者；其餘如 constant／has_inf 留空 ⇒ delta 拒收）
    reasons: Dict[str, str] = {}
    for column in set(before) - set(after):
        if dropped.get(column) in sm.DELTA_REASONS:
            reasons[column] = dropped[column]
    # 新增欄（SPEC v50）：查改前原始碼同設定同窗之 L3 剔除紀錄凍結檔，以 classify_added 做因果配對判定；
    # 凍結檔無此欄、改前理由非開頭過長或因果不成立 ⇒ 無原因（blocked）
    from momentum.FeatureEngineering.preprocessing.calibration import tagged_column_name

    # 改前 L3 以未標記週期之欄名運算（close_trend_…），公開欄名已標記（close_1h_trend_…）⇒ 同一規則正規化
    frozen = json.loads(DEAD_DROPS_PATH.read_text(encoding="utf-8"))
    old = {tagged_column_name(c, frozen["timeframe"]): rec for c, rec in frozen["l3_dead_drops"].items()}
    start = pd.Timestamp(h.WINDOW[0], tz="UTC")
    for column in set(after) - set(before):
        ts = stable_start.get(column)
        reason = classify_added(old.get(column), added_values[column], ts is not None and pd.Timestamp(ts) <= start)
        if reason is not None:
            reasons[column] = reason
    try:
        delta = sm.column_set_delta(before, after, reasons)
    except sm.DeltaReasonError as exc:
        # SPEC Task 2.3 ⑦（v36）：原因不在封閉集合 ⇒ 拒收並出 blocked 收據（列每個無合法原因之差異欄與其原始原因）
        unreasoned = [{"column": c, "side": "removed" if c in before else "added", "raw_reason": dropped.get(c)}
                      for c in sorted(set(before) ^ set(after)) if c not in reasons]
        return {"schema_version": 1, "status": "blocked", "error": str(exc),
                "command": "venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py column-delta",
                "exit_code": 1, "added": len(set(after) - set(before)), "removed": len(set(before) - set(after)),
                "unclassified": unreasoned}
    return {"schema_version": 1,
            "command": "venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py column-delta",
            "exit_code": 0, "before_sha256": sm.column_set_sha256(before), "after_sha256": sm.column_set_sha256(after),
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
