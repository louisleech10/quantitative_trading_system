"""GAP-3 UX Task 6.3 驗收（`-k ic_progress_fields`）——進度回報帶 `feature_count`。

邊界①：progress response 含 `feature_count` 鍵。
🔴 必須驗**經過 `response_model` 之後**的回應：service 塞了值而 pydantic 沒宣告時會被
   **靜默濾掉**、前端永遠看不到（本 epic §4.2 之假綠實例第 5 條）。故本檔打真的端點。

🔴 `current_stage` 為**可擴充集合**：本檔**刻意不**以固定 enum 窮舉相等斷言鎖死
   （GAP-6 會細分更多階段；改測試是掩蓋行為變更的常見路徑）。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import ic_analysis_service as svc_mod
from momentum.factories import resolve_run_feature_count

client = TestClient(app)
API = "/api/v1/ic"


@pytest.fixture()
def injected_task():
    """直接把一筆 task 放進 store 再打端點——不真的跑 IC 分析（那是十分鐘級且與本 Task 無關）。

    要驗的是**回應形狀**有沒有被 `response_model` 濾掉，跑不跑分析不影響該判準。
    """
    service = svc_mod.ic_analysis_service
    task_id = "gap3-progress-fixture"
    with service._lock:  # noqa: SLF001 — 測試刻意走 store，見 docstring
        service._tasks[task_id] = {
            "task_id": task_id, "status": "running", "progress": 0.42,
            "current_stage": "loading_features", "current_step": None,
            "applied_tier": "intermediate", "error": None, "result": None,
            "feature_count": 218369,
        }
    yield task_id
    with service._lock:  # noqa: SLF001
        service._tasks.pop(task_id, None)


def test_gap3_ic_progress_fields_exposes_feature_count(injected_task):
    """邊界①：端點回應（過 `response_model` 之後）含 `feature_count` 且值正確。"""
    r = client.get(f"{API}/task/{injected_task}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "feature_count" in body, f"response_model 把它濾掉了：{sorted(body)}"
    assert body["feature_count"] == 218369


def test_gap3_ic_progress_fields_stage_set_is_open_not_fixed_enum(injected_task):
    """🔴 階段字串為**可擴充集合**：只斷言「有值且為字串」，不窮舉。

    本條的存在本身就是那條設計約束的載體——若日後有人把它改成固定 enum 相等斷言，
    會與這裡的註解直接矛盾。
    """
    body = client.get(f"{API}/task/{injected_task}").json()
    assert isinstance(body.get("current_stage"), str) and body["current_stage"]


def test_gap3_ic_progress_fields_no_fake_value_when_unresolvable():
    """不可做：**不得以固定假值填充**。

    解析不出來時 `feature_count` 須為 `None`——UAT 已證實填充值比沒有更誤導
    （`progress==0.12` 卡 15 分鐘，使用者以為還在動）。
    """
    assert resolve_run_feature_count(config_hash="no-such-hash") is None
    assert resolve_run_feature_count(config_hash=None) is None

    # 🔴 **service 端的 helper 也要驗**：上面兩條驗的是 momentum 那支函式，
    #    而任務裡實際填值的是 `ic_analysis_service._resolve_feature_count`。
    #    只驗前者時，把後者改成「解析不到就填 0」不會被察覺（mutation `6.3-M2` 實測）。
    class _Req:
        config_hash = "no-such-hash-at-all"
        symbol = "BTCUSDT"
        timeframe = "12h"

    assert svc_mod._resolve_feature_count(_Req()) is None, "解析不到卻填了假值"


def test_gap3_ic_progress_fields_resolver_reads_registry_only():
    """🔴 解析器只讀 registry、**不開 HDF5**——Task 6.4 要證明「擋下時未載入大矩陣」。

    正向對照：真實 registry 內的 `config_hash` 解析得出數字（否則本條退化成恆真）。
    🔴 且**不得**以 (symbol, timeframe) 猜：`find_latest` 會取到**別的 run**
    （實測 BTCUSDT/12h 最新一筆是 15 個特徵，而同組合下另有 218,369 的 run）。
    """
    import json as _json
    from pathlib import Path as _Path

    registry = _json.loads(
        (_Path(__file__).resolve().parents[2] / "data_cache" / "features" / "registry.json")
        .read_text(encoding="utf-8"))
    with_count = [e for e in registry if isinstance(e.get("feature_count"), int) and e.get("config_hash")]
    if not with_count:
        pytest.skip("本機 registry 無帶 feature_count 之登記，無法做正向對照")
    entry = with_count[0]
    assert resolve_run_feature_count(config_hash=entry["config_hash"]) == entry["feature_count"]
    # 只給 symbol/timeframe（無 hash）⇒ 一律 None，不猜
    assert resolve_run_feature_count(symbol=entry.get("symbol"), timeframe=entry.get("timeframe")) is None
