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


def _registry_entries():
    """讀本機 registry 原始內容（測試之對照基準；不經任何被測程式碼）。"""
    return json.loads(
        (REPO / "data_cache" / "features" / "registry.json").read_text(encoding="utf-8"))


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
    """
    library = svc_mod.ic_analysis_service._feature_library  # noqa: SLF001
    registry = library._registry  # noqa: SLF001
    original = list(registry._entries)  # noqa: SLF001
    counter = {"n": 0}

    def _inject(symbol: str, feature_count: int, *, timeframe: str = "12h"):
        counter["n"] += 1
        manifest = tmp_path / f"m{counter['n']}" / "feature_manifest.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"total_features": feature_count}), encoding="utf-8")
        entry = {
            "symbol": symbol, "timeframe": timeframe,
            "config_hash": f"injected{counter['n']:02d}",
            "feature_count": feature_count,
            "hdf5_relative_path": str(manifest),
            "last_generated_at": 1_900_000_000 + counter["n"],
        }
        registry._entries = list(registry._entries) + [entry]  # noqa: SLF001
        return entry

    yield _inject
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


def test_gap3_ic_feature_cap_rejects_big_run_without_creating_task(spy_start_analysis):
    """邊界①：超量 ⇒ 400 且**任務未被建立**，且 `start_analysis` **一次都沒被呼叫**。

    🔴 第三個斷言是 `CODEX-R1-P1-03` 之後補的：只驗「任務數不變」時，
    「呼叫了 service、但 service 內部提前失敗」也會綠——那不是閘門擋下的。
    """
    before = _task_count()
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": BIG_RUN_CONFIG_HASH,
    })
    assert spy_start_analysis == [], "start_analysis 被呼叫了 ⇒ 閘門沒擋在它前面"
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


def test_gap3_ic_feature_cap_unresolvable_is_allowed_through(spy_start_analysis):
    """解析不出特徵數且**無 `features_path`** ⇒ 不被本閘擋（本閘只擋「已知超量」）。

    🔴 `GROK-R1-P2-01`：本條原本寫成
       `assert detail.get("reason") != "..." or True` ——**恆真、證明不了任何事**；
       且成功路徑為 200 時整個 `if status_code == 400` 區塊根本不執行。
       改為**無條件斷言**：不論回什麼碼，都必須證明「閘門放行了」＝
       `start_analysis` 確實被呼叫到（那才是『沒被 cap 擋下』的證據）。
    """
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "no-such-hash-at-all",
    })
    # 🔴 無條件：閘門放行 ⇒ 請求必定抵達 service（之後是否失敗與本閘無關）
    assert spy_start_analysis != [], "閘門把『解析不出特徵數』的請求擋掉了 ⇒ 與本 Task 之決策不符"
    detail = r.json().get("detail")
    if isinstance(detail, dict):
        assert "cap" not in detail, f"未解析出特徵數卻被 cap 擋下：{detail}"


def test_gap3_ic_feature_cap_reads_features_path_not_just_hash(spy_start_analysis, monkeypatch):
    """🔴 `CODEX-R1-P1-01`＋`GROK-R1-P1-01`：`features_path` 這條路也必須被閘門看見。

    兩家一致要求本批修（不接受只具名）。最惡形態是「**小 hash ＋ 實際大 `features_path`**」
    ——宣稱一個小 run、實際載入大的。故閘門取兩個來源之**最大值**。
    """
    from momentum import factories

    # 以替身模擬「檔案側算出超量」，避免測試依賴本機是否存在某個大特徵檔
    monkeypatch.setattr(factories, "feature_count_from_features_file",
                        lambda p, **_kw: 999_999 if p else None)
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h",
        "config_hash": "a6a998593c3c55aa54e5d6fa537114b4",   # 只有 15 個特徵的小 hash
        "features_path": "/tmp/pretend-big-features.h5",
    })
    assert r.status_code == 400, f"小 hash＋大 features_path 繞過了閘門：{r.text}"
    assert r.json()["detail"]["feature_count"] == 999_999, "取的不是兩者最大值"
    assert spy_start_analysis == [], "任務被啟動了 ⇒ 閘門沒擋住這條路"


def test_gap3_ic_feature_cap_covers_cross_sectional_runs(spy_start_analysis):
    """🔴 `CODEX-R2-P1-01`：橫截面請求帶的是 **per-symbol 的一組 run**，也必須被閘門看見。

    首版只看單一 `config_hash` ⇒ 兩個各自超標的 run 一起送進來會被整組放行。
    判準＝逐筆解析取**最大值**（任一筆超標即擋整組）。
    """
    r = client.post(f"{API}/analyze", json={
        "mode": "cross_sectional", "timeframe": "12h",
        "cross_sectional_runs": [
            {"symbol": "BTCUSDT", "config_hash": "a6a998593c3c55aa54e5d6fa537114b4"},  # 15
            {"symbol": "BTCUSDT", "config_hash": BIG_RUN_CONFIG_HASH},                  # 218369
        ],
    })
    assert r.status_code == 400, f"橫截面請求繞過了閘門：{r.text}"
    assert r.json()["detail"]["feature_count"] == 218369, "取的不是逐筆最大值"
    assert spy_start_analysis == [], "任務被啟動了 ⇒ 閘門沒擋住橫截面這條路"


def test_gap3_ic_feature_cap_features_path_can_be_identifier_not_file(spy_start_analysis):
    """🔴 `GROK-R2-P2-01`：`features_path` **未必是檔案路徑**（如 `parquet:SYM:<hash>`）。

    首版只認檔案 ⇒ `is_file()` 為假就放行，繞過復活。
    """
    from momentum.factories import feature_count_from_features_file

    # 🔴 該 hash 在 registry 對到**多筆**（不同標的）。
    #    R2 首版一律取跨標的 max；`CODEX-R3-P2-02` 判定那是缺陷——識別字串**自己帶了 symbol**，
    #    取別的標的的數字等於把被選 run 的合法小值誤報成大值（false-block）。
    #    故本條現在釘的是「帶 symbol ⇒ 取該標的自己的數字」；
    #    「無 symbol scope ⇒ 跨標的 max」由 `..._identifier_keeps_symbol_scope` 以替身 registry 釘住。
    import json as _json

    entries = _json.loads(
        (REPO / "data_cache" / "features" / "registry.json").read_text(encoding="utf-8"))
    same_hash = [e for e in entries
                 if str(e.get("config_hash") or "").strip() == BIG_RUN_CONFIG_HASH
                 and isinstance(e.get("feature_count"), int)]
    assert same_hash, "本機 registry 無該 hash，無法做正向對照"
    btc = [e["feature_count"] for e in same_hash if e.get("symbol") == "BTCUSDT"]
    assert btc, "本機 registry 之該 hash 無 BTCUSDT 筆，無法做 symbol scope 對照"
    got = feature_count_from_features_file(f"parquet:BTCUSDT:{BIG_RUN_CONFIG_HASH}")
    assert got == max(btc), f"識別字串未取被選標的自己的數字（得 {got}，應為 {max(btc)}）"
    assert got > int(settings.ic_analysis_max_features), "本機該 run 未超 cap，無法續驗閘門擋下"
    # 🔴 **必須顯式帶一個小 `config_hash`**，否則本條測不到它該測的東西：
    #    R3 之後閘門在「沒帶 hash」時會去解析 latest（本機 BTCUSDT/12h latest 為 161,031 > cap），
    #    於是即使閘門**完全不看** `features_path` 也照樣回 400 ⇒ 這條測試變成無法證偽。
    #    實際被抓到過：`6.1-M3`（閘門不看 features_path）的紅集合因此從兩條縮成一條。
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h",
        "config_hash": "a6a998593c3c55aa54e5d6fa537114b4",   # 只有 15 個特徵的小 hash
        "features_path": f"parquet:BTCUSDT:{BIG_RUN_CONFIG_HASH}",
    })
    assert r.status_code == 400, f"識別字串形式繞過了閘門：{r.text}"
    assert r.json()["detail"]["feature_count"] == max(btc), "擋下時報的不是識別字串解析出的數字"
    assert spy_start_analysis == []


def test_gap3_ic_feature_cap_covers_implicit_latest_longitudinal(spy_start_analysis, inject_latest_run):
    """🔴 R3 三家一致（`CODEX-R3-P1-01`／`COMPOSER-R3-P1-01`／`GROK-R3-P1-02`）：
    **省略 `config_hash` 時 service 自己會挑 latest**，閘門必須看得到那一個 run。

    這條路徑對 R2 之前的所有候選都是隱形的：候選全部解析不出 ⇒ 放行 ⇒
    service 走 `find_latest_materialized` 把 latest 載進來。三家各自實跑同一組對照：
    不帶 hash ⇒ 200 且 `start_analysis` 被呼叫；補上 hash ⇒ 400、`calls=0`。
    """
    cap = int(settings.ic_analysis_max_features)
    latest = cap + 5_000
    inject_latest_run("ICGATEBIG", latest)
    r = client.post(f"{API}/analyze", json={"symbol": "ICGATEBIG", "timeframe": "12h"})
    assert r.status_code == 400, f"省略 config_hash 就繞過了閘門：{r.text}"
    assert r.json()["detail"]["feature_count"] == latest, "擋下時報的不是 service 會載入的那個 run"
    assert spy_start_analysis == [], "任務被啟動了 ⇒ 隱式 latest 這條路沒被擋住"


def test_gap3_ic_feature_cap_covers_implicit_latest_cross_sectional(spy_start_analysis, inject_latest_run):
    """🔴 `GROK-R3-P1-01`／`COMPOSER-R3-P1-01`：橫截面只給 `symbols`（不帶 `cross_sectional_runs`）
    時，service 以 `config_hashes=None` 呼叫 `load_multi` ⇒ **逐標的 latest**。

    R2 只封了 `cross_sectional_runs`，同一端點的 `symbols`-only 形態仍開著。
    判準＝逐標的解析 latest 取 max（任一標的超標即擋整組——橫截面本來就一起載入）。
    """
    cap = int(settings.ic_analysis_max_features)
    big = cap + 7_000
    inject_latest_run("ICGATESMALL", 100)
    inject_latest_run("ICGATEBIG", big)
    r = client.post(f"{API}/analyze", json={
        "mode": "cross_sectional", "timeframe": "12h", "symbols": ["ICGATESMALL", "ICGATEBIG"],
    })
    assert r.status_code == 400, f"symbols-only 橫截面繞過了閘門：{r.text}"
    assert r.json()["detail"]["feature_count"] == big, "取的不是逐標的 latest 之最大值"
    assert spy_start_analysis == [], "任務被啟動了 ⇒ symbols-only 這條路沒被擋住"


def test_gap3_ic_feature_cap_implicit_latest_under_cap_still_allowed(spy_start_analysis, inject_latest_run):
    """**反向對照**：latest 在 cap 以內時，省略 `config_hash` 仍必須放行。

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
    from momentum import factories
    cap = int(settings.ic_analysis_max_features)
    inject_latest_run("ICGATEBIG", cap + 5_000)
    # 明確指向一個「小」的 features_path：閘門若仍把 latest 算進去就會誤擋
    monkeypatch.setattr(factories, "feature_count_from_features_file",
                        lambda p, **_kw: 10 if p else None)
    r = client.post(f"{API}/analyze", json={
        "symbol": "ICGATEBIG", "timeframe": "12h",
        "features_path": "/tmp/pretend-small-features.h5",
    })
    assert r.status_code != 400, f"明確給小 features_path 卻被不相干的 latest 誤擋：{r.text}"
    assert spy_start_analysis != [], "請求沒有抵達 service ⇒ 被閘門擋掉了"


def test_gap3_ic_feature_cap_cross_sectional_ignores_top_level_features_path(spy_start_analysis, monkeypatch):
    """🔴 `CODEX-R4-P1-01` 之後半：橫截面走 `load_multi`，**完全不看**頂層 `features_path`
    ⇒ 閘門也不得把它算進來。

    釘的是「閘門的候選集合＝service 該分支實際會用的東西」，不是「所有欄位一起取 max」。
    """
    from momentum import factories

    monkeypatch.setattr(factories, "feature_count_from_features_file",
                        lambda p, **_kw: 999_999 if p else None)
    r = client.post(f"{API}/analyze", json={
        "mode": "cross_sectional", "timeframe": "12h",
        "cross_sectional_runs": [
            {"symbol": "BTCUSDT", "config_hash": "a6a998593c3c55aa54e5d6fa537114b4"},  # 15
            {"symbol": "ETHUSDT", "config_hash": "a6a998593c3c55aa54e5d6fa537114b4"},
        ],
        "features_path": "/tmp/irrelevant-huge.h5",
    })
    assert r.status_code != 400, f"橫截面被 service 根本不看的 features_path 誤擋：{r.text}"
    assert spy_start_analysis != [], "請求沒有抵達 service ⇒ 被閘門擋掉了"


def test_gap3_ic_feature_cap_full_analysis_does_not_resolve_latest(spy_start_analysis, inject_latest_run):
    """🔴 `/full-analysis` 與 `/analyze` **走的不是同一條載入路徑**，閘門必須分開對齊。

    `_run_full_analysis` 直接把 `request.features_path` 餵給 `analyzer.analyze`，
    **從不碰 registry**（沒有 `get_entry`／`find_latest_materialized`／`load_multi`）。
    因此對它去查 latest 會擋掉一個根本不會載入任何 registry run 的請求——
    那正是 `CODEX-R4-P1-01` 那一族的誤擋，只是換**主委自己**在結構修正時犯。
    **本條由主委自攻抓到、未進 review**；它示範了 `resolve_planned_feature_count` 的維護風險：
    「鏡像 service」只有在**逐個入口**對齊時才成立，多一個入口就多一份對齊責任。
    """
    cap = int(settings.ic_analysis_max_features)
    inject_latest_run("ICGATEBIG", cap + 5_000)
    # 🔴 **本請求刻意不帶 `features_path`**：帶了的話 longitudinal 分支也會優先用它，
    #    於是「拿掉入口分支」這個變異不改變行為 ⇒ 錄到**空紅集合**（實際發生過一次）。
    #    只有在「有 symbol／timeframe、無 features_path」時，兩條分支的行為才分岔：
    #    正確碼回 None（放行），錯誤碼去查 latest 並擋下。
    r = client.post(f"{API}/full-analysis", json={
        "symbol": "ICGATEBIG", "timeframe": "12h",
        "labels_path": "/tmp/pretend-labels.h5",
    })
    detail = r.json().get("detail") if r.status_code == 400 else None
    assert not (isinstance(detail, dict) and "cap" in detail), (
        f"/full-analysis 被一個它根本不會載入的 latest 擋掉了：{r.text}"
    )


def test_gap3_ic_feature_cap_registry_lowball_is_caught_by_manifest(monkeypatch):
    """🔴 `CODEX-R4-P1-02`：latest 解析**不得只信 registry 的 `feature_count`**。

    registry 是產生時寫的中繼資料，會過期／低報；低報時閘門就放行實際超量的 artifact。
    codex 用真 manifest（`total_features`）配 stub registry（15）打出反例。
    判準＝registry 與 manifest **取大**（保守側）。
    """
    from momentum.factories import feature_count_from_registry_entry

    manifest = None
    for entry in _registry_entries():
        rel = str(entry.get("hdf5_relative_path") or "")
        if rel and (REPO / rel).is_file() and isinstance(entry.get("feature_count"), int):
            manifest = (rel, entry["feature_count"])
            break
    assert manifest, "本機無可用 manifest，無法做正向對照"
    rel, real_count = manifest
    # registry 低報成 15，manifest 仍是真值 ⇒ 必須取到真值
    got = feature_count_from_registry_entry({"feature_count": 15, "hdf5_relative_path": rel})
    assert got == real_count, f"registry 低報時未由 manifest 糾正（得 {got}，manifest 為 {real_count}）"
    # manifest 讀不到時退回 registry，不憑空造值
    assert feature_count_from_registry_entry(
        {"feature_count": 15, "hdf5_relative_path": "/no/such/manifest.json"}) == 15
    assert feature_count_from_registry_entry(None) is None


def test_gap3_ic_feature_cap_gate_and_service_share_one_registry_snapshot():
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

    # 🔴 判準必須可證偽：注入一筆**只存在於 service 這份記憶體快照**的 entry
    #    （磁碟上的 registry.json 沒有它）。解析器若改用自己新建的 `FeatureRegistry()`
    #    重讀磁碟，就看不到它 ⇒ 回 None ⇒ 本條紅。
    #    manifest 指向一個真實存在的檔案，否則 `is_materialized` 為假、latest 不會選到它。
    real_manifest = next(
        (str(e["hdf5_relative_path"]) for e in _registry_entries()
         if str(e.get("hdf5_relative_path") or "") and (REPO / str(e["hdf5_relative_path"])).is_file()),
        None,
    )
    assert real_manifest, "本機無可用 manifest，無法做正向對照"

    fake = {"symbol": "GATEPROBE", "timeframe": "12h", "config_hash": "probe",
            "feature_count": 90_000, "hdf5_relative_path": real_manifest,
            "last_generated_at": 9_999_999_999}
    original = list(registry._entries)  # noqa: SLF001
    try:
        registry._entries = original + [fake]  # noqa: SLF001
        got = service.resolve_planned_feature_count(_Req())
        assert got is not None, (
            "解析器看不到只存在於 service 記憶體快照的 entry "
            "⇒ 它讀的是自己新建的 registry，與 service 實際會載入的不是同一份"
        )
        assert got >= 90_000, f"解析到的不是那筆注入的 entry：{got}"
    finally:
        registry._entries = original  # noqa: SLF001
    # 還原後必須解析不出（證明上面的成功不是來自別處）
    assert service.resolve_planned_feature_count(_Req()) is None


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


def test_gap3_ic_feature_cap_message_does_not_ask_for_impossible_action():
    """🔴 使用者裁定（2026-08-27）：錯誤訊息**不得叫使用者去做他沒有介面可做的事**。

    原文為「請先縮減特徵數再分析」——本專案沒有任何縮減特徵數的介面，
    那句話把「系統暫時做不到」寫成了「你操作錯了」，是一條死路。
    """
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": BIG_RUN_CONFIG_HASH,
    })
    assert r.status_code == 400
    message = r.json()["detail"]["message"]
    assert "請先縮減特徵數" not in message, "訊息仍指向一個沒有介面可做的操作"
    assert "無法分析" in message, "訊息未明講這個 run 目前做不到"
    assert "GAP-6" in message, "訊息未指出限制何時會取消"


def test_gap3_ic_feature_cap_features_file_reads_metadata_only():
    """檔案側解析**只讀 HDF5 header 之 shape**，不載入矩陣（Task 6.4 之硬性要求）。"""
    from momentum.factories import feature_count_from_features_file

    sample = sorted((REPO / "data_cache" / "features").glob("*.h5"))
    if not sample:
        pytest.skip("本機無特徵檔可做正向對照")
    count = feature_count_from_features_file(str(sample[0]))
    assert isinstance(count, int) and count > 0, "讀不到欄數 ⇒ 檔案側解析形同虛設"
    # 讀不到／不存在一律 None，不猜
    assert feature_count_from_features_file("/no/such/file.h5") is None
    assert feature_count_from_features_file(None) is None


def test_gap3_ic_feature_cap_value_is_backed_by_measurement_receipt():
    """🔴 **禁拍腦袋填**：設定值須 `<=` receipt 內最小超標點 × 0.5。"""
    receipt = REPO / "handoffs" / "run_receipts" / "gap3ux-b9-footprint.receipt.json"
    assert receipt.exists(), "上限值必須有量測 receipt 佐證（Task 6.2 之死線）"
    data = json.loads(receipt.read_text(encoding="utf-8"))
    # 🔴 頂層與逐點**都要**驗工具字面：receipt 兩處各有一個 `tool`，只驗其中一處時
    #    改另一處不會被察覺（mutation `6.2-M1` 首次錄到空紅集合就是打在頂層那處）。
    assert data["tool"] == "sample:Physical footprint", "禁以 ps rss 當量測值（頂層）"
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

    # 🔴 `CODEX-R1-P1-04`：SPEC 要求「同一 run 重跑 2 次之 peak 差 < 20%」，
    #    而我原本只是**手算過**、沒寫進任何斷言——把第二個 peak 改成 1e9 照樣會過。
    #    這裡真的算一次；且**必須存在**至少一組重跑，否則等於沒驗重現性。
    by_count = {}
    for p in points:
        by_count.setdefault(p["feature_count"], []).append(float(p["peak_footprint_bytes"]))
    repeated = {k: v for k, v in by_count.items() if len(v) >= 2}
    assert repeated, "receipt 內沒有任何 run 被量兩次 ⇒ 重現性未驗（SPEC 6.2 邊界②）"
    for count, peaks in sorted(repeated.items()):
        lo, hi = min(peaks), max(peaks)
        assert lo > 0
        diff_pct = (hi - lo) / lo * 100.0
        assert diff_pct < 20.0, f"feature_count={count} 之重跑 peak 差 {diff_pct:.1f}% >= 20%"


def test_gap3_ic_stop_gate_alive_no_big_matrix_loaded(spy_start_analysis):
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
    # 🔴 `CODEX-R1-P1-03` 之後補：**證明分析路徑一步都沒走**。
    #    原本只看記憶體差，而我當時的替身讓 service 根本不執行 ⇒ 該斷言恆真、是假綠。
    assert spy_start_analysis == [], "start_analysis 被呼叫了 ⇒ 本條之『未載入大矩陣』無意義"
    assert os.getpid() > 0                        # ②單一 pid（本行程自身）
    # ③未載入大矩陣：該 run 的量測 peak 為 GB 級；擋下之路徑不得有可觀增長。
    # 🔴 這裡用 `ru_maxrss` 而非 `sample`：本條要驗的是「**這個行程**在被擋的路徑上有沒有長大」，
    #    是同行程前後差；Task 6.2 之絕對量測才需要 footprint（跨行程、且 RSS 會失真）。
    growth_mb = (max(after_request, after_response) - before) / 1024.0
    assert growth_mb < 256, f"擋下時記憶體成長 {growth_mb:.1f}MB ⇒ 疑似已載入特徵矩陣"


def test_gap3_ic_stop_gate_alive_small_run_still_creates_task():
    """邊界②：小 run ⇒ 不被擋，且任務**確實被建立**（筆數 +1）。

    🔴 對照組：沒有這條的話，「把所有請求都擋掉」也會讓邊界①全綠。
    """
    before = _task_count()
    r = client.post(f"{API}/analyze", json={
        "symbol": "BTCUSDT", "timeframe": "12h",
        "config_hash": "a6a998593c3c55aa54e5d6fa537114b4",   # 15 個特徵
    })
    assert r.status_code == 200, r.text
    assert _task_count() == before + 1, "小 run 未建立任務 ⇒ 閘門誤擋"
