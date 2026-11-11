"""GAP-3 UX Task 6.1 ＋ 6.4 驗收（`-k "ic_feature_cap or ic_stop_gate_alive"`）。

🔴 **6.1 與 6.4 同批、同一檔**：6.4 之取樣時點綁定 6.1 之檢查位置——
   6.1 若被移到任務啟動之後，6.4 會量到已載入大矩陣之 footprint 而失去意義。
   本檔以**同一組測試**釘住那個先後順序。

🔴 ICPERF SPEC v5.87 Task 0.6 (h)「⑤ IC 分析啟動准入」：固定欄數上限 80515（`settings.ic_analysis_max_features`）
   已刪，改為路由於 `start_*` 之前呼叫 `precheck_admission`——依「這次實際會載入的那些 run」之列×欄估算峰值，
   逾准入快照之 `budget_bytes` ⇒ 400 帶 need／have；工作量不可得 ⇒ 400 純字串（未知不放行，諮詢 r165 C2）。
   本檔各條之意圖不變（解析器須鏡像 loader、擋下時未建任務、未載入矩陣），門檻改由 autouse fixture 注入：
   預算＝「`ROWS` 列 × 舊上限 `OLD_CAP` 欄」單一來源之估算峰值 ⇒ 同列數下超過舊上限之 run 被擋、以內放行。

Task 6.1 邊界①：218369 特徵之 run ⇒ 400 **且任務未被建立**
   （斷言 task store 筆數不變，**不是只驗 HTTP 碼**——「先建任務再回 400」也會讓只驗碼的測試綠，
   而那正是要防的事）。
Task 6.1 邊界②：小 run ⇒ 200 **且任務確實被建立**（筆數 +1）。
Task 6.4：擋下時**未載入大矩陣**——以「本行程 footprint 在請求前後幾乎不變」證之。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import ic_analysis_service as svc_mod
from momentum.factories import get_memory_budget, ic_report_reason, load_ic_config

client = TestClient(app)
API = "/api/v1/ic"
REPO = Path(__file__).resolve().parents[2]

#: 量測 receipt 導出之上限所依據的那個 run 之特徵數（218,369）。TESTREG Task 4.4：原寫死本機 registry 之
#: run `e53e2290…`（2026-10-03 已刪）⇒ 改由 `inject_latest_run` 注入受控大 run（hash 由注入回傳，不寫死）。
BIG_RUN_FEATURES = 218_369
#: 已刪之固定欄數上限（GAP-3 UX Task 6.1）；本檔之准入預算以「`ROWS` 列 × 本欄數」之估算峰值注入。
OLD_CAP = 80_515
#: 注入 run 之列數（registry 實有 BTCUSDT 12h 之列數；以注入固定之，不依本機 registry 現況）。
ROWS = 1_951


def _src(n_f32: int) -> Dict[str, int]:
    """單一來源之准入估算規模（與 `ic_source_from_registry_entry` 同鍵；特徵庫原生 float32 ⇒ n_f64＝0）。"""
    return {"rows": ROWS, "n_f32": int(n_f32), "n_f64": 0}


def _planned_bytes(sources: List[Dict[str, int]], *, cross_sectional: bool = False) -> int:
    """以 service 之同一組鍵與預設設定（`resolve_planned_workload` 之 `/analyze` 分支）組工作量並估算峰值。

    🔴 用來**精確比對** detail 之 `need_bytes`：解析器若解析到錯的 run（他標的、被覆蓋之重複筆、
    不會被載入之 latest），need 必不等於本函式對「loader 實際會載入之那組來源」之估算 ⇒ 紅。
    """
    calc = load_ic_config(api_override=None).ic_calculation
    workload: Dict[str, Any] = {
        "sources": [dict(s) for s in sources],
        "cross_sectional": bool(cross_sectional),
        "windows": [int(w) for w in calc.rolling_windows],
        "icir_window": int(calc.icir.window),
        "stride": int(calc.rolling_stride),
        "method": ",".join(str(m) for m in calc.methods),
        "preprocess": "pit_expanding",
        "decay_horizons": len(calc.ic_decay_horizons),
        "redundancy_cols": 0,
        "deep_modules": [],
        "event_cells": 0,
    }
    budget = get_memory_budget()
    return int(budget.planned_bytes(budget.estimate("IC.analysis", workload)))


@pytest.fixture(autouse=True)
def admission_budget(monkeypatch):
    """注入准入快照：預算＝`ROWS` 列 × `OLD_CAP` 欄單一來源之估算峰值（不依實機記憶體）。

    同列數下欄數 > `OLD_CAP` ⇒ 估算峰值 > 預算 ⇒ 擋；欄數 ≤ `OLD_CAP` ⇒ 放行
    （判定為 `planned > budget_bytes`，恰等於時放行）。回傳注入之預算位元組數。
    """
    budget_bytes = _planned_bytes([_src(OLD_CAP)])
    state = {"available_bytes": budget_bytes, "budget_bytes": budget_bytes, "source": "test"}
    monkeypatch.setattr(get_memory_budget(), "admission_snapshot", lambda: dict(state))
    return budget_bytes


def _assert_rejected_for_memory(r, expected_need: int) -> Dict[str, Any]:
    """400 且為記憶體准入拒收：reason 由契約取、need 精確等於 loader 實際會載入那組來源之估算、need > have。"""
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert isinstance(detail, dict), f"拒收非記憶體准入（應為結構化 need／have）：{detail}"
    assert detail["reason"] == ic_report_reason("analysis_rejected")
    assert detail["need_bytes"] > detail["have_bytes"]
    assert detail["need_bytes"] == expected_need, (
        f"need_bytes={detail['need_bytes']} ≠ 預期 {expected_need} ⇒ 解析到的不是 loader 實際會載入的那組 run"
    )
    return detail


@pytest.fixture
def inject_latest_run(tmp_path):
    """把一筆**完全受控**的 run 注入 service 那份 registry 快照，離開時還原。

    🔴 **為什麼不能用本機現有的 run 當前提**（實際踩到兩次）：
      ① 止血閘讀的是 `ic_analysis_service._feature_library` 的快照，
         而 `resolve_latest_run_feature_count` 會**新建 registry 重讀磁碟**——
         拿後者算前提、用前者驗行為，兩者在全套跑時會分岔。
         這正是 `CODEX-R4-P1-03` 那個缺陷的鏡像：**我修好了產品碼，卻把同一個錯留在測試裡**。
      ② 更根本的問題是 `pytest tests/api` **會實際改寫** `data_cache/features/registry.json`
         （實查：跑完後 BTCUSDT/12h 的 latest 變成一筆指向 `pytest-of-louis/pytest-2770/…`
         暫存目錄、只有 15 個特徵的新 entry）。任何以「本機 latest 超過 cap」為前提的斷言
         都會因此在單跑時綠、全套時紅。**測試不得依賴會被測試自己改動的環境狀態。**

    manifest 由本 fixture 現寫（`total_features` 自訂），故 `is_materialized` 為真且數字可控。
    ICPERF v5.87 (h)：registry entry 與 manifest 皆寫 `row_count: ROWS`（准入估算之列數來源；缺列數 ⇒
    工作量不可得 ⇒ 400 純字串，不再放行）。

    🔴 **注入落在暫存 registry 檔，而非只改記憶體快照**（PRE-RED 審碼 r1 歸因）：`39377e29`
       起 service 於每次解析 run 前 `reload_registry()` 重讀磁碟，只改 `_entries` 之注入會被洗掉
       ⇒ 閘門看不到大 run 而放行（四支「繞過了閘門」紅之根因，非刪檔）。改為把 registry 之
       `_path` 指向暫存檔並把「原快照＋注入」寫入，重讀走真實 `_load` 而注入存活。
    """
    library = svc_mod.ic_analysis_service._feature_library  # noqa: SLF001
    registry = library._registry  # noqa: SLF001
    original = list(registry._entries)  # noqa: SLF001
    original_path = registry._path  # noqa: SLF001
    staged = tmp_path / "registry.json"
    staged.write_text(json.dumps(original), encoding="utf-8")
    registry._path = staged  # noqa: SLF001
    counter = {"n": 0}

    def _inject(symbol: str, feature_count: int, *, timeframe: str = "12h", config_hash: str = "",
                rows: Optional[int] = ROWS):
        """`rows=None` ⇒ registry 與 manifest 皆無列數（run 存在而規模不可得之情境）。"""
        counter["n"] += 1
        manifest = tmp_path / f"m{counter['n']}" / "feature_manifest.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest_body: Dict[str, Any] = {"total_features": feature_count}
        if rows is not None:
            manifest_body["row_count"] = rows
        manifest.write_text(json.dumps(manifest_body), encoding="utf-8")
        entry = {
            "symbol": symbol, "timeframe": timeframe,
            # `config_hash` 可指定（同一 hash 跨標的之情境）；未指定則自動唯一
            "config_hash": config_hash or f"injected{counter['n']:02d}",
            "feature_count": feature_count,
            "hdf5_relative_path": str(manifest),
            "last_generated_at": 1_900_000_000 + counter["n"],
        }
        if rows is not None:
            entry["row_count"] = rows
        registry._entries = list(registry._entries) + [entry]  # noqa: SLF001
        staged.write_text(json.dumps(registry._entries), encoding="utf-8")  # noqa: SLF001
        return entry

    _inject.registry_path = staged  # 新建 `FeatureRegistry()` 之讀取點（測試以 env 指向它）
    yield _inject
    registry._path = original_path  # noqa: SLF001
    registry._entries = original  # noqa: SLF001


def _task_count() -> int:
    service = svc_mod.ic_analysis_service
    with service._lock:  # noqa: SLF001 — 邊界①要求斷言 store 筆數，只能走 store
        return len(service._tasks)


@pytest.fixture(autouse=True)
def spy_start_analysis(monkeypatch):
    """記錄 `start_analysis` **有沒有被呼叫過**；被呼叫時**照實往下走**（不假裝成功）。

    🔴 **不是替身、不吞掉呼叫**：`CODEX-R1-P1-03` 指出我原本的 autouse 替身讓
    `start_analysis` 根本不執行 ⇒ 不建 analyzer、不開 HDF5，於是 Task 6.4 的
    「擋下時未載入大矩陣」變成**恆真**——用一個快測試換掉了真證據。
    現在改成純觀測：閘門正常時 `start_analysis` **一次都不會被呼叫**（那才是要證明的事），
    所以也不會有分析啟動、不會卡、不會吃記憶體。
    """
    service = svc_mod.ic_analysis_service
    calls = []

    async def spy(request):
        calls.append(request)
        # 記錄之後建一筆任務就回，**不跑真的分析**（那是十分鐘級、GB 級記憶體）。
        # 🔴 這樣**不會**變成假綠，因為判準不是「有沒有爆記憶體」而是 `calls == []`：
        #    閘門正常 ⇒ 本函式一次都不會被呼叫；閘門失效 ⇒ `calls` 非空 ⇒ 立刻紅。
        #    `CODEX-R1-P1-03` 當初抓的是「只看記憶體差」——那才是替身能矇混的地方。
        task_id = "gap3-stop-gate-observed"
        with service._lock:  # noqa: SLF001
            service._tasks[task_id] = {"task_id": task_id, "status": "running", "progress": 0.0}
        return {"task_id": task_id, "status": "running"}

    monkeypatch.setattr(service, "start_analysis", spy)
    yield calls
    with service._lock:  # noqa: SLF001
        service._tasks.pop("gap3-stop-gate-observed", None)


def test_gap3_ic_feature_cap_rejects_big_run_without_creating_task(spy_start_analysis, inject_latest_run):
    """邊界①：超量 ⇒ 400 且**任務未被建立**，且 `start_analysis` **一次都沒被呼叫**。

    🔴 第三個斷言是 `CODEX-R1-P1-03` 之後補的：只驗「任務數不變」時，
    「呼叫了 service、但 service 內部提前失敗」也會綠——那不是閘門擋下的。
    """
    big = inject_latest_run("BTCUSDT", BIG_RUN_FEATURES)
    before = _task_count()
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": big["config_hash"],
    })
    assert spy_start_analysis == [], "start_analysis 被呼叫了 ⇒ 閘門沒擋在它前面"
    # reason 由契約取得（Task 6.0）；need 精確等於該大 run 之估算峰值且逾預算
    _assert_rejected_for_memory(r, _planned_bytes([_src(BIG_RUN_FEATURES)]))
    # 🔴 這一條才是重點：只驗 400 的話，「先建任務再回 400」也會綠
    assert _task_count() == before, "任務被建立了 ⇒ 檢查沒有擋在 start_analysis 之前"


def test_gap3_ic_feature_cap_reason_comes_from_contract_not_hardcoded(inject_latest_run):
    """reason 字面須與 IC 契約一致（api 層不得自寫）。"""
    big = inject_latest_run("BTCUSDT", BIG_RUN_FEATURES)
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": big["config_hash"],
    })
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["reason"] == ic_report_reason("analysis_rejected")


def test_gap3_ic_feature_cap_unresolvable_is_rejected_explicitly(spy_start_analysis, inject_latest_run):
    """兩臂（ICPERF v5.87 (h)「⑤ IC 分析啟動准入」：路由解析不出者，來源存在則以中繼資料判、未知不放行）：

    ① run **存在**而列數不可得（registry 與 manifest 皆無 `row_count`）⇒ **明示拒收**（400 純字串），
       `start_analysis` 一次都不得被呼叫、任務數不變（「先建任務再回 400」也會讓只驗碼的測試綠）。
    ② run **不存在**（registry 無此 hash、無 `features_path`）⇒ 無物可載入，**交 service／loader 報其原錯**
       （run not found 於載入資料前即 raise，不吃記憶體），故准入不擋、`start_analysis` 被呼叫。

    🔴 前提已改（諮詢 r165 C2）：原 `..._unresolvable_is_allowed_through` 對兩者一律放行；改後只放行「無物可載入」。
    """
    unknown = inject_latest_run("BTCUSDT", BIG_RUN_FEATURES, rows=None)
    before = _task_count()
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": unknown["config_hash"],
    })
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert isinstance(detail, str) and detail.startswith("無法估算這次 IC 分析的記憶體需求"), detail
    assert spy_start_analysis == [], "run 存在而規模不可得卻抵達 service ⇒ 未知規模被放行"
    assert _task_count() == before, "任務被建立了 ⇒ 拒收沒有擋在 start_analysis 之前"

    r2 = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "no-such-hash-at-all",
    })
    assert r2.status_code != 400 or "無法估算" not in str(r2.json().get("detail")), r2.text
    assert spy_start_analysis != [], "run 不存在（無物可載入）卻被准入擋下 ⇒ loader 之原錯（run not found）被遮蔽"


def test_gap3_ic_feature_cap_reads_features_path_not_just_hash(spy_start_analysis, monkeypatch):
    """🔴 `CODEX-R1-P1-01`＋`GROK-R1-P1-01`：`features_path` 這條路也必須被閘門看見。

    兩家一致要求本批修（不接受只具名）。最惡形態是「**小 hash ＋ 實際大 `features_path`**」
    ——宣稱一個小 run、實際載入大的。service 在有 `features_path` 時載入的**就是它**，
    故准入以它之規模估算（need 精確等於大 path 之估算，非小 hash 之估算）。
    """
    # 以替身模擬「檔案側讀出超量」，避免測試依賴本機是否存在某個大特徵檔（路徑不會被讀取）
    monkeypatch.setattr(svc_mod, "ic_source_from_features_ref",
                        lambda p, **_kw: _src(999_999) if p else None)
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h",
        "config_hash": "a6a998593c3c55aa54e5d6fa537114b4",   # 只有 15 個特徵的小 hash
        "features_path": "pretend-gap3/pretend-big-features.h5",
    })
    assert r.status_code == 400, f"小 hash＋大 features_path 繞過了閘門：{r.text}"
    _assert_rejected_for_memory(r, _planned_bytes([_src(999_999)]))
    assert spy_start_analysis == [], "任務被啟動了 ⇒ 閘門沒擋住這條路"


def test_gap3_ic_feature_cap_covers_cross_sectional_runs(spy_start_analysis, inject_latest_run):
    """🔴 `CODEX-R2-P1-01`：橫截面請求帶的是 **per-symbol 的一組 run**，也必須被閘門看見。

    首版只看單一 `config_hash` ⇒ 兩個各自超標的 run 一起送進來會被整組放行。
    判準＝逐筆解析、整組估算（任一筆超標即擋整組）。
    TESTREG Task 4.4：兩筆 run 改由 `inject_latest_run` 注入（小 15／大 218,369；原依賴本機 registry 之已刪 run）。
    """
    small = inject_latest_run("BTCUSDT", 15)
    big = inject_latest_run("BTCUSDT", BIG_RUN_FEATURES)
    r = client.post(f"{API}/analyze", json={
        "mode": "cross_sectional", "timeframe": "12h",
        "cross_sectional_runs": [
            {"symbol": "BTCUSDT", "config_hash": small["config_hash"]},  # 15
            {"symbol": "BTCUSDT", "config_hash": big["config_hash"]},    # 218369
        ],
    })
    assert r.status_code == 400, f"橫截面請求繞過了閘門：{r.text}"
    # 兩筆同 symbol ⇒ loader 以 symbol 為 key、後者勝 ⇒ 實際只載入大那筆（橫截面估算）；
    # need 精確等於它——漏看大那筆（放行）或兩筆都算（列相加）皆不等
    _assert_rejected_for_memory(r, _planned_bytes([_src(BIG_RUN_FEATURES)], cross_sectional=True))
    assert spy_start_analysis == [], "任務被啟動了 ⇒ 閘門沒擋住橫截面這條路"


def test_gap3_ic_feature_cap_features_path_can_be_identifier_not_file(spy_start_analysis, inject_latest_run, monkeypatch):
    """🔴 `GROK-R2-P2-01`：`features_path` **未必是檔案路徑**（如 `parquet:SYM:<hash>`）。

    首版只認檔案 ⇒ `is_file()` 為假就放行，繞過復活。
    TESTREG Task 4.4：原依賴本機 registry 恰有「同一大 hash 跨多標的」之已刪 run；改為注入受控情境
    （同一 hash：BTCUSDT 218,369、ETHUSDT 300,000；另注入 BTCUSDT 小 run 15 作顯式小 hash）。
    """
    from momentum.factories import feature_count_from_features_file

    # 🔴 該 hash 在 registry 對到**多筆**（不同標的）。
    #    R2 首版一律取跨標的 max；`CODEX-R3-P2-02` 判定那是缺陷——識別字串**自己帶了 symbol**，
    #    取別的標的的數字等於把被選 run 的合法小值誤報成大值（false-block）。
    #    故本條現在釘的是「帶 symbol ⇒ 取該標的自己的數字」；
    #    「無 symbol scope ⇒ 跨標的 max」由 `..._identifier_keeps_symbol_scope` 以替身 registry 釘住。
    shared_hash = "gapcapidentprobe00000000000000ab"
    inject_latest_run("BTCUSDT", BIG_RUN_FEATURES, config_hash=shared_hash)
    inject_latest_run("ETHUSDT", 300_000, config_hash=shared_hash)   # 他標的較大 ⇒ 跨標的 max 會誤取它
    small = inject_latest_run("BTCUSDT", 15)
    # `feature_count_from_features_file` 對識別字串新建 `FeatureRegistry()` 重讀 ⇒ 指向注入之暫存 registry
    monkeypatch.setenv("FFACT_FEATURE_REGISTRY_PATH", str(inject_latest_run.registry_path))
    got = feature_count_from_features_file(f"parquet:BTCUSDT:{shared_hash}")
    assert got == BIG_RUN_FEATURES, f"識別字串未取被選標的自己的數字（得 {got}，應為 {BIG_RUN_FEATURES}）"
    assert got > OLD_CAP, "該 run 未逾注入預算對應之欄數，無法續驗閘門擋下"
    # 🔴 **必須顯式帶一個小 `config_hash`**，否則本條測不到它該測的東西：
    #    R3 之後閘門在「沒帶 hash」時會去解析 latest（latest 為大 run 時），
    #    於是即使閘門**完全不看** `features_path` 也照樣回 400 ⇒ 這條測試變成無法證偽。
    #    實際被抓到過：`6.1-M3`（閘門不看 features_path）的紅集合因此從兩條縮成一條。
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h",
        "config_hash": small["config_hash"],   # 只有 15 個特徵的小 hash
        "features_path": f"parquet:BTCUSDT:{shared_hash}",
    })
    assert r.status_code == 400, f"識別字串形式繞過了閘門：{r.text}"
    # need 精確等於 BTCUSDT 那筆（218,369）之估算——取到 ETHUSDT（300,000）或小 hash（15）皆不等
    _assert_rejected_for_memory(r, _planned_bytes([_src(BIG_RUN_FEATURES)]))
    assert spy_start_analysis == []


def test_gap3_ic_feature_cap_covers_implicit_latest_longitudinal(spy_start_analysis, inject_latest_run):
    """🔴 R3 三家一致（`CODEX-R3-P1-01`／`COMPOSER-R3-P1-01`／`GROK-R3-P1-02`）：
    **省略 `config_hash` 時 service 自己會挑 latest**，閘門必須看得到那一個 run。

    這條路徑對 R2 之前的所有候選都是隱形的：候選全部解析不出 ⇒ 放行 ⇒
    service 走 `find_latest_materialized` 把 latest 載進來。三家各自實跑同一組對照：
    不帶 hash ⇒ 200 且 `start_analysis` 被呼叫；補上 hash ⇒ 400、`calls=0`。
    """
    latest = OLD_CAP + 5_000
    inject_latest_run("ICGATEBIG", latest)
    r = client.post(f"{API}/analyze", json={"symbol": "ICGATEBIG", "timeframe": "12h"})
    assert r.status_code == 400, f"省略 config_hash 就繞過了閘門：{r.text}"
    # need 精確等於 service 會載入之 latest 的估算
    _assert_rejected_for_memory(r, _planned_bytes([_src(latest)]))
    assert spy_start_analysis == [], "任務被啟動了 ⇒ 隱式 latest 這條路沒被擋住"


def test_gap3_ic_feature_cap_covers_implicit_latest_cross_sectional(spy_start_analysis, inject_latest_run):
    """🔴 `GROK-R3-P1-01`／`COMPOSER-R3-P1-01`：橫截面只給 `symbols`（不帶 `cross_sectional_runs`）
    時，service 以 `config_hashes=None` 呼叫 `load_multi` ⇒ **逐標的 latest**。

    R2 只封了 `cross_sectional_runs`，同一端點的 `symbols`-only 形態仍開著。
    判準＝逐標的解析 latest、整組估算（任一標的超標即擋整組——橫截面本來就一起載入）。
    """
    big = OLD_CAP + 7_000
    inject_latest_run("ICGATESMALL", 100)
    inject_latest_run("ICGATEBIG", big)
    r = client.post(f"{API}/analyze", json={
        "mode": "cross_sectional", "timeframe": "12h", "symbols": ["ICGATESMALL", "ICGATEBIG"],
    })
    assert r.status_code == 400, f"symbols-only 橫截面繞過了閘門：{r.text}"
    _assert_rejected_for_memory(r, _planned_bytes([_src(100), _src(big)], cross_sectional=True))
    assert spy_start_analysis == [], "任務被啟動了 ⇒ symbols-only 這條路沒被擋住"


def test_gap3_ic_feature_cap_implicit_latest_under_cap_still_allowed(spy_start_analysis, inject_latest_run):
    """**反向對照**：latest 之估算在預算以內時，省略 `config_hash` 仍必須放行。

    🔴 沒有這條，「閘門把所有不帶 hash 的請求一律擋掉」也會讓上面兩條變綠——
    那是把止血閘做成了拒絕服務。本條釘住「擋的是超量，不是『沒指定 run』」。
    """
    inject_latest_run("ICGATESMALL", 100)
    client.post(f"{API}/analyze", json={"symbol": "ICGATESMALL", "timeframe": "12h"})
    assert spy_start_analysis != [], "cap 以內的隱式 latest 被擋掉了 ⇒ 閘門擋的是『沒指定 run』而非『超量』"


def test_gap3_ic_feature_cap_identifier_keeps_symbol_scope(monkeypatch):
    """🔴 `CODEX-R3-P2-02`：識別字串 `parquet:<SYMBOL>:<hash>` **自己帶了 symbol**，
    先前一律跨標的取 max ⇒ 會把被選標的的**合法小 run** 誤報成另一標的的大 run（false-block）。

    本條用替身 registry 構造 codex 指定的對照（同一 hash、兩個標的、一大一小），
    不依賴本機資料現況：帶 symbol 時取該標的自己的數字，無 symbol scope 時才取 max。
    """
    from momentum.FeatureEngineering import feature_registry as reg_mod
    from momentum.factories import feature_count_from_features_file

    rows = [
        {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "sharedhash", "feature_count": 100},
        {"symbol": "BCHUSDT", "timeframe": "12h", "config_hash": "sharedhash", "feature_count": 900},
    ]
    monkeypatch.setattr(reg_mod.FeatureRegistry, "list_all", lambda self: list(rows))
    assert feature_count_from_features_file("parquet:BTCUSDT:sharedhash") == 100, \
        "識別字串帶了 symbol 卻仍取跨標的 max ⇒ 合法小 run 會被誤擋"
    assert feature_count_from_features_file("parquet:BCHUSDT:sharedhash") == 900
    # 真正無 scope 的參照（只有 hash）維持跨標的 max＝保守
    assert feature_count_from_features_file("sharedhash") == 900, \
        "無 symbol scope 時不該收斂到某一筆——那會低報"


def test_gap3_ic_feature_cap_explicit_features_path_not_false_blocked(
        spy_start_analysis, monkeypatch, inject_latest_run):
    """🔴 `CODEX-R4-P1-01`：呼叫端**明確給了** `features_path` 時，service 載入的就是它，
    entry 只用來補 meta ⇒ 閘門**不得**再把不相干的 latest 算進來取 max（誤擋）。

    這是 R1–R3 那個病的**另一面**：前三輪是袋子少一味（該擋沒擋），本條是袋子多一味（不該擋卻擋）。
    codex RECHECK：`file=10, latest=90000` ⇒ 舊碼 `decision=BLOCK feature_count=90000`。
    """
    inject_latest_run("ICGATEBIG", OLD_CAP + 5_000)
    # 明確指向一個「小」的 features_path：閘門若仍把 latest 算進去就會誤擋（路徑不會被讀取）
    monkeypatch.setattr(svc_mod, "ic_source_from_features_ref",
                        lambda p, **_kw: _src(10) if p else None)
    r = client.post(f"{API}/analyze", json={
        "symbol": "ICGATEBIG", "timeframe": "12h",
        "features_path": "pretend-gap3/pretend-small-features.h5",
    })
    assert r.status_code != 400, f"明確給小 features_path 卻被不相干的 latest 誤擋：{r.text}"
    assert spy_start_analysis != [], "請求沒有抵達 service ⇒ 被閘門擋掉了"


def test_gap3_ic_feature_cap_cross_sectional_ignores_top_level_features_path(
        spy_start_analysis, monkeypatch, inject_latest_run):
    """🔴 `CODEX-R4-P1-01` 之後半：橫截面走 `load_multi`，**完全不看**頂層 `features_path`
    ⇒ 閘門也不得把它算進來。

    釘的是「閘門的候選集合＝service 該分支實際會用的東西」，不是「所有欄位一起取 max」。
    ICPERF v5.87 (h)：原依賴本機 registry 恰有之 hash（實查只有 BTCUSDT 一筆、且為他測試寫入之暫存
    run，ETHUSDT 無此 hash）——舊閘略過解析不出者，准入改為未知不放行後即誤紅 ⇒ 兩標的改由注入（同一小 hash）。
    """
    shared = "gapcapxsecsmall000000000000000ab"
    inject_latest_run("BTCUSDT", 15, config_hash=shared)
    inject_latest_run("ETHUSDT", 15, config_hash=shared)
    # 頂層 features_path 若被算進來即為超量（路徑不會被讀取）
    monkeypatch.setattr(svc_mod, "ic_source_from_features_ref",
                        lambda p, **_kw: _src(999_999) if p else None)
    r = client.post(f"{API}/analyze", json={
        "mode": "cross_sectional", "timeframe": "12h",
        "cross_sectional_runs": [
            {"symbol": "BTCUSDT", "config_hash": shared},  # 15
            {"symbol": "ETHUSDT", "config_hash": shared},
        ],
        "features_path": "pretend-gap3/irrelevant-huge.h5",
    })
    assert r.status_code != 400, f"橫截面被 service 根本不看的 features_path 誤擋：{r.text}"
    assert spy_start_analysis != [], "請求沒有抵達 service ⇒ 被閘門擋掉了"


def test_gap3_ic_feature_cap_full_analysis_does_not_resolve_latest(
        spy_start_analysis, inject_latest_run, monkeypatch):
    """🔴 `/full-analysis` 與 `/analyze` **走的不是同一條載入路徑**，閘門必須分開對齊。

    `_run_full_analysis` 直接把 `request.features_path` 餵給 `analyzer.analyze`，
    **從不碰 registry**（沒有 `get_entry`／`find_latest_materialized`／`load_multi`）。
    因此對它去查 latest 會擋掉一個根本不會載入任何 registry run 的請求——
    那正是 `CODEX-R4-P1-01` 那一族的誤擋，只是換**主委自己**在結構修正時犯。
    **本條由主委自攻抓到、未進 review**；它示範了 `resolve_planned_feature_count` 的維護風險：
    「鏡像 service」只有在**逐個入口**對齊時才成立，多一個入口就多一份對齊責任。

    ICPERF v5.87 (h)：工作量不可得改為明示拒收（未知不放行）⇒ 「不帶 `features_path`」之請求
    今為 400 **純字串**（工作量不可得）；若准入替它查了 latest，得到的會是大 latest 之**結構化** need／have
    拒收——兩者可分辨，故本條仍能證偽「拿掉入口分支」。另以小 `features_path` 對照：放行且抵達 service。
    兩段皆無條件斷言 registry 之 run 查詢**一次都沒發生**。
    """
    inject_latest_run("ICGATEBIG", OLD_CAP + 5_000)
    library = svc_mod.ic_analysis_service._feature_library  # noqa: SLF001
    lookups = []
    real_get, real_latest = library.get_entry, library.find_latest_materialized

    def spy_get(symbol, timeframe, config_hash):
        lookups.append(("get_entry", symbol, config_hash))
        return real_get(symbol, timeframe, config_hash)

    def spy_latest(symbol, timeframe):
        lookups.append(("find_latest_materialized", symbol))
        return real_latest(symbol, timeframe)

    monkeypatch.setattr(library, "get_entry", spy_get)
    monkeypatch.setattr(library, "find_latest_materialized", spy_latest)

    # 🔴 `CODEX-R5-P2-01`：本條原本只斷言「400 的 detail 不含 cap」，
    #    於是 full-analysis **非同步失敗**（`features_path=None` 傳給 analyzer）時它照樣綠——
    #    綠燈證明不了「閘門放行了」。改成觀測 stub ＋ **無條件斷言請求是否抵達 service**。
    calls = []

    async def spy_full(request):
        calls.append(request)
        return {"task_id": "gap3-full-observed", "status": "running"}

    monkeypatch.setattr(svc_mod.ic_analysis_service, "start_full_analysis", spy_full)

    # 🔴 **本請求刻意不帶 `features_path`**：帶了的話 longitudinal 分支也會優先用它，
    #    於是「拿掉入口分支」這個變異不改變行為 ⇒ 錄到**空紅集合**（實際發生過一次）。
    #    只有在「有 symbol／timeframe、無 features_path」時，兩條分支的行為才分岔。
    r = client.post(f"{API}/full-analysis", json={
        "symbol": "ICGATEBIG", "timeframe": "12h",
        "labels_path": "pretend-gap3/pretend-labels.h5",
    })
    # 不帶 features_path ⇒ /full-analysis 無物可載入（不碰 registry）⇒ 准入不擋、交 service 報其原錯；
    # 若准入替它查了 latest，大 latest 會得到結構化 need／have 拒收而請求不抵達 service（可分辨）
    assert r.status_code != 400, f"/full-analysis 被一個它根本不會載入的 latest 擋掉了：{r.text}"
    assert lookups == [], f"/full-analysis 之准入去查了 registry：{lookups}"
    assert calls != [], "無物可載入之請求未抵達 service ⇒ 被准入誤擋"
    calls.clear()

    # 對照：小 features_path（它唯一會載入的東西）⇒ 放行並抵達 service；大 latest 不得被算進來
    monkeypatch.setattr(svc_mod, "ic_source_from_features_ref",
                        lambda p, **_kw: _src(10) if p else None)
    r = client.post(f"{API}/full-analysis", json={
        "symbol": "ICGATEBIG", "timeframe": "12h",
        "features_path": "pretend-gap3/pretend-small-features.h5",
        "labels_path": "pretend-gap3/pretend-labels.h5",
    })
    assert calls != [], f"/full-analysis 被一個它根本不會載入的 latest 擋掉了：{r.text}"
    assert r.status_code == 200, f"閘門放行但請求未成功建立任務：{r.text}"
    assert lookups == [], f"/full-analysis 之准入去查了 registry：{lookups}"


def test_gap3_ic_feature_cap_cross_run_empty_hash_means_latest(spy_start_analysis, inject_latest_run):
    """🔴 `COMPOSER-R5-P1-01`（**該擋沒擋**）：逐筆 `config_hash` 為**空字串**時，
    `load_multi` 看到 falsy hash 會走 `find_latest`，閘門必須跟著走同一條。

    原碼 `get_entry(sym, tf, "")` 回 `None` ⇒ 所有候選解析不出 ⇒ 放行，
    而實際載入的是 latest（本機 161,031 > cap）。
    這是「解析器與 loader 不等價」的第三種形態——前兩種在 R4。
    """
    inject_latest_run("ICGATEBIG", OLD_CAP + 9_000)
    inject_latest_run("ICGATESMALL", 100)
    r = client.post(f"{API}/analyze", json={
        "mode": "cross_sectional", "timeframe": "12h",
        "cross_sectional_runs": [
            {"symbol": "ICGATESMALL", "config_hash": ""},
            {"symbol": "ICGATEBIG", "config_hash": ""},
        ],
    })
    assert r.status_code == 400, f"空字串 hash 繞過了閘門：{r.text}"
    # 空 hash 若未被視同「未指定 run」⇒ 解析不出 ⇒ 純字串拒收（非結構化 need／have）⇒ 下列斷言紅；
    # need 精確等於「兩標的各自 latest」之整組估算
    _assert_rejected_for_memory(
        r, _planned_bytes([_src(100), _src(OLD_CAP + 9_000)], cross_sectional=True))
    assert spy_start_analysis == [], "任務被啟動了 ⇒ 空 hash 這條路沒被擋住"


def test_gap3_ic_feature_cap_duplicate_symbol_uses_last_hash_like_loader(
        spy_start_analysis, inject_latest_run):
    """🔴 `CODEX-R5-P1-01`（**不該擋卻擋**）：同一 symbol 在 `cross_sectional_runs` 出現兩次時，
    `load_multi` 收到的是 **symbol-keyed dict**（後者覆蓋前者）⇒ 實際只載入最後那筆。

    閘門若對每一筆取 max，就會用一個**根本不會被載入**的 run 去擋 ⇒ 誤擋。
    codex RECHECK：`resolver_planned_count=80516` 而 `actual_loaded_keys={'BTCUSDT': 'small'}`。
    判準＝以 symbol 去重、取最後那筆（逐字沿用 loader 的 dict comprehension 語意）。
    """
    big = inject_latest_run("ICGATEDUP", OLD_CAP + 3_000)
    small = inject_latest_run("ICGATEDUP", 100)
    other = inject_latest_run("ICGATEOTHER", 100)
    r = client.post(f"{API}/analyze", json={
        "mode": "cross_sectional", "timeframe": "12h",
        "cross_sectional_runs": [
            {"symbol": "ICGATEDUP", "config_hash": big["config_hash"]},     # 會被下一筆覆蓋
            {"symbol": "ICGATEDUP", "config_hash": small["config_hash"]},   # loader 實際用這筆
            {"symbol": "ICGATEOTHER", "config_hash": other["config_hash"]},
        ],
    })
    assert r.status_code != 400, f"用一個不會被載入的 run 誤擋了：{r.text}"
    assert spy_start_analysis != [], "請求沒有抵達 service ⇒ 被閘門擋掉了"


# ── 收案判準 D：請求形狀**雙向**探針矩陣 ────────────────────────────────────
# 🔴 三家 consult 一致（`20260828-gap3ux-b9-consult-r1`）：B9 之收案判準由「三家零 finding」
#    改為**每一種請求形狀都有 under-block（該擋）與 over-block（不該擋）各一條**。
#    理由：五輪 finding 數 10→3→4→5→3 非單調，證明每輪是在**擴攻擊面**而非品質退步；
#    對一個「存活至 GAP-6、上線即刪」的過渡止血閘，無限輪 review 的 ROI 為負。
#    本節補齊矩陣中原本只有單向的六格——**單向的格子正是前五輪缺陷的藏身處**。

def test_gap3_matrix_hash_path_conflict_big_hash_small_path_allowed(spy_start_analysis, inject_latest_run, monkeypatch):
    """矩陣：longitudinal「hash ＋ path 衝突」之 **over-block** 側。

    service 在有 `features_path` 時載入的**就是它**（entry 只用來補 meta），
    所以「大 hash ＋ 小 path」必須放行。反向（小 hash ＋ 大 path 須擋）由
    `..._reads_features_path_not_just_hash` 守住。
    """
    # 實際會載入之小 path（路徑不會被讀取）
    monkeypatch.setattr(svc_mod, "ic_source_from_features_ref",
                        lambda p, **_kw: _src(10) if p else None)
    big = inject_latest_run("BTCUSDT", BIG_RUN_FEATURES)
    # 🔴 非空前提（TESTREG Task 4.4）：原寫死之大 hash 已不在 registry ⇒ 解析不出、閘門行為與本條無關，
    #    本條變成恆真。先證「同一大 hash 單獨送 ⇒ 被擋（need＝大 run 之估算）」，下方之放行才代表「path 蓋過 hash」。
    pre = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": big["config_hash"],
    })
    assert pre.status_code == 400 and pre.json()["detail"]["need_bytes"] == _planned_bytes(
        [_src(BIG_RUN_FEATURES)]), f"前提不成立：大 hash 單獨送未被擋（{pre.status_code}: {pre.text[:200]}）"
    assert spy_start_analysis == [], "前提請求不得抵達 service"
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h",
        "config_hash": big["config_hash"],                          # 218,369，估算遠逾預算
        "features_path": "pretend-gap3/pretend-small-features.h5",  # 實際會載入的是這個
    })
    assert r.status_code != 400, f"大 hash 蓋過了實際會載入的小 path：{r.text}"
    assert spy_start_analysis != [], "請求沒有抵達 service ⇒ 被閘門擋掉了"


def test_gap3_matrix_cross_sectional_runs_all_small_allowed(spy_start_analysis, inject_latest_run):
    """矩陣：`cross_sectional_runs` 之 **over-block** 側——整組估算在預算以內須放行。"""
    a = inject_latest_run("ICGATEA", 100)
    b = inject_latest_run("ICGATEB", 200)
    r = client.post(f"{API}/analyze", json={
        "mode": "cross_sectional", "timeframe": "12h",
        "cross_sectional_runs": [
            {"symbol": "ICGATEA", "config_hash": a["config_hash"]},
            {"symbol": "ICGATEB", "config_hash": b["config_hash"]},
        ],
    })
    assert r.status_code != 400, f"全部在 cap 以內卻被擋：{r.text}"
    assert spy_start_analysis != [], "請求沒有抵達 service"


def test_gap3_matrix_symbols_only_all_small_allowed(spy_start_analysis, inject_latest_run):
    """矩陣：`symbols`-only 之 **over-block** 側——逐標的 latest 皆小須放行。"""
    inject_latest_run("ICGATEA", 100)
    inject_latest_run("ICGATEB", 200)
    r = client.post(f"{API}/analyze", json={
        "mode": "cross_sectional", "timeframe": "12h", "symbols": ["ICGATEA", "ICGATEB"],
    })
    assert r.status_code != 400, f"逐標的 latest 皆小卻被擋：{r.text}"
    assert spy_start_analysis != [], "請求沒有抵達 service"


def test_gap3_matrix_empty_hash_with_small_latest_allowed(spy_start_analysis, inject_latest_run):
    """矩陣：空字串 hash 之 **over-block** 側——退回 latest 後若估算在預算以內須放行。

    沒有這條，「空 hash 一律擋」也會讓 `..._cross_run_empty_hash_means_latest` 變綠。
    """
    inject_latest_run("ICGATEA", 100)
    inject_latest_run("ICGATEB", 200)
    r = client.post(f"{API}/analyze", json={
        "mode": "cross_sectional", "timeframe": "12h",
        "cross_sectional_runs": [
            {"symbol": "ICGATEA", "config_hash": ""},
            {"symbol": "ICGATEB", "config_hash": ""},
        ],
    })
    assert r.status_code != 400, f"空 hash 退回的小 latest 被擋：{r.text}"
    assert spy_start_analysis != [], "請求沒有抵達 service"


def test_gap3_matrix_duplicate_symbol_last_is_big_must_block(spy_start_analysis, inject_latest_run):
    """矩陣：同 symbol 重複之 **under-block** 側——**最後那筆**大時必須擋。

    與 `..._duplicate_symbol_uses_last_hash_like_loader`（最後那筆小 ⇒ 放行）成對。
    兩條一起才證明判準是「取最後那筆」，而不是「重複就放行」或「重複就擋」。
    """
    small = inject_latest_run("ICGATEDUP", 100)
    big = inject_latest_run("ICGATEDUP", OLD_CAP + 4_000)
    other = inject_latest_run("ICGATEOTHER", 100)
    r = client.post(f"{API}/analyze", json={
        "mode": "cross_sectional", "timeframe": "12h",
        "cross_sectional_runs": [
            {"symbol": "ICGATEDUP", "config_hash": small["config_hash"]},   # 被覆蓋
            {"symbol": "ICGATEDUP", "config_hash": big["config_hash"]},     # loader 實際用這筆
            {"symbol": "ICGATEOTHER", "config_hash": other["config_hash"]},
        ],
    })
    assert r.status_code == 400, f"最後那筆超標卻放行：{r.text}"
    # need 精確等於 loader 實際載入之「最後那筆＋他標的」兩來源（多算被覆蓋之那筆即不等）
    _assert_rejected_for_memory(
        r, _planned_bytes([_src(OLD_CAP + 4_000), _src(100)], cross_sectional=True))
    assert spy_start_analysis == [], "任務被啟動了"


def test_gap3_matrix_full_analysis_big_features_path_must_block(monkeypatch):
    """矩陣：`/full-analysis` 之 **under-block** 側——它唯一會載入的東西超標時必須擋。

    與 `..._full_analysis_does_not_resolve_latest`（不得替它查 registry）成對：
    一條證明「不看它不會載入的」，一條證明「看它真的會載入的」。
    """
    calls = []

    async def spy_full(request):
        calls.append(request)
        return {"task_id": "gap3-full-observed", "status": "running"}

    monkeypatch.setattr(svc_mod.ic_analysis_service, "start_full_analysis", spy_full)
    # 以替身模擬「檔頭讀出超量」（路徑不會被讀取）
    monkeypatch.setattr(svc_mod, "ic_source_from_features_ref",
                        lambda p, **_kw: _src(999_999) if p else None)
    r = client.post(f"{API}/full-analysis", json={
        "features_path": "pretend-gap3/pretend-huge-features.h5",
        "labels_path": "pretend-gap3/pretend-labels.h5",
    })
    assert r.status_code == 400, f"/full-analysis 的大 features_path 沒被擋：{r.text}"
    _assert_rejected_for_memory(r, _planned_bytes([_src(999_999)]))
    assert calls == [], "任務被啟動了 ⇒ 閘門沒擋在它前面"


def test_gap3_matrix_resolver_equals_loader_plan(inject_latest_run, monkeypatch):
    """🔴 **雙路徑比對**（consult `COMPOSER-R1` RULING-4 步驟 2）：
    同一 request 下，閘門解析用的 `(symbol → config_hash)` 必須**逐一等於**
    `_plan_cross_sectional_load` 交給 `load_multi` 的那一份。

    這是 R5 兩條 P1 的直接防線：它們的病根就是「兩處各推導一次」。
    本條不驗數字大小，只驗**兩邊看的是同一組 run**——不等即 FAIL。
    ICPERF v5.87 (h)：准入之解析器（`resolve_planned_workload` → `_resolve_workload_sources`）與既有之
    `resolve_planned_feature_count` **兩者都**須逐一等於 loader 之計畫。第三組改用注入之真實 hash：
    准入解析器於任一來源不可得時即停（未知不放行），不存在之 hash 會使觀測只到第一筆、無從比對整組。
    """
    from api.models.ic_models import CrossRunRef, ICAnalyzeRequest

    a = inject_latest_run("ICGATEA", 100)
    a2 = inject_latest_run("ICGATEA", 150)
    b = inject_latest_run("ICGATEB", 200)
    service = svc_mod.ic_analysis_service

    cases = [
        ICAnalyzeRequest(mode="cross_sectional", timeframe="12h",
                         symbols=["ICGATEA", "ICGATEB"]),
        ICAnalyzeRequest(mode="cross_sectional", timeframe="12h",
                         cross_sectional_runs=[CrossRunRef(symbol="ICGATEA", config_hash=""),
                                               CrossRunRef(symbol="ICGATEB", config_hash="")]),
        ICAnalyzeRequest(mode="cross_sectional", timeframe="12h",
                         cross_sectional_runs=[CrossRunRef(symbol="ICGATEA", config_hash=a["config_hash"]),
                                               CrossRunRef(symbol="ICGATEA", config_hash=a2["config_hash"]),
                                               CrossRunRef(symbol="ICGATEB", config_hash=b["config_hash"])]),
    ]
    library = service._feature_library  # noqa: SLF001
    resolvers = {
        "resolve_planned_feature_count": service.resolve_planned_feature_count,
        "resolve_planned_workload": service.resolve_planned_workload,
    }
    for req in cases:
        # ── loader 側：`load_multi` 以 symbol 為 key ⇒ 實際選擇＝去重後該 key 的值
        symbols_resolved, config_hashes = service._plan_cross_sectional_load(req)  # noqa: SLF001
        loader_view = {
            sym: ((config_hashes or {}).get(sym) or "").strip() or None
            for sym in dict.fromkeys(symbols_resolved)
        }

        for name, resolve in resolvers.items():
            # ── 閘門側：**實際觀測**解析器去查了哪些 run（不是重算一次——那會是恆真斷言）
            observed = {}
            real_get, real_latest = library.get_entry, library.find_latest_materialized

            def spy_get(symbol, timeframe, config_hash, _r=real_get, _o=observed):
                _o[symbol] = config_hash
                return _r(symbol, timeframe, config_hash)

            def spy_latest(symbol, timeframe, _r=real_latest, _o=observed):
                _o[symbol] = None          # 未指定 run ⇒ 走 latest
                return _r(symbol, timeframe)

            monkeypatch.setattr(library, "get_entry", spy_get)
            monkeypatch.setattr(library, "find_latest_materialized", spy_latest)
            try:
                resolved = resolve(req)
            finally:
                monkeypatch.setattr(library, "get_entry", real_get)
                monkeypatch.setattr(library, "find_latest_materialized", real_latest)

            assert resolved is not None, f"{name} 解析不出（注入之 run 皆有列數與特徵數）：request={req}"
            assert observed == loader_view, (
                f"閘門實際查的 run 與 loader 會載入的不同：\n"
                f"  閘門={observed}\n  loader={loader_view}\n  request={req}"
            )


def test_gap3_ic_feature_cap_registry_lowball_is_caught_by_manifest(monkeypatch, tmp_path):
    """🔴 `CODEX-R4-P1-02`：latest 解析**不得只信 registry 的 `feature_count`**。

    registry 是產生時寫的中繼資料，會過期／低報；低報時閘門就放行實際超量的 artifact。
    codex 用真 manifest（`total_features`）配 stub registry（15）打出反例。
    判準＝registry 與 manifest **取大**（保守側）。
    """
    from momentum.factories import feature_count_from_registry_entry

    # TESTREG Task 4.4：原掃本機 registry 找「恰好存在之 manifest」（環境依賴；釘選 run 刪除後即無對照）
    # ⇒ 改由本測試現寫 manifest（total_features 為真值），registry 低報值與之明確不同。
    manifest_file = tmp_path / "run" / "feature_manifest.json"
    manifest_file.parent.mkdir(parents=True)
    manifest_file.write_text(json.dumps({"total_features": 218_369}), encoding="utf-8")
    rel, real_count = str(manifest_file), 218_369
    # registry 低報成 15，manifest 仍是真值 ⇒ 必須取到真值
    got = feature_count_from_registry_entry({"feature_count": 15, "hdf5_relative_path": rel})
    assert got == real_count, f"registry 低報時未由 manifest 糾正（得 {got}，manifest 為 {real_count}）"
    # manifest 讀不到時退回 registry，不憑空造值
    assert feature_count_from_registry_entry(
        {"feature_count": 15, "hdf5_relative_path": "/no/such/manifest.json"}) == 15
    assert feature_count_from_registry_entry(None) is None


def test_gap3_ic_feature_cap_gate_and_service_share_one_registry_snapshot(tmp_path_factory):
    """🔴 `CODEX-R4-P1-03`：閘門與 service **必須讀同一份 registry 快照**。

    這**不是**極窄的競態（composer R4 之判語，經複驗推翻）：
    `ic_analysis_service` 是模組級單例，`_feature_library` 在**行程啟動時**建好、registry 只讀一次；
    而閘門原本每次請求 `FeatureRegistry()` 重讀磁碟 ⇒ 兩份快照在**整個行程生命期**持續不同步。
    觸發條件正是本專案主要流程：跑完 Feature Factory 產生新 run、沒重啟後端就去分析。

    判準＝閘門解析出來的數字，來自 **service 自己那個 `_feature_library`**：
    改動該實例的 registry，閘門的答案必須跟著改。
    """
    service = svc_mod.ic_analysis_service
    registry = service._feature_library._registry  # noqa: SLF001 — 本條要證明的就是「同一個實例」

    class _Req:
        mode = "longitudinal"
        symbol = "GATEPROBE"
        timeframe = "12h"
        config_hash = None
        features_path = None
        symbols = None
        cross_sectional_runs = None

    # 🔴 判準必須可證偽：注入一筆**只存在於 service 這個 registry 實例**的 entry
    #    （正式 data_cache/features/registry.json 沒有它）。解析器若改用自己新建的 `FeatureRegistry()`
    #    重讀正式磁碟檔，就看不到它 ⇒ 回 None ⇒ 本條紅。
    #    TESTREG Task 4.4：`39377e29` 起 service 於每次解析前 `reload_registry()` 重讀**該實例之 `_path`**，
    #    只改 `_entries` 之注入會被洗掉（本條原紅之根因，同 inject_latest_run 之歸因）⇒ 改為把該實例之
    #    `_path` 指向暫存 registry（原快照＋注入）；manifest 改由本測試現寫（原依賴本機 registry 恰有可用
    #    manifest，屬環境依賴），`is_materialized` 為真。
    tmp_path = tmp_path_factory.mktemp("share_snapshot")
    real_manifest = tmp_path / "probe" / "feature_manifest.json"
    real_manifest.parent.mkdir(parents=True)
    real_manifest.write_text(json.dumps({"total_features": 90_000, "row_count": ROWS}), encoding="utf-8")

    # ICPERF v5.87 (h)：准入之解析器（`_resolve_workload_sources`）亦須讀同一份快照 ⇒ entry 帶列數
    fake = {"symbol": "GATEPROBE", "timeframe": "12h", "config_hash": "probe",
            "feature_count": 90_000, "row_count": ROWS, "hdf5_relative_path": str(real_manifest),
            "last_generated_at": 9_999_999_999}
    original = list(registry._entries)  # noqa: SLF001
    original_path = registry._path  # noqa: SLF001
    staged = tmp_path / "registry.json"
    staged.write_text(json.dumps(original + [fake]), encoding="utf-8")
    try:
        registry._path = staged  # noqa: SLF001
        registry._entries = original + [fake]  # noqa: SLF001
        got = service.resolve_planned_feature_count(_Req())
        assert got is not None, (
            "解析器看不到只存在於 service 記憶體快照的 entry "
            "⇒ 它讀的是自己新建的 registry，與 service 實際會載入的不是同一份"
        )
        assert got >= 90_000, f"解析到的不是那筆注入的 entry：{got}"
        sources = service._resolve_workload_sources(_Req())  # noqa: SLF001 — 准入解析器
        assert sources == [_src(90_000)], (
            f"准入解析器看不到只存在於 service 快照的 entry（或解析到別筆）：{sources}"
        )
    finally:
        registry._path = original_path  # noqa: SLF001
        registry._entries = original  # noqa: SLF001
    # 還原後必須解析不出（證明上面的成功不是來自別處）
    assert service.resolve_planned_feature_count(_Req()) is None
    # 快照還原後該 run 不存在 ⇒ 無物可載入（空清單；交 loader 報 run not found），非「存在而規模不可得」之 None
    assert service._resolve_workload_sources(_Req()) == []  # noqa: SLF001


def test_gap3_ic_feature_cap_identifier_scopes_by_timeframe(monkeypatch):
    """🔴 `CODEX-R4-P2-02`：識別字串只用 symbol 收斂**不夠**——同一 hash 可跨 timeframe。

    `parquet:BTCUSDT:<hash>` 會挑到 1h 的大 run 去擋 12h 的小 run（誤擋）。
    codex RECHECK：`identifier_count=90000 expected_12h_count=10`。
    """
    from momentum.FeatureEngineering import feature_registry as reg_mod
    from momentum.factories import feature_count_from_features_file

    rows = [
        {"symbol": "BTCUSDT", "timeframe": "1h", "config_hash": "shared", "feature_count": 90_000},
        {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "shared", "feature_count": 10},
    ]
    monkeypatch.setattr(reg_mod.FeatureRegistry, "list_all", lambda self: list(rows))
    assert feature_count_from_features_file(
        "parquet:BTCUSDT:shared", symbol="BTCUSDT", timeframe="12h") == 10, \
        "識別字串未用 timeframe 收斂 ⇒ 12h 的小 run 會被 1h 的大 run 誤擋"
    assert feature_count_from_features_file(
        "parquet:BTCUSDT:shared", symbol="BTCUSDT", timeframe="1h") == 90_000
    # 呼叫端沒給 scope 時維持跨範圍 max＝保守
    assert feature_count_from_features_file("parquet:BTCUSDT:shared") == 90_000


def test_gap3_ic_feature_cap_message_does_not_ask_for_impossible_action(inject_latest_run):
    """🔴 使用者裁定（2026-08-27）：錯誤訊息**不得叫使用者去做他沒有介面可做的事**。

    原文為「請先縮減特徵數再分析」——本專案沒有任何縮減特徵數的介面，
    那句話把「系統暫時做不到」寫成了「你操作錯了」，是一條死路。

    ICPERF v5.87 (h)：訊息改為陳述需要與可用（GB）、在啟動前擋下、以及何時需求會下降
    （分塊計算 ICPERF Task 3.2；原指 GAP-6 之固定上限已刪）。
    """
    big = inject_latest_run("BTCUSDT", BIG_RUN_FEATURES)
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": big["config_hash"],
    })
    assert r.status_code == 400
    detail = r.json()["detail"]
    message = detail["message"]
    assert "請先縮減特徵數" not in message, "訊息仍指向一個沒有介面可做的操作"
    assert "縮減特徵" not in message, "訊息仍指向一個沒有介面可做的操作"
    gib = float(1 << 30)
    assert f"{detail['need_bytes'] / gib:.2f} GB" in message, "訊息未明講這次需要多少記憶體"
    assert f"{detail['have_bytes'] / gib:.2f} GB" in message, "訊息未明講本機可用之預算"
    assert "擋下" in message, "訊息未明講這個 run 目前做不到（於啟動前擋下）"
    assert "ICPERF Task 3.2" in message, "訊息未指出需求何時會下降"


def test_gap3_ic_feature_cap_features_file_reads_metadata_only(tmp_path):
    """檔案側解析**只讀 HDF5 header 之 shape**，不載入矩陣（Task 6.4 之硬性要求）。

    TESTREG Task 4.4：原掃本機 data_cache/features/*.h5 頂層檔、缺即 skip（環境依賴，現行佈局下恆 skip 之虞）。
    改為 tmp 寫一個巢狀 `features` 資料集：宣告形狀 1,000,000 × 200,000 float32（約 800 GB）但 chunked
    且從未寫入 ⇒ 檔案只有 header；解析器若載入矩陣須配置約 800 GB（無法在本機完成），只讀 shape 才能毫秒回答。
    """
    import h5py

    from momentum.factories import feature_count_from_features_file

    sample = [tmp_path / "declared_only.h5"]
    from momentum.FeatureEngineering.feature_naming import stamp_h5_feature_naming_version

    with h5py.File(sample[0], "w") as handle:
        stamp_h5_feature_naming_version(handle.attrs)  # FF-NAME Task 3.4（v18）：IC 交接 h5 根屬性（正式寫出端同一函式）
        handle.create_dataset("ETHUSDT/12h/features", shape=(1_000_000, 200_000), dtype="float32",
                              chunks=(1024, 1024))
    assert sample[0].stat().st_size < 1_000_000  # 只有 header（未配置資料區塊）
    count = feature_count_from_features_file(str(sample[0]))
    assert isinstance(count, int) and count > 0, "讀不到欄數 ⇒ 檔案側解析形同虛設"
    assert count == 200_000
    # FF-NAME Task 3.4（v18）：缺 feature_naming_version 根屬性之交接 h5 ⇒ 拒（不吞為「量不出」而放行）
    from momentum.FeatureEngineering.feature_naming import FeatureNamingVersionError

    unstamped = tmp_path / "unstamped.h5"
    with h5py.File(unstamped, "w") as handle:
        handle.create_dataset("ETHUSDT/12h/features", shape=(10, 3), dtype="float32")
    with pytest.raises(FeatureNamingVersionError, match="feature_naming_version"):
        feature_count_from_features_file(str(unstamped))
    # 讀不到／不存在一律 None，不猜
    assert feature_count_from_features_file("/no/such/file.h5") is None
    assert feature_count_from_features_file(None) is None


def test_gap3_ic_feature_cap_budget_comes_from_admission_snapshot(inject_latest_run, monkeypatch):
    """🔴 **禁拍腦袋填**（原 `..._value_is_backed_by_measurement_receipt`）：固定欄數上限已刪
    （ICPERF v5.87 (h)），擋下之依據＝准入快照之 `budget_bytes`（實機量測之可用記憶體），不是寫死的常數。

    判準：①設定欄位 `ic_analysis_max_features` 已不存在；②拒收之 `have_bytes` 精確等於注入之預算；
    ③改注入另一個預算，`have_bytes` 跟著變（證明非常數）。
    """
    from api.core.config import Settings

    # 只看欄位名，不印 settings 物件（其 repr 含交易所金鑰）
    assert "ic_analysis_max_features" not in set(Settings.model_fields)

    big = inject_latest_run("BTCUSDT", BIG_RUN_FEATURES)
    body = {"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": big["config_hash"]}
    budget_bytes = _planned_bytes([_src(OLD_CAP)])
    detail = _assert_rejected_for_memory(client.post(f"{API}/analyze", json=body),
                                         _planned_bytes([_src(BIG_RUN_FEATURES)]))
    assert detail["have_bytes"] == budget_bytes, "have_bytes 不是准入快照之預算"
    assert detail["measurement_source"] == "test", "量測來源不是准入快照"

    other = budget_bytes + 12_345
    monkeypatch.setattr(get_memory_budget(), "admission_snapshot",
                        lambda: {"available_bytes": other, "budget_bytes": other, "source": "test-2"})
    detail = client.post(f"{API}/analyze", json=body).json()["detail"]
    assert detail["have_bytes"] == other, "改注入預算後 have_bytes 未跟著變 ⇒ 預算是寫死的常數"
    assert detail["measurement_source"] == "test-2"


def test_gap3_ic_stop_gate_alive_no_big_matrix_loaded(spy_start_analysis, inject_latest_run):
    """Task 6.4：擋下時**未載入大矩陣**。

    🔴 取樣時點綁 6.1 之檢查位置：本測試在**同一個行程**內量請求前後之 footprint。
    若 6.1 被移到任務啟動之後，分析會開始載入特徵、footprint 大幅上升 ⇒ 本條紅。
    🔴 **不得在准入檢查（原 cap 檢查）之前採樣就宣稱通過**（SPEC 明列之假綠形態）——
    本條的兩次採樣都在請求**之後**，比較的是「擋下之後」與「請求之前」的差。
    """
    import os
    import resource

    def rss_kb() -> int:
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024

    big = inject_latest_run("BTCUSDT", BIG_RUN_FEATURES)   # 注入只寫 manifest（無矩陣），不影響下方 RSS 對照
    before_tasks = _task_count()
    before = rss_kb()
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": big["config_hash"],
    })
    after_request = rss_kb()
    assert r.status_code == 400
    after_response = rss_kb()

    assert _task_count() == before_tasks          # ①任務未建立
    # 🔴 `CODEX-R1-P1-03` 之後補：**證明分析路徑一步都沒走**。
    #    原本只看記憶體差，而我當時的替身讓 service 根本不執行 ⇒ 該斷言恆真、是假綠。
    assert spy_start_analysis == [], "start_analysis 被呼叫了 ⇒ 本條之『未載入大矩陣』無意義"
    assert os.getpid() > 0                        # ②單一 pid（本行程自身）
    # ③未載入大矩陣：該 run 的量測 peak 為 GB 級；擋下之路徑不得有可觀增長。
    # 🔴 這裡用 `ru_maxrss` 而非 `sample`：本條要驗的是「**這個行程**在被擋的路徑上有沒有長大」，
    #    是同行程前後差；Task 6.2 之絕對量測才需要 footprint（跨行程、且 RSS 會失真）。
    growth_mb = (max(after_request, after_response) - before) / 1024.0
    assert growth_mb < 256, f"擋下時記憶體成長 {growth_mb:.1f}MB ⇒ 疑似已載入特徵矩陣"


def test_gap3_ic_stop_gate_alive_small_run_still_creates_task(inject_latest_run):
    """邊界②：小 run ⇒ 不被擋，且任務**確實被建立**（筆數 +1）。

    🔴 對照組：沒有這條的話，「把所有請求都擋掉」也會讓邊界①全綠。
    ICPERF v5.87 (h)：原依賴本機 registry 恰有之小 hash（實查為他測試寫入之暫存 run）；准入改為未知不放行後，
    該筆一旦消失本條即誤紅 ⇒ 改由注入受控小 run（15 個特徵、`ROWS` 列）。
    """
    small = inject_latest_run("BTCUSDT", 15)
    before = _task_count()
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h",
        "config_hash": small["config_hash"],   # 15 個特徵
    })
    assert r.status_code == 200, r.text
    assert _task_count() == before + 1, "小 run 未建立任務 ⇒ 閘門誤擋"
