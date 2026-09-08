"""EVTALIGN Task 5.1：隔離區之兩塊來源分開揭露（`票 UAT-2`）。

SPEC：`docs/GAP3_EVENT_ALIGNMENT_SPEC.md` §N C6　TODO：Task 5.1

`report.metadata.isolation = {purge:{bars,source}, embargo:{bars,source}, total_bars}`，數字全取自
orchestrator 之 `ic_train_test_split`（不重算、不改算法）；只在事件路徑且切分已套用時寫；未切分不寫（不顯示 0）。
mutation（`--phase 5`）：A12 total 算錯 ⇒ `total_equals_sum` 紅；A13 source 寫死 ⇒ `source_reflects_event_lookahead` 紅。
"""

from __future__ import annotations

import json
from pathlib import Path

from api.services.ic_analysis_service import _inject_isolation_source

REPO = Path(__file__).resolve().parents[2]


def _report(applied: bool = True, purge: int = 5, embargo: int = 12, horizon: int = 5) -> dict:
    split = {"requested": True, "applied": applied, "purge_gap": purge, "embargo": embargo, "effective_horizon": horizon}
    return {"metadata": {"ic_train_test_split": split}}


def test_isolation_total_equals_sum_and_sources_nonempty():
    report = _report()
    _inject_isolation_source({"purge_rows": 12, "embargo_before_event": 0}, report)
    iso = report["metadata"]["isolation"]
    assert iso["total_bars"] == iso["purge"]["bars"] + iso["embargo"]["bars"] == 17
    assert iso["purge"]["source"] and iso["embargo"]["source"]
    assert iso["purge"]["bars"] == 5 and iso["purge"]["effective_horizon"] == 5
    # 數字與 orchestrator 之 ic_train_test_split 逐值相同（只揭露、沒改算法）
    split = report["metadata"]["ic_train_test_split"]
    assert iso["purge"]["bars"] == split["purge_gap"] and iso["embargo"]["bars"] == split["embargo"]


def test_isolation_source_reflects_event_lookahead_or_config():
    report = _report(embargo=12)
    _inject_isolation_source({"purge_rows": 12, "embargo_before_event": 3}, report)
    e = report["metadata"]["isolation"]["embargo"]
    assert e["source"] == "event_lookahead" and e["event_purge_rows"] == 12 and e["config_embargo"] == 3
    report = _report(embargo=20)
    _inject_isolation_source({"purge_rows": 12, "embargo_before_event": 20}, report)
    assert report["metadata"]["isolation"]["embargo"]["source"] == "config_embargo"
    assert report["metadata"]["isolation"]["purge"]["source"] == "global_default_horizon"


def test_isolation_absent_when_split_not_applied():
    report = _report(applied=False)
    _inject_isolation_source({"purge_rows": 12, "embargo_before_event": 0}, report)
    assert "isolation" not in report["metadata"]          # 未切分 ⇒ 不顯示（不是 0）
    report = {"metadata": {}}
    _inject_isolation_source({"purge_rows": 12}, report)
    assert "isolation" not in report["metadata"]


def test_isolation_purge_matches_split_golden_baseline():
    """與 Task 0.2 基線之 purge_gap 逐值相同：同一 config default_horizon 來源（證明只揭露、沒改算法）。"""
    golden = json.loads((REPO / "tests/golden/evtalign/split_baseline.json").read_text(encoding="utf-8"))
    case = next(c for c in golden["cases"] if c["case"] == "h5_emb0_n500")
    from tests.momentum.helpers.ichc_run import run_analyze

    report = run_analyze(None)
    split = report["metadata"].get("ic_train_test_split") or {}
    if not split.get("applied"):
        # fixture 走了 fallback ⇒ 本條無法對證切分；以 skip 以外的方式留痕（不變綠）
        raise AssertionError(f"fixture 未套用切分：{split}")
    _inject_isolation_source({"purge_rows": 0, "embargo_before_event": int(split.get("embargo") or 0)}, report)
    iso = report["metadata"]["isolation"]
    assert iso["purge"]["bars"] == case["purge_gap"] == split["purge_gap"]
    assert iso["total_bars"] == split["purge_gap"] + split["embargo"]


def test_non_event_report_unchanged_without_injection():
    """非事件 run 不呼叫本函式 ⇒ 報告無 isolation 鍵（golden 逐位元組不變）。"""
    from tests.momentum.helpers.ichc_run import run_analyze

    report = run_analyze(None)
    assert "isolation" not in report["metadata"]
