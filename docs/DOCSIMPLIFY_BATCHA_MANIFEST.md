# DOCSIMPLIFY Batch A — A00 disposition manifest

> Frozen against `docs/ARCHITECTURE.md` at 2026-07-13. Line spans are inclusive and refer to the pre-A0/A1/A2 file. `—（不適用）` is an explicit non-applicable value, not a missing field. A parent H3 row inventories the capability identity; child rows inventory every H4, table, and fenced code block independently.

## A00.1 disposition inventory

### 點名必留（inventory 範圍外）

| ID | 原 heading | line-span 或 content-hash | 分類{刪\|外移\|留} | 可重生證據命令(刪) | 目的 file#anchor(外移) | 不可重生理由(留) |
|---|---|---:|---|---|---|---|
| KEEP-ARTIFACT-L65 | Artifact Contract Table — L6.5 raw/processed 順序 why | L365–374（A00 主 inventory 範圍外） | 留 | —（不適用） | —（不適用） | `L6.5_pre → L7_raw → IC Gate → L6.5_post → L7_processed` 的順序、格式與 canonical path 是 SPEC 點名 contract；明列為 out-of-scope-keep，後續 A1/A2 不得因範圍外而省略 |

### §636–999：目錄結構

| ID | 原 heading | line-span 或 content-hash | 分類{刪\|外移\|留} | 可重生證據命令(刪) | 目的 file#anchor(外移) | 不可重生理由(留) |
|---|---|---:|---|---|---|---|
| DIR-API-H3 | Backend (`api/`) | L638–731 | 留 | —（不適用） | —（不適用） | domain ownership 與關鍵入口 `api/main.py` 須留作頂層導航；細節樹另列可刪 |
| DIR-API-CODE | `api/` 完整樹碼塊 | L640–730 | 刪 | `find api -print \| sort` | —（不適用） | —（不適用） |
| DIR-CORE-H3 | Core Engines (`momentum/`) | L732–878 | 留 | —（不適用） | —（不適用） | domain ownership、`factories.py`/`protocols.py` 關鍵入口屬架構導航 |
| DIR-CORE-CODE | `momentum/` 完整樹碼塊 | L734–877 | 刪 | `find momentum -print \| sort` | —（不適用） | —（不適用） |
| DIR-FE-H3 | Frontend (`frontend/src/`) | L879–989 | 留 | —（不適用） | —（不適用） | frontend domain ownership 與入口導航不可只由樹狀輸出表達 |
| DIR-FE-CODE | `frontend/src/` 完整樹碼塊 | L881–988 | 刪 | `find frontend/src -print \| sort` | —（不適用） | —（不適用） |
| DIR-DATA-H3 | Data (`data_cache/`) | L990–999 | 留 | —（不適用） | —（不適用） | data lifecycle/ownership 與禁止 fake/cross-symbol contamination 是邊界語意 |
| DIR-DATA-CODE | `data_cache/` 樹碼塊 | L991–996 | 刪 | `find data_cache -print \| sort` | —（不適用） | —（不適用） |

### §1000–1852：已實現功能

共同重生命令縮寫：`MOD=<module>; test -e "$MOD"`（模組存在）；`rg -n '^@(router|app)\\.(get|post|put|patch|delete)' api/routes/<route>.py`（route decorators）；`find frontend/src -type f | sort`（前端元件）；`find tests -type f | sort`（測試 inventory）。表內仍逐列給出 authoritative source。

| ID | 原 heading | line-span 或 content-hash | 分類{刪\|外移\|留} | 可重生證據命令(刪) | 目的 file#anchor(外移) | 不可重生理由(留) |
|---|---|---:|---|---|---|---|
| CAP-01 | ✅ 1. Case Search 系統 | L1002–1036 | 留 | —（不適用） | —（不適用） | 能力 ID/ownership 留在能力索引；細節逐列處置 |
| CAP-01-OV | 功能概述 | L1004–1006 | 留 | —（不適用） | —（不適用） | 搜索 workflow 與輸入/結果 ownership 語意 |
| CAP-01-MODEL | 數據模型 | L1007–1021 | 留 | —（不適用） | —（不適用） | API_SPEC `#數據模型` 僅有 request shape，沒有 6+24+2 搜索參數 taxonomy；目的地契約不足，不外移 |
| CAP-01-MODEL-CODE | `SearchConfig` taxonomy 碼塊 | L1008–1020 | 留 | —（不適用） | —（不適用） | `rg` 只能找到 class，不能完整重生 6 個觸發、24 個未來表現、2 個反例參數的分類與研究語意 |
| CAP-01-MODULE | 核心模組 | L1022–1028 | 刪 | `find momentum/DataExtraction api/services api/routes -type f | sort` | —（不適用） | —（不適用） |
| CAP-01-STRAT | 已實現的搜索策略 | L1029–1036 | 留 | —（不適用） | —（不適用） | 正反例、區間與時間序列切分屬研究資料可得性/防洩漏語意 |
| CAP-02 | ✅ 2. K 線數據系統 | L1037–1072 | 留 | —（不適用） | —（不適用） | 資料 ownership/lifecycle 能力 ID |
| CAP-02-ACCESS | KlineDataService — 統一資料存取層 | L1039–1053 | 留 | —（不適用） | —（不適用） | cache-first、缺口下載、symbol/timeframe 隔離是資料 lifecycle 契約 |
| CAP-02-ACCESS-CODE | KlineDataService usage 碼塊 | L1044–1052 | 刪 | `rg -n 'class KlineDataService|def get_klines' api/services` | —（不適用） | —（不適用） |
| CAP-02-STORAGE | KlineStorageService — HDF5 讀寫操作 | L1054–1065 | 留 | —（不適用） | —（不適用） | HDF5 schema/相容與 merge failure 語意 |
| CAP-02-STORAGE-CODE | HDF5 methods 碼塊 | L1055–1064 | 刪 | `rg -n '^ *def (write_klines\|append_klines\|read_klines\|read_klines_around_timestamp\|check_data_integrity\|get_data_quality_report\|get_stats)' api/services/kline_storage_service.py` | —（不適用） | —（不適用） |
| CAP-02-BATCH | 批量下載 heading | L1066 | 留 | —（不適用） | —（不適用） | 保留能力索引入口；lifecycle 與 API 子列分開處置 |
| CAP-02-BATCH-LIFECYCLE | 批量下載服務與 lifecycle | L1067–1068 | 留 | —（不適用） | —（不適用） | 平行批量、時間重疊偵測/合併、進度追蹤是資料 lifecycle/failure 語意，不能由檔名完整重生 |
| CAP-02-BATCH-API | 批量下載 API | L1069 | 外移 | —（不適用） | `docs/API_SPECIFICATION.md#2-case-management-api` | `batch-download` 與 `download-status/{task_id}` 端點已在該實際 H2 驗真；不以章名推測不存在的 Kline anchor |
| CAP-03 | ✅ 3. 圖表分析系統 | L1073–1090 | 留 | —（不適用） | —（不適用） | 能力索引 ID |
| CAP-03-PANEL | 多面板同步圖表 | L1075–1078 | 刪 | `find frontend/src/components -type f | rg 'Chart|Panel'` | —（不適用） | —（不適用） |
| CAP-03-SIGNAL | 策略信號標記 | L1079–1083 | 留 | —（不適用） | —（不適用） | 混合服務 ownership、API 與動態買賣箭頭語意；寬泛 `rg` 不能完整重生，端點另由 API_SPEC `#4-chart-signals-api` 維護 |
| CAP-03-DATA | 圖表數據 | L1084–1090 | 外移 | —（不適用） | `docs/API_SPECIFICATION.md#3-chart-data-api` | endpoint/schema 維護責任且目的章已驗真 |
| CAP-04 | ✅ 4. Optuna 參數優化系統 | L1091–1143 | 留 | —（不適用） | —（不適用） | 能力索引 ID；目標函數與 failure semantics 子列保留 |
| CAP-04-OBJ | 優化目標函數（雙密度 v2.0 公式） | L1093–1103 | 留 | —（不適用） | —（不適用） | 量綱、目標方向及版本相容是數值契約，不能以模組 inventory 完整重生 |
| CAP-04-OBJ-CODE | 目標函數公式碼塊 | L1094–1102 | 留 | —（不適用） | —（不適用） | 公式 why/量綱契約，無單一 docs canonical destination |
| CAP-04-OPT | 支持 5 種優化器 | L1104–1106 | 刪 | `rg -n 'TPESampler|CmaEsSampler|RandomSampler|GridSampler|NSGA' momentum api` | —（不適用） | —（不適用） |
| CAP-04-FAIL | 容錯機制 | L1107–1109 | 留 | —（不適用） | —（不適用） | pruning/retry/exception 分類屬 failure semantics |
| CAP-04-WS | WebSocket 即時通訊 | L1110–1114 | 外移 | —（不適用） | `docs/API_SPECIFICATION.md#websocket-api` | WebSocket protocol canonical 目的章存在 |
| CAP-04-MOD | 核心模組 | L1115–1119 | 刪 | `find momentum/Optimization api/services -type f | sort` | —（不適用） | —（不適用） |
| CAP-04-API | API 端點（核心 + 分析共 17 個） | L1120–1143 | 外移 | —（不適用） | `docs/API_SPECIFICATION.md#7-optimization-api-core`；`#8-optimization-analysis-api` | decorators 與兩個 API H2 均驗真 |
| CAP-05 | ✅ 5. 優化結果視覺化系統 | L1144–1161 | 留 | —（不適用） | —（不適用） | 能力索引 ID |
| CAP-05-TABLE | 組件/功能表 | L1148–1158 | 刪 | `find frontend/src/components -type f | sort` | —（不適用） | —（不適用） |
| CAP-06 | ✅ 6. 信號密度分析系統 | L1162–1176 | 留 | —（不適用） | —（不適用） | 能力索引 ID |
| CAP-06-CALC | 核心計算 | L1164–1169 | 留 | —（不適用） | —（不適用） | 正反例密度定義及分數量綱屬數值語意 |
| CAP-06-MOD | 核心模組 | L1170–1176 | 留 | —（不適用） | —（不適用） | 同段混合引擎/服務 ownership 與兩個 Signal Analysis API；檔名搜尋不能完整重生邊界語意，端點 canonical 目的章為 `#6-signal-analysis-api` |
| CAP-07 | ✅ 7. 多指標計算引擎 | L1177–1189 | 留 | —（不適用） | —（不適用） | 能力索引 ID |
| CAP-07-SOURCE | 數據源支持 (7 種) | L1179–1181 | 刪 | `rg -n 'DataSource|data_sources' momentum api config` | —（不適用） | —（不適用） |
| CAP-07-ENGINE | 指標引擎 | L1182–1189 | 留 | —（不適用） | —（不適用） | 「無未來函數驗證」是 look-ahead invariant，不能由檔案樹完整重生；span 不再吃入 CAP-08 H3 |
| CAP-08 | ✅ 8. 特徵工程系統 | L1190–1209 | 留 | —（不適用） | —（不適用） | 能力索引 ID |
| CAP-08-OV | 功能概述 | L1192–1194 | 留 | —（不適用） | —（不適用） | L1193 明列 IC-First `L7_raw + L7_processed` 順序；特徵輸入/輸出 ownership 與 pipeline lifecycle |
| CAP-08-MOD | 核心模組 | L1195–1204 | 留 | —（不適用） | —（不適用） | V2 canonical `raw|processed` path schema 與 legacy HDF5 向後相容是 contract；檔案樹不可重生，API 子項後續可 pointer 至 API_SPEC |
| CAP-08-IND | 特徵指標 | L1205–1209 | 刪 | `find momentum/FeatureEngineering -type f | sort` | —（不適用） | —（不適用） |
| CAP-09 | ✅ 9. XGBoost 分析系統 | L1210–1248 | 留 | —（不適用） | —（不適用） | 能力索引 ID |
| CAP-09-CORE | 核心能力 | L1212–1224 | 留 | —（不適用） | —（不適用） | Purged CV/OOT/漂移等防洩漏與時間可得性 contract |
| CAP-09-CORE-TABLE | 功能/模組表 | L1213–1223 | 留 | —（不適用） | —（不適用） | Purged CV、OOT、PSI、跨標的驗證等防洩漏能力集合是跨邊界 invariant；`find` 只能重生檔名 |
| CAP-09-SVC | 服務層 | L1225–1229 | 刪 | `find api/services -type f | rg 'xgboost|shap|pattern'` | —（不適用） | —（不適用） |
| CAP-09-API | API 路由（21 個端點） | L1230–1248 | 外移 | —（不適用） | `docs/API_SPECIFICATION.md#10-pattern-analysis-api-xgboost--lightgbm` | endpoint/schema canonical H2 已存在 |
| CAP-10 | ✅ 10. Pattern 管理系統 | L1249–1271 | 留 | —（不適用） | —（不適用） | 能力索引 ID |
| CAP-10-OV | 功能概述 | L1251–1253 | 留 | —（不適用） | —（不適用） | Pattern lifecycle/ownership 語意 |
| CAP-10-MOD | 核心模組 heading | L1254 | 留 | —（不適用） | —（不適用） | 子列拆分 core inventory 與 API canonical destination |
| CAP-10-MOD-CORE | Pattern 核心模組/服務 inventory | L1255–1259 | 刪 | `find momentum/Analysis api/services -type f \| rg 'pattern_(definition\|extractor\|storage\|validator\|management_service)'` | —（不適用） | —（不適用） |
| CAP-10-MOD-API | Pattern CRUD API | L1260–1271 | 外移 | —（不適用） | `docs/API_SPECIFICATION.md#11-pattern-management-api` | 8 個 CRUD endpoint 已在目的章逐一驗真，不再以模組 inventory 當重生證據 |
| CAP-11 | ✅ 11. ML Pipeline 系統 | L1272–1281 | 留 | —（不適用） | —（不適用） | 訓練→驗證→報告 lifecycle 與時間切分契約 |
| CAP-12 | ✅ 12. 配置管理系統 | L1282–1293 | 留 | —（不適用） | —（不適用） | config single-source/precedence/ownership 契約 |
| CAP-13 | ✅ 13. 案例匯入系統 | L1294–1305 | 留 | —（不適用） | —（不適用） | import schema、驗證與 failure semantics |
| CAP-14 | ✅ 14. IC 特徵篩選系統（Phase 2 IC Gatekeeper） | L1306–1490 | 留 | —（不適用） | —（不適用） | IC pipeline 是跨階段資料品質契約 |
| CAP-14-OV | 系統概述 | L1308–1310 | 留 | —（不適用） | —（不適用） | Gatekeeper ownership/輸入輸出語意 |
| CAP-14-MOD | 核心模組（18 個） | L1311–1374 | 留 | —（不適用） | —（不適用） | 八階段與三層 config precedence 必留；漂移計數可由子表刪 |
| CAP-14-MOD-T1 | IC 核心模組表 | L1315–1328 | 留 | —（不適用） | —（不適用） | `ic_filter_orchestrator` 八階段與 `Default < YAML < API` precedence 是點名契約 |
| CAP-14-MOD-T2 | 模型驗證模組表 | L1332–1338 | 留 | —（不適用） | —（不適用） | OOT/CV gap/PSI 時間與資料可得性語意 |
| CAP-14-MOD-T3 | API 層模組表 | L1342–1347 | 外移 | —（不適用） | `docs/API_SPECIFICATION.md#14-ic-analysis-api` | endpoint/schema canonical H2 已存在 |
| CAP-14-MOD-T4 | 前端元件計數表 | L1351–1356 | 刪 | `find frontend/src/app/ic-analysis frontend/src/components/ic-analysis frontend/src/hooks frontend/src/store -type f | sort` | —（不適用） | —（不適用） |
| CAP-14-PIPE | 八階段篩選管線 | L1375–1397 | 留 | —（不適用） | —（不適用） | Stage 0–7 ordering 是點名 lifecycle/資料品質契約 |
| CAP-14-PIPE-CODE | 八階段 ASCII pipeline 碼塊 | L1377–1396 | 留 | —（不適用） | —（不適用） | 精確 stage ordering 不可由單一 tree/route 完整重生 |
| CAP-14-IC | 三種 IC 方法 | L1398–1405 | 留 | —（不適用） | —（不適用） | 方法適用性與 robust trade-off 是 why |
| CAP-14-IC-TABLE | IC 方法比較表 | L1400–1404 | 留 | —（不適用） | —（不適用） | quant 方法選擇理由不可由程式 inventory 重生 |
| CAP-14-RED | 四種冗餘篩選演算法 | L1406–1414 | 留 | —（不適用） | —（不適用） | 算法適用情境及參數語意 |
| CAP-14-RED-TABLE | 冗餘算法表 | L1408–1413 | 留 | —（不適用） | —（不適用） | threshold 語意/適用場景是 contract/why |
| CAP-14-TEST | 測試套件（26 個測試檔案） | L1415–1433 | 刪 | `find tests -type f | rg 'ic|factor|redundancy|turnover|coverage' | sort` | —（不適用） | —（不適用） |
| CAP-14-TEST-TABLE | 測試數/行數/coverage 表 | L1417–1426 | 刪 | `pytest --collect-only -q` | —（不適用） | —（不適用） |
| CAP-14-ARCH | 架構特色 | L1434–1473 | 留 | —（不適用） | —（不適用） | Factory boundary、refilter cache 與 config precedence 是跨邊界 invariant |
| CAP-14-ARCH-CODE1 | Factory injection 碼塊 | L1448–1461 | 刪 | `rg -n 'create_ic_analyzer|I.*Analyzer' momentum/factories.py api/services` | —（不適用） | —（不適用） |
| CAP-14-ARCH-CODE2 | config precedence 碼塊 | L1464–1469 | 留 | —（不適用） | —（不適用） | `Default < YAML < API` 是點名 precedence 契約 |
| CAP-14-PERF | 效能表現 | L1474–1480 | 刪 | `find tests -type f | rg 'performance|benchmark|ic'` | —（不適用） | —（不適用） |
| CAP-14-TODO | 待開發（前端 UI） | L1481–1490 | 刪 | `find frontend/src -type f | rg 'ic-analysis|ICAnalysis'` | —（不適用） | —（不適用） |
| CAP-15 | ✅ 15. 雙引擎 ML 系統（Phase 3.7） | L1491–1549 | 留 | —（不適用） | —（不適用） | 能力索引與雙引擎相容 contract |
| CAP-15-ARCH | 架構概觀 | L1493–1508 | 留 | —（不適用） | —（不適用） | Protocol boundary 與比較 lifecycle |
| CAP-15-ARCH-CODE | 雙引擎 ASCII 架構碼塊 | L1495–1507 | 刪 | `find momentum/Analysis momentum/Optimization -type f | sort` | —（不適用） | —（不適用） |
| CAP-15-CORE | 核心元件 | L1509–1521 | 留 | —（不適用） | —（不適用） | `IModelTrainer` 向後相容與 objective boundary |
| CAP-15-CORE-TABLE | 核心元件表 | L1511–1520 | 留 | —（不適用） | —（不適用） | Protocol 方法集合/相容性屬 schema contract |
| CAP-15-API | API 層 | L1522–1530 | 外移 | —（不適用） | `docs/API_SPECIFICATION.md#15-dual-engine-ml-api-phase-37` | endpoint/schema canonical H2 已存在 |
| CAP-15-API-TABLE | API 層模組表 | L1524–1529 | 外移 | —（不適用） | `docs/API_SPECIFICATION.md#15-dual-engine-ml-api-phase-37` | 同上 |
| CAP-15-FE | 前端元件 | L1531–1541 | 刪 | `find frontend/src/components/pattern -type f | sort` | —（不適用） | —（不適用） |
| CAP-15-FE-TABLE | 前端元件表 | L1533–1540 | 刪 | `find frontend/src/components/pattern -type f | sort` | —（不適用） | —（不適用） |
| CAP-15-TEST | 測試覆蓋 | L1542–1549 | 刪 | `pytest --collect-only -q` | —（不適用） | —（不適用） |
| CAP-16 | ✅ 16. Feature Factory 特徵工程系統（Phase 1 + 1.5） | L1550–1614 | 留 | —（不適用） | —（不適用） | 核心 FF contract 集；點名語意不可丟失 |
| CAP-16-OV | 系統概述 | L1552–1554 | 留 | —（不適用） | —（不適用） | 七段式命名規範及增量生成 lifecycle 是點名契約 |
| CAP-16-LAYERS | 7 層 Pipeline 架構 | L1555–1568 | 留 | —（不適用） | —（不適用） | L6.5 raw→processed ordering/why 與 L7 label ordering |
| CAP-16-LAYERS-TABLE | Layer 0–7 表 | L1557–1567 | 留 | —（不適用） | —（不適用） | pipeline ordering、L6.5 preprocessing 位置是點名 why |
| CAP-16-CORE | 核心模組 | L1569–1576 | 刪 | `find momentum/FeatureEngineering -type f | sort` | —（不適用） | —（不適用） |
| CAP-16-EXT | Phase 1.5 擴充引擎 | L1577–1585 | 留 | —（不適用） | —（不適用） | prefix/命名 schema 與 preprocessing 相容語意 |
| CAP-16-EXT-TABLE | 擴充引擎/prefix 表 | L1579–1584 | 留 | —（不適用） | —（不適用） | prefix 是輸出 schema 相容契約 |
| CAP-16-L65 | L6.5 優化路徑 | L1586–1596 | 留 | —（不適用） | —（不適用） | native-tf、d_star key 與 raw/processed 順序為點名必留 |
| CAP-16-L65-TABLE | L6.5 四路徑表 | L1590–1595 | 留 | —（不適用） | —（不適用） | L1592 非主 TF 沿用主 TF d_star；L1593 per-column value fingerprint；不得以無 receipt 百分比替代契約 |
| CAP-16-GRAN | Feature Factory Granular Control heading | L1597 | 留 | —（不適用） | —（不適用） | 混合區段拆分為引擎 contract、API、前端 inventory、測試快照四列 |
| CAP-16-GRAN-ENGINE | granular 引擎/相容/warmup 契約 | L1598–1599、L1604 | 留 | —（不適用） | —（不適用） | `IndicatorDef.enabled` schema、`migrate_config()` 相容語意、per-indicator warmup/NaN 修復不在 API_SPEC，屬引擎 contract |
| CAP-16-GRAN-API | Preset/Batch-Toggle/Schema API | L1600–1602 | 外移 | —（不適用） | `docs/API_SPECIFICATION.md#19-feature-factory-granular-control-api` | 三組 endpoint/schema 已在目的章驗真；外移範圍不含 engine contract |
| CAP-16-GRAN-FE | granular 前端元件 inventory | L1603 | 刪 | `find frontend/src -type f \| rg 'LayerPanel\|IndicatorCheckbox\|CategorySection\|FeaturePreviewBar\|ConfigIOButtons'` | —（不適用） | —（不適用） |
| CAP-16-GRAN-TEST | `175 tests` 快照 | L1605–1606 | 刪 | `find tests -type f \| rg 'feature_factory\|granular\|indicator.*config' \| sort` | —（不適用） | —（不適用） |
| CAP-16-ARCH | 架構特色 | L1607–1614 | 留 | —（不適用） | —（不適用） | 七段式命名文法+相容理由、`force_regenerate`/增量生成語意為點名契約；完成徽章與測試數不保留 |
| CAP-17 | ✅ 17. IC 深度分析系統（Phase 2.4-2.12） | L1615–1642 | 留 | —（不適用） | —（不適用） | 能力索引及 OOS/時間語意 |
| CAP-17-OV | 系統概述 | L1617–1619 | 留 | —（不適用） | —（不適用） | deep-analysis lifecycle |
| CAP-17-MOD | 10 個深度分析模組 | L1620–1634 | 留 | —（不適用） | —（不適用） | rolling OOS、Net IC/成本等 quant semantics；模組計數本身可再生 |
| CAP-17-MOD-TABLE | 深度分析模組表 | L1622–1633 | 留 | —（不適用） | —（不適用） | 模組責任及 OOS/成本語意不可由檔名完整重生 |
| CAP-17-OTHER | 其他擴展功能 | L1635–1642 | 留 | —（不適用） | —（不適用） | skipped/failure 與結果 schema 相容語意 |
| CAP-18 | ✅ 18. 模型增強系統（Phase 3.5） | L1643–1677 | 留 | —（不適用） | —（不適用） | 能力索引與防洩漏方法 contract |
| CAP-18-OV | 系統概述 | L1645–1647 | 留 | —（不適用） | —（不適用） | validation lifecycle |
| CAP-18-CORE | 核心模組 | L1648–1658 | 留 | —（不適用） | —（不適用） | Walk-Forward/CPCV/adversarial leakage 語意 |
| CAP-18-CORE-TABLE | 模型增強模組表 | L1650–1657 | 留 | —（不適用） | —（不適用） | validation method semantics |
| CAP-18-API | API 端點 | L1659–1668 | 外移 | —（不適用） | `docs/API_SPECIFICATION.md#16-model-enhancement-api-phase-35` | endpoint/schema canonical H2 已驗真 |
| CAP-18-FE | 前端元件 | L1669–1677 | 刪 | `find frontend/src -type f | rg 'enhancement|Enhancement'` | —（不適用） | —（不適用） |
| CAP-19 | ✅ 19. Strategy 回測與優化系統（Phase 4） | L1678–1721 | 留 | —（不適用） | —（不適用） | 回測/部位 sizing 數值 contract |
| CAP-19-OV | 系統概述 | L1680–1682 | 留 | —（不適用） | —（不適用） | 信號→執行→metrics lifecycle |
| CAP-19-CORE | 核心模組 | L1683–1693 | 留 | —（不適用） | —（不適用） | 指標與 position sizing ownership/量綱 |
| CAP-19-CORE-TABLE | 回測核心模組表 | L1685–1692 | 留 | —（不適用） | —（不適用） | risk/position sizing contract |
| CAP-19-PROTO | 新 Protocol | L1694–1703 | 留 | —（不適用） | —（不適用） | 跨 domain Protocol boundary |
| CAP-19-PROTO-CODE | Protocol 碼塊 | L1695–1702 | 留 | —（不適用） | —（不適用） | interface schema/相容性 contract |
| CAP-19-OPTUNA | Optuna 重構 | L1704–1709 | 留 | —（不適用） | —（不適用） | objective plug-in ownership 與 backward compatibility |
| CAP-19-API | API 端點 | L1710–1714 | 外移 | —（不適用） | `docs/API_SPECIFICATION.md#17-hyperparameter-optimization-api-phase-4`；`#18-execution-optimization-api-phase-4` | endpoint/schema canonical H2 已驗真 |
| CAP-19-WS | WebSocket 新事件 | L1715–1721 | 外移 | —（不適用） | `docs/API_SPECIFICATION.md#websocket-api` | WS protocol canonical H2 已存在 |
| CAP-20 | ✅ 20. Feature Factory MultiTF 整合 + 多標的批次計算 | L1722–1809 | 留 | —（不適用） | —（不適用） | MultiTF/AlignmentMode 防 look-ahead 點名契約 |
| CAP-20-OV | 系統概述 | L1724–1728 | 留 | —（不適用） | —（不適用） | 多 TF 計算/對齊及多 symbol isolation lifecycle |
| CAP-20-ROUTE | MultiTF 路由策略 | L1729–1747 | 留 | —（不適用） | —（不適用） | 各 TF 先獨立計算再對齊的時間可得性契約 |
| CAP-20-ROUTE-CODE | MultiTF pseudo-code | L1731–1746 | 留 | —（不適用） | —（不適用） | ordering/對齊 contract，不以可能漂移的 pseudo implementation 作唯一來源 |
| CAP-20-ALIGN | AlignmentMode Paradigm | L1748–1761 | 留 | —（不適用） | —（不適用） | `OPEN_MINUS`/`CLOSE_TIME` 防 look-ahead 點名契約 |
| CAP-20-ALIGN-TABLE | AlignmentMode 表 | L1750–1753 | 留 | —（不適用） | —（不適用） | bar 可得時間定義 |
| CAP-20-ALIGN-CODE | AlignmentMode Enum 碼塊 | L1755–1760 | 留 | —（不適用） | —（不適用） | schema/相容性契約 |
| CAP-20-BATCH | FeatureFactoryBatchService 架構 | L1762–1794 | 留 | —（不適用） | —（不適用） | concurrency、TTL、per-symbol failure isolation lifecycle |
| CAP-20-BATCH-CODE | BatchService pseudo-code | L1764–1793 | 留 | —（不適用） | —（不適用） | task lifecycle/failure isolation contract |
| CAP-20-API | 已實作 API 端點 | L1795–1802 | 外移 | —（不適用） | `docs/API_SPECIFICATION.md#20-feature-factory-multitf--batch-api` | endpoint/schema canonical H2 已驗真 |
| CAP-20-API-TABLE | MultiTF/Batch endpoint 表 | L1796–1801 | 外移 | —（不適用） | `docs/API_SPECIFICATION.md#20-feature-factory-multitf--batch-api` | 同上；WS 另由 `#websocket-api` 核對 |
| CAP-20-TEST | Tests | L1803–1809 | 刪 | `find tests -type f | rg 'feature_factory|multi_tf|batch_generation' | sort` | —（不適用） | —（不適用） |
| CAP-21 | ✅ 21. L7 Storage 增強 | L1810–1831 | 留 | —（不適用） | —（不適用） | L7 tier/storage/cleanup lifecycle 點名契約 |
| CAP-21-SHARD | Sharded npy Storage + L7 Raw Streaming | L1812–1815 | 留 | —（不適用） | —（不適用） | raw→storage lifecycle、峰值記憶體 ownership |
| CAP-21-TIER | Hardware-Adaptive L7 Compression | L1816–1825 | 留 | —（不適用） | —（不適用） | hardware tier policy/跨 tier repeatability |
| CAP-21-TIER-TABLE | L7 tier/compression 表 | L1819–1824 | 留 | —（不適用） | —（不適用） | tier 選擇與壓縮 lifecycle 是點名 contract |
| CAP-21-CLEAN | IC-First raw/ Cleanup | L1826–1831 | 留 | —（不適用） | —（不適用） | cleanup 時序、per-part disk failure semantics |
| CAP-22 | ✅ 22. IC Engine Cache Hit Path | L1832–1838 | 留 | —（不適用） | —（不適用） | raw cleanup 後 cache-hit/重算決策 lifecycle 點名契約 |
| CAP-23 | ✅ 23. Feature Browser CGSA 優化 + FeatureTimeSeriesChart 重構 | L1839–1852 | 留 | —（不適用） | —（不適用） | CGSA 能力 ID 與冷快取 lifecycle |
| CAP-23-CGSA | Feature Browser CGSA 優化 | L1841–1845 | 留 | —（不適用） | —（不適用） | sampling quantile、parallel warmup、sync cap 500 的 CGSA/冷快取語意為點名必留 |
| CAP-23-CHART | FeatureTimeSeriesChart 重構 | L1846–1852 | 刪 | `find frontend/src -type f | rg 'FeatureTimeSeriesChart|feature.*chart'` | —（不適用） | —（不適用） |

## A00.2 route basename → API_SPEC stable H2 mapping

判定規則：以 `api/main.py` 的 mount prefix + route `APIRouter(prefix=...)` 組合所得公開 path 為 runtime 證據；API_SPEC Router 表與穩定 H2 是文件目的地。若 basename 未列，結果不是猜測的相近章，而是固定 fallback「讀 API_SPEC Router 表 + 人工確認」；在確認前標 `BLOCKED-scope` 且不得外移。

| fixture / route basename | 唯一穩定 API_SPEC H2（非序數引用） | 公開 path 判定 | 目的地契約驗真命令 | 結果 |
|---|---|---|---|---|
| `feature_factory` | `Feature Factory Granular Control API`；MultiTF/batch 子能力用 `Feature Factory MultiTF + Batch API` | canonical `/api/v1/features`; ARCH 的 `/features/` 是 `feature_engineering.py` 局部 prefix，不是 FF 公開 prefix | `rg -n '路由.*feature_factory.py|/api/v1/features/(schema|generate|batch)' docs/API_SPECIFICATION.md api/routes/feature_factory.py` | 唯一依能力類型分流；PASS |
| `case_search` | `Case Search API` | `case_search.py` 為 `/search`，由 `api/main.py` mount `/api/v1`，組合後 `/api/v1/search`；以組合後 runtime path 為準 | `rg -n 'case_search.router|prefix="/api/v1"' api/main.py`; `rg -n '路由.*case_search.py|/api/v1/search/(execute|preview|task)' docs/API_SPECIFICATION.md`; `rg -n '@router\.(get|post|delete)' api/routes/case_search.py` | PASS |
| `optimization` | `Optimization API (Core)` | `/api/v1/optimization`，route prefix 已是完整公開 prefix | `rg -n '路由.*optimization.py|/api/v1/optimization/(tasks|strategies|trials)' docs/API_SPECIFICATION.md`; `rg -n '@router\.(get|post)' api/routes/optimization.py` | PASS |
| `optimization_analysis` | `Optimization Analysis API` | `/api/v1/optimization` | `rg -n '路由.*optimization_analysis.py|analysis/(importance|history|param-space)' docs/API_SPECIFICATION.md api/routes/optimization_analysis.py` | PASS |
| `feature_engineering` | `Feature Engineering API` | route 局部 `/features` + main mount `/api/v1` = `/api/v1/features`; 此項解釋 ARCH `/features/` 舊寫法 | `rg -n 'feature_engineering.router|prefix="/api/v1"' api/main.py`; `rg -n '路由.*feature_engineering.py|/api/v1/features' docs/API_SPECIFICATION.md` | PASS |
| `pattern_analysis` | `Pattern Analysis API (XGBoost / LightGBM)`；雙引擎 schema 用 `Dual-Engine ML API (Phase 3.7)` | `/api/v1/pattern-analysis`（main mount + local prefix） | `rg -n 'pattern_analysis.py|/api/v1/pattern-analysis|/model/|/lightgbm/' docs/API_SPECIFICATION.md api/routes/pattern_analysis.py` | PASS |
| `ic_analysis` | `IC Analysis API` | API_SPEC canonical `/api/v1/ic`; route decorator同值 | `rg -n '路由.*ic_analysis.py|/api/v1/ic' docs/API_SPECIFICATION.md api/routes/ic_analysis.py` | PASS |
| `model_enhancement` | `Model Enhancement API (Phase 3.5)` | `/api/v1/model-enhancement` | `rg -n '路由.*model_enhancement.py|/api/v1/model-enhancement' docs/API_SPECIFICATION.md api/routes/model_enhancement.py` | PASS |
| `hyperparameter_optimization` | `Hyperparameter Optimization API (Phase 4)` | runtime route 目前 `/api/v1/optimization`; API_SPEC Router 表宣稱 `/api/v1/hyperparameter-optimization`，存在漂移 | `rg -n 'prefix=|@router\.' api/routes/hyperparameter_optimization.py`; `rg -n 'hyperparameter_optimization.py|/api/v1/hyperparameter-optimization' docs/API_SPECIFICATION.md` | H2/端點內容存在，可作文件目的地；path 漂移另記，外移內容不得宣稱 runtime prefix 已一致 |
| `execution_optimization` | `Execution Optimization API (Phase 4)` | runtime route 目前 `/api/v1/optimization`; API_SPEC Router 表宣稱 `/api/v1/execution-optimization`，存在漂移 | `rg -n 'prefix=|@router\.' api/routes/execution_optimization.py`; `rg -n 'execution_optimization.py|/api/v1/execution-optimization' docs/API_SPECIFICATION.md` | H2/端點內容存在，可作文件目的地；path 漂移另記，外移內容不得宣稱 runtime prefix 已一致 |
| `unknown_new_route` | `讀 API_SPEC Router 表 + 人工確認` | 不推導、不 fuzzy-match | `rg -n '^### Router 註冊對照表|^\| .*unknown_new_route' docs/API_SPECIFICATION.md` | 明確 fallback；`BLOCKED-scope`，不得外移 |

### 「端點已在 API_SPEC」能力 assertion receipts

| manifest capability | API_SPEC 目的章 | endpoint/schema 真存在的命令 | disposition gate |
|---|---|---|---|
| CAP-02-BATCH-API | `Case Management API`（目前實際承載 Kline batch） | `rg -n '^## 2\. Case Management API|/api/v1/kline/(batch-download\|download-status)' docs/API_SPECIFICATION.md` | 兩端點均命中才外移；章名與內容責任不一致的既存漂移如實保留 |
| CAP-03-SIGNAL（僅 endpoint pointer） | `Chart Signals API` | `rg -n '^## 4\.|/api/v1/chart/(signals\|validate-strategy)' docs/API_SPECIFICATION.md` | endpoint 已驗真；服務/動態箭頭語意仍留，不整段外移 |
| CAP-03-DATA | `Chart Data API` | `rg -n '^## 3\. Chart Data API|/api/v1/chart/data|ChartDataResponse' docs/API_SPECIFICATION.md` | 有命中才外移 |
| CAP-04-API | `Optimization API (Core)` / `Optimization Analysis API` | `rg -n '^## [78]\.|/api/v1/optimization/tasks|analysis/importance' docs/API_SPECIFICATION.md` | 有命中才外移 |
| CAP-09-API | `Pattern Analysis API (XGBoost / LightGBM)` | `rg -n '^## 10\.|/api/v1/pattern-analysis' docs/API_SPECIFICATION.md` | 有命中才外移 |
| CAP-10-MOD-API | `Pattern Management API` | `rg -n '^## 11\.|/api/v1/patterns/(define\|list\|statistics\|\{pattern_id\}\|batch/delete-all)' docs/API_SPECIFICATION.md` | 8 個 CRUD endpoint 逐項命中才外移 |
| CAP-14-MOD-T3 | `IC Analysis API` | `rg -n '^## 14\.|/api/v1/ic|ICAnalysis(Request|Response)' docs/API_SPECIFICATION.md` | 有命中才外移 |
| CAP-15-API | `Dual-Engine ML API (Phase 3.7)` | `rg -n '^## 15\.|ModelTrainingRequest|LightGBMTrainingRequest' docs/API_SPECIFICATION.md` | 有命中才外移 |
| CAP-16-GRAN-API | `Feature Factory Granular Control API` | `rg -n '^## 19\.|/api/v1/features/(schema|config/batch-toggle|config/presets)' docs/API_SPECIFICATION.md` | 三個 API 命中才外移；`migrate_config`/warmup/`IndicatorDef` 因目的地 0 命中而留 |
| CAP-18-API | `Model Enhancement API (Phase 3.5)` | `rg -n '^## 16\.|/api/v1/model-enhancement' docs/API_SPECIFICATION.md` | 有命中才外移 |
| CAP-19-API | Hyperparameter / Execution Optimization H2 | `rg -n '^## (17|18)\.|hyperparameter_optimization.py|execution_optimization.py' docs/API_SPECIFICATION.md` | H2/schema 可外移；保留上述 runtime path 漂移註記 |
| CAP-20-API | `Feature Factory MultiTF + Batch API` | `rg -n '^## 20\.|/api/v1/features/(generate|batch)|force_regenerate' docs/API_SPECIFICATION.md` | 有命中才外移；`force_regenerate` lifecycle assertion仍在 ARCH contract 集保留 |

## Coverage lock

- H3 coverage source: `awk 'NR>=636&&NR<=1852 && /^### / {print NR ":" $0}' docs/ARCHITECTURE.md` → 4 directory H3 + 23 `### ✅` capability H3，全部有 `DIR-*` / `CAP-*` parent row。
- H4 coverage source: `awk 'NR>=636&&NR<=1852 && /^#### / {print NR ":" $0}' docs/ARCHITECTURE.md` → 每一輸出 heading 均有對應 child row。
- fenced-code coverage source: `awk 'NR>=636&&NR<=1852 && /^```/ {print NR ":" $0}' docs/ARCHITECTURE.md` → 每一成對 fence 均有 `*-CODE` row。
- table coverage source: `awk 'NR>=636&&NR<=1852 && /^\|/ {print NR ":" $0}' docs/ARCHITECTURE.md` → 每個連續 table block 均有 `*-TABLE` / `*-T1..T4` row。
- 點名必留 lock: KEEP-ARTIFACT-L65（L365–374 out-of-scope-keep，完整 raw/processed Artifact Contract）、CAP-16-L65-TABLE（native-tf + per-column value fingerprint）、CAP-16-ARCH（force_regenerate/增量 + 七段命名）、CAP-08-OV/CAP-16-LAYERS（inventory 內的 lifecycle/ordering）、CAP-20-ROUTE/CAP-20-ALIGN（MultiTF/防 look-ahead）、CAP-14-PIPE/CAP-14-ARCH-CODE2（八階段 + 三層 precedence）、CAP-21/CAP-22（tier/cache-hit lifecycle）、CAP-23-CGSA（CGSA）全部分類為「留」。

## r2 review-lock 修正 receipts（2026-07-13 實跑）

| finding / audit | 實跑命令 | receipt | manifest 處置 |
|---|---|---|---|
| CAP-16-GRAN 混合責任 | `rg -c 'migrate_config\|warmup lookup\|IndicatorDef' docs/API_SPECIFICATION.md`；另查 §19 三 API | engine needles 各 0；schema/batch-toggle/presets 分別命中 L1378/L1469/L1517 | ENGINE 留、API 外移、FE/TEST 以可重生 inventory 刪 |
| Artifact Table 點名必留 | `sed -n '365,374p' docs/ARCHITECTURE.md` | 10 行含 L7_raw、L7_processed、IC selection、manifest 路徑契約 | 新增 KEEP-ARTIFACT-L65 out-of-scope-keep |
| CAP-08-MOD | `sed -n '1195,1204p' docs/ARCHITECTURE.md` | L1198 V2 path；L1199 legacy 向後相容 | 整列改留 |
| CAP-01 taxonomy 淨刪 | `rg -n 'positive_negative_ratio\|time_separation_days\|migrate_config' docs/API_SPECIFICATION.md` | 0 命中；`SearchConfigRequest` 只在 L114/L1881 | MODEL 與 CODE 均改留 |
| CAP-09 防洩漏表 | `sed -n '1213,1223p' docs/ARCHITECTURE.md`；`find momentum/Analysis -type f \| sort` | 表含 Purged CV/OOT/PSI/跨標的；find 只列 72 個路徑 | TABLE 改留 |
| storage 假重生 | `rg -n '^ *def (write_klines\|append_klines\|read_klines\|read_klines_around_timestamp\|check_data_integrity\|get_data_quality_report\|get_stats)' api/services/kline_storage_service.py` | 7/7 方法命中 L61/L122/L167/L215/L498/L527/L558 | 修正 CAP-02-STORAGE-CODE 命令 |
| span bleed | `nl -ba docs/ARCHITECTURE.md \| sed -n '1177,1191p'` | CAP-07 separator 結束 L1189；CAP-08 H3 起於 L1190 | CAP-07/CAP-07-ENGINE 終點改 L1189 |
| 其餘 API challenge | `rg -n '^## (2\. Case Management\|4\. Chart Signals\|6\. Signal Analysis\|11\. Pattern Management)|batch-download|download-status|chart/(signals\|validate-strategy)|signal-analysis/(density\|preview-window)|/api/v1/patterns/' docs/API_SPECIFICATION.md` | Kline 2、Chart 2、Signal 2、Pattern 8 個 endpoints 命中 | CAP-02/CAP-10 拆出 API 外移；CAP-03/CAP-06 混合契約保守留 |

### 全部「刪」列重生命令 audit

以下命令均以 `set -o pipefail` 實跑，exit 0；括號為輸出行數。命令可重生 inventory，但不被用來取代 why/schema/lifecycle（該類列已改「留」）。

- 目錄樹：DIR-API `find api -print | sort`（114）；DIR-CORE（256）；DIR-FE（357）；DIR-DATA（11802）。
- 模組/方法：CAP-01-MODULE（85）；CAP-02-ACCESS（1）；CAP-02-STORAGE（7）；CAP-04-OPT（24）；CAP-04-MOD（47）；CAP-05-TABLE（216）；CAP-07-SOURCE（222）；CAP-08-IND（91）；CAP-09-SVC（5）；CAP-10-MOD-CORE（5）；CAP-14-ARCH-CODE1（9）；CAP-15-ARCH-CODE（83）；CAP-16-CORE（91）。
- 前端 inventory：CAP-03-PANEL（91）；CAP-14-MOD-T4（52）；CAP-14-TODO（34）；CAP-15-FE/CAP-15-FE-TABLE（各 39）；CAP-16-GRAN-FE（5）；CAP-18-FE（1）；CAP-23-CHART（1）。
- 測試 inventory：CAP-14-TEST（141）；CAP-14-PERF（120）；CAP-20-TEST（26）；CAP-16-GRAN-TEST（26）。`source venv/bin/activate && pytest --collect-only -q` 對 CAP-14-TEST-TABLE/CAP-15-TEST 兩次皆 exit 0（各 4255 行輸出）；故 r1 reviewer 當時的 numba cache 紅在本次環境未重現。
