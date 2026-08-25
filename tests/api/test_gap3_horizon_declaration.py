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


def _defaults() -> dict:
    base = make_event(0)
    return {k: base[k] for k in DEFAULT_FIELDS}


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


def _post(content: bytes, declaration=None):
    data = {"column_mapping": json.dumps(MAPPING, ensure_ascii=False), "batch_defaults": json.dumps(_defaults())}
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
    r = _post(_csv(extra_columns=FUTURE_COLUMNS), declaration={"declared_window_bars": {"12h": 12}})
    assert r.status_code == 200, r.text

    assert len(calls) == 1, "CSV 路徑未呼叫唯一深度函式（＝另寫了一份計算）"
    call = calls[0]
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


def test_gap3_horizon_declaration_06b_single_input_applied_to_all_timeframes_is_fail_closed():
    content = _csv(rows_tf=("1h", "12h"))
    before = _stored_count()
    r = _post(content, declaration={"declared_window_bars": {"1h": 4}})     # 少一個 tf＝單格套全部
    assert r.status_code in (400, 422), r.text
    assert r.json()["detail"]["kind"] == "lookahead_declaration_invalid"
    scalar = _post(content, declaration={"declared_window_bars": 4})        # 純量＝單格套全部
    assert scalar.status_code in (400, 422), scalar.text
    assert _stored_count() == before
