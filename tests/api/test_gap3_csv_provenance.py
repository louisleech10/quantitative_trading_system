"""GAP-3 UX Task 1.6 驗證（-k gap3_csv_provenance）：對映 provenance 落檔。

判準字面之唯一來源＝SPEC L1588–1601 該 Task「驗證」欄
（`pytest tests/api -q -k gap3_csv_provenance` ≥2 條；斷言 receipt 之
`column_mapping.label ==` 送出值）。本檔另覆蓋兩條邊界：
①未帶 `source_file_digest`（＝批內無法解析出單一值）⇒ fail-closed，落檔數 0；
②provenance 只**補**一個 namespace，不覆寫 receipt 之任何既有欄。

🔴 欄名與型別之唯一來源＝`event_import_contract.json` 之 `receipt_schema.mapping_provenance`；
本檔以**同一支** `flatten_receipt_schema` 讀出欄名，不在測試裡另抄一份清單。
"""

from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import case_import_service as svc_mod
from momentum.Analysis.event_samples.import_contract import (
    canonical_event_id,
    flatten_receipt_schema,
    load_event_import_contract,
)
from tests.momentum.event_samples.test_import_contract import canonical_event as make_event

client = TestClient(app)

USER_HEADER = ["我的編號", "幣種", "K線週期", "毫秒時間", "是不是正例", "來源檔雜湊"]
MAPPING = {
    "event_id": "我的編號", "symbol": "幣種", "timeframe": "K線週期",
    "t0": "毫秒時間", "label": "是不是正例", "source_file_digest": "來源檔雜湊",
}
DEFAULT_FIELDS = ("decision_offset_bars", "entry_price_semantic", "direction", "scenario",
                  "label_definition", "control_kind", "data_snapshot_digest")
CONFIRMED_AT = "2026-08-25T09:30:00Z"


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    svc = svc_mod.EventImportService(storage_dir=tmp_path / "events")
    monkeypatch.setattr(svc_mod, "_event_import_service", svc)
    return svc


def _defaults(**over) -> dict:
    base = make_event(0)
    out = {k: base[k] for k in DEFAULT_FIELDS}
    out.update(over)
    return out


def _csv(digests) -> bytes:
    """兩列 CSV；`digests` 逐列給 `source_file_digest`（用以造出「批內不一致」）。"""
    base = make_event(0)
    lines = [",".join(USER_HEADER)]
    for i, dg in enumerate(digests):
        t0 = base["t0"] + i * 43200000
        lines.append(",".join([canonical_event_id("ETHUSDT", "12h", t0), "ETHUSDT", "12h",
                               str(t0), str(i % 2), dg]))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _post(content: bytes, *, confirmed_at=CONFIRMED_AT, mapping=None):
    data = {
        "column_mapping": json.dumps(MAPPING if mapping is None else mapping, ensure_ascii=False),
        "batch_defaults": json.dumps(_defaults()),
    }
    if confirmed_at is not None:
        data["mapping_confirmed_at"] = confirmed_at
    return client.post(
        "/api/v1/case/import-events/csv",
        files={"file": ("mine.csv", io.BytesIO(content), "text/csv")},
        data=data,
    )


def _receipt(svc, import_id: str) -> dict:
    return json.loads((svc.storage_dir / f"{import_id}.json").read_text(encoding="utf-8"))


def _stored_count(svc) -> int:
    return len(list(svc.storage_dir.glob("*.json"))) if svc.storage_dir.is_dir() else 0


# ── ① 四項落檔（SPEC 之 `column_mapping.label ==` 送出值） ────────────────────
def test_gap3_csv_provenance_records_four_items(_isolated_storage):
    r = _post(_csv(["a" * 64, "a" * 64]))
    assert r.status_code == 200, r.text
    prov = _receipt(_isolated_storage, r.json()["import_id"])["mapping_provenance"]

    assert prov["column_mapping"]["label"] == MAPPING["label"]        # SPEC 驗證欄之字面
    assert prov["column_mapping"] == MAPPING                          # 送出之對映逐鍵原樣
    assert prov["source_file_name"] == "mine.csv"
    assert prov["source_file_digest"] == "a" * 64
    assert prov["confirmed_at"] == CONFIRMED_AT
    assert prov["confirmed_at_source"] == svc_mod.EventImportService.CONFIRMED_AT_CLIENT


# ── ② 邊界①：批內解析不出單一 digest ⇒ fail-closed 且落檔數 == 0 ─────────────
def test_gap3_csv_provenance_missing_digest_fail_closed(_isolated_storage):
    """🔴 兩列各自宣告**不同**的 `source_file_digest`：逐列契約檢核皆合法
    （`source_file_digest` 無 batch_single_value 約束）⇒ 一定會走到 provenance 這一層，
    本層才是被驗的東西。若改用「整批缺欄」造反例，拒收會由**上游**逐列檢核發出，
    本 Task 的保護被拿掉也照樣綠（假綠）。"""
    r = _post(_csv(["a" * 64, "b" * 64]))
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    fields = {f["field"] for f in detail["failures"]}
    assert "mapping_provenance.source_file_digest" in fields
    assert _stored_count(_isolated_storage) == 0


def test_gap3_csv_provenance_uniform_digest_accepts(_isolated_storage):
    """正例對照（防「恆紅型假保證」）：同一份 digest ⇒ 收，且落檔數 == 1。"""
    r = _post(_csv(["c" * 64, "c" * 64]))
    assert r.status_code == 200, r.text
    assert _stored_count(_isolated_storage) == 1


# ── ③ 邊界②：不覆寫 receipt 之任何既有欄 ────────────────────────────────────
def test_gap3_csv_provenance_does_not_overwrite_existing_receipt_fields(_isolated_storage):
    r = _post(_csv(["d" * 64, "d" * 64]))
    assert r.status_code == 200, r.text
    receipt = _receipt(_isolated_storage, r.json()["import_id"])
    for key in ("import_id", "source_name", "upload_sha256", "imported_at",
                "contract_version", "lookahead_declaration", "records"):
        assert key in receipt, f"provenance 覆寫或擠掉了既有欄 {key}"
    assert len(receipt["records"]) == 2
    assert receipt["upload_sha256"] == r.json()["upload_sha256"]


# ── ④ 伺服器時間不冒充使用者確認時間 ────────────────────────────────────────
def test_gap3_csv_provenance_server_fallback_is_disclosed(_isolated_storage):
    r = _post(_csv(["e" * 64, "e" * 64]), confirmed_at=None)
    assert r.status_code == 200, r.text
    receipt = _receipt(_isolated_storage, r.json()["import_id"])
    prov = receipt["mapping_provenance"]
    assert prov["confirmed_at_source"] == svc_mod.EventImportService.CONFIRMED_AT_SERVER
    assert prov["confirmed_at"] == receipt["imported_at"]


# ── ⑤ JSON 直傳路徑無對映可追 ⇒ 不寫本 namespace ────────────────────────────
def test_gap3_csv_provenance_absent_on_json_path(_isolated_storage):
    recs = [make_event(0, label=1), make_event(1, label=0)]
    r = client.post("/api/v1/case/import-events/json", json={"records": recs})
    assert r.status_code == 200, r.text
    assert "mapping_provenance" not in _receipt(_isolated_storage, r.json()["import_id"])


# ── ⑥ 契約登記：落檔鍵集 == 契約宣告之欄名（同一 traversal，不另抄清單） ─────
def test_gap3_csv_provenance_keys_match_contract_registration(_isolated_storage):
    r = _post(_csv(["f" * 64, "f" * 64]))
    assert r.status_code == 200, r.text
    prov = _receipt(_isolated_storage, r.json()["import_id"])["mapping_provenance"]
    declared = [n.split(".", 1)[1] for n in flatten_receipt_schema(load_event_import_contract()["receipt_schema"])
                if n.startswith("mapping_provenance.")]
    assert declared, "契約未登記 mapping_provenance namespace（D-6：新欄位必須先進契約）"
    assert sorted(prov.keys()) == sorted(declared)
