"""GAP-3 條件 IC 餵入層（docs/GAP3_EVENT_TODO.md Task B2.3；SPEC D1-3／D1-5／R5 A′）。

純函式：由 manifest＋收據＋匯入表產 `event_timestamps`（＝錨定 TF 之 feature_cutoff bar open，
即決策前最後一根已收盤 bar 的特徵列）＋`event_label_values`（{ms: label_value}）。
條件 IC 只吃連續 `label_value`（缺任一 ⇒ capability unavailable:missing_label_value，v1 不重算）；
`label_return_mode ≠ close_to_close` ⇒ `label_price_mismatch=true` 揭露。
"""

from __future__ import annotations

import hashlib
import json
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

    # survivor v2 六鍵 event_context（CODEX-R1-P1-03：餵入層必須接通；批內 label_definition／control_kind 須單值）
    lds = ev.loc[keep["event_id"], "label_definition"].map(lambda d: json.dumps(d, sort_keys=True, separators=(",", ":")))
    if lds.nunique() != 1:
        raise ValueError("build_event_ic_inputs: 批內 label_definition 不唯一（多組 label 請以 label_id 分批餵入）")
    cks = ev.loc[keep["event_id"], "control_kind"]
    if cks.nunique() != 1:
        raise ValueError("build_event_ic_inputs: 批內 control_kind 不唯一")
    ld = ev.loc[keep["event_id"].iloc[0], "label_definition"]
    manifest_hash = hashlib.sha256(
        keep.sort_values("event_id")[["event_id", "label_start_ms", "label_end_ms", "dedupe_cluster_id", "uniqueness_weight"]]
        .to_json(orient="records").encode("utf-8")
    ).hexdigest()
    event_context = {
        "event_manifest_hash": manifest_hash,
        "label_definition_hash": hashlib.sha256(lds.iloc[0].encode("utf-8")).hexdigest(),
        "decision_time_rule": "t0_open_minus_k_bars",
        "feature_cutoff_rule": "max_close_ms_le_decision_at",
        "label_window_rule": f"{ld.get('label_return_mode')}:horizon_bars={ld['window']['horizon_bars']}",
        "control_kind": str(cks.iloc[0]),
    }
    return {
        **base,
        "capability_status": "ok",
        "reason": None,
        "event_timestamps": sorted(ts_map),
        "event_label_values": ts_map,
        "label_price_mismatch": label_price_mismatch,
        "event_context": event_context,
    }
