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
    """單格用之 fake analyzer。

    🔴 `GROK-R1-P2-02`（R1 閉合）：回傳形狀改為**真實**形狀——計數住 `metadata`，
    根層只有 `analysis_status`／`oos_guarantees`。原版在根上捏造 `n_features`，
    正好掩蓋了 `_scan_cell_summary` 於根層取計數（恆取不到）的洞。
    """

    def __init__(self, delay: float = 0.0, sink: Any = None):
        self.calls: List[Dict[str, Any]] = []
        self.delay = delay
        self.sink = sink            # 共享 list：記錄「哪一個 analyzer 實例跑了哪一格」

    def analyze(self, **kwargs):
        if self.delay:
            import time as _t
            _t.sleep(self.delay)
        self.calls.append(kwargs)
        if self.sink is not None:
            self.sink.append(id(self))
        return {
            "analysis_status": "ok_oos",
            "oos_guarantees": True,
            "metadata": {"n_samples": 42, "total_features_evaluated": 7},
        }


class _FakeAnalyzerFactory:
    """`create_ic_analyzer` 之替身：**每格造一個新實例**（`CODEX-R1-P1-01`）。"""

    def __init__(self, delay: float = 0.0):
        self.delay = delay
        self.instances: List[_FakeAnalyzer] = []
        self.ran_instance_ids: List[int] = []

    def __call__(self, config_override=None):
        a = _FakeAnalyzer(delay=self.delay, sink=self.ran_instance_ids)
        self.instances.append(a)
        return a

    @property
    def calls(self) -> List[Dict[str, Any]]:
        return [c for a in self.instances for c in a.calls]


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


def _run_grid(analyzer_factory, batch, progress=None):
    svc = svc_mod.ICAnalysisService()
    events: List[Dict[str, Any]] = []

    def _cb(payload):
        events.append(payload)
        if progress is not None:
            progress.append(payload)

    out = asyncio.run(svc._run_scan_grid(
        "task-scan", analyzer_factory, _Req(), batch,
        features_path=FEATURES_PATH, meta_path=None, feature_manifest_path=None,
        labels_path=None, kline_reader=None, config_override=None,
        progress_callback=_cb,
    ))
    return out, events


# ── (0) 網格形狀：恰 9 格、(k,h) 唯一、hash 互異 ───────────────────────────

def test_scan_grid_shape_is_exactly_nine_cells(bars):
    """`mk=2, mh=3` ⇒ k∈{0,1,2} × h∈{1,2,3} ＝ **9 格**；每格 `(k,h)` 唯一。"""
    analyzer = _FakeAnalyzerFactory()
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
    out, _ = _run_grid(_FakeAnalyzerFactory(), _batch(bars, scan={"decision_offset_bars_max": 2,
                                                           "horizon_bars_max": 3}))
    hashes = [c["analysis_alignment_receipt_hash"] for c in out["scan_results"]]
    assert all(h for h in hashes), "每格皆須有 hash"
    assert len(set(hashes)) == len(hashes), f"hash 須互異，實得 {len(set(hashes))}/{len(hashes)}"


def test_scan_grid_mutation_reused_spec_collapses_hashes(bars, monkeypatch):
    """🔴 **mutation 自證**：把逐格 spec 之剝離改成「恆用基準 spec」⇒ 上一條必紅。

    這正是「網格迴圈重用同一 prepared」的可觀察形態——所有格的 hash 會塌成一個。
    """
    real = svc_mod.ICAnalysisService._run_scan_cell

    def _mutated(self, analyzer_factory, request, cell_batch, **kw):
        frozen = {**cell_batch, "event_label_spec": {
            "horizon_bars": 3, "entry_price_semantic": "trigger_open",
            "label_return_mode": "open_to_horizon_close", "decision_offset_bars": 0,
        }}
        return real(self, analyzer_factory, request, frozen, **kw)

    monkeypatch.setattr(svc_mod.ICAnalysisService, "_run_scan_cell", _mutated)
    out, _ = _run_grid(_FakeAnalyzerFactory(), _batch(bars, scan={"decision_offset_bars_max": 2,
                                                           "horizon_bars_max": 3}))
    hashes = [c["analysis_alignment_receipt_hash"] for c in out["scan_results"]]
    assert len(set(hashes)) == 1, "mutation 未生效 ⇒ 上一條之斷言不可證偽"


def test_scan_grid_axis_defaults_to_single_value_when_max_absent(bars):
    """只給 `horizon_bars_max` ⇒ k 軸維持 spec 之單值（**不是**整條掃）。"""
    out, _ = _run_grid(_FakeAnalyzerFactory(), _batch(bars, k=2, scan={"horizon_bars_max": 3}))
    assert out["scan_total"] == 3
    assert sorted({c["k"] for c in out["scan_results"]}) == [2]
    assert sorted(c["h"] for c in out["scan_results"]) == [1, 2, 3]


# ── (0) 續：超上限 ⇒ scan_grid_too_large ───────────────────────────────────

def test_scan_grid_too_large_is_rejected_without_running_any_cell(bars):
    """`mk=20, mh=20` ⇒ 21×20＝420 > 110（契約上限）⇒ `unavailable`，且**一格都不跑**。"""
    analyzer = _FakeAnalyzerFactory()
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
    out, _ = _run_grid(_FakeAnalyzerFactory(), _batch(bars, scan={"decision_offset_bars_max": 10,
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
        _FakeAnalyzerFactory(),
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
    out, _ = _run_grid(_FakeAnalyzerFactory(delay=0.2),
                       _batch(bars, scan={"horizon_bars_max": 2}))
    assert out["scan_total"] == 2
    reasons = {c["reason"] for c in out["scan_results"]}
    assert reasons == {svc_mod.ICAnalysisService.SCAN_REASON_CELL_TIMEOUT}
    assert all(c["capability"] == "unavailable" for c in out["scan_results"])
    # 🔴 逾時之格仍**出現在結果裡**（不是被丟掉）——否則使用者看不出哪一格沒跑
    assert sorted(c["h"] for c in out["scan_results"]) == [1, 2]


def test_scan_grid_progress_reports_scan_done_and_total(bars):
    """進度事件須帶 `scan_done`／`scan_total`（走既有 progress 通道，不另開）。"""
    _, events = _run_grid(_FakeAnalyzerFactory(), _batch(bars, scan={"horizon_bars_max": 3}))
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


# ── R1 閉合：`CODEX-R1-P1-01` 之所有權隔離、`GROK-R1-P2-02` 之投影鍵 ──────────

def test_scan_grid_each_cell_gets_its_own_analyzer(bars):
    """🔴 `CODEX-R1-P1-01`：每格用**自己的** analyzer 實例（逾時之殘存 worker 碰不到他格）。

    `asyncio.wait_for` 只取消 await、**不會停掉已在跑的 thread**，而
    `ICFilterOrchestrator` 持有 `_ic_cache`／`_report`／`_filtered_features_df` 等可變欄位
    ⇒ 共用一個實例時，逾時之格仍會在背景改下一格（與網格後主分析）正在用的狀態。
    """
    factory = _FakeAnalyzerFactory()
    out, _ = _run_grid(factory, _batch(bars, scan={"decision_offset_bars_max": 2,
                                                   "horizon_bars_max": 3}))
    assert out["scan_done"] == 9
    # 9 格 ⇒ 造了 9 個實例，且**每個都只跑一次**（沒有任何實例被兩格共用）
    assert len(factory.instances) == 9
    assert len(set(factory.ran_instance_ids)) == 9
    assert all(len(a.calls) == 1 for a in factory.instances)


def test_scan_grid_cell_receives_its_own_embargo_override(bars):
    """每格之 analyzer 以**該格**的 `config_override`（含 embargo）建構，不是共用一份。"""
    seen: List[Any] = []

    class _RecordingFactory(_FakeAnalyzerFactory):
        def __call__(self, config_override=None):
            seen.append(dict(config_override or {}))
            return super().__call__(config_override)

    out, _ = _run_grid(_RecordingFactory(), _batch(bars, scan={"horizon_bars_max": 2}))
    assert out["scan_done"] == 2
    assert len(seen) == 2
    assert all("embargo" in o for o in seen), "每格之 override 須帶自己的 embargo"


def test_scan_cell_summary_reads_metadata_not_only_root(bars):
    """🔴 `GROK-R1-P2-02`：計數住 `metadata` 也要取得到（真實 analyzer 之形狀）。"""
    summarize = svc_mod.ICAnalysisService._scan_cell_summary
    # 真實形狀：根層只有 status，計數在 metadata
    real_shape = {
        "analysis_status": "ok_oos", "oos_guarantees": True,
        "metadata": {"n_samples": 42, "total_features_evaluated": 7},
    }
    got = summarize(real_shape)
    assert got["n_samples"] == 42
    assert got["total_features_evaluated"] == 7
    assert got["analysis_status"] == "ok_oos"
    # 舊 fake 形狀（根層計數）仍取得到——修法是「逐層取」，不是「改讀另一處」
    assert summarize({"analysis_status": "ok", "n_features": 3})["n_features"] == 3
    # 🔴 兩處皆無 ⇒ **不填假值**
    assert "n_samples" not in (summarize({"analysis_status": "ok"}) or {})
    assert summarize(None) is None


def test_scan_grid_cell_summary_is_populated_from_real_shape(bars):
    """端到端：格子之 `ic_summary` 真的帶得到計數（原版恆為只有 status）。"""
    out, _ = _run_grid(_FakeAnalyzerFactory(), _batch(bars, scan={"horizon_bars_max": 2}))
    for cell in out["scan_results"]:
        assert cell["ic_summary"]["n_samples"] == 42, f"格 {cell['k']},{cell['h']} 之摘要缺計數"


# ── R1 閉合：`CODEX-R1-P2-04` bounds 母體須與實際 IC 母體同源 ────────────────

def test_bounds_scope_is_limited_to_run_symbol(bars):
    """🔴 他 symbol 之事件**不得**壓低上界——它們也不進本次 IC（具名排除）。

    codex 實跑之反例：ETH-only `k_max=119`，混入一筆 BTC 尾端事件後變 `no_feasible_k`。
    """
    eth_only = _batch(bars)
    base = svc_mod.ICAnalysisService._event_k_disclosure(_Req(), eth_only)
    assert base["k_bound_status"] == "bounded"

    n = len(bars[SYMBOL][TF])
    ot = bars[SYMBOL][TF]["open_time_ms"].to_numpy()
    alien = dict(make_event(99, t0=int(ot[n - 2]), label=1, direction="long"))
    alien["symbol"] = "BTCUSDT"
    alien["decision_offset_bars"] = 0
    alien["entry_price_semantic"] = "trigger_open"
    alien["label_definition"] = {
        **dict(alien.get("label_definition") or {}),
        "label_return_mode": "open_to_horizon_close",
        "window": {"horizon_bars": 3},
    }
    mixed = {**eth_only, "records": [*eth_only["records"], alien]}
    got = svc_mod.ICAnalysisService._event_k_disclosure(_Req(), mixed)

    # 上界與純 ETH 批**相同**（他 symbol 不計入）
    assert got["k_max_feasible_at_h"] == base["k_max_feasible_at_h"]
    assert got["h_max_feasible_at_k"] == base["h_max_feasible_at_k"]
    # 🔴 且**說出**上界是對誰算的、排除了幾筆（不讓它變成暗知識）
    assert got["bounds_scope_symbol"] == SYMBOL
    assert got["bounds_scope_excluded_events"] == 1


def test_bounds_scope_without_run_symbol_uses_whole_batch(bars):
    """over 向：未指定 run symbol ⇒ 對全批算，且 `bounds_scope_symbol` 為 `None`（不謊報）。"""
    class _NoSymbolReq(_Req):
        symbol = None

    got = svc_mod.ICAnalysisService._event_k_disclosure(_NoSymbolReq(), _batch(bars))
    assert got["bounds_scope_symbol"] is None
    assert got["bounds_scope_excluded_events"] == 0
