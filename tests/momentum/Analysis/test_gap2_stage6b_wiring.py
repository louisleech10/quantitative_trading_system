"""GAP-2 B4 Task 4.1 — stage 6b 接線整合測試（真實 kline 衍生 fixture 經 ichc_run；禁合成冒充）。

驗證 ①–⑯（TODO Task 4.1）＋探針 ``test_mutation_fit_scope_derived_oos_breaks_root_oracle``。
xsec 節（⑯）沿 tests/momentum/Analysis/test_ichc_xsec_capability.py 之合成 MultiIndex 慣例（xsec 單元層既有做法）。
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis import ic_filter_orchestrator as orch_mod
from momentum.Analysis.ic_config_schema import contract_enum, load_ic_config, load_report_contract
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator, STAGE_OVERRIDE_PATHS
from momentum.Analysis.survivor_contract import load_survivor_contract
from momentum.core.contracts import deny_factor_in_ok_oos
from tests.momentum.helpers.ichc_run import KLINE_CACHE_DIR, feature_index, fixture_paths

REPO = Path(__file__).resolve().parents[3]


def _run(config_override: Optional[dict] = None, *, event_timestamps=None, meta_override: Optional[dict] = None) -> Tuple[ICFilterOrchestrator, dict, Path]:
    """同 ichc_run.run_analyze 但回傳 orchestrator（refilter／cache 測試需要）；persist 導 tmp。"""
    from momentum.factories import create_ic_analyzer, create_kline_storage_manager

    h5, meta = fixture_paths()
    tmp = Path(tempfile.mkdtemp(prefix="gap2_b4_"))
    meta_path = meta
    if meta_override is not None:
        data = json.loads(meta.read_text(encoding="utf-8"))
        for k, v in meta_override.items():
            if v is None:
                data.pop(k, None)
            else:
                data[k] = v
        meta_path = tmp / meta.name
        meta_path.write_text(json.dumps(data), encoding="utf-8")
    orch = create_ic_analyzer()
    reporter = orch._reporter
    o_sr, o_sfl, o_sff = reporter.save_report, reporter.save_filter_log, reporter.save_filtered_features
    reporter.save_report = lambda report, output_dir=None, case_id=None, **kw: o_sr(report, output_dir=str(tmp / "reports"), case_id=case_id, **kw)
    reporter.save_filter_log = lambda fl, output_dir=None, case_id=None, **kw: o_sfl(fl, output_dir=str(tmp / "reports"), case_id=case_id, **kw)
    reporter.save_filtered_features = lambda df, cols, output_path, **kw: o_sff(df, cols, str(tmp / "features" / Path(str(output_path)).name), **kw)
    kline_reader = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    report = orch.analyze(
        features_path=str(h5.resolve()), labels_path="", meta_path=str(meta_path.resolve()),
        config_override=config_override, kline_reader=kline_reader, event_timestamps=event_timestamps,
    )
    return orch, report, tmp


def _sec_sha(section: dict) -> str:
    return hashlib.sha256(json.dumps(section, sort_keys=True, default=str).encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def default_run():
    return _run()


# ---------------------------------------------------------------- ①
def test_default_config_section_ok_and_root_oracle(default_run):
    orch, report, _ = default_run
    m = report["marginal_ic"]
    assert m["status"] == "ok" and m["reason"] is None
    assert m["fit_scope"] == "train"
    # oos 兩欄與 root 一致（root 為 oracle，不以 fit_scope 為 oracle）
    assert report["analysis_status"] == "ok_oos"
    assert m["oos_guarantees"] is True and m["pass_class"] == "oos"
    assert m["composite"]["oos_guarantees"] is True
    assert m["independent_oos_validation"] is False and m["selection_sample"] == "test"
    assert set(m["per_feature"].keys()) == set(orch._filtered_features_df.columns)
    assert m["n_regressions"] == 2 * len(m["per_feature"]) + len(m["removed_candidates"])


# ---------------------------------------------------------------- ②
def test_disabled_gives_status_object_only():
    _, report, _ = _run({"marginal_ic": {"enabled": False}})
    assert report["marginal_ic"] == {"status": "disabled", "reason": "disabled_by_config"}
    assert set(report["marginal_ic"].keys()) == {"status", "reason"}
    # 倖存者檔仍寫（marginal 為 disabled 物件）
    so = report["metadata"]["survivor_output"]
    assert so["status"] == "ok" and set(so.keys()) == {"status", "reason", "path", "sha256", "case_id"}
    payload = json.loads(Path(so["path"]).read_text(encoding="utf-8"))
    assert payload["composite"] == {"status": "not_computed", "reason": "disabled_by_config"}
    assert payload["status"] == "not_computed" and payload["reason"] == "disabled_by_config"


# ---------------------------------------------------------------- ③
def test_forced_full_sample_fallback():
    # 放寬門檻使 full-sample 路徑仍有倖存者（預設門檻下 fixture 於 full-sample 為 0 survivors）
    orch, report, _ = _run({"min_test_rows": 100000, "thresholds": {"ic_mean_min": 0.0, "icir_min": 0.0, "p_value_max": 1.0}})
    assert report["analysis_status"] == "degraded_full_sample"
    m = report["marginal_ic"]
    assert m["fit_scope"] == "full_sample"
    if m["status"] == "ok":
        assert m["oos_guarantees"] is False and m["pass_class"] == "full_sample_research_only"
        assert m["composite"]["oos_guarantees"] is False
    else:  # 仍無倖存者 ⇒ 節 not_applicable:no_survivors，OOS 欄不注入
        assert (m["status"], m["reason"]) == ("not_applicable", "no_survivors") and m["oos_guarantees"] is None
        pytest.skip("fixture 於 full-sample fallback 無倖存者：③ 之 OOS 注入斷言改由 ③′（事件 fallback）覆蓋")
    assert orch._in_fallback_rerun is False  # try/finally 還原
    so = report["metadata"]["survivor_output"]
    assert so["status"] == "ok"
    payload = json.loads(Path(so["path"]).read_text(encoding="utf-8"))
    assert payload["oos_guarantees"] is False and payload["pass_class"] == "full_sample_research_only"
    assert payload["split"]["split_method"] == "full_sample_fallback"


# ---------------------------------------------------------------- ③′
def test_event_fallback_holdout_present_but_root_degraded():
    """holdout 存在但事件不足 fallback ⇒ fit_scope=train 但 oos 欄由 root 注入為 False（A1-3 之證）。"""
    ts = list(feature_index(3))
    orch, report, _ = _run({"event_filter": {"enabled": True, "min_events": 30}}, event_timestamps=ts)
    ef = report["metadata"].get("event_filter") or {}
    assert ef.get("fallback") is True
    assert report["analysis_status"] == "degraded_full_sample"
    m = report["marginal_ic"]
    assert m["status"] == "ok" and m["fit_scope"] == "train"
    assert m["oos_guarantees"] is False and m["pass_class"] == "full_sample_research_only"
    payload = json.loads(Path(report["metadata"]["survivor_output"]["path"]).read_text(encoding="utf-8"))
    assert payload["sample_scope"]["kind"] == "full" and payload["sample_scope"]["degraded"] is True
    assert payload["sample_scope"]["event"]["mode"] == "timestamps"


# ---------------------------------------------------------------- ④ ⑩ ⑬
def test_refilter_recomputes_section_and_cache_snapshot(default_run):
    orch, report, _ = default_run
    ident_before = copy.deepcopy(orch._ic_cache["event_identity"])
    sha_before = _sec_sha(orch._ic_cache["stage6b_results"])
    per_before = set(report["marginal_ic"]["per_feature"].keys())
    # 收緊門檻 ⇒ 倖存者集合改變（可為空 ⇒ 節 not_applicable:no_survivors、per_feature 亦空）
    report2 = orch.refilter({"ic_mean_min": 0.9, "icir_min": 5.0})
    m2 = report2["marginal_ic"]
    new_cols = set(orch._filtered_features_df.columns) if orch._filtered_features_df is not None else set()
    assert set(m2["per_feature"].keys()) == new_cols
    assert new_cols != per_before
    assert _sec_sha(orch._ic_cache["stage6b_results"]) != sha_before  # ⑩ cache snapshot 更新
    assert orch._ic_cache["event_identity"] == ident_before  # ⑬ 同 request 沿用
    if m2["status"] == "ok":
        assert m2["oos_guarantees"] is True and m2["pass_class"] == "oos"
    else:
        assert (m2["status"], m2["reason"]) == ("not_applicable", "no_survivors")


def test_event_identity_changes_across_requests():
    orch_a, rep_a, _ = _run()
    orch_b, rep_b, _ = _run({"event_filter": {"enabled": True, "min_events": 30}}, event_timestamps=list(feature_index(3)))
    assert orch_a._ic_cache["event_identity"]["mode"] == "none"
    assert orch_b._ic_cache["event_identity"]["mode"] == "timestamps"
    assert orch_a._ic_cache["event_identity"] != orch_b._ic_cache["event_identity"]


# ---------------------------------------------------------------- ⑤ ⑥ ⑦
def test_deny_factor_and_contract_sync_and_determinism(default_run):
    _, report, _ = default_run
    deny_factor_in_ok_oos(report)  # ⑤ 不 raise
    contract = load_report_contract()
    assert "marginal_ic" in contract["report_sections"]  # ⑥（同 commit 增鍵）
    orch_src = (REPO / "momentum/Analysis/ic_filter_orchestrator.py").read_text(encoding="utf-8")
    assert '"marginal_ic"' in orch_src
    _, report_b, _ = _run()
    assert _sec_sha(report["marginal_ic"]) == _sec_sha(report_b["marginal_ic"])  # ⑦ 決定性
    assert report["marginal_ic"]["status"] in contract_enum("capability_status")


# ---------------------------------------------------------------- ⑨ wiring check
def test_wiring_check_green():
    proc = subprocess.run(["bash", str(REPO / "scripts/ic_wiring_check.sh")], capture_output=True, text=True, cwd=str(REPO))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "marginal_ic" in STAGE_OVERRIDE_PATHS and STAGE_OVERRIDE_PATHS["marginal_ic"] == ("marginal_ic", "enabled")


# ---------------------------------------------------------------- ⑫ reason 字面 ⊆ 契約
def test_orchestrator_marginal_reasons_subset_of_contract(default_run):
    _, report, _ = default_run
    pool = set(load_survivor_contract()["reasons"]["marginal_ic"])
    m = report["marginal_ic"]
    if m["reason"] is not None:
        assert m["reason"] in pool
    for v in m["views"].values():
        assert v["reason"] is None or v["reason"] in pool
    # AST（可選）：_stage6b_marginal_ic／_marginal_status_object 內字串常數 ⊆ 契約 ∪ 非 reason 字面
    src = (REPO / "momentum/Analysis/ic_filter_orchestrator.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "_marginal_status_object":
            args = node.args
            if len(args) == 2 and isinstance(args[1], ast.Constant) and args[1].value is not None:
                assert args[1].value in pool, args[1].value


# ---------------------------------------------------------------- ⑭ 缺 symbol
def test_missing_symbol_identity_missing(default_run):
    """缺 symbol ⇒ 不組裝不寫檔、identity_missing 五鍵；marginal_ic 節不受影響。
    註：完整 analyze 於缺 symbol 時無法取 kline／label（`metadata.symbol is required for IC train/test split`／
    `labels_path is required when kline_reader is missing`），故本案例於 persist 層驗（同一 `_persist_outputs` 入口）。"""
    orch, report, tmp = default_run
    report_copy = copy.deepcopy(report)
    meta_no_symbol = {k: v for k, v in orch._ic_cache["metadata"].items() if k != "symbol"}
    out_dir = tmp / "reports_nosym"
    saved = (orch._reporter.save_report, orch._reporter.save_filter_log, orch._reporter.save_filtered_features)
    orch._reporter.save_report = lambda r, output_dir=None, case_id=None, **kw: {"json": str(out_dir / f"ic_report_{case_id}.json"), "markdown": ""}
    orch._reporter.save_filter_log = lambda fl, output_dir=None, case_id=None, **kw: str(out_dir / "fl.json")
    orch._reporter.save_filtered_features = lambda df, cols, output_path, **kw: str(out_dir / "f.h5")
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        orch._persist_outputs(
            orch._ic_cache["features_df"], orch._filtered_features_df, report_copy, meta_no_symbol, report_copy.get("filter_log") or {},
            stage6b_results=report_copy["marginal_ic"], event_identity=orch._ic_cache["event_identity"],
            features_path=orch._features_path, label_series=orch._ic_cache["label_series"], split_context=orch._ic_cache["split_context"],
        )
    finally:
        orch._reporter.save_report, orch._reporter.save_filter_log, orch._reporter.save_filtered_features = saved
    so = report_copy["metadata"]["survivor_output"]
    assert so["status"] == "computation_failed" and so["reason"] == "identity_missing"
    assert so["path"] is None and so["sha256"] is None and so["case_id"] == "ic_gatekeeper"
    assert set(so.keys()) == {"status", "reason", "path", "sha256", "case_id"}
    assert report_copy["marginal_ic"]["status"] == "ok"
    assert not list(out_dir.glob("ic_survivors_*.json"))


# ---------------------------------------------------------------- ⑮ 預算
def test_budget_exceeded_whole_views_not_computed():
    _, report, _ = _run({"marginal_ic": {"max_survivors_for_loo": 1}})
    m = report["marginal_ic"]
    assert m["views"]["loo"] == {"status": "not_computed", "reason": "candidate_budget_exceeded"}
    assert m["views"]["sequential"]["reason"] == "candidate_budget_exceeded"
    assert m["per_feature"] == {} and m["sequential"] == []
    assert m["status"] == "not_computed" and m["reason"] == "candidate_budget_exceeded"
    assert m["n_regressions"] == 0
    assert m["oos_guarantees"] is None  # 非 ok 節不注入


# ---------------------------------------------------------------- ⑯ xsec N/A
def _make_xsec_frame(n_timestamps: int = 60, seed: int = 7) -> pd.DataFrame:
    symbols = ["BTCUSDT", "ETHUSDT", "BCHUSDT", "LTCUSDT", "XRPUSDT"]
    timestamps = pd.date_range("2020-01-01", periods=n_timestamps, freq="12h")
    index = pd.MultiIndex.from_product([timestamps, symbols], names=["timestamp", "_symbol"])
    rng = np.random.default_rng(seed)
    n = len(index)
    feat = rng.normal(0, 1, n)
    label = feat * 0.5 + rng.normal(0, 1, n)
    return pd.DataFrame({"alpha": feat.astype(np.float32), "return_1": label.astype(np.float32)}, index=index)


def test_xsec_marginal_ic_not_applicable(monkeypatch):
    calls = []
    real = ICFilterOrchestrator._stage6b_marginal_ic

    def spy(self, *a, **k):
        calls.append(1)
        return real(self, *a, **k)

    monkeypatch.setattr(ICFilterOrchestrator, "_stage6b_marginal_ic", spy)
    orch = ICFilterOrchestrator(load_ic_config())
    report = orch.analyze_cross_sectional(_make_xsec_frame(), config_override={"ic_train_test_split": False})
    assert report["marginal_ic"] == {"status": "not_applicable", "reason": "cross_sectional_mode"}
    assert calls == []


# ---------------------------------------------------------------- 探針：重現 R2 bug（fit_scope 推導 OOS＋注入被繞過）⇒ ③′ oracle 紅
def test_mutation_fit_scope_derived_oos_breaks_root_oracle(monkeypatch):
    ts = list(feature_index(3))
    base_orch, base_report, _ = _run({"event_filter": {"enabled": True, "min_events": 30}}, event_timestamps=ts)
    assert base_report["marginal_ic"]["oos_guarantees"] is False  # 基線綠（root degraded 注入）

    real_stage6b = ICFilterOrchestrator._stage6b_marginal_ic

    def fit_scope_derived(self, *a, **k):
        section = real_stage6b(self, *a, **k)
        if section.get("status") == "ok":  # R2 之 bug：由 fit_scope 推 OOS
            section["oos_guarantees"] = k.get("fit_scope") == "train"
            section["pass_class"] = "oos" if k.get("fit_scope") == "train" else "full_sample_research_only"
        return section

    monkeypatch.setattr(ICFilterOrchestrator, "_stage6b_marginal_ic", fit_scope_derived)
    monkeypatch.setattr(ICFilterOrchestrator, "_inject_root_oos", staticmethod(lambda section, st, oos: None))
    _, mutant_report, _ = _run({"event_filter": {"enabled": True, "min_events": 30}}, event_timestamps=ts)
    with pytest.raises(AssertionError):
        assert mutant_report["marginal_ic"]["oos_guarantees"] is False and mutant_report["marginal_ic"]["pass_class"] == "full_sample_research_only"
