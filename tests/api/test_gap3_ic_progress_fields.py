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
from momentum.FeatureEngineering.feature_naming import stamp_h5_feature_naming_version as _stamp_ic_handoff  # FF-NAME 3.4 v18

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


def test_gap3_ic_progress_fields_populated_for_implicit_latest_and_full_analysis():
    """🔴 `CODEX-R4-P2-01`：`feature_count` 原本只在「顯式帶 hash 的 `/analyze`」才有值
    ⇒ **隱式 latest 與所有 `/full-analysis`** 一律回 `None`，欄位在最常見的兩種用法下是空的。

    根因是解析器只認 `config_hash`；結構修正後改用
    `ICAnalysisService.resolve_planned_feature_count`——與止血閘、與實際載入路徑同一支。
    另 `/full-analysis` 之 `task_info` 原本**根本沒有這個鍵**，一併補上。
    """
    from api.services.ic_analysis_service import ic_analysis_service

    class _Implicit:
        mode = "longitudinal"
        symbol = "BTCUSDT"
        timeframe = "12h"
        config_hash = None          # 不指定 ⇒ service 會挑 latest
        features_path = None
        symbols = None
        cross_sectional_runs = None

    got = svc_mod._resolve_feature_count(_Implicit())
    assert isinstance(got, int), "隱式 latest 的任務仍回 None ⇒ Task 6.3 的欄位是空的"
    assert got == ic_analysis_service.resolve_planned_feature_count(_Implicit()), \
        "進度欄位與止血閘用的不是同一支解析 ⇒ 兩者會再次不同步"

    # `/full-analysis` 之 task_info 必須含此鍵（缺鍵與值為 None 是兩件事）
    import inspect
    source = inspect.getsource(svc_mod.ICAnalysisService.start_full_analysis)
    assert '"feature_count"' in source, "/full-analysis 的 task_info 沒有 feature_count 鍵"


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
    # 🔴 `CODEX-R1-P1-02`：同一個 `config_hash` 在真實 registry 裡**會對到多個標的**
    #    （實查 `4a8a0b37…` 對到 BTCUSDT/ETHUSDT/BCHUSDT，feature_count 各為 437066/437110/437210）。
    #    只比對 hash 並取第一筆 ⇒ 閘門會拿**別的標的**的數字去守。以下逐一釘住：
    from collections import Counter

    hash_counts = Counter(e["config_hash"] for e in with_count)
    unique = [e for e in with_count if hash_counts[e["config_hash"]] == 1]
    ambiguous = [e for e in with_count if hash_counts[e["config_hash"]] > 1]

    # ① 帶 symbol＋timeframe ⇒ 精準解析（含歧義 hash）
    for entry in (unique[:1] + ambiguous[:1]):
        assert resolve_run_feature_count(
            config_hash=entry["config_hash"],
            symbol=entry["symbol"], timeframe=entry["timeframe"],
        ) == entry["feature_count"], f"{entry['symbol']}/{entry['timeframe']} 解析錯誤"

    # ② 歧義 hash 只給 hash ⇒ **不猜**，回 None
    if ambiguous:
        assert resolve_run_feature_count(config_hash=ambiguous[0]["config_hash"]) is None, (
            "同一 hash 對到多個標的時仍回了一個值 ⇒ 閘門會拿別的 run 的數字去守")

    # ③ 只給 symbol/timeframe（無 hash）⇒ 一律 None，不猜
    assert resolve_run_feature_count(
        symbol=with_count[0].get("symbol"), timeframe=with_count[0].get("timeframe")) is None


def test_gap3_ic_progress_fields_hermetic_implicit_latest_and_full_analysis_task_info(tmp_path, monkeypatch):
    """密閉版：受控 registry 注入＋真打 `/full-analysis` 後讀 task 回應之 `feature_count`。

    隱式 latest：注入同一 symbol/12h 三筆——較舊已物化（9000）、較新已物化（4321）、
    最新但 manifest 不存在（50000，孤兒須跳過）⇒ 期望＝4321（由本測試寫入之 manifest 決定）。
    `/full-analysis`：features 檔之 `features` 資料集寬 77 欄 ⇒ 經 `response_model` 後之
    task 回應 `feature_count` 須為 77（只看原始碼字面不足以證明鍵有值）。
    """
    import h5py as _h5py_pf
    import json as _json_pf

    service = svc_mod.ic_analysis_service
    registry = service._feature_library._registry  # noqa: SLF001
    original_entries = list(registry._entries)  # noqa: SLF001
    original_path = registry._path  # noqa: SLF001
    staged = tmp_path / "registry.json"
    started_ids = []

    def _manifest(name, total):
        p = tmp_path / name / "feature_manifest.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_json_pf.dumps({"total_features": total}), encoding="utf-8")
        return str(p)

    rows = [
        {"symbol": "ICPROGHERM", "timeframe": "12h", "config_hash": "progherm01",
         "feature_count": 9000, "hdf5_relative_path": _manifest("old", 9000),
         "last_generated_at": 1_900_000_001},
        {"symbol": "ICPROGHERM", "timeframe": "12h", "config_hash": "progherm02",
         "feature_count": 4321, "hdf5_relative_path": _manifest("new", 4321),
         "last_generated_at": 1_900_000_002},
        {"symbol": "ICPROGHERM", "timeframe": "12h", "config_hash": "progherm03",
         "feature_count": 50000, "hdf5_relative_path": str(tmp_path / "gone" / "feature_manifest.json"),
         "last_generated_at": 1_900_000_003},
    ]
    staged.write_text(_json_pf.dumps(original_entries + rows), encoding="utf-8")
    registry._path = staged  # noqa: SLF001

    features_h5 = tmp_path / "features.h5"
    with _h5py_pf.File(str(features_h5), "w") as handle:
        _stamp_ic_handoff(handle.attrs)  # FF-NAME Task 3.4（v18）：IC 交接 h5 根屬性，同正式寫出端之函式
        handle.create_dataset("features", data=[[0.0] * 77] * 3)
    monkeypatch.setattr(service, "_start_background_coroutine", lambda factory: None)

    class _ImplicitHermetic:
        mode = "longitudinal"
        symbol = "ICPROGHERM"
        timeframe = "12h"
        config_hash = None
        features_path = None
        symbols = None
        cross_sectional_runs = None

    try:
        got = svc_mod._resolve_feature_count(_ImplicitHermetic())
        planned = svc_mod.ICAnalysisService.resolve_planned_feature_count(service, _ImplicitHermetic())
        assert got == 4321 and planned == 4321, f"隱式 latest 解析錯：got={got} planned={planned}"

        r = client.post(f"{API}/full-analysis", json={
            "features_path": str(features_h5), "labels_path": str(tmp_path / "labels.h5"),
            "symbol": "ICPROGHERM", "timeframe": "12h",
        })
        task_id = (r.json() or {}).get("task_id") if r.status_code == 200 else None
        started_ids.append(task_id)
        body = client.get(f"{API}/task/{task_id}").json() if task_id else {}
        assert r.status_code == 200 and body.get("feature_count") == 77, \
            f"/full-analysis 任務回應之 feature_count 錯：{r.status_code} {r.text} {body}"
    finally:
        registry._path = original_path  # noqa: SLF001
        registry._entries = original_entries  # noqa: SLF001
        with service._lock:  # noqa: SLF001
            for tid in started_ids:
                service._tasks.pop(tid, None)
