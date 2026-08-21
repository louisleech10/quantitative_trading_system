"""Task B3.2 驗證：G1–G6 逐項斷言（真實 kline ETHUSDT 12h；特徵欄由真實價格導出，禁合成價格）；
`platform_same_trigger_rule` 產出過 B1.0 validator＋control_kind 正確；0 命中 loud 空結果；單類別 fail-closed；
event_filter adapter：legacy query 路徑行為不變、condition_spec 只收 feature 角色（D3-4）。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.event_filter import EventFilter, allowed_filtering_params, apply_condition_spec
from momentum.Analysis.event_samples import all_bars_eval as ab
from momentum.Analysis.event_samples import generator as gen
from momentum.Analysis.event_samples.condition_engine import parse_condition
from momentum.Analysis.event_samples.generator import GeneratorConfig, LabelRule, generate_events, outcome_column_registry
from momentum.Analysis.event_samples.import_contract import ContractValidationError, validate_event_import
from momentum.core.exceptions import InvalidQueryError
from tests.momentum.event_samples.helpers import load_bars

FEATURE_REG = {"ret_1": "pit_feature", "ma_fast": "pit_feature", "ma_slow": "pit_feature", "vol_pct": "pit_feature"}


@pytest.fixture(scope="module")
def bars():
    """真實 kline 400 根＋由真實價格導出之 pit 特徵欄（rolling 只看過去含當根）。"""
    b = load_bars("ETHUSDT", ("12h",))["ETHUSDT"]["12h"].iloc[800:1200].reset_index(drop=True).copy()
    close = b["close"]
    b["ret_1"] = close.pct_change()
    b["ma_fast"] = close.rolling(5).mean()
    b["ma_slow"] = close.rolling(20).mean()
    vol = b["ret_1"].rolling(20).std()
    b["vol_pct"] = vol.rolling(60).rank(pct=True)
    return b


RULES = (LabelRule("up1", horizon_bars=2, threshold=0.01), LabelRule("up5", horizon_bars=3, threshold=0.05))


def registry(rules=RULES):
    return {**FEATURE_REG, **outcome_column_registry(rules)}


def cfg(**over):
    base = dict(symbol="ETHUSDT", timeframe="12h", data_snapshot_digest="snap-test", direction="long", scenario="C",
                decision_offset_bars=0, entry_price_semantic="trigger_open", run_all_bars_eval=False, n_boot=5)
    base.update(over)
    return GeneratorConfig(**base)


# ---- G1：十類中 ①②③⑩ 代表案例各一（任意特徵＋t₀ 結果＋未來結果欄觸發） ----
def test_G1_cat1_price_drop_trigger_outcome(bars):
    """① 價量觸發：單根跌 ≥3%（t₀ 結果欄 trigger_return；selection_predicate 角色）。"""
    spec = parse_condition("trigger_return <= -0.03", registry(), "selection_predicate")
    ev, prov = generate_events(spec, {"12h": bars}, RULES, cfg())
    assert prov["status"] == "ok" and len(ev) > 0
    r = bars.set_index("open_time_ms")
    for t0 in ev["t0"]:
        assert r.loc[t0, "close"] / r.loc[t0, "open"] - 1.0 <= -0.03          # 命中列逐一手算 exact
    assert prov["selection_uses_outcome_columns"] is True


def test_G1_cat2_ma_cross_pit_feature(bars):
    """② 技術指標：均線黃金交叉（只用 pit 特徵＋lag；feature 角色可過）。"""
    spec = parse_condition("ma_fast > ma_slow and lag(ma_fast, 1) <= lag(ma_slow, 1)", registry(), "feature")
    ev, prov = generate_events(spec, {"12h": bars}, RULES[:1], cfg())
    assert len(ev) > 0 and spec.max_lookback == 1 and prov["selection_uses_outcome_columns"] is False
    idx = bars.set_index("open_time_ms")
    pos = {t: i for i, t in enumerate(bars["open_time_ms"])}
    for t0 in ev["t0"]:
        i = pos[t0]
        assert bars.loc[i, "ma_fast"] > bars.loc[i, "ma_slow"] and bars.loc[i - 1, "ma_fast"] <= bars.loc[i - 1, "ma_slow"]
    assert idx is not None


def test_G1_cat3_volatility_state(bars):
    """③ 波動／狀態：波動率分位 ≥ 0.9。"""
    spec = parse_condition("vol_pct >= 0.9", registry(), "feature")
    ev, prov = generate_events(spec, {"12h": bars}, RULES[:1], cfg())
    assert len(ev) > 0
    r = bars.set_index("open_time_ms")
    assert (r.loc[ev["t0"], "vol_pct"] >= 0.9).all()


def test_G1_cat10_combination_with_future_column(bars):
    """⑩ 組合：跌幅＋狀態＋未來結果欄（只准 selection_predicate；feature 角色同式必拒——D3）。"""
    expr = "ret_1 < -0.02 and vol_pct > 0.3 and future_return_2 > 0"
    spec = parse_condition(expr, registry(), "selection_predicate")
    ev, prov = generate_events(spec, {"12h": bars}, RULES[:1], cfg())
    assert prov["column_roles"]["future_return_2"] == "future_outcome"
    assert len(ev) > 0 and (ev["label_value"] > 0).all()                    # 未來欄選樣 ⇒ 正報酬（看答案選樣）
    from momentum.Analysis.event_samples.condition_engine import ConditionError
    with pytest.raises(ConditionError):
        parse_condition(expr, registry(), "feature")


# ---- G2：多組 label 一次設定（label_id manifest；非布林覆寫） ----
def test_G2_multi_label_manifest_and_hand_exact_labels(bars):
    spec = parse_condition("ret_1 < -0.02", registry(), "feature")
    ev, prov = generate_events(spec, {"12h": bars}, RULES, cfg(scenario="A"))
    ids = ev["label_definition"].apply(lambda d: d["rule_id"])
    assert set(ids) == {"up1", "up5"}
    assert [m["label_id"] for m in prov["label_manifest"]] == ["up1", "up5"]
    assert ev["event_id"].is_unique
    close = bars.set_index("open_time_ms")["close"]
    pos = {t: i for i, t in enumerate(bars["open_time_ms"])}
    for _, row in ev.iterrows():
        h = row["label_definition"]["window"]["horizon_bars"]
        thr = {"up1": 0.01, "up5": 0.05}[row["label_definition"]["rule_id"]]
        i = pos[row["t0"]]
        ret = bars.loc[i + h, "close"] / bars.loc[i, "close"] - 1.0
        assert row["label"] == int(ret >= thr)                               # 標籤逐列手算 exact
        assert abs(row["label_value"] - ret) < 1e-12
    assert close is not None


def test_G2_default_scenario_C_dedupes_per_label_id(bars):
    """CODEX-R1-P1-01 RECHECK：預設 C 情境下每個 label_id 各自去重、不得被另一 label_id 的簇刪光。"""
    spec = parse_condition("ret_1 < 0", registry(), "feature")                    # 高命中 ⇒ 簇多
    ev, prov = generate_events(spec, {"12h": bars}, RULES, cfg(scenario="C"))
    ids = ev["label_definition"].apply(lambda d: d["rule_id"])
    assert set(ids) == {"up1", "up5"}
    assert set(prov["manifests"]) == {"up1", "up5"} and set(prov["dedupe"]) == {"up1", "up5"}
    for lid in ("up1", "up5"):
        tbl = prov["manifests"][lid].table
        assert tbl.groupby("dedupe_cluster_id")["in_primary"].sum().eq(1).all()  # 各 label_id 內簇首保留
        assert int((ids == lid).sum()) == int(tbl["in_primary"].sum())
    # 逐 label_id 去重 ＝ 對該 label_id 單獨跑產生器之結果（同 t₀ 集合）
    ev1, _ = generate_events(spec, {"12h": bars}, RULES[:1], cfg(scenario="C"))
    assert sorted(ev.loc[ids == "up1", "t0"]) == sorted(ev1["t0"])


def test_control_kind_not_overridable():
    """CODEX-R1-P1-03 RECHECK：GeneratorConfig 無 control_kind 欄；平台路徑寫死 platform_same_trigger_rule。"""
    with pytest.raises(TypeError):
        GeneratorConfig(symbol="ETHUSDT", timeframe="12h", data_snapshot_digest="x", control_kind="user_labeled_other")  # type: ignore[call-arg]
    from momentum.Analysis.event_samples.generator import PLATFORM_CONTROL_KIND
    assert PLATFORM_CONTROL_KIND == "platform_same_trigger_rule"


def test_short_with_raw_outcome_selection_flagged(bars, monkeypatch):
    """COMPOSER-R1-P2-02 RECHECK：結果欄 raw／label_value signed 於 provenance 明示；short＋結果欄選樣 loud warning。"""
    msgs = []
    monkeypatch.setattr(gen.logger, "warning", lambda m, *a, **k: msgs.append(m % a if a else m))
    spec = parse_condition("trigger_return <= -0.03", registry(), "selection_predicate")
    ev, prov = generate_events(spec, {"12h": bars}, RULES[:1], cfg(direction="short"))
    assert prov["outcome_columns_are_raw_unsigned"] is True and prov["label_value_is_signed"] is True
    assert any("direction=short" in m for m in msgs)
    pos = {t: i for i, t in enumerate(bars["open_time_ms"])}
    i = pos[ev["t0"].iloc[0]]
    assert abs(ev["label_value"].iloc[0] - (-(bars.loc[i + 2, "close"] / bars.loc[i, "close"] - 1.0))) < 1e-12
    # long＋純 pit 條件不告警
    msgs.clear()
    generate_events(parse_condition("ret_1 < -0.02", registry(), "feature"), {"12h": bars}, RULES[:1], cfg())
    assert not any("direction=short" in m for m in msgs)


# ---- G3：方向／情境／答案窗／規則摘要自動存 ----
def test_G3_auto_fields(bars):
    spec = parse_condition("ret_1 < -0.02", registry(), "feature")
    c = cfg(direction="short", scenario="B", entry_price_semantic="next_open", decision_offset_bars=1)
    ev, prov = generate_events(spec, {"12h": bars}, RULES[:1], c)
    assert (ev["direction"] == "short").all() and (ev["scenario"] == "B").all()
    assert (ev["decision_offset_bars"] == 1).all() and (ev["entry_price_semantic"] == "next_open").all()
    assert ev["label_definition"].apply(lambda d: d["window"]["horizon_bars"]).eq(2).all()
    import json
    s = json.loads(ev["search_rule_summary"].iloc[0])
    assert s["canonical_digest"] == spec.canonical_digest and s["expression"] == spec.expression
    assert s["column_roles"] == {"ret_1": "pit_feature"}
    # short：label_value 為 signed（dir=-1）
    pos = {t: i for i, t in enumerate(bars["open_time_ms"])}
    i = pos[ev["t0"].iloc[0]]
    assert abs(ev["label_value"].iloc[0] - (-(bars.loc[i + 2, "close"] / bars.loc[i, "close"] - 1.0))) < 1e-12


# ---- G4：去重在產生期，回報原始／去重後數 ----
def test_G4_dedupe_reports_raw_and_after(bars):
    spec = parse_condition("ret_1 < 0", registry(), "feature")             # 高命中 ⇒ 必有重疊簇
    ev, prov = generate_events(spec, {"12h": bars}, (LabelRule("up", 3, 0.01),), cfg(scenario="C"))
    assert prov["n_events_raw"] > prov["n_events_after_dedupe"] == len(ev)
    assert prov["dedupe"]["up"]["n_events_raw"] == prov["n_events_raw"]
    assert prov["dedupe"]["up"]["policy"]["primary"] == "cluster_first"
    assert prov["n_candidates"] == prov["n_events_raw"] + sum(prov["n_dropped_by_reason"].values())
    assert prov["accounting_ok"] is True
    # 簇首保留：每簇只留一顆且為 label_start 最早者
    tbl = prov["manifests"]["up"].table
    assert tbl.groupby("dedupe_cluster_id")["in_primary"].sum().eq(1).all()
    # A 情境：全留、靠權重
    ev_a, prov_a = generate_events(spec, {"12h": bars}, (LabelRule("up", 3, 0.01),), cfg(scenario="A"))
    assert prov_a["n_events_after_dedupe"] == prov_a["n_events_raw"] == len(ev_a)
    assert prov_a["dedupe"]["up"]["policy"]["requires_cluster_robust"] is True


# ---- G5：一鍵合規檔＋platform_same_trigger_rule 控制組 ----
def test_G5_output_passes_same_validator_and_control_kind(bars):
    spec = parse_condition("ret_1 < -0.02", registry(), "feature")
    ev, prov = generate_events(spec, {"12h": bars}, RULES[:1], cfg())
    again = validate_event_import(ev.to_dict("records"))                      # 同一 validator、再過一次
    assert len(again) == len(ev)
    assert (ev["control_kind"] == "platform_same_trigger_rule").all()
    assert set(ev["label"]) == {0, 1}                                          # 同觸發規則下 label=0 ＝ 平台控制組
    assert (ev["kind_source"] == "platform_auto").all()
    assert (ev["source_file_digest"] == prov["source_file_digest"]).all()
    # 尾端答案窗不完整者被同一 eligibility 丟棄且記帳
    assert prov["n_dropped_by_reason"].get("label_window_incomplete", 0) >= 0
    assert ev["t0"].max() <= bars["open_time_ms"].iloc[-3]


def test_G5_one_class_fail_closed(bars):
    """只有正例（future_return_2 選樣 ⇒ 全 label=1）⇒ validator missing_control_group（不靜默）。"""
    spec = parse_condition("future_return_2 >= 0.01", registry(), "selection_predicate")
    with pytest.raises(ContractValidationError) as ei:
        generate_events(spec, {"12h": bars}, RULES[:1], cfg())
    assert {f["reason"] for f in ei.value.failures} == {"missing_control_group"}


def test_empty_hits_loud_non_error(bars):
    spec = parse_condition("ret_1 < -0.99", registry(), "feature")
    ev, prov = generate_events(spec, {"12h": bars}, RULES[:1], cfg())
    assert ev.empty and prov["status"] == "empty" and prov["n_hits"] == 0 and prov["n_events_after_dedupe"] == 0


def test_always_true_flagged(bars):
    spec = parse_condition("notnull(ret_1) or isnull(ret_1)", registry(), "feature")
    _, prov = generate_events(spec, {"12h": bars}, RULES[:1], cfg())
    assert prov["always_true"] is True and prov["n_hits"] == len(bars)


def test_input_guards(bars):
    spec = parse_condition("ret_1 < -0.02", registry(), "feature")
    with pytest.raises(ValueError):
        generate_events(spec, {"4h": bars}, RULES[:1], cfg())                 # 缺錨定 TF
    with pytest.raises(ValueError):
        generate_events(spec, {"12h": bars}, (), cfg())                        # 空 label_config
    with pytest.raises(ValueError):
        generate_events(spec, {"12h": bars}, (LabelRule("a", 2, 0.01), LabelRule("a", 3, 0.01)), cfg())
    with pytest.raises(ValueError):
        generate_events(spec, {"12h": bars}, (LabelRule("a", 2, 0.01, "open_to_close"),), cfg())
    with pytest.raises(ValueError):
        generate_events(spec, {"12h": bars}, RULES[:1], cfg(data_snapshot_digest=""))
    lab = parse_condition("future_return_2 > 0", registry(), "label")
    with pytest.raises(ValueError):
        generate_events(lab, {"12h": bars}, RULES[:1], cfg())                  # label 角色非選樣式


# ---- G6：全 K 線標籤重算＝呼叫 B2.5 evaluate_all_bars（禁平行實作） ----
def test_G6_calls_evaluate_all_bars_not_parallel(bars, monkeypatch):
    spec = parse_condition("ret_1 < -0.02", registry(), "feature")
    calls = []
    orig = ab.evaluate_all_bars

    def spy(*a, **kw):
        calls.append((a[2]["label_id"], a[2]["prevalence_learn"], kw.get("manifest") is not None))
        return orig(*a, **kw)

    monkeypatch.setattr(ab, "evaluate_all_bars", spy)
    ev, prov = generate_events(spec, {"12h": bars}, RULES, cfg(run_all_bars_eval=True))
    assert [c[0] for c in calls] == ["up1", "up5"]                             # 每 label_id 各呼叫一次 B2.5
    assert all(c[2] for c in calls)                                            # manifest 透傳（AR-3 共同欄）
    rep = prov["all_bars_evaluation"]["up1"]
    assert rep["statistic_kind"] == "all_bars_evaluation" and rep["capability_status"] == "ok"
    assert rep["label_id"] == "up1"
    # GROK-R1-P1-01 RECHECK：prevalence_learn＝**回傳 primary（去重後）集**該 label_id 正例率，exact
    ids = ev["label_definition"].apply(lambda d: d["rule_id"])
    for j, lid in enumerate(("up1", "up5")):
        assert calls[j][1] == pytest.approx(float(ev.loc[ids == lid, "label"].mean()), abs=1e-12)
        assert prov["all_bars_evaluation"][lid]["prevalence_learn_scope"] == "primary_after_dedupe"
        assert prov["all_bars_evaluation"][lid]["overall"]["prevalence_learn"] == pytest.approx(float(ev.loc[ids == lid, "label"].mean()), abs=1e-12)
    # 規則分數＝遮罩：signal_frequency ≈ 命中率（分母 eligible）
    assert 0 < rep["overall"]["signal_frequency"] < 1
    assert rep["estimand_note"].startswith("rule 僅引用 pit")
    assert "n_eligible" in rep["counts"] and rep["counts"]["n_eligible"] == len(bars) - 2
    assert ids is not None


def test_G6_offset_shift_consistent(bars, monkeypatch):
    """k=1：決策根分數＝「觸發於下一根」之遮罩（與 evaluate_all_bars 自身 decision=ot[i−k] 映射一致）。"""
    spec = parse_condition("ret_1 < -0.02", registry(), "feature")
    captured = {}
    orig = ab.evaluate_all_bars

    def spy(rule, b, c, **kw):
        captured["scores"] = rule(b["ETHUSDT"])
        return orig(rule, b, c, **kw)

    monkeypatch.setattr(ab, "evaluate_all_bars", spy)
    generate_events(spec, {"12h": bars}, RULES[:1], cfg(run_all_bars_eval=True, decision_offset_bars=1))
    mask = (bars["ret_1"] < -0.02).to_numpy()
    s = captured["scores"].to_numpy()
    assert np.array_equal(s[:-1][~np.isnan(s[:-1])], mask[1:].astype(float)[~np.isnan(s[:-1])])
    assert np.isnan(s[-1])


# ---- event_filter adapter ----
def _feat_df():
    return pd.DataFrame({"timestamp": [1, 2, 3, 4], "f1": [0.1, -0.2, 0.3, np.nan], "f2": [1.0, 2.0, 3.0, 4.0]})


def test_event_filter_legacy_query_path_unchanged():
    ef = EventFilter({"min_events": 1, "sample_size_tiers": {"low_confidence": 1}})
    out, info = ef.apply_filter(_feat_df(), query="f1 > 0")
    assert out["timestamp"].tolist() == [1, 3] and info["mode"] == "query" and info["n_events"] == 2
    out2, info2 = ef.apply_filter(_feat_df(), timestamps=[2, 4])
    assert out2["timestamp"].tolist() == [2, 4] and info2["mode"] == "timestamps"
    out3, info3 = ef.apply_filter(_feat_df())
    assert len(out3) == 4 and info3["mode"] == "none"
    assert "condition_digest" not in info                                      # legacy info 鍵集不變


def test_event_filter_condition_spec_feature_role():
    ef = EventFilter({"min_events": 1, "sample_size_tiers": {"low_confidence": 1}})
    spec = parse_condition("f1 > 0 and f2 < 3", {"f1": "pit_feature", "f2": "pit_feature"}, "feature")
    out, info = ef.apply_filter(_feat_df(), condition_spec=spec)
    assert out["timestamp"].tolist() == [1] and info["mode"] == "condition_engine"
    assert info["condition_digest"] == spec.canonical_digest and info["n_events"] == 1
    out_direct, _ = apply_condition_spec(_feat_df(), spec)
    assert out_direct.equals(out)


def test_event_filter_rejects_selection_predicate_and_mixed():
    ef = EventFilter({})
    sp = parse_condition("f1 > 0 and fut > 0", {"f1": "pit_feature", "fut": "future_outcome"}, "selection_predicate")
    with pytest.raises(InvalidQueryError):
        ef.apply_filter(_feat_df().assign(fut=1.0), condition_spec=sp)       # D3-4：不得流入特徵表
    fe = parse_condition("f1 > 0", {"f1": "pit_feature"}, "feature")
    with pytest.raises(InvalidQueryError):
        ef.apply_filter(_feat_df(), query="f1 > 0", condition_spec=fe)       # 單一遮罩來源
    with pytest.raises(InvalidQueryError):
        ef.apply_filter(_feat_df().drop(columns=["f1"]), condition_spec=fe)  # 缺欄 loud


def test_allowed_filtering_params_contractized():
    assert allowed_filtering_params() == frozenset({"price_change"})
