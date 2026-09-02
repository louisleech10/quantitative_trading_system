"""GAP-3 UX Task 1.11 驗證（-k lookahead_declaration）：未知欄強制宣告（D-7 之 L2）。

判準字面之唯一來源＝`docs/GAP3_EVENT_UX_SPEC.md` Task 1.11「驗證」欄：
①fixture 含 `my_custom_signal` 欄且被條件引用 ⇒ 不得自動放行（`requires_declaration == True`）
②未填宣告即送出 ⇒ fail-closed（落檔數 `== 0`）

🔴 ①刻意以 `provenance="system_generated"` 呼叫判定函式：`external_upload` 之信任邊界會讓
   **任何**欄都回 True，那樣「忽略無法解析之欄」的 mutation 不會轉紅（＝這條測試會失去鑑別力）。
   兩條路徑各測一次：函式面（可證偽）＋端點面（真實接線）。
"""

from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import case_import_service as svc_mod
from momentum.Analysis.event_samples.lookahead_registry import (
    PROVENANCE_EXTERNAL_UPLOAD,
    PROVENANCE_SYSTEM_GENERATED,
    requires_declaration,
)
from tests.momentum.event_samples.test_import_contract import canonical_event as make_event

client = TestClient(app)

#: 自訂欄——registry 解析不出深度（既非已登記 future 欄，也不是可推導之命名）
CUSTOM = "my_custom_signal"
USER_HEADER = ["我的編號", "幣種", "K線週期", "毫秒時間", "是不是正例", CUSTOM]
MAPPING = {"event_id": "我的編號", "symbol": "幣種", "timeframe": "K線週期", "t0": "毫秒時間", "label": "是不是正例"}
DEFAULT_FIELDS = ("decision_offset_bars", "entry_price_semantic", "direction", "scenario",
                  "label_definition", "control_kind", "source_file_digest", "data_snapshot_digest")


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    svc = svc_mod.EventImportService(storage_dir=tmp_path / "events")
    monkeypatch.setattr(svc_mod, "_event_import_service", svc)
    return svc


def _defaults_with_filters(filters: object) -> dict:
    """batch_defaults：`label_definition.filters` 帶入指定條件物件（＝「被條件引用」）。"""
    base = make_event(0)
    out = {k: base[k] for k in DEFAULT_FIELDS}
    ld = dict(out["label_definition"])
    ld["filters"] = filters
    out["label_definition"] = ld
    return out


def _defaults_referencing_custom() -> dict:
    return _defaults_with_filters({"conditions": [{"column": CUSTOM, "op": ">=", "value": 1}]})


def _csv(n=2) -> bytes:
    from momentum.Analysis.event_samples.import_contract import canonical_event_id

    base = make_event(0)
    lines = [",".join(USER_HEADER)]
    for i in range(n):
        t0 = base["t0"] + i * 43200000
        lines.append(",".join([canonical_event_id("ETHUSDT", "12h", t0), "ETHUSDT", "12h", str(t0), str(i % 2), "3.5"]))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _post_csv(declaration=None, defaults=None):
    data = {
        "column_mapping": json.dumps(MAPPING, ensure_ascii=False),
        "batch_defaults": json.dumps(defaults if defaults is not None else _defaults_referencing_custom()),
    }
    if declaration is not None:
        data["lookahead_declaration"] = json.dumps(declaration)
    return client.post("/api/v1/case/import-events/csv",
                       files={"file": ("mine.csv", io.BytesIO(_csv()), "text/csv")}, data=data)


def _stored_count() -> int:
    return client.get("/api/v1/case/events").json()["total"]


# ── ① 解析不出深度之引用欄 ⇒ 強制宣告（不得取其他欄之 max 自動放行） ──────────
def test_lookahead_declaration_01_unresolvable_column_requires_declaration():
    # 函式面：可解析欄不觸發、自訂欄觸發——這條分得出「忽略無法解析之欄」的 mutation
    assert requires_declaration(["future_4bar_return"], "12h", provenance=PROVENANCE_SYSTEM_GENERATED) is False
    assert requires_declaration([CUSTOM], "12h", provenance=PROVENANCE_SYSTEM_GENERATED) is True
    # 🔴 混入可解析欄仍須為 True：不得因「其他欄都能解析」就取它們的 max 當全批深度
    assert requires_declaration(
        ["future_1bar_return", "future_12bar_return", CUSTOM], "12h",
        provenance=PROVENANCE_SYSTEM_GENERATED,
    ) is True
    # 外部上傳之信任邊界：欄名不具證據力 ⇒ 即使命中 registry 亦須宣告
    assert requires_declaration(["future_4bar_return"], "12h", provenance=PROVENANCE_EXTERNAL_UPLOAD) is True


def test_lookahead_declaration_01b_endpoint_reports_requires_declaration():
    """端點面：真實接線亦回報須宣告，且指名是哪個引用欄。"""
    r = client.post("/api/v1/case/import-events/lookahead-declaration",
                    files={"file": ("mine.csv", io.BytesIO(_csv()), "text/csv")},
                    data={"column_mapping": json.dumps(MAPPING, ensure_ascii=False),
                          "batch_defaults": json.dumps(_defaults_referencing_custom())})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["requires_declaration"] is True
    assert body["referenced_columns"] == [CUSTOM]
    assert body["timeframes"] == ["12h"]


# ── ② 未填宣告即送出 ⇒ fail-closed，落檔數 == 0 ───────────────────────────
def test_lookahead_declaration_02_missing_declaration_is_fail_closed():
    assert _stored_count() == 0
    r = _post_csv(declaration=None)
    assert r.status_code in (400, 422), r.text
    assert r.json()["detail"]["kind"] == "lookahead_declaration_required"
    assert _stored_count() == 0                      # 🔴 落檔數 == 0（不半套、不先寫再擋）


def test_lookahead_declaration_02b_declared_batch_is_accepted_and_stored():
    """對照組：填了宣告並勾了聲明就過——證明 ② 的紅不是「這條路徑本來就不通」。"""
    r = _post_csv(declaration={"declared_window_bars": {"12h": 4}, "acknowledged_unverifiable": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lookahead_declaration"]["lookahead_bars_declared"] == {"12h": 4}
    assert body["lookahead_declaration"]["requires_declaration"] is True
    assert body["lookahead_declaration"]["acknowledged_unverifiable"] is True
    assert _stored_count() == 1


# ── R1 群集 A（CODEX-R1-P1-01＋GROK-R1-P1-01）：引用欄抽不出來 ≠ 沒有引用 ─────
#    四種真實編碼會讓「字串 ∩ 可見欄」抽出空集合。抽空時若讀成「沒引用欄」即 fail-open：
#    未知深度欄可在未宣告下直接落檔並進切分。以下逐形態釘死其為 fail-closed。
# 🔴 id 刻意**不含空白**：mutation runner 由 pytest `-rf` 輸出以空白切 node id，
#    label 帶空白會讓紀錄下來的 node id 在空白處被截斷，逐一相等之判準因此失真。
@pytest.mark.parametrize("filters, why", [
    ({"formula": f"row['{CUSTOM}'] >= 1"}, "欄名只在運算式字串內部_整詞不等"),
    ({"conditions": [{"field_id": 42, "op": ">=", "value": 1}]}, "以opaque_id引用_根本沒有欄名"),
    ({"ref": {"path": f"features.{CUSTOM}"}}, "欄名是dotted_path的一段"),
    ({"conditions": [{"column": "future_4bar_return", "op": ">=", "value": 0}]}, "對映後用契約欄名_可見header是使用者欄名"),
])
def test_lookahead_declaration_03_unextractable_filters_are_fail_closed(filters, why):
    assert _stored_count() == 0
    r = _post_csv(declaration=None, defaults=_defaults_with_filters(filters))
    assert r.status_code in (400, 422), f"{why} ⇒ 應 fail-closed，實得 {r.status_code}: {r.text}"
    assert r.json()["detail"]["kind"] == "lookahead_declaration_required", why
    assert _stored_count() == 0, why


def test_lookahead_declaration_03b_no_filters_still_requires_declaration():
    """🔴 R 重開（SPEC Task 1.11 驗證②）：**沒有任何條件、全為系統欄** ⇒ 仍強制宣告。

    R 前本條是對照組「無條件 ⇒ 不強制」；R 後 `label_definition.filters` 無寫入者，
    條件式 `needs` 會恆假而 fail-open（三家 R35 P0）⇒ `needs` 恆 True。
    mutation：把 `needs` 改回條件式 ⇒ 本條紅（200 而非拒收）。
    對照（防「全部都拒收」之壞掉實作）：同一批**帶宣告**即 200——見下一條。
    """
    base = make_event(0)
    plain = {k: base[k] for k in DEFAULT_FIELDS}
    r = _post_csv(declaration=None, defaults=plain)
    assert r.status_code in (400, 422), r.text
    assert r.json()["detail"]["kind"] == "lookahead_declaration_required"
    assert _stored_count() == 0


def test_lookahead_declaration_03c_no_filters_with_declaration_is_accepted():
    """對照組：同一「無條件、全系統欄」之批，**帶宣告**即收（證 03b 擋的是缺宣告，不是恆紅）。"""
    base = make_event(0)
    plain = {k: base[k] for k in DEFAULT_FIELDS}
    r = _post_csv(declaration={"declared_window_bars": {"12h": 2}, "acknowledged_unverifiable": True}, defaults=plain)
    assert r.status_code == 200, r.text
    assert r.json()["lookahead_declaration"]["requires_declaration"] is True
    assert r.json()["lookahead_declaration"]["lookahead_bars_declared"] == {"12h": 2}
    assert _stored_count() == 1


# ── R1（CODEX-R1-P1-02）：深度驗不了時，宣告值本身就是不可驗聲明 ⇒ 一律須勾選 ──
def test_lookahead_declaration_04_unverifiable_declaration_requires_acknowledgement():
    # 檔內無可解析未來欄 ⇒ 預設 0 ⇒ 任何正值都不算「調低」；若只在調低時要求勾選，
    # 這條最該勾的路徑反而不必勾（SPEC Task 1.11 ③ 明列勾選為要件）。
    r = _post_csv(declaration={"declared_window_bars": {"12h": 4}, "acknowledged_unverifiable": False})
    assert r.status_code in (400, 422), r.text
    assert r.json()["detail"]["kind"] == "lookahead_declaration_unacknowledged_unverifiable"
    assert _stored_count() == 0
