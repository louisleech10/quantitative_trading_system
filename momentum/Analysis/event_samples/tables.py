"""GAP-3 三張表之 B2.1 事件後報酬表／B2.2 正反例辨別表（docs/GAP3_EVENT_TODO.md Task B2.1／B2.2）。

estimand 隔離（SPEC §V）：`statistic_kind ∈ {event_return, binary_discrimination, conditional_ic}`
三值分節、禁合併總分。B2 全批共同約束（AR-3）：必需輸入＝B1.3 `event_split_plan`＋cluster
manifest；每張表必列 macro primary／micro sensitivity／raw·effective n／cluster CI／`degraded`／
LOSO status；未 cluster 調整 ⇒ 禁 formal pooled inference（以 `degraded` 旗標機械揭露）。
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score

from momentum.Analysis.event_samples.baseline import permutation_oracle
from momentum.Analysis.event_samples.types import AlignmentReceipts, EventManifest, EventSplitPlan, OracleConfig


# ---------------------------------------------------------------------------
# 共用：cluster bootstrap CI（固定 seed 決定性；抽樣單位＝time_cluster）
# ---------------------------------------------------------------------------
def _cluster_bootstrap_ci(
    values: np.ndarray, weights: np.ndarray, clusters: np.ndarray, *, seed: int, n_boot: int, q: float = 0.025
) -> Dict[str, float]:
    """加權平均之 cluster bootstrap 分位 CI；單一 cluster 或 n<2 ⇒ unavailable（NaN）。"""
    uniq = np.unique(clusters)
    if len(values) < 2 or len(uniq) < 2:
        return {"ci_low": float("nan"), "ci_high": float("nan"), "n_clusters": int(len(uniq)), "status": "unavailable"}
    rng = np.random.default_rng(seed)
    idx_by_cluster = [np.flatnonzero(clusters == c) for c in uniq]
    boots = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, len(uniq), len(uniq))
        sel = np.concatenate([idx_by_cluster[p] for p in pick])
        w = weights[sel]
        boots[b] = float(np.sum(values[sel] * w) / np.sum(w))
    return {
        "ci_low": float(np.quantile(boots, q)), "ci_high": float(np.quantile(boots, 1 - q)),
        "n_clusters": int(len(uniq)), "status": "ok",
    }


def _weighted_stats(values: np.ndarray, weights: np.ndarray) -> Dict[str, float]:
    if len(values) == 0:
        return {"mean": float("nan"), "median": float("nan"), "win_rate": float("nan"), "n": 0, "n_effective": 0.0}
    w = weights / weights.sum()
    order = np.argsort(values)
    cw = np.cumsum(w[order])
    median = float(values[order][int(np.searchsorted(cw, 0.5))])
    return {
        "mean": float(np.sum(values * w)),
        "median": median,
        "win_rate": float(np.sum((values > 0) * w)),
        "n": int(len(values)),
        "n_effective": float(weights.sum()),
    }


def _common_constraint_block(event_split_plan: Optional[EventSplitPlan], manifest: Optional[EventManifest]) -> Dict:
    """AR-3 共同約束欄（每張表/報告必列；機械可讀）。

    缺 split plan ⇒ `formal_pooled_inference_allowed=False`＋`reason=no_event_split_plan`（fail-closed 揭露，
    CODEX/COMPOSER/GROK B2-R1 共同 finding）；缺 manifest ⇒ raw/effective n 為 null。
    """
    s = event_split_plan.summary if event_split_plan is not None else {}
    degraded = list(s.get("degraded", []))
    allowed = bool(event_split_plan is not None and not degraded and s.get("loso_status") not in (None, "not_evaluated"))
    return {
        "stats_modes": s.get("stats_modes", {"primary": "macro", "sensitivity": "micro"}),
        "n_events_raw": int(manifest.summary["n_events_raw"]) if manifest is not None else None,
        "n_events_effective": manifest.summary["n_events_effective"] if manifest is not None else None,
        "degraded": degraded,
        "loso_status": s.get("loso_status", "not_evaluated"),
        "n_symbols": int(s.get("n_symbols", 0)),
        "insufficient_events_in_test": list(s.get("insufficient_events_in_test", [])),
        "cluster_adjusted": event_split_plan is not None and "no_cluster_adjustment" not in degraded,
        "formal_pooled_inference_allowed": allowed,
        "reason": None if event_split_plan is not None else "no_event_split_plan",
        "dedupe_policy": manifest.policy if manifest is not None else None,
    }


# ---------------------------------------------------------------------------
# B2.1 事件後報酬表
# ---------------------------------------------------------------------------
def event_forward_return_table(
    manifest: EventManifest,
    receipts: AlignmentReceipts,
    bars_by_tf: Dict[str, Dict[str, pd.DataFrame]],
    event_split_plan: EventSplitPlan,
    table_config: dict,
) -> Dict:
    """事件後多 horizon signed 報酬分布表（K5/C7-i；U1；不需反例）。

    signed `(exit_h − entry)/entry`：entry＝D1-6 映射（收據 `entry_price_source_*`）、
    exit_h＝entry bar 之後第 h 根錨定 TF bar 之 close（與標籤基準 t₀ close 報酬並排揭露＝D1-4）。
    table_config：{"horizons": [int,...]（config 化，不寫死）, "seed": int, "n_boot": int}。
    horizon 超出資料 ⇒ 該格 n 反映排除、不灌 0；單事件 ⇒ CI unavailable。
    """
    horizons: List[int] = [int(h) for h in table_config["horizons"]]
    if not horizons or any(h < 1 for h in horizons):
        raise ValueError("event_forward_return_table: horizons 須為 ≥1 之整數清單（config 化）")
    seed = int(table_config.get("seed", 20260820))
    n_boot = int(table_config.get("n_boot", 500))

    t = manifest.table
    for col in ("symbol", "timeframe", "direction"):
        if col not in t.columns:
            raise ValueError(f"event_forward_return_table: manifest 缺 {col}（build_event_manifest 需帶 events=）")
    ev = receipts.event_level.set_index("event_id")
    cl = event_split_plan.clusters.set_index("event_id")

    rows: List[dict] = []
    for rec in t.to_dict("records"):
        eid = rec["event_id"]
        r = ev.loc[eid]
        bars = bars_by_tf[rec["symbol"]][rec["timeframe"]]
        ot = bars["open_time_ms"].to_numpy()
        entry_idx = int(np.searchsorted(ot, int(r["entry_price_source_bar_open_ms"])))
        entry_price = float(bars[r["entry_price_source_field"]].iloc[entry_idx])
        sign = 1.0 if rec["direction"] == "long" else -1.0
        t0_idx = int(np.searchsorted(ot, int(r["t0_ms"])))
        t0_close = float(bars["close"].iloc[t0_idx])
        for h in horizons:
            exit_idx = entry_idx + h
            if exit_idx >= len(bars):
                continue  # horizon 超出資料：該格排除（n 反映），不灌 0
            exit_close = float(bars["close"].iloc[exit_idx])
            rows.append({
                "event_id": eid, "horizon": h,
                "symbol": rec["symbol"], "direction": rec["direction"], "scenario": rec.get("scenario"),
                "period": pd.Timestamp(int(r["t0_ms"]), unit="ms", tz="UTC").strftime("%Y-%m"),
                "ret_entry": sign * (exit_close - entry_price) / entry_price,       # 實際進場持有報酬
                "ret_label_anchor": sign * (exit_close - t0_close) / t0_close,      # 標籤基準（t₀ close）報酬——兩數並排
                "weight": float(rec.get("uniqueness_weight", 1.0)) if rec.get("in_primary", True) else 0.0,
                "in_primary": bool(rec.get("in_primary", True)),
                "time_cluster_id": int(cl.loc[eid, "time_cluster_id"]) if eid in cl.index else -1,
            })
    df = pd.DataFrame(rows)

    def block(sub: pd.DataFrame, weighted: bool) -> Dict:
        out: Dict = {}
        for h in horizons:
            s = sub[sub["horizon"] == h]
            w = s["weight"].to_numpy() if weighted else np.ones(len(s))
            m = w > 0
            vals = s["ret_entry"].to_numpy()[m]
            out[str(h)] = {
                **_weighted_stats(vals, w[m]),
                "label_anchor_mean": float(np.average(s["ret_label_anchor"].to_numpy()[m], weights=w[m])) if m.any() else float("nan"),
                "ci": _cluster_bootstrap_ci(vals, w[m], s["time_cluster_id"].to_numpy()[m], seed=seed, n_boot=n_boot),
            }
        return out

    # primary＝macro（symbol 等權：各 symbol 先算再等權平均）；sensitivity＝micro（**event 等權**，AR-3／B1.3 定義；
    # GROK-R1-P2-02：uniqueness 加權另立獨立鍵 `uniqueness_weighted`，不冒充 micro）
    per_symbol = {sym: block(g, weighted=True) for sym, g in df.groupby("symbol")}
    macro: Dict = {}
    for h in horizons:
        means = [per_symbol[s][str(h)]["mean"] for s in per_symbol if per_symbol[s][str(h)]["n"] > 0]
        macro[str(h)] = {"mean": float(np.mean(means)) if means else float("nan"), "n_symbols": len(means)}

    strata = {
        "by_symbol": per_symbol,
        "by_direction": {d: block(g, True) for d, g in df.groupby("direction")},
        "by_scenario": {str(sc): block(g, True) for sc, g in df.groupby("scenario", dropna=False)},
        "by_period": {p: block(g, True) for p, g in df.groupby("period")},
    }
    return {
        "statistic_kind": "event_return",
        "horizons": horizons,
        "primary_macro": macro,
        "sensitivity_micro": block(df, weighted=False),        # event 等權（AR-3 micro）
        "uniqueness_weighted": block(df, weighted=True),       # 1/overlap_count 加權（B1.2 policy；非 micro）
        "strata": strata,
        "common": _common_constraint_block(event_split_plan, manifest),
        "receipts": {"seed": seed, "n_boot": n_boot, "n_rows": int(len(df))},
    }


# ---------------------------------------------------------------------------
# B2.2 正反例辨別表
# ---------------------------------------------------------------------------
def binary_discrimination_table(
    scores_oos: pd.Series,
    labels: pd.Series,
    event_split_plan: EventSplitPlan,
    strata: pd.DataFrame,
    table_config: dict,
    *,
    manifest: Optional[EventManifest] = None,
) -> Dict:
    """OOS only 之 0/1 辨別表（K5/C7-ii）；擴 B1.4 baseline 為正式表，共用 permutation 核心。

    scores_oos／labels：index=event_id（只取 split_label=="test" 者）；
    strata：index=event_id，欄含 `counterexample_kind_effective`（derived 欄）、`leg`（兩段式腿，選填）。
    分層按 kind a/b/c；`unclassifiable` 不進分層分母、單列 `n_unclassifiable`；one-class ⇒ unavailable。
    """
    oc = OracleConfig(seed=int(table_config.get("seed", 20260820)), n_perm=int(table_config.get("n_perm", 1000)))
    threshold = float(table_config.get("threshold", 0.5))
    top_q = float(table_config.get("top_q", 0.1))
    test_ids = event_split_plan.assignments.loc[event_split_plan.assignments["split_label"] == "test", "event_id"]
    idx = scores_oos.index.intersection(labels.index).intersection(pd.Index(test_ids))
    s = scores_oos.loc[idx].to_numpy(dtype=float)
    y = labels.loc[idx].astype(int).to_numpy()
    if len(s) and not np.isfinite(s).all():
        raise ValueError("binary_discrimination_table: scores 含非有限值，loud 拒")

    def metrics(sv: np.ndarray, yv: np.ndarray) -> Dict:
        if len(np.unique(yv)) < 2:
            return {"capability_status": "unavailable", "reason": "one_class_test_segment", "n": int(len(yv))}
        auc_o = permutation_oracle(sv, yv, lambda a, b: float(roc_auc_score(b, a)), oc)
        pr_o = permutation_oracle(sv, yv, lambda a, b: float(average_precision_score(b, a)), oc)
        pred = (sv >= threshold).astype(int)
        cm = confusion_matrix(yv, pred, labels=[0, 1]).tolist()
        prev = float(yv.mean())
        k = max(1, int(np.ceil(top_q * len(sv))))
        top = np.argsort(-sv)[:k]
        lift_topq = float(yv[top].mean() / prev) if prev > 0 else float("nan")
        lift_thr = float(yv[pred == 1].mean() / prev) if prev > 0 and (pred == 1).any() else float("nan")
        n1, n0 = int(yv.sum()), int((1 - yv).sum())
        rank_biserial = float(2.0 * auc_o["observed"] - 1.0)
        return {
            "capability_status": "ok", "n": int(len(yv)), "prevalence": prev,
            "auc": auc_o["observed"], "auc_band": [auc_o["band_low"], auc_o["band_high"]], "auc_in_band": auc_o["in_band"],
            "pr_auc": pr_o["observed"], "pr_auc_band": [pr_o["band_low"], pr_o["band_high"]], "pr_auc_in_band": pr_o["in_band"],
            "rank_biserial": rank_biserial, "threshold": threshold, "confusion": cm,
            "lift_top_q": lift_topq, "lift_threshold": lift_thr, "n_pos": n1, "n_neg": n0,
        }

    out: Dict = {"statistic_kind": "binary_discrimination", "overall": metrics(s, y)}
    kinds = strata.reindex(idx)["counterexample_kind_effective"] if "counterexample_kind_effective" in strata.columns else pd.Series(index=idx, dtype=object)
    by_kind: Dict[str, Dict] = {}
    n_unclassifiable = int((kinds == "unclassifiable").sum())
    for kind in ("a_trigger_no_follow", "b_range", "c_drop"):
        m = (kinds == kind).to_numpy() | (y == 1)   # 該類反例 vs 全部正例
        if not (kinds == kind).any():
            by_kind[kind] = {"capability_status": "unavailable", "reason": "one_class_test_segment", "n": 0}
            continue
        by_kind[kind] = metrics(s[m], y[m])
    out["by_counterexample_kind"] = by_kind
    out["n_unclassifiable"] = n_unclassifiable
    if "leg" in strata.columns:
        legs = strata.reindex(idx)["leg"]
        out["by_leg"] = {str(l): metrics(s[(legs == l).to_numpy()], y[(legs == l).to_numpy()]) for l in legs.dropna().unique()}
    out["common"] = _common_constraint_block(event_split_plan, manifest)  # AR-3 全套欄（COMPOSER/GROK R1-P2-01）
    # CODEX-R2-P1-01：實際 macro／micro／cluster-CI 數值（非只旗標）
    sym = event_split_plan.assignments.set_index("event_id")["symbol"].reindex(idx)
    clus = event_split_plan.clusters.set_index("event_id")["time_cluster_id"].reindex(idx) if not event_split_plan.clusters.empty else pd.Series(range(len(idx)), index=idx)
    if len(np.unique(y)) >= 2:
        per_sym = []
        for s_name, g in pd.DataFrame({"y": y, "s": s, "sym": sym.to_numpy()}).groupby("sym"):
            if g["y"].nunique() >= 2:
                per_sym.append(float(roc_auc_score(g["y"], g["s"])))
        out["common"]["macro_auc"] = float(np.mean(per_sym)) if per_sym else float("nan")
        out["common"]["micro_auc"] = float(roc_auc_score(y, s))
        cl = clus.fillna(-1).to_numpy().astype("int64")
        from momentum.Analysis.event_samples.all_bars_eval import _cluster_bootstrap_stat

        def _auc_sel(sel):
            return float(roc_auc_score(y[sel], s[sel])) if len(np.unique(y[sel])) >= 2 else None

        out["common"]["auc_cluster_ci"] = _cluster_bootstrap_stat(_auc_sel, cl, seed=oc.seed, n_boot=int(table_config.get("n_boot", 300)))
        out["common"]["n_time_clusters"] = int(len(np.unique(cl)))
    else:
        out["common"].update({"macro_auc": None, "micro_auc": None, "auc_cluster_ci": {"status": "unavailable"}, "n_time_clusters": 0})
    out["receipts"] = {"seed": oc.seed, "n_perm": oc.n_perm, "oos_only": True}
    return out
