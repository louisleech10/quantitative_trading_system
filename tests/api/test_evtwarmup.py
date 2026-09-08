"""EVTWARMUP B1：事件路徑豁免 bar-rolling warmup／`min_test_events` 地板／ICIR 降診斷。

SPEC：`docs/EVTWARMUP_SPEC.md`（R2 修訂）　TODO：`docs/EVTWARMUP_TODO.md` Task 1.1／1.2／2.1

- precheck：分流兩段判（`bool(values) and enabled`；stage3 後 `label_source==event_label_value`）；空 dict／disabled／棄條件 ⇒ 主線 bar 規則照舊
- min_test_events：13 事件 ⇒ holdout 仍套用、`fit_mode=train_mask`、`oos_guarantees=false`、reason `insufficient_test_events`、status 仍兩值
- (e′)：values 非空＋enabled 但 `n_events<min_events`（棄條件）⇒ **不**寫 `insufficient_test_events`
- icir：事件路徑不以 `icir_min` 剔除、tiebreaker 改 ic_mean、`get_top_features`／reporter 排序 None-safe、三個序列化入口無 `NaN` 字面
- global：探針 `global_run` 逐鍵 == 改前 golden；全域報告 `ic_window_disclosure.icir_role=="threshold"`（TFWINDOW 後）、無 `tiebreaker_effective`
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_config_schema import ICConfig, load_ic_config
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.Analysis.ic_reporter import _finite_or_neg_inf
from tests.momentum.helpers.ichc_run import feature_index, run_analyze

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests/golden/evtwarmup/baseline.json"
CTX = {"event_manifest_hash": "1" * 64, "label_definition_hash": "2" * 64,
       "decision_time_rule": "t0_open_minus_k_bars", "feature_cutoff_rule": "max_close_ms_le_decision_at",
       "label_window_rule": "close_to_close:horizon_bars=2", "control_kind": "user_labeled_same_trigger"}


def _raise_const(value):
    raise ValueError(f"non-standard JSON constant: {value}")


def _config(event_enabled: bool, min_events: int = 30, min_test_events: int = 30) -> ICConfig:
    data = load_ic_config().model_dump()
    data["event_filter"] = {**data.get("event_filter", {}), "enabled": event_enabled,
                            "min_events": min_events, "min_test_events": min_test_events}
    return ICConfig.model_validate(data)


def _event_inputs(n: int):
    idx = feature_index(n)
    rng = np.random.default_rng(20260908 + n)
    lv = {int(t.value // 10**6): float(v) for t, v in zip(idx, rng.normal(0, 0.02, len(idx)))}
    owners = {t: f"ev{i:03d}" for i, t in enumerate(lv)}
    return lv, owners


# ───────────── Task 1.1：分流與預檢 ─────────────

def test_precheck_predicates_two_stage():
    cfg_on, cfg_off = _config(True), _config(False)
    P = ICFilterOrchestrator._is_event_conditional_precheck
    C = ICFilterOrchestrator._is_event_conditional_consumed
    assert P({1: 0.1}, cfg_on) is True
    assert P({}, cfg_on) is False                 # 空 dict ⇒ 主線（COMPOSER-R1-P1-02）
    assert P(None, cfg_on) is False
    assert P({1: 0.1}, cfg_off) is False          # filter 未啟用 ⇒ 主線
    assert C({"label_source": "event_label_value"}) is True
    assert C({"label_source": "mainline_return_N"}) is False   # 棄條件 ⇒ bar 規則照舊
    assert C({}) is False and C(None) is False


def test_precheck_event_conditional_skips_bar_warmup_but_global_keeps_it():
    config = _config(True)
    o = ICFilterOrchestrator(config)
    n = 400
    idx = pd.Index(1_704_067_200 + np.arange(n, dtype=np.int64) * 43_200, name="timestamp")
    features = pd.DataFrame({"f1": np.arange(n, dtype=float)}, index=idx)
    test_mask = np.zeros(n, dtype=bool)
    test_mask[-80:] = True
    ctx = {"train_mask": ~test_mask, "test_mask": test_mask, "effective_horizon": 5}
    ev = [int(idx[i]) * 1000 for i in range(n - 34, n)]   # 測試段 34 個事件
    # 事件條件 IC ⇒ 不擋，但 test_events 記錄
    assert o._precheck_rolling_warmup(features, config, dict(ctx), ev, event_conditional=True) is None
    c2 = dict(ctx)
    o._precheck_rolling_warmup(features, config, c2, ev, event_conditional=True)
    assert c2["test_events"] == 34
    # 全域（同樣 34 列）⇒ 規則未動仍擋
    out = o._precheck_rolling_warmup(features, config, dict(ctx), None, event_conditional=False)
    assert out is not None and out["test_rows"] == 80 and out["min_test_rows"] == o._rolling_warmup_min_rows(config, 5)
    # values 給了但 enabled=False ⇒ predicate False ⇒ 仍擋
    assert o._precheck_rolling_warmup(features, config, dict(ctx), ev, event_conditional=False) is not None


def test_precheck_mainline_keeps_bar_rows_even_with_timestamps():
    """R4 CODEX-R4-P2-02：主線（event_conditional=False）給了 timestamps 也不得以事件交集覆蓋 bar 列數。"""
    config = _config(False)
    o = ICFilterOrchestrator(config)
    n = 200
    idx = pd.Index(1_704_067_200 + np.arange(n, dtype=np.int64) * 43_200, name="timestamp")
    features = pd.DataFrame({"f1": np.arange(n, dtype=float)}, index=idx)
    test_mask = np.zeros(n, dtype=bool)
    test_mask[-50:] = True
    ctx = {"train_mask": ~test_mask, "test_mask": test_mask, "effective_horizon": 5}
    ev = [int(idx[i]) * 1000 for i in range(n - 3, n)]
    out = o._precheck_rolling_warmup(features, config, ctx, ev, event_conditional=False)
    assert out is not None and out["test_rows"] == 50 and ctx["test_events"] is None
    ctx2 = dict(ctx)
    assert o._precheck_rolling_warmup(features, config, ctx2, ev, event_conditional=True) is None and ctx2["test_events"] == 3


def test_refilter_uses_same_scores_helper_as_analyze():
    """R4 CODEX-R4-P1-01：analyze 與 refilter 之 stage6 分數字典同源——事件路徑 ic_mean、全域 icir。"""
    import inspect

    o = ICFilterOrchestrator(load_ic_config())
    stage5 = {"summary_table": [{"feature_name": "a", "ic_mean": 0.1, "icir": None}, {"feature_name": "b", "ic_mean": 0.2, "icir": 0.9}]}
    icir = {"a": {"icir": 9.0}, "b": {"icir": 0.9}}
    ev_scores, ev_tb = o._redundancy_scores({"label_source": "event_label_value"}, stage5, icir)
    gl_scores, gl_tb = o._redundancy_scores({"label_source": "mainline_return_N"}, stage5, icir)
    assert ev_scores == {"a": 0.1, "b": 0.2} and ev_tb == "ic_mean"
    assert gl_scores is icir and gl_tb is None
    src = inspect.getsource(ICFilterOrchestrator.refilter)
    assert "_redundancy_scores(" in src and 'self._ic_cache["icir"],\n            metadata' not in src


# ───────────── Task 1.2：min_test_events 地板（真實 la0 fixture）─────────────

def _event_run(n_events: int, min_events: int = 30, min_test_events: int = 30) -> dict:
    lv, owners = _event_inputs(n_events)
    return run_analyze({"event_filter": {"enabled": True, "min_events": min_events, "min_test_events": min_test_events}},
                       event_timestamps=list(lv), event_label_values=lv, event_label_owners=owners, event_context=CTX)


@pytest.fixture(scope="module")
def event_report_80():
    return _event_run(80)


def test_min_test_events_floor_keeps_holdout_and_flags_reason(event_report_80):
    m = event_report_80["metadata"]
    split = m["ic_train_test_split"]
    assert split["applied"] is True, split
    assert split["oos_guarantees"] is False and split["test_events"] < split["min_test_events"] == 30
    dg = m["oos_downgrade"]
    assert dg["reason"] == "insufficient_test_events" and dg["test_events"] == split["test_events"] and dg["min_test_events"] == 30
    assert event_report_80["analysis_status"] == "degraded_full_sample"      # 兩值契約（方案 B）
    assert event_report_80["oos_guarantees"] is False
    assert m.get("fit_mode") == "train_mask", m.get("fit_mode")               # 沒有 full-sample 重跑
    assert m.get("fit_mode_source") != "fallback"
    assert m["event_filter"]["label_source"] == "event_label_value"
    # TFWINDOW（B2）後：全路徑鍵集固定，事件路徑 icir_role 覆蓋為 diagnostic
    assert m["ic_window_disclosure"]["icir_role"] == "diagnostic"
    assert m["ic_window_disclosure"]["timeframe_adjustment"] == "applied" and m["ic_window_disclosure"]["window_unit"] == "bars"
    assert m["tiebreaker_effective"] == "ic_mean"
    assert len(event_report_80["summary_table"]) >= 1
    # ICIR 不作事件路徑門檻：removed["icir"] 必空、且被跳過者列入 icir_skipped_event_path（mutation M6 之紅錨）
    thr = _find_key(event_report_80, "stage5_thresholds") or {}
    removed = thr.get("removed_features") or {}
    assert removed.get("icir", []) == [], removed
    assert "icir_skipped_event_path" in removed, removed.keys()


def _find_key(node, key):
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for v in node.values():
            r = _find_key(v, key)
            if r is not None:
                return r
    return None


def test_min_test_events_floor_disabled_gives_oos():
    rep = _event_run(80, min_test_events=0)
    m = rep["metadata"]
    assert m["ic_train_test_split"]["applied"] is True and m["ic_train_test_split"]["oos_guarantees"] is True
    assert "oos_downgrade" not in m and rep["analysis_status"] == "ok_oos"


def test_event_path_without_split_still_discloses_window_and_icir_role():
    """R4 CODEX-R4-P2-03：ic_train_test_split=False 之事件 run 仍須有 ic_window_disclosure（與切分無關）。"""
    lv, owners = _event_inputs(80)
    rep = run_analyze({"ic_train_test_split": False, "event_filter": {"enabled": True, "min_events": 30, "min_test_events": 30}},
                      event_timestamps=list(lv), event_label_values=lv, event_label_owners=owners, event_context=CTX)
    m = rep["metadata"]
    assert m["event_filter"]["label_source"] == "event_label_value"
    assert m["ic_window_disclosure"]["icir_role"] == "diagnostic" and m["tiebreaker_effective"] == "ic_mean"
    assert "oos_downgrade" not in m or m["oos_downgrade"].get("reason") != "insufficient_test_events"


def test_abandoned_conditional_path_is_not_flagged_insufficient_test_events():
    """(e′)：values 非空＋enabled 但事件總數 < min_events ⇒ 棄條件走主線 ⇒ 地板不得開火。"""
    rep = _event_run(20, min_events=30)
    m = rep["metadata"]
    assert m["conditional_ic"]["capability_status"] == "unavailable"
    assert (m.get("oos_downgrade") or {}).get("reason") != "insufficient_test_events"
    assert m["ic_window_disclosure"]["icir_role"] == "threshold" and "tiebreaker_effective" not in m   # 棄條件走主線 ⇒ threshold
    assert m["event_filter"]["label_source"] == "mainline_return_N"


# ───────────── Task 2.1：ICIR 降診斷 ─────────────

def test_icir_not_a_gate_on_event_path_but_still_gate_on_global():
    config = load_ic_config()
    o = ICFilterOrchestrator(config)
    rows = [
        {"feature_name": "a", "ic_mean": 0.05, "icir": None, "p_value": 0.001, "p_value_adj": 0.001,
         "ic_hit_rate": 0.6, "monotonicity_score": 0.9, "coverage": 0.99, "long_short_spread": 0.01},
        {"feature_name": "b", "ic_mean": 0.05, "icir": 0.9, "p_value": 0.001, "p_value_adj": 0.001,
         "ic_hit_rate": 0.6, "monotonicity_score": 0.9, "coverage": 0.99, "long_short_spread": 0.01},
    ]
    passed_ev, log_ev = o._apply_thresholds(rows, config.thresholds, 0.05, icir_gate=False)
    passed_gl, log_gl = o._apply_thresholds(rows, config.thresholds, 0.05, icir_gate=True)
    assert "a" in passed_ev and "a" in log_ev["removed_features"].get("icir_skipped_event_path", [])
    assert "a" not in passed_gl and "a" in log_gl["removed_features"]["icir"]
    assert "icir_skipped_event_path" not in log_gl["removed_features"]


def test_finite_or_neg_inf_and_top_features_sort_none_safe(event_report_80):
    assert _finite_or_neg_inf(None) == float("-inf") and _finite_or_neg_inf(float("nan")) == float("-inf")
    assert _finite_or_neg_inf("x") == float("-inf") and _finite_or_neg_inf(0.5) == 0.5
    o = ICFilterOrchestrator(load_ic_config())
    o._report = {"summary_table": [{"feature_name": "a", "icir": None}, {"feature_name": "b", "icir": 0.5}, {"feature_name": "c", "icir": float("nan")}]}
    top = o.get_top_features(2, sort_by="icir")
    assert top[0]["feature_name"] == "b"
    from momentum.factories import create_ic_analyzer
    a = create_ic_analyzer()
    a._report = event_report_80
    a.get_top_features(10, sort_by="icir")   # 事件報告：不 raise


def test_serialization_entries_have_no_nan_literal(event_report_80, tmp_path):
    """三個序列化入口：save_report（ic_report_*.json）／export_all 之 ai json／scan_cube._dumps。"""
    from momentum.factories import create_ic_analyzer
    from momentum.Analysis.scan_cube import _dumps

    reporter = create_ic_analyzer()._reporter
    path = reporter.save_report(event_report_80, output_dir=str(tmp_path), case_id="evtwarmup")
    assert path is not None
    # 🔴 誠實邊界（EW-RESID-5）：既有欄位 long_short_spread／turnover_rate 等本來就會落成 `NaN` 字面（改前即如此），
    #    不在本票政策內；本票保證的是 icir／ic_mean 一律 null。逐鍵斷言，不以整檔 strict parse 代替。
    files = list(tmp_path.rglob("*.json"))
    assert files
    for p in files:
        text = p.read_text(encoding="utf-8")
        assert '"icir":NaN' not in text and '"icir": NaN' not in text, p
        assert '"ic_mean":NaN' not in text and '"ic_mean": NaN' not in text, p
        loaded = json.loads(text, parse_constant=lambda v: None)   # 既有 NaN 欄位當 null 讀
        rows = loaded.get("summary_table") if isinstance(loaded, dict) else None
        if rows:
            assert all(r.get("icir") is None or isinstance(r.get("icir"), float) for r in rows if isinstance(r, dict))
    # scan cube：以 sanitize 後的 summary 逐節 dump（producer 端已轉 null）
    sanitized = reporter._sanitize_summary_table_for_json(event_report_80["summary_table"])
    cube_text = _dumps({"summary_table": sanitized})
    assert '"icir":NaN' not in cube_text and '"ic_mean":NaN' not in cube_text
    assert all(row.get("icir") is None or np.isfinite(row["icir"]) for row in sanitized)
    assert all(row.get("ic_mean") is None or np.isfinite(row["ic_mean"]) for row in sanitized)


def test_sanitize_converts_nonfinite_icir_and_ic_mean_to_null():
    from momentum.factories import create_ic_analyzer

    reporter = create_ic_analyzer()._reporter
    out = reporter._sanitize_summary_table_for_json([{"feature_name": "a", "icir": float("nan"), "ic_mean": float("inf"), "p_value": 0.1}])
    assert out[0]["icir"] is None and out[0]["ic_mean"] is None and out[0]["p_value"] == 0.1


# ───────────── §G：全域逐鍵不變 ─────────────

def test_global_run_unchanged_vs_golden():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))["global_run"]
    rep = run_analyze(None)
    m = rep["metadata"]
    live = {
        "ic_train_test_split": m.get("ic_train_test_split"),
        "oos_downgrade": m.get("oos_downgrade"),
        "analysis_status": rep.get("analysis_status"),
        "oos_guarantees": rep.get("oos_guarantees"),
        "event_filter_label_source": (m.get("event_filter") or {}).get("label_source"),
        "event_filter_tier": (m.get("event_filter") or {}).get("tier"),
        "n_summary_rows": len(rep.get("summary_table") or []),
    }
    assert live == golden
    assert "tiebreaker_effective" not in m
    # TFWINDOW（B2）後全域亦寫 ic_window_disclosure，但 icir_role 必為 threshold（事件路徑才是 diagnostic）
    assert m["ic_window_disclosure"]["icir_role"] == "threshold"
