"""GAP-3 UX Task 1.9 驗證（-k gap3_horizon_declaration）：答案窗宣告與 purge 下界（D-7 之 L2 使用者介面）。

判準字面之唯一來源＝`docs/GAP3_EVENT_UX_SPEC.md` Task 1.9「驗證」欄：
①CSV 含 future_1..12 ⇒ 預設值 `== 12`
②未勾聲明而調低 ⇒ fail-closed（落檔數 `== 0`）
③宣告 `== 4` 之單一 1h 批 ⇒ 該 symbol 之 `embargo_ms_by_symbol` `== 4 * TIMEFRAME_SECONDS['1h'] * 1000`
④宣告 20（>12）⇒ 接受（不限 1..12）
⑤深度公式一致性：兩條路徑呼叫**同一 exported 函式**（非各自實作）
⑥多 TF 批 ⇒ `declared_window_bars` 與 `lookahead_bars_declared` 鍵集皆恰為 `{'1h','12h'}`；
  以單一輸入框套用全部 tf ⇒ fail-closed

🔴 ⑤採**執行期**兩重 oracle（物件同一性＋呼叫探針），不用原始碼形狀——
   「原始碼裡有沒有出現那個函式名」在本 epic 已被繞過三次（B1 R3／B2 R1／B2 R2）。
"""

from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import case_import_service as svc_mod
from momentum.Analysis.event_samples import lookahead_declaration as decl_mod
from momentum.Analysis.event_samples import lookahead_depth as depth_mod
from momentum.core.constants import TIMEFRAME_SECONDS
from tests.momentum.event_samples.test_import_contract import canonical_event as make_event

client = TestClient(app)

BASE_HEADER = ["我的編號", "幣種", "K線週期", "毫秒時間", "是不是正例"]
MAPPING = {"event_id": "我的編號", "symbol": "幣種", "timeframe": "K線週期", "t0": "毫秒時間", "label": "是不是正例"}
#: 檔內最大可用 horizon＝12（future_1bar_return .. future_12bar_return，皆 bar 命名）
FUTURE_COLUMNS = [f"future_{n}bar_return" for n in range(1, 13)]
DEFAULT_FIELDS = ("decision_offset_bars", "entry_price_semantic", "direction", "scenario",
                  "label_definition", "control_kind", "source_file_digest", "data_snapshot_digest")


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    svc = svc_mod.EventImportService(storage_dir=tmp_path / "events")
    monkeypatch.setattr(svc_mod, "_event_import_service", svc)
    return svc


def _defaults(filters: object = None) -> dict:
    base = make_event(0)
    out = {k: base[k] for k in DEFAULT_FIELDS}
    if filters is not None:
        ld = dict(out["label_definition"])
        ld["filters"] = filters
        out["label_definition"] = ld
    return out


def _csv(rows_tf=("12h", "12h"), extra_columns=()) -> bytes:
    from momentum.Analysis.event_samples.import_contract import canonical_event_id

    header = BASE_HEADER + list(extra_columns)
    base_t0 = make_event(0)["t0"]
    lines = [",".join(header)]
    for i, tf in enumerate(rows_tf):
        t0 = base_t0 + i * 43200000
        cells = [canonical_event_id("ETHUSDT", tf, t0), "ETHUSDT", tf, str(t0), str(i % 2)]
        cells += ["0.01"] * len(extra_columns)
        lines.append(",".join(cells))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _post(content: bytes, declaration=None, defaults=None):
    data = {"column_mapping": json.dumps(MAPPING, ensure_ascii=False),
            "batch_defaults": json.dumps(defaults if defaults is not None else _defaults())}
    if declaration is not None:
        data["lookahead_declaration"] = json.dumps(declaration)
    return client.post("/api/v1/case/import-events/csv",
                       files={"file": ("mine.csv", io.BytesIO(content), "text/csv")}, data=data)


def _preview(content: bytes):
    return client.post("/api/v1/case/import-events/lookahead-declaration",
                       files={"file": ("mine.csv", io.BytesIO(content), "text/csv")},
                       data={"column_mapping": json.dumps(MAPPING, ensure_ascii=False),
                             "batch_defaults": json.dumps(_defaults())})


def _stored_count() -> int:
    return client.get("/api/v1/case/events").json()["total"]


# ── ① 預設取檔內最大可用 horizon ────────────────────────────────────────────
def test_gap3_horizon_declaration_01_default_is_max_available_horizon():
    r = _preview(_csv(extra_columns=FUTURE_COLUMNS))
    assert r.status_code == 200, r.text
    assert r.json()["default_window_bars"] == {"12h": 12}


# ── ② 未勾聲明而調低 ⇒ fail-closed，落檔數 == 0 ────────────────────────────
def test_gap3_horizon_declaration_02_lowering_without_acknowledgement_is_fail_closed():
    content = _csv(extra_columns=FUTURE_COLUMNS)
    r = _post(content, declaration={"declared_window_bars": {"12h": 4}, "acknowledged_unverifiable": False})
    assert r.status_code in (400, 422), r.text
    assert r.json()["detail"]["kind"] == "lookahead_declaration_unacknowledged_lowering"
    assert _stored_count() == 0

    # 對照組：勾了就過（證明 ② 的紅不是這條路徑本來就不通）
    ok = _post(content, declaration={"declared_window_bars": {"12h": 4}, "acknowledged_unverifiable": True})
    assert ok.status_code == 200, ok.text
    assert ok.json()["lookahead_declaration"]["lookahead_bars_declared"] == {"12h": 4}
    assert _stored_count() == 1


# ── ③ 宣告 4 之單一 1h 批 ⇒ embargo == 4 根之毫秒數 ────────────────────────
def test_gap3_horizon_declaration_03_embargo_matches_declared_bars_on_1h():
    r = _post(_csv(rows_tf=("1h", "1h")), declaration={"declared_window_bars": {"1h": 4}})
    assert r.status_code == 200, r.text
    embargo = r.json()["lookahead_declaration"]["embargo_ms_by_symbol"]
    assert embargo == {"ETHUSDT": 4 * TIMEFRAME_SECONDS["1h"] * 1000}


# ── ④ 宣告 20（>12）⇒ 接受（欄位吃任意正整數） ─────────────────────────────
def test_gap3_horizon_declaration_04_declaration_above_file_max_is_accepted():
    r = _post(_csv(extra_columns=FUTURE_COLUMNS), declaration={"declared_window_bars": {"12h": 20}})
    assert r.status_code == 200, r.text
    assert r.json()["lookahead_declaration"]["lookahead_bars_declared"] == {"12h": 20}


# ── ⑤ 深度公式一致性：同一 exported 函式，非各自實作 ───────────────────────
def test_gap3_horizon_declaration_05_depth_formula_is_the_single_exported_function(monkeypatch):
    # (a) 物件同一性：CSV 路徑所綁的名字**就是** Task 2.1b 那一個 function object
    assert decl_mod.depth_by_timeframe is depth_mod.depth_by_timeframe

    # (b) 執行期探針：CSV 路徑真的呼叫它，且結果與系統內篩選路徑直接呼叫同一函式逐鍵相等
    calls = []
    real = depth_mod.depth_by_timeframe

    def spy(referenced_columns, declared_window_bars, timeframes, registry=None):
        out = real(referenced_columns, declared_window_bars, timeframes, registry=registry)
        calls.append({"referenced": sorted(str(c) for c in referenced_columns),
                      "declared": dict(declared_window_bars), "timeframes": sorted(str(t) for t in timeframes),
                      "out": dict(out)})
        return out

    monkeypatch.setattr(decl_mod, "depth_by_timeframe", spy)
    # 🔴 R1（`CODEX-R1-P2-05`）：fixture 必須讓**引用欄非空**，否則
    #    「把 referenced_for_depth 改成 ()」這個變異算出同值、探針仍被呼叫一次 ⇒ 兩條斷言都綠（假綠）。
    referencing = _defaults({"conditions": [{"column": "future_4bar_return", "op": ">=", "value": 0}]})
    r = _post(_csv(extra_columns=FUTURE_COLUMNS),
              declaration={"declared_window_bars": {"12h": 12}, "acknowledged_unverifiable": True},
              defaults=referencing)
    assert r.status_code == 200, r.text

    assert len(calls) == 1, "CSV 路徑未呼叫唯一深度函式（＝另寫了一份計算）"
    call = calls[0]
    # 未調低 ⇒ 條件引用之可解析欄必須**真的餵進**同一式做 max，不得清空
    assert call["referenced"] == ["future_4bar_return"], "CSV 路徑沒把引用欄餵進唯一深度函式"
    assert call["out"] == real(call["referenced"], call["declared"], call["timeframes"])
    assert r.json()["lookahead_declaration"]["lookahead_bars_declared"] == call["out"]


# ── ⑥ 多 TF 批：鍵集恰為兩個 tf；單一輸入框套用全部 tf ⇒ fail-closed ───────
def test_gap3_horizon_declaration_06_multi_timeframe_keys_are_per_tf():
    content = _csv(rows_tf=("1h", "12h"))
    r = _post(content, declaration={"declared_window_bars": {"1h": 4, "12h": 2}})
    assert r.status_code == 200, r.text
    receipt = r.json()["lookahead_declaration"]
    assert set(receipt["declared_window_bars"]) == {"1h", "12h"}
    assert set(receipt["lookahead_bars_declared"]) == {"1h", "12h"}
    assert receipt["embargo_ms_by_symbol"] == {
        "ETHUSDT": max(4 * TIMEFRAME_SECONDS["1h"], 2 * TIMEFRAME_SECONDS["12h"]) * 1000
    }


# ── R1（CODEX-R1-P1-03）：宣告的下界必須**真的接到 split**，不能只是收據上的數字 ──
def test_gap3_horizon_declaration_07_declared_depth_reaches_split_embargo(monkeypatch):
    """`label_return_mode="open_to_close"` 之 label 窗**不隨 horizon 變**。

    若 analyze 把 `embargo_ms=None` 直傳，`split_events` 會退回「label 窗最大值」＝1 根，
    宣告 20 根卻只隔 1 根＝洩漏。本條以執行期探針攔截真正送進 split 的 embargo。
    """
    from momentum.Analysis.event_samples import pipeline as pipeline_mod
    from momentum.core.constants import TIMEFRAME_SECONDS as TFS

    base = make_event(0)
    defaults = {k: base[k] for k in DEFAULT_FIELDS}
    ld = dict(defaults["label_definition"])
    ld["label_return_mode"] = "open_to_close"
    defaults["label_definition"] = ld

    r = _post(_csv(rows_tf=("12h", "12h")),
              declaration={"declared_window_bars": {"12h": 20}}, defaults=defaults)
    assert r.status_code == 200, r.text
    import_id = r.json()["import_id"]
    declared_ms = 20 * TFS["12h"] * 1000
    assert r.json()["lookahead_declaration"]["embargo_ms_by_symbol"] == {"ETHUSDT": declared_ms}

    seen = []
    real_split = pipeline_mod.split_events

    def spy(manifest, split_config, **kw):
        seen.append(split_config.embargo_ms)
        return real_split(manifest, split_config, **kw)

    monkeypatch.setattr(pipeline_mod, "split_events", spy)
    a = client.post(f"/api/v1/case/events/{import_id}/analyze", json={"horizons": [1]})
    assert a.status_code == 200, a.text
    assert seen and seen[0] is not None, "analyze 沒把任何 embargo 下界送進 split"
    assert seen[0] >= declared_ms, f"送進 split 的 embargo {seen[0]} 低於宣告深度 {declared_ms}（purge 不足＝洩漏）"
    assert a.json()["embargo"]["applied_ms"] >= declared_ms


# ── R2（CODEX-R2-P1-01）：不同 scope 的下界不得被折成全批 scalar ────────────
def _import_two_symbol_batch(declaration):
    """兩個標的分屬不同 timeframe ⇒ 逐 symbol 之宣告下界不同。"""
    from momentum.Analysis.event_samples.import_contract import canonical_event_id

    base_t0 = make_event(0)["t0"]
    lines = [",".join(BASE_HEADER)]
    for i, (sym, tf) in enumerate((("ETHUSDT", "1h"), ("BTCUSDT", "12h"))):
        t0 = base_t0 + i * 43200000
        lines.append(",".join([canonical_event_id(sym, tf, t0), sym, tf, str(t0), str(i % 2)]))
    content = ("\n".join(lines) + "\n").encode("utf-8")
    return _post(content, declaration=declaration)


def test_gap3_horizon_declaration_08_divergent_scope_bounds_are_fail_closed(monkeypatch):
    """SPEC §D-3′-a(ii) 明令禁止「以單一 batch scalar 冒充 per-scope 下界」。

    取 max ⇒ 窗較小的標的被過度 purge（§C0：過度 purge 亦是錯誤）；取 min ⇒ 洩漏。
    兩者皆錯 ⇒ 拒絕分析，且**在做任何工作之前**（斷言切分未被呼叫）。
    """
    from momentum.Analysis.event_samples import pipeline as pipeline_mod
    from momentum.core.constants import TIMEFRAME_SECONDS as TFS

    r = _import_two_symbol_batch({"declared_window_bars": {"1h": 4, "12h": 2}})
    assert r.status_code == 200, r.text
    bounds = r.json()["lookahead_declaration"]["embargo_ms_by_symbol"]
    assert bounds == {"ETHUSDT": 4 * TFS["1h"] * 1000, "BTCUSDT": 2 * TFS["12h"] * 1000}
    assert len(set(bounds.values())) == 2, "fixture 失效：兩個標的的下界必須不同，否則本條沒有鑑別力"

    seen = []
    real_split = pipeline_mod.split_events
    monkeypatch.setattr(pipeline_mod, "split_events",
                        lambda *a, **k: (seen.append(1), real_split(*a, **k))[1])
    a = client.post(f"/api/v1/case/events/{r.json()['import_id']}/analyze", json={"horizons": [1]})
    assert a.status_code == 422, a.text
    assert "Task 7.0b" in a.json()["detail"]["message"]
    assert seen == [], "拒絕應發生在做任何切分之前"


def test_gap3_horizon_declaration_08b_equal_scope_bounds_are_accepted():
    """對照組：各標的下界**相同**時 scalar 與 per-scope 等價 ⇒ 必須放行。

    沒有這條，⑧ 會被一個「多標的一律拒絕」的實作滿足——那不是 fail-closed，是弄壞功能。
    """
    from momentum.Analysis.event_samples.import_contract import canonical_event_id

    base_t0 = make_event(0)["t0"]
    lines = [",".join(BASE_HEADER)]
    for i, sym in enumerate(("ETHUSDT", "BTCUSDT")):
        t0 = base_t0 + i * 43200000
        lines.append(",".join([canonical_event_id(sym, "12h", t0), sym, "12h", str(t0), str(i % 2)]))
    r = _post(("\n".join(lines) + "\n").encode("utf-8"), declaration={"declared_window_bars": {"12h": 2}})
    assert r.status_code == 200, r.text
    bounds = r.json()["lookahead_declaration"]["embargo_ms_by_symbol"]
    assert len(set(bounds.values())) == 1
    svc = svc_mod.get_event_import_service()
    svc._assert_scope_embargo_expressible(r.json()["lookahead_declaration"])   # 不得 raise


def test_gap3_horizon_declaration_06b_single_input_applied_to_all_timeframes_is_fail_closed():
    content = _csv(rows_tf=("1h", "12h"))
    before = _stored_count()
    r = _post(content, declaration={"declared_window_bars": {"1h": 4}})     # 少一個 tf＝單格套全部
    assert r.status_code in (400, 422), r.text
    assert r.json()["detail"]["kind"] == "lookahead_declaration_invalid"
    scalar = _post(content, declaration={"declared_window_bars": 4})        # 純量＝單格套全部
    assert scalar.status_code in (400, 422), scalar.text
    assert _stored_count() == before
