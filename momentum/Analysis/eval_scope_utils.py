"""LA-2 B2：model_performance eval_scope 組裝與 OOT OMITTED 契約。

供 analyzer / service 共用，避免各造 dict。
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from momentum.core.contracts import (
    EVAL_SCOPE_CONSUMER_DENY,
    MODEL_PERFORMANCE_EVAL_SCOPE,
    OMITTED_METRIC,
    tag_model_performance_scopes,
)


def performance_to_scoped_dict(performance: Any) -> Dict[str, Any]:
    """ModelPerformance → dict，rename 已完成時直接 asdict + eval_scope。"""
    if is_dataclass(performance):
        raw = asdict(performance)
    elif isinstance(performance, dict):
        raw = dict(performance)
    else:
        raw = dict(getattr(performance, "__dict__", {}))

    # 禁 train_auc 並存
    if "train_auc" in raw and "in_sample_train_auc" not in raw:
        raw["in_sample_train_auc"] = raw.pop("train_auc")
    else:
        raw.pop("train_auc", None)

    return tag_model_performance_scopes(raw)


def mark_oot_omitted(model_performance: Dict[str, Any]) -> Dict[str, Any]:
    """缺 held-out → oot 指標 OMITTED + consumer deny（非 silent 全樣本）。"""
    out = dict(model_performance)
    out["oot_auc"] = None
    out["oot_status"] = OMITTED_METRIC
    scopes = dict(out.get("eval_scope") or {})
    scopes["oot_auc"] = "oot"
    out["eval_scope"] = scopes
    deny = set(out.get("consumer_deny") or [])
    deny.add("oot_auc")  # OMITTED 亦 deny 晉升
    out["consumer_deny"] = sorted(deny)
    out["metrics_omitted"] = list(
        dict.fromkeys([*(out.get("metrics_omitted") or []), "oot_auc", "precision_at_k", "recommend_k"])
    )
    return out


def apply_service_matrix_scopes(
    result: Dict[str, Any],
    *,
    has_oot_held_out: bool,
) -> Dict[str, Any]:
    """service 全矩陣逐欄 scope（§0.6-C）。

    - model_performance nested + top-level 對照（migration）
    - recommend_k / precision@K / expectancy / bootstrap → oot（無 held-out → OMITTED）
    - importance / shap / regime / cross_symbol → in_sample_research_only + deny
    - cal/PR → cv_oof
    """
    out = dict(result)

    mp = out.get("model_performance")
    if isinstance(mp, dict):
        mp = performance_to_scoped_dict(mp)
        if not has_oot_held_out:
            mp = mark_oot_omitted(mp)
        out["model_performance"] = mp

    # nested under model_performance for canonical paths（保留 top-level 對照）
    nested = dict(out.get("model_performance") or {})
    field_scopes: Dict[str, str] = dict(nested.get("eval_scope") or {})
    consumer_deny: List[str] = list(nested.get("consumer_deny") or [])

    def _scope(key: str, path_key: Optional[str] = None) -> str:
        pk = path_key or key
        if pk not in MODEL_PERFORMANCE_EVAL_SCOPE:
            raise ValueError(
                f"unknown eval_scope metric not in 28-path canonical set: {pk}"
            )
        return MODEL_PERFORMANCE_EVAL_SCOPE[pk]

    # top-level → scope tags（migration map）
    top_scope_map = {
        "feature_importance": "feature_importance",
        "feature_importance_all": "feature_importance_all",
        "permutation_importance": "permutation_importance",
        "fold_importance_stability": "fold_importance_stability",
        "shap_sample": "shap_sample",
        "regime_analysis": "regime_analysis",
        "cross_symbol_validation": "cross_symbol_validation",
        "calibration_curve": "calibration_curve",
        "pr_curve": "pr_curve",
        "precision_at_k": "precision_at_k",
        "bootstrap_ci": "bootstrap_ci",
        "expectancy": "expectancy",
    }

    matrix_scopes: Dict[str, str] = {}
    matrix_deny: List[str] = []

    for top_key, scope_key in top_scope_map.items():
        if top_key not in out or out[top_key] is None:
            continue
        scope = _scope(scope_key)
        matrix_scopes[top_key] = scope
        if scope == "in_sample_research_only" or scope_key in EVAL_SCOPE_CONSUMER_DENY:
            matrix_deny.append(top_key)
        # nest into model_performance for canonical path
        if top_key in {
            "feature_importance",
            "feature_importance_all",
            "permutation_importance",
            "fold_importance_stability",
            "shap_sample",
            "regime_analysis",
            "cross_symbol_validation",
            "calibration_curve",
            "pr_curve",
            "precision_at_k",
            "bootstrap_ci",
        }:
            nested[top_key] = out[top_key]
            field_scopes[scope_key] = scope

    # recommend_k / expectancy / sharpe → oot（F8：None 表示源頭未算全樣本）
    if "precision_at_k" in out:
        if not has_oot_held_out or out["precision_at_k"] is None:
            pak = {
                "status": OMITTED_METRIC,
                "reason": "no_held_out_oot",
                "eval_scope": "oot",
                "consumer": "deny",
            }
            out["precision_at_k"] = pak
            nested["precision_at_k"] = pak
        elif isinstance(out["precision_at_k"], dict):
            pak = dict(out["precision_at_k"])
            pak["eval_scope"] = "oot"
            out["precision_at_k"] = pak
            nested["precision_at_k"] = pak
        matrix_scopes["precision_at_k"] = "oot"
        matrix_scopes["recommend_k"] = "oot"
        field_scopes["precision_at_k"] = "oot"
        field_scopes["recommend_k"] = "oot"

    if "expectancy" in out:
        if not has_oot_held_out or out["expectancy"] is None:
            out["expectancy"] = {
                "status": OMITTED_METRIC,
                "reason": "no_held_out_oot",
                "eval_scope": "oot",
                "consumer": "deny",
            }
        elif isinstance(out["expectancy"], dict):
            exp = dict(out["expectancy"])
            exp["eval_scope"] = "oot"
            if "sharpe_proxy" in exp:
                exp["sharpe_proxy_eval_scope"] = "oot"
            out["expectancy"] = exp
        matrix_scopes["expectancy"] = "oot"
        matrix_scopes["sharpe_proxy"] = "oot"
        field_scopes["expectancy"] = "oot"
        field_scopes["sharpe_proxy"] = "oot"
        nested["expectancy"] = out["expectancy"]

    if "bootstrap_ci" in out:
        if not has_oot_held_out or out["bootstrap_ci"] is None:
            out["bootstrap_ci"] = {
                "status": OMITTED_METRIC,
                "reason": "no_held_out_oot",
                "eval_scope": "oot",
                "consumer": "deny",
            }
        elif isinstance(out["bootstrap_ci"], dict):
            bc = dict(out["bootstrap_ci"])
            bc["eval_scope"] = "oot"
            out["bootstrap_ci"] = bc
        matrix_scopes["bootstrap_ci"] = "oot"
        field_scopes["bootstrap_ci"] = "oot"
        nested["bootstrap_ci"] = out["bootstrap_ci"]

    # predictions train/oot 分列
    if "predictions" in out:
        preds = out["predictions"]
        if not has_oot_held_out:
            nested_preds = {
                "train": preds,
                "oot": {"status": OMITTED_METRIC, "reason": "no_held_out_oot"},
                "eval_scope": {
                    "train": "in_sample_research_only",
                    "oot": "oot",
                },
            }
        else:
            nested_preds = {
                "train": preds.get("train") if isinstance(preds, dict) else None,
                "oot": preds.get("oot") if isinstance(preds, dict) else preds,
                "eval_scope": {
                    "train": "in_sample_research_only",
                    "oot": "oot",
                },
            }
        nested["predictions"] = nested_preds
        matrix_scopes["predictions/train"] = "in_sample_research_only"
        matrix_scopes["predictions/oot"] = "oot"
        field_scopes["predictions/train"] = "in_sample_research_only"
        field_scopes["predictions/oot"] = "oot"
        matrix_deny.append("predictions/train")
        consumer_deny.append("predictions/train")

    # research_only deny tags on importance family
    for deny_key in (
        "feature_importance",
        "feature_importance_all",
        "permutation_importance",
        "shap_sample",
        "regime_analysis",
        "cross_symbol_validation",
    ):
        if deny_key in out and isinstance(out[deny_key], dict):
            tagged = dict(out[deny_key])
            tagged["eval_scope"] = "in_sample_research_only"
            tagged["consumer"] = "deny"
            out[deny_key] = tagged
        elif deny_key in out and isinstance(out[deny_key], list):
            # wrap list payloads
            out[deny_key] = {
                "items": out[deny_key],
                "eval_scope": "in_sample_research_only",
                "consumer": "deny",
            }
        if deny_key in out:
            matrix_deny.append(deny_key)
            consumer_deny.append(deny_key)

    if "fold_importance_stability" in out:
        matrix_scopes["fold_importance_stability"] = "cv_oof"
        field_scopes["fold_importance_stability"] = "cv_oof"

    if "calibration_curve" in out and out["calibration_curve"] is not None:
        matrix_scopes["calibration_curve"] = "cv_oof"
        field_scopes["calibration_curve"] = "cv_oof"
    if "pr_curve" in out and out["pr_curve"] is not None:
        if isinstance(out["pr_curve"], dict):
            pr = dict(out["pr_curve"])
            pr["eval_scope"] = "cv_oof"
            out["pr_curve"] = pr
        matrix_scopes["pr_curve"] = "cv_oof"
        field_scopes["pr_curve"] = "cv_oof"

    nested["eval_scope"] = field_scopes
    nested["consumer_deny"] = sorted(set(consumer_deny) | set(matrix_deny))
    out["model_performance"] = nested
    out["matrix_eval_scope"] = matrix_scopes
    out["matrix_consumer_deny"] = sorted(set(matrix_deny))

    # old→new migration map（U13）
    out["field_migration"] = {
        "/model_performance/train_auc": "/model_performance/in_sample_train_auc",
    }
    return out


def build_service_oot_bundle(
    *,
    n_samples: int,
    model_artifact: bytes,
    trusted_issuer: str,
    oot_ratio: float = 0.2,
    horizon: int = 1,
    embargo: int = 0,
    purge_gap: int = 0,
    symbol: str | None = None,
    base_universe_hash: str = "service_run",
) -> dict:
    """service 共用：建 train/OOT SplitPlan + OotReceipt envelope（有 held-out 時）。

    回傳 dict:
      has_oot_held_out: bool
      train_plan / eval_plan: SplitPlan | None
      oot_receipt: envelope dict | None
      train_idx / oot_idx: np.ndarray | None
      horizon: int
    """
    from momentum.core.contracts import (
        build_receipt_envelope,
        build_train_oot_split_plans,
        make_oot_receipt,
    )

    plans = build_train_oot_split_plans(
        n_samples,
        oot_ratio=oot_ratio,
        horizon=horizon,
        embargo=embargo,
        purge_gap=purge_gap,
        symbol=symbol,
        base_universe_hash=base_universe_hash,
    )
    if plans is None:
        return {
            "has_oot_held_out": False,
            "train_plan": None,
            "eval_plan": None,
            "oot_receipt": None,
            "train_idx": None,
            "oot_idx": None,
            "horizon": int(horizon),
        }
    train_plan, eval_plan = plans
    receipt = make_oot_receipt(
        train_plan,
        eval_plan,
        horizon=int(horizon),
        model_artifact=model_artifact,
        trusted_issuer=trusted_issuer,
        embargo=int(embargo),
    )
    envelope = build_receipt_envelope("oot", receipt)
    return {
        "has_oot_held_out": True,
        "train_plan": train_plan,
        "eval_plan": eval_plan,
        "oot_receipt": envelope,
        "train_idx": np.asarray(train_plan.row_index, dtype=int),
        "oot_idx": np.asarray(eval_plan.row_index, dtype=int),
        "horizon": int(horizon),
    }

