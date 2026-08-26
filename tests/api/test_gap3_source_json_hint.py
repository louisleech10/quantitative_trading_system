"""GAP-3 UX Task 5.1 驗收（`-k source_json_hint`）——`.source.json` 誤傳之訊息追加正解。

邊界①：status_code `== 400` 且訊息含 `source_file`。
邊界②：誤送到 **CSV 端點**（副檔名非 `.csv`）⇒ **同一則**正解提示。

鑑別力（防「恆顯示」）：非來源檔之拒收**不得**出現該提示——否則邊界①永遠綠，等於沒驗。
不可做：判別為來源檔**不得**自動改走 `source_file` 流程（落檔數須為 0，reason 字面不變）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import case_import_service as svc_mod
from momentum.factories import create_event_sample_pipeline
from tests.momentum.event_samples.test_import_contract import canonical_event as make_event

client = TestClient(app)
API = "/api/v1"


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    svc = svc_mod.EventImportService(storage_dir=tmp_path / "events")
    monkeypatch.setattr(svc_mod, "_event_import_service", svc)
    return svc


def _source_json_bytes() -> bytes:
    """真的走 `/search` 那條產生路徑：`CaseData.model_dump` → canonical_source_payload。

    🔴 不手寫一份「看起來像」的 JSON——手寫的形狀會與實際匯出檔漂移，
    那樣測到的是我以為的形狀，不是使用者手上真的那個檔。
    """
    from api.models.responses import CaseData

    cases = [
        CaseData(symbol="ETHUSDT", timestamp="2024-01-01T00:00:00Z", trigger_idx=10, open=1.0, high=2.0,
                 low=0.5, close=1.5, volume=100.0, price_change=3.2, market_phase="up",
                 positive_case=True, timeframe="12h"),
        CaseData(symbol="ETHUSDT", timestamp="2024-01-02T00:00:00Z", trigger_idx=11, open=1.5, high=2.5,
                 low=1.0, close=2.0, volume=120.0, price_change=-1.0, market_phase="down",
                 positive_case=False, timeframe="12h"),
    ]
    text, _digest = create_event_sample_pipeline().canonical_source_payload(
        [c.model_dump(mode="json") for c in cases])
    return text.encode("utf-8")


def _legacy_csv_bytes() -> bytes:
    """舊三欄格式：同樣走 `legacy_schema_detected`，但**不是**來源對證檔。"""
    return b"symbol,timestamp,Positive_case\nETHUSDT,1704067200,1\n"


def test_gap3_source_json_hint_on_event_upload_endpoint(_isolated_storage):
    """邊界①：來源對證檔誤傳事件檔欄 ⇒ 400 且訊息含 `source_file`；reason 字面不變、不落檔。"""
    r = client.post(f"{API}/case/import-events",
                    files={"file": ("gap3_events.source.json", _source_json_bytes(), "application/json")})
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert "source_file" in detail["message"], detail["message"]
    assert "verify_source_digest" in detail["message"], detail["message"]
    # reason 字面不變（下游依 kind 判斷；只准在訊息尾端追加）
    assert detail["kind"] == "legacy_schema_detected"
    # 靜默轉換之禁令：不得因判別為來源檔就改走 source_file 流程 ⇒ 一筆都不准落檔
    assert client.get(f"{API}/case/events").json()["total"] == 0


def test_gap3_source_json_hint_on_csv_endpoint(_isolated_storage):
    """邊界②：同一份檔誤送 CSV 對映端點 ⇒ **同一則**正解提示（新路徑不得比舊路徑更難排除）。

    🔴 狀態碼在此為 **422**，不是邊界①的 400：CSV 端點自己的拒收理由是對映欄找不到
    （`contract_violation`），而 Task 5.1 之邊界是「**只追加提示**」——改狀態碼會動到
    與本 Task 無關之既有行為。故本條驗的是**提示到得了新路徑**，狀態碼原樣釘住防它被順手改掉。
    """
    r = client.post(f"{API}/case/import-events/csv",
                    files={"file": ("gap3_events.source.json", _source_json_bytes(), "application/json")},
                    data={"column_mapping": json.dumps({"event_id": "event_id", "t0": "timestamp", "label": "positive_case"})})
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert "source_file" in detail["message"] and "verify_source_digest" in detail["message"], detail["message"]
    assert detail["kind"] == "contract_violation"          # reason 字面不變
    assert client.get(f"{API}/case/events").json()["total"] == 0


def test_gap3_source_json_hint_two_endpoints_share_one_literal(_isolated_storage):
    """兩條路徑之提示字面**逐字相同**（各自寫一份必然漂移；V-3 之教訓）。"""
    src = _source_json_bytes()
    a = client.post(f"{API}/case/import-events",
                    files={"file": ("a.source.json", src, "application/json")}).json()["detail"]["message"]
    b = client.post(f"{API}/case/import-events/csv",
                    files={"file": ("b.source.json", src, "application/json")},
                    data={"column_mapping": json.dumps({"event_id": "event_id", "t0": "timestamp", "label": "positive_case"})},
                    ).json()["detail"]["message"]
    hint = create_event_sample_pipeline().source_file_misupload_hint(src)
    assert hint and a.endswith(hint) and b.endswith(hint), (a, b, hint)


def test_gap3_source_json_hint_not_shown_for_legacy_three_column_file(_isolated_storage):
    """鑑別力：舊三欄檔同樣 400／同一 kind，但**不得**出現來源檔提示（它的正解是改 schema）。

    🔴 本條擋的是「不是 JSON 就不該命中」；**標記鍵的鬆緊由下一條擋**——
    兩者是不同的破口，用同一個 CSV fixture 會漏掉後者（`5.1-M2` 實跑證實：
    放寬成三鍵時本條仍綠，因為 CSV 在 `json.loads` 就先失敗了）。
    """
    r = client.post(f"{API}/case/import-events",
                    files={"file": ("old.csv", _legacy_csv_bytes(), "text/csv")})
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert detail["kind"] == "legacy_schema_detected"
    assert "verify_source_digest" not in detail["message"], detail["message"]


def test_gap3_source_json_hint_not_shown_for_legacy_json_file(_isolated_storage):
    """鑑別力（標記鍵之鬆緊）：**JSON 格式**的舊三欄檔不得被當成來源對證檔。

    它只有 `symbol`／`timestamp`／`positive_case`，缺 `timeframe`／`price_change`
    ⇒ 五鍵判準不命中。把判準放寬到三鍵（`5.1-M2`）時本條**須紅**：
    使用者會拿到「請改放到 source_file 欄」這個對他毫無用處的正解，而真正的正解是改 schema。
    """
    # 🔴 三個標記鍵之值**刻意都用合法型別**（`timestamp` 為字串、`positive_case` 為 bool）：
    #    若寫成 `1704067200`／`1` 這種型別不合的值，擋下它的會是**型別驗證**而不是鍵數判準，
    #    本條就變成在驗別的東西——mutation `5.1-M2`（放寬成三鍵）實跑證實了這一點。
    legacy_json = json.dumps(
        [{"symbol": "ETHUSDT", "timestamp": "2024-01-01T00:00:00Z", "positive_case": True},
         {"symbol": "ETHUSDT", "timestamp": "2024-01-02T00:00:00Z", "positive_case": False}],
        ensure_ascii=False,
    ).encode("utf-8")
    r = client.post(f"{API}/case/import-events",
                    files={"file": ("old.json", legacy_json, "application/json")})
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert detail["kind"] == "legacy_schema_detected"      # 走的是同一條拒收路徑
    assert "verify_source_digest" not in detail["message"], detail["message"]
    assert "source_file" not in detail["message"], detail["message"]


def test_gap3_source_json_hint_not_shown_for_contract_violation(_isolated_storage):
    """鑑別力②：新 schema 但契約違規 ⇒ 422，訊息不得被塞進來源檔提示。"""
    bad = [make_event(0, t0=1704067, label=1)]
    r = client.post(f"{API}/case/import-events/json", json={"records": bad})
    assert r.status_code == 422, r.text
    assert "verify_source_digest" not in r.json()["detail"]["message"]


def test_gap3_source_json_hint_not_shown_for_new_schema_with_leftover_columns(_isolated_storage):
    """鑑別力③：**合法新 schema 事件檔**殘留 `/search` 的三個欄，不得被貼上來源檔正解。

    使用者從 `/search` 另存再手改成事件檔時，很容易留著 `timestamp`／`positive_case`／
    `price_change`。那時他該做的是**移掉非契約欄**；若給他「請改放到 source_file 欄」，
    是把他往完全錯的方向推——給錯正解比不給更糟。
    排除判準＝該列帶 `event_id`（來源對證檔結構上沒有這個欄）。
    """
    row = dict(make_event(0, label=1))
    row.update({"timestamp": "2024-01-01T00:00:00Z", "positive_case": True, "price_change": 3.2})
    r = client.post(f"{API}/case/import-events",
                    files={"file": ("ev.json", json.dumps([row]).encode("utf-8"), "application/json")})
    assert r.status_code == 422, r.text            # 非契約欄 ⇒ 契約違規（而非 legacy）
    assert "verify_source_digest" not in r.json()["detail"]["message"]


def test_gap3_source_json_hint_detector_shape_only(_isolated_storage):
    """判別函式只看形狀：五個標記鍵**逐列**都要有；缺一鍵或非陣列即不命中。"""
    pipeline = create_event_sample_pipeline()
    src = json.loads(_source_json_bytes().decode("utf-8"))
    assert pipeline.source_file_misupload_hint(json.dumps(src).encode("utf-8"))

    missing_one_key = [{k: v for k, v in row.items() if k != "price_change"} for row in src]
    assert pipeline.source_file_misupload_hint(json.dumps(missing_one_key).encode("utf-8")) is None

    only_first_row_ok = [src[0], {k: v for k, v in src[1].items() if k != "timeframe"}]
    assert pipeline.source_file_misupload_hint(json.dumps(only_first_row_ok).encode("utf-8")) is None

    assert pipeline.source_file_misupload_hint(b"not json at all") is None
    assert pipeline.source_file_misupload_hint(b"[]") is None
    assert pipeline.source_file_misupload_hint(json.dumps({"records": src}).encode("utf-8")) is None


def test_gap3_source_json_hint_rejects_wrong_marker_types(_isolated_storage):
    """鑑別力④：五鍵齊但**型別明顯不對**之畸形 JSON 不得被判為來源對證檔。

    反例（`CODEX-R3-P2-04`）：只看鍵在不在時，`symbol` 是 dict、`price_change` 是 list、
    甚至五鍵全 null 的 payload 都會命中 ⇒ 使用者收到一個對他毫無用處的正解。
    型別取自 `CaseData` 之序列化形態。
    """
    pipeline = create_event_sample_pipeline()
    good = json.loads(_source_json_bytes().decode("utf-8"))
    assert pipeline.source_file_misupload_hint(json.dumps(good).encode())      # 正向對照

    malformed = [
        ("型別全錯", [{"symbol": {"x": 1}, "timeframe": [1, 2], "timestamp": None,
                       "positive_case": "yes", "price_change": ["a"]}]),
        ("五鍵全 null", [{"symbol": None, "timeframe": None, "timestamp": None,
                          "positive_case": None, "price_change": None}]),
        ("symbol 空字串", [{**good[0], "symbol": ""}]),
        ("positive_case 用 0/1 而非 bool", [{**good[0], "positive_case": 1}]),
        ("price_change 是字串", [{**good[0], "price_change": "3.2"}]),
    ]
    for label, rows in malformed:
        assert pipeline.source_file_misupload_hint(json.dumps(rows).encode()) is None, label

    # 只有一列壞掉也不得命中（逐列驗，非只看第一列）
    mixed = [good[0], {**good[1], "price_change": "3.2"}]
    assert pipeline.source_file_misupload_hint(json.dumps(mixed).encode()) is None


def test_gap3_source_json_hint_literal_lives_in_contract_module():
    """提示字面之唯一實作在 momentum；api 層（route／service）不得複列**那個字串**。

    🔴 錨點＝**提示字串本身**，不是「來源對證」這種字樣——後者會被自己的註解與 docstring 命中
    （本 epic 之 §6.1 第 6 條：掃整段原始碼文字會讓斷言誤紅）。
    """
    hint = create_event_sample_pipeline().source_file_misupload_hint(_source_json_bytes())
    assert isinstance(hint, str) and hint            # 正向對照：真的取得到那個字面
    repo = Path(__file__).resolve().parents[2]
    for rel in ("api/routes/case.py", "api/services/case_import_service.py"):
        text = (repo / rel).read_text(encoding="utf-8")
        assert hint not in text, f"{rel} 複列了提示字面"
