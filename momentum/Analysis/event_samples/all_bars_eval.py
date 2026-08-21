"""GAP-3 全部 K 線驗證 evaluator（docs/GAP3_EVENT_TODO.md Task B2.5；SPEC D4＝整票靈魂的機器形）。

all-bars evaluation manifest 以 `decision_at` 為索引，只納 `eligible`（答案窗完整、資料連續、
價格有效、PIT 合法）；報 n_total／n_eligible／n_labeled／n_unknown／n_tail_excluded／n_missing＋reason。
`prevalence_learn`（case-control 學習樣本）與 `prevalence_full`（全 K 線）**必並排**＋
`sample_design=case_control` 揭露＋lift；缺任一 ⇒ capability unavailable:missing_prevalence_disclosure。
D4-4 不做：倉位／手續費／滑價／複利／資金曲線／turnover／capacity／triple-barrier／long-short。
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score

from momentum.core.constants import TIMEFRAME_SECONDS
from momentum.Analysis.event_samples.counterexample_classifier import _classify_one


def _cluster_bootstrap_stat(
    values_fn, clusters: np.ndarray, *, seed: int, n_boot: int
) -> Dict[str, float]:
    """以 cluster 為抽樣單位的 bootstrap 分位 CI（CODEX-R2-P1-01：共同欄須含實際 cluster-CI）。
    values_fn(sel_idx) → 統計量；單一 cluster ⇒ unavailable。"""
    uniq = np.unique(clusters)
    if len(uniq) < 2:
        return {"ci_low": float("nan"), "ci_high": float("nan"), "n_clusters": int(len(uniq)), "status": "unavailable"}
    rng = np.random.default_rng(seed)
    idx_by = [np.flatnonzero(clusters == c) for c in uniq]
    boots = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(uniq), len(uniq))
        sel = np.concatenate([idx_by[p] for p in pick])
        v = values_fn(sel)
        if v is not None and np.isfinite(v):
            boots.append(float(v))
    if len(boots) < max(10, n_boot // 4):
        return {"ci_low": float("nan"), "ci_high": float("nan"), "n_clusters": int(len(uniq)), "status": "unavailable"}
    return {"ci_low": float(np.quantile(boots, 0.025)), "ci_high": float(np.quantile(boots, 0.975)),
            "n_clusters": int(len(uniq)), "status": "ok"}


def _is_eligible(
    i: int, n: int, horizon: int, k: int, open_: np.ndarray, close: np.ndarray,
    open_ms: Optional[np.ndarray] = None, step_ms: Optional[int] = None,
) -> Optional[str]:
    """回 None＝eligible，否則 reason（D4-1：答案窗完整／資料連續／價格有效／PIT 合法）。
    獨立小函式供 mutation guard（M4 分母竄改）monkeypatch。"""
    if i - k < 0:
        return "warmup_insufficient"
    if i + horizon >= n:
        return "label_window_incomplete"
    # 資料連續（CODEX-R1-P1-02／R2-P1-02）：決策 bar → 答案窗末 bar **逐鄰**差恰＝契約 TF 步長
    # （duplicate ⇒ 差 0、缺根 ⇒ 差 2Δ，皆拒；步長來自 TIMEFRAME_SECONDS 非資料自身）
    if open_ms is not None and step_ms is not None:
        seg = open_ms[i - k: i + horizon + 1].astype("int64")
        if len(seg) > 1 and not (np.diff(seg) == int(step_ms)).all():
            return "missing_bar"
    seg_o = open_[i - k: i + horizon + 1]
    seg_c = close[i - k: i + horizon + 1]
    if not (np.isfinite(seg_o).all() and np.isfinite(seg_c).all() and (seg_o > 0).all() and (seg_c > 0).all()):
        return "nonpositive_reference_price"
    return None


def _entry_price(semantic: str, open_: np.ndarray, close: np.ndarray, i: int, k: int, horizon: int) -> float:
    """D1-6 entry 語意 → 價格（與 B1.1 映射同義；next_open 須落在答案窗內）。"""
    if semantic == "trigger_open":
        return float(open_[i])
    if semantic == "trigger_close":
        return float(close[i])
    if semantic == "next_open":
        if horizon < 1:
            raise ValueError("next_open 需 horizon_bars ≥ 1")
        return float(open_[i + 1])
    if semantic == "decision_bar_open":
        return float(open_[i - k])
    if semantic == "decision_bar_close":
        return float(close[i - k])
    raise ValueError(f"unknown entry_price_semantic {semantic!r}")


def _label_from_rule(direction_sign: float, close: np.ndarray, i: int, horizon: int, threshold: float) -> int:
    """標籤規則（close_to_close）：dir·(close[i+h]/close[i]−1) ≥ threshold ⇒ 1。"""
    r = direction_sign * (close[i + horizon] / close[i] - 1.0)
    return int(r >= threshold)


def evaluate_all_bars(
    model_scores_or_rule: Union[pd.Series, Callable[[pd.DataFrame], pd.Series]],
    bars: Dict[str, pd.DataFrame],
    manifest_config: dict,
    *,
    event_split_plan=None,
    manifest=None,
) -> Dict:
    """固定分母 evaluation。

    bars：{symbol: DataFrame(open_time_ms/close_time_ms/open/close)}（單一錨定 TF）。
    model_scores_or_rule：index=(symbol, open_time_ms) MultiIndex 之 score Series，或 callable(bars_df)->Series（index=open_time_ms）。
    manifest_config：{"horizon_bars":int, "label_threshold":float, "direction":"long|short",
      "decision_offset_bars":int, "score_threshold":float, "top_q":float,
      "prevalence_learn":float|None（case-control 學習樣本基率，必填揭露）, "sample_design":"case_control",
      "classifier_config":dict|None（反例分層用，選填）, "seed":int, "n_boot":int,
      "label_id":str（多組條件命中時以 label_id 區分，禁默默覆蓋）}。
    """
    horizon = int(manifest_config["horizon_bars"])
    thr_label = float(manifest_config["label_threshold"])
    sign = 1.0 if manifest_config.get("direction", "long") == "long" else -1.0
    k = int(manifest_config.get("decision_offset_bars", 0))
    score_thr = float(manifest_config.get("score_threshold", 0.5))
    top_q = float(manifest_config.get("top_q", 0.1))
    seed = int(manifest_config.get("seed", 20260820))
    n_boot = int(manifest_config.get("n_boot", 300))
    cls_cfg = manifest_config.get("classifier_config")
    label_id = str(manifest_config.get("label_id", "default"))
    # CODEX-R2-P1-02：entry 語意與 TF 為必填（無預設；estimand 不得靜默改變）；k ≥ 0
    if "entry_price_semantic" not in manifest_config:
        raise ValueError("evaluate_all_bars: manifest_config.entry_price_semantic 必填（D1-6 五值之一，無預設）")
    entry_semantic = str(manifest_config["entry_price_semantic"])
    if entry_semantic not in ("trigger_open", "trigger_close", "next_open", "decision_bar_open", "decision_bar_close"):
        raise ValueError(f"evaluate_all_bars: entry_price_semantic {entry_semantic!r} 非 D1-6 五值")
    if k < 0:
        raise ValueError("evaluate_all_bars: decision_offset_bars 須 ≥ 0")
    if "timeframe" not in manifest_config or manifest_config["timeframe"] not in TIMEFRAME_SECONDS:
        raise ValueError("evaluate_all_bars: manifest_config.timeframe 必填且須在 TIMEFRAME_SECONDS（網格步長來源）")
    expected_step_ms = TIMEFRAME_SECONDS[manifest_config["timeframe"]] * 1000
    bucket_ms = int(manifest_config.get("bucket_ms", expected_step_ms))  # time-cluster 桶（cluster CI 用）

    prevalence_learn = manifest_config.get("prevalence_learn")
    if prevalence_learn is None or manifest_config.get("sample_design") != "case_control":
        return {
            "statistic_kind": "all_bars_evaluation",
            "capability_status": "unavailable",
            "reason": "missing_prevalence_disclosure",
            "doc": "prevalence_learn（case-control 學習樣本基率）與 sample_design=case_control 為必填揭露（D4-3）",
        }

    rows: List[dict] = []
    counts = {"n_total": 0, "n_eligible": 0, "n_labeled": 0, "n_unknown": 0, "n_tail_excluded": 0, "n_missing": 0}
    reasons: Dict[str, int] = {}
    for symbol, df in sorted(bars.items()):
        df = df.sort_values("open_time_ms").reset_index(drop=True)
        open_ = df["open"].to_numpy(dtype=float)
        close = df["close"].to_numpy(dtype=float)
        ot = df["open_time_ms"].to_numpy()
        n = len(df)
        step_ms = expected_step_ms  # 網格步長＝契約 TF（非資料自身 median；CODEX-R2-P1-02）
        if n != len(np.unique(ot)):
            raise ValueError(f"evaluate_all_bars: {symbol} bars 含重複 open_time_ms（duplicate_bar）")
        if callable(model_scores_or_rule):
            scores = model_scores_or_rule(df)
            scores = pd.Series(np.asarray(scores, dtype=float), index=ot)
        else:
            s = model_scores_or_rule
            scores = s.xs(symbol, level=0) if isinstance(s.index, pd.MultiIndex) else s
        for i in range(n):
            counts["n_total"] += 1
            reason = _is_eligible(i, n, horizon, k, open_, close, ot, step_ms)
            if reason is not None:
                reasons[reason] = reasons.get(reason, 0) + 1
                if reason == "label_window_incomplete":
                    counts["n_tail_excluded"] += 1
                else:
                    counts["n_unknown"] += 1
                continue
            counts["n_eligible"] += 1
            decision_ms = int(ot[i - k])
            sc = scores.get(int(ot[i - k]), np.nan) if not callable(model_scores_or_rule) else float(scores.iloc[i - k])
            if sc is None or not np.isfinite(float(sc)):
                counts["n_missing"] += 1
                continue
            y = _label_from_rule(sign, close, i, horizon, thr_label)
            counts["n_labeled"] += 1
            # 實際持有報酬：entry（D1-6 語意）→ 答案窗末 close（D1-4 並排）
            entry = _entry_price(entry_semantic, open_, close, i, k, horizon)
            hold = sign * (close[i + horizon] - entry) / entry
            kind = None
            if cls_cfg is not None and y == 0:
                r0 = sign * (close[i] - open_[i]) / open_[i]
                rw = sign * (close[i + horizon] - close[i]) / close[i]
                kind = _classify_one(r0, rw, cls_cfg)
            rows.append({
                "symbol": symbol, "decision_at_ms": decision_ms, "t0_ms": int(ot[i]), "score": float(sc), "y": y,
                "hold_return": hold, "period": pd.Timestamp(int(ot[i]), unit="ms", tz="UTC").strftime("%Y-%m"),
                "counterexample_kind_effective": kind, "label_id": label_id,
                "time_cluster_id": int(decision_ms // bucket_ms),
            })
    m = pd.DataFrame(rows)

    def metrics(sub: pd.DataFrame) -> Dict:
        if sub.empty or sub["y"].nunique() < 2:
            return {"capability_status": "unavailable", "reason": "one_class_test_segment", "n": int(len(sub))}
        yv, sv = sub["y"].to_numpy(), sub["score"].to_numpy()
        pred = (sv >= score_thr).astype(int)
        tp = int(((pred == 1) & (yv == 1)).sum()); fp = int(((pred == 1) & (yv == 0)).sum())
        fn = int(((pred == 0) & (yv == 1)).sum()); tn = int(((pred == 0) & (yv == 0)).sum())
        prec = tp / (tp + fp) if tp + fp else float("nan")
        rec = tp / (tp + fn) if tp + fn else float("nan")
        f1 = 2 * prec * rec / (prec + rec) if (tp + fp) and (tp + fn) and (prec + rec) > 0 else float("nan")
        p_curve, r_curve, _ = precision_recall_curve(yv, sv)
        prev_full = float(yv.mean())
        kq = max(1, int(np.ceil(top_q * len(sv))))
        top = np.argsort(-sv)[:kq]
        rng = np.random.default_rng(seed)
        boots = [float(np.random.default_rng(seed + b).choice(sub["hold_return"].to_numpy()[pred == 1], len(top), replace=True).mean())
                 for b in range(n_boot)] if (pred == 1).any() else []
        return {
            "capability_status": "ok", "n": int(len(sub)),
            "precision": prec, "recall": rec, "f1": f1, "confusion": [[tn, fp], [fn, tp]],
            "auc": float(roc_auc_score(yv, sv)), "pr_auc": float(average_precision_score(yv, sv)),
            "pr_curve": {"precision": p_curve.tolist()[:200], "recall": r_curve.tolist()[:200]},
            "signal_frequency": float(pred.mean()),
            "prevalence_full": prev_full, "prevalence_learn": float(prevalence_learn),
            "lift_top_q": float(yv[top].mean() / prev_full) if prev_full > 0 else float("nan"),
            "lift_threshold": float(yv[pred == 1].mean() / prev_full) if prev_full > 0 and (pred == 1).any() else float("nan"),
            "signed_hold_return_signaled_mean": float(sub["hold_return"].to_numpy()[pred == 1].mean()) if (pred == 1).any() else float("nan"),
            "signed_hold_return_ci": [float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))] if boots else None,
        }

    out: Dict = {
        "statistic_kind": "all_bars_evaluation",
        "capability_status": "ok",
        "sample_design": "case_control",
        "label_id": label_id,
        "counts": counts,
        "ineligible_reasons": reasons,
        "overall": metrics(m),
        "strata": {
            "by_symbol": {s: metrics(g) for s, g in m.groupby("symbol")} if not m.empty else {},
            "by_period": {p: metrics(g) for p, g in m.groupby("period")} if not m.empty else {},
            "by_counterexample_kind": (
                {k_: metrics(m[(m["counterexample_kind_effective"] == k_) | (m["y"] == 1)])
                 for k_ in ("a_trigger_no_follow", "b_range", "c_drop")} if cls_cfg is not None and not m.empty else {}
            ),
            "n_unclassifiable": int((m["counterexample_kind_effective"] == "unclassifiable").sum()) if not m.empty else 0,
        },
        "manifest": {"horizon_bars": horizon, "label_threshold": thr_label, "direction": manifest_config.get("direction", "long"),
                     "decision_offset_bars": k, "score_threshold": score_thr, "top_q": top_q, "entry_price_semantic": entry_semantic,
                     "index": "decision_at_ms", "eligibility": "label_window_complete ∧ grid_continuous ∧ prices_finite_positive ∧ warmup_ok"},
        "receipts": {"seed": seed, "n_boot": n_boot},
    }
    # AR-3 共同約束欄（B2 全批共同；三家 R1 同抓）：缺 split plan ⇒ formal_pooled_inference_allowed=False 揭露
    from momentum.Analysis.event_samples.tables import _common_constraint_block
    out["common"] = _common_constraint_block(event_split_plan, manifest)
    # CODEX-R2-P1-01：共同欄須含**實際** macro／micro／cluster-CI 數值（非只旗標）
    if not m.empty and m["y"].nunique() >= 2:
        yv, sv = m["y"].to_numpy(), m["score"].to_numpy()
        cl = m["time_cluster_id"].to_numpy()

        def _auc_sel(sel):
            if len(np.unique(yv[sel])) < 2:
                return None
            return float(roc_auc_score(yv[sel], sv[sel]))

        per_sym = [v["auc"] for v in out["strata"]["by_symbol"].values() if v.get("capability_status") == "ok"]
        out["common"]["macro_auc"] = float(np.mean(per_sym)) if per_sym else float("nan")   # symbol 等權
        out["common"]["micro_auc"] = float(roc_auc_score(yv, sv))                            # bar 等權（pooled）
        out["common"]["auc_cluster_ci"] = _cluster_bootstrap_stat(_auc_sel, cl, seed=seed, n_boot=n_boot)
        out["common"]["n_time_clusters"] = int(len(np.unique(cl)))
    else:
        out["common"].update({"macro_auc": None, "micro_auc": None, "auc_cluster_ci": {"status": "unavailable"}, "n_time_clusters": 0})
    assert counts["n_total"] == counts["n_eligible"] + counts["n_unknown"] + counts["n_tail_excluded"]
    assert counts["n_eligible"] == counts["n_labeled"] + counts["n_missing"]
    return out
