"""GAP-3 單特徵二元 baseline＋自檢 oracle 載體（docs/GAP3_EVENT_TODO.md Task B1.4；R1 C5-2）。

chance-level oracle＝permutation quantile（SPEC R2 Y5／R3 Z4 定式）：固定 seed、
N_perm=1000、經驗分位帶；三道硬檢——(i) 置亂分布非退化（variance>0 且 n_unique>1，
否則 oracle 自身 FAIL）(ii) 至少一排列 ≠ identity（seed＋排列 digest 寫 receipt）
(iii) 帶判定用經驗分位。oracle 計算核心以 statistic_kind 參數化
（AUC null 中心 0.5／PR-AUC null 中心＝prevalence／IC null 中心 0），供 B2.2/B2.3 重用（W3）。
"""

from __future__ import annotations

import hashlib
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from momentum.Analysis.event_samples.types import EventSplitPlan, OracleConfig


def _permute(rng: np.random.Generator, y: np.ndarray) -> np.ndarray:
    """單次置亂（獨立小函式供 M8 mutation guard monkeypatch——恆等排列必被硬檢攔）。"""
    return rng.permutation(y)


def permutation_oracle(
    values: np.ndarray,
    y: np.ndarray,
    stat_fn: Callable[[np.ndarray, np.ndarray], float],
    oracle_config: OracleConfig,
) -> Dict:
    """對 stat_fn(values, y) 建 permutation quantile 帶＋三道硬檢；回 band/observed/receipt。"""
    rng = np.random.default_rng(oracle_config.seed)
    observed = float(stat_fn(values, y))
    perm_stats = np.empty(oracle_config.n_perm, dtype=float)
    any_non_identity = False
    first_perm_digest = None
    for i in range(oracle_config.n_perm):
        yp = _permute(rng, y)
        if first_perm_digest is None:
            first_perm_digest = hashlib.sha256(yp.tobytes()).hexdigest()
        if not np.array_equal(yp, y):
            any_non_identity = True
        perm_stats[i] = stat_fn(values, yp)

    # 硬檢 (i)：分布非退化；(ii)：非恆等——違反＝oracle 自身 FAIL（「觀測值∈觀測值」假綠封死）
    if not (np.nanvar(perm_stats) > 0.0 and len(np.unique(perm_stats[~np.isnan(perm_stats)])) > 1):
        raise ValueError("permutation oracle degenerate: variance==0 or n_unique<=1（硬檢 i）")
    if not any_non_identity:
        raise ValueError("permutation oracle identity-only permutations（硬檢 ii）")

    lo = float(np.nanquantile(perm_stats, oracle_config.q_low))   # 硬檢 (iii)：經驗分位
    hi = float(np.nanquantile(perm_stats, oracle_config.q_high))
    # 雙尾經驗 p（供 BH-FDR）
    p = float(min(1.0, 2.0 * min(
        (1 + np.sum(perm_stats >= observed)) / (oracle_config.n_perm + 1),
        (1 + np.sum(perm_stats <= observed)) / (oracle_config.n_perm + 1),
    )))
    return {
        "observed": observed, "band_low": lo, "band_high": hi,
        "in_band": bool(lo <= observed <= hi), "p_value": p,
        "receipt": {"seed": oracle_config.seed, "n_perm": oracle_config.n_perm,
                    "first_permutation_digest": first_perm_digest},
    }


def _bh_fdr(pvals: List[float]) -> List[float]:
    """Benjamini–Hochberg q 值（單調校正）。"""
    n = len(pvals)
    order = np.argsort(pvals)
    q = np.empty(n, dtype=float)
    prev = 1.0
    for rank_pos in range(n - 1, -1, -1):
        i = order[rank_pos]
        val = min(prev, pvals[i] * n / (rank_pos + 1))
        q[i] = val
        prev = val
    return q.tolist()


def single_feature_binary_baseline(
    features_at_decision: pd.DataFrame,
    labels: pd.Series,
    event_split_plan: EventSplitPlan,
    *,
    oracle_config: OracleConfig,
    feature_manifest_hash: Optional[str],
) -> Dict:
    """對每特徵單獨算 OOS AUC/PR-AUC（test 段 only）＋BH-FDR＋permutation 帶。

    features_at_decision：index=event_id、columns=特徵；labels：index=event_id 之 0/1。
    one-class test 段 ⇒ capability unavailable:one_class_test_segment。
    任何非有限值（NaN/inf）⇒ loud 拒（CODEX-R1-P1-06：上游 B1.6 已保證無 NaN 混入，
    此處出現即契約破缺，不做 pairwise 靜默刪列）。
    feature_manifest_hash（CODEX-R1-P2-07）：B1.6 產出之 provenance，寫入 report receipts。
    """
    if not isinstance(feature_manifest_hash, str) or len(feature_manifest_hash) != 64:
        # CODEX-R2-P2-02：provenance 不可省略——缺 hash fail-closed
        raise ValueError("single_feature_binary_baseline: feature_manifest_hash 須為 64 位 sha256（B1.6 產出），缺則 fail-closed")
    test_ids = event_split_plan.assignments.loc[
        event_split_plan.assignments["split_label"] == "test", "event_id"
    ]
    idx = features_at_decision.index.intersection(pd.Index(test_ids))
    X = features_at_decision.loc[idx]
    y = labels.loc[idx].astype(int).to_numpy()

    # CODEX-R2-P2-01：有限值閘前移——在 one-class 分支之前，NaN 不得被誤報為 one_class_test_segment
    Xv = X.to_numpy(dtype=float)
    if Xv.size and not np.isfinite(Xv).all():
        bad = [c for c in X.columns if not np.isfinite(X[c].to_numpy(dtype=float)).all()]
        raise ValueError(f"single_feature_binary_baseline: 特徵含非有限值（NaN/inf）loud 拒——{bad}")

    report: Dict = {
        "statistic_kind": "binary_discrimination",
        "n_test": int(len(idx)),
        "prevalence": float(y.mean()) if len(y) else float("nan"),
        "receipts": {
            "seed": oracle_config.seed, "n_perm": oracle_config.n_perm,
            "feature_manifest_hash": feature_manifest_hash,
        },
    }
    if len(np.unique(y)) < 2:
        report["capability_status"] = "unavailable"
        report["reason"] = "one_class_test_segment"
        report["features"] = {}
        return report

    feats: Dict[str, Dict] = {}
    pvals: List[float] = []
    names: List[str] = []
    for col in features_at_decision.columns:
        vv, yy = X[col].to_numpy(dtype=float), y
        if len(np.unique(yy)) < 2:
            feats[col] = {"capability_status": "unavailable", "reason": "one_class_test_segment"}
            continue

        def _auc(values: np.ndarray, yy_: np.ndarray) -> float:
            return float(roc_auc_score(yy_, values))

        o_auc = permutation_oracle(vv, yy, _auc, oracle_config)
        o_pr = permutation_oracle(vv, yy, lambda values, yy_: float(average_precision_score(yy_, values)), oracle_config)
        feats[col] = {
            "auc": o_auc["observed"], "auc_band": [o_auc["band_low"], o_auc["band_high"]],
            "auc_in_band": o_auc["in_band"], "p_value": o_auc["p_value"],
            "pr_auc": o_pr["observed"], "pr_auc_band": [o_pr["band_low"], o_pr["band_high"]],
            "pr_auc_in_band": o_pr["in_band"],
            "permutation_digest": o_auc["receipt"]["first_permutation_digest"],
            "n_used": int(len(vv)),
        }
        pvals.append(o_auc["p_value"])
        names.append(col)

    for name, q in zip(names, _bh_fdr(pvals)):
        feats[name]["q_value"] = q
    report["capability_status"] = "ok"
    report["features"] = feats
    return report
