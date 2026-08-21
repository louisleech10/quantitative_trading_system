"""GAP-3 pattern 橋（docs/GAP3_EVENT_TODO.md Task B4.1；SPEC J8：IC 粗篩 → ML 組合）。

消費既有 `momentum/Analysis/pattern_extractor.PatternExtractor`（**不改其簽名**、不動 `xgboost_batch_service` 訓練殼）：
- 訓練只在事件樣本 **train 段**（`EventSplitPlan.assignments.split_label=='train'`）；score 只在 **test 段**報。
- split 缺 ⇒ `PatternSplitRequiredError`（fail-closed，**不** fallback 全樣本）。
- `sample_weight` **不**接訓練（§N-4）；引擎 XGBoost（U8：引擎之選不影響契約）。
- J8：特徵數 > train 可撐（`train_n // rows_per_feature`）⇒ 以 **train-only** 點二系列相關（IC）粗篩先行。
- AR-3 共同約束：報告列 `common`（macro/micro/degraded/LOSO/formal_pooled_inference_allowed）；
  test 段辨別表復用 B2.2 `binary_discrimination_table`（含 B1.4 置亂 oracle）。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from momentum.core.contracts import SplitPlan, canonical_split_plan_hash
from momentum.core.logging import get_logger
from momentum.Analysis.event_samples.tables import _common_constraint_block, binary_discrimination_table
from momentum.Analysis.event_samples.types import EventManifest, EventSplitPlan
from momentum.Analysis.pattern_extractor import PatternExtractor, PatternSplitRequiredError

logger = get_logger(__name__)

SURVIVOR_SCHEMA_VERSION_REQUIRED = 2


@dataclass(frozen=True)
class BridgeConfig:
    """pattern 橋設定。

    rows_per_feature：J8 粗篩門檻——train_n // rows_per_feature 為可撐特徵數上限（超過 ⇒ IC 粗篩）。
    engine 固定 xgboost；`n_estimators`／`max_depth` 為研究參數（非契約）。
    """

    top_n_rules: int = 10
    min_support: int = 10
    rows_per_feature: int = 10
    n_estimators: int = 50
    max_depth: int = 3
    learning_rate: float = 0.1
    seed: int = 20260820
    n_perm: int = 300
    engine: str = "xgboost"


def _survivor_feature_names(survivor_v2: Optional[dict]) -> Optional[List[str]]:
    """自 B2.4 survivor v2 payload 取倖存特徵名；缺／版本錯 ⇒ loud。"""
    if survivor_v2 is None:
        return None
    if not isinstance(survivor_v2, dict) or int(survivor_v2.get("schema_version", -1)) != SURVIVOR_SCHEMA_VERSION_REQUIRED:
        raise ValueError(f"extract_event_patterns: survivor_v2 須為 schema_version={SURVIVOR_SCHEMA_VERSION_REQUIRED} payload")
    survivors = survivor_v2.get("survivors")
    if not isinstance(survivors, list):
        raise ValueError("extract_event_patterns: survivor_v2 缺 survivors[]")
    names = [str(s["feature_name"]) for s in survivors if isinstance(s, dict) and "feature_name" in s]
    if not names:
        raise ValueError("extract_event_patterns: survivor_v2.survivors 為空（無倖存特徵可組合）")
    return names


def _point_biserial_abs(x: np.ndarray, y: np.ndarray) -> float:
    """train-only IC 粗篩統計量：|corr(feature, label)|（NaN 列剔除；退化 ⇒ 0）。"""
    m = np.isfinite(x)
    if m.sum() < 3 or np.nanstd(x[m]) == 0 or np.std(y[m]) == 0:
        return 0.0
    return float(abs(np.corrcoef(x[m], y[m])[0, 1]))


def _split_plans(event_ids: Sequence[str], train_ids: set, test_ids: set) -> tuple:
    """由事件列序建 GAP-1 `SplitPlan`（index_kind=row_id；base_universe_hash＝事件 id 集 sha256）。"""
    universe = hashlib.sha256(json.dumps(sorted(event_ids)).encode("utf-8")).hexdigest()
    pos = {e: i for i, e in enumerate(event_ids)}
    tr = np.array(sorted(pos[e] for e in train_ids), dtype=int)
    te = np.array(sorted(pos[e] for e in test_ids), dtype=int)
    mk = lambda label, idx: SplitPlan(  # noqa: E731
        split_label=label, index_kind="row_id", row_index=idx,
        time_bounds=(int(idx.min()) if len(idx) else -1, int(idx.max()) if len(idx) else -1),
        purge_gap=0, embargo=0, purge_semantic="rows", base_universe_hash=universe,
    )
    return mk("train", tr), (mk("test", te) if len(te) else None)


def extract_event_patterns(
    features_at_decision: pd.DataFrame,
    labels: pd.Series,
    event_split_plan: Optional[EventSplitPlan],
    survivor_v2: Optional[dict],
    bridge_config: BridgeConfig,
    *,
    manifest: EventManifest,
    strata: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """在事件 train 段擬合多特徵組合、test 段評分。

    features_at_decision：index=event_id（B1.6 產出）；labels：index=event_id ∈ {0,1}。
    event_split_plan：B1.3 產出（必填；None ⇒ PatternSplitRequiredError）。
    manifest：B1.2 cluster manifest（**必填** keyword；AR-3 必需輸入——raw/effective n 來源；缺 ⇒ ValueError，CODEX-R1-P1-01）。
    survivor_v2：B2.4 payload（選用；給定 ⇒ 特徵候選限縮為倖存特徵）。
    strata：index=event_id，欄 `counterexample_kind_effective`（選用；反例分層非 AR-3 必需輸入，缺 ⇒ 分層空、overall 照算）。
    """
    if event_split_plan is None:
        raise PatternSplitRequiredError("extract_event_patterns: event_split_plan 必填（fail-closed；不 fallback 全樣本）")
    if not isinstance(manifest, EventManifest) or manifest.table is None or manifest.table.empty \
            or "n_events_raw" not in manifest.summary or "n_events_effective" not in manifest.summary:
        raise ValueError("extract_event_patterns: manifest（B1.2 cluster manifest）必填且須含 table＋summary.n_events_raw/effective（AR-3 必需輸入）")
    if not isinstance(features_at_decision, pd.DataFrame) or features_at_decision.empty:
        raise ValueError("extract_event_patterns: features_at_decision 為空")
    assign = event_split_plan.assignments
    if assign is None or assign.empty or "split_label" not in assign.columns:
        raise PatternSplitRequiredError("extract_event_patterns: split plan 無 assignments")

    labels = labels.astype(int)
    if not set(labels.unique()) <= {0, 1}:
        raise ValueError("extract_event_patterns: labels 須 ∈ {0,1}")

    ids = sorted(set(features_at_decision.index) & set(labels.index) & set(assign["event_id"]))
    if not ids:
        raise ValueError("extract_event_patterns: features／labels／split 無交集事件")
    lab_by_id = assign.set_index("event_id")["split_label"]
    train_ids = {e for e in ids if lab_by_id[e] == "train"}
    test_ids = {e for e in ids if lab_by_id[e] == "test"}
    if not train_ids:
        raise PatternSplitRequiredError("extract_event_patterns: train 段為空（fail-closed）")

    # ---- 特徵候選：survivor v2 限縮 → J8 粗篩（train-only）----
    cand = _survivor_feature_names(survivor_v2)
    feature_names = [c for c in features_at_decision.columns if (cand is None or c in cand)]
    if cand is not None:
        missing = sorted(set(cand) - set(features_at_decision.columns))
        if missing:
            logger.warning("extract_event_patterns: survivor 特徵不在特徵表 %s", missing)
    if not feature_names:
        raise ValueError("extract_event_patterns: 無可用特徵欄")

    X_all = features_at_decision.loc[ids, feature_names].astype(float)
    y_all = labels.loc[ids].to_numpy(dtype=int)
    train_mask = np.array([e in train_ids for e in ids])
    cap = max(1, len(train_ids) // int(bridge_config.rows_per_feature))
    prescreen = {"applied": False, "cap": cap, "n_before": len(feature_names), "kept": feature_names, "dropped": []}
    if len(feature_names) > cap:
        Xtr, ytr = X_all.to_numpy()[train_mask], y_all[train_mask]
        scores = {f: _point_biserial_abs(Xtr[:, j], ytr) for j, f in enumerate(feature_names)}
        kept = sorted(feature_names, key=lambda f: (-scores[f], f))[:cap]
        prescreen = {"applied": True, "cap": cap, "n_before": len(feature_names), "kept": kept,
                     "dropped": [f for f in feature_names if f not in kept], "statistic": "abs_point_biserial_train_only"}
        feature_names = kept
        X_all = X_all[feature_names]

    # ---- 訓練：只在 train 段；禁 sample_weight（§N-4）----
    import xgboost as xgb  # 引擎（U8）；延後 import 降低模組載入成本

    model = xgb.XGBClassifier(
        n_estimators=int(bridge_config.n_estimators), max_depth=int(bridge_config.max_depth),
        learning_rate=float(bridge_config.learning_rate), random_state=int(bridge_config.seed),
        n_jobs=1, verbosity=0, eval_metric="logloss",
    )
    X_train = X_all.iloc[np.flatnonzero(train_mask)]
    y_train = y_all[train_mask]
    if len(np.unique(y_train)) < 2:
        raise ValueError("extract_event_patterns: train 段單一類別，無法擬合（loud）")
    model.fit(X_train, y_train)  # 無 sample_weight

    train_plan, test_plan = _split_plans(ids, train_ids, test_ids)
    extractor = PatternExtractor()
    rules = extractor.extract_decision_rules(
        model, X_all, y_all, feature_names,
        top_n=int(bridge_config.top_n_rules), min_support=int(bridge_config.min_support),
        split=train_plan, oot_split=test_plan,
    )

    # ---- test 段：model score ＋ 規則命中（同 extractor 條件語意）----
    test_report: Dict[str, Any]
    rule_rows: List[Dict[str, Any]] = []
    if test_ids:
        te_pos = np.flatnonzero(~train_mask & np.array([e in test_ids for e in ids]))
        X_test = X_all.iloc[te_pos]
        y_test = y_all[te_pos]
        te_ids = [ids[i] for i in te_pos]
        scores_oos = pd.Series(model.predict_proba(X_test)[:, 1], index=te_ids)
        st = strata.reindex(te_ids) if strata is not None else pd.DataFrame({"counterexample_kind_effective": [None] * len(te_ids)}, index=te_ids)
        test_report = binary_discrimination_table(
            scores_oos, pd.Series(y_test, index=te_ids), event_split_plan, st,
            {"seed": int(bridge_config.seed), "n_perm": int(bridge_config.n_perm)}, manifest=manifest,
        )
        base_test = float(np.mean(y_test)) if len(y_test) else float("nan")
        for r in rules:
            hit = extractor._apply_conditions(X_test, feature_names, r.feature_conditions)
            n_hit = int(hit.sum())
            prec = float(np.mean(y_test[hit])) if n_hit else float("nan")
            rule_rows.append({**r.to_dict(), "test_n_hit": n_hit, "test_precision": prec,
                              "test_lift": (prec / base_test) if n_hit and base_test > 0 else float("nan")})
    else:
        test_report = {"capability_status": "unavailable", "reason": "no_test_segment"}
        rule_rows = [r.to_dict() for r in rules]

    out: Dict[str, Any] = {
        "statistic_kind": "pattern_bridge",
        "capability_status": "ok" if rules else "unavailable",
        "reason": None if rules else "no_rules_meeting_min_support",
        "engine": bridge_config.engine,
        "n_train": int(len(train_ids)), "n_test": int(len(test_ids)), "n_features_used": len(feature_names),
        "feature_names_used": list(feature_names),
        "ic_prescreen": prescreen,
        "survivor_restricted": cand is not None,
        "rules": rule_rows,
        "test_discrimination": test_report,
        "common": _common_constraint_block(event_split_plan, manifest),
        "receipt": {
            "seed": int(bridge_config.seed), "config": asdict(bridge_config),
            "train_plan_hash": canonical_split_plan_hash(train_plan),
            "train_ids_sha256": hashlib.sha256(json.dumps(sorted(train_ids)).encode("utf-8")).hexdigest(),
            "sample_weight_used": False, "fit_scope": "event_train_only",
        },
    }
    return out


__all__ = ["BridgeConfig", "extract_event_patterns", "PatternSplitRequiredError"]
