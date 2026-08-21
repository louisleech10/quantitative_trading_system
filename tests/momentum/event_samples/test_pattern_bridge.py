"""Task B4.1 驗證：train/test 隔離斷言（fit 只見 train 列、無 sample_weight）；split 缺 ⇒ fail-closed；
置亂 oracle 沿用（shuffled label ⇒ test AUC 落帶內）；test one-class ⇒ unavailable；J8 粗篩；survivor v2 限縮；AR-3 common 欄。
合成的是因子／label 序列（章程 §F），非價格。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.event_samples import pattern_bridge as pb
from momentum.Analysis.event_samples.pattern_bridge import BridgeConfig, PatternSplitRequiredError, extract_event_patterns
from momentum.Analysis.event_samples.types import EventManifest, EventSplitPlan

SEED = 20260821


def synth(n=400, n_feat=4, planted=True, seed=SEED):
    """planted pattern：f0 > 0.5 ∧ f1 < 0 ⇒ P(y=1)=0.9，否則 0.2。"""
    rng = np.random.default_rng(seed)
    ids = [f"e{i:04d}" for i in range(n)]
    X = pd.DataFrame(rng.normal(size=(n, n_feat)), index=ids, columns=[f"f{j}" for j in range(n_feat)])
    if planted:
        p = np.where((X["f0"] > 0.5) & (X["f1"] < 0), 0.9, 0.2)
    else:
        p = np.full(n, 0.4)
    y = pd.Series((rng.uniform(size=n) < p).astype(int), index=ids)
    n_tr = int(n * 0.7)
    plan = EventSplitPlan(
        assignments=pd.DataFrame({"event_id": ids, "symbol": "S", "split_label": ["train"] * n_tr + ["test"] * (n - n_tr)}),
        purged=pd.DataFrame(), clusters=pd.DataFrame(),
        summary={"stats_modes": {"primary": "macro", "sensitivity": "micro"}, "degraded": ["single_symbol"],
                 "loso_status": "not_evaluated", "n_symbols": 1},
    )
    manifest = EventManifest(table=pd.DataFrame({"event_id": ids, "in_primary": True}), summary={"n_events_raw": n, "n_events_effective": n}, policy={"primary": "cluster_first"})
    return X, y, plan, manifest


def cfg(**over):
    base = dict(top_n_rules=5, min_support=5, n_estimators=30, max_depth=3, seed=SEED, n_perm=200)
    base.update(over)
    return BridgeConfig(**base)


def test_happy_path_rules_and_test_score():
    X, y, plan, MAN = synth()
    rep = extract_event_patterns(X, y, plan, None, cfg(), manifest=MAN)
    assert rep["capability_status"] == "ok" and rep["statistic_kind"] == "pattern_bridge"
    assert rep["n_train"] == 280 and rep["n_test"] == 120
    assert len(rep["rules"]) >= 1
    feats = {fc["feature"] for r in rep["rules"] for fc in r["feature_conditions"]}
    assert feats & {"f0", "f1"}                                         # 規則命中 planted 特徵
    td = rep["test_discrimination"]
    assert td["overall"]["capability_status"] == "ok" and td["overall"]["auc"] > td["overall"]["auc_band"][1]
    assert rep["receipt"]["sample_weight_used"] is False and rep["receipt"]["fit_scope"] == "event_train_only"
    assert set(rep["common"]) >= {"degraded", "formal_pooled_inference_allowed", "loso_status", "stats_modes"}
    assert rep["common"]["formal_pooled_inference_allowed"] is False      # degraded:single_symbol


def test_split_missing_fail_closed_no_fallback():
    X, y, _, MAN = synth()
    with pytest.raises(PatternSplitRequiredError):
        extract_event_patterns(X, y, None, None, cfg(), manifest=MAN)
    empty_plan = EventSplitPlan(assignments=pd.DataFrame(), purged=pd.DataFrame(), clusters=pd.DataFrame(), summary={})
    with pytest.raises(PatternSplitRequiredError):
        extract_event_patterns(X, y, empty_plan, None, cfg(), manifest=MAN)
    # 全 test、無 train ⇒ 拒（不 fallback 全樣本）
    X2, y2, plan2, MAN2 = synth()
    plan2.assignments["split_label"] = "test"
    with pytest.raises(PatternSplitRequiredError):
        extract_event_patterns(X2, y2, plan2, None, cfg(), manifest=MAN2)


def test_train_test_isolation_fit_sees_only_train_rows(monkeypatch):
    """fit 只見 train 列（列數＋索引集合）且未傳 sample_weight；score 只在 test 段。"""
    import xgboost as xgb
    X, y, plan, MAN = synth()
    seen = {}
    orig_fit = xgb.XGBClassifier.fit

    def spy(self, Xf, yf, *a, **kw):
        seen["n"] = len(Xf)
        seen["idx"] = set(Xf.index)
        seen["kw"] = dict(kw)
        seen["has_sw"] = ("sample_weight" in kw) or (len(a) > 0)
        return orig_fit(self, Xf, yf, *a, **kw)

    monkeypatch.setattr(xgb.XGBClassifier, "fit", spy)
    rep = extract_event_patterns(X, y, plan, None, cfg(), manifest=MAN)
    train_ids = set(plan.assignments.loc[plan.assignments["split_label"] == "train", "event_id"])
    test_ids = set(plan.assignments.loc[plan.assignments["split_label"] == "test", "event_id"])
    assert seen["n"] == len(train_ids) and seen["idx"] == train_ids and not (seen["idx"] & test_ids)
    assert seen["has_sw"] is False
    assert rep["test_discrimination"]["overall"]["n"] == len(test_ids)


def test_shuffled_labels_auc_in_permutation_band():
    """置亂 oracle 沿用（B1.4 定式）：label 置亂 ⇒ test AUC 落帶內、規則 test_lift 無系統性優勢。"""
    X, y, plan, MAN = synth()
    rng = np.random.default_rng(SEED)
    y_sh = pd.Series(rng.permutation(y.to_numpy()), index=y.index)
    rep = extract_event_patterns(X, y_sh, plan, None, cfg(), manifest=MAN)
    td = rep["test_discrimination"]["overall"]
    assert td["capability_status"] == "ok" and td["auc_in_band"] is True


def test_test_one_class_unavailable():
    X, y, plan, MAN = synth()
    test_ids = plan.assignments.loc[plan.assignments["split_label"] == "test", "event_id"]
    y2 = y.copy()
    y2.loc[test_ids] = 1
    rep = extract_event_patterns(X, y2, plan, None, cfg(), manifest=MAN)
    assert rep["test_discrimination"]["overall"]["capability_status"] == "unavailable"


def test_j8_ic_prescreen_train_only():
    X, y, plan, MAN = synth(n=200, n_feat=60)                                   # train 140 // 10 ⇒ cap 14 < 60
    rep = extract_event_patterns(X, y, plan, None, cfg(min_support=3), manifest=MAN)
    ps = rep["ic_prescreen"]
    assert ps["applied"] is True and ps["cap"] == 14 and len(ps["kept"]) == 14 and rep["n_features_used"] == 14
    assert "f0" in ps["kept"] and ps["statistic"] == "abs_point_biserial_train_only"
    # 粗篩只看 train：把 test 段 f59 改成與 label 完全相同，仍不得入選
    X2 = X.copy()
    test_ids = plan.assignments.loc[plan.assignments["split_label"] == "test", "event_id"]
    X2.loc[test_ids, "f59"] = y.loc[test_ids].astype(float) * 10
    rep2 = extract_event_patterns(X2, y, plan, None, cfg(min_support=3), manifest=MAN)
    assert "f59" not in rep2["ic_prescreen"]["kept"]


def test_survivor_v2_restricts_features_and_v1_rejected():
    X, y, plan, MAN = synth()
    sv = {"schema_version": 2, "survivors": [{"feature_name": "f0"}, {"feature_name": "f1"}, {"feature_name": "ghost"}]}
    rep = extract_event_patterns(X, y, plan, sv, cfg(), manifest=MAN)
    assert rep["feature_names_used"] == ["f0", "f1"] and rep["survivor_restricted"] is True
    with pytest.raises(ValueError):
        extract_event_patterns(X, y, plan, {"schema_version": 1, "survivors": [{"feature_name": "f0"}]}, cfg(), manifest=MAN)
    with pytest.raises(ValueError):
        extract_event_patterns(X, y, plan, {"schema_version": 2, "survivors": []}, cfg(), manifest=MAN)


def test_labels_and_inputs_guards():
    X, y, plan, MAN = synth()
    with pytest.raises(ValueError):
        extract_event_patterns(X, y.replace({1: 2}), plan, None, cfg(), manifest=MAN)
    with pytest.raises(ValueError):
        extract_event_patterns(X.iloc[0:0], y, plan, None, cfg(), manifest=MAN)
    # train 單類別 ⇒ loud
    y3 = y.copy()
    tr = plan.assignments.loc[plan.assignments["split_label"] == "train", "event_id"]
    y3.loc[tr] = 0
    with pytest.raises(ValueError):
        extract_event_patterns(X, y3, plan, None, cfg(), manifest=MAN)


def test_receipt_deterministic():
    X, y, plan, MAN = synth()
    a = extract_event_patterns(X, y, plan, None, cfg(), manifest=MAN)
    b = extract_event_patterns(X, y, plan, None, cfg(), manifest=MAN)
    assert a["receipt"]["train_plan_hash"] == b["receipt"]["train_plan_hash"]
    assert a["receipt"]["train_ids_sha256"] == b["receipt"]["train_ids_sha256"]
    assert [r["condition"] for r in a["rules"]] == [r["condition"] for r in b["rules"]]
    assert pb.SURVIVOR_SCHEMA_VERSION_REQUIRED == 2


def test_manifest_required_fail_closed_and_common_n():
    """CODEX-R1-P1-01 RECHECK：cluster manifest 為 AR-3 必需輸入——缺／空／無 n 欄 ⇒ 拒；有 ⇒ common raw/effective n 實值。"""
    X, y, plan, MAN = synth()
    with pytest.raises(TypeError):
        extract_event_patterns(X, y, plan, None, cfg())                      # keyword 必填
    with pytest.raises(ValueError):
        extract_event_patterns(X, y, plan, None, cfg(), manifest=None)      # type: ignore[arg-type]
    with pytest.raises(ValueError):
        extract_event_patterns(X, y, plan, None, cfg(), manifest=EventManifest(table=pd.DataFrame(), summary={"n_events_raw": 1, "n_events_effective": 1}, policy={}))
    with pytest.raises(ValueError):
        extract_event_patterns(X, y, plan, None, cfg(), manifest=EventManifest(table=MAN.table, summary={}, policy={}))
    rep = extract_event_patterns(X, y, plan, None, cfg(), manifest=MAN)
    assert rep["common"]["n_events_raw"] == 400 and rep["common"]["n_events_effective"] == 400
    assert rep["test_discrimination"]["common"]["n_events_raw"] == 400
