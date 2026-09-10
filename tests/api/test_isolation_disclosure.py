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
    """🔴 EVTLABEL Task 2.3 語意更新（非放寬）：embargo 之來源改由**深度**判定。

    改前用 `purge_rows`（＝max(深度, 答案窗)）判，答案窗比深度長時會把 embargo 誤標成
    「事件 look-ahead 抬的」——實際上抬它的是答案窗，而答案窗現在歸 purge 管（Task 2.2）。
    """
    report = _report(embargo=12)
    _inject_isolation_source(
        {"lookahead_depth_rows": 12, "label_window_rows": 4, "purge_rows": 12, "embargo_before_event": 3}, report
    )
    e = report["metadata"]["isolation"]["embargo"]
    assert e["source"] == "event_lookahead_depth"
    assert e["lookahead_depth_rows"] == 12 and e["config_embargo"] == 3
    assert e["event_purge_rows"] == 12  # 舊欄保留供對照

    report = _report(embargo=20)
    _inject_isolation_source(
        {"lookahead_depth_rows": 12, "label_window_rows": 4, "purge_rows": 12, "embargo_before_event": 20}, report
    )
    assert report["metadata"]["isolation"]["embargo"]["source"] == "config_embargo"


def test_embargo_source_no_longer_credits_label_window():
    """答案窗 156 > 深度 144：embargo 只由深度抬 ⇒ 深度未超過 config 時仍標 config_embargo。"""
    report = _report(embargo=200)
    _inject_isolation_source(
        {"lookahead_depth_rows": 144, "label_window_rows": 156, "purge_rows": 156, "embargo_before_event": 200},
        report,
    )
    assert report["metadata"]["isolation"]["embargo"]["source"] == "config_embargo"


def test_purge_source_copied_from_orchestrator_not_recomputed():
    """purge 之來源**抄** orchestrator 寫的 `purge_gap_source`（唯一判定點），service 不重判。"""
    report = _report(purge=12, horizon=5)
    report["metadata"]["ic_train_test_split"]["purge_gap_source"] = "event_label_window"
    _inject_isolation_source(
        {"lookahead_depth_rows": 144, "label_window_rows": 12, "embargo_before_event": 0}, report
    )
    p = report["metadata"]["isolation"]["purge"]
    assert p["source"] == "event_label_window" and p["event_label_window_rows"] == 12
    assert "答案窗" in p["note"] and "12" in p["note"]

    report2 = _report(purge=5, horizon=5)
    report2["metadata"]["ic_train_test_split"]["purge_gap_source"] = "mainline_horizon"
    _inject_isolation_source(
        {"lookahead_depth_rows": 144, "label_window_rows": 3, "embargo_before_event": 0}, report2
    )
    assert report2["metadata"]["isolation"]["purge"]["source"] == "mainline_horizon"


def test_equal_window_and_horizon_note_says_both_counted():
    """B2 review R1（三家同提）：W==H 時來源仍是 mainline，但 note 必須講明「兩者都算進去了」。"""
    report = _report(purge=5, horizon=5)
    report["metadata"]["ic_train_test_split"]["purge_gap_source"] = "mainline_horizon"
    _inject_isolation_source(
        {"lookahead_depth_rows": 144, "label_window_rows": 5, "embargo_before_event": 0}, report
    )
    note = report["metadata"]["isolation"]["purge"]["note"]
    assert "相等" in note and "都已算進去" in note
    assert "沒有比它長" not in note


def test_scan_cell_embargo_source_uses_pristine_config_value():
    """B2 review R1 `CODEX-R1-P2-01`：掃描格之 `embargo_before_event` 必須是**抬高前**的值。

    外層在進掃描格前已把 config embargo 抬到深度；若每格讀那個已抬高的值當「原始設定」，
    來源會全部誤標 `config_embargo`（實跑：incoming=144 ⇒ 誤標）。
    """
    import inspect

    from api.services.ic_analysis_service import ICAnalysisService

    src = inspect.getsource(ICAnalysisService._run_scan_cell)
    assert "original_embargo if original_embargo is not None" in src, "掃描格未使用抬高前之原始值"
    grid = inspect.getsource(ICAnalysisService._run_scan_grid)
    assert "original_embargo" in grid, "掃描格入口未接收原始值"
    # 顯式參數，不得改回塞 config_override（那正是本票剛擋掉的通道）
    assert "_ORIGINAL_EMBARGO_KEY" not in src


def test_legacy_report_without_new_key_falls_back():
    """舊報告（無 `purge_gap_source`）⇒ 沿用舊字串，前端仍有對應文案。"""
    report = _report()
    _inject_isolation_source({"purge_rows": 12, "embargo_before_event": 0}, report)
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
