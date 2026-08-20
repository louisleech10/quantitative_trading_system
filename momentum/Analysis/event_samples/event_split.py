"""GAP-3 per-symbol 時間切分＋interval-aware purge＋跨標的 time-cluster
（docs/GAP3_EVENT_TODO.md Task B1.3；K4/C6；U12 多標的必要）。

不改 `momentum/core/contracts.py::SplitPlan`（row identity 契約另軌）；
切分一律依 epoch ms 時間比較，**禁 positional index**（ML 孤島舊坑）。
reason／flag 字面＝契約檔 split_purge_reasons／split_loud_flags／degraded_flags。
"""

from __future__ import annotations

import math
from typing import Dict, List

import pandas as pd

from momentum.core.constants import TIMEFRAME_SECONDS
from momentum.Analysis.event_samples.types import EventManifest, EventSplitConfig, EventSplitPlan


def split_events(manifest: EventManifest, split_config: EventSplitConfig) -> EventSplitPlan:
    """事件切分：每標的各自按時間切＋緩衝 ≥ 答案窗；interval 跨界 ⇒ purge。"""
    t = manifest.table
    for col in ("symbol", "timeframe"):
        if col not in t.columns or t[col].isna().any():
            raise ValueError(
                f"split_events: manifest 缺 {col}（build_event_manifest 需帶 events= context；fail-closed）"
            )
    if not (0.0 < split_config.test_fraction < 1.0):
        raise ValueError(f"split_events: test_fraction 須在 (0,1)：{split_config.test_fraction}")

    assign_rows: List[dict] = []
    purge_rows: List[dict] = []
    insufficient: List[str] = []
    per_symbol_n: Dict[str, int] = {}

    for symbol, g in t.groupby("symbol", sort=True):
        g = g.sort_values(["decision_at_ms", "event_id"]).reset_index(drop=True)
        n = len(g)
        per_symbol_n[symbol] = int(n)
        window = (g["label_end_ms"] - g["label_start_ms"]).astype("int64")
        embargo = split_config.embargo_ms if split_config.embargo_ms is not None else int(window.max())
        if embargo < int(window.max()):
            raise ValueError(f"split_events: embargo_ms({embargo}) < 最大答案窗({int(window.max())})——緩衝須 ≥ 答案窗")

        boundary_idx = int(math.floor(n * (1.0 - split_config.test_fraction)))
        if boundary_idx >= n:
            boundary_idx = n - 1
        test_start = int(g["decision_at_ms"].iloc[boundary_idx]) if n > 1 else int(g["decision_at_ms"].iloc[0]) + 1
        # 指派一律以 ms 比較（同 decision 時刻之事件同側；非列號切）
        for rec in g.to_dict("records"):
            if int(rec["decision_at_ms"]) >= test_start:
                assign_rows.append({"event_id": rec["event_id"], "symbol": symbol, "split_label": "test"})
            elif int(rec["label_end_ms"]) > test_start - embargo:
                purge_rows.append({"event_id": rec["event_id"], "reason": "interval_crosses_split_boundary"})
            else:
                assign_rows.append({"event_id": rec["event_id"], "symbol": symbol, "split_label": "train"})

        n_test = sum(1 for r in assign_rows if r["symbol"] == symbol and r["split_label"] == "test")
        if n_test < split_config.tier_min_test_events:
            insufficient.append(symbol)  # loud；不回退全樣本（R1 C3-3）

    assignments = pd.DataFrame(assign_rows, columns=["event_id", "symbol", "split_label"])
    purged = pd.DataFrame(purge_rows, columns=["event_id", "reason"])

    # ---- 跨標的 time-cluster（bucket 預設＝觸發 TF 一根；混 TF 須顯式 bucket_ms）----
    if split_config.bucket_ms is not None:
        bucket = int(split_config.bucket_ms)
    else:
        tfs = sorted(set(t["timeframe"]))
        if len(tfs) != 1:
            raise ValueError(f"split_events: 批內多 TF {tfs}，bucket_ms 須顯式指定（預設＝觸發 TF 一根僅單 TF 適用）")
        bucket = TIMEFRAME_SECONDS[tfs[0]] * 1000
    tc = (t["decision_at_ms"].astype("int64") // bucket).rename("time_cluster_id")
    counts = tc.map(tc.value_counts())
    clusters = pd.DataFrame({
        "event_id": t["event_id"],
        "time_cluster_id": tc.astype("int64"),
        "cluster_weight": 1.0 / counts.astype(float),  # primary（R1 X9）；bootstrap over clusters＝敏感度
    })

    n_symbols = len(per_symbol_n)
    degraded: List[str] = []
    if n_symbols == 1:
        degraded.append("single_symbol")  # exploratory 可跑；禁 formal pooled inference 由下游讀旗標強制

    summary = {
        "n_symbols": n_symbols,
        "per_symbol_n": per_symbol_n,
        "n_time_clusters": int(clusters["time_cluster_id"].nunique()),
        "avg_cluster_size": float(len(clusters) / max(1, clusters["time_cluster_id"].nunique())),
        "degraded": degraded,
        "loso_status": "not_evaluated",  # 跨 symbol 泛化宣稱須 LOSO/held-out receipt
        "insufficient_events_in_test": insufficient,
        "stats_modes": {"primary": "macro", "sensitivity": "micro"},
        "n_events_raw": int(manifest.summary["n_events_raw"]),
        "n_events_effective": manifest.summary["n_events_effective"],
        "n_purged": int(len(purged)),
        "bucket_ms": bucket,
    }
    return EventSplitPlan(assignments=assignments, purged=purged, clusters=clusters, summary=summary)
