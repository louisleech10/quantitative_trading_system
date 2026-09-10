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

from api.services.ic_analysis_service import _assert_binary_rows_bound, _binary_label_domain
from momentum.core.split_preview import count_binary_classes_in_rows

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


def test_bool_labels_are_rejected_to_match_the_import_validator():
    """🔴 B3 review R1（三家同提）：`bool` 必須**拒收**，與匯入端 `_is_int` 對齊。

    `True` 之 float 值恰為 1.0，我原本因此放行。但 `import_contract._is_int` 寫的是
    `isinstance(v, Integral) and not isinstance(v, bool)`——兩份不同的「什麼算 int」會讓
    維護者以為上游可以送 bool。合法落檔路徑不會產生 bool，故這不是現行漏洞；
    採嚴的那一份是為了讓兩層政策只有一個答案。
    """
    assert _binary_label_domain([{"label": True}, {"label": False}]) == (False, "label_invalid_domain")
    assert _binary_label_domain([{"label": 1}, {"label": 0}]) == (True, None)


def test_domain_gate_bool_policy_matches_import_contract():
    """碼證：兩層對 bool 的判定一致——任一邊改了政策，本條就紅。"""
    from momentum.Analysis.event_samples.import_contract import _is_int

    for value in (True, False):
        assert _is_int(value) is False
        assert _binary_label_domain([{"label": value}])[0] is False
    for value in (0, 1):
        assert _is_int(value) is True
        assert _binary_label_domain([{"label": value}])[0] is True


def test_single_bad_row_poisons_the_whole_batch():
    """一筆壞就整批不建向量——半套 0/1 會讓分母與 `event_label_values` 不同。"""
    ok, _ = _binary_label_domain([{"label": 0}] * 100 + [{"label": 7}])
    assert ok is False


# ══════════════════════════════════════════════════════════════════════════
# ② 選樣計數：唯一實作，由 orchestrator 交出已算好的測試段列
#
# 🔴 B3 review R1：原本 service 端自己重建一份「測試段」（自組 purge/embargo、自取 config、
#    自讀 h5 索引），三家實測證明那份重建必然與 orchestrator 分歧、且索引讀取對真實 h5
#    恆失敗（＝預檢從未跑過）。改為 orchestrator 交出 `test_plan.row_index`，本函式只計數。
# ══════════════════════════════════════════════════════════════════════════


def test_counts_only_rows_handed_in():
    """只數交進來的那些列；訓練段與隔離區的不算——因為它們根本不在 row_index 裡。"""
    index = list(range(100))
    labels = {80: 1, 84: 0, 85: 1, 90: 1, 95: 0}
    out = count_binary_classes_in_rows(labels, index, list(range(85, 100)))
    assert out == {"n_pos": 2, "n_neg": 1}


def test_counting_has_no_split_arithmetic_of_its_own():
    """🔴 承重條：本函式**不得**自己算切分——沒有第二份算術，就沒有可漂的東西。

    以 AST 確認它的**程式碼**（非 docstring）不呼叫切分算術、也不讀切分參數。
    """
    import ast
    import inspect
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(count_binary_classes_in_rows)))
    called = {
        node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
        for node in ast.walk(tree) if isinstance(node, ast.Call)
    }
    assert "holdout_test_row_index" not in called and "holdout_split_point" not in called
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert not ({"oos_test_size", "purge_gap", "embargo"} & names), (
        f"計數函式不得碰切分參數，實際碰到 {sorted({'oos_test_size', 'purge_gap', 'embargo'} & names)}"
    )


def test_counting_returns_none_when_no_binary_labels():
    """沒有 0/1 ⇒ None（與「有 0/1 但一個都沒落在測試段」＝(0,0) 是兩件事）。"""
    assert count_binary_classes_in_rows(None, list(range(10)), [1, 2]) is None
    assert count_binary_classes_in_rows({}, list(range(10)), [1, 2]) == {"n_pos": 0, "n_neg": 0}


def test_counting_empty_row_index_returns_zeros():
    assert count_binary_classes_in_rows({5: 1}, list(range(10)), []) == {"n_pos": 0, "n_neg": 0}


def test_counting_ignores_labels_not_on_the_feature_index():
    """事件時間戳若已被期間對齊剔除 ⇒ 不計入，也不 raise。"""
    out = count_binary_classes_in_rows({999999: 1, 90: 0}, list(range(100)), list(range(80, 100)))
    assert out == {"n_pos": 0, "n_neg": 1}


def test_service_no_longer_reconstructs_the_test_segment():
    """🔴 防復發：service 不得再出現自建測試段的那兩個函式。"""
    import api.services.ic_analysis_service as svc

    assert not hasattr(svc, "prevalidate_imported_binary_selection_classes")
    assert not hasattr(svc, "_feature_index_for_preview")


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
        for name in ("event_binary_labels", "label_mode_requested", "label_mode_hint"):
            assert name in params, f"{fn.__name__} 缺 kwarg {name}"
        # B3 review R1：`selection_preview` 已**移除**——選樣計數改由 orchestrator 於
        # 切分計畫做完當下自算（`test_plan.row_index` 就是答案），service 不再交一份重建值。
        assert "selection_preview" not in params, f"{fn.__name__} 不該再收 selection_preview"


def test_all_fallback_callsites_forward_binary_kwargs():
    """三個 fallback 呼叫點都要透傳；漏一個 ⇒ 該路徑靜默變報酬版。"""
    from pathlib import Path

    src = (Path(__file__).resolve().parents[2] / "momentum/Analysis/ic_filter_orchestrator.py").read_text(
        encoding="utf-8"
    )
    # 🔴 用 AST 逐個呼叫點檢查，不數字串總數：Task 3.4 起 stage3 也收同名 kwarg，
    #    「總數 == 呼叫點數 + 1」這種算法會隨無關改動而假紅／假綠。
    import ast

    tree = ast.parse(src)
    checked = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "attr", "")
        if name not in ("_run_full_sample_fallback", "analyze"):
            continue
        kwargs = {kw.arg for kw in node.keywords if kw.arg}
        if "event_label_owners" not in kwargs:      # 只看事件語意透傳的那些呼叫
            continue
        checked += 1
        for required in ("event_binary_labels", "label_mode_requested", "label_mode_hint"):
            assert required in kwargs, f"{name} 之某呼叫點漏傳 {required}（該路徑會靜默變報酬版）"
    assert checked >= 4, f"應至少涵蓋 3 個 fallback 呼叫點＋1 個內層 analyze，實得 {checked}"


def test_scan_cell_never_sends_binary_labels():
    """🔴 掃描格恆為報酬版：0/1 與 k、h 無關，每格會得到同一份標籤 ⇒ 整張網格是假的變化。"""
    import inspect

    from api.services.ic_analysis_service import ICAnalysisService

    src = inspect.getsource(ICAnalysisService._run_scan_cell)
    assert "event_binary_labels=None" in src
    assert 'label_mode_requested="return_rule"' in src


# ══════════════════════════════════════════════════════════════════════════
# ⑥ B3 review R1 修補：值域閘只看**被消費**的事件；掃描格揭露 effective mode
# ══════════════════════════════════════════════════════════════════════════


def test_domain_gate_scans_only_consumed_events_not_whole_batch():
    """🔴 `COMPOSER-R1-P1-02`／`GROK-R1-P1-04`（兩家獨立命中，且我在 brief 自列為可疑）。

    混 symbol 批：本次只分析 ETH，而 BTC 某筆 label=2。舊版掃全批 ⇒ 整批被判 invalid、
    本次 run 拿不到 0/1。這是 B1 review 抓過的「分母用全批」同型錯。

    本條以**函式介面**釘住修法：值域閘收到的必須是**已篩選**的清單，
    餵全批與餵被消費子集會得到不同結論——這正是為什麼呼叫端必須先篩。
    """
    eth_ok = [{"event_id": "e1", "label": 1}, {"event_id": "e2", "label": 0}]
    btc_bad = [{"event_id": "b1", "label": 2}]
    assert _binary_label_domain(eth_ok) == (True, None)
    assert _binary_label_domain(eth_ok + btc_bad) == (False, "label_invalid_domain")


def test_staging_filters_by_run_symbol_before_domain_gate():
    """🔴 防復發（碼證）：`_binary_label_domain` 的引數必須是 `consumed_event_ids` 篩過的清單。

    直接把 `records` 整包餵進去 ⇒ 本條紅並指名。
    """
    import inspect

    from api.services.ic_analysis_service import ICAnalysisService

    src = inspect.getsource(ICAnalysisService._run_event_label_stages)
    assert "_binary_label_domain(records)" not in src, "值域閘又餵了全批 records"
    assert "consumed_event_ids" in src
    # 篩選條件必須含 run_symbol，否則「被消費」的定義又回到全批
    idx = src.index("consumed_event_ids")
    assert "run_symbol" in src[idx: idx + 400]


def test_scan_cell_summary_discloses_effective_mode():
    """🔴 `CODEX-R1-P1-03`：掃描格恆為報酬版，這件事必須**寫出來**。

    使用者選 `auto` ＋ 掃描時，若不揭露就會以為每一格是用他的 0/1 算的。
    """
    from api.services.ic_analysis_service import ICAnalysisService

    out = ICAnalysisService._scan_cell_summary({
        "analysis_status": "ok_oos",
        "metadata": {"n_samples": 42, "event_filter": {"label_source": "event_label_value"}},
    })
    assert out["label_mode_effective"] == "return_rule"
    assert out["label_source"] == "event_label_value"


def test_scan_cell_summary_still_returns_none_for_non_dict():
    """不得因為新增揭露鍵而讓「沒有報告」也生出一個 dict。"""
    from api.services.ic_analysis_service import ICAnalysisService

    assert ICAnalysisService._scan_cell_summary(None) is None


def test_counting_handles_datetime_index_not_just_int():
    """🔴 出生事故（Task 3.4 的 selection-scope 測試抓到）：0/1 的鍵是 **epoch 毫秒整數**，
    而特徵索引通常是 `DatetimeIndex`（內部 ns）。不換算就永遠對不上 ⇒ 計數恆為 0
    ⇒ 明示模式恆 raise、auto 恆退回報酬版，而且**不拋任何例外**。
    兩種索引型別必須給出同一個答案。
    """
    import pandas as pd

    idx = pd.to_datetime([1_700_000_000_000 + i * 3_600_000 for i in range(10)], unit="ms")
    ms = (idx.asi8 // 10**6).astype("int64")
    labels = {int(ms[8]): 1, int(ms[9]): 0}
    assert count_binary_classes_in_rows(labels, idx, [8, 9]) == {"n_pos": 1, "n_neg": 1}
    assert count_binary_classes_in_rows(labels, list(ms), [8, 9]) == {"n_pos": 1, "n_neg": 1}


# ══════════════════════════════════════════════════════════════════════════
# ⑦ Task 3.8：來源身分不得憑空編造
# ══════════════════════════════════════════════════════════════════════════


def test_label_origin_values_are_not_faked_from_labels():
    """🔴 `label_origin` 在匯入契約裡是**選填**。

    缺席時若回退成 `label` 本身，`label_origin_values` 會變成 `["0","1"]`——
    一份假裝是來源揭露、實際只是把答案抄一遍的資料。缺席就回空 list。
    """
    import inspect

    from api.services.ic_analysis_service import ICAnalysisService

    src = inspect.getsource(ICAnalysisService._run_event_label_stages)
    assert 'rec.get("label_origin", rec.get("label"))' not in src, "又用 label 當 label_origin 的替身"
    assert 'rec.get("label_origin") is not None' in src


def test_label_origin_is_optional_in_the_import_contract():
    """碼證：契約確實把 `label_origin` 列在選填欄——這正是上一條存在的理由。"""
    import json
    from pathlib import Path

    contract = json.loads(
        (Path(__file__).resolve().parents[2] / "momentum/Analysis/contracts/event_import_contract.json")
        .read_text(encoding="utf-8")
    )
    assert "label_origin" in contract["optional_fields"]
    assert "label_origin" not in contract["required_fields"]
