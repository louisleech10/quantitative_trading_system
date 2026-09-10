"""EVTLABEL Task 3.3：staging 之 0/1 向量、值域閘、選樣預檢、三元組回綁。

SPEC：`docs/EVTLABEL_SPEC.md` Task 3.3　TODO：Task 3.3

## 這批測試在防什麼

匯入標籤模式最危險的失敗形態**不會拋例外**：使用者標的 `2` 被 `int()` 變成別的類、
NaN 被 Mann-Whitney 的 `nan_policy="omit"` 默默丟掉、兩個正例的時間戳對調而值不變。
三種都會跑出漂亮的數字，而報告上看不出來。故本檔一律以「值域先擋、快照獨立、逐筆比三項」
的形式釘住，並要求**明示模式不得靜默降級**。

mutation（`--phase 3`）：
`M-P3-2`（值域閘放行非 0/1）⇒ `test_invalid_domain_*` 紅。
`M-P3-3`（三元組只比 label 不比 ms）⇒ `test_binary_rows_swapped_timestamps_raise` 紅。
"""

from __future__ import annotations

import pytest

from api.services.ic_analysis_service import (
    _assert_binary_rows_bound,
    _binary_label_domain,
    prevalidate_imported_binary_selection_classes,
)

# ══════════════════════════════════════════════════════════════════════════
# ① 值域閘：0/1 以外一律不放行
# ══════════════════════════════════════════════════════════════════════════


def test_clean_binary_batch_passes():
    ok, reason = _binary_label_domain([{"label": 1}, {"label": 0}, {"label": 1.0}])
    assert ok is True and reason is None


def test_missing_label_column_is_its_own_reason():
    """legacy 匯入完全沒有 `label` 欄 ⇒ `no_label_column`（與「有但壞掉」是兩件事）。"""
    ok, reason = _binary_label_domain([{"event_id": "e1"}, {"event_id": "e2"}])
    assert ok is False and reason == "no_label_column"


@pytest.mark.parametrize("bad", [2, -1, 0.5, float("nan"), float("inf"), None, "1", "yes", True_ := object()])
def test_invalid_domain_values_are_rejected(bad):
    """🔴 逐一釘住最危險的那幾個值。

    `2`／`-1`：使用者可能用多分類標籤；`0.5`：`int()` 會無聲截成 0；
    `NaN`：Mann-Whitney 會 omit 掉；`None`：整筆消失；字串與物件：型別錯。
    """
    ok, reason = _binary_label_domain([{"label": 1}, {"label": bad}])
    assert ok is False and reason == "label_invalid_domain"


def test_bool_labels_are_accepted_as_zero_one():
    """Python `True/False` 之 float 值恰為 1.0／0.0 ⇒ 合法（CSV 解析常見）。"""
    ok, reason = _binary_label_domain([{"label": True}, {"label": False}])
    assert ok is True and reason is None


def test_single_bad_row_poisons_the_whole_batch():
    """一筆壞就整批不建向量——半套 0/1 會讓分母與 `event_label_values` 不同。"""
    ok, _ = _binary_label_domain([{"label": 0}] * 100 + [{"label": 7}])
    assert ok is False


# ══════════════════════════════════════════════════════════════════════════
# ② 選樣預檢：與切分器共用同一支算術
# ══════════════════════════════════════════════════════════════════════════


def test_selection_preview_counts_only_rows_inside_test_segment():
    """預檢只數落在**驗證段**的事件；訓練段與隔離區的不算。"""
    index = list(range(100))
    # oos_test_size=0.2 ⇒ split_point=80；purge 2 + embargo 3 ⇒ 測試段自 85 起
    labels = {80: 1, 84: 0, 85: 1, 90: 1, 95: 0}
    n_pos, n_neg = prevalidate_imported_binary_selection_classes(
        labels, index, oos_test_size=0.2, purge_gap=2, embargo=3
    )
    assert (n_pos, n_neg) == (2, 1), "只有 85／90（正）與 95（反）在測試段內"


def test_selection_preview_uses_the_same_function_as_the_splitter():
    """🔴 與 orchestrator 共用 `holdout_test_row_index`：兩端各寫一份算術就會漂。

    這裡直接以該函式算出的起點回推，證明預檢沒有自己另算一套。
    """
    from momentum.core.split_preview import holdout_test_row_index

    index = list(range(1000))
    rows = holdout_test_row_index(1000, oos_test_size=0.2, purge_gap=12, embargo=144)
    start = int(rows[0])
    labels = {start - 1: 1, start: 1, start + 1: 0}
    n_pos, n_neg = prevalidate_imported_binary_selection_classes(
        labels, index, oos_test_size=0.2, purge_gap=12, embargo=144
    )
    assert (n_pos, n_neg) == (1, 1), f"測試段起點 {start}：前一列不得算進去"


def test_selection_preview_empty_test_segment_returns_zeros():
    """隔離區吃掉整段 ⇒ (0, 0)，不是例外（由呼叫端據門檻決定要不要擋）。"""
    assert prevalidate_imported_binary_selection_classes(
        {5: 1}, list(range(10)), oos_test_size=0.2, purge_gap=50, embargo=50
    ) == (0, 0)


def test_selection_preview_ignores_labels_not_on_the_feature_index():
    """事件時間戳若不在特徵索引上（期間對齊已剔除）⇒ 不計入，也不 raise。"""
    n_pos, n_neg = prevalidate_imported_binary_selection_classes(
        {999999: 1, 90: 0}, list(range(100)), oos_test_size=0.2, purge_gap=0, embargo=0
    )
    assert (n_pos, n_neg) == (0, 1)


# ══════════════════════════════════════════════════════════════════════════
# ③ 三元組回綁：逐筆比 (event_id, ms, 0/1)
# ══════════════════════════════════════════════════════════════════════════


def _staged(rows: dict) -> dict:
    return {"event_binary_rows_by_id": rows}


def test_binary_rows_matching_pass():
    rows = {"e1": (100, 1), "e2": (200, 0)}
    _assert_binary_rows_bound(_staged(rows), {"consumed_event_binary_rows": {"e1": [100, 1], "e2": [200, 0]}})


def test_binary_rows_swapped_timestamps_raise():
    """🔴 承重條：兩個**同值**事件把時間戳對調 ⇒ 只比 label 察覺不到，比 ms 才會現形。

    165 個事件裡 136 個是正例，這種錯不會讓任何統計爆掉——只會讓結論悄悄指向錯的列。
    """
    rows = {"e1": (100, 1), "e2": (200, 1)}
    with pytest.raises(ValueError, match="0/1 三元組不符"):
        _assert_binary_rows_bound(_staged(rows), {"consumed_event_binary_rows": {"e1": [200, 1], "e2": [100, 1]}})


def test_binary_rows_flipped_label_raises():
    rows = {"e1": (100, 1)}
    with pytest.raises(ValueError, match="0/1 三元組不符"):
        _assert_binary_rows_bound(_staged(rows), {"consumed_event_binary_rows": {"e1": [100, 0]}})


def test_binary_rows_key_set_mismatch_raises():
    """少消費一個事件（或多出一個）⇒ raise，不容忍「大致相同」。"""
    rows = {"e1": (100, 1), "e2": (200, 0)}
    with pytest.raises(ValueError, match="鍵集不一致"):
        _assert_binary_rows_bound(_staged(rows), {"consumed_event_binary_rows": {"e1": [100, 1]}})
    with pytest.raises(ValueError, match="鍵集不一致"):
        _assert_binary_rows_bound(
            _staged(rows),
            {"consumed_event_binary_rows": {"e1": [100, 1], "e2": [200, 0], "e3": [300, 1]}},
        )


def test_binary_rows_missing_snapshot_fails_closed():
    """service 端沒有快照 ⇒ raise（無從回綁時**不得**當作通過）。"""
    with pytest.raises(ValueError, match="沒有 event_binary_rows_by_id"):
        _assert_binary_rows_bound(_staged({}), {"consumed_event_binary_rows": {"e1": [1, 1]}})


def test_binary_rows_missing_report_side_fails_closed():
    """orchestrator 沒回報 ⇒ raise（缺席不得預設通過）。"""
    with pytest.raises(ValueError, match="缺 consumed_event_binary_rows"):
        _assert_binary_rows_bound(_staged({"e1": (1, 1)}), {})


def test_binary_rows_malformed_pair_raises():
    with pytest.raises(ValueError, match="形狀非"):
        _assert_binary_rows_bound(_staged({"e1": (1, 1)}), {"consumed_event_binary_rows": {"e1": "nope"}})


# ══════════════════════════════════════════════════════════════════════════
# ④ 分派：imported_binary 走兩腿，其他 label_source 行為不變
# ══════════════════════════════════════════════════════════════════════════


def test_triple_bound_dispatches_binary_leg_for_imported_binary():
    """`imported_binary_label` ⇒ 報酬腿與 0/1 腿**都**要過。"""
    from api.services.ic_analysis_service import _assert_event_triple_bound

    staged = {
        "event_label_by_id": {"e1": 0.05},
        "event_binary_rows_by_id": {"e1": (100, 1)},
    }
    report = {"metadata": {"event_filter": {
        "label_source": "imported_binary_label",
        "consumed_event_labels": {"e1": 0.05},
        "consumed_event_binary_rows": {"e1": [100, 1]},
    }}}
    _assert_event_triple_bound(staged, report)

    # 0/1 腿壞掉但報酬腿完好 ⇒ 仍須 raise（少了第二腿這裡會全綠）
    bad = {"metadata": {"event_filter": {
        "label_source": "imported_binary_label",
        "consumed_event_labels": {"e1": 0.05},
        "consumed_event_binary_rows": {"e1": [100, 0]},
    }}}
    with pytest.raises(ValueError):
        _assert_event_triple_bound(staged, bad)


def test_triple_bound_unchanged_for_return_rule():
    """`event_label_value` 之行為**逐字不變**（本 Task 只加分支，不動既有腿）。"""
    from api.services.ic_analysis_service import _assert_event_triple_bound

    staged = {"event_label_by_id": {"e1": 0.05}}
    report = {"metadata": {"event_filter": {
        "label_source": "event_label_value",
        "consumed_event_labels": {"e1": 0.05},
    }}}
    _assert_event_triple_bound(staged, report)


def test_triple_bound_still_early_returns_for_mainline_fallback():
    """事件不足退回 mainline ⇒ 沒有事件 label 可比，維持既有 early-return。"""
    from api.services.ic_analysis_service import _assert_event_triple_bound

    report = {"metadata": {"event_filter": {"label_source": "mainline_return_N"}}}
    _assert_event_triple_bound({"event_label_by_id": {}}, report)


# ══════════════════════════════════════════════════════════════════════════
# ⑤ 入口簽名：0/1 與模式只走顯式 kwarg
# ══════════════════════════════════════════════════════════════════════════


def test_orchestrator_analyze_accepts_binary_kwargs_explicitly():
    """🔴 顯式 kwarg，**不得**改回塞 config_override——config 對未知鍵是靜默忽略。"""
    import inspect

    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    for fn in (ICFilterOrchestrator.analyze, ICFilterOrchestrator._run_full_sample_fallback):
        params = inspect.signature(fn).parameters
        for name in ("event_binary_labels", "label_mode_requested", "label_mode_hint", "selection_preview"):
            assert name in params, f"{fn.__name__} 缺 kwarg {name}"


def test_all_fallback_callsites_forward_binary_kwargs():
    """三個 fallback 呼叫點都要透傳；漏一個 ⇒ 該路徑靜默變報酬版。"""
    from pathlib import Path

    src = (Path(__file__).resolve().parents[2] / "momentum/Analysis/ic_filter_orchestrator.py").read_text(
        encoding="utf-8"
    )
    n_callsites = src.count("self._run_full_sample_fallback(")
    assert src.count("event_binary_labels=event_binary_labels,") == n_callsites + 1, (
        f"{n_callsites} 個 fallback 呼叫點＋1 個內層 analyze 透傳，實際 "
        f"{src.count('event_binary_labels=event_binary_labels,')}"
    )


def test_scan_cell_never_sends_binary_labels():
    """🔴 掃描格恆為報酬版：0/1 與 k、h 無關，每格會得到同一份標籤 ⇒ 整張網格是假的變化。"""
    import inspect

    from api.services.ic_analysis_service import ICAnalysisService

    src = inspect.getsource(ICAnalysisService._run_scan_cell)
    assert "event_binary_labels=None" in src
    assert 'label_mode_requested="return_rule"' in src
