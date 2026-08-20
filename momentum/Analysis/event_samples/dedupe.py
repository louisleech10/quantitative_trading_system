"""GAP-3 去重/簇/唯一性權重 manifest（docs/GAP3_EVENT_TODO.md Task B1.2；K3/C5）。

cluster_gap 以 UTC duration（預設＝各事件答案窗 duration）非 row count；
跨 symbol 同時刻與 interval overlap 一併 union；primary policy 事前固定依情境：
C ⇒ cluster_first（簇首代表＝interval 最早）、A/B ⇒ all_with_uniqueness
（w_i=1/overlap_count 於 label 窗；顯著性必配 cluster-robust/bootstrap，無修正 raw-all 禁出）。
另一 policy＝預先登記之敏感度，報 sensitivity_flip。
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List

import pandas as pd

from momentum.Analysis.event_samples.types import AlignmentReceipts, DedupePolicyConfig, EventManifest

_POLICY_BY_SCENARIO = {"C": "cluster_first", "A": "all_with_uniqueness", "B": "all_with_uniqueness", "two_stage": "all_with_uniqueness"}


def _overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def build_event_manifest(
    receipts: AlignmentReceipts,
    policy_config: DedupePolicyConfig,
    *,
    events: "pd.DataFrame | None" = None,
) -> EventManifest:
    """由事件級收據建 manifest。缺 interval（label_start/label_end 缺值）⇒ fail-closed。

    events（選用 keyword；不改 SPEC 位置簽名）：驗證後匯入表，join symbol/timeframe/label
    入 manifest.table——B1.3 per-symbol 切分與 time-cluster bucket（觸發 TF 一根）之必要輸入；
    receipt_schema 為契約閉集不得擴欄，故 context 走 manifest 層。
    """
    ev = receipts.event_level.copy()
    if ev.empty:
        raise ValueError("build_event_manifest: empty receipts（無事件可組 manifest，loud）")
    for col in ("label_start_ms", "label_end_ms"):
        if ev[col].isna().any():
            raise ValueError(f"build_event_manifest: 缺 interval 欄 {col}（fail-closed，R2 C5）")

    ev = ev.sort_values(["label_start_ms", "event_id"]).reset_index(drop=True)
    starts = ev["label_start_ms"].astype("int64").to_numpy()
    ends = ev["label_end_ms"].astype("int64").to_numpy()
    n = len(ev)

    # ---- 簇 union-find（COMPOSER-R1-P1-01／CODEX-R1-P1-02 修）：interval overlap 或
    # start 差 ≤ cluster_gap 即 union；連通分量＝簇。鏈式「只比前一顆」會把
    # 仍與更早長窗相交之事件錯拆（反例：A[0,100],C[30,35],B[40,50]）。O(n²) 對事件級 n 可承受。----
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for i in range(n):
        gap_i = policy_config.cluster_gap_ms
        if gap_i is None:
            gap_i = int(ends[i] - starts[i])  # 預設＝該事件答案窗 duration（UTC duration）
        for j in range(i + 1, n):
            if _overlap(int(starts[i]), int(ends[i]), int(starts[j]), int(ends[j])) or (
                int(starts[j] - starts[i]) <= gap_i
            ):
                union(i, j)

    # 連通分量 → 依最早 start 之出現序編號（決定性）
    root_order: Dict[int, int] = {}
    cluster_ids: List[int] = [0] * n
    for i in range(n):
        r = find(i)
        if r not in root_order:
            root_order[r] = len(root_order)
        cluster_ids[i] = root_order[r]

    # ---- overlap set / uniqueness weight（label 窗兩兩相交；簇內 n 小）----
    overlap_sets: List[List[str]] = []
    for i in range(n):
        members = [
            str(ev["event_id"].iloc[j])
            for j in range(n)
            if _overlap(int(starts[i]), int(ends[i]), int(starts[j]), int(ends[j]))
        ]
        overlap_sets.append(sorted(members))
    overlap_hash = [
        hashlib.sha256(json.dumps(s, separators=(",", ":")).encode("utf-8")).hexdigest() for s in overlap_sets
    ]
    overlap_count = [len(s) for s in overlap_sets]
    weights = [1.0 / c for c in overlap_count]

    table = pd.DataFrame({
        "event_id": ev["event_id"],
        "observation_interval_start_ms": starts,
        "observation_interval_end_ms": ends,
        "label_start_ms": starts,
        "label_end_ms": ends,
        "decision_at_ms": ev["decision_at_ms"].astype("int64").to_numpy(),
        "dedupe_cluster_id": [f"c{c}" for c in cluster_ids],
        "overlap_set_hash": overlap_hash,
        "uniqueness_weight": weights,
    })
    if events is not None:
        ctx_cols = [c for c in ("event_id", "symbol", "timeframe", "label", "scenario", "direction") if c in events.columns]
        table = table.merge(events[ctx_cols], on="event_id", how="left", validate="one_to_one")

    # ---- 兩種 policy 的保留集 ----
    def retained(policy: str) -> pd.Series:
        if policy == "cluster_first":
            first_idx = table.groupby("dedupe_cluster_id")["observation_interval_start_ms"].idxmin()
            # tie（同 start）→ event_id 最小；排序已保證 idxmin 取先出現者
            keep = pd.Series(False, index=table.index)
            keep.loc[first_idx] = True
            return keep
        return pd.Series(True, index=table.index)  # all_with_uniqueness：全留、靠權重

    primary = _POLICY_BY_SCENARIO.get(policy_config.scenario)
    if primary is None:
        raise ValueError(f"unknown scenario for dedupe policy: {policy_config.scenario!r}")
    sensitivity = "all_with_uniqueness" if primary == "cluster_first" else "cluster_first"

    table["in_primary"] = retained(primary)
    table["in_sensitivity"] = retained(sensitivity)

    n_clusters = table["dedupe_cluster_id"].nunique()
    eff_primary = int(table["in_primary"].sum()) if primary == "cluster_first" else float(sum(weights))
    eff_sens = int(table["in_sensitivity"].sum()) if sensitivity == "cluster_first" else float(sum(weights))
    summary: Dict = {
        "n_events_raw": int(n),
        "n_events_effective": eff_primary,
        "n_clusters": int(n_clusters),
        "overlap_fraction": float(sum(1 for c in overlap_count if c > 1) / n),
        "sensitivity_flip": bool(
            set(table.loc[table["in_primary"], "event_id"]) != set(table.loc[table["in_sensitivity"], "event_id"])
            or eff_primary != eff_sens
        ),
    }
    policy = {
        "primary": primary,
        "sensitivity": sensitivity,
        "scenario": policy_config.scenario,
        "cluster_gap_ms": policy_config.cluster_gap_ms,
        # A/B 全留之顯著性必配 cluster-robust/bootstrap（下游 B2 讀此旗標強制；無修正 raw-all 禁出）
        "requires_cluster_robust": primary == "all_with_uniqueness",
    }
    return EventManifest(table=table, summary=summary, policy=policy)
