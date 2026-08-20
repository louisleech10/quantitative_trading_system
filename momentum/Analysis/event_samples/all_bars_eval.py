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

from momentum.Analysis.event_samples.counterexample_classifier import _classify_one


def _is_eligible(i: int, n: int, horizon: int, k: int, open_: np.ndarray, close: np.ndarray) -> Optional[str]:
    """回 None＝eligible，否則 reason。獨立小函式供 mutation guard（M4 分母竄改）monkeypatch。"""
    if i - k < 0:
        return "warmup_insufficient"
    if i + horizon >= n:
        return "label_window_incomplete"
    seg_o = open_[i - k: i + horizon + 1]
    seg_c = close[i - k: i + horizon + 1]
    if not (np.isfinite(seg_o).all() and np.isfinite(seg_c).all() and (seg_o > 0).all() and (seg_c > 0).all()):
        return "nonpositive_reference_price"
    return None


def _label_from_rule(direction_sign: float, close: np.ndarray, i: int, horizon: int, threshold: float) -> int:
    """標籤規則（close_to_close）：dir·(close[i+h]/close[i]−1) ≥ threshold ⇒ 1。"""
    r = direction_sign * (close[i + horizon] / close[i] - 1.0)
    return int(r >= threshold)


def evaluate_all_bars(
    model_scores_or_rule: Union[pd.Series, Callable[[pd.DataFrame], pd.Series]],
    bars: Dict[str, pd.DataFrame],
    manifest_config: dict,
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
        if callable(model_scores_or_rule):
            scores = model_scores_or_rule(df)
            scores = pd.Series(np.asarray(scores, dtype=float), index=ot)
        else:
            s = model_scores_or_rule
            scores = s.xs(symbol, level=0) if isinstance(s.index, pd.MultiIndex) else s
        for i in range(n):
            counts["n_total"] += 1
            reason = _is_eligible(i, n, horizon, k, open_, close)
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
            # 實際持有報酬：決策列 open → 答案窗末 close（D1-4 並排）
            hold = sign * (close[i + horizon] - open_[i - k]) / open_[i - k]
            kind = None
            if cls_cfg is not None and y == 0:
                r0 = sign * (close[i] - open_[i]) / open_[i]
                rw = sign * (close[i + horizon] - close[i]) / close[i]
                kind = _classify_one(r0, rw, cls_cfg)
            rows.append({
                "symbol": symbol, "decision_at_ms": decision_ms, "t0_ms": int(ot[i]), "score": float(sc), "y": y,
                "hold_return": hold, "period": pd.Timestamp(int(ot[i]), unit="ms", tz="UTC").strftime("%Y-%m"),
                "counterexample_kind_effective": kind, "label_id": label_id,
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
                     "decision_offset_bars": k, "score_threshold": score_thr, "top_q": top_q,
                     "index": "decision_at_ms", "eligibility": "label_window_complete ∧ prices_finite_positive ∧ warmup_ok"},
        "receipts": {"seed": seed, "n_boot": n_boot},
    }
    assert counts["n_total"] == counts["n_eligible"] + counts["n_unknown"] + counts["n_tail_excluded"]
    assert counts["n_eligible"] == counts["n_labeled"] + counts["n_missing"]
    return out
