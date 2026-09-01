"""GAP-3：`/search` 匯出之 CSV **可直接回灌**（`-k gap3_csv_roundtrip`）。

出生事故（2026-09-01 使用者 UAT B9）：`/search` 的「導出CSV檔案」用展示用欄名
（`Timestamp`／`Positive_Case`／`Price_Change_%`），與契約欄名／型別／單位全對不上
⇒ 使用者在 Excel 標好正反例後**回不去**：要逐欄對映，還要手寫含兩個 64 位 hex digest
的批次預設 JSON。使用者原話：「我根本也看不懂也沒辦法自己寫」。

🔴 **本檔驗的是「匯出的那個位元組串，後端收不收」**，不是「函式有沒有產出字串」——
前者是使用者真的會走的那一步。前端的 `buildEventContractCsv()` 之欄名規則若與後端
`_csv_rows_to_records()` 的解析規則漂移，這裡會紅。

🔴 **CSV 由前端產生、後端解析，兩邊是不同語言**，故本檔以**逐字重現前端規則**的方式
產生 CSV（見 `_flatten`／`_cell` 之註解）——那是刻意的第二份實作：
它與 `frontend/src/lib/eventContractCsv.ts` 互為對照，任一邊改了規則而另一邊沒跟，
`eventContractCsv.test.ts`（前端）與本檔（後端）**兩邊都會紅**。
"""

from __future__ import annotations

import io
import json
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import case_import_service as svc_mod
from tests.momentum.event_samples.test_import_contract import canonical_event as make_event

client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    svc = svc_mod.EventImportService(storage_dir=tmp_path / "events")
    monkeypatch.setattr(svc_mod, "_event_import_service", svc)
    return svc


def _flatten(obj: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """與 `eventContractCsv.ts::flatten` 同規則：巢狀 → 點路徑；陣列為葉節點。"""
    out: Dict[str, Any] = {}
    for k, v in obj.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        else:
            out[key] = v
    return out


def _cell(v: Any) -> str:
    """與 `eventContractCsv.ts::cell` 同規則。"""
    if v is None:
        return ""
    s = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else str(v)
    if any(ch in s for ch in ',"\n\r'):
        return '"' + s.replace('"', '""') + '"'
    return s


def _to_csv(records: List[Dict[str, Any]], extra: List[Dict[str, Any]] | None = None) -> bytes:
    rows = []
    for i, rec in enumerate(records):
        flat = _flatten(rec)
        for k, v in ((extra or [{}] * len(records))[i]).items():
            if v not in (None, ""):
                flat[f"meta.{k}"] = v
        rows.append(flat)
    names = sorted({k for r in rows for k in r},
                   key=lambda n: (1 if n.startswith("meta.") else 0, n))
    lines = [",".join(names)]
    lines += [",".join(_cell(r.get(n)) for n in names) for r in rows]
    return "\n".join(lines).encode("utf-8")


def _upload(csv_bytes: bytes, *, validate_only: bool = True):
    return client.post(
        "/api/v1/case/import-events",
        files={"file": ("gap3_events.csv", csv_bytes, "text/csv")},
        data={"validate_only": str(validate_only).lower()},
    )


def _records(n: int = 4) -> List[Dict[str, Any]]:
    return [make_event(i, label=i % 2) for i in range(n)]


def test_gap3_csv_roundtrip_contract_csv_is_accepted_with_zero_mapping():
    """🔴 主條：契約欄名之 CSV ⇒ 走**無對映**端點直接被接受。

    這一條紅＝使用者在 Excel 改完 label 後回不去（正是本次要修的病）。
    """
    recs = _records()
    r = _upload(_to_csv(recs))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted"] is True
    assert body["n_valid"] == len(recs)


def test_gap3_csv_roundtrip_meta_columns_do_not_get_rejected():
    """🔴 分析欄放進 `meta.` ⇒ **不得**被 `unknown_field` 拒收。

    使用者要在 Excel 裡靠這些欄篩選（市場階段、波動度分類…），
    若它們一律被拒，那份 CSV 對使用者就沒有用。
    """
    recs = _records()
    extra = [{"Market_Phase": "bull", "Volatility_Class": "high", "price_change": 0.031}] * len(recs)
    r = _upload(_to_csv(recs, extra))
    assert r.status_code == 200, r.text
    assert r.json()["accepted"] is True


def test_gap3_csv_roundtrip_over_unknown_top_level_column_still_rejected():
    """🔴 **over 向**：把分析欄放在**頂層**（不加 `meta.`）⇒ 仍須被拒。

    這條證明上一條的通過**不是因為契約被放寬**——`meta.` 是唯一的容納處，
    契約之頂層鍵集仍然是閉集。只驗「meta 可用」而不驗這條，
    就分不出「正確容納」與「整個不檢查了」。
    """
    recs = _records()
    csv_bytes = _to_csv(recs)
    head, *rest = csv_bytes.decode("utf-8").split("\n")
    broken = "\n".join([head + ",Market_Phase"] + [r + ",bull" for r in rest])
    r = _upload(broken.encode("utf-8"))
    # 422＝contract_violation（逐列 reason）；400 是解析／schema 層之拒收，兩者不同層
    assert r.status_code == 422, f"頂層未知欄應被拒，實得 {r.status_code}：{r.text[:200]}"
    failures = r.json()["detail"]["failures"]
    assert any(f.get("field") == "Market_Phase" for f in failures), failures[:3]


def test_gap3_csv_roundtrip_label_edited_in_excel_takes_effect():
    """使用者在 Excel 改 `label` ⇒ 落檔就是改後的值（這是整條路存在的理由）。"""
    recs = _records(4)
    csv_text = _to_csv(recs).decode("utf-8")
    lines = csv_text.split("\n")
    header = lines[0].split(",")
    li = header.index("label")
    # 把全部改成 1 會缺類別（missing_control_group）⇒ 只翻轉第一列，並確認落檔跟著變
    first = lines[1].split(",")
    before = first[li]
    first[li] = "1" if before == "0" else "0"
    lines[1] = ",".join(first)
    r = _upload("\n".join(lines).encode("utf-8"), validate_only=False)
    assert r.status_code == 200, r.text
    import_id = r.json()["import_id"]
    detail = client.get(f"/api/v1/case/events/{import_id}").json()
    by_id = {row["event_id"]: row["label"] for row in detail["batch_facts"]["label"]}
    assert by_id[recs[0]["event_id"]] == int(first[li])
    assert by_id[recs[0]["event_id"]] != int(before)


def test_gap3_csv_roundtrip_lookahead_bars_declared_dotted_survives():
    """🔴 `/search` 匯出之 CSV **每列必帶** `lookahead_bars_declared.<tf>` ⇒ 必須收得下。

    出生事故（2026-09-01，`scripts/gen_uat_samples.py` 之後端回灌檢查抓到）：
    後端 dotted 還原用的是**手寫**欄名清單，`lookahead_bars_declared` 加進契約時沒同步
    ⇒ 整批 `unknown_field` 被拒。本條把「這一欄」釘住，`_nested_fields()` 改回手寫清單即紅。
    """
    recs = [make_event(i, label=i % 2) for i in range(2)]
    for r in recs:
        r["lookahead_bars_declared"] = {r["timeframe"]: 3}
    csv_bytes = _to_csv(recs)
    assert b"lookahead_bars_declared." in csv_bytes, "前置條件：該欄要真的以 dotted 形式在檔裡"
    r = _upload(csv_bytes, validate_only=False)
    assert r.status_code == 200, r.text
    detail = client.get(f"/api/v1/case/events/{r.json()['import_id']}").json()
    got = detail["records"][0]["lookahead_bars_declared"]
    assert got == recs[0]["lookahead_bars_declared"], got


def test_gap3_csv_roundtrip_nested_dotted_columns_survive():
    """巢狀欄以點路徑往返後仍是巢狀物件（不是被壓成字串）。"""
    recs = _records(2)
    r = _upload(_to_csv(recs), validate_only=False)
    assert r.status_code == 200, r.text
    detail = client.get(f"/api/v1/case/events/{r.json()['import_id']}").json()
    ld = detail["records"][0]["label_definition"]
    assert isinstance(ld, dict)
    assert isinstance(ld["window"], dict)
    assert ld["window"]["horizon_bars"] == recs[0]["label_definition"]["window"]["horizon_bars"]
    assert ld["label_return_mode"] == recs[0]["label_definition"]["label_return_mode"]
