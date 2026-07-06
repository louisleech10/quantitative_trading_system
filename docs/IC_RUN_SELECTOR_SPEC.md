# IC Gatekeeper Run 選擇器重做 — SPEC

> 來源 PLAN/診斷：handoffs/20260623-ic-run-selector-DESIGN.md §6（雙家族 reconcile 定案）｜ 日期：2026-06-23 ｜ 對應 TODO：docs/IC_RUN_SELECTOR_TODO.md ｜ manifest：handoffs/20260623-ic-run-selector-MANIFEST.md

## §RISK 風險分級
- RISK-HIT: b,d
- **大小**：大。
- **命中高風險原則**：
  - **(b) 跨模組共用路徑**：`feature_library.load/load_multi/_load_internal` 有多消費者（IC 分析 ic_analysis_service、ML 訓練 cross_symbol_training_service:38、browser feature_browser_service:97）。改簽名一處影響三片。
  - **(d) ML/回測分析真實性**：現 `find_latest` 靜默挑最新 run，使用者選了某批次卻分析到別的 run = 分析非預期資料。config_hash 消歧是正確性核心。
- 命中 (d) → **§G Golden 必填、adversarial review 必跑**（雙家族）。

## §A 假設與待使用者確認
- **已驗證事實**（附驗證方式：grep/實讀 *.py）：
  - 三模式 `mode: 'global'|'event'|'cross_sectional'`（grep types.ts:1956 實見）。
  - 單 run 解析 = `find_latest(symbol, timeframe)`，靜默挑最新（讀 ic_analysis_service.py:133）。
  - 橫截面 = `load_multi(symbols, tf)` → 每 symbol `load()` → `_load_internal` → `find_latest`，無 config_hash 參數（讀 feature_library.py:169,43）。
  - 精確解析已存在 `registry.get(symbol,tf,config_hash)`（讀 feature_registry.py:139）。
  - **/analyze 主路徑（修正）**：`entry.hdf5_relative_path → features_path → orchestrator.analyze`（讀 ic_analysis_service.py:139-148 實見）；entry path 已是 `data_cache/features/{sym}/{tf}/{hash}/feature_manifest.json`（V2 含 tf+hash，registry.json 實見）。ic_engine.py:145 是 `compute_ic_from_l7_raw` 內部 cache 路徑，**非主流程**。故 A-2 只需 find_latest→registry.get，features 載入機制不變、不需新 adapter（已驗證）。
  - **label ingestion（cursor 抓）**：orchestrator(ic_filter_orchestrator.py:1034) labels_df 空 + kline_reader=None → `InvalidInputError`；run_dir 無 labels 檔（實 ls：raw/timestamps/manifest）；現況靠手填 labels_path。移除路徑欄後須補 kline_reader。
  - **run 完整身分含 timeframe**：V2 路徑 `features/{symbol}/{timeframe}/{config_hash}/`，legacy reader 另有 `base/symbol/config_hash` fallback；`parquet:{symbol}:{config_hash}` 二段缺 tf（codex consult 實查，2026-06-23）。
  - load/load_multi caller 清單：ic_analysis_service:111、cross_symbol_training_service:38、feature_browser_service:97、ic_analysis_service:808（grep 實見）。
  - RunInfo 有 batch_alias/config_hash/symbol/timeframe(primary)，無 training[]（讀 feature_factory_models.py）。
  - store 已有 runs:RunInfo[] + fetchRuns()（讀 featureFactoryStore.ts:88,564）；formatRunLabel 批次感知（runExplorer.ts:77）。
  - ic-analysis 無既有測試（cursor grep 零命中 ICConfigPanel/useICAnalysis/ic-analysis）。
- **待使用者確認**：無（D1-D7 已於 2026-06-23 定案，見 §A 已確認結果）。
- **已確認結果**（使用者 2026-06-23）：三模式都用；run 可合併多 TF（2tf=primary 1h+training 12h，folder 只記 primary）；主訴=辨識批次；決定「從根本一次做好」不分期；橫截面採「選一個批次」。

## §C 約束
- 解耦 7 條：`grep "from api\." momentum/`→0；服務不互 import；services 用 factories。本任務後端改動在 momentum（feature_library/registry）與 api（service/models），不得讓 momentum import api。
- 不可違反原則：不改 IC 數值計算；不弱化 NaN/inf gate；不改 HDF5 schema/輸出大小。
- **本任務特別注意**：`load/load_multi` 為共用路徑——**新增參數一律 optional 且預設維持 find_latest**，確保 ML 訓練 caller（cross_symbol_training_service:38）與 browser caller 行為 byte 不變。

## §G Golden / Baseline（命中 (d) 必填）
- **凍結時機 / reference 設定（[A-0]）**：動工前跑 baseline 存 `tests/fixtures/ic_run_selector_baseline.json`。**消歧必用同 symbol+同 timeframe+不同 config_hash**：BTCUSDT 12h `1c4b825498449860a639b0ac37f66d73`（無批次）vs `90f586663db18ba594b21ce909ad83e0`（批次 a08a292c）（registry.json 實見）——tf 相同，唯有真消歧才會不同（原 1h vs 12h 設計會假綠，codex 抓）。
- **baseline 內容**：
  - **向後相容 golden**：不帶 config_hash 呼叫 `/analyze`（symbol=BTCUSDT,tf=1h）→ 記錄選中 config_hash、feature 名稱集合 sha256、row_count、IC 報告關鍵聚合（top-N feature + IC 值）。
  - **消歧 baseline**：BTCUSDT 12h 的兩個 config_hash 各自 feature sha256 + row_count + **選中 run identity（symbol/timeframe/config_hash/path）**。
- **通過條件（可證偽）**：
  - 改後「不帶 config_hash」呼叫 → 選中 config_hash、feature sha256、row_count、IC 聚合 **與 baseline 完全一致**（向後相容；任一不符=FAIL 並列 diff）。
  - 改後「帶 `1c4b825...`」vs「帶 `90f586...`」（同 BTCUSDT 12h）→ feature sha256/row_count **不同**，且 **assert 選中 run identity == 請求 config_hash**（不只比 hash；若 identity≠請求或兩者相同=FAIL，證仍 find_latest）。
  - **ML caller golden（[G-3]，codex#5）**：spy/run `CrossSymbolTrainingService.run_cross_symbol_validation()`，凍結其對 `load_multi` 的 call kwargs（for_training/allow_partial_training/feature_columns）+ service 輸出摘要 == baseline（非只直接 load_multi）。

## §P Phase 與依賴
> 自檢：每 Task 輸入來源無「依賴尚未完成的後續 Phase」。後端 A→B→C 漸進；前端 D 依賴 A/C、E 依賴 B；F/G 最後。

### Phase A — 後端單 run config_hash（依賴：無）
**Task [A-0] 凍結 baseline fixture**
- 目標：動工前產生 golden baseline。檔案：`tests/fixtures/ic_run_selector_baseline.json`（新建腳本 `tests/fixtures/gen_ic_run_selector_baseline.py`）。
- 改法：跑三組——(1) 不帶 config_hash analyze(BTCUSDT,12h)；(2) 帶 `1c4b825...`、帶 `90f586...` 各一；(3) load_multi/CrossSymbolTrainingService 摘要。寫 sha256/row_count/identity。
- 驗證：`python tests/fixtures/gen_ic_run_selector_baseline.py` 產出 .json，含三組 key（assert 存在）。
- 邊界：run 不存在→腳本報錯不寫半套。
- 不可做：不在 baseline 用合成資料（用真實 registry run）。

**Task [A-1] ICAnalyzeRequest 加 config_hash**
- 目標：請求可帶單 run config_hash。檔案：`api/models/ic_models.py` `ICAnalyzeRequest`（:44）。既有 caller：前端 useICAnalysis payload（後續 D-6 補送）。
- 改法：加 `config_hash: Optional[str] = Field(None, ...)`。不動既有欄位。
- 驗證：pydantic 接受帶/不帶 config_hash 的 payload；`pytest tests/api/test_ic_models.py` 新斷言 config_hash optional。
- 邊界：config_hash=None（舊呼叫）；config_hash="" 空字串視同 None。
- 不可做：不改 features_path/labels_path/meta_path 既有語義。

**Task [A-2] service 單 run 解析用 registry.get**
- 目標：config_hash 有值精確命中，否則回退並 warn。檔案：`api/services/ic_analysis_service.py`（:130-142）。既有 caller：analyze task。
- 改法：`if request.config_hash: entry = registry.get(symbol,tf,config_hash)` else `find_latest` + `logger.warning("未指定 config_hash，回退最新 run")`。entry 缺→ raise（非靜默）。features_path 取 entry.hdf5_relative_path（機制不變）。
- **labels（cursor#2 必修）**：移除手填 labels_path 後，須傳 `kline_reader=create_kline_cache(...)` 給 orchestrator 並確保 meta 帶 symbol/timeframe → 從 kline 生 label（orchestrator:1034 路徑）。**先驗證現況 symbol/tf-only 是否本就掛**，再決定是否同屬既存修復。實作端須用真實 run 驗單 run analyze 端到端完成（禁 mock）。
- 驗證：帶 config_hash → 解析到該 run_dir（assert path 含 config_hash）；不帶 → 走 find_latest 且有 warn log；**真實 run analyze 端到端完成不拋 InvalidInputError**（`pytest tests/api -k analyze_real_run`）。
- 邊界：config_hash 不存在於 registry → ValueError 明確訊息；symbol/tf 缺 → 既有錯誤路徑不變。
- 不可做：不改 find_latest 預設行為。

**Task [A-3] feature_library load 加 optional config_hash**
- 目標：load 可指定 config_hash。檔案：`momentum/FeatureEngineering/feature_library.py` `_load_internal`/`load`（:43）。**既有 caller：browser:97、ic_analysis_service:808**。
- 改法：`load(symbol, tf, *, config_hash: Optional[str]=None, ...)`；`_load_internal` config_hash 有值用 `registry.get` 否則 `find_latest`。預設 None=現行為。
- 驗證：`pytest tests/momentum/test_feature_library.py -k config_hash`；不帶 config_hash 的 DataFrame == 改前 golden（shape/columns/NaN mask 全等），帶則載對應 run_dir（assert path 含 hash）。
- 邊界：config_hash=None；config_hash 指向已刪 run → FeatureNotFoundError。
- 不可做：不改回傳型別/欄位。

### Phase B — 後端橫截面消歧（依賴：A-3）
**Task [B-1] ICAnalyzeRequest 加 cross_sectional_runs**
- 目標：橫截面可帶 per-symbol config_hash。檔案：`ic_models.py`。
- 改法：加 `cross_sectional_runs: Optional[List[CrossRunRef]]`，`CrossRunRef{symbol:str, config_hash:str}`。保留 `symbols` 向後相容。
- 驗證：pydantic 接受;`pytest` 斷言結構。
- 邊界：空 list；symbols 與 cross_sectional_runs 同時給→以 cross_sectional_runs 為準。
- 不可做：不刪 symbols 欄。

**Task [B-2] load_multi 加 optional config_hashes map**
- 目標：橫截面精確載各 run。檔案：`feature_library.py:169`。**既有 caller：ic_analysis_service:111、ML 訓練 cross_symbol_training_service:38**。
- 改法：`load_multi(symbols, tf, *, config_hashes: Optional[Dict[str,str]]=None, ...)`；逐 symbol `self.load(symbol, tf, config_hash=config_hashes.get(symbol) if config_hashes else None)`。預設 None=現行為。
- 驗證：不帶 config_hashes → ML caller 路徑 byte 一致（golden G-3）；帶 → 各 symbol 載對應 hash。
- 邊界：config_hashes 缺某 symbol → 該 symbol 回退 find_latest（與舊一致）+ warn。
- 不可做：不改 ML 訓練呼叫的預設行為。

**Task [B-3] service 橫截面傳 map**
- 目標：cross_sectional_runs → load_multi config_hashes。檔案：`ic_analysis_service.py:111`。
- 改法：有 cross_sectional_runs → 組 `{r.symbol:r.config_hash}` 傳入；labels 同 A-2 用 kline_reader 生成。
- 驗證：帶 cross_sectional_runs → load_multi 收到 map（assert）。
- 邊界：無 cross_sectional_runs → 維持 symbols+find_latest。
- 不可做：—

### Phase C — 後端 list_features timeframe 一致（依賴：無；codex C1）
**Task [C-1] list_features 補 timeframe**
- 目標：消除 legacy vs V2 路徑不一致。檔案：`ic_analysis_service.py:305-324`、`feature_reader.py:218`。
- 改法：**不改 protocol `FeatureReader.list_features(symbol, config_hash)` 2 參數簽名**（codex#3）；新增 `list_features_v2(symbol, tf, config_hash)` 或 `list_features(..., tf: Optional[str]=None)` 保留 legacy 行為；IC service 走 V2 帶 tf。
- **blast-radius（必列）**：IC list endpoint、feature_browser_service:129、coverage_analyzer:186、FeatureReader protocol(protocols.py:268)/tests——確認哪些保留 legacy、哪些需 V2。
- **key 定案（D-A7）**：前後端用獨立 query params `(symbol,timeframe,config_hash)`，**不塞 parquet key**（現碼 3 段=sym:hash，4 段會 ValueError，易分叉）。
- 驗證：list_features(symbol,tf,config_hash) 回傳的 feature 集合 == analyze 同 run 載入的欄位集合（一致性斷言）。
- 邊界：legacy 2 段 key 輸入 → 向後相容 fallback 或明確錯誤（擇一，SPEC adversarial 定）。
- 不可做：不破壞既有 list_features 呼叫（feature_export_service 等）。

**Task [C-2] fetchAvailableFeatures 後端來源由三件解析**
- 目標：IC 排名總覽特徵來源與選定 run 一致。檔案：`ic_analysis_service.list_features` 對應 endpoint。
- 驗證：`pytest tests/api/test_ic_analysis.py -k list_features`；給 (symbol,tf,config_hash) 回該 run feature 清單，集合 == analyze 同 run 欄位。
- 邊界：run 不存在 → 4xx 明確訊息。
- 不可做：—

**Task [C-2b] 前端 list 鏈（cursor#1 必修）**
- 目標：移除路徑欄後 fetchAvailableFeatures 仍運作。檔案：`useICAnalysis.ts:220-226`、`page.tsx:235-244`、`api/routes/ic_analysis.py:77-80`。
- 改法：`fetchAvailableFeatures(symbol,timeframe,config_hash)` 改傳三件；page effect 依賴改 `config.{symbol,timeframe,config_hash}`；route 加 query params。
- 驗證：選 run→FeatureFilterPanel 非空（vitest `expect(availableFeatures.length).toBeGreaterThan(0)`）。
- 邊界：未選 run→不 fetch；fetch 失敗→featuresError（非靜默 []）。
- 不可做：不留 features_path 硬綁殘留。

### Phase D — 前端單 run 選擇器（依賴：A、C）
**Task [D-1] types 擴充**
- 檔案：`frontend/src/lib/types.ts`（ICAnalysisConfig:1956 加 config_hash/cross_sectional_runs；RunInfo:597 加 training_timeframes?）；**`icAnalysisStore.ts defaultConfig`（cursor#4）加新欄；mode 切換清舊 cross_sectional_symbols**。
- 驗證：`npm run build` 無型別錯（.ts/.tsx tsc）；既有用 config 處不報錯。
- 邊界：config_hash undefined。
- 不可做：不刪既有欄。

**Task [D-2] page.tsx fetchRuns + 三態**
- 檔案：`frontend/src/app/ic-analysis/page.tsx:92-93,231-233`。
- 改法：from featureFactoryStore 取 runs/fetchRuns/runsLoading/runsError；mount fetchRuns()；傳 runs 給 ICConfigPanel。
- 驗證：vitest `expect(fetchRuns).toHaveBeenCalled()`；runs 空/載入/錯誤三態各渲染對應節點。
- 邊界：runs=[]（空）→ 提示無可選 run；fetch 失敗→error UI。
- 不可做：—

**Task [D-3] ICConfigPanel 批次分組 Run 下拉**
- 檔案：`frontend/src/components/ic-analysis/ICConfigPanel.tsx:56-96,167-194`。
- 改法：global/event 用 runs **依 batch_id 分組（顯示 batch_alias）**（cursor#3 統一 stable key），leaf=formatRunLabel；onSelect 寫 config.{symbol,timeframe,config_hash}；刪 registryEntries/symbolOptions/timeframeOptions。**僅 browse_ready 可選**（或選後 ensureBrowse）。
- 驗證：vitest `expect(updateConfig).toHaveBeenCalledWith({symbol,timeframe,config_hash})`；下拉依 batch_alias 分組（ICConfigPanel.test.tsx）。
- 邊界：run 無 batch_alias → 歸「未分組」；單 run 批次。
- 不可做：不在此 Task 動 cross_sectional（E）。

**Task [D-4] 移除貼路徑欄**
- 檔案：`ICConfigPanel.tsx:150-164`。改法：刪三個路徑 input。
- 驗證：vitest `expect(queryByPlaceholderText(/features/)).toBeNull()`（.tsx）；無路徑 input 殘留。
- 邊界：—。不可做：不留隱藏殘留欄。

**Task [D-5] 啟動 gate**
- 檔案：`ICConfigPanel.tsx:113-121`（runDisabled）。
- 改法：未選 run（config_hash 空）→ disabled。
- 驗證：vitest `expect(button).toBeDisabled()` 未選 config_hash 時；選後 `not.toBeDisabled()`。
- 邊界：cross 模式未選批次→disabled。不可做：—

**Task [D-6] useICAnalysis payload 送 config_hash**
- 檔案：`frontend/src/hooks/useICAnalysis.ts:126-178`。
- 改法：payload 加 config_hash；hasLibrarySelection 納入 config_hash。
- 驗證：vitest `expect(payload.config_hash).toBe(run.config_hash)`（useICAnalysis.test.ts）。
- 邊界：無 config_hash→不啟動（接 D-5）。不可做：—

### Phase E — 前端橫截面批次選擇器（依賴：B、D）
**Task [E-1] cross_sectional 改選一個批次**
- 檔案：`ICConfigPanel.tsx:60-84,201-211`。
- 改法：cross_sectional 改「選一批次（pickedBatchId）」→ cross_sectional_runs=`runs.filter(r=>r.batch_id===pickedBatchId)` 的 {symbol,config_hash}（同批共享 tf）；移除共同 tf 交集邏輯。
- 驗證：vitest `expect(config.cross_sectional_runs).toHaveLength(batchSymbols)`（.tsx）；tf 取自批次。
- 邊界：批次只 1 symbol→仍可（但提示橫截面需≥2）。不可做：—

**Task [E-2] useICAnalysis 橫截面 payload + anchor**
- 檔案：`useICAnalysis.ts`；`page.tsx:116-159`（crossSectionalFeatureCount）。
- 改法：payload 送 cross_sectional_runs；crossSectionalFeatureCount anchor=cross_sectional_runs[0]；**`page.tsx:361-368 handleRunAnalysis` 改驗 cross_sectional_runs；hasCrossSectionSelection 取代 symbols 檢查**（cursor#7）。
- 驗證：vitest `expect(payload.cross_sectional_runs).toEqual(...)`；crossSectionalFeatureCount 用 anchor run（useICAnalysis.test.ts）。
- 邊界：—。不可做：—

### Phase F — training_timeframes 標籤（依賴：D；低風險）
**Task [F-1] list_runs 補 training_timeframes**
- 檔案：`api/services/feature_factory_service.py:811`。改法：讀 run manifest `timeframes.training` 填 RunInfo.training_timeframes。
- 驗證：`pytest tests/api -k list_runs`；/runs 回傳含 training_timeframes，manifest 缺 → None（不拋錯）。
- 邊界：manifest 不存在→None 不報錯。不可做：不每 run 重算特徵。

**Task [F-2] 選擇器顯示「1h(+12h)」**
- 檔案：`ICConfigPanel.tsx` leaf label。驗證：training 有值→顯示 (+12h)；無→只 primary。邊界：training=[primary]→不顯示加號。不可做：—

### Phase G — 測試（依賴：A-F）
**Task [G-1]~[G-5]** 見 §V。

## §V 驗證策略與邊界測試目錄
- 測試層級：單元（pydantic/型別）、整合（service 解析路徑）、Golden 對照（§G）、邊界。後端可獨立 `pytest tests/api tests/momentum`，不需 run_api.py；前端 `npm run test`（vitest）。
- **防假綠**：ic-analysis 現無測試（新建）；後端既有 feature_library/registry 測試 **diff 斷言確認未放寬**；G-3 必須證 ML 訓練 caller 行為不變（非刪測試換綠）。
- **邊界目錄**（打勾對應 Task）：
  - [x] 空輸入：runs=[]（D-2）、cross 0 symbol（E-1）
  - [x] config_hash=None/""（A-1,A-2,B-2）→ 回退 find_latest（不可靜默錯，須 warn）
  - [x] config_hash 指向已刪 run（A-3）→ 明確錯誤
  - [x] 同 symbol/tf 多批次（G-1）→ 消歧證明
  - [x] ML 訓練 caller 不帶 config_hashes（G-3）→ byte 不變
  - [x] fetchAvailableFeatures 失敗（G-5）→ setError 非靜默清空
- **測試清單**：
  - [G-1] 後端：批次X BTC vs 批次Y BTC → feature sha256/row_count 不同。
  - [G-2] 後端：不送 config_hash → == find_latest baseline（向後相容）。
  - [G-3] 後端：load_multi 無 config_hashes → ML caller DataFrame 一致。
  - [G-4] 前端：選 run→config→payload config_hash/cross_sectional_runs wiring。
  - [G-5] 前端：fetchAvailableFeatures reject → error state（非 []）。

## §R 回退
- 每 Phase 獨立 commit 可單獨 revert。後端新欄位/參數皆 optional 預設舊行為 → A/B/C 可逐一退。前端選擇器替換包在 ICConfigPanel + page，整段可 revert 回 registryEntries 版。Golden（§G 向後相容）FAIL → 不 merge。training 標籤（F）獨立最後，可不做不影響主功能。

## §N N/A 登記
- 無省略段（§RISK §A §C §G §P §V §R 皆已填）。
