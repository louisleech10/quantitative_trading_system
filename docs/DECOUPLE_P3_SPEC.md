# DECOUPLE-P3 — 解耦 P3 三件整理 — SPEC

> 來源 PLAN/診斷：handoffs/20260713-DECOUPLE-TRIAGE-RECONCILE.md §D-3　|　日期：2026-07-14　|　對應 TODO：docs/DECOUPLE_P3_TODO.md

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：中(三件皆 contained,但 Task 3 碰 IC run-selector 路徑——純委派,行為零變)。
- **命中高風險原則**：(b) 跨模組共用路徑(feature_library 公開面/route-service 邊界)。零數值/ML 行為變更(全部同義改寫/加委派層)。
- RISK-HIT: b
- §G 於 §N 登記;adversarial 照中管線必跑。

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**(receipt ×4)：
  - FACT-RECEIPT: `sed -n '18,40p' api/routes/config.py` → route 層直接 `from momentum.FeatureEngineering.utils.hardware_utils import TIER_THRESHOLDS, get_memory_tier, get_tier_config`(Claude 實跑 2026-07-14)。
  - FACT-RECEIPT: `sed -n '180,196p' api/services/ic_analysis_service.py` → `_registry` 穿透兩處:L183 `self._feature_library._registry.get(symbol, timeframe, config_hash)`、L193 `…find_latest_materialized(symbol, timeframe)`;夾註釋(run-selector 消歧語意)必須原樣保留(Claude 實跑 2026-07-14)。
  - FACT-RECEIPT: `grep -n "def " momentum/FeatureEngineering/feature_library.py` → 公開面=list_available/load/load_for_training/load_multi/ensure_fresh,無 get_entry/find_latest 類方法;`feature_registry.py` 有 `get`(L164)/`find_latest_materialized`(L152)公開方法(Claude 實跑 2026-07-14)。
  - FACT-RECEIPT: `grep -rn "_feature_library._registry" api --include="*.py"` → 僅 ic_analysis_service 兩處(穿透面全貌)(Claude 實跑 2026-07-14)。
- **待使用者確認**：無(RECONCILE §D-3 已列三件;hardware「不搬家只正名」=技術取捨,依 grok triage 論證「遷 core 搬不掉 FF 政策本質」+搬家會作廢剛完成的 manifest 雙戳記,搬家選項列 DECOUPLE-TRIAGE-2 附帶再議)。
- **已確認結果**：`2026-07-14 使用者指示「照順序完成三段」`。

## §C 約束（不重抄，引用 + 只列本任務相關）
- **零行為變更**:三件全部=加委派層/搬 import 位置/改文案;任何回傳值/例外/log 語意都不得變。
- **不碰 manifest**:`scripts/decouple_allowlist.md` 已雙戳記,本票不得改(改=戳記失效 scanner 紅);Task 1 新 service 檔 import hardware_utils 仍在 R3 掃描根(services)內、且 module 在白名單 → scanner 維持綠(實跑驗證)。
- Task 3 委派方法=唯讀 façade;**不得**暴露 registry 寫入面(add/remove/_persist);L183-193 夾註釋逐字保留。
- 不新增 service→service import(R4);route→service import 合法。

## §G Golden / Baseline
- 移 §N(零行為變更;由既有測試+委派等值測試承擔)。

## §P Phase 與依賴

### Phase 1 — 三 Task(互獨立,各自 commit)

**Task 1 — route 層 hardware 下沉 service(r2 依三家 BLOCKING 重寫)**
- 目標:routes/config.py 不再直接 import momentum 具體工具;route 變薄 handler。檔案:新建 `api/services/hardware_info_service.py`;改 `api/routes/config.py`;**改 `tests/test_hardware_api.py`(monkeypatch 改指 service namespace,r2 入 scope——三家一致 BLOCKING)**。
- 改法(r2 凍結呼叫圖):①service 函式命名 **`build_hardware_info(data_cache_path) -> Dict[str, Any]`**(禁用 `get_hardware_info`,route 既有同名 async handler 會遞迴——三家一致);②**全量下沉**:hardware_utils 三符號+`_build_cpu_info` 等 psutil 輔助+env 解析段(route L29-158 相關塊)全搬 service;route handler 保留 async 定義+`settings.data_cache_path` 取值傳參+try/except+logger+HTTPException(L182-184 語意原樣);③service **不 import api settings**(data_cache_path 由 route 注入)、不 import 其他 service;④**applied_settings 註解與實作不一致=已知現況,本票禁「順手修正」**(零行為鐵律;列 receipt known-issue);⑤psutil try/except fallback 原樣搬。
- 既有 caller:route handler;`tests/test_hardware_api.py:43-142` 三測(monkeypatch `config_route.psutil/get_memory_tier/get_tier_config` → 改 patch service namespace)。
- 驗證(r2):`pytest tests/test_hardware_api.py -q` 0 failed(=hardware endpoint 真契約,含 500/psutil fallback);**回應等值 golden**:改前先實跑 endpoint(mock 固定環境)存 JSON dict 於 receipt,改後同環境重跑逐欄 `==`(禁「receipt 指認」逃逸);`grep -c "momentum" api/routes/config.py` 輸出 `0`;`grep -cE "from api\.services\.|import api\.services" api/services/hardware_info_service.py` 輸出 `0`(R4 手動 gate,scanner R4 grep 有 import 形式盲區——列 follow-up)。
- 邊界:(1) psutil 缺席 → fallback 值同修前(test_hardware_api 既有測試釘);(2) tier 解析異常 → HTTPException 500 語意不變。
- 不可做:不改回應 schema/欄位;不修 applied_settings 語意;不動 hardware_utils;不碰 manifest;不 import api.core.config 進 service。

**Task 2 — hardware_utils 正名(不搬家)**
- 目標:消「純硬體偵測」誤導文案。檔案:`momentum/FeatureEngineering/utils/hardware_utils.py`(僅 docstring)。
- 改法:module docstring 改為「Feature Factory hardware-tier 運維政策表(workers/persist/shard 等 keyed by RAM tier);package 位置錯位為已知債,搬遷選項見 ROADMAP DECOUPLE-TRIAGE-2 附帶」;不改任何 code。
- 驗證(r2,原 grep 可繞——codex 實證 `+TIER_THRESHOLDS = …` 不命中):**AST dump 等值 gate**——`python -c` 對修前(git show HEAD:path)與修後各 `ast.parse` 後剝除 module docstring 再 `ast.dump` 比對,輸出 `IDENTICAL` 才過;另 diff hunk 人工確認僅落 docstring;`bash scripts/check_decoupling.sh` 仍全綠 exit 0。
- 邊界:(1) docstring 變更不影響任何 import/測試;(2) 不動 TIER_THRESHOLDS 值。
- 不可做:不搬檔;不改函式;不碰 manifest。

**Task 3 — `_registry` 穿透公開 API 化**
- 目標:ic_analysis_service 不再摸 `_feature_library._registry`。檔案:`momentum/FeatureEngineering/feature_library.py`(加兩公開方法)、`api/services/ic_analysis_service.py` L183/L193、新測試 `tests/momentum/test_feature_library_registry_facade.py`。
- 改法:FeatureLibrary 加 `get_entry(self, symbol, timeframe, config_hash) -> Optional[Dict]` = `return self._registry.get(symbol, timeframe, config_hash)`;`find_latest_materialized(self, symbol, timeframe) -> Optional[Dict]` = 同名純轉發;**契約措辭(r2,codex ADV-5 裁決)**:docstring 標「無寫方法之轉發 façade;**不承諾回傳物 immutability**(registry.get 回 copy、find_latest_materialized 回內部原 dict=既有行為,本票零行為不加 defensive copy;mutable-leak 為既有現況註記)」。ic_analysis_service 兩處改呼叫公開方法;**夾註釋逐字保留原位**。
- 既有 caller:api 穿透僅此兩處(receipt 已證;tests 另有 2 處穿透=既有測試自身,不在本票 scope,composer ADV-9 核實)。
- 驗證(r2):`grep -rn "_feature_library._registry" api --include="*.py"` 輸出 0 行;新測試(**mock registry 語境限定**):兩方法參數逐一轉發(mock assert_called_once_with)+回傳 `is` mock 回傳物+None 傳透;`pytest tests/api/test_ic_transform_feature_loading.py tests/momentum/test_feature_library_registry_facade.py -q` 0 failed;修前先跑 `pytest tests/api -k "ic" -q` 記 baseline,修後對照無新紅(receipt 兩份輸出)。
- 邊界:(1) entry=None 路徑(run not found ValueError)行為不變;(2) 公開方法不做任何轉換/過濾(純轉發,mock 測試釘)。
- 不可做:不暴露 registry 寫入面;不改 run-selector 邏輯/例外訊息;不動 `_load_features_for_transforms`。

## §V 驗證策略與邊界測試目錄
- mutation(§N 登記豁免理由):零行為變更票,委派等值由 mock 轉發測試釘(改壞轉發參數 → 測試必 FAIL,天然可證偽);不另設 mutant。
- 測試層級:單元(Task 1 回應等值/Task 3 façade 轉發)、整合(scanner 全綠+既有 pytest)、邊界(psutil 缺席/entry=None)。
- 防假綠:不得放寬既有斷言;review 方 diff 三檔確認零邏輯變更(Task 2)與純轉發(Task 3)。

## §R 回退
- 三 Task 獨立 commit 可單獨 revert;零 schema/數據變更。

## §N N/A 登記
- §G:N/A — 零行為/數值變更(委派+文案+import 搬位);等值由 mock 轉發與回應等值測試承擔。
- §V mutation:N/A — 轉發測試本身即可證偽(改壞必 FAIL);無數值面。
- §V 邊界目錄全NaN/Inf/並發/OOM 等:N/A — 不適用。
