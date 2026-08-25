"""GAP-3 UX Task 1.4 驗證（-k gap3_t0_unit_detect）：t0 單位偵測。

SPEC L1566–1577／TODO Task 1.4。判準字面之唯一來源＝SPEC 該 Task「驗證」欄：
三組 fixture（ms／秒／不合法）各 1 測；秒級輸入之輸出精確 `== 1704067200000`。

本檔另證兩件 TODO「實作要點」所要求之性質：
- 偵測函式為 **exported 單一函式**，CSV 與 JSON 兩路徑共用（端到端各一測）；
- 判不出單位時**不猜預設值**（原值保留，交由契約量級閘逐列拒）。
"""

from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import case_import_service as svc_mod
from momentum.factories import create_event_sample_pipeline
from tests.momentum.event_samples.test_import_contract import make_event

client = TestClient(app)

#: SPEC 邊界①之字面：`1704067200`（秒）⇒ `== 1704067200000`。
SECONDS_INPUT = 1704067200
EXPECTED_MS = 1704067200000


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    svc = svc_mod.EventImportService(storage_dir=tmp_path / "events")
    monkeypatch.setattr(svc_mod, "_event_import_service", svc)
    return svc


def _detect():
    """經 momentum 取得**唯一** exported 偵測函式（api 層走 pipeline 出口，見 test_gap3_csv_import 之 AST oracle）。"""
    from momentum.Analysis.event_samples.import_contract import detect_t0_unit_ms

    return detect_t0_unit_ms


def test_gap3_t0_unit_detect_milliseconds_passthrough():
    """① ms 級輸入原樣回傳（不重複 ×1000）。"""
    assert _detect()(EXPECTED_MS) == EXPECTED_MS


def test_gap3_t0_unit_detect_seconds_scaled_exact():
    """② 秒級輸入 ×1000，輸出**精確**等於 1704067200000（SPEC 邊界①）。"""
    assert _detect()(SECONDS_INPUT) == EXPECTED_MS


def test_gap3_t0_unit_detect_undetectable_rejected_without_guessing():
    """③ 兩帶皆不落入 ⇒ raise，且 reason 字面＝契約既有值；**不得**回傳任何猜測值。"""
    from momentum.Analysis.event_samples.import_contract import T0UnitUndetectedError

    contract = create_event_sample_pipeline().import_contract()
    ms_min = int(contract["ms_magnitude_min"])
    # 兩側之模糊值：×1000 仍 < ms_min（過小）／已 >= ms_min*1000（量級像 ns，過大）
    for bad in (ms_min // 10**6, ms_min * 1000, "1704067200", None, 1.5, True):
        with pytest.raises(T0UnitUndetectedError) as exc:
            _detect()(bad)
        assert exc.value.reason in set(contract["import_failure_reasons"])


def test_gap3_t0_unit_detect_bands_are_disjoint():
    """④ ms 帶與秒帶依建構互斥 ⇒ 不存在「同時可解為兩種單位」之值（故無須猜）。"""
    contract = create_event_sample_pipeline().import_contract()
    ms_min = int(contract["ms_magnitude_min"])
    ms_max = ms_min * 1000
    for v in (ms_min, ms_min + 1, ms_max - 1, ms_min // 1000, EXPECTED_MS, SECONDS_INPUT):
        in_ms = ms_min <= v < ms_max
        in_sec = ms_min <= v * 1000 < ms_max
        assert not (in_ms and in_sec), f"{v} 同時落在兩帶 ⇒ 判定有歧義"


def test_gap3_t0_unit_detect_shared_by_json_path(_isolated_storage):
    """⑤ JSON 路徑：秒級 t0 匯入後落檔為 ms（證偵測已接在共用函式上）。"""
    recs = [make_event(0, label=1, t0=SECONDS_INPUT), make_event(1, label=0, t0=SECONDS_INPUT + 43200)]
    r = client.post("/api/v1/case/import-events/json", json={"records": recs})
    assert r.status_code == 200, r.text
    det = client.get(f"/api/v1/case/events/{r.json()['import_id']}").json()
    assert [rec["t0"] for rec in det["records"]] == [EXPECTED_MS, EXPECTED_MS + 43200000]


def test_gap3_t0_unit_detect_shared_by_csv_mapping_path(_isolated_storage):
    """⑥ CSV 對映路徑：同一秒級輸入得到**相同**毫秒輸出（兩路徑共用同一偵測函式）。"""
    ev = make_event(0, label=1)
    rows = [
        {"我的id": "ev0", "幣種": "ETHUSDT", "週期": "12h", "秒時間": str(SECONDS_INPUT), "答案": "1"},
        {"我的id": "ev1", "幣種": "ETHUSDT", "週期": "12h", "秒時間": str(SECONDS_INPUT + 43200), "答案": "0"},
    ]
    csv = "我的id,幣種,週期,秒時間,答案\n" + "\n".join(
        ",".join(r[k] for k in ("我的id", "幣種", "週期", "秒時間", "答案")) for r in rows) + "\n"
    mapping = {"event_id": "我的id", "symbol": "幣種", "timeframe": "週期", "t0": "秒時間", "label": "答案"}
    defaults = {k: ev[k] for k in ("decision_offset_bars", "entry_price_semantic", "direction", "scenario",
                                   "label_definition", "control_kind", "source_file_digest", "data_snapshot_digest")}
    r = client.post(
        "/api/v1/case/import-events/csv",
        files={"file": ("mine.csv", io.BytesIO(csv.encode("utf-8")), "text/csv")},
        data={"column_mapping": json.dumps(mapping, ensure_ascii=False), "batch_defaults": json.dumps(defaults)},
    )
    assert r.status_code == 200, r.text
    det = client.get(f"/api/v1/case/events/{r.json()['import_id']}").json()
    assert [rec["t0"] for rec in det["records"]] == [EXPECTED_MS, EXPECTED_MS + 43200000]


def test_gap3_t0_unit_detect_undetectable_still_rejected_end_to_end(_isolated_storage):
    """⑦ 判不出者原值保留 ⇒ 契約量級閘逐列拒且**落檔數 == 0**（不猜預設值之端到端證據）。"""
    contract = create_event_sample_pipeline().import_contract()
    recs = [make_event(0, label=1, t0=int(contract["ms_magnitude_min"]) // 10**6), make_event(1, label=0)]
    r = client.post("/api/v1/case/import-events/json", json={"records": recs})
    assert r.status_code == 422
    reasons = {f["reason"] for f in r.json()["detail"]["failures"]}
    assert "invalid_timestamp_unit" in reasons
    assert client.get("/api/v1/case/events").json()["total"] == 0
