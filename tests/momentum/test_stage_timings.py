"""FU-3（併入 EVTLABEL P1）：報告逐 stage 耗時揭露 `metadata.stage_timings`。

出生理由：報告完全沒有分段耗時 ⇒「多 horizon 會多久」「哪段該加速」只能猜；
主委 2026-09-10 因此把事件 run 成本估錯一個量級。GLOBALH（多 horizon 全算）之前置。

守三件事：
1. 裝飾器真的記時且**累加**（同 stage 多次呼叫不覆蓋）。
2. `_attach_stage_timings` 只在有資料時寫，且寫進 metadata。
3. golden 不受影響：`canonical_sha` 把 `stage_timings` 當時鐘鍵排除（值不同 ⇒ sha 仍相等）。
"""

from __future__ import annotations

import time

import pytest

from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator, _timed_stage
from tests.momentum.helpers.ichc_run import canonical_sha


class _Dummy:
    @_timed_stage("stageX")
    def work(self, seconds: float = 0.0, boom: bool = False):
        if seconds:
            time.sleep(seconds)
        if boom:
            raise RuntimeError("boom")
        return "ok"


def test_decorator_records_and_accumulates():
    d = _Dummy()
    assert d.work() == "ok"
    first = d._stage_timings["stageX"]
    assert first >= 0.0
    d.work()
    assert d._stage_timings["stageX"] >= first, "同名 stage 第二次呼叫必須累加，不得覆蓋"


def test_decorator_records_even_when_stage_raises():
    d = _Dummy()
    with pytest.raises(RuntimeError):
        d.work(boom=True)
    assert "stageX" in d._stage_timings, "stage 拋例外時仍須留下耗時（finally）"


def test_attach_writes_into_metadata_only_when_present():
    orch = object.__new__(ICFilterOrchestrator)
    report: dict = {"metadata": {}}
    ICFilterOrchestrator._attach_stage_timings(orch, report)
    assert "stage_timings" not in report["metadata"], "無資料時不得寫空殼鍵"

    orch._stage_timings = {"stage4_ic_calculation": 2.5, "stage1_preprocessing": 11.0}
    ICFilterOrchestrator._attach_stage_timings(orch, report)
    assert report["metadata"]["stage_timings"] == {
        "stage1_preprocessing": 11.0,
        "stage4_ic_calculation": 2.5,
    }
    assert list(report["metadata"]["stage_timings"]) == sorted(report["metadata"]["stage_timings"])


def test_all_nine_stages_are_instrumented():
    """新增 stage 卻忘了掛計時 ⇒ 本條紅（防「加了段卻看不到成本」）。"""
    expected = {
        "_stage0_ingestion",
        "_stage1_preprocessing",
        "_stage2_label_generation",
        "_stage3_event_filter",
        "_stage4_ic_calculation",
        "_stage5_statistical_validation",
        "_stage6_redundancy",
        "_stage6b_marginal_ic",
        "_stage7_report",
    }
    for name in expected:
        fn = getattr(ICFilterOrchestrator, name)
        assert getattr(fn, "__wrapped__", None) is not None, f"{name} 未掛 @_timed_stage"


def test_stage_timings_excluded_from_golden_sha():
    """耗時非決定性 ⇒ 不得進 golden 比對範圍（否則每跑一次 golden 就紅）。"""
    base = {"metadata": {"a": 1}, "summary_table": []}
    r1 = {"metadata": {"a": 1, "stage_timings": {"stage4_ic_calculation": 1.0}}, "summary_table": []}
    r2 = {"metadata": {"a": 1, "stage_timings": {"stage4_ic_calculation": 999.0}}, "summary_table": []}
    assert canonical_sha(r1) == canonical_sha(r2) == canonical_sha(base)
