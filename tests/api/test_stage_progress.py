"""EVTALIGN Task 4.1：階段內進度 ＋ 記憶體 WARN（非阻擋）（`票 UAT-1`）。

SPEC：`docs/GAP3_EVENT_ALIGNMENT_SPEC.md` Task 4.1　TODO：Task 4.1

使用者原話①「可以跑的話，幹嘛擋? 但我只是不知確切的狀態進行式是什麼」⇒
- preprocessing 長迴圈回報 `done/total`＋ETA；估不出 ⇒ `estimating`（**不給假 ETA**）
- 回報次數 ∈ [3, max(3, ceil(n/100))]（不進 hot loop）
- 記憶體壓力 ⇒ WARN `memory_pressure_observed`，**不 raise、不擋**；正常 ⇒ 不發；每次 analyze 至多一次
- service 把 sub_progress／warnings 寫進 task status；前端顯示

mutation（`--phase 4`）：A8 WARN 改 raise ⇒ `not_blocking` 紅；A10 每欄都回報 ⇒ `count_within_bounds` 紅；
A11 第一次就給 ETA ⇒ `first_report_estimating` 紅。
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from api.services.ic_analysis_service import _apply_stage_progress
from momentum.Analysis import ic_filter_orchestrator as orch_mod
from momentum.Analysis.data_preprocessor import DataPreprocessor, _progress_interval
from momentum.Analysis.ic_config_schema import load_ic_config
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator


def _df(n_cols: int, n_rows: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(n_cols)
    idx = pd.date_range("2024-01-01", periods=n_rows, freq="12h")
    return pd.DataFrame(rng.normal(size=(n_rows, n_cols)), index=idx, columns=[f"f{i}" for i in range(n_cols)])


def _preprocessor() -> DataPreprocessor:
    return DataPreprocessor(load_ic_config().preprocessing.model_dump())


@pytest.mark.parametrize("n_cols", [1, 2, 3, 14, 157, 350, 1000])
def test_progress_report_count_within_bounds_not_hot_loop(n_cols):
    calls: list[dict] = []
    _preprocessor().preprocess(_df(n_cols), None, fit_mode="full_sample", progress=calls.append)
    n = len(calls)
    # CODEX-R4-P2-01：total < 3 時每欄一次（不補假回報）⇒ 下界 min(3, total)
    assert min(3, n_cols) <= n <= max(3, math.ceil(n_cols / 100)), f"n_cols={n_cols}: 回報 {n} 次"
    assert calls[-1]["done"] == calls[-1]["total"] == n_cols
    assert all(set(c) >= {"sub_step", "done", "total", "elapsed_seconds", "eta_seconds", "eta_state"} for c in calls)
    assert [c["done"] for c in calls] == sorted(c["done"] for c in calls)


def test_progress_interval_values():
    assert _progress_interval(157) == 53 and _progress_interval(299) == 100 and _progress_interval(300) == 100
    assert _progress_interval(1000) == 100 and _progress_interval(1) == 1 and DataPreprocessor.progress_interval(14) == 5


def test_first_report_is_estimating_no_fake_eta():
    calls: list[dict] = []
    _preprocessor().preprocess(_df(157), None, fit_mode="full_sample", progress=calls.append)
    assert calls[0]["eta_state"] == "estimating" and calls[0]["eta_seconds"] is None
    assert calls[-1]["eta_state"] == "done" and calls[-1]["eta_seconds"] == 0.0
    mid = [c for c in calls if 0 < c["done"] < c["total"]]
    assert all((c["eta_state"] == "estimating") == (c["eta_seconds"] is None) for c in mid)


def test_progress_done_counts_only_processed_columns(monkeypatch):
    """CODEX-R4-P2-02：回報時 `done` 必須等於**已處理完**的欄數（含 skip），不得在處理前先報。"""
    pre = _preprocessor()
    processed: list[str] = []
    real = pre._clip_series

    def spy(series, *a, **k):
        processed.append(str(series.name))
        return real(series, *a, **k)

    monkeypatch.setattr(pre, "_clip_series", spy)
    seen: list[tuple[int, int]] = []
    pre.preprocess(_df(9), None, fit_mode="full_sample", progress=lambda p: seen.append((p["done"], len(processed))))
    assert seen and all(done == n_processed for done, n_processed in seen), seen
    assert seen[-1] == (9, 9)


def test_progress_hook_exception_does_not_break_preprocess():
    def boom(_):
        raise RuntimeError("ui gone")

    df, _ = _preprocessor().preprocess(_df(30), None, fit_mode="full_sample", progress=boom)
    assert df.shape[1] == 30


def _orch_with_spy(monkeypatch, pressure):
    o = ICFilterOrchestrator(load_ic_config())
    payloads: list[dict] = []
    o._progress_callback = payloads.append
    o._memory_warned = False
    monkeypatch.setattr(orch_mod, "_memory_pressure", lambda _b: pressure)
    return o, payloads


def test_memory_warn_is_not_blocking_and_emitted_once(monkeypatch):
    detail = {"rss_bytes": 17 << 30, "phys_total_bytes": 8 << 30, "swap_used_bytes": 15 << 30,
              "swap_growth_bytes": 2 << 30, "reason": "rss_exceeds_physical"}
    o, payloads = _orch_with_spy(monkeypatch, detail)
    sub = {"sub_step": "winsorize", "done": 10, "total": 100, "eta_state": "estimating", "eta_seconds": None}
    o._stage1_progress_hook(sub)                      # 不得 raise
    o._stage1_progress_hook({**sub, "done": 20, "eta_state": "ok", "eta_seconds": 40.0})
    assert payloads[0]["warning"] == "memory_pressure_observed" and payloads[0]["warning_detail"] == detail
    assert "warning" not in payloads[1]               # 每次 analyze 至多一次
    assert payloads[0]["stage_name"] == "preprocessing" and payloads[0]["sub_done"] == 10 and payloads[0]["sub_total"] == 100
    assert "預估中" in payloads[0]["message"] and "約 40 秒" in payloads[1]["message"]
    assert 0.05 <= payloads[0]["progress"] <= 0.20


def test_no_warn_when_memory_normal(monkeypatch):
    o, payloads = _orch_with_spy(monkeypatch, None)
    o._stage1_progress_hook({"sub_step": "winsorize", "done": 50, "total": 100, "eta_state": "ok", "eta_seconds": 3.2})
    assert payloads and "warning" not in payloads[0] and payloads[0]["eta_seconds"] == 3.2


def test_memory_pressure_rules(monkeypatch):
    def snap(rss, phys, swap):
        return {"rss": rss, "phys_total": phys, "swap_used": swap}

    monkeypatch.setattr(orch_mod, "_memory_snapshot", lambda: snap(17 << 30, 8 << 30, 0))
    assert orch_mod._memory_pressure({"swap_used": 0})["reason"] == "rss_exceeds_physical"
    monkeypatch.setattr(orch_mod, "_memory_snapshot", lambda: snap(2 << 30, 8 << 30, 3 << 30))
    assert orch_mod._memory_pressure({"swap_used": 1 << 30})["reason"] == "swap_growth"
    assert orch_mod._memory_pressure({"swap_used": 3 << 30}) is None           # swap 無增長
    monkeypatch.setattr(orch_mod, "_memory_snapshot", lambda: snap(2 << 30, 8 << 30, 0))
    assert orch_mod._memory_pressure(None) is None                             # 正常 ⇒ 不發
    monkeypatch.setattr(orch_mod, "_memory_snapshot", lambda: None)
    assert orch_mod._memory_pressure(None) is None                             # 取不到 ⇒ 不猜


def test_service_stores_sub_progress_and_dedupes_warnings():
    task_info: dict = {}
    payload = {"sub_step": "winsorize", "sub_done": 53, "sub_total": 157, "eta_seconds": None, "eta_state": "estimating",
               "warning": "memory_pressure_observed", "warning_detail": {"reason": "swap_growth"}}
    _apply_stage_progress(task_info, payload, "preprocessing winsorize 53/157（ETA 預估中）")
    _apply_stage_progress(task_info, {**payload, "sub_done": 106}, "x")
    assert task_info["sub_progress"]["done"] == 106 and task_info["sub_progress"]["total"] == 157
    assert task_info["sub_progress"]["eta_state"] == "estimating" and task_info["sub_progress"]["eta_seconds"] is None
    assert task_info["warnings"] == [{"code": "memory_pressure_observed", "detail": {"reason": "swap_growth"}}]
    assert "status" not in task_info                  # WARN 不改 status、不擋


def test_report_progress_propagates_cancel_but_swallows_other_callback_errors():
    """UAT 2026-09-08：後端 Ctrl+C 後 loop 已關，分析仍跑完並洗版。callback 拋 AnalysisCancelled ⇒ 不吞、分析停下；其他例外照舊只記 warning。"""
    from momentum.core.exceptions import AnalysisCancelled

    o = ICFilterOrchestrator(load_ic_config())

    def cancel(_):
        raise AnalysisCancelled("server closed")

    o._progress_callback = cancel
    with pytest.raises(AnalysisCancelled):
        o._report_progress(1, "preprocessing", 0.1, "x")

    def boom(_):
        raise RuntimeError("ui gone")

    o._progress_callback = boom
    o._report_progress(1, "preprocessing", 0.1, "x")   # 不得 raise


def test_ws_payload_forwards_sub_progress_and_warning_fields():
    """UAT B29（2026-09-08 實機）：WS 只轉發固定欄位 ⇒ 前端永遠看不到 sub_progress。轉發集合須與 task_info 那條同源。"""
    from api.services.ic_analysis_service import _ws_stage_progress_fields

    payload = {"stage": 1, "stage_name": "preprocessing", "progress": 0.1, "message": "m",
               "sub_step": "winsorize", "sub_done": 100, "sub_total": 39373, "eta_seconds": None, "eta_state": "estimating",
               "warning": "memory_pressure_observed", "warning_detail": {"reason": "swap_growth"}}
    out = _ws_stage_progress_fields(payload)
    assert out == {k: payload[k] for k in ("sub_step", "sub_done", "sub_total", "eta_seconds", "eta_state", "warning", "warning_detail")}
    assert _ws_stage_progress_fields({"stage": 1, "progress": 0.1}) == {}     # 沒有就不補 None
    task_info: dict = {}
    _apply_stage_progress(task_info, payload, "m")
    assert task_info["sub_progress"]["total"] == out["sub_total"]              # 兩條通道同源


def test_precheck_rolling_warmup_uses_same_rule_as_stage4_and_counts_event_rows_in_test():
    """UAT 2026-09-08：切分後、預處理前先判 warmup；事件模式以「事件 ∩ 測試段」計數；規則與 stage4 同一份。"""
    config = load_ic_config()
    o = ICFilterOrchestrator(config)
    n = 400
    idx = pd.Index(1_704_067_200 + np.arange(n, dtype=np.int64) * 43_200, name="timestamp")
    features = pd.DataFrame({"f1": np.arange(n, dtype=float)}, index=idx)
    test_mask = np.zeros(n, dtype=bool)
    test_mask[-80:] = True
    ctx = {"train_mask": ~test_mask, "test_mask": test_mask, "effective_horizon": 5}
    min_required = o._rolling_warmup_min_rows(config, 5)
    assert min_required == max(o._ic_engine._adjust_rolling_windows(config.ic_calculation.rolling_windows)) + 5
    out = o._precheck_rolling_warmup(features, config, ctx, None)
    if 80 < min_required:
        assert out == {"train_rows": n - 80, "test_rows": 80, "min_test_rows": min_required, "decided_at": "precheck_before_preprocessing"}
    else:
        assert out is None
    # 事件模式：只有 3 個事件落在測試段 ⇒ test_rows=3 ⇒ 不足
    ev = [int(idx[-1]) * 1000, int(idx[-2]) * 1000, int(idx[-3]) * 1000, int(idx[10]) * 1000]  # ms
    out_ev = o._precheck_rolling_warmup(features, config, ctx, ev)
    assert out_ev is not None and out_ev["test_rows"] == 3
    # 測試段夠大 ⇒ None（不誤擋）
    big_mask = np.zeros(n, dtype=bool)
    big_mask[-(min_required + 1):] = True
    assert o._precheck_rolling_warmup(features, config, {"train_mask": ~big_mask, "test_mask": big_mask, "effective_horizon": 5}, None) is None


def test_fallback_reason_is_pushed_live_and_ws_forwards_it():
    """降級重跑原因即時進 task_info／WS，不等報告；sub_progress 歸零。"""
    from api.services.ic_analysis_service import _ws_stage_progress_fields

    payload = {"stage": 0, "stage_name": "fallback", "progress": 0.02, "message": "切分不足…",
               "fallback_reason": "rolling_warmup_insufficient",
               "fallback_details": {"train_rows": 66, "test_rows": 13, "min_test_rows": 131}}
    task_info = {"sub_progress": {"done": 5}}
    _apply_stage_progress(task_info, payload, payload["message"])
    assert task_info["fallback"] == {"reason": "rolling_warmup_insufficient", "details": payload["fallback_details"]}
    assert task_info["sub_progress"] is None
    assert _ws_stage_progress_fields(payload) == {"fallback_reason": payload["fallback_reason"], "fallback_details": payload["fallback_details"]}


def test_cancel_task_states():
    from api.services.ic_analysis_service import ICAnalysisService

    svc = ICAnalysisService()
    assert svc.cancel_task("nope") is None
    with svc._lock:
        svc._tasks["t1"] = {"task_id": "t1", "status": "running"}
        svc._tasks["t2"] = {"task_id": "t2", "status": "completed"}
    assert svc.cancel_task("t1") == "cancel_requested" and svc._tasks["t1"]["cancel_requested"] is True
    assert svc.cancel_task("t2") == "already_terminal"
    st = svc.get_task_status("t1")
    assert st["cancel_requested"] is True and st["fallback"] is None and st["warnings"] == []


def test_real_fixture_analyze_emits_sub_progress_within_bounds():
    from tests.momentum.helpers.ichc_run import run_analyze

    payloads: list[dict] = []
    report = run_analyze(None, progress_callback=payloads.append)
    subs = [p for p in payloads if "sub_total" in p]
    n_feat = int(report["metadata"]["total_features_input"])
    # fallback 重跑會再跑一次 preprocessing ⇒ 上界乘以 analyze 次數（以 stage 0 之回報次數推得）
    runs = max(1, sum(1 for p in payloads if p.get("stage") == 0))
    assert 3 <= len(subs) <= runs * max(3, math.ceil(n_feat / 100))
    assert subs[0]["eta_state"] == "estimating" and all(p["stage_name"] == "preprocessing" for p in subs)
