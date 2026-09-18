"""SPLITUNIFY `Task 10.4`／`R5-C8`：逐事件處置帳。

驗的是什麼：兩端差集與剔除揭露只有一個來源；`ic_disposition` 是**入口之預測**，
不得讀 stage3（讀了就是拿自己比自己，`Task 10.7` 的對證會恆真）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from momentum.Analysis.event_samples.event_disposition import (
    build_event_disposition_ledger,
    disposition_values,
    excluded_by_symbol,
)

REPO = Path(__file__).resolve().parents[3]
CONTRACT = REPO / "momentum/Analysis/contracts/split_unify.json"
RUN_SYM = "ETHUSDT"
H1 = 3_600_000
BASE = 1_700_000_000_000


def _ev(eid, sym=RUN_SYM):
    return {"event_id": eid, "symbol": sym}


def test_disposition_values_read_from_contract() -> None:
    """🔴 值集自契約讀，**手打即紅**（`R5-C8` 2.）。

    本條同時擋兩種退化：①程式內手打字面；②契約鍵被刪掉而程式回退到內建預設。
    """
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    vals = contract["event_disposition_values"]
    got = disposition_values()
    assert set(got) == set(vals), f"值集之欄不符：{sorted(got)} vs {sorted(vals)}"
    for k in vals:
        assert list(got[k]) == list(vals[k]), f"{k} 之值集與契約不逐值相符"
    # 手打一個不在契約內的值 ⇒ 必須被擋
    with pytest.raises(ValueError, match="封閉值集"):
        build_event_disposition_ledger(
            events=[_ev("e0")], run_symbol=RUN_SYM,
            aligned_event_ids={"e0"}, coverage_ok_event_ids={"e0"},
            feature_row_key_by_id={"e0": BASE}, post_trim_index_ms={BASE},
            label_value_by_id={"e0": 0.1},
        ) if False else _force_invalid()


def _force_invalid():
    """以契約外之字面直呼內部檢查，證明封閉值集真的會擋（不是只寫在註解裡）。"""
    from momentum.Analysis.event_samples.event_disposition import _check

    return _check("totally_made_up", "ic_disposition")


def test_each_event_exactly_one_row() -> None:
    """`R5-C8` 1.：每個通過匯入驗證之 `event_id` 恰一列；重複即 fail-closed。"""
    rows = build_event_disposition_ledger(
        events=[_ev("a"), _ev("b")], run_symbol=RUN_SYM,
        aligned_event_ids={"a", "b"}, coverage_ok_event_ids={"a", "b"},
        feature_row_key_by_id={"a": BASE, "b": BASE + H1},
        post_trim_index_ms={BASE, BASE + H1}, label_value_by_id={"a": 0.1, "b": -0.2},
    )
    assert [r.event_id for r in rows] == ["a", "b"]
    assert all(r.ic_disposition == "ic_consumed" for r in rows)
    with pytest.raises(ValueError, match="恰一列"):
        build_event_disposition_ledger(
            events=[_ev("a"), _ev("a")], run_symbol=RUN_SYM,
            aligned_event_ids={"a"}, coverage_ok_event_ids={"a"},
            feature_row_key_by_id={"a": BASE}, post_trim_index_ms={BASE},
            label_value_by_id={"a": 0.1},
        )


def test_scan_disposition_outside_post_trim_index() -> None:
    """🔴 錨點在 manifest 區間內、在 **post-trim 索引外** ⇒ `outside_post_trim_index`。

    鑑別力（`M-SU-R5-13`）：略過 post-trim 首尾剔除（改以 manifest 區間判定）⇒ 本條轉紅。
    """
    rows = build_event_disposition_ledger(
        events=[_ev("trimmed")], run_symbol=RUN_SYM,
        aligned_event_ids={"trimmed"}, coverage_ok_event_ids={"trimmed"},
        feature_row_key_by_id={"trimmed": BASE},          # 錨點存在
        post_trim_index_ms={BASE + H1, BASE + 2 * H1},    # 但已被裁掉
        label_value_by_id={"trimmed": 0.1},
    )
    assert rows[0].scan_disposition == "outside_post_trim_index"
    assert rows[0].ic_disposition == "feature_row_not_in_feature_index"


def test_boundary_event_ledger_predicts_feature_row_not_in_feature_index() -> None:
    """🔴 邊界事件：`feature_cutoff_ms ∈ post-trim 索引` 但 `last_bar_open_ms ∉` ⇒ 預測為
    `feature_row_not_in_feature_index`。

    這正是換錨之後才會出現的一類——以**收盤**判會說「在索引內」，以**開盤**（實際消費之列）
    判才看得出不在。fixture 前提不成立即 fail（擋空心通過）。
    """
    cutoff, anchor = BASE + H1, BASE          # 開盤在前、收盤在後
    post_trim = {cutoff, cutoff + H1}         # 只含收盤那根，不含錨點那根
    assert cutoff in post_trim and anchor not in post_trim, "fixture 前提不成立，本條空心"
    rows = build_event_disposition_ledger(
        events=[_ev("bnd")], run_symbol=RUN_SYM,
        aligned_event_ids={"bnd"}, coverage_ok_event_ids={"bnd"},
        feature_row_key_by_id={"bnd": anchor},   # `R5-C9` 之鍵＝開盤
        post_trim_index_ms=post_trim, label_value_by_id={"bnd": 0.1},
    )
    assert rows[0].ic_disposition == "feature_row_not_in_feature_index", (
        "以收盤判會誤判為在索引內——本條就是要擋那個"
    )


def test_decision_order_is_align_symbol_coverage_label_row() -> None:
    """`R5-C8` 3.：判定順序不可調。前一段成立才輪到後一段。"""
    # 對齊失敗優先於 symbol 不符
    rows = build_event_disposition_ledger(
        events=[_ev("x", sym="BTCUSDT")], run_symbol=RUN_SYM,
        aligned_event_ids=set(), coverage_ok_event_ids=set(),
        feature_row_key_by_id={}, post_trim_index_ms=set(),
    )
    assert rows[0].ic_disposition == "align_failed", "對齊失敗須優先於 symbol 判定"

    # symbol 不符優先於 coverage
    rows = build_event_disposition_ledger(
        events=[_ev("y", sym="BTCUSDT")], run_symbol=RUN_SYM,
        aligned_event_ids={"y"}, coverage_ok_event_ids=set(),
        feature_row_key_by_id={}, post_trim_index_ms=set(),
    )
    assert rows[0].ic_disposition == "symbol_not_run_symbol"

    # label 值缺席優先於特徵列判定
    rows = build_event_disposition_ledger(
        events=[_ev("z")], run_symbol=RUN_SYM,
        aligned_event_ids={"z"}, coverage_ok_event_ids={"z"},
        feature_row_key_by_id={"z": BASE}, post_trim_index_ms=set(),
        label_value_by_id={"z": None},
    )
    assert rows[0].ic_disposition == "label_value_unavailable"


def test_excluded_by_symbol_is_derived_not_recomputed() -> None:
    """`R5-C8` 4.：`excluded_by_symbol` 由處置帳導出，不另算。"""
    rows = build_event_disposition_ledger(
        events=[_ev("a"), _ev("b", sym="BTCUSDT"), _ev("c", sym="BCHUSDT")],
        run_symbol=RUN_SYM,
        aligned_event_ids={"a", "b", "c"}, coverage_ok_event_ids={"a", "b", "c"},
        feature_row_key_by_id={"a": BASE}, post_trim_index_ms={BASE},
        label_value_by_id={"a": 0.1},
    )
    assert excluded_by_symbol(rows) == ["b", "c"]


def test_ledger_does_not_read_stage3() -> None:
    """🔴 `R5-C8` 6.：`ic_disposition` 為**預測**，簽名內不得出現 stage3 之觀測面。

    以函式簽名為機械判準：出現 `observed`／`stage3` 一類參數即代表讀了觀測，
    那會讓 `Task 10.7` 的預測-觀測對證變成拿自己比自己。
    """
    import inspect

    sig = inspect.signature(build_event_disposition_ledger)
    bad = [p for p in sig.parameters if "observ" in p.lower() or "stage3" in p.lower()]
    assert not bad, f"處置帳簽名混入觀測面參數：{bad}"
