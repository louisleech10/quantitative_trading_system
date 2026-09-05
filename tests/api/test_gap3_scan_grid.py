"""GAP-3 `G3-D2` **Task D4.3** — `event_label_scan` 網格與 k 之雙值揭露。

選擇器：`pytest tests/api -q -k gap3_scan_grid`

驗收（`D-006` D4.3「驗證」欄逐條）：
- (0) `scan={mk:2, mh:3}` ⇒ `scan_results` **恰 9 格**、`(k,h)` 唯一、**hash 互異**；
      超可行域之格 `unavailable` 而他格有值；`mk=20, mh=20` ⇒ `scan_grid_too_large`；
      mutation：網格重用同一 `prepared_token` ⇒ hash 互異之斷言必紅。
- (ii) 缺揭露欄 ⇒ `unavailable:missing_decision_offset_disclosure`。
- (iii) **經分析路徑回傳**之兩上界對真實 kline 三事件手算相等
      （含一 `decision_bar_open × open_to_horizon_close`，證明 k／h 耦合真的接上了）。

🔴 **具名邊界**：本檔之 `analyzer` 是 fake（`analyze` 回固定 dict）。被測的是**網格編排**
——格數、逐格 spec 之剝離、每格獨立 receipt、逾時與上限之處置。**不測** IC 引擎本身
（那是 `ic_engine` 的測試面，且真跑一格需要已物化 feature run）。此邊界刻意寫出。
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import pytest

from api.services import ic_analysis_service as svc_mod
from momentum.Analysis.event_samples import pipeline as pipeline_mod
from tests.momentum.event_samples.helpers import load_bars, make_event

SYMBOL = "ETHUSDT"
TF = "12h"
FEATURES_PATH = "data_cache/features/BCHUSDT/1h/4a8a0b3726cc906ab3534994605e77f5/x.h5"


@pytest.fixture(scope="module")
def bars():
    return load_bars(SYMBOL, (TF,))


@pytest.fixture(autouse=True)
def _real_bars(bars, monkeypatch):
    """把 kline 載入指向已載入之真實 bar 表（避免每格重讀 HDF5）。"""
    monkeypatch.setattr(
        pipeline_mod.EventSamplePipeline, "bars_from_kline_cache",
        staticmethod(lambda symbols, timeframes, **kw: bars),
    )


class _Req:
    event_import_id = "imp-scan"
    event_timestamps = None
    timeframe = TF
    symbol = SYMBOL
    event_label_scan = None


class _FakeAnalyzer:
    """只記錄被呼叫幾次並回固定報告；不做任何統計。"""

    def __init__(self, delay: float = 0.0):
        self.calls: List[Dict[str, Any]] = []
        self.delay = delay

    def analyze(self, **kwargs):
        if self.delay:
            import time as _t
            _t.sleep(self.delay)
        self.calls.append(kwargs)
        return {"analysis_status": "ok_oos", "oos_guarantees": True, "n_features": 3}


def _records(bars, *, t0_idxs=(120, 180, 240), entry="trigger_open",
             mode="open_to_horizon_close", k=0, h=3):
    ot = bars[SYMBOL][TF]["open_time_ms"].to_numpy()
    out = []
    for i, idx in enumerate(t0_idxs):
        rec = dict(make_event(i, t0=int(ot[idx]), label=i % 2, direction="long"))
        rec["decision_offset_bars"] = k
        rec["entry_price_semantic"] = entry
        ld = dict(rec.get("label_definition") or {})
        ld["label_return_mode"] = mode
        ld["window"] = {**dict(ld.get("window") or {}), "horizon_bars": h}
        rec["label_definition"] = ld
        out.append(rec)
    return out


def _batch(bars, *, scan=None, entry="trigger_open", mode="open_to_horizon_close",
           k=0, h=3, t0_idxs=(120, 180, 240), with_disclosure=True):
    recs = _records(bars, t0_idxs=t0_idxs, entry=entry, mode=mode, k=k, h=h)
    batch: Dict[str, Any] = {
        "records": recs,
        "event_label_spec": {
            "horizon_bars": h, "entry_price_semantic": entry,
            "label_return_mode": mode, "decision_offset_bars": k,
        },
        "lookahead_bars_declared": {TF: 0},
        "event_label_scan": scan,
    }
    if with_disclosure:
        batch["decision_offset_bars_record_values"] = sorted({int(r["decision_offset_bars"]) for r in recs})
        batch["decision_offset_bars_analysis"] = k
    return batch


def _run_grid(analyzer, batch, progress=None):
    svc = svc_mod.ICAnalysisService()
    events: List[Dict[str, Any]] = []

    def _cb(payload):
        events.append(payload)
        if progress is not None:
            progress.append(payload)

    out = asyncio.run(svc._run_scan_grid(
        "task-scan", analyzer, _Req(), batch,
        features_path=FEATURES_PATH, meta_path=None, feature_manifest_path=None,
        labels_path=None, kline_reader=None, config_override=None,
        progress_callback=_cb,
    ))
    return out, events


# ── (0) 網格形狀：恰 9 格、(k,h) 唯一、hash 互異 ───────────────────────────

def test_scan_grid_shape_is_exactly_nine_cells(bars):
    """`mk=2, mh=3` ⇒ k∈{0,1,2} × h∈{1,2,3} ＝ **9 格**；每格 `(k,h)` 唯一。"""
    analyzer = _FakeAnalyzer()
    out, _ = _run_grid(analyzer, _batch(bars, scan={"decision_offset_bars_max": 2,
                                                    "horizon_bars_max": 3}))
    assert out["capability"] == "available" and out["reason"] is None
    assert out["scan_total"] == 9 and out["scan_done"] == 9
    cells = out["scan_results"]
    assert len(cells) == 9
    assert sorted((c["k"], c["h"]) for c in cells) == [
        (k, h) for k in (0, 1, 2) for h in (1, 2, 3)
    ]
    assert len(analyzer.calls) == 9, "每格各跑一次條件 IC"


def test_scan_grid_each_cell_has_its_own_receipt_hash(bars):
    """🔴 **每格獨立 `analysis_alignment_receipt_hash`**：9 格 ⇒ 9 個互異 hash。

    重用 prepare 之產物會讓「用 k=0 對齊、用 k=2 算值」這種錯配全綠；
    hash 互異就是那件事的可證偽形態。
    """
    out, _ = _run_grid(_FakeAnalyzer(), _batch(bars, scan={"decision_offset_bars_max": 2,
                                                           "horizon_bars_max": 3}))
    hashes = [c["analysis_alignment_receipt_hash"] for c in out["scan_results"]]
    assert all(h for h in hashes), "每格皆須有 hash"
    assert len(set(hashes)) == len(hashes), f"hash 須互異，實得 {len(set(hashes))}/{len(hashes)}"


def test_scan_grid_mutation_reused_spec_collapses_hashes(bars, monkeypatch):
    """🔴 **mutation 自證**：把逐格 spec 之剝離改成「恆用基準 spec」⇒ 上一條必紅。

    這正是「網格迴圈重用同一 prepared」的可觀察形態——所有格的 hash 會塌成一個。
    """
    real = svc_mod.ICAnalysisService._run_scan_cell

    def _mutated(self, analyzer, request, cell_batch, **kw):
        frozen = {**cell_batch, "event_label_spec": {
            "horizon_bars": 3, "entry_price_semantic": "trigger_open",
            "label_return_mode": "open_to_horizon_close", "decision_offset_bars": 0,
        }}
        return real(self, analyzer, request, frozen, **kw)

    monkeypatch.setattr(svc_mod.ICAnalysisService, "_run_scan_cell", _mutated)
    out, _ = _run_grid(_FakeAnalyzer(), _batch(bars, scan={"decision_offset_bars_max": 2,
                                                           "horizon_bars_max": 3}))
    hashes = [c["analysis_alignment_receipt_hash"] for c in out["scan_results"]]
    assert len(set(hashes)) == 1, "mutation 未生效 ⇒ 上一條之斷言不可證偽"


def test_scan_grid_axis_defaults_to_single_value_when_max_absent(bars):
    """只給 `horizon_bars_max` ⇒ k 軸維持 spec 之單值（**不是**整條掃）。"""
    out, _ = _run_grid(_FakeAnalyzer(), _batch(bars, k=2, scan={"horizon_bars_max": 3}))
    assert out["scan_total"] == 3
    assert sorted({c["k"] for c in out["scan_results"]}) == [2]
    assert sorted(c["h"] for c in out["scan_results"]) == [1, 2, 3]


# ── (0) 續：超上限 ⇒ scan_grid_too_large ───────────────────────────────────

def test_scan_grid_too_large_is_rejected_without_running_any_cell(bars):
    """`mk=20, mh=20` ⇒ 21×20＝420 > 110（契約上限）⇒ `unavailable`，且**一格都不跑**。"""
    analyzer = _FakeAnalyzer()
    out, _ = _run_grid(analyzer, _batch(bars, scan={"decision_offset_bars_max": 20,
                                                    "horizon_bars_max": 20}))
    assert out["capability"] == "unavailable"
    assert out["reason"] == svc_mod.ICAnalysisService.SCAN_REASON_TOO_LARGE
    assert out["scan_total"] == 420 and out["scan_done"] == 0
    assert out["scan_results"] == []
    assert analyzer.calls == [], "超上限時不得部分執行"


def test_scan_grid_max_runs_comes_from_contract_not_hardcoded(bars):
    """上限值取自契約 `analysis_params.scan_grid_max_runs`（改契約即改行為）。"""
    from momentum.factories import create_event_sample_pipeline

    params = create_event_sample_pipeline().analysis_params()
    assert params["scan_grid_max_runs"] == 110, "benchmark 凍結值（見 receipt）"
    # 恰好等於上限 ⇒ 放行（邊界之 over 向：不得把 `==` 也擋掉）
    out, _ = _run_grid(_FakeAnalyzer(), _batch(bars, scan={"decision_offset_bars_max": 10,
                                                           "horizon_bars_max": 10}))
    assert out["capability"] == "available" and out["scan_total"] == 110


# ── (0) 續：超可行域之格 unavailable，他格仍有值 ────────────────────────────

def test_scan_grid_infeasible_cell_is_unavailable_without_killing_others(bars):
    """t0 落在資料最前（bar index 1、2）⇒ **k=3 全批暖機不足**（該格 `unavailable`），
    而 k=0／1 之格照常算得出來。

    🔴 判準是**全批**不可行才 `unavailable`：部分事件不可行時它們逐條進 failures，
    該格仍有值（`D-001` D4.2「全批不可行 ⇒ unavailable」）。
    """
    out, _ = _run_grid(
        _FakeAnalyzer(),
        _batch(bars, t0_idxs=(1, 2), mode="close_to_close", entry="trigger_close", h=1,
               scan={"decision_offset_bars_max": 3, "horizon_bars_max": 1}),
    )
    cells = {c["k"]: c for c in out["scan_results"]}
    assert cells[0]["capability"] == "available", "k=0 之格須算得出來"
    assert cells[1]["capability"] == "available", "k=1 之格（兩事件皆 t0_idx>=1）須算得出來"
    assert cells[3]["capability"] == "unavailable", "k=3 ⇒ 兩事件皆 t0_idx-k<0 ⇒ 全批不可行"
    # 🔴 不可因一格 unavailable 而少跑其他格
    assert out["scan_total"] == 4 and out["scan_done"] == 4
    assert {c["k"] for c in out["scan_results"]} == {0, 1, 2, 3}


# ── (0) 續：逾時 ⇒ 該格 unavailable、保留 partial ──────────────────────────

def test_scan_grid_cell_timeout_keeps_partial_results(bars, monkeypatch):
    """單格逾時 ⇒ 該格 `scan_cell_timeout`，其餘格照常完成（partial 保留）。"""
    from momentum.factories import create_event_sample_pipeline

    real_params = create_event_sample_pipeline().analysis_params()
    monkeypatch.setattr(
        pipeline_mod.EventSamplePipeline, "analysis_params",
        staticmethod(lambda: {**real_params, "per_cell_timeout_s": 0.05}),
    )
    # 每格 fake analyzer 睡 0.2s > 0.05s 之單格上限 ⇒ 全部逾時
    out, _ = _run_grid(_FakeAnalyzer(delay=0.2),
                       _batch(bars, scan={"horizon_bars_max": 2}))
    assert out["scan_total"] == 2
    reasons = {c["reason"] for c in out["scan_results"]}
    assert reasons == {svc_mod.ICAnalysisService.SCAN_REASON_CELL_TIMEOUT}
    assert all(c["capability"] == "unavailable" for c in out["scan_results"])
    # 🔴 逾時之格仍**出現在結果裡**（不是被丟掉）——否則使用者看不出哪一格沒跑
    assert sorted(c["h"] for c in out["scan_results"]) == [1, 2]


def test_scan_grid_progress_reports_scan_done_and_total(bars):
    """進度事件須帶 `scan_done`／`scan_total`（走既有 progress 通道，不另開）。"""
    _, events = _run_grid(_FakeAnalyzer(), _batch(bars, scan={"horizon_bars_max": 3}))
    scan_events = [e for e in events if "scan_total" in e]
    assert len(scan_events) == 3
    assert [e["scan_done"] for e in scan_events] == [1, 2, 3]
    assert {e["scan_total"] for e in scan_events} == {3}
    assert scan_events[-1]["progress"] == pytest.approx(1.0)


# ── (ii) 缺揭露欄 ⇒ unavailable ───────────────────────────────────────────

def test_k_disclosure_missing_field_is_unavailable(bars):
    """缺 `decision_offset_bars_record_values`／`_analysis` ⇒ `unavailable` 具名 reason。"""
    batch = _batch(bars, with_disclosure=False)
    out = svc_mod.ICAnalysisService._event_k_disclosure(_Req(), batch)
    assert out["decision_offset_bars_capability"] == "unavailable"
    assert out["decision_offset_bars_reason"] == \
        svc_mod.ICAnalysisService.SCAN_REASON_MISSING_K_DISCLOSURE
    # over 向：兩欄齊全 ⇒ available（證明上一條不是「恆 unavailable」）
    ok = svc_mod.ICAnalysisService._event_k_disclosure(_Req(), _batch(bars))
    assert ok["decision_offset_bars_capability"] == "available"
    assert ok["decision_offset_bars_reason"] is None


# ── (iii) 兩上界經分析路徑回傳，且與手算相等 ───────────────────────────────

@pytest.mark.parametrize("entry,mode", [
    ("trigger_open", "open_to_horizon_close"),
    # 🔴 這一組證明 k／h **耦合**真的接到揭露欄（`end_idx = t0_idx − k + h`）
    ("decision_bar_open", "open_to_horizon_close"),
])
def test_k_disclosure_bounds_match_hand_computation(bars, entry, mode):
    """`_event_k_disclosure` 回傳之兩上界＝producer `feasible_bounds` 之值（只投影不重算）。"""
    from momentum.Analysis.event_samples.label_value_from_case import (
        end_bar_index, entry_bar_index, feasible_bounds,
    )

    k, h = 2, 3
    batch = _batch(bars, entry=entry, mode=mode, k=k, h=h)
    out = svc_mod.ICAnalysisService._event_k_disclosure(_Req(), batch)
    assert out["decision_offset_bars_capability"] == "available"

    want = feasible_bounds(batch["records"], bars,
                           event_label_spec=batch["event_label_spec"], timeframes=(TF,))
    assert out["k_max_feasible_at_h"] == want.k_max_feasible_at_h
    assert out["h_max_feasible_at_k"] == want.h_max_feasible_at_k
    assert out["k_bound_status"] == want.k_status
    assert out["h_bound_status"] == want.h_status

    # 三事件手算（測試側獨立算一次，不呼叫 producer 之 bounds）
    df = bars[SYMBOL][TF]
    n = len(df)
    ot = df["open_time_ms"].to_numpy()
    cov_min_idx = int(ot.searchsorted(int(df["close_time_ms"].to_numpy()[0]), side="left"))
    k_hand, h_hand = [], []
    for rec in batch["records"]:
        t0_idx = int((ot == int(rec["t0"])).nonzero()[0][0])
        k_hand.append(min(t0_idx, t0_idx - cov_min_idx))
        e1 = end_bar_index(mode, t0_idx=t0_idx,
                           entry_idx=entry_bar_index(entry, t0_idx=t0_idx, k=k), h=1)
        h_hand.append(n - 1 - e1 + 1)
    assert out["k_max_feasible_at_h"] == min(k_hand)
    assert out["h_max_feasible_at_k"] == min(h_hand)


def test_k_disclosure_reports_both_record_and_analysis_k(bars):
    """🔴 雙值揭露：記錄值集合與本次分析 k **分開回傳**（同名不同義，不得合成一個）。"""
    batch = _batch(bars, k=1)
    out = svc_mod.ICAnalysisService._event_k_disclosure(_Req(), batch)
    assert out["decision_offset_bars_record_values"] == [1]
    assert out["decision_offset_bars_analysis"] == 1
    assert "decision_offset_bars_record_values" in out and "decision_offset_bars_analysis" in out
