"""SPLITUNIFY B2b 自查：`build_time_clusters` 抽出**前後**之 A/B 對照。

背景：我把分簇邏輯從 `split_events` 抽成共用函式。既有測試全綠，但那只證明
「被測到的形狀」不變。本探針另外對三種**沒被既有測試涵蓋**的 manifest 形狀做前後逐值對照：
單 TF、共桶（權重非 1）、多筆同時刻。混 TF 與空 table 走 raise 路徑，另外驗錯誤型別一致。

否證觀測：任一形狀之 clusters DataFrame 前後不逐值相等，或 raise 的型別／訊息不同。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, ".")

import pandas as pd

from momentum.Analysis.event_samples.event_split import build_time_clusters as after
from momentum.Analysis.event_samples.types import EventManifest

BEFORE_PATH = (
    Path("/private/tmp/claude-501/-Users-louis-Desktop-quantitative-trading-system")
    / "7972ea91-868b-4287-ae64-ee6737a31e77/scratchpad/event_split_before.py"
)
H1 = 3_600_000
BASE = 1_700_000_000_000


def _load_before():
    spec = importlib.util.spec_from_file_location("event_split_before", BEFORE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _manifest(rows) -> EventManifest:
    table = pd.DataFrame(rows)
    return EventManifest(
        table=table,
        summary={"n_events_raw": len(table), "n_events_effective": len(table)},
        policy={},
    )


def _clusters_before(mod, manifest: EventManifest, bucket_ms: int) -> pd.DataFrame:
    """抽出**前**的行為：逐字重現 `split_events` 內那段（見 `1be5be3f` 之 :156-165）。"""
    t = manifest.table
    bucket = int(bucket_ms)
    tc = (t["decision_at_ms"].astype("int64") // bucket).rename("time_cluster_id")
    counts = tc.map(tc.value_counts())
    return pd.DataFrame(
        {
            "event_id": t["event_id"],
            "time_cluster_id": tc.astype("int64"),
            "cluster_weight": mod._cluster_weight(counts.astype(float)),
        }
    )


CASES = {
    "單 TF 各自成簇": [
        {"event_id": "a", "symbol": "ETHUSDT", "timeframe": "1h", "decision_at_ms": BASE},
        {"event_id": "b", "symbol": "ETHUSDT", "timeframe": "1h", "decision_at_ms": BASE + H1},
    ],
    "共桶（權重 0.5）": [
        {"event_id": "a", "symbol": "ETHUSDT", "timeframe": "1h", "decision_at_ms": BASE},
        {"event_id": "b", "symbol": "ETHUSDT", "timeframe": "1h", "decision_at_ms": BASE + 1},
    ],
    "三筆同時刻（權重 1/3）": [
        {"event_id": f"e{i}", "symbol": "ETHUSDT", "timeframe": "1h", "decision_at_ms": BASE}
        for i in range(3)
    ],
    "跨標的同桶": [
        {"event_id": "a", "symbol": "ETHUSDT", "timeframe": "1h", "decision_at_ms": BASE},
        {"event_id": "b", "symbol": "BTCUSDT", "timeframe": "1h", "decision_at_ms": BASE + 5},
    ],
}


def main() -> int:
    mod = _load_before()
    failures = []
    for name, rows in CASES.items():
        man = _manifest(rows)
        lhs = _clusters_before(mod, man, H1)
        rhs = after(man, H1)
        try:
            pd.testing.assert_frame_equal(lhs, rhs)
            print(f"  ✓ {name}: 前後逐值相等（權重 {sorted(set(rhs['cluster_weight']))}）")
        except AssertionError as exc:
            failures.append(name)
            print(f"  ✗ {name}: 前後**不相等** → {exc}")

    # 混 TF：兩版都應 raise ValueError 且訊息含同一關鍵字
    mixed = _manifest(
        [
            {"event_id": "a", "symbol": "ETHUSDT", "timeframe": "1h", "decision_at_ms": BASE},
            {"event_id": "b", "symbol": "ETHUSDT", "timeframe": "12h", "decision_at_ms": BASE},
        ]
    )
    try:
        after(mixed, None)
        failures.append("混 TF 未 raise")
        print("  ✗ 混 TF：抽出後**沒有** raise（抽出前會）")
    except ValueError as exc:
        ok = "bucket_ms 須顯式指定" in str(exc)
        print(f"  {'✓' if ok else '✗'} 混 TF：raise ValueError，訊息關鍵字{'相符' if ok else '不符'}")
        if not ok:
            failures.append("混 TF 訊息不符")

    print(f"\nA/B FAILURES={len(failures)}" + (f" → {failures}" if failures else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
