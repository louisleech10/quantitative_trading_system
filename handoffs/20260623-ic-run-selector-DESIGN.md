# IC Gatekeeper Run 選擇器 — 從根本重做（Claude 獨立設計版 v1）

> 日期 2026-06-23 ｜ 任務級別：大（命中 (b) 跨模組共用路徑、(d) 分析到非預期 run = 回測/分析真實性）
> 用途：規劃委員會 challenge 的底稿；非最終 SPEC。先寫自己一版再三方互審（feedback_claude_own_version）。

## 0. 問題陳述（使用者主訴 + 根因）
ic-analysis 從 Feature Library 選擇只能挑 symbol/timeframe，無法辨認是哪個批次；上方貼資料夾路徑不友善。
根因比 label 更深：後端用 `find_latest(symbol, tf)` **靜默挑最新 run**，使用者**無法選舊批次**。

## 1. 已驗證事實（§A 底稿，皆附出處）
- 三模式：`global`/`event`（單 run）、`cross_sectional`（多 symbol）。types.ts:1956 `mode: 'global'|'event'|'cross_sectional'`。
- 單 run 解析：ic_analysis_service.py:133 `find_latest(symbol, timeframe)` → 靜默挑最新。
- 橫截面解析：service `load_multi(symbols, tf)` → feature_library.py:169 → 每 symbol `load()` → `_load_internal` → :43 `find_latest`。同樣靜默挑最新，**且無 config_hash 參數**。
- 精確解析已存在：feature_registry.py:139 `get(symbol, tf, config_hash)`；:123 `find(symbol, tf)` 列同 key 全部 run。
- analyze 由 (symbol,tf,config_hash) 從 run_dir 載 features+labels（ic_engine.py:145 `feature_run_dir`）。
- V7 路徑格式：`parquet:{symbol}:{config_hash}`（ic_analysis_service.py:314 list_features 已支援）。
- ICAnalyzeRequest（ic_models.py:44）：features_path, symbol, symbols, timeframe, labels_path, meta_path — **無 config_hash**。
- /runs → RunInfo（feature_factory_models.py）：有 symbol/timeframe(primary)/config_hash/batch_id/batch_alias/created_at/size_bytes/feature_count/row_count — **無 training[] TF 清單**。
- 一個 run 的 TF 模型：`timeframes:{primary, training[]}`（types.ts:190）。「2tf」run = primary 1h + training 含 12h，registry 只記 primary。
- 前端：選擇器 ICConfigPanel.tsx；payload 組裝 useICAnalysis.ts:123-182（送 features_path/symbol/symbols/timeframe/labels_path/meta_path）；config state icAnalysisStore.ts:154；IC 排名總覽 fetchAvailableFeatures 綁 config.features_path（page.tsx:236）。
- store 已有 runs:RunInfo[] + fetchRuns()（featureFactoryStore.ts:88,564）；formatRunLabel 已批次感知（runExplorer.ts:77）。

## 2. 三個身分維度（選擇器須能辨識）
| 維度 | 資料現況 | 動作 |
|---|---|---|
| ① 批次 batch_alias | RunInfo 已有 | 前端用 |
| ② symbol | 已有 | — |
| ③ 合併 TF（1h vs 1h+12h） | /runs 只吐 primary | **後端 list_runs 讀 manifest 補 training[]** |

## 3. 設計（從根本，三模式統一身分 = run 由 (symbol, tf_primary, config_hash) 唯一定位）

### 後端
- **B1** ICAnalyzeRequest 加 `config_hash: Optional[str]`（單 run）+ `cross_sectional_runs: Optional[List[{symbol,config_hash}]]`（橫截面，取代只送 symbols）。向後相容：欄位 optional，舊呼叫走 find_latest。
- **B2** ic_analysis_service 單 run 路徑：config_hash 有值 → `registry.get(symbol,tf,config_hash)`，否則維持 find_latest（log warn「未指定 run，回退最新」）。
- **B3** feature_library `_load_internal`/`load`/`load_multi` 加 optional config_hash（load_multi 收 `{symbol:config_hash}` map）；有值走 registry.get，無值維持 find_latest。橫截面 service 改傳 map。
- **B4** list_runs 讀每 run manifest 的 `timeframes.training`，RunInfo 加 `training_timeframes: Optional[List[str]]`。
- **不可做**：不改 IC 數值計算；不改 find_latest 預設行為（無 config_hash 時）；不動 HDF5 schema。

### 前端
- **F1** ICConfigPanel：global/event → 批次分組 Run 下拉（group label = batch_alias，leaf = `{symbol} / {primary}{(+training)} · {time} · {size}`）；選定寫 config.{symbol,timeframe,config_hash}。移除三個貼路徑欄（收進「進階」摺疊或刪）。
- **F2** cross_sectional → 批次分組多選；選定寫 config.cross_sectional_runs=[{symbol,config_hash}]。
- **F3** useICAnalysis payload 送 config_hash / cross_sectional_runs；features_path 改由 run 推導 `parquet:{symbol}:{config_hash}`（保留 fetchAvailableFeatures 運作）。
- **F4** types ICAnalysisConfig 加 config_hash、cross_sectional_runs；RunInfo 加 training_timeframes。
- **F5** page.tsx fetchRuns() on mount，傳 runs 給 ICConfigPanel；fetchAvailableFeatures 由選定 run 推導路徑。

## 4. 風險與驗證（§V 底稿）
- **真實路徑驗證鐵律**：用使用者真實 3 批次（99ccd2cd / a08a292c / 1symbol）跑端到端。可證偽檢查：
  - 選「批次X的BTCUSDT」vs「批次Y的BTCUSDT」→ 分析結果（feature 集合 hash / row_count）**不同**，證明 config_hash 真的消歧（防 find_latest 漏網）。
  - 不送 config_hash（舊呼叫）→ 結果 == find_latest 舊行為（向後相容 golden）。
  - 橫截面選整批 3 symbol → 載到的 3 份各自 config_hash 正確。
- **邊界**：批次只 1 run；同 batch 同 symbol 多 config_hash；run 已刪但仍在下拉（stale）；training[] manifest 缺失 → label 退回 primary。
- 回退：後端欄位 optional 可單獨 revert；前端選擇器替換包在元件層。

## 5. 待委員會 challenge 的開放決策
1. 橫截面身分用 `{symbol:config_hash}` map vs `batch_id`（registry 需不需要 find_by_batch）？
2. config_hash 缺失時「靜默回退最新」vs「報錯要求明選」——回退是否會重蹈靜默挑錯 bug？建議：UI 一律帶 config_hash，後端回退僅為 API 相容並 log warn。
3. F1 路徑欄「移除 vs 進階摺疊」——使用者要求完全移除，但 features_path 仍是 list_features 的 key，內部保留（不顯示）。
4. training[] 補在 list_runs（每 run 讀 manifest，N 次 IO）vs 寫進 registry（生成時記）——效能 vs 改動面。
5. 分期 vs 一次到位：使用者定「一次做好」。但 B3(load_multi 簽名改) 命中跨模組多消費者，需查 load/load_multi 其他 caller 不被破壞。

---

## §6 委員會 reconcile（2026-06-23，codex 後端 + cursor 前端，雙家族）

### codex（後端 adversary）— BLOCKING
- **C1 身分必含 timeframe**：run 完整身分 = (symbol, timeframe, config_hash)。`parquet:{symbol}:{config_hash}` 二段格式缺 tf，且 `list_features`(ic_analysis_service:314)走 legacy `base/symbol/config_hash`，與 analyze 走 V2 `features/{symbol}/{timeframe}/{config_hash}/`(ic_engine:145)不一致 → 統一用三件，config_hash 當獨立欄不塞二段 key；list_features 須補 timeframe。

### cursor（前端 adversary）— CONCERNS
- **C2 全鏈未接通**：ICAnalysisConfig 無 config_hash/cross_sectional_runs；startAnalysis 不送 config_hash(useICAnalysis:126-178)；hasLibrarySelection=symbol&&timeframe 無法區分多批次 → 同步擴 config/payload/後端契約。
- **C3 fetchRuns 位置**：runs/fetchRuns 在 featureFactoryStore 不在 icAnalysisStore；page.tsx 只 fetchRegistry()(231-233)，缺 runs 的 loading/error/empty。
- **C4 啟動 gate**：runDisabled(113-121)不檢查是否選 run；移除路徑欄後須補「未選 run→禁啟動」gate，否則空啟動。
- **C5 cross_sectional tf 衝突**：現強制共同 tf 交集(60-84,108-111)與每 run {symbol,config_hash} 衝突 → 解法見 D2。
- **C6 路徑推導**：選 run 須寫 features_path 並推導 labels/meta(現只手填 150-164，無 helper)；建議後端由三件全解析，前端只送三件。
- **C7 fetchAvailableFeatures**：失敗靜默清空(243)→ 改 setError；effect 依賴改選中 run key。
- **C8 cross anchor**：crossSectionalFeatureCount(116-159)多 run 時 anchor run 規則待定。
- **C9 無既有測試**：grep 零 ICConfigPanel/useICAnalysis/ic-analysis 測試 → 必新增真實 3 批次端到端測試。registryEntries 邏輯(ICConfigPanel:23,45,56-96)整段可刪。

### reconcile 後定案（D = decision）
- **D1（採 C1）**：run 身分三件齊送(symbol+timeframe+config_hash)。後端由 registry.get 全解析 features/labels/meta，前端不送路徑。list_features/fetchAvailableFeatures 補 timeframe(新端點或 3 段 key)。
- **D2（解 C5 + §5#1）**：**cross_sectional = 選「一個批次」**。同批次所有 run 共享 tf(批次 99ccd2cd=3sym×1h、a08a292c=3sym×12h)，故選批次即得「統一 tf + 每 symbol 的 config_hash」，天然消解 tf 交集衝突。cross_sectional_runs=[{symbol,config_hash}] 全來自同批。registry 不需新 find_by_batch(前端已有 runs by batch_id)。
- **D3（採 C4）**：啟動 gate = 必須選定 run(單)或批次(cross)且 config_hash 齊全才 enable 啟動。
- **D4（採 C3）**：page.tsx 加 fetchRuns + runsLoading/runsError/empty 三態。
- **D5（採 C6）**：前端只送三件；後端 ICAnalyzeRequest 加 config_hash + cross_sectional_runs，service 用 registry.get；load/load_multi 加 optional config_hash(map)預設 find_latest 保 ML 訓練 caller 相容。
- **D6（採 C7）**：fetchAvailableFeatures setError 不靜默清空。
- **D7（採 C9）**：新增真實 3 批次端到端測試(選批次X的BTC vs 批次Y的BTC→結果不同證消歧；不送 config_hash→==find_latest 舊行為 golden)。
- **§5#2 回退語義定案**：UI 一律帶 config_hash;後端「無 config_hash→find_latest」僅為 API 向後相容並 log warn，UI 路徑永不觸發 → 不重蹈靜默挑錯。
- **training[] 標籤(§5#4 / 維度③)**：list_runs 讀 manifest 補 training_timeframes，選擇器顯示「1h(+12h)」。低風險、放最後 phase。

### 修訂後 blast radius（命中 (b)(d)，確認為「大」）
後端：ic_models、ic_analysis_service、feature_library(load/load_multi/_load_internal，含 ML 訓練 caller cross_symbol_training_service:38 須相容)、feature_factory_service.list_runs、feature_reader/list_features。
前端：ICConfigPanel(重寫選擇器段)、useICAnalysis(payload)、icAnalysisStore(config)、ic-analysis/page(fetchRuns+三態)、types。

