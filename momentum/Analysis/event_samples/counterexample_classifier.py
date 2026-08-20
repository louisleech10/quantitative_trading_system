"""GAP-3 反例自動分類（docs/GAP3_EVENT_TODO.md Task B1.5；SPEC AR-2／R2 Y2 公式寫死）。

僅 `label=0` 且 `counterexample_kind` 缺值時執行；direction-aware signed return、
錨＝t₀ close（同 D1）。同時滿足多條（或零條）⇒ `unclassifiable`（不猜）。
使用者已標 ⇒ 不重算不回寫（kind_source=user）；user/platform 衝突 ⇒ 保留 user＋
`platform_suggested_kind` 留痕。門檻四值皆 example_default 可調（白話閘裁決①），
字面唯一住契約檔 `counterexample_classifier_config`。
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

from momentum.Analysis.event_samples.types import AlignmentReceipts

_KIND_A = "a_trigger_no_follow"
_KIND_B = "b_range"
_KIND_C = "c_drop"
_UNCLASSIFIABLE = "unclassifiable"


def _threshold(cfg: dict, name: str) -> float:
    """契約檔形（{value, example_default}）與 runtime 覆寫形（float）皆收。"""
    v = cfg["thresholds"][name]
    return float(v["value"]) if isinstance(v, dict) else float(v)


def _classify_one(r0: float, rw: float, cfg: dict) -> str:
    hits = []
    if r0 >= _threshold(cfg, "trigger_threshold") and rw <= _threshold(cfg, "follow_threshold"):
        hits.append(_KIND_A)
    if abs(r0) <= _threshold(cfg, "range_threshold"):
        hits.append(_KIND_B)
    if r0 <= -_threshold(cfg, "drop_threshold"):
        hits.append(_KIND_C)
    return hits[0] if len(hits) == 1 else _UNCLASSIFIABLE


def classify_counterexamples(
    events: pd.DataFrame,
    receipts: AlignmentReceipts,
    bars_by_tf: Dict[str, Dict[str, pd.DataFrame]],
    classifier_config: dict,
) -> pd.DataFrame:
    """回 derived 欄 DataFrame：{event_id, counterexample_kind_effective, kind_source, platform_suggested_kind}。

    只輸出 label==0 之事件列；答案窗不完整（不在 receipts）⇒ unclassifiable 非亂填。
    """
    ev_receipt = receipts.event_level.set_index("event_id")
    rows = []
    for rec in events.to_dict("records"):
        if int(rec["label"]) != 0:
            continue
        eid = rec["event_id"]
        user_kind: Optional[str] = rec.get("counterexample_kind") or None

        suggestion: Optional[str] = None
        if eid in ev_receipt.index:
            r = ev_receipt.loc[eid]
            bars = bars_by_tf.get(rec["symbol"], {}).get(rec["timeframe"])
            if bars is not None:
                ot = bars["open_time_ms"].to_numpy()
                t0_pos = int(np.searchsorted(ot, int(r["t0_ms"])))
                end_pos = int(np.searchsorted(bars["close_time_ms"].to_numpy(), int(r["label_end_ms"])))
                if t0_pos < len(ot) and int(ot[t0_pos]) == int(r["t0_ms"]) and end_pos < len(ot):
                    o0 = float(bars["open"].iloc[t0_pos])
                    c0 = float(bars["close"].iloc[t0_pos])
                    ce = float(bars["close"].iloc[end_pos])
                    if o0 > 0 and c0 > 0 and np.isfinite(ce):
                        sign = 1.0 if rec["direction"] == "long" else -1.0
                        r0 = sign * (c0 - o0) / o0            # t₀ 自身走勢
                        rw = sign * (ce - c0) / c0            # 答案窗走勢（錨＝t₀ close；末 close aggregation）
                        suggestion = _classify_one(r0, rw, classifier_config)

        if user_kind is not None:
            rows.append({
                "event_id": eid,
                "counterexample_kind_effective": user_kind,   # 主鍵保留 user，不回寫
                "kind_source": "user",
                "platform_suggested_kind": suggestion if (suggestion is not None and suggestion != user_kind) else None,
            })
        else:
            rows.append({
                "event_id": eid,
                "counterexample_kind_effective": suggestion if suggestion is not None else _UNCLASSIFIABLE,
                "kind_source": "platform_auto",
                "platform_suggested_kind": None,
            })
    return pd.DataFrame(rows, columns=["event_id", "counterexample_kind_effective", "kind_source", "platform_suggested_kind"])
