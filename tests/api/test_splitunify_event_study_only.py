"""SPLITUNIFY Task 3.3 驗證（-k splitunify_event_study_only）：無 canonical universe ⇒ 明示不切分。

判準字面之唯一來源＝`docs/SPLITUNIFY_TODO.md` Task 3.3「驗證」欄；本檔只把它機械化。

出生理由（SPEC C-0 決議③）：事件掃描端手上只有匯入的事件與 K 線，**完全不碰 FF run**
⇒ 拿不到 IC 主線切分所依據的 post-trim feature universe。沒有 universe 就沒有 canonical 邊界，
此時若按事件數自己切一份並叫它 OOS，就是本票要消滅的**第二套切分**。

🔴 三條斷言的分工（缺任一條都會留下具體漏洞）：
  ①`capability` 兩條 reason 可分辨 → 畫面才講得出「為什麼沒有驗證段」；
  ②summary **不得出現** `n_train`／`n_test`／`n_purged` → 填 0 會被讀成「切了但都空」；
  ③`estimand_scope == "full_sample_not_oos"` → 這張表確實跑全樣本，必須自己講明白。

🔴 ④採**執行期探針**（monkeypatch `pipeline.split_events` 計數）而非原始碼形狀斷言——
   形狀 oracle 在本 epic 已被繞過三次；計數 `== 0` 是執行期事實。
"""

from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import case_import_service as svc_mod
from momentum.Analysis.event_samples import pipeline as pipeline_mod
from momentum.Analysis.event_samples.lookahead_gate import split_blocked_reason
from momentum.Analysis.event_samples.split_projection import (
    canonical_universe_unavailable_reason,
    full_sample_estimand_scope,
)
from tests.momentum.event_samples.test_import_contract import canonical_event as make_event

client = TestClient(app)

BASE_HEADER = ["我的編號", "幣種", "K線週期", "毫秒時間", "是不是正例"]
MAPPING = {"event_id": "我的編號", "symbol": "幣種", "timeframe": "K線週期",
           "t0": "毫秒時間", "label": "是不是正例"}
DEFAULT_FIELDS = ("decision_offset_bars", "entry_price_semantic", "direction", "scenario",
                  "label_definition", "control_kind", "source_file_digest", "data_snapshot_digest")


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    svc = svc_mod.EventImportService(storage_dir=tmp_path / "events")
    monkeypatch.setattr(svc_mod, "_event_import_service", svc)
    return svc


@pytest.fixture
def spy_split(monkeypatch):
    """執行期探針：`pipeline` 命名空間裡的 `split_events` 換成計數器（不改行為）。"""
    calls = []
    real = pipeline_mod.split_events

    def counting(*args, **kwargs):
        calls.append((args, kwargs))
        return real(*args, **kwargs)

    monkeypatch.setattr(pipeline_mod, "split_events", counting)
    return calls


def _csv(rows_tf=("12h", "12h", "12h", "12h")) -> bytes:
    from momentum.Analysis.event_samples.import_contract import canonical_event_id

    base_t0 = make_event(0)["t0"]
    lines = [",".join(BASE_HEADER)]
    for i, tf in enumerate(rows_tf):
        t0 = base_t0 + i * 43200000
        lines.append(",".join([canonical_event_id("ETHUSDT", tf, t0), "ETHUSDT", tf, str(t0), str(i % 2)]))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _import(declaration=None) -> str:
    base = make_event(0)
    data = {"column_mapping": json.dumps(MAPPING, ensure_ascii=False),
            "batch_defaults": json.dumps({k: base[k] for k in DEFAULT_FIELDS})}
    if declaration is not None:
        data["lookahead_declaration"] = json.dumps(declaration)
    r = client.post("/api/v1/case/import-events/csv",
                    files={"file": ("mine.csv", io.BytesIO(_csv()), "text/csv")}, data=data)
    assert r.status_code == 200, r.text
    return r.json()["import_id"]


def _analyze(import_id: str) -> dict:
    a = client.post(f"/api/v1/case/events/{import_id}/analyze", json={"horizons": [1]})
    assert a.status_code == 200, a.text
    return a.json()


# ── ① capability：恆為 unavailable，reason 為「拿不到 universe」 ──────────────
def test_splitunify_event_study_only_capability_reason_is_no_universe(spy_split):
    payload = _analyze(_import(declaration={"declared_window_bars": {"12h": 1}}))
    cap = payload["capability"]
    assert cap["split"] == "unavailable"
    assert cap["reason"] == canonical_universe_unavailable_reason() == "canonical_feature_universe_unavailable"
    # 兩條 reason 必須**不同字面**，否則畫面分不出「深度不可證」與「拿不到 universe」（R2 之 D5）
    assert cap["reason"] != split_blocked_reason()


# ── ② summary：三個切分計數鍵**不得存在**（不是填 0） ────────────────────────
@pytest.mark.parametrize("key", ["n_train", "n_test", "n_purged"])
def test_splitunify_event_study_only_summary_has_no_split_counts(key, spy_split):
    summary = _analyze(_import(declaration={"declared_window_bars": {"12h": 1}}))["summary"]
    assert key not in summary, (
        f"未切分卻出現 {key}——填 0 會被讀成「切了但都空」，正是 C-0 要禁的假 OOS 數字"
    )
    assert summary["execution_mode"] == "event_study_only"
    assert summary["split"] is None


# ── ② 之另一半：L3（深度不可證）走**同一個**新形狀（既有分支之回歸） ─────────
def test_splitunify_event_study_only_lookahead_blocked_shares_the_same_shape(spy_split, monkeypatch):
    """🔴 L3 之落檔批**無法**由 HTTP 匯入路徑造出（未宣告即拒收），故改由**落檔資料**注入。

    注入的是 receipt 這筆**資料**（`split_blocked: True`），不是分派行為——
    `lookahead_split_blocked` → `gate_from_receipt` → analyze 的分支判斷全都照真的跑。
    """
    import_id = _import(declaration={"declared_window_bars": {"12h": 1}})
    monkeypatch.setattr(
        svc_mod.EventImportService, "_stored_declaration",
        lambda self, _iid: {"split_blocked": True, "requires_declaration": True,
                            "lookahead_bars_declared": {"12h": 1},
                            "embargo_ms_by_symbol": {"ETHUSDT": 43200000}},
    )
    payload = _analyze(import_id)
    cap, summary = payload["capability"], payload["summary"]
    assert cap["split"] == "unavailable"
    assert cap["reason"] == split_blocked_reason()
    for key in ("n_train", "n_test", "n_purged"):
        assert key not in summary, f"L3 分支仍留著 {key}（兩條 reason 必須共用同一形狀）"


# ── ③ estimand_scope：這張表跑的是全樣本，必須自己講明白 ────────────────────
def test_splitunify_event_study_only_table_declares_full_sample_estimand(spy_split):
    payload = _analyze(_import(declaration={"declared_window_bars": {"12h": 1}}))
    common = payload["tables"]["event_forward_return_table"]["common"]
    assert common["estimand_scope"] == full_sample_estimand_scope() == "full_sample_not_oos"
    # 既有降級揭露不得因此被弱化（同一個 common 區塊的兩件事）
    assert common["formal_pooled_inference_allowed"] is False
    assert common["reason"] == "no_event_split_plan"


# ── ④ 生產路徑對 `split_events` 之呼叫次數釘 0（執行期事實，非原始碼形狀） ────
def test_splitunify_split_events_production_call_count_is_zero(spy_split):
    """🔴 `split_events` 保留為歷史路徑／G-3a 對照，但**生產呼叫點數＝0**（Task 3.1 ③）。

    本條走**真實 HTTP 路由**（route → service → pipeline），不是單元層的假呼叫；
    同時斷言表確實產得出來——只斷言「沒呼叫切分」的話，一條 raise 在最前面的實作也會綠。
    """
    payload = _analyze(_import(declaration={"declared_window_bars": {"12h": 1}}))
    assert spy_split == [], f"生產路徑呼叫了 split_events {len(spy_split)} 次（應為 0）"
    assert payload["tables"]["event_forward_return_table"]["receipts"]["n_rows"] > 0
    assert payload["embargo"] == {"applied_ms": None, "source": "not_applicable_event_study_only"}
