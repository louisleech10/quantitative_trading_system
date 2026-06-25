# IC Gatekeeper Run 選擇器重做 — MANIFEST（扁平 ID，逐 Phase）

> 日期 2026-06-23 ｜ 級別：大（命中 (b)(d)）｜ 來源：handoffs/20260623-ic-run-selector-DESIGN.md §6 定案 D1-D7
> 用途：SPEC/TODO coverage_check 比對基準。每個 `[X-n]` 須落進 SPEC 與 TODO，缺項=churn。

## Phase A — 後端：單 run config_hash 端到端（global/event）
- [A-0] 動工前跑 baseline 寫 `tests/fixtures/ic_run_selector_baseline.json`（向後相容+消歧+ML caller 三組）
- [A-1] ICAnalyzeRequest 加 `config_hash: Optional[str]`（ic_models.py:44）
- [A-2] ic_analysis_service 單 run 路徑：config_hash 有值→`registry.get(symbol,tf,config_hash)`；無值→find_latest + log warn（:130-142）
- [A-3] feature_library `_load_internal`/`load` 加 optional config_hash，預設維持 find_latest（:43）

## Phase B — 後端：橫截面批次消歧
- [B-1] ICAnalyzeRequest 加 `cross_sectional_runs: Optional[List[CrossRunRef{symbol,config_hash}]]`
- [B-2] load_multi 加 optional `config_hashes: Dict[symbol,hash]`，預設 find_latest（feature_library.py:169；ML caller cross_symbol_training_service:38 須相容）
- [B-3] ic_analysis_service 橫截面路徑：有 cross_sectional_runs→傳 map 給 load_multi（:111）

## Phase C — 後端：list_features / 特徵清單 timeframe 一致性（codex C1）
- [C-1] list_features / features_path 解析補 timeframe，消除 legacy(base/symbol/hash) vs V2(features/symbol/tf/hash) 不一致（ic_analysis_service:305-324；feature_reader:218）
- [C-2] fetchAvailableFeatures 後端來源由 (symbol,tf,config_hash) 解析（list endpoint 加 query params）
- [C-2b] 前端 list 鏈：useICAnalysis.fetchAvailableFeatures + page effect 依賴 + route client 改吃 (symbol,tf,config_hash)

## Phase D — 前端：單 run 選擇器（global/event）
- [D-1] types：ICAnalysisConfig 加 config_hash；RunInfo 加 training_timeframes?（types.ts:285,597,1956）
- [D-2] page.tsx：fetchRuns() on mount + runsLoading/runsError/empty 三態（取代/並存 fetchRegistry，:92-93,231-233）
- [D-3] ICConfigPanel：global/event 改批次分組 Run 下拉（group=batch_alias，leaf=formatRunLabel），選定寫 config.{symbol,timeframe,config_hash}；刪 registryEntries symbol/tf 邏輯（:56-96,167-194）
- [D-4] ICConfigPanel：完全移除三個貼路徑欄輸入（:150-164）
- [D-5] 啟動 gate：未選 run/config_hash 不齊→runDisabled（:113-121）
- [D-6] useICAnalysis：payload 送 config_hash；hasLibrarySelection 納入 config_hash（:126-178）

## Phase E — 前端：橫截面批次選擇器（D2 決策）
- [E-1] ICConfigPanel：cross_sectional 改「選一個批次」→ cross_sectional_runs=[{symbol,config_hash}]（同批共享 tf）；取代共同 tf 交集邏輯（:60-84,201-211）
- [E-2] useICAnalysis：橫截面 payload 送 cross_sectional_runs；crossSectionalFeatureCount anchor run 規則（page.tsx:116-159）

## Phase F — training_timeframes 標籤（低風險，最後）
- [F-1] list_runs 讀 run manifest 補 training_timeframes（feature_factory_service.py:811）
- [F-2] 選擇器 leaf 顯示「1h(+12h)」

## Phase G — 測試（真實 3 批次，驗證保真度鐵律）
- [G-1] 後端：選批次X的BTC vs 批次Y的BTC → 分析結果(feature 集合 hash/row_count)不同（證 config_hash 真消歧）
- [G-2] 後端：不送 config_hash → 結果 == find_latest 舊行為（向後相容 golden）
- [G-3] 後端：load_multi ML 訓練 caller（無 config_hashes）行為不變
- [G-4] 前端：選擇器→config→payload config_hash/cross_sectional_runs 端到端 wiring 測試
- [G-5] fetchAvailableFeatures 失敗→setError（非靜默清空）測試

## 風險錨點（SPEC §RISK 須對應）
- (b) 跨模組共用路徑：feature_library.load/load_multi 多消費者（IC + ML 訓練 + browser）
- (d) 分析真實性：選錯 run = 分析非預期資料；config_hash 消歧為正確性核心
- 回退：後端欄位 optional 可單獨 revert；前端選擇器替換包元件層；find_latest 預設行為不變
