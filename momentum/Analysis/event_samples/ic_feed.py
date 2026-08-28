"""GAP-3 條件 IC 餵入層（docs/GAP3_EVENT_TODO.md Task B2.3；SPEC D1-3／D1-5／R5 A′）。

純函式：由 manifest＋收據＋匯入表產 `event_timestamps`（＝錨定 TF 之 feature_cutoff bar open，
即決策前最後一根已收盤 bar 的特徵列）＋`event_label_values`（{ms: label_value}）。
條件 IC 只吃連續 `label_value`（缺任一 ⇒ capability unavailable:missing_label_value）。
🔴 **Task 7.0b 已落地（2026-08-28），但走的是另一條路，請勿誤讀本模組**：
分析時 producer 完成後，IC 分析路徑（`api/services/ic_analysis_service.py::_run_event_label_stages`）
**不經過本模組**——它直接由 `PreparedAnalysisWindows` 之 `windows` ＋ `per_tf` 組出
`{feature_cutoff_ms: label_value}` 餵給 `analyzer.analyze(event_label_values=...)`。
理由：SPEC ⑩(ii″) 要求四處收到的物件**皆 `is prepared1`**（身分比對），
而本模組的簽章吃的是 manifest／receipts／DataFrame，把 prepared 拆回 DataFrame 再組回來
就等於**新增一次重組**，`is` 比對必然失效。
⇒ **本模組現行的唯一 consumer 是匯入端之 `EventImportService.analyze`（表格鏈），
不是 IC 分析鏈。** 「v1 不重算」對**那條鏈**仍然成立；它不是設計上限，
只是那條鏈沒有分析時 producer。
🔴 **具名偏差**：TODO 7.0b 之「修改檔案」列了 `ic_feed.py（只吃 prepared1）`，
本批**未改本檔**。改法會是把它的簽章換成吃 `PreparedAnalysisWindows`，
但那會讓匯入端表格鏈也被迫走 prepared——那條鏈根本沒有 prepared。留待 review 裁。
`label_return_mode ≠ close_to_close` ⇒ `label_price_mismatch=true` 揭露。
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, Optional

import pandas as pd

from momentum.Analysis.event_samples.lookahead_gate import LookaheadGate, capability_unavailable_block
from momentum.Analysis.event_samples.types import AlignmentReceipts, EventManifest, EventSplitPlan


def build_event_ic_inputs(
    manifest: EventManifest,
    event_split_plan: Optional[EventSplitPlan],
    events: pd.DataFrame,
    receipts: AlignmentReceipts,
    *,
    timeframe: str,
    lookahead_gate: Optional[LookaheadGate] = None,
) -> Dict:
    """回 dict：capability_status／reason／event_timestamps／event_label_values／label_price_mismatch／n_events。

    只取 manifest `in_primary` 事件（dedupe policy）；同一 feature 列被兩事件映射 ⇒ loud（禁默默覆蓋）。

    `lookahead_gate`（GAP-3 UX Task 1.12／D-7 之 L3）：深度不可證之批 ⇒ 條件 IC
    `capability_status="unavailable"`＋契約之 reason，**不**產出 timestamps／label 值。
    `None` ＝平台產生器路徑，不開本閘。
    """
    blocked = capability_unavailable_block(lookahead_gate)
    if blocked is not None:
        return {
            "statistic_kind": "conditional_ic",
            "sample_scope_kind": "event",
            "timeframe": timeframe,
            "n_events": 0,
            "split_summary": {},
            **blocked,
            "event_timestamps": [],
            "event_label_values": {},
        }
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
