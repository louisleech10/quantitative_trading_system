"""GAP-3 `G3-D2` **Task D1.7** — IC 分析頁之 `event_label_spec` 初始值（依宣告深度）。

選擇器：`pytest tests/api -q -k ic_event_label_defaults`

規則（`D-001` D1.7，deterministic）：
- `trigger_tfs = sorted({r["timeframe"]})`；**單 tf** ⇒ `depth = lookahead_bars_declared[tf]`
- `depth == 0` ⇒ 「當根」`(trigger_open, open_to_close)`、`horizon_bars = 1`
- `depth >= 1` ⇒ 「持有」`(trigger_open, open_to_horizon_close)`、`horizon_bars = depth`
- **混 tf** ⇒ 不自動選深度：當根、`horizon_bars = 1`、揭露「混合 timeframe」

🔴 **仍禁**讀匯出檔之 `label_definition.window.horizon_bars`（§D-3′-a：該欄語意是深度宣告，
分析層讀成答案窗即靜默給錯預設）。本檔以「窗欄殘值與宣告深度**不同**」之 fixture 釘住這件事。
"""

from __future__ import annotations

import pytest

from api.models.ic_models import EventLabelScanModel, EventLabelSpecModel
from api.routes.ic_analysis import _resolve_event_batch
from api.services import case_import_service as svc_mod
from tests.momentum.event_samples.test_import_contract import canonical_event as make_event


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    svc = svc_mod.EventImportService(storage_dir=tmp_path / "events")
    monkeypatch.setattr(svc_mod, "_event_import_service", svc)
    return svc


class _Req:
    """`_resolve_event_batch` 只讀這三個欄位。

    🔴 `G3-D2` D4.3：`event_label_spec` 已 typed（`EventLabelSpecModel`），route 走
    `.model_dump(exclude_none=True)` ⇒ 本 double 亦須交出 typed 物件，不能再遞 raw dict
    （遞 dict 會讓測試走一條**生產不存在**的路徑，那正是假綠的來源）。
    """

    def __init__(self, import_id: str, spec=None, scan=None):
        self.event_import_id = import_id
        self.event_label_spec = None if spec is None else EventLabelSpecModel(**spec)
        self.event_label_scan = None if scan is None else EventLabelScanModel(**scan)


def _store(svc, records, declared):
    """把一批 records 落檔並回 import_id（走服務層**真實**落檔路徑，不偽造 payload）。

    🔴 深度宣告以 `lookahead_declaration` 參數寫入**批次層 receipt**——不是逐列欄。
    route 之解析順序是「批次 receipt（權威）→ 逐列欄 → fail-closed」，
    本 helper 走的正是權威那條。
    """
    res = svc.import_records(
        records, source_name="unit", upload_bytes=None, validate_only=False,
        # 宣告 receipt 之形狀＝`{declared_window_bars: {tf: 非負整數}, acknowledged_unverifiable: bool}`
        # （逐 tf 各一值；單一輸入框套用全部 tf 不被接受）
        lookahead_declaration={"declared_window_bars": dict(declared),
                               "acknowledged_unverifiable": True},
    )
    return res.import_id


def _batch(svc, *, tfs, declared, window_h=7, spec=None):
    """建立單／多 tf 之批次。`window_h` 刻意與宣告深度不同（防「讀了窗欄」）。"""
    recs = []
    for i, tf in enumerate(tfs):
        r = make_event(
            i, label=i % 2, timeframe=tf,
            lookahead_bars_declared=declared,
            label_definition={
                "rule_id": "rule-x", "canonical_digest": "c" * 64,
                # 🔴 殘值刻意設成 window_h（≠ 宣告深度）——若實作誤讀本欄，h 會等於它
                "window": {"horizon_bars": window_h}, "label_return_mode": "close_to_close",
            },
        )
        recs.append(r)
    import_id = _store(svc, recs, declared)
    return _resolve_event_batch(_Req(import_id, spec))


# ── 單 tf、深度 0 ⇒ 當根 ────────────────────────────────────────────────────

def test_ic_event_label_defaults_depth_zero_is_trigger_open_open_to_close(_isolated_storage):
    out = _batch(_isolated_storage, tfs=["12h", "12h"], declared={"12h": 0}, window_h=7)
    spec = out["event_label_spec"]
    assert spec["entry_price_semantic"] == "trigger_open"
    assert spec["label_return_mode"] == "open_to_close"
    assert spec["horizon_bars"] == 1, "當根之 h 為 inert 哨兵 1（恆四鍵，不省略）"
    assert set(spec) == {"horizon_bars", "entry_price_semantic",
                         "label_return_mode", "decision_offset_bars"}, "須恰四鍵"
    assert "當根" in out["event_label_spec_seed_note"]


# ── 單 tf、深度 ≥1 ⇒ 持有，且 h == 深度（不是窗欄殘值） ─────────────────────

@pytest.mark.parametrize("depth", [1, 3, 6])
def test_ic_event_label_defaults_positive_depth_is_hold_with_h_equal_depth(_isolated_storage, depth):
    out = _batch(_isolated_storage, tfs=["12h", "12h"], declared={"12h": depth}, window_h=7)
    spec = out["event_label_spec"]
    assert spec["entry_price_semantic"] == "trigger_open"
    assert spec["label_return_mode"] == "open_to_horizon_close"
    assert spec["horizon_bars"] == depth
    # 🔴 承重斷言：窗欄殘值為 7；若實作誤讀 `window.horizon_bars`，上一行在 depth != 7 時會紅
    assert spec["horizon_bars"] != 7 or depth == 7
    assert "持有" in out["event_label_spec_seed_note"]


def test_ic_event_label_defaults_never_reads_window_horizon_bars(_isolated_storage):
    """🔴 §D-3′-a：分析層**禁讀**匯出檔之 `label_definition.window.horizon_bars`。

    宣告深度 2、窗欄殘值 9 ⇒ h 須為 2。這條是該禁令的可證偽形式。
    """
    out = _batch(_isolated_storage, tfs=["12h", "12h"], declared={"12h": 2}, window_h=9)
    assert out["event_label_spec"]["horizon_bars"] == 2


# ── 混 tf ⇒ 不自動選深度 ───────────────────────────────────────────────────

def test_ic_event_label_defaults_mixed_timeframe_does_not_autoselect(_isolated_storage):
    """混 tf 批（1h 深度 0 ＋ 12h 深度 3）⇒ 當根、h=1、揭露含「混合 timeframe」。

    🔴 不自動選是刻意的：各 tf 之「一根」長度不同，取任一個都是猜。
    """
    out = _batch(_isolated_storage, tfs=["1h", "12h"], declared={"1h": 0, "12h": 3}, window_h=7)
    spec = out["event_label_spec"]
    assert spec["entry_price_semantic"] == "trigger_open"
    assert spec["label_return_mode"] == "open_to_close"
    assert spec["horizon_bars"] == 1
    assert "混合 timeframe" in out["event_label_spec_seed_note"]
    # 🔴 over 向：不得悄悄採用 12h 之深度 3
    assert spec["horizon_bars"] != 3


# ── 請求明給之值一律優先（setdefault 語意不變） ─────────────────────────────

def test_ic_event_label_defaults_request_values_win_over_preset(_isolated_storage):
    """使用者已在請求裡指定 ⇒ 預設**不覆蓋**（本段只補沒給的鍵）。"""
    given = {"horizon_bars": 5, "entry_price_semantic": "trigger_close",
             "label_return_mode": "close_to_close", "decision_offset_bars": 0}
    out = _batch(_isolated_storage, tfs=["12h", "12h"], declared={"12h": 3}, spec=given)
    assert out["event_label_spec"] == given


def test_ic_event_label_defaults_partial_request_fills_only_missing(_isolated_storage):
    """只給 `horizon_bars` ⇒ 該值保留，其餘由預設補（證明不是「有給就整組不套」）。"""
    out = _batch(_isolated_storage, tfs=["12h", "12h"], declared={"12h": 3},
                 spec={"horizon_bars": 4})
    spec = out["event_label_spec"]
    assert spec["horizon_bars"] == 4                       # 使用者給的
    assert spec["label_return_mode"] == "open_to_horizon_close"   # 預設補的
    assert spec["entry_price_semantic"] == "trigger_open"


# ── 預設之三元組必須落在支援矩陣內（否則預設值本身就跑不動） ────────────────

@pytest.mark.parametrize("depth", [0, 2])
def test_ic_event_label_defaults_preset_is_inside_supported_matrix(_isolated_storage, depth):
    """🔴 預設值本身**必須**在 `SUPPORTED_MATRIX` 內。

    這正是 Task 7.0 修過的舊病：預設 `trigger_open` 落在當時矩陣外，
    等於「開箱即用的預設值是分析層不支援的組合」。
    """
    from momentum.Analysis.event_samples.label_value_from_case import (
        SUPPORTED_PAIRS, normalize_event_label_spec, spec_is_supported,
    )

    out = _batch(_isolated_storage, tfs=["12h", "12h"], declared={"12h": depth})
    spec = out["event_label_spec"]
    pair = (spec["entry_price_semantic"], spec["label_return_mode"])
    assert pair in SUPPORTED_PAIRS, f"預設對 {pair} 不在支援矩陣內"
    # 🔴 D4.2 起 k 已不入矩陣 ⇒ 連 k 一起判的唯一入口是 `spec_is_supported`。
    assert spec_is_supported(normalize_event_label_spec(spec)) is True


# ══════════════════════════════════════════════════════════════════════════
# B-D1 R2 閉合輪 — codex P1-02／P1-03 之負向測試
# ══════════════════════════════════════════════════════════════════════════

def test_d43_mixed_decision_offset_bars_is_disclosed_not_rejected(_isolated_storage):
    """🔴 **`G3-D2` D4.3 改寫**：批內 k 混值**不再 422**，改為**照實揭露**。

    原斷言（`CODEX-R2-P1-02`）之前提是「分析 k 取自 `records[0]` 並套用全批」
    ⇒ 混值必然讓部分事件對齊到錯的決策根，故 fail-closed。
    D4.3（裁定②）把分析 k 改為**使用者於分析頁指定、全批一致套用**
    ⇒ records 之 k 只是**事實**，混值不再能造成錯誤對齊，擋它只會擋掉合法批。
    原訊息末句「請拆批，或等 k 之分析參數化上線」即預告本次解除。

    **改寫後仍是強斷言**：分析 k 必須是常數 0（不得偷偷取任一列之值），
    且記錄值集合必須**逐值列出** `[0, 2]`（不得只留一個、不得聚合成單值）。
    """
    recs = [
        make_event(0, label=1, decision_offset_bars=0, lookahead_bars_declared={"12h": 0}),
        make_event(1, label=0, decision_offset_bars=2, lookahead_bars_declared={"12h": 0}),
    ]
    import_id = _store(_isolated_storage, recs, {"12h": 0})
    out = _resolve_event_batch(_Req(import_id))
    assert out["event_label_spec"]["decision_offset_bars"] == 0, "分析 k 之初始值＝契約 min 常數"
    assert out["decision_offset_bars_record_values"] == [0, 2], "記錄值須逐值揭露，不得聚合"
    assert out["decision_offset_bars_analysis"] == 0


def test_d43_uniform_decision_offset_bars_does_not_seed_analysis_k(_isolated_storage):
    """🔴 **`G3-D2` D4.3 改寫**：單值 k（含非 0）**不再種子化**分析 k。

    原斷言是 `spec["decision_offset_bars"] == k`（k 由 records 種子化）。
    D4.3 之後「這批當初宣告過 k=2」與「這次分析要用 k=2」是兩件事
    ⇒ 分析 k 恆為契約 min，記錄值以獨立欄呈現。
    """
    for k in (0, 2):
        recs = [
            make_event(i, label=i % 2, decision_offset_bars=k,
                       lookahead_bars_declared={"12h": 0})
            for i in range(2)
        ]
        import_id = _store(_isolated_storage, recs, {"12h": 0})
        out = _resolve_event_batch(_Req(import_id))
        assert out["event_label_spec"]["decision_offset_bars"] == 0
        assert out["decision_offset_bars_record_values"] == [k]
    # over 向：**使用者明給**之 k 仍優先（否則本 Task 等於把 k 鎖死成 0）
    out = _resolve_event_batch(_Req(import_id, spec={"decision_offset_bars": 3}))
    assert out["event_label_spec"]["decision_offset_bars"] == 3


def test_r2_closure_frontend_omits_spec_so_backend_default_is_reachable(_isolated_storage):
    """`CODEX-R2-P1-03`：前端**未設定**時整個鍵省略 ⇒ 後端依深度導出之預設**可達**。

    🔴 修正前：hook 明送 `{horizon_bars: 1}`，而後端用 `setdefault` ⇒ 壓不過已存在的鍵
    ⇒ 宣告深度 3 的批，「持有」實際跑成 h=1。兩端都對、就是沒接上。
    本條以 route 層釘住「spec 為 None 時導出 h=depth」，前端半邊由 vitest
    `…_omits_event_label_spec_when_unset` 釘住。
    """
    recs = [make_event(i, label=i % 2, lookahead_bars_declared={"12h": 3}) for i in range(2)]
    import_id = _store(_isolated_storage, recs, {"12h": 3})
    out = _resolve_event_batch(_Req(import_id, spec=None))
    assert out["event_label_spec"]["horizon_bars"] == 3
    assert out["event_label_spec"]["label_return_mode"] == "open_to_horizon_close"


def test_r2_closure_frontend_constant_seed_would_defeat_depth_default(_isolated_storage):
    """🔴 **把缺陷本身釘成測試**：若有人再讓前端送 `{horizon_bars: 1}`，深度預設就失效。

    本條**不是**驗現行行為對，而是把「為什麼前端不能送常數」寫成可執行的證據：
    同一批、同一深度，spec 給 `{horizon_bars: 1}` 時 h 就是 1（不是 3）。
    ⇒ 日後看到這條紅，代表有人把常數種子加回去了。
    """
    recs = [make_event(i, label=i % 2, lookahead_bars_declared={"12h": 3}) for i in range(2)]
    import_id = _store(_isolated_storage, recs, {"12h": 3})
    out = _resolve_event_batch(_Req(import_id, spec={"horizon_bars": 1}))
    assert out["event_label_spec"]["horizon_bars"] == 1, (
        "setdefault 壓不過已存在的鍵——這就是 CODEX-R2-P1-03 的機制；"
        "前端必須省略該鍵，不能送常數"
    )

# ══════════════════════════════════════════════════════════════════════════
# B-D1 R3 閉合輪 — `CODEX-R3-P1-01`：混 k 之「部分缺鍵」路徑
#
# 選擇器：`pytest tests/api/test_gap3_ic_event_label_defaults.py -q -k r3_closure`
#
# 🔴 **可達性**：`decision_offset_bars` 是契約 `required_fields`，匯入路徑會以
#    `missing_required_field` 擋下缺鍵列 ⇒ 本缺陷**不可能經由匯入產生**。
#    codex 之原探針是 stub 掉 `get_event_import_service` 直接打 route。
#    唯一真實可達路徑＝**繞過匯入驗證的歷史／直寫落檔**（殘留 `B1-LEGACY-1`）。
#    ⇒ 下列測試以「正常匯入後改寫落檔 JSON」重現該形狀，而不是 stub 服務——
#      stub 只證明函式邏輯，改寫落檔才證明**真的有一條路能走到這裡**。
# ══════════════════════════════════════════════════════════════════════════

def _rewrite_stored_records(svc, import_id, mutate):
    """把已落檔批次的 records 就地改寫（模擬繞過匯入驗證的歷史檔）。"""
    import json as _json

    p = svc.storage_dir / f"{import_id}.json"
    payload = _json.loads(p.read_text(encoding="utf-8"))
    mutate(payload["records"])
    p.write_text(_json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
                 encoding="utf-8")


def _legacy_batch(svc, mutate, k=2):
    recs = [
        make_event(i, label=i % 2, decision_offset_bars=k,
                   lookahead_bars_declared={"12h": 0})
        for i in range(2)
    ]
    import_id = _store(svc, recs, {"12h": 0})
    _rewrite_stored_records(svc, import_id, mutate)
    return import_id


def test_d43_partial_missing_decision_offset_bars_is_disclosed(_isolated_storage):
    """🔴 **D4.3 改寫**：部分列缺 k ⇒ 不再 422；缺者**不進值集合**（空 ≠ 0）。

    原斷言（`CODEX-R3-P1-01`）之危害是「缺鍵列被靜默略過，而 `setdefault` 取 `records[0]`
    得 `None`」——D4.3 之後 `setdefault` 根本不讀 records ⇒ 該路徑不存在。
    改寫後守的是**揭露的誠實性**：缺鍵不得被補成 0（那是替使用者宣告他沒宣告過的東西）。
    """
    import_id = _legacy_batch(_isolated_storage,
                              lambda rs: rs[0].pop("decision_offset_bars", None))
    out = _resolve_event_batch(_Req(import_id))
    assert out["decision_offset_bars_record_values"] == [2], "缺鍵列不得被補成 0"
    assert out["event_label_spec"]["decision_offset_bars"] == 0


def test_d43_null_decision_offset_bars_is_disclosed(_isolated_storage):
    """同一形狀之另一半：鍵在但值為 `null`（JSON 直寫最常見的樣子）⇒ 同樣不計入值集合。"""

    def _null_first(rs):
        rs[0]["decision_offset_bars"] = None

    import_id = _legacy_batch(_isolated_storage, _null_first)
    out = _resolve_event_batch(_Req(import_id))
    assert out["decision_offset_bars_record_values"] == [2]


def test_r3_closure_bool_decision_offset_bars_counts_as_missing(_isolated_storage):
    """🔴 `bool` 是 `int` 的子型別：`True` 不得被當成 `k=1`，也不得被當成「缺」。

    🔴 **本條抓到本輪修法的第一版**：當時把「型別錯」歸進「缺」，於是整批都是 `True`
    時 `k_values` 為空 ⇒ 走「全批皆缺」那條 over 向而**放行**，`spec` 拿到 `True`。
    ⇒ 型別錯另立 `invalid_decision_offset_bars`，任何情況都不進分析。
    """
    from fastapi import HTTPException

    def _bool_all(rs):
        for r in rs:
            r["decision_offset_bars"] = True

    import_id = _legacy_batch(_isolated_storage, _bool_all)
    with pytest.raises(HTTPException) as ei:
        _resolve_event_batch(_Req(import_id))
    assert ei.value.detail["kind"] == "invalid_decision_offset_bars"


def test_r3_closure_string_decision_offset_bars_is_rejected(_isolated_storage):
    """同上之另一型別：字串 `"2"` 不得被當成 `k=2`（CSV 直寫最常見的損壞形狀）。"""
    from fastapi import HTTPException

    def _str_all(rs):
        for r in rs:
            r["decision_offset_bars"] = "2"

    import_id = _legacy_batch(_isolated_storage, _str_all)
    with pytest.raises(HTTPException) as ei:
        _resolve_event_batch(_Req(import_id))
    assert ei.value.detail["kind"] == "invalid_decision_offset_bars"


def test_r4_closure_all_missing_decision_offset_bars_is_rejected(_isolated_storage):
    """`CODEX-R4-P1-02`：整批都沒有 `decision_offset_bars` ⇒ **422，不是放行**。

    🔴 **本條是 R3 那條 over 向斷言的更正，不是放寬**。R3 版寫成
    `assert out[...]["decision_offset_bars"] in (0, None)`——**`None` 也算過**，
    於是「route 放行、`normalize_event_label_spec` 在深處拋
    `LabelProducerError ... 須為 int`」這個缺陷被斷言吞掉。codex 實跑
    `ALL_MISSING_NORMALIZER_PROBE_RC=1` 打穿。

    判準更正：「全批皆缺仍放行」**不是值得保留的既有行為**，它只是把錯誤推到更深處。
    ⇒ route 當場 422，並在訊息指出這是繞過匯入驗證的落檔。
    🔴 **寫鬆的 over 向斷言比沒有 over 向更危險**：它看起來有守，其實沒有。

    🔴 **`G3-D2` D4.3 改寫**：本條之危害（放行後在 `normalize_event_label_spec` 深處
    炸 `須為 int`）之成因是 `setdefault(..., seed.get(...))` 會留下 `None`；
    D4.3 之後該處填的是**契約 min 之常數 int** ⇒ 那個深處錯誤在結構上不可能發生。
    改寫後守的是新的不變式：全批缺 k 仍可分析，且揭露為**空清單**（不是 `[0]`）。
    """
    def _drop_all(rs):
        for r in rs:
            r.pop("decision_offset_bars", None)

    import_id = _legacy_batch(_isolated_storage, _drop_all)
    out = _resolve_event_batch(_Req(import_id))
    got = out["event_label_spec"]["decision_offset_bars"]
    assert got == 0 and isinstance(got, int) and not isinstance(got, bool)
    assert out["decision_offset_bars_record_values"] == [], "全批缺 ⇒ 空清單，不得填 [0]"


def test_d43_analysis_k_is_constant_regardless_of_records(_isolated_storage):
    """🔴 **over 向**：records 之 k 為 0 或 2，分析 k **恆為 0**（常數，非種子）。"""
    for k in (0, 2):
        recs = [
            make_event(i, label=i % 2, decision_offset_bars=k,
                       lookahead_bars_declared={"12h": 0})
            for i in range(2)
        ]
        import_id = _store(_isolated_storage, recs, {"12h": 0})
        out = _resolve_event_batch(_Req(import_id))
        got = out["event_label_spec"]["decision_offset_bars"]
        assert got == 0 and isinstance(got, int) and not isinstance(got, bool), \
            f"records k={k} 不得種子化分析 k，實得 {got!r}"


def test_d43_uniform_k_survives_rewrite_path(_isolated_storage):
    """🔴 **對照**：改寫落檔但保持單值 k ⇒ 揭露為 `[2]`、分析 k 仍為 0。

    證明擋／不擋的判準與「經過改寫」這件事無關
    （否則 `_legacy_batch` 這個 helper 就成了測試的作弊面）。
    """
    import_id = _legacy_batch(_isolated_storage, lambda rs: None, k=2)
    out = _resolve_event_batch(_Req(import_id))
    assert out["decision_offset_bars_record_values"] == [2]
    assert out["event_label_spec"]["decision_offset_bars"] == 0


# ══════════════════════════════════════════════════════════════════════════
# B-D1 R5 閉合輪 — `CODEX-R5-P1-01`：值域（負值）＋ composer 之「缺＋型別錯」組合
#
# 選擇器：`pytest tests/api/test_gap3_ic_event_label_defaults.py -q -k r5_closure`
# ══════════════════════════════════════════════════════════════════════════

def test_r5_closure_negative_decision_offset_bars_is_rejected(_isolated_storage):
    """`CODEX-R5-P1-01`：整批負整數 k ⇒ route 當場 422，不得留到 normalizer。

    🔴 修正前：`-1` 是合法 int ⇒ 通過型別過濾、`resolved -1`，
    到 `normalize_event_label_spec` 才拋 `須 >= 0`。codex 實跑 `negative_all RESOLVED -1`。
    這是同一病灶第四刀（型別 → 缺 → 值域），故修法改為**從契約導出值域**。
    """
    from fastapi import HTTPException

    def _neg_all(rs):
        for r in rs:
            r["decision_offset_bars"] = -1

    import_id = _legacy_batch(_isolated_storage, _neg_all)
    with pytest.raises(HTTPException) as ei:
        _resolve_event_batch(_Req(import_id))
    assert ei.value.status_code == 422
    assert ei.value.detail["kind"] == "invalid_decision_offset_bars"


def test_r5_closure_mixed_negative_and_valid_is_rejected(_isolated_storage):
    """同上之混合形狀：一列 `-1`、一列合法 ⇒ 亦須 422（走 invalid，非 mixed）。"""
    from fastapi import HTTPException

    def _neg_first(rs):
        rs[0]["decision_offset_bars"] = -1

    import_id = _legacy_batch(_isolated_storage, _neg_first)
    with pytest.raises(HTTPException) as ei:
        _resolve_event_batch(_Req(import_id))
    assert ei.value.detail["kind"] == "invalid_decision_offset_bars", \
        "值域外與型別錯同類，應優先於 mixed 回報"


def test_r5_closure_missing_plus_invalid_reports_invalid(_isolated_storage):
    """composer R5 之建議：**「缺」與「型別錯」同時出現**時之訊息未被釘住。

    主委在 R5 brief 之 assumed 寫「型別錯優先於缺是對的，但沒有測試釘住這個順序」。
    三家判此為 P2、不阻 B-D3；本輪一併補，不另等一輪。
    """
    from fastapi import HTTPException

    def _missing_and_bad(rs):
        rs[0].pop("decision_offset_bars", None)
        rs[1]["decision_offset_bars"] = "bad"

    import_id = _legacy_batch(_isolated_storage, _missing_and_bad)
    with pytest.raises(HTTPException) as ei:
        _resolve_event_batch(_Req(import_id))
    assert ei.value.detail["kind"] == "invalid_decision_offset_bars", \
        "型別錯（落檔已損壞）比缺（歷史批的合法形狀）嚴重，應優先回報"


def test_r5_closure_domain_comes_from_contract_not_hardcoded(_isolated_storage, monkeypatch):
    """🔴 **本條釘住的是修法的形狀，不是行為**：值域須**從契約導出**。

    R3／R4／R5 三輪都在 route 手刻一條新規則，而契約一直寫著 `{"type": "int", "min": 0}`。

    🔴 **本條的第一版是假的，被 mutation `i2_domain_hardcoded_again` 當場戳破**：
    當時寫成「取契約的 min（＝0），斷言訊息含 `>=0`」——而手刻的 `{"min": 0}`
    產生**一模一樣的字面**，所以把值域改回手刻，這條照樣綠。
    **一條宣稱「證明 X 來自 Y」的測試，若 X 在兩種來源下取值相同，它就什麼也沒證明。**

    ⇒ 正解：把契約的 `min` **改成一個與手刻值不同的數**（2），再看行為跟不跟著變。
    跟著變 ⇒ 真的在讀契約；不變 ⇒ 有人把它寫死了。
    """
    from fastapi import HTTPException
    from momentum.Analysis.event_samples import import_contract as ic_mod

    real = ic_mod.load_event_import_contract()
    assert real["required_fields"]["decision_offset_bars"]["min"] == 0, \
        "前提：契約現行 min 為 0（本條靠『把它改成 2』來證明有在讀）"

    # 🔴 **順序要緊**：匯入層讀的是同一份契約，若先改再匯入，k=1 會在匯入當場被拒
    #    （第一次寫這條時就是這樣紅的）。⇒ 先以真實契約落檔，再改契約，只讓 route 讀到新值。
    recs = [
        make_event(i, label=i % 2, decision_offset_bars=1,
                   lookahead_bars_declared={"12h": 0})
        for i in range(2)
    ]
    import_id = _store(_isolated_storage, recs, {"12h": 0})

    def _fake_contract():
        import copy

        c = copy.deepcopy(real)
        c["required_fields"]["decision_offset_bars"]["min"] = 2
        return c

    monkeypatch.setattr(ic_mod, "load_event_import_contract", _fake_contract)
    with pytest.raises(HTTPException) as ei:
        _resolve_event_batch(_Req(import_id))
    assert ei.value.detail["kind"] == "invalid_decision_offset_bars", \
        "route 未跟著契約的 min 走 ⇒ 值域被寫死了"
    assert ">=2" in ei.value.detail["message"], \
        "訊息之值域字面亦須由契約導出，不得手寫"


def test_r5_closure_unknown_field_domain_is_fail_closed():
    """🔴 出口本身之 fail-closed：問一個契約沒有的欄 ⇒ `KeyError`，不得回「無界」。

    回一個無界的 domain 會讓呼叫端**以為驗過了**——那正是本輪要根治的病。
    """
    from momentum.factories import create_event_sample_pipeline

    with pytest.raises(KeyError):
        create_event_sample_pipeline().int_field_domain("no_such_field_in_contract")
