"""GAP-3 per-symbol 時間切分＋interval-aware purge＋跨標的 time-cluster
（docs/GAP3_EVENT_TODO.md Task B1.3；K4/C6；U12 多標的必要）。

不改 `momentum/core/contracts.py::SplitPlan`（row identity 契約另軌）；
切分一律依 epoch ms 時間比較，**禁 positional index**（ML 孤島舊坑）。
reason／flag 字面＝契約檔 split_purge_reasons／split_loud_flags／degraded_flags。
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

import pandas as pd

from momentum.core.constants import TIMEFRAME_SECONDS
from momentum.Analysis.event_samples.lookahead_gate import LookaheadGate, assert_split_allowed
from momentum.Analysis.event_samples.types import EventManifest, EventSplitConfig, EventSplitPlan


def _degraded_flags(n_symbols: int, *, cluster_adjusted: bool) -> List[str]:
    """`degraded` 旗標唯一產生點（AR-3 共同約束；M11 mutation seam）：
    單 symbol ⇒ `single_symbol`（exploratory 可跑、禁 formal pooled inference）；未 cluster 調整 ⇒ `no_cluster_adjustment`。
    字面＝契約檔 degraded_flags。"""
    flags: List[str] = []
    if n_symbols == 1:
        flags.append("single_symbol")
    if not cluster_adjusted:
        flags.append("no_cluster_adjustment")
    return flags


def _cluster_weight(counts: "pd.Series") -> "pd.Series":
    """time-cluster 權重公式 w=1/n（R1 X9）唯一實作點（CODEX-R1-P1-01：M5 production
    seam——monkeypatch 改全 1 即破「同簇權重和＝1」斷言，測試必紅）。"""
    return 1.0 / counts


def split_events(
    manifest: EventManifest,
    split_config: EventSplitConfig,
    *,
    lookahead_gate: Optional[LookaheadGate] = None,
) -> EventSplitPlan:
    """事件切分：每標的各自按時間切＋緩衝 ≥ 答案窗；interval 跨界 ⇒ purge。

    `lookahead_gate`（GAP-3 UX Task 1.12／D-7 之 L3）：深度不可證之批 ⇒ **raise**，
    不得以警告放行（fail-open）。`None` ＝平台產生器路徑，不開本閘（見 `lookahead_gate` 檔頭）。
    """
    assert_split_allowed(lookahead_gate, where="split_events")
    t = manifest.table
    for col in ("symbol", "timeframe"):
        if col not in t.columns or t[col].isna().any():
            raise ValueError(
                f"split_events: manifest 缺 {col}（build_event_manifest 需帶 events= context；fail-closed）"
            )
    if not (0.0 < split_config.test_fraction < 1.0):
        raise ValueError(f"split_events: test_fraction 須在 (0,1)：{split_config.test_fraction}")

    # 🔴 GAP-3 UX Task 7.0b（§D-3′-a（ii））：`embargo_ms` 與 `embargo_ms_by_symbol` **互斥**。
    #    不做「以哪個為優先」之隱含規則——那種規則寫下來的當天就沒人記得，出錯時也看不出來。
    by_symbol = split_config.embargo_ms_by_symbol
    if by_symbol is not None and split_config.embargo_ms is not None:
        raise ValueError(
            "split_events: `embargo_ms` 與 `embargo_ms_by_symbol` 不得同時給定（fail-closed）"
            "——事件分析路徑一律用後者，非事件之既有 caller 用前者"
        )
    if by_symbol is not None and not by_symbol:
        raise ValueError(
            "split_events: `embargo_ms_by_symbol` 給定但為空——事件分析路徑必傳且非空（fail-closed）"
        )

    assign_rows: List[dict] = []
    purge_rows: List[dict] = []
    insufficient: List[str] = []
    per_symbol_n: Dict[str, int] = {}

    for symbol, g in t.groupby("symbol", sort=True):
        g = g.sort_values(["decision_at_ms", "event_id"]).reset_index(drop=True)
        n = len(g)
        per_symbol_n[symbol] = int(n)
        window = (g["label_end_ms"] - g["label_start_ms"]).astype("int64")
        if by_symbol is not None:
            # 🔴 **逐 symbol 檢核，缺一即 fail-closed，不得跳過或補預設**（§D-3′-a（ii)）：
            #    ① 本次 split 的每個 symbol 都必須是 map 的鍵；② 值須為 `int >= 0`。
            #    補預設等於讓「這個 symbol 的下界沒算出來」偽裝成「下界是 0」，
            #    而 0 會讓 train/test 之間完全沒有緩衝——那正是這條路徑要防的事。
            if symbol not in by_symbol:
                raise ValueError(
                    f"split_events: `embargo_ms_by_symbol` 缺 symbol {symbol!r}（fail-closed，不補預設）"
                )
            raw = by_symbol[symbol]
            if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
                raise ValueError(
                    f"split_events: `embargo_ms_by_symbol[{symbol!r}]` 須為 int >= 0，實得 {raw!r}"
                )
            embargo = int(raw)
        else:
            embargo = split_config.embargo_ms if split_config.embargo_ms is not None else int(window.max())
        # ③ 值須 >= 該 symbol 之答案窗（既有不變式；深度側之下限已由呼叫端之
        #    `purge_lower_bound_ms` 併入，本層看不到深度，故此處只驗得到窗寬那一半——
        #    這是**具名邊界**，不是漏檢。
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
        "cluster_weight": _cluster_weight(counts.astype(float)),  # primary（R1 X9）；bootstrap over clusters＝敏感度
    })

    n_symbols = len(per_symbol_n)
    degraded: List[str] = _degraded_flags(n_symbols, cluster_adjusted=True)

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
