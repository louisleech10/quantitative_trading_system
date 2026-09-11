"""SPLITUNIFY SPEC C-9 驗收：統一切分**改前 vs 改後**之逐項差異報告（原殘留 R-2，已判不合格）。

C-9 原文：「驗收**必須**對改前後做逐 event ID 集合、逐列 train／test fingerprint、
報告 numeric keys 與 capability reason 的 exact／tolerance diff；**不得**以『型別不變』宣稱數值不變」。

🔴 為何這支原本被我掛成殘留是錯的：C-9 是**驗收條件**不是可選項，而阻塞它的
G-3a 遷移報告在 B2c 就跑出來了（`only_in_new_test=['te0']`）。阻塞消失我卻沒回來關它。

兩條路各自比：
  ① **事件掃描端**（`tables.py`／`baseline.py`／`pattern_bridge.py` 之消費路徑）
     改前＝`pipeline.run()` 之 `split_events` 切分；改後＝生產路徑 `run_event_study_only()`
     （SPLITUNIFY Task 3.3：事件掃描端拿不到 canonical universe ⇒ 不切分）。
  ② **IC 端**（`ic_filter_orchestrator._build_holdout_split_plan`）
     改前＝`holdout_split_point` ＋ `holdout_test_row_index` 就地組；改後＝`holdout_boundary`。

用法：`venv/bin/python scripts/splitunify_c9_diff.py [--out <receipt.json>]`（rc=0；差異寫進 receipt）。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

BASE = 1704067200000
H12 = 43200000
TF = "12h"
SYM = "ETHUSDT"
#: 刻意橫跨整段真實 kline 的 12 筆事件，讓切分邊界落在事件之間（否則兩種切法沒有可比之處）
EVENT_BARS = (60, 180, 300, 420, 540, 660, 780, 900, 1020, 1140, 1260, 1380)
HORIZONS = (1, 2, 4)


def _numeric_leaves(node: Any, prefix: str = "") -> Dict[str, Any]:
    """所有數值／字串葉（dotted path → 值），供 exact／tolerance diff。"""
    out: Dict[str, Any] = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(_numeric_leaves(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(node, (list, tuple)):
        for i, v in enumerate(node):
            out.update(_numeric_leaves(v, f"{prefix}[{i}]"))
    elif isinstance(node, (bool, int, float, str)) or node is None:
        out[prefix] = node
    elif isinstance(node, (np.integer, np.floating)):
        out[prefix] = node.item()
    return out


def _diff(old: Dict[str, Any], new: Dict[str, Any], *, rtol: float = 1e-12) -> Dict[str, Any]:
    only_old = sorted(set(old) - set(new))
    only_new = sorted(set(new) - set(old))
    changed = {}
    for k in sorted(set(old) & set(new)):
        a, b = old[k], new[k]
        if isinstance(a, float) and isinstance(b, float):
            if (np.isnan(a) and np.isnan(b)) or np.isclose(a, b, rtol=rtol, atol=0.0):
                continue
        elif a == b:
            continue
        changed[k] = {"old": a, "new": b}
    return {"only_in_old": only_old, "only_in_new": only_new, "changed": changed,
            "n_only_in_old": len(only_old), "n_only_in_new": len(only_new), "n_changed": len(changed)}


def event_scan_path() -> Dict[str, Any]:
    from momentum.Analysis.event_samples.pipeline import EventPipelineConfig, EventSamplePipeline
    from tests.momentum.event_samples.helpers import load_bars, make_event

    bars = load_bars(SYM, (TF,))
    records = [make_event(i, t0=BASE + n * H12, label=i % 2) for i, n in enumerate(EVENT_BARS)]
    pipe = EventSamplePipeline()
    cfg = EventPipelineConfig(timeframes=(TF,))

    old = pipe.run(records, bars, cfg)                         # 改前：split_events
    new = pipe.run_event_study_only(records, bars, cfg)        # 改後：生產路徑
    old_tables = pipe.analyze_tables(old, bars, horizons=HORIZONS, n_boot=100)
    new_tables = pipe.analyze_tables(new, bars, horizons=HORIZONS, n_boot=100)

    old_assign = old.split_plan.assignments
    membership_old = {
        "train": sorted(old_assign.loc[old_assign["split_label"] == "train", "event_id"].tolist()),
        "test": sorted(old_assign.loc[old_assign["split_label"] == "test", "event_id"].tolist()),
        "purged": sorted(old.split_plan.purged["event_id"].tolist()),
    }
    return {
        "old_split": "split_events（pipeline.run 歷史路徑）",
        "new_split": "none（run_event_study_only；SPLITUNIFY Task 3.3）",
        "n_events": len(records),
        "membership_old": membership_old,
        "membership_new": "未切分（全部事件進 event-study 全樣本）",
        "summary_diff": _diff(_numeric_leaves(old.summary), _numeric_leaves(new.summary)),
        "tables_diff": _diff(_numeric_leaves(old_tables), _numeric_leaves(new_tables)),
    }


def ic_path() -> Dict[str, Any]:
    from momentum.core.split_preview import holdout_boundary, holdout_split_point, holdout_test_row_index

    rows = []
    for n, oos, purge, emb in ((200, 0.3, 3, 2), (1000, 0.2, 24, 12), (20352, 0.2, 12, 144), (97, 0.25, 0, 0)):
        idx = pd.date_range("2024-01-01", periods=n, freq="12h")
        split_point = holdout_split_point(n, oos_test_size=oos)
        old_train = np.arange(0, split_point, dtype=int)
        old_test = holdout_test_row_index(n, oos_test_size=oos, purge_gap=purge, embargo=emb)
        b = holdout_boundary(idx, oos_test_size=oos, purge_gap=purge, embargo=emb)
        fp = lambda a: hashlib.sha256(np.asarray(a, dtype=np.int64).tobytes()).hexdigest()[:16]  # noqa: E731
        rows.append({
            "n_rows": n, "oos_test_size": oos, "purge_gap": purge, "embargo": emb,
            "train_equal": bool(np.array_equal(old_train, b["train_row_index"])),
            "test_equal": bool(np.array_equal(old_test, b["test_row_index"])),
            "train_fp_old": fp(old_train), "train_fp_new": fp(b["train_row_index"]),
            "test_fp_old": fp(old_test), "test_fp_new": fp(b["test_row_index"]),
        })
    return {
        "old": "holdout_split_point + holdout_test_row_index（就地組）",
        "new": "holdout_boundary（canonical builder）",
        "cases": rows,
        "all_rows_identical": all(r["train_equal"] and r["test_equal"] for r in rows),
    }


def main() -> int:
    out_path = None
    if "--out" in sys.argv:
        out_path = Path(sys.argv[sys.argv.index("--out") + 1])
    report = {
        "_doc": "SPLITUNIFY SPEC C-9 改前改後差異（原殘留 R-2）。事件掃描端比 split_events vs event-study-only；"
                "IC 端比就地列計畫 vs canonical holdout_boundary。",
        "event_scan": event_scan_path(),
        "ic": ic_path(),
    }
    es = report["event_scan"]
    print("=== 事件掃描端 ===")
    print("  改前成員：", {k: len(v) for k, v in es["membership_old"].items()})
    print("  summary：只在改前 %d 鍵、只在改後 %d 鍵、值改變 %d 鍵" % (
        es["summary_diff"]["n_only_in_old"], es["summary_diff"]["n_only_in_new"], es["summary_diff"]["n_changed"]))
    print("  tables ：只在改前 %d 鍵、只在改後 %d 鍵、值改變 %d 鍵" % (
        es["tables_diff"]["n_only_in_old"], es["tables_diff"]["n_only_in_new"], es["tables_diff"]["n_changed"]))
    print("=== IC 端 ===")
    print("  四組參數列計畫逐列相同：", report["ic"]["all_rows_identical"])
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print("receipt →", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
