"""GAP-3 UX B5（-k gap3_export_filter）：篩選條件之端到端接線與兩條具名殘留之解除。

覆蓋三件事：
1. **`R-B3-2`**：`label_definition.filters` 之 wire shape 於 Task 2.2 定案後，
   引用欄改為**精確抽取**——帶條件而抽不出欄名時不再多要一次宣告。
   🔴 但只對**符合契約形狀**者；外部產生之任意形狀仍走 fail-closed（那是 B3 R1 抓到的 fail-open）。
2. **`D-002 A-004`**：下界之**值來源**——`POST /case/lookahead-depth` 由
   `depth_by_timeframe()` 導出逐 tf 下界（前端不自算）。
3. **`R-B3-1`**：Task 1.9 ⑤ 之「系統內篩選路徑」端到端對證——B3 時該 production caller
   尚不存在，只能鎖住函式物件同一性；Task 2.1 落地後可從**條件物件**一路走到**下界**。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from momentum.Analysis.event_samples.lookahead_declaration import (
    batch_filters_are_canonical,
    canonical_filter_columns,
    filters_referenced_columns,
    resolve_declaration,
)
from momentum.core.constants import TIMEFRAME_SECONDS
from tests.momentum.event_samples.test_import_contract import canonical_event as make_event

client = TestClient(app)

#: Task 2.2 定案之形狀（與 `frontend/src/lib/exportFilter.ts::buildExportFilterSpec()` 同形）
CANONICAL_FILTERS = {
    "version": 1,
    "combinator": "AND",
    "conditions": [
        {"column": "future72_max_drawdown", "op": ">=", "value": -0.1},
        {"column": "price_change", "op": "between", "range": [1.0, 5.0]},
    ],
}


def _records(filters, timeframe="12h", n=2):
    out = []
    for i in range(n):
        rec = make_event(i, label=i % 2)
        rec["timeframe"] = timeframe
        rec["label_definition"] = {**dict(rec["label_definition"]), "filters": filters}
        out.append(rec)
    return out


# ── R-B3-2 ①：符合契約形狀 ⇒ 精確抽取 ───────────────────────────────────────
def test_gap3_export_filter_canonical_shape_extracts_exact_columns():
    assert canonical_filter_columns(CANONICAL_FILTERS) == {"future72_max_drawdown", "price_change"}
    # 🔴 精確抽取**不與可見欄取交集**：條件引用了什麼就是什麼
    assert filters_referenced_columns(CANONICAL_FILTERS, []) == {"future72_max_drawdown", "price_change"}


def test_gap3_export_filter_hidden_column_in_extra_key_is_not_silently_ignored():
    """🔴 R1 `CODEX-R1-P1-04` 之核心反例：多餘鍵裡藏著另一個未來欄。

    寬鬆版會回 `{'future_2bar_return'}` 並宣稱「形狀已認得」——`future_999bar_return`
    完全看不見，抽取集合與實際引用集合因此分離。精確版必須回 `None`（不認得），
    讓呼叫端走 fail-closed 的舊路徑。
    """
    hidden = {
        "version": 1, "combinator": "AND",
        "conditions": [{"column": "future_2bar_return", "op": ">=", "value": 1,
                        "expr": "future_999bar_return"}],
    }
    assert canonical_filter_columns(hidden) is None
    assert batch_filters_are_canonical([{"label_definition": {"filters": hidden}}]) is False


def test_gap3_export_filter_canonical_shape_accepts_both_ops():
    """正例對照（防「恆 None 型假保證」）：兩種 op 之合法形狀都要認得。"""
    ge = {"version": 1, "combinator": "AND",
          "conditions": [{"column": "a", "op": ">=", "value": 1.5}]}
    le = {"version": 1, "combinator": "AND",
          "conditions": [{"column": "b", "op": "<=", "value": -2}]}
    between = {"version": 1, "combinator": "AND",
               "conditions": [{"column": "c", "op": "between", "range": [1, 2]}]}
    assert canonical_filter_columns(ge) == {"a"}
    assert canonical_filter_columns(le) == {"b"}
    assert canonical_filter_columns(between) == {"c"}
    assert canonical_filter_columns({"version": 1, "combinator": "AND", "conditions": []}) == set()


# ── R-B3-2 ②：不符形狀 ⇒ 回 None，呼叫端須走 fail-closed 舊路徑 ─────────────
@pytest.mark.parametrize(
    "bad",
    [
        {"version": 2, "combinator": "AND", "conditions": []},          # 版本不認得
        {"version": 1, "combinator": "AND", "conditions": {"no": "t"}},  # conditions 不是 list
        {"version": 1, "combinator": "AND", "conditions": [{"field_id": 42}]},   # 條目沒有 column
        {"version": 1, "combinator": "AND",
         "conditions": [{"column": "", "op": ">=", "value": 1}]},        # column 是空字串
        {"expr": "row['my_signal'] >= 1"},                               # 外部產生之任意形狀
        "not-an-object",
        # 🔴 以下六種是 R1 `CODEX-R1-P1-04` 之反例族：寬鬆版把它們全當成「形狀已認得」
        {"version": 1, "combinator": "OR",
         "conditions": [{"column": "future_2bar_return", "op": ">=", "value": 1}]},   # OR 未支援
        {"version": 1, "combinator": "AND",
         "conditions": [{"column": "a", "op": "bogus", "value": 1}]},                 # op 不在枚舉
        {"version": 1, "combinator": "AND",
         "conditions": [{"column": "a", "op": ">=", "value": 1, "expr": "future_999bar_return"}]},  # 多餘鍵藏欄名
        {"version": 1, "combinator": "AND", "conditions": [{"column": "a", "op": ">="}]},   # 缺 value
        {"version": 1, "combinator": "AND",
         "conditions": [{"column": "a", "op": "between", "range": [2, 1]}]},          # 區間反了
        {"version": 1, "combinator": "AND",
         "conditions": [{"column": "a", "op": ">=", "value": float("nan")}]},         # 非有限數
        {"version": 1, "combinator": "AND", "conditions": [], "extra": 1},            # 頂層多餘鍵
    ],
    ids=["bad_version", "conditions_not_list", "no_column", "empty_column", "opaque_expr", "not_mapping",
         "combinator_or", "bogus_op", "extra_key_hiding_column", "missing_value", "reversed_range",
         "nan_value", "top_level_extra_key"],
)
def test_gap3_export_filter_non_canonical_shape_is_not_trusted(bad):
    """🔴 回 `None`（不認得）與回 `set()`（認得且真的沒引用）**意義不同**。

    混為一談就會把外部產生的任意形狀當成「沒有引用欄」而放行——B3 R1 抓到的 fail-open。
    """
    assert canonical_filter_columns(bad) is None


# ── R-B3-2 ③：定案前後之行為差 —— 帶條件時是否多要一次宣告 ─────────────────
def test_gap3_export_filter_canonical_empty_conditions_no_longer_forces_declaration():
    """形狀認得 ＋ 沒有引用欄 ⇒ **不再**強制宣告（`R-B3-2` 之止血解除）。"""
    empty = {"version": 1, "combinator": "AND", "conditions": []}
    records = _records(empty)
    assert batch_filters_are_canonical(records) is True
    out = resolve_declaration(records, data_columns=["close"], declaration=None,
                              timeframe_seconds=TIMEFRAME_SECONDS, on_missing="block")
    assert out.requires_declaration is False


def test_gap3_export_filter_unextractable_shape_still_forces_declaration():
    """形狀不認得 ＋ 抽不出欄名 ⇒ **仍然**強制宣告（fail-closed 未被本批放寬）。"""
    opaque = {"expr": "row['my_custom_signal'] >= 1"}
    records = _records(opaque)
    assert batch_filters_are_canonical(records) is False
    out = resolve_declaration(records, data_columns=["close"], declaration=None,
                              timeframe_seconds=TIMEFRAME_SECONDS, on_missing="block")
    assert out.requires_declaration is True


def test_gap3_export_filter_one_bad_row_makes_whole_batch_fail_closed():
    """🔴 只要**一列**之 filters 不符形狀，整批回到 fail-closed（不得因多數符合就放行）。"""
    records = _records({"version": 1, "combinator": "AND", "conditions": []}, n=2)
    records[1]["label_definition"] = {**records[1]["label_definition"], "filters": {"expr": "x"}}
    assert batch_filters_are_canonical(records) is False


# ── D-002 A-004 ＋ R-B3-1：條件物件 → 下界之端到端 ─────────────────────────
def test_gap3_export_filter_lookahead_depth_endpoint_derives_bound_per_timeframe():
    """🔴 小時命名欄之逐 tf 解析：同一個 `future72_*` 在 1h 是 72 根、在 12h 是 6 根。

    （時間長度相同、根數逐 tf 不同——這正是 SPEC Task 2.1b 驗收②要表達的相反面。）
    """
    referenced = sorted(canonical_filter_columns(CANONICAL_FILTERS))
    r = client.post("/api/v1/case/lookahead-depth", json={
        "referenced_columns": referenced,
        "declared_window_bars": {"1h": 2, "12h": 2},
        "timeframes": ["1h", "12h"],
    })
    assert r.status_code == 200, r.text
    depth = r.json()["depth_by_timeframe"]
    assert depth["1h"] == 72 * 3600 // TIMEFRAME_SECONDS["1h"]
    assert depth["12h"] == 72 * 3600 // TIMEFRAME_SECONDS["12h"]
    assert depth["1h"] != depth["12h"], "根數逐 tf 不同才對；相同代表換算被寫死"


def test_gap3_export_filter_lookahead_depth_takes_max_of_declared_and_referenced():
    """深度＝max(宣告值, 引用欄之最遠深度)——兩者缺一不可。"""
    r = client.post("/api/v1/case/lookahead-depth", json={
        "referenced_columns": ["future_2bar_return"],
        "declared_window_bars": {"12h": 9},
        "timeframes": ["12h"],
    })
    assert r.status_code == 200, r.text
    assert r.json()["depth_by_timeframe"]["12h"] == 9      # 宣告 9 > 引用欄 2 ⇒ 取 9

    r2 = client.post("/api/v1/case/lookahead-depth", json={
        "referenced_columns": ["future_7bar_return"],
        "declared_window_bars": {"12h": 2},
        "timeframes": ["12h"],
    })
    assert r2.status_code == 200, r2.text
    assert r2.json()["depth_by_timeframe"]["12h"] == 7      # 引用欄 7 > 宣告 2 ⇒ 取 7


def test_gap3_export_filter_lookahead_depth_fail_closed_on_missing_timeframe_key():
    """缺該 tf 之宣告鍵 ⇒ fail-closed（不得以 1 或其他 tf 之值默認替代）。"""
    r = client.post("/api/v1/case/lookahead-depth", json={
        "referenced_columns": ["future_2bar_return"],
        "declared_window_bars": {"1h": 2},
        "timeframes": ["1h", "12h"],
    })
    assert r.status_code == 422, r.text


def test_gap3_export_filter_unregistered_future_column_is_fail_closed():
    """🔴 **看起來是未來欄但沒登記** ⇒ 顯式拒（新增未來欄之 PR 須先登記，不得以放寬本閘消紅）。"""
    r = client.post("/api/v1/case/lookahead-depth", json={
        "referenced_columns": ["future_999bar_return"],
        "declared_window_bars": {"12h": 2},
        "timeframes": ["12h"],
    })
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["kind"] == "lookahead_depth_unresolvable"


@pytest.mark.parametrize(
    "column", ["price_change", "volume_multiplier", "closing_strength", "my_custom_signal"],
)
def test_gap3_export_filter_present_time_column_contributes_zero_depth(column):
    """🔴 **當下欄**（沒有前視）不進 max，也不該逼使用者宣告深度。

    這是篩選面板最常見的用法。少了這條，`price_change >= 2` 這種條件會每次都 422
    ——把 fail-closed 用在不存在的風險上。與上一條合起來釘住三分之兩側：
    看起來像未來欄的一律擋、根本不是未來欄的一律 0。
    """
    r = client.post("/api/v1/case/lookahead-depth", json={
        "referenced_columns": [column],
        "declared_window_bars": {"12h": 3},
        "timeframes": ["12h"],
    })
    assert r.status_code == 200, r.text
    assert r.json()["depth_by_timeframe"]["12h"] == 3      # 仍等於宣告值，未被推高


def test_gap3_export_filter_end_to_end_condition_object_to_lower_bound():
    """`R-B3-1`：從**條件物件**一路走到**下界**（B3 時這條 production 路徑還不存在）。

    鏈路＝Task 2.2 之 filters 物件 → `canonical_filter_columns()` 精確抽取
    → `POST /case/lookahead-depth` → `depth_by_timeframe()` → 前端下界。
    """
    filters = {"version": 1, "combinator": "AND",
               "conditions": [{"column": "future_7bar_return", "op": ">=", "value": 0.0}]}
    referenced = sorted(canonical_filter_columns(filters))
    assert referenced == ["future_7bar_return"]

    r = client.post("/api/v1/case/lookahead-depth", json={
        "referenced_columns": referenced,
        "declared_window_bars": {"1h": 5},
        "timeframes": ["1h"],
    })
    assert r.status_code == 200, r.text
    # SPEC Task 2.1b 邊界①：條件用到 future_7 ⇒ 下界鎖定 >= 7（宣告的 5 被推高）
    assert r.json()["depth_by_timeframe"]["1h"] == 7


def test_gap3_export_filter_carry_columns_must_not_raise_the_bound():
    """🔴 SPEC Task 2.1b 邊界②：Task 4.1 之**附帶欄**不得納入 max。

    條件只引用 `future_2bar_return`，即使使用者另外多帶了 `future_7bar_return` 之類的欄，
    下界仍須 `== 2`——本測試以「附帶欄不進 referenced_columns」之契約表達該區分。
    """
    filters = {"version": 1, "combinator": "AND",
               "conditions": [{"column": "future_2bar_return", "op": ">=", "value": 0.0}]}
    referenced = sorted(canonical_filter_columns(filters))
    r = client.post("/api/v1/case/lookahead-depth", json={
        "referenced_columns": referenced,          # 附帶欄不在此列
        "declared_window_bars": {"1h": 0},
        "timeframes": ["1h"],
    })
    assert r.status_code == 200, r.text
    assert r.json()["depth_by_timeframe"]["1h"] == 2
