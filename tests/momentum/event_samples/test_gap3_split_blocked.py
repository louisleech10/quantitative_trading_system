"""GAP-3 UX Task 1.12 驗證（-k split_blocked）：不可證則禁進切分（D-7 之 L3）。

判準字面之唯一來源＝`docs/GAP3_EVENT_UX_SPEC.md` Task 1.12「驗證」欄（①②③③b③c④）；
本檔只把它機械化。

🔴 ①採**執行期探針**（monkeypatch `pipeline.split_events` 計數）而非原始碼形狀斷言——
   「掃 `run_event_study_only()` 原始碼裡沒有 `split_events` 字樣」那種形狀 oracle 在本 epic
   已被繞過三次（B1 R3／B2 R1／B2 R2）。計數 `== 0` 是執行期事實，assignment／subclass／
   間接呼叫全都關得住。
🔴 ①同時斷言**表有產出**：若只斷言「沒呼叫切分」，一條 raise 在最前面的實作也會綠（假綠）。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from momentum.Analysis.event_samples import pipeline as pipeline_mod
from momentum.Analysis.event_samples.ic_feed import build_event_ic_inputs
from momentum.Analysis.event_samples.import_contract import load_event_import_contract
from momentum.Analysis.event_samples.lookahead_gate import (
    LookaheadGate,
    SplitBlockedError,
    split_blocked_reason,
)
from momentum.Analysis.event_samples.pipeline import EventPipelineConfig, EventSamplePipeline
from momentum.Analysis.event_samples.tables import event_forward_return_table
from momentum.Analysis.event_samples.types import EventSplitPlan
from tests.momentum.event_samples.helpers import load_bars, make_event

BASE = 1704067200000
H12 = 43200000
HORIZONS = (1, 2, 4)
REPO = Path(__file__).resolve().parents[3]

#: 深度不可證之批（L2 宣告缺失）——本檔全部情境共用同一個閘。
BLOCKED = LookaheadGate.blocked_by("未填答案窗宣告，深度不可證（測試）", ("my_custom_signal",))


@pytest.fixture(scope="module")
def bars():
    return load_bars("ETHUSDT", ("12h",))


@pytest.fixture(scope="module")
def records():
    return [make_event(i, t0=BASE + n * H12, label=i % 2) for i, n in enumerate((300, 600, 900, 1200))]


@pytest.fixture
def spy_split(monkeypatch):
    """執行期探針：把 `pipeline` 命名空間裡的 `split_events` 換成計數器。"""
    calls = []
    real = pipeline_mod.split_events

    def counting(*args, **kwargs):
        calls.append((args, kwargs))
        return real(*args, **kwargs)

    monkeypatch.setattr(pipeline_mod, "split_events", counting)
    return calls


def _study_only(records, bars):
    return EventSamplePipeline().run_event_study_only(
        records, bars, EventPipelineConfig(timeframes=("12h",)))


# ── ① 該批呼叫 analyze ⇒ 切分**未被呼叫**（且表確實產得出來） ────────────────
def test_gap3_split_blocked_01_event_study_only_never_calls_split_events(records, bars, spy_split):
    res = _study_only(records, bars)
    tables = EventSamplePipeline().analyze_tables(res, bars, horizons=HORIZONS, n_boot=50)

    assert spy_split == []                                   # 執行期事實：一次都沒呼叫
    assert res.split_plan is None                            # 不是空的假 plan
    assert res.summary["execution_mode"] == "event_study_only"
    assert tables["event_forward_return_table"]["receipts"]["n_rows"] > 0   # 有產出，非「raise 在最前面」的假綠


# ── ① 封鎖之批走 run()（切分路徑）⇒ raise，且切分仍未被呼叫 ─────────────────
def test_gap3_split_blocked_01b_run_raises_before_calling_split_events(records, bars, spy_split):
    with pytest.raises(SplitBlockedError) as exc:
        EventSamplePipeline().run(records, bars, EventPipelineConfig(timeframes=("12h",)), lookahead_gate=BLOCKED)
    assert exc.value.reason == split_blocked_reason()
    assert spy_split == []


# ── ② 條件 IC ⇒ capability unavailable ＋ 契約 reason ──────────────────────
def test_gap3_split_blocked_02_conditional_ic_capability_unavailable(records, bars):
    res = _study_only(records, bars)
    out = build_event_ic_inputs(res.manifest, None, res.events, res.receipts,
                                timeframe="12h", lookahead_gate=BLOCKED)
    assert out["capability_status"] == "unavailable"
    assert out["reason"] == split_blocked_reason()
    assert out["event_timestamps"] == [] and out["event_label_values"] == {}


# ── ③ 事件研究表仍可產出 ───────────────────────────────────────────────────
def test_gap3_split_blocked_03_event_study_table_still_produced(records, bars):
    res = _study_only(records, bars)
    tables = EventSamplePipeline().analyze_tables(res, bars, horizons=HORIZONS, n_boot=50)
    fwd = tables["event_forward_return_table"]
    assert len(fwd["sensitivity_micro"]) == len(HORIZONS)
    assert fwd["receipts"]["n_rows"] > 0


# ── ③b event_split_plan=None ⇒ 每個 horizon 之 ci 為 "unavailable"（非數值區間） ──
def test_gap3_split_blocked_03b_ci_unavailable_when_no_split_plan(records, bars):
    res = _study_only(records, bars)
    fwd = event_forward_return_table(res.manifest, res.receipts, bars, None,
                                     {"horizons": list(HORIZONS), "seed": 1, "n_boot": 50})
    for h in HORIZONS:
        assert fwd["sensitivity_micro"][str(h)]["ci"] == "unavailable"
        assert fwd["uniqueness_weighted"][str(h)]["ci"] == "unavailable"
    assert fwd["common"]["formal_pooled_inference_allowed"] is False
    assert fwd["common"]["reason"] == "no_event_split_plan"


# ── ③c clusters 為空之**假** split plan ⇒ raise（不得靜默當 None） ──────────
def test_gap3_split_blocked_03c_fake_empty_split_plan_raises(records, bars):
    res = _study_only(records, bars)
    fake = EventSplitPlan(
        assignments=pd.DataFrame(columns=["event_id", "symbol", "split_label"]),
        purged=pd.DataFrame(columns=["event_id", "reason"]),
        clusters=pd.DataFrame(columns=["event_id", "time_cluster_id", "cluster_weight"]),
        summary={},
    )
    with pytest.raises(ValueError, match="clusters"):
        event_forward_return_table(res.manifest, res.receipts, bars, fake,
                                   {"horizons": list(HORIZONS), "seed": 1, "n_boot": 50})


# ── ④ reason 字面取自契約，且**未**硬寫進 api/ frontend/src/ momentum/ 之 .py/.ts ──
def _literal_hits(roots, suffixes, needle: str) -> int:
    total = 0
    for root in roots:
        for p in (REPO / root).rglob("*"):
            if p.suffix in suffixes and p.is_file():
                total += p.read_text(encoding="utf-8", errors="ignore").count(needle)
    return total


def test_gap3_split_blocked_04_reason_literal_lives_only_in_contract():
    reason = split_blocked_reason()
    assert reason in load_event_import_contract()["capability_unavailable_reasons"]

    roots = ("api", "frontend/src", "momentum")
    # 鑑別力自證：同一支掃描器對**已知會紅**的輸入（契約 JSON）必須數得到，否則 == 0 毫無意義
    assert _literal_hits(roots, {".json"}, reason) > 0
    assert _literal_hits(roots, {".py", ".ts"}, reason) == 0
