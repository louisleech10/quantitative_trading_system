# DECOUPLE-P3 TODO　(v1 / DRAFT / 基於 docs/DECOUPLE_P3_SPEC.md / 2026-07-14)

## 階段 1 SPEC 索引(100% 覆蓋追溯)
| ID | SPEC 原文節錄(≤30字) | 本檔位置 |
|---|---|---|
| Task 1 | 「route 層 hardware 下沉 service」 | Task 1.1 |
| Task 2 | 「hardware_utils 正名(不搬家)」 | Task 1.2 |
| Task 3 | 「_registry 穿透公開 API 化」 | Task 1.3 |
| T1a-d/T2a-b/T3a-c | 驗證命令(T1d=AST import allow-set) | 各 Task |
- 合計:3 Task、驗證 ID 9(T1a-d/T2a-b/T3a-c)。RISK-HIT: b。無 Golden(§N)/無 mutation(§N,轉發測試自可證偽)/無環境變數。

## §0 全域規則與約束
- 解耦 7 條 canonical=CLAUDE.md;本票=**層次衛生整理,零行為變更**;R1-R7 檢查邏輯不碰,`bash scripts/check_decoupling.sh` 修後必須仍全綠 exit 0。
- **不碰 `scripts/decouple_allowlist.md`**(已雙戳記,改=scanner 紅)。
- 零行為變更紀律:回傳值/例外型別與訊息/log 全不變;Task 3 夾註釋逐字保留。
- 不新增 service→service import(R4);新 service 檔只 import momentum 白名單模組+標準庫。
- 防假綠:不放寬既有斷言;兩輪斷路器。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B1 | Task 1.1/1.2/1.3 | 互獨立 | 一次派工,各自獨立 commit | 小-中 |

- B1 驗收 Gate:T1a-d/T2a-b/T3a-c 全 PASS+`bash scripts/check_decoupling.sh` 全綠+`pytest tests/api tests/momentum -q` 無新紅(inventory 慣例 revert)。
- 派工 prompt:「讀 docs/DECOUPLE_P3_TODO.md §0+Task 1.1-1.3(冷啟動自足),實作+自跑驗證,stdout 入 handoffs/DECOUPLE-P3-RECEIPT.md;不跑 git commit(主委代);結構化收尾。」

## Phase 1 — 三件整理(完成後:route 零 momentum 直呼、hardware 文案誠實、api 零 `_registry` 穿透)

### Task 1.1 — route hardware 下沉(SPEC ref:Task 1;r2 依三家 BLOCKING 重寫)
- 輸入/輸出:輸入=現行 routes/config.py L23-184+`tests/test_hardware_api.py`;輸出=新 service+薄 route+改 patch 目標的測試。
- 實作要點:①service 函式名=**`build_hardware_info(data_cache_path) -> Dict[str, Any]`**(**禁 `get_hardware_info`**——route 既有同名 async handler,同名 import 會遞迴/被覆蓋);②**全量下沉**:hardware_utils 三符號 import+`_build_cpu_info` 等 psutil 輔助+env 解析段全搬 service;route handler 保留 async 定義+讀 `settings.data_cache_path` 傳參+try/log/HTTPException(L182-184 語意原樣);③service 不 import api settings/其他 service/api.core.config;④**applied_settings 註解與實作不一致=已知現況,禁順手修正**(零行為;receipt 記 known-issue);⑤`tests/test_hardware_api.py:43-142` 三測的 monkeypatch(`config_route.psutil/get_memory_tier/get_tier_config`)改 patch `hardware_info_service` namespace,斷言不變。
- 修改檔案:新建 `api/services/hardware_info_service.py`;`api/routes/config.py`;`tests/test_hardware_api.py`(僅 patch 目標)。既有 caller:route handler+該測試檔。
- 不可做:不改回應 schema/欄位/例外語意;不修 applied_settings;不動 hardware_utils;不碰 manifest;service 禁 import api.services.*/api.core.config。
- 邊界:(1) psutil 缺席 → fallback 同修前(test_hardware_api 釘);(2) tier 解析異常 → 500 語意不變。
- 風險緩解:golden JSON 等值。
- 驗證:**T1a** `pytest tests/test_hardware_api.py -q` 0 failed(斷言不得放寬);**T1b** `grep -c "momentum" api/routes/config.py` 輸出 `0`;**T1c** 回應等值 golden:**改前**以 mock 固定環境實跑 endpoint 存完整 JSON dict 於 receipt → 改後同環境重跑逐欄 `==`(兩份輸出都貼,禁指認逃逸);**T1d** AST import allow-set:python 對新 service 檔 ast.parse,走訪全部 Import/ImportFrom 節點,斷言無任何目標命中 `api.services*`/`api.core.config`/`api.routes*`(含 `from api import services` 包層級形式與別名),違者印節點+exit 1;命令與 stdout 貼 receipt。

### Task 1.2 — hardware_utils 正名(SPEC ref:Task 2)
- 輸入/輸出:輸入=現 docstring;輸出=誠實 docstring。
- 實作要點:①module docstring 改「Feature Factory hardware-tier 運維政策表(l65_workers/l3_persist_mode/cgsa_shard_bytes 等 keyed by RAM tier)」;②註明 package 錯位=已知債,搬遷選項見 ROADMAP DECOUPLE-TRIAGE-2 附帶;③零 code 變更。
- 修改檔案:`momentum/FeatureEngineering/utils/hardware_utils.py`(docstring only)。
- 不可做:不搬檔;不改任何函式/常數;不碰 manifest。
- 邊界:(1) 零邏輯行 diff(T2a 機檢);(2) import 面不變。
- 風險緩解:⊘。
- 驗證(r2):**T2a** AST dump 等值——python 對 `git show HEAD:momentum/FeatureEngineering/utils/hardware_utils.py` 與修後檔各 ast.parse、剝 module docstring、`ast.dump` 字串 `==` → 印 `IDENTICAL`(receipt 貼命令+輸出);**T2b** `bash scripts/check_decoupling.sh` 全綠 exit 0。

### Task 1.3 — `_registry` façade(SPEC ref:Task 3)
- 輸入/輸出:輸入=feature_library 現公開面;輸出=兩公開方法+ic_analysis 改呼叫+新測試。
- 實作要點(r2):①`FeatureLibrary.get_entry(self, symbol: str, timeframe: str, config_hash: str) -> Optional[Dict[str, Any]]` = `return self._registry.get(symbol, timeframe, config_hash)`;②`FeatureLibrary.find_latest_materialized(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]` = 純轉發;③docstring 契約(codex ADV-5 裁決):「無寫方法之轉發 façade;不承諾回傳物 immutability(get 底層回 copy、find_latest 回內部原 dict=既有行為,零行為票不加 defensive copy;mutable-leak 既有現況註記)」;④`api/services/ic_analysis_service.py` L183/L193 改公開方法;**夾註釋逐字原位保留**;⑤新測試(mock registry 語境):參數 assert_called_once_with 轉發+回傳 `is` mock 回傳物+None 傳透(`is` 斷言僅限 mock,不對真 registry 宣稱)。
- 修改檔案:`momentum/FeatureEngineering/feature_library.py`、`api/services/ic_analysis_service.py`(僅 L183/L193 兩行)、新建 `tests/momentum/test_feature_library_registry_facade.py`。既有 caller:穿透僅此兩處(SPEC receipt 已證)。
- 不可做:不暴露 add/remove/_persist;不改 ValueError 訊息;不動 `_load_features_for_transforms`;不做參數轉換/過濾。
- 邊界:(1) entry=None → 上游 `raise ValueError(run not found…)` 行為不變(既有/新測試釘);(2) mock 斷言純轉發(改壞參數順序 → 測試 FAIL,自可證偽)。
- 風險緩解:轉發 mock 測試。
- 驗證:**T3a** `grep -rn "_feature_library._registry" api --include="*.py"` 輸出 0 行(tests/ 內既有 2 處穿透不在 scope,不動);**T3b** `pytest tests/momentum/test_feature_library_registry_facade.py tests/api/test_ic_transform_feature_loading.py -q` 0 failed;**T3c** 修前先跑 `pytest tests/api -k "ic" -q` 記 baseline → 修後對照無新紅(receipt 貼兩份輸出)。

### Phase 1 測試 + Phase Gate
- 單元:T1c 等值/T3b 轉發。整合:scanner 全綠+`pytest tests/api tests/momentum -q` 無新紅。邊界:psutil 缺席/entry=None。效能:⊘。mutation:⊘(§N,轉發測試自可證偽)。
- Phase Gate:T1a-d/T2a-b/T3a-c 全 PASS。

## 階段 3 自檢(0 FAIL)
- 追溯:3 Task/驗證 9 全對應 ✓。深度:要點≥3+簽名/檔案到函式/邊界≥2/驗證可證偽 ✓;新測試檔在修改檔案 ✓。語義:三 Task 互獨立無同檔衝突(1.1 route+新 service;1.2 hardware_utils;1.3 feature_library+ic_analysis)✓。全棧:純後端層次整理,⋅跳過。錨點:§0/§B/驗證·邊界·不可做 ✓。

## 階段 4 Frozen 前 handoff
SPEC=docs/DECOUPLE_P3_SPEC.md TODO=docs/DECOUPLE_P3_TODO.md FOCUS=零行為變更保證(route 回應等值/façade 純轉發)+不碰已戳記 manifest
狀態:**Frozen**(2026-07-14 三家閉合 FROZEN-OK:grok/composer r2、codex r3,見 handoffs/DECOUPLE-P3-ADV-{CODEX,COMPOSER,GROK}.md)
