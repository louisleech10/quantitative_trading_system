"""GAP-3 條件 IC 餵入層（docs/GAP3_EVENT_TODO.md Task B2.3；SPEC D1-3／D1-5／R5 A′）。

純函式：由 manifest＋收據＋匯入表產 `event_timestamps`（＝錨定 TF 之 feature_cutoff bar open，
即決策前最後一根已收盤 bar 的特徵列）＋`event_label_values`（{ms: label_value}）。
條件 IC 只吃連續 `label_value`（缺任一 ⇒ capability unavailable:missing_label_value，v1 不重算）；
`label_return_mode ≠ close_to_close` ⇒ `label_price_mismatch=true` 揭露。
"""

from __future__ import annotations

from typing import Dict

import pandas as pd

from momentum.Analysis.event_samples.types import AlignmentReceipts, EventManifest, EventSplitPlan


def build_event_ic_inputs(
    manifest: EventManifest,
    event_split_plan: EventSplitPlan,
    events: pd.DataFrame,
    receipts: AlignmentReceipts,
    *,
    timeframe: str,
) -> Dict:
    """回 dict：capability_status／reason／event_timestamps／event_label_values／label_price_mismatch／n_events。

    只取 manifest `in_primary` 事件（dedupe policy）；同一 feature 列被兩事件映射 ⇒ loud（禁默默覆蓋）。
    """
    t = manifest.table
    keep = t[t["in_primary"]] if "in_primary" in t.columns else t
    ev = events.set_index("event_id")
    per_tf = receipts.per_tf[receipts.per_tf["timeframe"] == timeframe].set_index("event_id")

    base = {
        "statistic_kind": "conditional_ic",
        "sample_scope_kind": "event",
        "timeframe": timeframe,
        "n_events": int(len(keep)),
        "split_summary": {k: event_split_plan.summary.get(k) for k in ("degraded", "loso_status", "stats_modes")},
    }
    if "label_value" not in ev.columns or ev.loc[keep["event_id"], "label_value"].isna().any():
        return {**base, "capability_status": "unavailable", "reason": "missing_label_value",
                "event_timestamps": [], "event_label_values": {}}

    modes = ev.loc[keep["event_id"], "label_definition"].map(lambda d: d.get("label_return_mode"))
    label_price_mismatch = bool((modes != "close_to_close").any())

    ts_map: Dict[int, float] = {}
    for eid in keep["event_id"]:
        if eid not in per_tf.index:
            raise ValueError(f"build_event_ic_inputs: 事件 {eid} 無 {timeframe} per-TF 收據（對齊未過或 TF 不在 config）")
        ts = int(per_tf.loc[eid, "last_bar_open_ms"])
        if ts in ts_map:
            raise ValueError(f"build_event_ic_inputs: 兩事件映射同一 feature 列 {ts}（禁默默覆蓋；請先 dedupe）")
        ts_map[ts] = float(ev.loc[eid, "label_value"])

    return {
        **base,
        "capability_status": "ok",
        "reason": None,
        "event_timestamps": sorted(ts_map),
        "event_label_values": ts_map,
        "label_price_mismatch": label_price_mismatch,
    }
