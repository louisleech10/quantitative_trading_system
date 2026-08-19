"""GAP-2 B4 Task 4.2 — 倖存者檔持久化＋報告 metadata 鏡像（真實 fixture；persist 導 tmp）。

驗證 ⓪–⑧（TODO Task 4.2）＋探針 ``test_mutation_persist_reads_ic_cache_breaks_cold_call``。
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
from pathlib import Path

import pandas as pd
import pytest

from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.Analysis.survivor_contract import compute_event_identity, load_survivor_contract, validate_survivor_output
from tests.momentum.Analysis.test_gap2_stage6b_wiring import _run, feature_index

FIVE = {"status", "reason", "path", "sha256", "case_id"}


@pytest.fixture(scope="module")
def default_run():
    return _run()


def _persist_with(orch, report, metadata, out_dir: Path, **overrides):
    """以 default_run 之 orchestrator 直接呼叫 `_persist_outputs`（同一入口；reporter 導向 out_dir）。"""
    saved = (orch._reporter.save_report, orch._reporter.save_filter_log, orch._reporter.save_filtered_features)
    orch._reporter.save_report = lambda r, output_dir=None, case_id=None, **kw: {"json": str(out_dir / f"ic_report_{case_id}.json"), "markdown": ""}
    orch._reporter.save_filter_log = lambda fl, output_dir=None, case_id=None, **kw: str(out_dir / "fl.json")
    orch._reporter.save_filtered_features = lambda df, cols, output_path, **kw: str(out_dir / "f.h5")
    out_dir.mkdir(parents=True, exist_ok=True)
    kwargs = dict(
        stage6b_results=report["marginal_ic"], event_identity=orch._ic_cache["event_identity"],
        features_path=orch._features_path, label_series=orch._ic_cache["label_series"], split_context=orch._ic_cache["split_context"],
    )
    kwargs.update(overrides)
    try:
        return orch._persist_outputs(orch._ic_cache["features_df"], orch._filtered_features_df, report, metadata, report.get("filter_log") or {}, **kwargs)
    finally:
        orch._reporter.save_report, orch._reporter.save_filter_log, orch._reporter.save_filtered_features = saved


# ---------------------------------------------------------------- ⓪ 四形狀五鍵
def test_four_shapes_five_keys(default_run, monkeypatch):
    orch, report, tmp = default_run
    ok = report["metadata"]["survivor_output"]
    assert set(ok.keys()) == FIVE and ok["status"] == "ok" and ok["reason"] is None and ok["path"] and len(ok["sha256"]) == 64
    # identity_missing
    rc = copy.deepcopy(report)
    _persist_with(orch, rc, {k: v for k, v in orch._ic_cache["metadata"].items() if k != "timeframe"}, tmp / "shape_identity")
    im = rc["metadata"]["survivor_output"]
    assert set(im.keys()) == FIVE and (im["status"], im["reason"], im["path"], im["sha256"]) == ("computation_failed", "identity_missing", None, None)
    # write_failed（mock save_survivor_output raise ⇒ reason exact "write_failed"，例外類別只進 log；A1-6）
    rc2 = copy.deepcopy(report)

    def boom(payload, output_dir, case_id):
        raise PermissionError("disk full")

    monkeypatch.setattr(orch._reporter, "save_survivor_output", boom)
    _persist_with(orch, rc2, orch._ic_cache["metadata"], tmp / "shape_write")
    wf = rc2["metadata"]["survivor_output"]
    assert set(wf.keys()) == FIVE and (wf["status"], wf["reason"], wf["path"], wf["sha256"]) == ("computation_failed", "write_failed", None, None)
    assert wf["reason"] in load_survivor_contract()["reasons"]["survivor_output"]
    monkeypatch.undo()
    # persist_suppressed（_stage7_report 於 suppress 時寫入）
    rc3 = copy.deepcopy(report)
    orch._suppress_persist = True
    try:
        rep3 = orch._stage7_report(
            orch._ic_cache["features_df"], orch._ic_cache["metadata"], orch._ic_cache,
            {"summary_table": rc3["summary_table"], "passed_features": list(orch._filtered_features_df.columns)},
            {"filtered_df": orch._filtered_features_df}, {}, {}, orch._ic_cache.get("event_info", {}), {},
            split_context=orch._ic_cache["split_context"], stage6b_results=rc3["marginal_ic"],
        )
    finally:
        orch._suppress_persist = False
    ps = rep3["metadata"]["survivor_output"]
    assert set(ps.keys()) == FIVE and (ps["status"], ps["reason"], ps["path"], ps["sha256"]) == ("not_computed", "persist_suppressed", None, None)
    assert ps["case_id"] == "ic_gatekeeper"


# ---------------------------------------------------------------- ① ② ③ ④
def test_file_exists_validates_names_and_sha(default_run):
    orch, report, tmp = default_run
    so = report["metadata"]["survivor_output"]
    path = Path(so["path"])
    assert path.exists() and path.name == "ic_survivors_ic_gatekeeper.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_survivor_output(payload, report_meta=report["metadata"], report_ref_path=str(path.parent / "ic_report_ic_gatekeeper.json"))  # ①
    assert payload["feature_names"] == list(orch._filtered_features_df.columns)  # ②
    assert hashlib.sha256(path.read_bytes()).hexdigest() == so["sha256"]  # ③
    assert str(path).startswith(str(tmp))  # ④ hermetic：同 report 之 output_dir
    assert not list((Path("data_cache") / "reports").glob("ic_survivors_ic_gatekeeper.json")) or True  # 生產目錄不因本測試新增（下方另驗）
    assert payload["provenance"]["report_ref"] == "ic_report_ic_gatekeeper.json"
    assert payload["provenance"]["fit_mode"] in ("train_mask", "pit_expanding", "full_sample")
    assert payload["split"]["row_identity"]["train_index_hash"] != payload["split"]["row_identity"]["test_index_hash"]
    assert payload["sample_scope"]["n_samples_total"] == report["metadata"]["n_samples"]


def test_hermetic_no_production_write(default_run):
    """④：redirect 下 data_cache/reports/ 不得新增 ic_survivors_* 檔（以 mtime 於本 session 之後判）。"""
    import time
    orch, report, tmp = default_run
    prod = Path("data_cache") / "reports"
    if not prod.exists():
        return
    started = Path(report["metadata"]["survivor_output"]["path"]).stat().st_mtime - 3600
    fresh = [p for p in prod.glob("ic_survivors_*.json") if p.stat().st_mtime >= started]
    assert fresh == [], fresh


# ---------------------------------------------------------------- ⑤ ⑥ 事件模式
def test_event_mode_and_fallback_sample_scope():
    ts = list(feature_index(120))
    _, report, _ = _run({"event_filter": {"enabled": True, "min_events": 30}}, event_timestamps=ts)
    payload = json.loads(Path(report["metadata"]["survivor_output"]["path"]).read_text(encoding="utf-8"))
    ef = report["metadata"].get("event_filter") or {}
    if ef.get("fallback") is True:
        assert payload["sample_scope"]["kind"] == "full" and payload["sample_scope"]["degraded"] is True  # ⑥
    else:
        assert payload["sample_scope"]["kind"] == "event"  # ⑤
        assert len(payload["sample_scope"]["event"]["definition_hash"]) == 64
        assert payload["sample_scope"]["degraded"] is False
        assert payload["sample_scope"]["event"]["mode"] == "timestamps"
    _, report_fb, _ = _run({"event_filter": {"enabled": True, "min_events": 30}}, event_timestamps=list(feature_index(3)))
    payload_fb = json.loads(Path(report_fb["metadata"]["survivor_output"]["path"]).read_text(encoding="utf-8"))
    assert payload_fb["sample_scope"]["kind"] == "full" and payload_fb["sample_scope"]["degraded"] is True  # ⑥
    assert payload_fb["oos_guarantees"] is False


# ---------------------------------------------------------------- ⑦ 並發
def test_concurrent_same_case_id_atomic(default_run):
    orch, report, tmp = default_run
    out_dir = tmp / "concurrent"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = json.loads(Path(report["metadata"]["survivor_output"]["path"]).read_text(encoding="utf-8"))
    errors = []

    def worker(i):
        try:
            p = copy.deepcopy(payload)
            p["generated_at"] = f"2026-08-19T00:00:{i:02d}Z"
            orch._reporter.save_survivor_output(p, output_dir=str(out_dir), case_id="ic_gatekeeper")
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    final = json.loads((out_dir / "ic_survivors_ic_gatekeeper.json").read_text(encoding="utf-8"))
    validate_survivor_output(final)
    assert not list(out_dir.glob(".ic_survivors_*.tmp"))


# ---------------------------------------------------------------- ⑧ persist 不讀 _ic_cache
def test_persist_cold_call_without_ic_cache(default_run):
    orch, report, tmp = default_run
    cold = ICFilterOrchestrator(orch._config)
    assert cold._ic_cache is None
    out_dir = tmp / "cold"
    out_dir.mkdir(parents=True, exist_ok=True)
    cold._reporter.save_report = lambda r, output_dir=None, case_id=None, **kw: {"json": str(out_dir / f"ic_report_{case_id}.json"), "markdown": ""}
    cold._reporter.save_filter_log = lambda fl, output_dir=None, case_id=None, **kw: str(out_dir / "fl.json")
    cold._reporter.save_filtered_features = lambda df, cols, output_path, **kw: str(out_dir / "f.h5")
    cold._features_path = orch._features_path
    cold._current_config_hash = orch._current_config_hash
    ident = compute_event_identity(None, list(feature_index(50)))
    rc = copy.deepcopy(report)
    cold._persist_outputs(
        orch._ic_cache["features_df"], orch._filtered_features_df, rc, orch._ic_cache["metadata"], rc.get("filter_log") or {},
        stage6b_results=rc["marginal_ic"], event_identity=ident, features_path=orch._features_path,
        label_series=orch._ic_cache["label_series"], split_context=orch._ic_cache["split_context"],
    )
    so = rc["metadata"]["survivor_output"]
    assert so["status"] == "ok"
    payload = json.loads(Path(so["path"]).read_text(encoding="utf-8"))
    assert payload["sample_scope"]["event"]["definition_hash"] == ident["definition_hash"]  # 用傳入 identity，非 cache
    assert cold._ic_cache is None


def test_mutation_persist_reads_ic_cache_breaks_cold_call(default_run, monkeypatch):
    """探針：`_persist_outputs` 若忽略 kwarg 改讀 `self._ic_cache["event_identity"]` ⇒ ⑧ 於 `_ic_cache is None` 下 TypeError 紅。"""
    orch, report, tmp = default_run
    real = ICFilterOrchestrator._persist_outputs

    def variant(self, features_df, filtered_df, rep, metadata, filter_log, **kw):
        kw["event_identity"] = self._ic_cache["event_identity"]  # mutant：讀尚未建立之 cache
        return real(self, features_df, filtered_df, rep, metadata, filter_log, **kw)

    monkeypatch.setattr(ICFilterOrchestrator, "_persist_outputs", variant)
    cold = ICFilterOrchestrator(orch._config)
    with pytest.raises(AssertionError):
        try:
            cold._persist_outputs(orch._ic_cache["features_df"], orch._filtered_features_df, copy.deepcopy(report), orch._ic_cache["metadata"], {},
                                  stage6b_results=report["marginal_ic"], event_identity=orch._ic_cache["event_identity"],
                                  features_path=orch._features_path, label_series=orch._ic_cache["label_series"], split_context=orch._ic_cache["split_context"])
        except TypeError:
            raise AssertionError("cold call broke: mutant reads _ic_cache")


# ---------------------------------------------------------------- R21 修補（CODEX-R21-P1-01／P1-02）
def test_persisted_report_json_mirrors_survivor_output(default_run):
    """落盤之 ic_report_{case_id}.json 之 metadata.survivor_output 與回傳 report 五鍵一致（互指鏡像）。"""
    orch, report, tmp = default_run
    so = report["metadata"]["survivor_output"]
    disk = json.loads((tmp / "reports" / "ic_report_ic_gatekeeper.json").read_text(encoding="utf-8"))
    assert disk["metadata"]["survivor_output"] == so
    assert disk["marginal_ic"]["status"] == report["marginal_ic"]["status"]


def test_provenance_uses_effective_config():
    """config_override 改 IC method／label return_type ⇒ 倖存者檔 provenance 反映本次 effective config。"""
    _, report, _ = _run({"ic_calculation": {"methods": ["kendall"]}, "labels": {"return_type": "log"}})
    payload = json.loads(Path(report["metadata"]["survivor_output"]["path"]).read_text(encoding="utf-8"))
    assert payload["provenance"]["ic_method"] == "kendall"
    assert payload["provenance"]["label_return_type"] == "log"
