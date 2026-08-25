"""GAP-3 UX Task 1.8 驗證（-k gap3_heterogeneous_rows）：異質列顯式拒收（A-5′）。

SPEC L1614–1626／TODO Task 1.8。判準字面之唯一來源＝SPEC 該 Task「驗證」欄：
①混 long/short 之 fixture ⇒ reason `== 'heterogeneous_rows_in_batch'` 且**落檔數 `== 0`**；
②`batch_defaults` 指定 `scenario='A'` 而列間混 A／B ⇒ **落檔數 `== 0`**；
訊息須列出**前 3 個**衝突列號與欄名（斷言列號數 `== 3`）。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import case_import_service as svc_mod
from tests.momentum.event_samples.test_import_contract import canonical_event as make_event

client = TestClient(app)
REASON = "heterogeneous_rows_in_batch"


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    svc = svc_mod.EventImportService(storage_dir=tmp_path / "events")
    monkeypatch.setattr(svc_mod, "_event_import_service", svc)
    return svc


def _post(records, **body):
    return client.post("/api/v1/case/import-events/json", json={"records": records, **body})


def _stored_count() -> int:
    return client.get("/api/v1/case/events").json()["total"]


def test_gap3_heterogeneous_rows_direction_rejected_with_first_three_rows(_isolated_storage):
    """① 混 long/short ⇒ 得該 reason、落檔數 == 0，且**只**列出前 3 個衝突列號（本 fixture 有 4 個衝突列）。"""
    recs = [make_event(0, label=1, direction="long")] + [
        make_event(i, label=i % 2, direction="short") for i in range(1, 5)
    ]
    r = _post(recs)
    assert r.status_code == 422, r.text
    failures = [f for f in r.json()["detail"]["failures"] if f["reason"] == REASON]
    assert [f["field"] for f in failures] == ["direction"] * 3
    assert [f["row"] for f in failures] == [1, 2, 3], "須列出前 3 個衝突列號（不是全部 4 個、不是別的列）"
    assert len({f["row"] for f in failures}) == 3
    assert failures[0]["message"] and "direction" in failures[0]["message"]
    assert _stored_count() == 0


def test_gap3_heterogeneous_rows_scenario_mixed_under_batch_defaults(_isolated_storage):
    """② `batch_defaults` 指定 scenario='A' 而列間**自帶**混 A／B ⇒ 落檔數 == 0（defaults 不得掩蓋列自帶值）。

    🔴 這是 Task 7.1 把 `scenario` 由寫死 'C' 擴為四值可選之後的必要 fixture。
    """
    recs = [make_event(0, label=1, scenario="A")] + [make_event(i, label=i % 2, scenario="B") for i in range(1, 4)]
    r = _post(recs, batch_defaults={"scenario": "A"})
    assert r.status_code == 422, r.text
    failures = [f for f in r.json()["detail"]["failures"] if f["reason"] == REASON]
    assert [f["field"] for f in failures] == ["scenario"] * 3
    assert [f["row"] for f in failures] == [1, 2, 3]
    assert _stored_count() == 0


def test_gap3_heterogeneous_rows_label_definition_mixed(_isolated_storage):
    """③ `label_definition` 列間不一致（第三個維度）亦拒；比對為**遞迴值相等**，非物件同一性。"""
    base = make_event(0, label=1)
    other = dict(base["label_definition"], rule_id="rule-y")
    recs = [base] + [make_event(i, label=i % 2, label_definition=other) for i in range(1, 4)]
    r = _post(recs)
    assert r.status_code == 422, r.text
    failures = [f for f in r.json()["detail"]["failures"] if f["reason"] == REASON]
    assert [f["field"] for f in failures] == ["label_definition"] * 3
    assert _stored_count() == 0


def test_gap3_heterogeneous_rows_batch_defaults_fill_absent_is_accepted(_isolated_storage):
    """④ 不誤擋：列**缺**該維度、由 batch_defaults 填補 ⇒ 同質 ⇒ 接受並落檔（否則 1.8 會擋掉正常批次）。"""
    recs = []
    for i in range(2):
        e = make_event(i, label=i % 2)
        e.pop("scenario")
        recs.append(e)
    r = _post(recs, batch_defaults={"scenario": "C"})
    assert r.status_code == 200, r.text
    assert r.json()["n_valid"] == 2 and _stored_count() == 1


def test_gap3_heterogeneous_rows_no_silent_first_row_broadcast(_isolated_storage):
    """⑤ **不靜默取第一列之值套用全批**：混值批次不得因「首列是 long」而全部變 long 後放行。"""
    recs = [make_event(0, label=1, direction="long")] + [
        make_event(i, label=i % 2, direction="short") for i in range(1, 4)
    ]
    r = _post(recs)
    assert r.status_code == 422
    assert _stored_count() == 0
    # 同一批加上 batch_defaults 指定 direction 亦不得放行（defaults 只填缺值）
    assert _post(recs, batch_defaults={"direction": "long"}).status_code == 422
    assert _stored_count() == 0


def test_gap3_heterogeneous_rows_homogeneous_batch_unaffected(_isolated_storage):
    """⑥ 同質批次完全不受影響（本檢查不得產生偽陽性）。"""
    r = _post([make_event(0, label=1), make_event(1, label=0)])
    assert r.status_code == 200 and r.json()["n_valid"] == 2
    assert _stored_count() == 1
