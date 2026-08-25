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
    from momentum.factories import create_event_sample_pipeline
    reasons = set(create_event_sample_pipeline().import_contract()["import_failure_reasons"])
    # t0=1704067：兩帶皆不落入（×1000 仍 < ms_magnitude_min）⇒ 單位判不出，維持 invalid_timestamp_unit。
    # （原用 1704067200＝秒級；GAP-3 UX Task 1.4 起秒級會被偵測並 ×1000，不再是不合法值。）
    bad = [make_event(0, t0=1704067, label=1), make_event(1, label=0, control_kind="platform_random_bars")]
    r = client.post("/api/v1/case/import-events/json", json={"records": bad})
    assert r.status_code == 422
    got = {f["reason"] for f in r.json()["detail"]["failures"]}
    assert got <= reasons and {"invalid_timestamp_unit", "not_implemented_platform_random_bars"} <= got
    src = (REPO / "api" / "services" / "case_import_service.py").read_text(encoding="utf-8")
    gap3_part = src.split("GAP-3 Task B5.1", 1)[1]
    for literal in ("invalid_timestamp_unit", "missing_required_field", "enum_violation", "duplicate_event_id",
                    "column_mapping_missing", "column_not_found_in_file", "label_column_not_binary",
                    "heterogeneous_rows_in_batch"):
        assert literal not in gap3_part, f"API 層不得複列契約 reason 字面：{literal}"
    assert re.search(r"create_event_sample_pipeline\(\)", gap3_part)        # 經 factories 出口消費
    assert "validate_event_import" not in gap3_part and "import_contract import" not in gap3_part   # 不直 import validator（COMPOSER 建議）


def test_gap3_import_allowed_filtering_params_from_contract():
    """B3 follow-up：/search 篩選參數允許清單改讀契約出口（requests.py 不再硬編碼）。"""
    from api.models.requests import FilterConditionRequest
    from momentum.factories import create_event_sample_pipeline
    allowed = set(create_event_sample_pipeline().condition_engine_contract()["allowed_filtering_params"])
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


def test_gap3_import_new_schema_case_variants_on_legacy_endpoint():
    """CODEX-R1-P2-06 RECHECK：`Event_ID,T0,Label`／BOM／引號變體投舊端點 ⇒ 仍 400 new_schema_on_legacy_endpoint（非 generic 缺欄錯）。"""
    for header in ("Event_ID,Symbol,Timeframe,T0,Label", '"event_id","symbol","timeframe","t0","label"', "﻿EVENT_ID,symbol,timeframe,t0,LABEL"):
        csv = header + "\nev0,ETHUSDT,12h,1704067200000,1\n"
        r = client.post("/api/v1/case/import", files={"file": ("v.csv", csv.encode("utf-8"), "text/csv")}, params={"validate_only": "true"})
        assert r.status_code == 400 and r.json()["detail"]["kind"] == "new_schema_on_legacy_endpoint", (header, r.text)
    # 舊三欄大小寫變體投新端點 ⇒ legacy_schema_detected
    r2 = client.post("/api/v1/case/import-events/json", json={"records": [{"Symbol": "ETHUSDT", "Timestamp": 1704067200, "POSITIVE_CASE": 1}]})
    assert r2.status_code == 400 and r2.json()["detail"]["kind"] == "legacy_schema_detected"


def test_gap3_import_ic_timestamps_only_enables_event_filter():
    """CODEX-R1-P1-01 RECHECK：ICAnalyzeRequest 只給 event_timestamps（無 query）⇒ config_override 啟用 event_filter（否則 orchestrator mode=none 靜默丟事件）。"""
    from api.models.ic_models import ICAnalyzeRequest
    from api.services.ic_analysis_service import ICAnalysisService
    svc = ICAnalysisService()
    ov = svc._build_config_override(ICAnalyzeRequest(event_timestamps=[1704067200, 1704110400]))
    assert ov["event_filter"]["enabled"] is True and "query" not in ov["event_filter"]
    ov2 = svc._build_config_override(ICAnalyzeRequest(event_query="close > 1"))
    assert ov2["event_filter"] == {"enabled": True, "query": "close > 1"}
    assert svc._build_config_override(ICAnalyzeRequest()) is None


def test_gap3_import_analyze_all_bars_and_ic_seconds(_isolated_storage):
    """U11：analyze 端點附全 K 線驗證（rule＝事件成員）；event_timestamps 為 ms、event_timestamps_ic_seconds 為秒（GROK-R1-P2-02）。"""
    BASE, H12 = 1704067200000, 43200000
    recs = [make_event(i, t0=BASE + x * H12, label=i % 2) for i, x in enumerate([300, 420, 560, 700])]
    imp = client.post("/api/v1/case/import-events/json", json={"records": recs}).json()
    body = client.post(f"/api/v1/case/events/{imp['import_id']}/analyze", json={"horizons": [1], "n_boot": 10, "tier_min_test_events": 0}).json()
    ab = body["tables"]["all_bars_evaluation"]
    assert ab["statistic_kind"] == "all_bars_evaluation" and ab["capability_status"] == "ok" and ab["counts"]["n_total"] > 1000
    assert ab["overall"]["prevalence_learn"] == 0.5 and ab["label_id"] == "event_membership"
    assert all(t >= 1e12 for t in body["event_timestamps"]) and body["event_timestamps_ic_seconds"] == [t // 1000 for t in body["event_timestamps"]]


def test_gap3_import_json_verify_source_digest_rejected():
    """CODEX-R2-P1-03 RECHECK：JSON 端點傳 verify_source_digest=true ⇒ 400 顯式（body 位元組 ≠ 契約來源檔，比對必然不符）。"""
    r = client.post("/api/v1/case/import-events/json", json={"records": _records(), "verify_source_digest": True})
    assert r.status_code == 400
    d = r.json()["detail"]
    assert d["kind"] == "verify_unsupported_on_json_endpoint" and "import-events" in d["message"]
    assert client.get("/api/v1/case/events").json()["total"] == 0                # 拒收不落檔
    # 預設關 ⇒ 正常收
    assert client.post("/api/v1/case/import-events/json", json={"records": _records()}).status_code == 200


def test_gap3_import_file_verify_requires_source_file(tmp_path):
    """檔案端點：開 verify 但只給事件檔 ⇒ 400 顯式引導（自我對證必然不符，不讓使用者看一堆 digest_mismatch）；
    關閉 verify ⇒ 正常收（預設語意）。可通過之路徑見 test_gap3_import_verify_with_companion_source_file_passes。"""
    import hashlib
    recs = _records()
    body = json.dumps(recs, ensure_ascii=False).encode("utf-8")
    fixed = [dict(r, source_file_digest=hashlib.sha256(body).hexdigest()) for r in recs]
    body2 = json.dumps(fixed, ensure_ascii=False).encode("utf-8")
    r = client.post("/api/v1/case/import-events", files={"file": ("ev.json", body2, "application/json")},
                    params={"validate_only": "true", "verify_source_digest": "true"})
    assert r.status_code == 400 and r.json()["detail"]["kind"] == "source_file_required_for_verify"
    assert "source_file" in r.json()["detail"]["message"]
    assert client.post("/api/v1/case/import-events", files={"file": ("ev.json", body2, "application/json")},
                       params={"validate_only": "true"}).status_code == 200


def test_gap3_import_verify_with_companion_source_file_passes(_isolated_storage):
    """CODEX-R2-P1-03 RECHECK（原 OPEN）：/search 匯出之 events＋companion source 檔可端到端通過 verify。
    來源檔 sha256 == 各列 source_file_digest ⇒ 200；不傳 source_file 而開 verify ⇒ 400 顯式引導；來源檔被改 ⇒ 422 digest_mismatch。"""
    import hashlib
    source_text = json.dumps([{"symbol": "ETHUSDT", "timeframe": "12h", "timestamp": "1704067200", "positive_case": 1, "price_change": 0.05},
                              {"symbol": "ETHUSDT", "timeframe": "12h", "timestamp": "1704110400", "positive_case": 0, "price_change": -0.01}],
                             ensure_ascii=False)
    src_bytes = source_text.encode("utf-8")
    digest = hashlib.sha256(src_bytes).hexdigest()
    recs = [dict(make_event(i, label=i % 2), source_file_digest=digest) for i in range(2)]
    events_bytes = json.dumps(recs, ensure_ascii=False).encode("utf-8")

    # ① 兩檔齊 ⇒ verify 通過並落檔
    r = client.post("/api/v1/case/import-events",
                    files={"file": ("ev.json", events_bytes, "application/json"),
                           "source_file": ("ev.source.json", src_bytes, "application/json")},
                    params={"verify_source_digest": "true"})
    assert r.status_code == 200, r.text
    assert r.json()["source_digest_verified"] is True and r.json()["n_valid"] == 2
    # ② 開 verify 但沒給 source_file ⇒ 400 顯式引導（非一堆 digest_mismatch）
    r2 = client.post("/api/v1/case/import-events", files={"file": ("ev.json", events_bytes, "application/json")},
                     params={"verify_source_digest": "true"})
    assert r2.status_code == 400 and r2.json()["detail"]["kind"] == "source_file_required_for_verify"
    # ③ 來源檔被竄改 ⇒ 422 digest_mismatch（契約字面）
    r3 = client.post("/api/v1/case/import-events",
                     files={"file": ("ev.json", events_bytes, "application/json"),
                            "source_file": ("ev.source.json", src_bytes + b" ", "application/json")},
                     params={"verify_source_digest": "true", "validate_only": "true"})
    assert r3.status_code == 422 and {f["reason"] for f in r3.json()["detail"]["failures"]} == {"digest_mismatch"}


def test_gap3_import_verify_same_file_rejected_explicitly():
    """CODEX-R4-P1-01 RECHECK：source_file 與事件檔位元組相同 ⇒ 400 source_file_must_differ_from_event_file
    （自我指涉在數學上不可能；不讓使用者收一堆 digest_mismatch）。distinct companion 路徑仍可通過。"""
    import hashlib
    recs = _records()
    body = json.dumps(recs, ensure_ascii=False).encode("utf-8")
    fixed = [dict(r, source_file_digest=hashlib.sha256(body).hexdigest()) for r in recs]
    ev = json.dumps(fixed, ensure_ascii=False).encode("utf-8")
    r = client.post("/api/v1/case/import-events",
                    files={"file": ("ev.json", ev, "application/json"), "source_file": ("ev.json", ev, "application/json")},
                    params={"verify_source_digest": "true", "validate_only": "true"})
    assert r.status_code == 400
    d = r.json()["detail"]
    assert d["kind"] == "source_file_must_differ_from_event_file" and "source.json" in d["message"]
    # 關閉 verify ⇒ 同檔上傳仍可收（不影響既有路徑）
    assert client.post("/api/v1/case/import-events",
                       files={"file": ("ev.json", ev, "application/json"), "source_file": ("ev.json", ev, "application/json")},
                       params={"validate_only": "true"}).status_code == 200
