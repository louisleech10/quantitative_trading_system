"""GAP-3 UX Task 3.1 驗證（-k gap3_event_delete）：`DELETE /api/v1/case/events/{import_id}`。

涵蓋 TODO Task 3.1 之兩條邊界：
- 邊界①：刪後 `GET` status_code `== 404`。
- 邊界②：該 `import_id` 之**所有落檔路徑殘留檔數 `== 0`**
  （🔴 僅驗 404 偵測不到磁碟殘留——端點回 404 但 receipt 仍在）。

另釘住三件 TODO 明列之「不可做／須同步」：不提供「刪除全部」端點；不連帶刪 kline 快取；
刪除範圍隨 Phase 1／2 新增之產物**同步擴張**。
"""

from __future__ import annotations

import json
from pathlib import Path

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


def _import_batch(n: int = 2, source_name: str = "unit") -> str:
    r = client.post(
        "/api/v1/case/import-events/json",
        json={"records": [make_event(i, label=i % 2) for i in range(n)], "source_name": source_name},
    )
    assert r.status_code == 200, r.text
    import_id = r.json()["import_id"]
    assert import_id
    return import_id


def _residue(storage_dir: Path, import_id: str) -> list[str]:
    """該 `import_id` 在磁碟上的**全部**殘留（檔與目錄）。

    🔴 以 `rglob(f"*{import_id}*")` 掃**整棵**儲存樹，不是只問那一個已知檔名——
    「殘留檔數 == 0」若只問已知檔名，日後新增的產物一律漏檢（假綠）。
    """
    if not storage_dir.is_dir():
        return []
    return sorted(str(p.relative_to(storage_dir)) for p in storage_dir.rglob(f"*{import_id}*"))


# ---------------------------------------------------------------- 邊界①


def test_gap3_event_delete_then_get_returns_404(_isolated_storage):
    """邊界①：刪除回 204，其後 `GET` 該批 status_code `== 404`，且不再列於清單。"""
    import_id = _import_batch()
    assert client.get(f"/api/v1/case/events/{import_id}").status_code == 200

    resp = client.delete(f"/api/v1/case/events/{import_id}")
    assert resp.status_code == 204, resp.text

    assert client.get(f"/api/v1/case/events/{import_id}").status_code == 404
    assert client.get("/api/v1/case/events").json()["total"] == 0


# ---------------------------------------------------------------- 邊界②


def test_gap3_event_delete_leaves_zero_residue_on_disk(_isolated_storage):
    """邊界②：磁碟殘留檔數 `== 0`。

    🔴 先斷言刪除**前**殘留 > 0——否則本測試在「批根本沒落檔」時也會綠（空集合對空集合）。
    """
    import_id = _import_batch()
    storage_dir = _isolated_storage.storage_dir
    before = _residue(storage_dir, import_id)
    assert len(before) > 0, "前置失敗：批未落檔，邊界②之比較會退化為空集對空集"

    assert client.delete(f"/api/v1/case/events/{import_id}").status_code == 204
    assert _residue(storage_dir, import_id) == []


def test_gap3_event_delete_scope_expands_with_phase1_and_phase2_artifacts(_isolated_storage):
    """🔴 TODO Task 3.1「須同步」：刪除範圍須隨 Phase 1／2 新增之產物**同步擴張**。

    現況下 Phase 1 之 receipt（`mapping_provenance`／`lookahead_declaration`）與 Phase 2 之
    `filters` 都住在事件檔**同一個 payload 內**（故自動涵蓋）。本測試種下**未來形狀**的兩種
    per-batch 產物——拆出去的檔與 per-batch 目錄——證明刪除端是以枚舉涵蓋，
    不是寫死單一檔名；日後有人把 receipt 拆出去也不會產生孤兒檔。
    """
    import_id = _import_batch()
    storage_dir = _isolated_storage.storage_dir

    # 未來形狀 A：拆出去的 per-batch receipt 檔
    (storage_dir / f"{import_id}.receipt.json").write_text('{"mapping_provenance": {}}', encoding="utf-8")
    # 未來形狀 B：per-batch artifact 目錄（含巢狀檔）
    artifact_dir = storage_dir / import_id
    (artifact_dir / "nested").mkdir(parents=True)
    (artifact_dir / "nested" / "filters.json").write_text("{}", encoding="utf-8")

    assert len(_residue(storage_dir, import_id)) >= 3

    assert client.delete(f"/api/v1/case/events/{import_id}").status_code == 204
    assert _residue(storage_dir, import_id) == []


def test_gap3_event_delete_removes_stored_phase1_receipt_from_payload(_isolated_storage):
    """釘住「receipt 確實在刪除範圍內」：刪除前 payload 內讀得到 Phase 1 之 receipt，刪除後整份不存在。

    3.3 之警語正確性依賴此條（TODO：若 3.1 未涵蓋全部產物，警語與實況不符）。
    """
    import_id = _import_batch()
    payload_path = _isolated_storage.payload_path(import_id)
    assert payload_path is not None and payload_path.is_file()
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert "lookahead_declaration" in payload, "前置失敗：Phase 1 之 receipt 不在 payload 內，本測試失去意義"

    assert client.delete(f"/api/v1/case/events/{import_id}").status_code == 204
    assert not payload_path.exists()


# ---------------------------------------------------------------- 404 / 不可做 / 邊界


def test_gap3_event_delete_unknown_id_returns_404_not_500(_isolated_storage):
    """不存在之 `import_id` ⇒ 404（**非 500**）。"""
    assert client.delete("/api/v1/case/events/nope").status_code == 404
    assert client.delete("/api/v1/case/events/does-not-exist-at-all").status_code == 404


def test_gap3_event_delete_path_traversal_guard_is_at_service_layer(_isolated_storage):
    """路徑穿越防護（與 `get_import` **共用之同一條**）——在**服務層**直接驗。

    🔴 為何不只走 HTTP：ASGI／httpx 會在路由**之前**正規化 `..%2F` 之類的路徑，
    請求根本到不了防護，那樣的斷言是恆綠的假綠（§4.2「錨點放在無測試涵蓋之處」）。
    真正的決策點是 `payload_path()`，故直接對它下斷言。
    """
    svc = _isolated_storage
    outsider = svc.storage_dir.parent / "outside.json"
    outsider.parent.mkdir(parents=True, exist_ok=True)
    outsider.write_text("{}", encoding="utf-8")

    for bad in ("../outside", "..", "a/b", "..\\outside", "sub\\dir", ""):
        assert svc.payload_path(bad) is None, f"路徑穿越形狀未被擋：{bad!r}"
        assert svc.delete_import(bad) is False, f"路徑穿越形狀之刪除未被拒：{bad!r}"
        assert svc.get_import(bad) is None, f"路徑穿越形狀之讀取未被拒：{bad!r}"

    assert outsider.is_file(), "路徑穿越：動到了儲存區之外的檔"


def test_gap3_event_delete_no_delete_all_endpoint_for_events(_isolated_storage):
    """**不可做**：不得提供事件批之「刪除全部」端點。

    以 router 之實際方法表判定（執行期路由狀態，非原始碼字面），並以真實請求複驗。
    """
    delete_paths = {
        r.path for r in app.routes
        if getattr(r, "methods", None) and "DELETE" in r.methods and "/case/events" in r.path
    }
    assert delete_paths == {"/api/v1/case/events/{import_id}"}, f"出現非預期之事件批 DELETE 端點：{delete_paths}"
    assert client.delete("/api/v1/case/events").status_code in (404, 405)


def test_gap3_event_delete_only_targets_that_batch(_isolated_storage):
    """邊界：只刪該批——同儲存區之另一批完好，kline 快取路徑不受影響。"""
    keep_id = _import_batch(source_name="keep")
    drop_id = _import_batch(source_name="drop")
    assert keep_id != drop_id
    storage_dir = _isolated_storage.storage_dir

    # 種一個「非事件批」之相鄰產物，代表 kline 快取／Feature Library 之落點不得被連帶刪除
    kline_like = storage_dir.parent / "kline_cache.h5"
    kline_like.write_bytes(b"\x89HDF\r\n\x1a\n")

    assert client.delete(f"/api/v1/case/events/{drop_id}").status_code == 204

    assert _residue(storage_dir, drop_id) == []
    assert len(_residue(storage_dir, keep_id)) > 0
    assert client.get(f"/api/v1/case/events/{keep_id}").status_code == 200
    assert client.get("/api/v1/case/events").json()["total"] == 1
    assert kline_like.is_file(), "不得連帶刪除 kline 快取"


def test_gap3_event_delete_is_not_idempotent_second_call_is_404(_isolated_storage):
    """重複刪除 ⇒ 第二次 404（而非 204 假成功，亦非 500）。"""
    import_id = _import_batch()
    assert client.delete(f"/api/v1/case/events/{import_id}").status_code == 204
    assert client.delete(f"/api/v1/case/events/{import_id}").status_code == 404
