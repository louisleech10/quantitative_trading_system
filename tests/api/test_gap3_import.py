"""Task B5.1 驗證（-k gap3_import）：新 schema 過（JSON／CSV 巢狀欄）、舊三欄投新端點 ⇒ 400 顯式 migration 提示、
新 schema 投舊端點 ⇒ 400、混合新舊欄 ⇒ 422 逐列 reason 指出缺欄、validate_only 不落檔、list/get、API 層不重複實作契約檢查。"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import case_import_service as svc_mod
from tests.momentum.event_samples.test_import_contract import make_event

client = TestClient(app)
REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    svc = svc_mod.EventImportService(storage_dir=tmp_path / "events")
    monkeypatch.setattr(svc_mod, "_event_import_service", svc)
    return svc


def _records(n=2):
    return [make_event(i, label=i % 2) for i in range(n)]


def test_gap3_import_json_new_schema_accepted_and_stored(_isolated_storage):
    r = client.post("/api/v1/case/import-events/json", json={"records": _records(), "source_name": "unit"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted"] and body["n_valid"] == 2 and body["import_id"] and len(body["upload_sha256"]) == 64 and body["source_digest_verified"] is False
    assert Path(body["stored_path"]).is_file()
    lst = client.get("/api/v1/case/events").json()
    assert lst["total"] == 1 and lst["imports"][0]["import_id"] == body["import_id"]
    assert lst["imports"][0]["symbols"] == ["ETHUSDT"] and lst["imports"][0]["n_events"] == 2
    det = client.get(f"/api/v1/case/events/{body['import_id']}").json()
    assert len(det["records"]) == 2 and det["records"][0]["label_definition"]["label_return_mode"] == "close_to_close"
    assert client.get("/api/v1/case/events/nope").status_code == 404


def test_gap3_import_validate_only_does_not_store(_isolated_storage):
    r = client.post("/api/v1/case/import-events/json", json={"records": _records(), "validate_only": True})
    assert r.status_code == 200 and r.json()["import_id"] is None and r.json()["stored_path"] is None
    assert client.get("/api/v1/case/events").json()["total"] == 0


def test_gap3_import_csv_with_nested_json_and_dotted_columns():
    ev = make_event(0, label=1)
    ev2 = make_event(1, label=0)
    # 列 1：label_definition 為 JSON 儲存格；列 2：dotted 欄
    header = ["event_id", "symbol", "timeframe", "t0", "decision_offset_bars", "entry_price_semantic", "direction", "scenario",
              "label", "label_definition", "label_definition.rule_id", "label_definition.canonical_digest",
              "label_definition.window.horizon_bars", "label_definition.label_return_mode", "control_kind",
              "source_file_digest", "data_snapshot_digest"]
    ld = ev2["label_definition"]
    rows = [
        [ev["event_id"], ev["symbol"], ev["timeframe"], ev["t0"], 0, ev["entry_price_semantic"], "long", "C", 1,
         json.dumps(ev["label_definition"]).replace('"', '""'), "", "", "", "", ev["control_kind"], ev["source_file_digest"], ev["data_snapshot_digest"]],
        [ev2["event_id"], ev2["symbol"], ev2["timeframe"], ev2["t0"], 0, ev2["entry_price_semantic"], "long", "C", 0,
         "", ld["rule_id"], ld["canonical_digest"], ld["window"]["horizon_bars"], ld["label_return_mode"], ev2["control_kind"], ev2["source_file_digest"], ev2["data_snapshot_digest"]],
    ]
    csv = ",".join(header) + "\n" + "\n".join(",".join(f'"{c}"' if isinstance(c, str) and c.startswith("{") else str(c) for c in row) for row in rows) + "\n"
    r = client.post("/api/v1/case/import-events", files={"file": ("ev.csv", csv.encode("utf-8"), "text/csv")}, params={"validate_only": "true"})
    assert r.status_code == 200, r.text
    assert r.json()["n_valid"] == 2


def test_gap3_import_legacy_three_columns_rejected_with_migration_hint():
    csv = "symbol,timestamp,Positive_case,timeframe\nETHUSDT,1704067200,1,12h\nETHUSDT,1704110400,0,12h\n"
    r = client.post("/api/v1/case/import-events", files={"file": ("old.csv", csv.encode(), "text/csv")})
    assert r.status_code == 400
    d = r.json()["detail"]
    assert d["kind"] == "legacy_schema_detected" and "import-events" in d["migration_hint"]["endpoint"]
    assert "event_id" in d["migration_hint"]["required_fields_absent"] and "label_definition" in d["migration_hint"]["required_fields_absent"]
    assert "t0" in json.dumps(d["migration_hint"]["field_mapping"], ensure_ascii=False)
    # JSON 端點同樣拒
    r2 = client.post("/api/v1/case/import-events/json", json={"records": [{"symbol": "ETHUSDT", "timestamp": 1704067200, "Positive_case": 1}]})
    assert r2.status_code == 400 and r2.json()["detail"]["kind"] == "legacy_schema_detected"


def test_gap3_import_new_schema_on_legacy_endpoint_rejected_explicitly():
    ev = make_event(0)
    csv = "event_id,symbol,timeframe,t0,label\n" + f"{ev['event_id']},{ev['symbol']},{ev['timeframe']},{ev['t0']},1\n"
    r = client.post("/api/v1/case/import", files={"file": ("new.csv", csv.encode(), "text/csv")}, params={"validate_only": "true"})
    assert r.status_code == 400
    assert r.json()["detail"]["kind"] == "new_schema_on_legacy_endpoint" and "import-events" in r.json()["detail"]["message"]


def test_gap3_import_mixed_columns_rejected_listing_missing_fields():
    """混合新舊欄（有 event_id/t0/label 但缺 label_definition/control_kind…）⇒ 422 逐列 reason＝missing_required_field 指出缺欄。"""
    recs = [{"event_id": "e0", "symbol": "ETHUSDT", "timeframe": "12h", "t0": 1704067200000, "label": 1, "Positive_case": 1},
            {"event_id": "e1", "symbol": "ETHUSDT", "timeframe": "12h", "t0": 1704110400000, "label": 0}]
    r = client.post("/api/v1/case/import-events/json", json={"records": recs})
    assert r.status_code == 422
    d = r.json()["detail"]
    assert d["kind"] == "contract_violation"
    fields = {(f["row"], f["field"], f["reason"]) for f in d["failures"]}
    assert (0, "label_definition", "missing_required_field") in fields and (0, "control_kind", "missing_required_field") in fields
    assert (0, "Positive_case", "unknown_field") in fields
    assert set(d["migration_hint"]["required_fields_absent"]) >= {"label_definition", "control_kind"}
    assert client.get("/api/v1/case/events").json()["total"] == 0          # 拒收不落檔


def test_gap3_import_contract_reasons_passthrough_not_reimplemented():
    """API 層不得重複實作契約檢查：failures 字面全來自契約檔；service 檔無自寫 reason 字面。"""
    from momentum.factories import create_event_import_contract
    reasons = set(create_event_import_contract()["import_failure_reasons"])
    bad = [make_event(0, t0=1704067200, label=1), make_event(1, label=0, control_kind="platform_random_bars")]
    r = client.post("/api/v1/case/import-events/json", json={"records": bad})
    assert r.status_code == 422
    got = {f["reason"] for f in r.json()["detail"]["failures"]}
    assert got <= reasons and {"invalid_timestamp_unit", "not_implemented_platform_random_bars"} <= got
    src = (REPO / "api" / "services" / "case_import_service.py").read_text(encoding="utf-8")
    gap3_part = src.split("GAP-3 Task B5.1", 1)[1]
    for literal in ("invalid_timestamp_unit", "missing_required_field", "enum_violation", "duplicate_event_id"):
        assert literal not in gap3_part, f"API 層不得複列契約 reason 字面：{literal}"
    assert re.search(r"create_event_sample_pipeline\(\)", gap3_part)        # 經 factories 出口消費


def test_gap3_import_allowed_filtering_params_from_contract():
    """B3 follow-up：/search 篩選參數允許清單改讀契約出口（requests.py 不再硬編碼）。"""
    from api.models.requests import FilterConditionRequest
    from momentum.factories import create_condition_engine_contract
    allowed = set(create_condition_engine_contract()["allowed_filtering_params"])
    assert "price_change" in allowed
    src = (REPO / "api" / "models" / "requests.py").read_text(encoding="utf-8")
    assert "{'price_change'}" not in src
    with pytest.raises(ValueError):
        FilterConditionRequest(condition_type="percentage", parameter="rsi_14", operator=">=", value=1)


def test_gap3_import_analyze_tables_real_kline(_isolated_storage):
    """B5.2 資料源：POST /case/events/{id}/analyze ⇒ 對齊→去重→切分＋兩表（真實 kline）；辨別表 not_computed 帶 reason；404／缺 kline 顯式。"""
    BASE, H12 = 1704067200000, 43200000
    recs = [make_event(i, t0=BASE + x * H12, label=i % 2) for i, x in enumerate([300, 420, 560, 700, 820, 940])]
    imp = client.post("/api/v1/case/import-events/json", json={"records": recs}).json()
    r = client.post(f"/api/v1/case/events/{imp['import_id']}/analyze", json={"horizons": [1, 2], "n_boot": 20, "tier_min_test_events": 0})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["n_input"] == 6 and body["summary"]["accounting_ok"] is True
    fwd = body["tables"]["event_forward_return_table"]
    assert fwd["statistic_kind"] == "event_return" and set(fwd["sensitivity_micro"]) == {"1", "2"}
    assert "common" in fwd and "formal_pooled_inference_allowed" in fwd["common"]
    disc = body["tables"]["binary_discrimination_table"]
    assert disc["capability_status"] == "not_computed" and disc["reason"]
    assert sorted(body["event_timestamps"]) == sorted(e["t0"] for e in recs)
    assert client.post("/api/v1/case/events/nope/analyze", json={}).status_code == 404
    bad = [make_event(i, symbol="NOPEUSDT", t0=BASE + x * H12, label=i % 2) for i, x in enumerate([300, 420])]
    imp2 = client.post("/api/v1/case/import-events/json", json={"records": bad}).json()
    r2 = client.post(f"/api/v1/case/events/{imp2['import_id']}/analyze", json={})
    assert r2.status_code == 409 and r2.json()["detail"]["kind"] == "bars_unavailable"
