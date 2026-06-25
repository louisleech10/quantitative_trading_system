# IC Run 選擇器 — SPEC/TODO 雙家族 Adversarial Reconcile

> 2026-06-23 ｜ codex(GPT-5.5) + cursor(composer-2.5) 各一次 adversarial ｜ 合計 12 BLOCKING + 6 NON-BLOCKING
> 兩家 finding 都收齊 reconcile（大任務鐵律）。修補後才過 gate 派實作。

## BLOCKING 清單 + 定案修法（D=decision）

### 正確性 / Golden
- **codex#1 §G 消歧假綠**：原用 99ccd2cd(BTC **1h**) vs a08a292c(BTC **12h**)，tf 不同 → 即使忽略 config_hash 跑 find_latest 也過。
  **D-A1**：改用 registry 實存「同 symbol+同 tf+不同 hash」= **BTCUSDT 12h `1c4b825...`(無批次) vs `90f586...`(批次 a08a292c)**（registry.json 實見）。Golden 須 **assert 選中 run identity/path/config_hash == 請求值**，不只比 feature hash/row_count。
- **codex#5 G-3 沒驗真 ML caller**：真 caller=`CrossSymbolTrainingService.run_cross_symbol_validation()`，kwargs `for_training=True, allow_partial_training, feature_columns`。
  **D-A2**：G-3 改 spy/run 該 service，凍結 `load_multi` call kwargs + service 輸出摘要，非只直接 load_multi。
- **cursor §G baseline 未落地**：`tests/fixtures/ic_run_selector_baseline.json` 不存在。
  **D-A3**：新增 Task A-0「動工前跑 baseline 寫入 fixture」，列為 Batch1 前置 gate。

### §A 事實修正
- **codex#2 §A 主路徑寫錯**：ic_engine:145 是 `compute_ic_from_l7_raw` 內部 cache 路徑，**非 /analyze 主流程**。
  **D-A4**：§A 改正——/analyze 主路徑 = `entry.hdf5_relative_path → features_path → orchestrator.analyze`（ic_analysis_service:139-148 實見；entry path 已是 `data_cache/features/{sym}/{tf}/{hash}/feature_manifest.json` V2 完整含 tf+hash）。**A-2 只需 find_latest→registry.get，features 路徑機制不變、不需新 adapter**（驗證後確認比 codex 擔心的簡單）。

### Label ingestion（cursor 抓到的真實正確性 gap）
- **cursor#2 移除路徑欄後 labels/meta 鏈未覆蓋**：orchestrator(:1034) labels_df 空 + kline_reader=None → `InvalidInputError`；run_dir 無 labels 檔；現況靠手填 labels_path。
  **D-A5**：A-2/B-3 必須補 **kline_reader（`create_kline_cache`/`create_kline_storage_manager`）** 傳給 orchestrator，metadata 帶 symbol/tf → 從 kline 生 label。**實作端須用真實 run 驗單 run analyze 端到端完成**（驗證保真度鐵律，禁 mock）。**並須先驗證現況 symbol/tf-only 選擇是否本就會掛**（可能是既存 latent bug）。

### list_features / protocol 破壞面
- **codex#3 + codex#6 + cursor blast radius**：`FeatureReader.list_features(symbol, config_hash)` 是 protocol，feature browser(:129)、coverage analyzer(:186)、tests、2 段 `parquet:sym:hash` 都在用。改 3 參數會破。
  **D-A6**：**不改 protocol 2 參數簽名**；新增 `list_features_v2(symbol, tf, config_hash)` 或 `list_features(..., tf: Optional[str]=None)` 保留 legacy；C-1 補 **blast-radius 表**（IC list endpoint、feature_browser parquet reader、coverage_analyzer legacy、FeatureReader protocol/tests）。
- **cursor#6 + codex parquet key 格式未定案**：現碼要 3 段 `parquet:sym:hash`，4 段會 ValueError；DESIGN F3 還寫 2 段。
  **D-A7**：**定案用獨立 query params `(symbol, timeframe, config_hash)`**（不用塞 parquet key，避免前後端分叉）；刪 D-6「或送 parquet」歧義；更新 DESIGN F3。

### Phase 依賴 / 契約閉環
- **codex#4 Phase C 標可並行但驗證依賴 A**：C「== analyze 同源」需 A 完成。
  **D-A8**：Batch3 依賴改 Batch1（或「同源」驗證移 A+C 整合 gate）。
- **cursor#1 D-4 前端 list 鏈斷點**：page:235-244 + useICAnalysis:220-226 + route:77-80 硬綁 features_path，C-2 只改後端。
  **D-A9**：新增 Task **C-2b（前端 list 鏈）**：`fetchAvailableFeatures(symbol,tf,config_hash)` 改 hook + page effect 依賴 + route client；後端 route 加 query params。
- **cursor#3 batch key 不一致**：E-1 用 batch_id、D-3 用 batch_alias。
  **D-A10**：統一 stable key=**batch_id**（UI 顯示 batch_alias）；E-1 pickedBatchId。
- **cursor#4 icAnalysisStore 未列 D-1 blast radius**：defaultConfig 無新欄。
  **D-A11**：D-1 加 `icAnalysisStore::defaultConfig` config_hash/cross_sectional_runs；mode 切換清舊欄(cross_sectional_symbols)。
- **cursor#5 D-2 三態未落 props/檔**、**cursor#7 payload 未閉環**（handleRunAnalysis page:361-368、hasLibrarySelection 未納 config_hash）。
  **D-A12**：D-2 明寫 page 取三態+傳 panel+測試檔名；D-6/E-2 擴 scope 含 handleRunAnalysis、hasLibrarySelection/hasCrossSectionSelection。

## NON-BLOCKING（採納）
- D-5 啟動 gate（兩家一致）→ 已在 SPEC，補 vitest 兩模式。
- G-4/G-5 覆蓋偏窄 → 加 page 三態 + list 同源；featuresError 獨立欄（與 analyze error 不互蓋）。
- browse_ready 過濾 → D-3 邊界：僅 browse_ready 可選或選後 ensureBrowse。
- Batch4 過渡 cross 半套 → gate 註明 cross 驗收延 Batch5；D-3 後刪 fetchRegistry/registryEntries。

## 修法落地：新增/調整 Task
- 新增 **A-0**（baseline fixture）、**C-2b**（前端 list 鏈）。
- 調整 **§A**（D-A4）、**§G**（D-A1/A2/A3）、**A-2/B-3**（D-A5 kline_reader+labels）、**C-1**（D-A6/A7 protocol+key）、**Batch3 依賴**（D-A8）、**D-1**（D-A11 store）、**D-2/D-6/E-1/E-2**（D-A10/A12 key+閉環）。
