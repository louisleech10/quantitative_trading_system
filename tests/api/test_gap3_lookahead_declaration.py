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


def _defaults_referencing_custom() -> dict:
    """batch_defaults：`label_definition.filters` 引用 `my_custom_signal`（＝「被條件引用」）。"""
    base = make_event(0)
    out = {k: base[k] for k in DEFAULT_FIELDS}
    ld = dict(out["label_definition"])
    ld["filters"] = {"conditions": [{"column": CUSTOM, "op": ">=", "value": 1}]}
    out["label_definition"] = ld
    return out


def _csv(n=2) -> bytes:
    from momentum.Analysis.event_samples.import_contract import canonical_event_id

    base = make_event(0)
    lines = [",".join(USER_HEADER)]
    for i in range(n):
        t0 = base["t0"] + i * 43200000
        lines.append(",".join([canonical_event_id("ETHUSDT", "12h", t0), "ETHUSDT", "12h", str(t0), str(i % 2), "3.5"]))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _post_csv(declaration=None):
    data = {
        "column_mapping": json.dumps(MAPPING, ensure_ascii=False),
        "batch_defaults": json.dumps(_defaults_referencing_custom()),
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
    """對照組：填了宣告就過——證明 ② 的紅不是「這條路徑本來就不通」。"""
    r = _post_csv(declaration={"declared_window_bars": {"12h": 4}, "acknowledged_unverifiable": False})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lookahead_declaration"]["lookahead_bars_declared"] == {"12h": 4}
    assert body["lookahead_declaration"]["requires_declaration"] is True
    assert _stored_count() == 1
