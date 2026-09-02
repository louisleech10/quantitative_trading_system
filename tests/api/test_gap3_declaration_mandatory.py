"""GAP-3 UX R 重開（SPEC D-8）：Task 1.11「一律宣告」＋ Task 1.9′ 後端面之驗收（-k gap3_declaration_mandatory）。

SPEC Task 1.11 驗證 ②③④、Task 1.9′ 之 `0`／負數值域（前後端 validator `v < 1` → `v < 0`）、
`POST /case/lookahead-declaration/preview-columns`（唯一實作 `preview_from_columns`）、
以及 codex R35 轉入之三條實作批驗收條件（`CODEX-R35-P1-02／03／04`）。

🔴 mutation（皆須紅）：
- `needs` 改回條件式 ⇒ ②（`test_..._02_*`）③ 紅；
- JSON 直傳缺欄改回「落檔但 L3 封鎖」 ⇒ ④ 紅（落檔數不為 0）；
- validator 改回 `v < 1` ⇒ `test_..._zero_is_accepted` 紅；
- preview 端點自寫換算表（不經 `preview_from_columns`）⇒ `test_..._preview_columns_uses_single_impl` 紅。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import case_import_service as svc_mod
from momentum.Analysis.event_samples import lookahead_declaration as decl_mod
from tests.api._gap3_declaration import declaration_form
from tests.api.test_gap3_csv_roundtrip import _to_csv
from tests.momentum.event_samples.test_import_contract import canonical_event as make_event

client = TestClient(app)
API = "/api/v1"


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    svc = svc_mod.EventImportService(storage_dir=tmp_path / "events")
    monkeypatch.setattr(svc_mod, "_event_import_service", svc)
    return svc


def _stored_count() -> int:
    return client.get(f"{API}/case/events").json()["total"]


def _records(n: int = 2, **over) -> List[Dict[str, Any]]:
    return [make_event(i, label=i % 2, **over) for i in range(n)]


def _post_json(records):
    return client.post(f"{API}/case/import-events/json", json={"records": records})


def _upload_contract_csv(records, declaration: str | None = None):
    data = {}
    if declaration is not None:
        data["lookahead_declaration"] = declaration
    return client.post(f"{API}/case/import-events",
                       files={"file": ("events.csv", _to_csv(records), "text/csv")}, data=data)


# ── Task 1.11 ②：全系統欄、全可解析、無 filters ⇒ 仍須宣告 ─────────────────────────
def test_gap3_declaration_mandatory_02_all_resolvable_no_filters_still_requires():
    recs = _records(lookahead_bars_declared=None)          # 列內不攜帶 ⇒ 唯一宣告來源＝表單
    for r in recs:
        r["future_4bar_return"] = 0.01                     # 全可解析之系統欄
        assert "filters" not in r["label_definition"]
    # preview 端（匯入端）也必須說「要宣告」
    p = client.post(f"{API}/case/import-events/lookahead-declaration",
                    files={"file": ("events.csv", _to_csv(recs), "text/csv")})
    assert p.status_code == 200, p.text
    assert p.json()["requires_declaration"] is True
    assert p.json()["default_window_bars"] == {"12h": 4}   # 只是預設候選，不是免宣告的理由
    # ③：未填宣告即送出 ⇒ fail-closed，落檔數 0
    r = _upload_contract_csv(recs)
    assert r.status_code in (400, 422), r.text
    assert r.json()["detail"]["kind"] == "lookahead_declaration_required"
    assert _stored_count() == 0
    # 對照：帶宣告即收
    ok = _upload_contract_csv(recs, declaration_form({"12h": 4}))
    assert ok.status_code == 200, ok.text
    assert ok.json()["lookahead_declaration"]["lookahead_bars_declared"] == {"12h": 4}


# ── Task 1.11 ④：JSON 直傳 ────────────────────────────────────────────────────────
def test_gap3_declaration_mandatory_04_json_missing_column_is_rejected_not_blocked():
    """整批缺 `lookahead_bars_declared` ⇒ 拒收（4xx）、落檔數 == 0（R 前之 block 已刪）。"""
    r = _post_json(_records(lookahead_bars_declared=None))
    assert r.status_code in (400, 422), r.text
    assert r.json()["detail"]["kind"] == "lookahead_declaration_required"
    assert _stored_count() == 0


def test_gap3_declaration_mandatory_04b_json_heterogeneous_maps_rejected():
    """批內兩列該欄不同值 ⇒ `heterogeneous_rows_in_batch`（契約 validator 之 reason，本層不複列）。"""
    recs = _records()
    recs[0]["lookahead_bars_declared"] = {"12h": 2}
    recs[1]["lookahead_bars_declared"] = {"12h": 5}
    r = _post_json(recs)
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["kind"] == "contract_violation"
    assert "heterogeneous_rows_in_batch" in {f["reason"] for f in r.json()["detail"]["failures"]}
    assert _stored_count() == 0


def test_gap3_declaration_mandatory_04c_json_partial_column_rejected():
    """只有部分列帶該欄 ⇒ 同樣不齊，拒收、落檔 0。"""
    recs = _records()
    recs[1].pop("lookahead_bars_declared")
    r = _post_json(recs)
    assert r.status_code in (400, 422), r.text
    assert _stored_count() == 0


def test_gap3_declaration_mandatory_04d_json_carried_map_is_the_declaration():
    """列內攜帶（Task 1.9′ 匯出時寫入）⇒ 視為宣告：receipt 與落檔列皆 == 該 map。"""
    recs = _records(lookahead_bars_declared={"12h": 3})
    r = _post_json(recs)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lookahead_declaration"]["lookahead_bars_declared"] == {"12h": 3}
    assert body["lookahead_declaration"]["requires_declaration"] is True
    det = client.get(f"{API}/case/events/{body['import_id']}").json()
    assert all(rec["lookahead_bars_declared"] == {"12h": 3} for rec in det["records"])
    assert all(rec["label_definition"]["window"]["horizon_bars"] == 3 for rec in det["records"])


def test_gap3_declaration_mandatory_04e_json_missing_timeframe_key_rejected():
    """每個出現之 tf 皆須有鍵：批含 1h 與 12h 而 map 只有 12h ⇒ 拒（不以其他 tf 之值默認）。"""
    recs = _records(lookahead_bars_declared={"12h": 2})
    recs[1]["timeframe"] = "1h"
    from momentum.Analysis.event_samples.import_contract import canonical_event_id
    recs[1]["event_id"] = canonical_event_id("ETHUSDT", "1h", recs[1]["t0"])
    r = _post_json(recs)
    assert r.status_code in (400, 422), r.text
    assert r.json()["detail"]["kind"] == "lookahead_declaration_invalid"
    assert _stored_count() == 0


# ── Task 1.9′／R35：值域為非負整數；0 須明填 ───────────────────────────────────────
def test_gap3_declaration_mandatory_zero_is_accepted_and_floor_is_one():
    recs = _records(lookahead_bars_declared=None)
    r = _upload_contract_csv(recs, declaration_form({"12h": 0}))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lookahead_declaration"]["lookahead_bars_declared"] == {"12h": 0}
    det = client.get(f"{API}/case/events/{body['import_id']}").json()
    # 宣告 oracle 為 0；`window.horizon_bars` 是 serialization floor ⇒ 1（兩者刻意不相等）
    assert all(rec["lookahead_bars_declared"] == {"12h": 0} for rec in det["records"])
    assert all(rec["label_definition"]["window"]["horizon_bars"] == 1 for rec in det["records"])


@pytest.mark.parametrize("bad", [-1, True, 1.5, "0"], ids=["negative", "bool", "float", "string"])
def test_gap3_declaration_mandatory_negative_or_non_int_rejected(bad):
    recs = _records(lookahead_bars_declared=None)
    r = _upload_contract_csv(recs, json.dumps({"declared_window_bars": {"12h": bad}, "acknowledged_unverifiable": True}))
    assert r.status_code in (400, 422), r.text
    assert r.json()["detail"]["kind"] == "lookahead_declaration_invalid"
    assert _stored_count() == 0


def test_gap3_declaration_mandatory_blank_is_not_zero():
    """留白（缺鍵）≠ 0：map 為空 ⇒ 鍵集不符而拒，不得默認為 0。"""
    recs = _records(lookahead_bars_declared=None)
    r = _upload_contract_csv(recs, json.dumps({"declared_window_bars": {}, "acknowledged_unverifiable": True}))
    assert r.status_code in (400, 422), r.text
    assert r.json()["detail"]["kind"] == "lookahead_declaration_invalid"


# ── 表單宣告 vs 列內攜帶：表單為準、單一深度真相 ──────────────────────────────────
def test_gap3_declaration_mandatory_form_declaration_overrides_carried_map():
    recs = _records(lookahead_bars_declared={"12h": 2})
    r = _upload_contract_csv(recs, declaration_form({"12h": 5}))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lookahead_declaration"]["lookahead_bars_declared"] == {"12h": 5}
    det = client.get(f"{API}/case/events/{body['import_id']}").json()
    assert all(rec["lookahead_bars_declared"] == {"12h": 5} for rec in det["records"])
    assert all(rec["label_definition"]["window"]["horizon_bars"] == 5 for rec in det["records"])
    assert any("lookahead_bars_declared" in w for w in body.get("warnings", [])), body.get("warnings")


# ── Task 1.9′：`POST /case/lookahead-declaration/preview-columns` ──────────────────
def test_gap3_declaration_mandatory_preview_columns_endpoint_shape_and_defaults():
    r = client.post(f"{API}/case/lookahead-declaration/preview-columns",
                    json={"columns": ["close", "future_4bar_return", "future24_close_return"], "timeframes": ["12h", "1h"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"timeframes", "data_columns", "default_window_bars", "requires_declaration",
                         "referenced_columns", "acknowledgement_required"}
    assert body["acknowledgement_required"] is False      # 匯出端無 records ⇒ 只有調低才須勾選
    assert body["timeframes"] == ["12h", "1h"] or body["timeframes"] == ["1h", "12h"]
    assert body["requires_declaration"] is True
    assert body["referenced_columns"] == []
    # bar 命名欄逐 tf 同根數；hour 命名欄逐 tf 不同（1h=24、12h=2）⇒ 取最大：1h=24、12h=4
    assert body["default_window_bars"] == {"1h": 24, "12h": 4}
    # 無任何未來欄 ⇒ 預設 0（前端留空不預填；不是免宣告）
    r0 = client.post(f"{API}/case/lookahead-declaration/preview-columns",
                     json={"columns": ["close", "volume"], "timeframes": ["1h"]})
    assert r0.status_code == 200 and r0.json()["default_window_bars"] == {"1h": 0}
    assert r0.json()["requires_declaration"] is True


def test_gap3_declaration_mandatory_preview_columns_uses_single_impl(monkeypatch):
    """兩端 preview 之唯一實作＝`lookahead_declaration.preview_from_columns`（換掉它 ⇒ 兩端回傳同時改變）。"""
    real = decl_mod.preview_from_columns
    calls: List[Dict[str, Any]] = []

    def probe(data_columns, timeframes, **kw):
        out = real(data_columns, timeframes, **kw)
        calls.append({"cols": sorted(map(str, data_columns)), "tfs": sorted(map(str, timeframes))})
        out = dict(out)
        out["default_window_bars"] = {tf: 99 for tf in out["default_window_bars"]}
        return out

    monkeypatch.setattr(decl_mod, "preview_from_columns", probe)
    r = client.post(f"{API}/case/lookahead-declaration/preview-columns",
                    json={"columns": ["future_4bar_return"], "timeframes": ["12h"]})
    assert r.status_code == 200 and r.json()["default_window_bars"] == {"12h": 99}
    recs = _records(lookahead_bars_declared=None)
    p = client.post(f"{API}/case/import-events/lookahead-declaration",
                    files={"file": ("events.csv", _to_csv(recs), "text/csv")})
    assert p.status_code == 200 and p.json()["default_window_bars"] == {"12h": 99}
    assert len(calls) == 2 and calls[0]["tfs"] == ["12h"] and calls[1]["tfs"] == ["12h"]


def test_gap3_declaration_mandatory_acknowledgement_flag_matches_backend_rejection():
    """「須勾選」之判定兩端同一函式：preview 說要勾 ⇔ 後端未勾即拒（含 referenced 為空之非 canonical filters 分支）。"""
    import io
    base = make_event(0, lookahead_bars_declared=None)
    fields = ("decision_offset_bars", "entry_price_semantic", "direction", "scenario",
              "label_definition", "control_kind", "source_file_digest", "data_snapshot_digest")
    plain = {k: base[k] for k in fields}
    opaque = dict(plain, label_definition={**dict(plain["label_definition"]), "filters": {"expr": "row['x'] >= 1"}})
    header = "eid,sym,tf,ts,ans"
    from momentum.Analysis.event_samples.import_contract import canonical_event_id
    rows = [f"{canonical_event_id('ETHUSDT', '12h', base['t0'] + i * 43200000)},ETHUSDT,12h,{base['t0'] + i * 43200000},{i % 2}"
            for i in range(2)]
    csv = (header + "\n" + "\n".join(rows) + "\n").encode("utf-8")
    mapping = {"event_id": "eid", "symbol": "sym", "timeframe": "tf", "t0": "ts", "label": "ans"}

    def preview(defaults):
        return client.post(f"{API}/case/import-events/lookahead-declaration",
                           files={"file": ("m.csv", io.BytesIO(csv), "text/csv")},
                           data={"column_mapping": json.dumps(mapping), "batch_defaults": json.dumps(defaults)}).json()

    def upload(defaults, ack):
        return client.post(f"{API}/case/import-events/csv",
                           files={"file": ("m.csv", io.BytesIO(csv), "text/csv")},
                           data={"column_mapping": json.dumps(mapping), "batch_defaults": json.dumps(defaults),
                                 "lookahead_declaration": json.dumps({"declared_window_bars": {"12h": 2},
                                                                      "acknowledged_unverifiable": ack})})

    p_plain, p_opaque = preview(plain), preview(opaque)
    assert p_plain["requires_declaration"] is True and p_opaque["requires_declaration"] is True
    assert p_plain["acknowledgement_required"] is False
    assert p_opaque["acknowledgement_required"] is True and p_opaque["referenced_columns"] == []
    # 不勾：plain 收、opaque 拒（與 preview 旗標一致）
    assert upload(plain, False).status_code == 200
    r = upload(opaque, False)
    assert r.status_code in (400, 422) and r.json()["detail"]["kind"] == "lookahead_declaration_unacknowledged_unverifiable"
    assert upload(opaque, True).status_code == 200


def test_gap3_declaration_mandatory_retired_depth_endpoint_is_gone():
    """Phase 2 退役：`/case/lookahead-depth` 不再存在（深度不由篩選條件導出）。"""
    r = client.post(f"{API}/case/lookahead-depth",
                    json={"referenced_columns": [], "declared_window_bars": {"1h": 0}, "timeframes": ["1h"]})
    assert r.status_code in (404, 405), r.status_code
    assert not hasattr(svc_mod.EventImportService, "lookahead_depth")
