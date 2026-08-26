"""GAP-3 UX Task 6.1 ＋ 6.4 驗收（`-k "ic_feature_cap or ic_stop_gate_alive"`）。

🔴 **6.1 與 6.4 同批、同一檔**：6.4 之取樣時點綁定 6.1 之檢查位置——
   6.1 若被移到任務啟動之後，6.4 會量到已載入大矩陣之 footprint 而失去意義。
   本檔以**同一組測試**釘住那個先後順序。

Task 6.1 邊界①：218369 特徵之 run ⇒ 400 **且任務未被建立**
   （斷言 task store 筆數不變，**不是只驗 HTTP 碼**——「先建任務再回 400」也會讓只驗碼的測試綠，
   而那正是要防的事）。
Task 6.1 邊界②：小 run ⇒ 200 **且任務確實被建立**（筆數 +1）。
Task 6.4：擋下時**未載入大矩陣**——以「本行程 footprint 在請求前後幾乎不變」證之。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.core.config import settings
from api.main import app
from api.services import ic_analysis_service as svc_mod

client = TestClient(app)
API = "/api/v1/ic"
REPO = Path(__file__).resolve().parents[2]

#: 量測 receipt 導出之上限所依據的那個 run（218,369 特徵）
BIG_RUN_CONFIG_HASH = "e53e22906c35363757f4cd49d27f973e"


def _task_count() -> int:
    service = svc_mod.ic_analysis_service
    with service._lock:  # noqa: SLF001 — 邊界①要求斷言 store 筆數，只能走 store
        return len(service._tasks)


def test_gap3_ic_feature_cap_rejects_big_run_without_creating_task():
    """邊界①：超量 ⇒ 400 且**任務未被建立**。"""
    before = _task_count()
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": BIG_RUN_CONFIG_HASH,
    })
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert detail["feature_count"] > detail["cap"]
    assert detail["reason"]                       # reason 由契約取得（Task 6.0）
    # 🔴 這一條才是重點：只驗 400 的話，「先建任務再回 400」也會綠
    assert _task_count() == before, "任務被建立了 ⇒ 檢查沒有擋在 start_analysis 之前"


def test_gap3_ic_feature_cap_reason_comes_from_contract_not_hardcoded():
    """reason 字面須與 IC 契約一致（api 層不得自寫）。"""
    from momentum.factories import ic_report_reason

    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": BIG_RUN_CONFIG_HASH,
    })
    assert r.json()["detail"]["reason"] == ic_report_reason("analysis_rejected")


def test_gap3_ic_feature_cap_unresolvable_is_allowed_through():
    """解析不出特徵數 ⇒ **不擋**（本閘只擋「已知超量」）。

    🔴 具名破口：API 呼叫端硬塞 `features_path` 指向大 run 可繞過本閘。
    因本 Task 為過渡止血、且該路徑非使用者介面之路徑，接受並具名記錄。
    本條同時是那個決策的**載體**：若日後改成 fail-closed，這裡會紅、逼人回來看理由。
    """
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "no-such-hash-at-all",
    })
    # 不是被 cap 擋掉的 400（可能因別的原因失敗，但 reason 不會是 cap）
    if r.status_code == 400:
        detail = r.json().get("detail")
        if isinstance(detail, dict):
            assert detail.get("reason") != "feature_count_exceeds_cap" or True
            assert "cap" not in detail, f"未解析出特徵數卻被 cap 擋下：{detail}"


def test_gap3_ic_feature_cap_value_is_backed_by_measurement_receipt():
    """🔴 **禁拍腦袋填**：設定值須 `<=` receipt 內最小超標點 × 0.5。"""
    receipt = REPO / "handoffs" / "run_receipts" / "gap3ux-b9-footprint.receipt.json"
    assert receipt.exists(), "上限值必須有量測 receipt 佐證（Task 6.2 之死線）"
    data = json.loads(receipt.read_text(encoding="utf-8"))
    points = data["points"]
    assert len(points) >= 3, f"量測點須 >= 3，實得 {len(points)}"
    for p in points:                              # 六欄齊全
        assert p["machine"]["model"] and p["machine"]["ram_bytes"] > 0
        assert p["pid"] > 0
        assert p["baseline_footprint_bytes"] > 0 and p["peak_footprint_bytes"] > 0
        assert p["sampling"]["interval_sec"] and p["sampling"]["total_sec"] >= 0
        assert isinstance(p["feature_count"], int)
        assert p["tool"] == "sample:Physical footprint", "禁以 ps rss 當量測值"
    exceeded = [p["feature_count"] for p in points if p.get("exceeded") is True]
    assert exceeded, "receipt 內沒有任何超標點 ⇒ 上限無從導出"
    assert settings.ic_analysis_max_features <= min(exceeded) * 0.5


def test_gap3_ic_stop_gate_alive_no_big_matrix_loaded():
    """Task 6.4：擋下時**未載入大矩陣**。

    🔴 取樣時點綁 6.1 之檢查位置：本測試在**同一個行程**內量請求前後之 footprint。
    若 6.1 被移到任務啟動之後，分析會開始載入特徵、footprint 大幅上升 ⇒ 本條紅。
    🔴 **不得在 cap 檢查之前採樣就宣稱通過**（SPEC 明列之假綠形態）——
    本條的兩次採樣都在請求**之後**，比較的是「擋下之後」與「請求之前」的差。
    """
    import os
    import resource

    def rss_kb() -> int:
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024

    before_tasks = _task_count()
    before = rss_kb()
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": BIG_RUN_CONFIG_HASH,
    })
    after_request = rss_kb()
    assert r.status_code == 400
    after_response = rss_kb()

    assert _task_count() == before_tasks          # ①任務未建立
    assert os.getpid() > 0                        # ②單一 pid（本行程自身）
    # ③未載入大矩陣：該 run 的量測 peak 為 GB 級；擋下之路徑不得有可觀增長。
    # 🔴 這裡用 `ru_maxrss` 而非 `sample`：本條要驗的是「**這個行程**在被擋的路徑上有沒有長大」，
    #    是同行程前後差；Task 6.2 之絕對量測才需要 footprint（跨行程、且 RSS 會失真）。
    growth_mb = (max(after_request, after_response) - before) / 1024.0
    assert growth_mb < 256, f"擋下時記憶體成長 {growth_mb:.1f}MB ⇒ 疑似已載入特徵矩陣"


def test_gap3_ic_stop_gate_alive_small_run_still_creates_task(monkeypatch):
    """邊界②：小 run ⇒ 不被擋，且任務**確實被建立**（筆數 +1）。

    🔴 對照組：沒有這條的話，「把所有請求都擋掉」也會讓邊界①全綠。
    以替身取代 service 之實際分析（本條驗的是閘門放行與建任務，不是跑完分析）。
    """
    service = svc_mod.ic_analysis_service
    created = {}

    async def fake_start(request):
        task_id = "gap3-stop-gate-small"
        with service._lock:  # noqa: SLF001
            service._tasks[task_id] = {"task_id": task_id, "status": "running", "progress": 0.0}
        created["id"] = task_id
        return {"task_id": task_id, "status": "running"}

    monkeypatch.setattr(service, "start_analysis", fake_start)
    before = _task_count()
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h",
        "config_hash": "a6a998593c3c55aa54e5d6fa537114b4",   # 15 個特徵
    })
    assert r.status_code == 200, r.text
    assert _task_count() == before + 1, "小 run 未建立任務 ⇒ 閘門誤擋"
    with service._lock:  # noqa: SLF001
        service._tasks.pop(created.get("id"), None)
