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

from api.routes.ic_analysis import _resolve_event_batch
from api.services import case_import_service as svc_mod
from tests.momentum.event_samples.test_import_contract import canonical_event as make_event


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    svc = svc_mod.EventImportService(storage_dir=tmp_path / "events")
    monkeypatch.setattr(svc_mod, "_event_import_service", svc)
    return svc


class _Req:
    """`_resolve_event_batch` 只讀這兩個欄位。"""

    def __init__(self, import_id: str, spec=None):
        self.event_import_id = import_id
        self.event_label_spec = spec


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
    from momentum.Analysis.event_samples.label_value_from_case import SUPPORTED_MATRIX

    out = _batch(_isolated_storage, tfs=["12h", "12h"], declared={"12h": depth})
    spec = out["event_label_spec"]
    triple = (spec["entry_price_semantic"], spec["label_return_mode"],
              int(spec["decision_offset_bars"]))
    assert triple in SUPPORTED_MATRIX, f"預設三元組 {triple} 不在支援矩陣內"
