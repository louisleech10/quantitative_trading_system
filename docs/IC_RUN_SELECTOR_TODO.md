# IC Gatekeeper Run 選擇器重做 — TODO

> 版本 DRAFT ｜ 基於 docs/IC_RUN_SELECTOR_SPEC.md ｜ manifest handoffs/20260623-ic-run-selector-MANIFEST.md ｜ 2026-06-23 ｜ 狀態：未過 adversarial 前 Internal Frozen

## 階段 1：SPEC ID 覆蓋索引（追溯基準）
| 類別 | IDs | 合計 |
|---|---|---|
| Task | A-0,A-1,A-2,A-3 / B-1,B-2,B-3 / C-1,C-2,C-2b / D-1,D-2,D-3,D-4,D-5,D-6 / E-1,E-2 / F-1,F-2 | 20 |
| 測試 | G-1,G-2,G-3,G-4,G-5 | 5 |
| §G Golden | 向後相容(no config_hash==find_latest)、消歧(批次X≠批次Y)、ML caller 不變 | 3 |
| §RISK 命中 | (b)跨模組共用路徑 load/load_multi、(d)分析真實性 config_hash 消歧 | 2 |
| Phase 依賴 | A→(B,C,D)；D→E,F；B→E；G 最後 | — |

## §0 全域規則與約束（執行端讀完即可遵守）
- **解耦 7 條**：`momentum/` 不得 `from api.`（grep→0）；services 用 `momentum.factories.create_*`；DTO 不跨域。本任務後端改 momentum(feature_library/registry)+api(service/models)，保持 momentum 不依賴 api。
- **不可違反原則**：不改 IC 數值計算；不弱化 NaN/inf gate；不改 HDF5 schema/輸出大小；無假資料。
- **共用路徑鐵律**：`load/load_multi/_load_internal` 新增參數**一律 optional 且預設維持 find_latest**——ML 訓練 caller（cross_symbol_training_service:38）與 browser caller（feature_browser_service:97）行為必須 byte 不變。
- **防假綠**：ic-analysis 現無測試（新建）；後端既有 feature_library/registry 測試**不得放寬/刪斷言**，驗收 diff 斷言。
- **Logging**：`from api.core.logging import get_logger`；回退 find_latest 必 `logger.warning`；熱迴圈不 log。
- **型別**：Python 全函式 type hints；TS 全 props/state/API 型別。

## §B 批次執行策略（依賴拓撲 → 7 批，每批一次派工）
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| 1 | A-1,A-2,A-3 + G-2,G-3(部分) | 無 | 後端單 run config_hash 同一垂直切片 | 中 |
| 2 | B-1,B-2,B-3 | Batch1(A-3) | 橫截面消歧建在 load 之上 | 中 |
| 3 | C-1,C-2,C-2b | Batch1 | list_features『與 analyze 同源』驗證依賴 A（codex#4） | 中 |
| 4 | D-1,D-2,D-3,D-4,D-5,D-6 + G-4,G-5 | Batch1,3 | 前端單 run 選擇器整片 | 大 |
| 5 | E-1,E-2 | Batch2,4 | 橫截面前端依賴 B 契約+D 元件 | 中 |
| 6 | F-1,F-2 | Batch4 | training 標籤低風險收尾 | 小 |
| 7 | G-1 + 全測試整合 | Batch1-5 | 真實 3 批次端到端 golden | 中 |
- **批次間 Gate**：每批跑 `pytest tests/api tests/momentum -k ic_run_selector` 或前端 `npm run test`，引用對應 Test ID 綠燈才進下批。
- **派工 prompt（每批可直接複製，附前置狀態+Task+`pytest`/`npm run test` 命令）見各 Phase 末**。

## Phase A — 後端單 run config_hash（完成後：/analyze 可帶 config_hash 精確命中，不帶則 find_latest+warn）

### Task A-0 — 凍結 baseline fixture（前置 gate）
- SPEC ref：[A-0]　目標：動工前產 golden baseline。
- 輸入：真實 registry runs（BTCUSDT 12h `1c4b825...`、`90f586...`）　輸出：`tests/fixtures/ic_run_selector_baseline.json`
- 實作要點：
  1. 新建 `tests/fixtures/gen_ic_run_selector_baseline.py`。
  2. 跑：不帶 config_hash analyze(BTCUSDT,12h)；帶 `1c4b825...`、帶 `90f586...`；load_multi/CrossSymbolTrainingService 摘要。
  3. 寫 feature sha256/row_count/run identity 三組。
- 修改檔案：`tests/fixtures/gen_ic_run_selector_baseline.py`（新建）。
- 不可做：禁合成資料（用真實 registry run）；不寫半套（缺 run→報錯）。
- 邊界：run 不存在→raise 不產出。
- 驗證：`python tests/fixtures/gen_ic_run_selector_baseline.py` 產 .json，`assert` 三組 key 存在。

### Task A-1 — ICAnalyzeRequest 加 config_hash
- SPEC ref：[A-1]　目標：請求可帶單 run config_hash。
- 輸入：無　輸出：`ICAnalyzeRequest.config_hash: Optional[str]`
- 實作要點：
  1. `api/models/ic_models.py` `ICAnalyzeRequest`（:44）加 `config_hash: Optional[str] = Field(None, description="精確指定 run，None 則回退最新")`。
  2. 空字串正規化：在 service 取用時 `config_hash = (request.config_hash or "").strip() or None`。
  3. 不動 features_path/labels_path/meta_path。
- 修改檔案：`ic_models.py::ICAnalyzeRequest`　既有 caller：前端 useICAnalysis（D-6 補送）；舊呼叫不帶=None。
- 不可做：不改既有欄位語義；不設必填。
- 邊界：config_hash=None（舊呼叫）正常；config_hash=""→視同 None。
- 驗證（G-2 關聯）：`pytest` 斷言 `ICAnalyzeRequest(symbol="BTCUSDT",timeframe="1h").config_hash is None`；帶值可建構。

### Task A-2 — service 單 run 解析用 registry.get
- SPEC ref：[A-2]　目標：config_hash 精確命中，否則回退+warn。
- 輸入：A-1 欄位　輸出：解析到正確 run_dir
- 實作要點：
  1. `api/services/ic_analysis_service.py`（:130-142）：`ch=(request.config_hash or "").strip() or None`。
  2. `if ch: entry = self._feature_library._registry.get(symbol, timeframe, ch)`（缺→`raise ValueError(f"run not found: {symbol}/{timeframe}/{ch}")`）；`else: entry = find_latest(...)` + `logger.warning("未指定 config_hash，回退最新 run %s/%s", symbol, timeframe)`。
  3. 後續 features_path 解析沿用 entry.hdf5_relative_path（機制不變）。
  4. **labels（cursor#2 必修）**：傳 `kline_reader=create_kline_cache(...)`、meta 帶 symbol/tf → orchestrator 從 kline 生 label（:1034）；先驗證現況 symbol/tf-only 是否本就掛。
- 修改檔案：`ic_analysis_service.py::_run_analysis`（單 run 分支）　既有 caller：analyze task。
- 不可做：不改 find_latest 預設；不靜默吞缺失。
- 邊界：config_hash 不存在→ValueError 明確；不帶→find_latest+warn log 可見。
- 驗證：帶 config_hash → 解析 path 含該 hash（assert）；不帶 → caplog 有 warning；**真實 run analyze 端到端不拋 InvalidInputError**：`pytest tests/api -k analyze_real_run`。

### Task A-3 — feature_library load 加 optional config_hash
- SPEC ref：[A-3]　目標：load 可指定 config_hash。
- 輸入：無　輸出：`load(..., config_hash=None)` 行為
- 實作要點：
  1. `momentum/FeatureEngineering/feature_library.py`：`load(self, symbol, timeframe, *, config_hash: Optional[str]=None, for_training=False, allow_partial_training=False)`。
  2. `_load_internal` 加 `config_hash` 參數：`entry = self._registry.get(symbol,tf,config_hash) if config_hash else self._registry.find_latest(symbol,tf)`。
  3. 預設 None → 與改前完全一致路徑。
- 修改檔案：`feature_library.py::load,_load_internal`　既有 caller：feature_browser_service:97、ic_analysis_service:808（皆不帶=None，行為不變）。
- 不可做：不改回傳型別/欄位/index。
- 邊界：config_hash=None→byte 一致（G-3 golden）；config_hash 指向已刪 run→FeatureNotFoundError。
- 驗證（G-3）：不帶 config_hash load(BTCUSDT,1h) 的 DataFrame shape/columns/NaN mask == 改前 baseline。

**Phase A 測試**：G-2（不送 config_hash==find_latest baseline）、G-3（load byte 不變）。**Gate**：`pytest tests/momentum/test_feature_library.py tests/api/test_ic_analysis_service.py -k "config_hash or backward"` 綠。
**派工 prompt（Batch1）**：「實作 SPEC A-1/A-2/A-3。前置：乾淨 main。先跑 scripts/agent_preflight.sh。新增參數一律 optional 預設 find_latest，feature_library.load 不帶 config_hash 須與改前 byte 一致（跑 G-3 golden）。完成跑 `pytest tests/momentum/test_feature_library.py tests/api -k config_hash`，輸出結構化報告+handoffs，勿覆蓋根 HANDOFF。」

## Phase B — 後端橫截面消歧（完成後：橫截面可帶 per-symbol config_hash）

### Task B-1 — ICAnalyzeRequest 加 cross_sectional_runs
- SPEC ref：[B-1]　目標：橫截面 per-symbol config_hash。
- 實作要點：
  1. 新 model `class CrossRunRef(BaseModel): symbol: str; config_hash: str`。
  2. `ICAnalyzeRequest` 加 `cross_sectional_runs: Optional[List[CrossRunRef]] = None`。
  3. 保留 `symbols` 欄向後相容。
- 修改檔案：`ic_models.py`　既有 caller：前端（E-2 補送）。
- 不可做：不刪 symbols。
- 邊界：空 list；symbols 與 cross_sectional_runs 並存→以 cross_sectional_runs 為準。
- 驗證：`pytest tests/api/test_ic_models.py`；`ICAnalyzeRequest(...).cross_sectional_runs` 帶/不帶皆建構，assert CrossRunRef.symbol/config_hash。

### Task B-2 — load_multi 加 optional config_hashes map
- SPEC ref：[B-2]　目標：橫截面精確載各 run。
- 實作要點：
  1. `load_multi(self, symbols, timeframe, *, config_hashes: Optional[Dict[str,str]]=None, for_training=False, ...)`。
  2. 迴圈：`loaded[symbol] = self.load(symbol, timeframe, config_hash=(config_hashes or {}).get(symbol), for_training=for_training, ...)`。
  3. 缺 symbol 的 hash → None → 回退 find_latest + warn。
- 修改檔案：`feature_library.py::load_multi`　**既有 caller：ic_analysis_service:111、cross_symbol_training_service:38(ML 訓練!)**。
- 不可做：不改 ML 訓練呼叫預設行為（不帶 config_hashes=現行為）。
- 邊界：config_hashes=None→全 find_latest（ML caller，byte 不變）；部分缺→該 symbol 回退+warn。
- 驗證（G-3）：load_multi(symbols,tf) 不帶 config_hashes → 各 DataFrame == baseline。

### Task B-3 — service 橫截面傳 map
- SPEC ref：[B-3]　目標：cross_sectional_runs→load_multi。
- 實作要點：
  1. `ic_analysis_service.py:111`：`chs = {r.symbol:r.config_hash for r in request.cross_sectional_runs} if request.cross_sectional_runs else None`。
  2. `load_multi(symbols_resolved, timeframe, config_hashes=chs)`；symbols_resolved 從 cross_sectional_runs 或 symbols 取。
- 修改檔案：`ic_analysis_service.py::_run_analysis`（橫截面分支）。
- 不可做：無 cross_sectional_runs→維持 symbols+find_latest。
- 邊界：無→舊路徑；有→map 傳入。
- 驗證：帶 cross_sectional_runs→load_multi 收到 map（mock assert）。

**Phase B 測試**：G-3（ML caller 不變）。**Gate**：`pytest -k "load_multi or cross_sectional"` 綠。
**派工 prompt（Batch2）**：「實作 SPEC B-1/B-2/B-3，依賴 A-3 已並入。load_multi 新增 config_hashes 須 optional 預設 find_latest，cross_symbol_training_service ML 路徑 byte 不變。完成跑 `pytest -k 'load_multi or cross_sectional'`。」

## Phase C — 後端 list_features timeframe 一致（完成後：特徵清單與 analyze 同源）

### Task C-1 — list_features 補 timeframe
- SPEC ref：[C-1]　目標：消除 legacy vs V2 路徑不一致。
- 實作要點：
  1. `ic_analysis_service.py:305-324` list_features：支援 3 段 `parquet:{symbol}:{timeframe}:{config_hash}`，解析出 timeframe。
  2. 走 V2 `feature_reader.feature_run_dir(symbol,timeframe,config_hash)` 列欄，不走 legacy `base/symbol/config_hash`。
  3. **不改 protocol 2 參數簽名**；加 `list_features_v2(symbol,tf,config_hash)` 或 `list_features(...,tf=None)` 保留 legacy（codex#3）。
  4. blast-radius：feature_browser:129、coverage_analyzer:186、protocols.py:268、tests——列出保留 legacy/需 V2。
- 修改檔案：`ic_analysis_service.py::list_features`；必要時 `feature_reader.py:218 list_features` 簽名。既有 caller：feature_export_service（須不破壞）。
- 不可做：不破壞既有 2 段呼叫。
- 邊界：3 段格式；2 段格式 fallback；run 不存在→錯誤。
- 驗證（一致性）：list_features(symbol,tf,hash) 欄位集合 == analyze 同 run 載入欄位集合。

### Task C-2 — fetchAvailableFeatures 後端來源由三件解析
- SPEC ref：[C-2]　目標：IC 排名總覽與選定 run 一致。
- 實作要點：
  1. 對應 endpoint 接受 (symbol,tf,config_hash) 或 3 段 features_path。
  2. 回該 run 特徵清單。
- 修改檔案：`api/routes/ic_analysis.py`(list endpoint)、`ic_analysis_service.list_features`。
- 不可做：—
- 邊界：run 不存在→4xx 明確訊息。
- 驗證：`pytest tests/api -k list_features`；給 (symbol,tf,config_hash) 回該 run 清單。

**Phase C 測試**：list_features 一致性。**Gate**：`pytest -k list_features` 綠。
**派工 prompt（Batch3）**：「實作 SPEC C-1/C-2，與 Batch1 可並行。重點：list_features 統一走 V2 路徑帶 timeframe，與 analyze 同源；既有 2 段呼叫不破壞。跑 `pytest -k list_features`。」

## Phase D — 前端單 run 選擇器（完成後：global/event 用批次分組 Run 下拉，無路徑欄）

### Task D-1 — types 擴充
- SPEC ref：[D-1]　目標：config state + RunInfo 帶身分。
- 實作要點：
  1. `types.ts:1956` ICAnalysisConfig 加 `config_hash?: string`、`cross_sectional_runs?: {symbol:string; config_hash:string}[]`。
  2. `types.ts:597` RunInfo 加 `training_timeframes?: string[]`。
  3. **`icAnalysisStore.ts:153-168 defaultConfig` 加 config_hash/cross_sectional_runs（cursor#4）；mode 切換清舊 cross_sectional_symbols。**
- 修改檔案：`frontend/src/lib/types.ts`。既有 caller：store defaultConfig、useICAnalysis。
- 不可做：不刪既有欄。
- 邊界：config_hash undefined。
- 驗證：`tsc`/`npm run build` 無型別錯。

### Task D-2 — page.tsx fetchRuns + 三態
- SPEC ref：[D-2]　目標：載入 runs 並有空/載入/錯誤態。
- 實作要點：
  1. `page.tsx:92-93` 從 `useFeatureFactoryStore` 取 `runs, fetchRuns, runsLoading, runsError`。
  2. `useEffect(()=>{fetchRuns().catch(()=>{})},[fetchRuns])`（:231-233 旁）。
  3. 傳 `runs` 給 `<ICConfigPanel>`（:493）。runs 空/載入/錯誤 → 對應 UI 提示。
- 修改檔案：`frontend/src/app/ic-analysis/page.tsx`。既有 caller：—。
- 不可做：不刪 fetchRegistry（過渡可並存，最終 D-3 不再用 registryEntries）。
- 邊界：runs=[]→「無可選 run，請先去 Feature Factory 生成」；runsError→error UI。
- 驗證（G-4 關聯）：mount 後 fetchRuns 被呼叫；三態渲染測試。

### Task D-3 — ICConfigPanel 批次分組 Run 下拉
- SPEC ref：[D-3]　目標：global/event 批次分組選 run。
- 實作要點：
  1. props 由 `registryEntries` 改 `runs: RunInfo[]`（刪 :56-96 symbol/tf 衍生）。
  2. 用 `runs` 依 `batch_alias` 分組（reduce 成 `{[batchKey]: RunInfo[]}`）；下拉 group label=batch_alias(或「未分組」)，item label=`formatRunLabel(run)`。
  3. onSelect(run)→`updateConfig({symbol:run.symbol, timeframe:run.timeframe, config_hash:run.config_hash})`。
- 修改檔案：`ICConfigPanel.tsx`（:23 prop、:45 default、:56-96 刪、:167-194 換）。既有 caller：page.tsx:491。
- 不可做：此 Task 不動 cross_sectional 分支（E-1）。
- 邊界：run 無 batch_alias→「未分組」群組；單 run 批次正常。
- 驗證：選 leaf→config 三件正確（vitest）。

### Task D-4 — 移除貼路徑欄
- SPEC ref：[D-4]　目標：刪三個手填路徑 input。
- 實作要點：1. 刪 `ICConfigPanel.tsx:150-164` features_path/labels_path/meta_path input。2. config.features_path 改由選 run 後不需手填（後端三件解析）。
- 修改檔案：`ICConfigPanel.tsx`。
- 不可做：不留隱藏殘留欄/dead state。
- 邊界：—
- 驗證：DOM query 無路徑 input（vitest）。

### Task D-5 — 啟動 gate
- SPEC ref：[D-5]　目標：未選 run 禁啟動。
- 實作要點：1. `runDisabled`（:113-121）加 `|| !config.config_hash`（global/event）；cross 模式 `|| !(config.cross_sectional_runs?.length)`。
- 修改檔案：`ICConfigPanel.tsx::runDisabled`。
- 不可做：—
- 邊界：未選→disabled；選後→enable。
- 驗證：未選 config_hash→啟動鈕 disabled（vitest）。

### Task D-6 — useICAnalysis payload 送 config_hash
- SPEC ref：[D-6]　目標：payload 帶 config_hash。
- 實作要點：1. `useICAnalysis.ts:165-170` payload 加 `config_hash: config.config_hash || undefined`。2. `hasLibrarySelection`（:126）= `Boolean(config.symbol && config.timeframe && config.config_hash)`（global/event）。3. features_path 不再手送（後端解析），或送 3 段 `parquet:{symbol}:{timeframe}:{config_hash}`。
- 修改檔案：`useICAnalysis.ts::startAnalysis`。既有 caller：page.tsx startAnalysis。
- 不可做：不破壞 cross 分支（E-2 改）。
- 邊界：無 config_hash→不啟動（接 D-5）。
- 驗證（G-4）：選 run 啟動→payload 含 config_hash。

**Phase D 測試**：G-4（wiring）、G-5（fetchAvailableFeatures setError）。**Gate**：`npm run test -- ic-analysis` + `npm run build` 綠。
**派工 prompt（Batch4，大）**：「實作 SPEC D-1..D-6，依賴 Batch1(A 契約)+Batch3(C list_features)。重點：ICConfigPanel global/event 改批次分組 Run 下拉、刪路徑欄、加啟動 gate；page.tsx 補 fetchRuns 三態；payload 送 config_hash。新增 vitest（現無 ic-analysis 測試）。跑 `npm run test` + `npm run build`。前端驗收須跑 vitest（教訓）。」

## Phase E — 前端橫截面批次選擇器（完成後：cross_sectional 選一批次→cross_sectional_runs）

### Task E-1 — cross_sectional 改選一個批次
- SPEC ref：[E-1]　目標：選批次=該批全 run。
- 實作要點：1. `ICConfigPanel.tsx:60-84,201-211` cross 分支改「批次下拉」（單選批次）。2. 選批次→`cross_sectional_runs = runs.filter(r=>r.batch_id===picked).map(r=>({symbol:r.symbol, config_hash:r.config_hash}))`；timeframe 從該批任一 run 取。3. 移除共同 tf 交集邏輯。
- 修改檔案：`ICConfigPanel.tsx`（cross 分支）。
- 不可做：—
- 邊界：批次只 1 symbol→可選但提示橫截面需≥2 symbol。
- 驗證：選批次→cross_sectional_runs 含該批全 symbol（vitest）。

### Task E-2 — useICAnalysis 橫截面 payload + anchor
- SPEC ref：[E-2]　目標：送 cross_sectional_runs。
- 實作要點：1. `useICAnalysis.ts` cross payload 送 `cross_sectional_runs`（取代/並存 symbols）。2. `page.tsx:116-159` crossSectionalFeatureCount anchor=cross_sectional_runs[0]。
- 修改檔案：`useICAnalysis.ts`、`page.tsx`。
- 不可做：—
- 邊界：cross_sectional_runs 空→不啟動。
- 驗證：橫截面啟動→payload cross_sectional_runs（vitest）。

**Phase E 測試**：橫截面 wiring。**Gate**：`npm run test` 綠。
**派工 prompt（Batch5）**：「實作 SPEC E-1/E-2，依賴 Batch2(B 契約)+Batch4(D 元件)。cross_sectional 改選一批次→cross_sectional_runs。跑 `npm run test`。」

## Phase F — training_timeframes 標籤（低風險收尾）

### Task F-1 — list_runs 補 training_timeframes
- SPEC ref：[F-1]　目標：/runs 吐 training[]。
- 實作要點：1. `feature_factory_service.py:811 list_runs`：讀 run manifest `timeframes.training` 填 `training_timeframes`。2. manifest 缺→None。
- 修改檔案：`feature_factory_service.py::list_runs`、`feature_factory_models.py::RunInfo`。
- 不可做：不每 run 重算特徵；不阻塞 list_runs（manifest 讀失敗→None 續行）。
- 邊界：manifest 不存在→None；training=[primary]→[primary]。
- 驗證：/runs 回傳含 training_timeframes（pytest）。

### Task F-2 — 選擇器顯示「1h(+12h)」
- SPEC ref：[F-2]　目標：leaf label 顯示合併 TF。
- 實作要點：1. ICConfigPanel leaf label：`training_timeframes` 含 primary 外其他→`{primary}(+{others})`。
- 修改檔案：`ICConfigPanel.tsx` label。
- 不可做：—
- 邊界：無 training/只 primary→只顯示 primary。
- 驗證：training=[1h,12h]→label 含 (+12h)（vitest）。

**派工 prompt（Batch6，小）**：「實作 SPEC F-1/F-2，依賴 Batch4。list_runs 讀 manifest training[] 補 RunInfo；選擇器 label 顯示合併 TF。manifest 讀失敗 graceful None。」

## Phase G — 測試（真實 3 批次，驗證保真度鐵律）

### Task [G-1] 消歧測試（同 symbol+tf 不同 config_hash）
- SPEC ref：[G-1]　修改檔案：`tests/api/test_ic_run_selector.py`（新建）。
- 實作要點：analyze(BTCUSDT,12h,`1c4b825...`) vs analyze(BTCUSDT,12h,`90f586...`)→feature sha256/row_count **不同**，且 **assert 選中 run identity.config_hash == 請求值**（codex#1：同 tf 才真測消歧）。
- 不可做：禁用不同 tf 充當消歧（會假綠）；禁合成 fixture。
- 邊界：兩 hash 不存在→skip 標記；相同→FAIL。
- 驗證：`pytest tests/api/test_ic_run_selector.py -k disambig`；sha256 不同 + identity==請求。

### Task [G-2] 向後相容 golden
- SPEC ref：[G-2]　修改檔案：`tests/api/test_ic_run_selector.py`。
- 實作要點：analyze(BTCUSDT,12h, 不帶 config_hash)→ 選中 config_hash/feature sha256/row_count/IC 聚合 == `tests/fixtures/ic_run_selector_baseline.json`。
- 不可做：不放寬容差換綠。
- 邊界：baseline 缺→FAIL（不靜默 pass）。
- 驗證：`pytest -k backward_compat`；全等 baseline，任一 diff=FAIL。

### Task [G-3] ML caller byte 不變（真 service）
- SPEC ref：[G-3]　修改檔案：`tests/momentum/test_feature_library.py` 或 `tests/api/test_cross_symbol.py`。
- 實作要點：spy/run `CrossSymbolTrainingService.run_cross_symbol_validation()`，凍結對 load_multi 的 call kwargs（for_training/allow_partial_training/feature_columns）+ service 輸出摘要 == baseline（codex#5：非只直接 load_multi）。
- 不可做：不改 ML caller 預設行為。
- 邊界：不帶 config_hashes→byte 不變。
- 驗證：`pytest -k cross_symbol`；kwargs + 輸出摘要 == baseline。

### Task [G-4] 前端 wiring
- SPEC ref：[G-4]　修改檔案：`frontend/.../ICConfigPanel.test.tsx`、`useICAnalysis.test.ts`（新建）。
- 實作要點：選 run→config→payload config_hash/cross_sectional_runs；page fetchRuns 三態（cursor#5）。
- 不可做：不只測「不拋錯」smoke。
- 邊界：runs 空/error 三態。
- 驗證：vitest `expect(payload.config_hash).toBe(run.config_hash)` + 三態渲染。

### Task [G-5] feature list error 態
- SPEC ref：[G-5]　修改檔案：`frontend/.../page.test.tsx`（新建）。
- 實作要點：fetchAvailableFeatures reject→`featuresError` 有值且 availableFeatures 不變 `[]`（cursor#5：featuresError 獨立欄，與 analyze error 不互蓋）。
- 不可做：不靜默 `setAvailableFeatures([])`。
- 邊界：reject vs 空清單區分。
- 驗證：vitest `expect(featuresError).toBeTruthy()`。

**Gate（最終）**：`pytest tests/api tests/momentum -k ic_run_selector` + `npm run test` + `npm run build` 全綠；§G 三 golden 通過。
**派工 prompt（Batch7）**：「實作 SPEC G-1..G-5。必用真實 kline_cache.h5 生成 3 批次，禁合成 fixture。G-1 證消歧（批次X≠Y）、G-2 向後相容 golden、G-3 ML caller 不變。輸出測試 pass/fail + golden diff。」

## 階段 3：自檢結果
- **追溯**：18 Task + 5 測試 + 3 Golden 全部落入上述 Phase（合計與階段 1 一致）。
- **深度**：每 Task 實作要點≥3 含偽碼/函式簽名、修改檔案到函式名、邊界≥2、驗證可證偽。
- **語義**：load/load_multi 改簽名的 caller（browser/ML/IC）皆有「optional 預設不變」同步策略；引用檔案/行號比對程式碼實見；測試測核心行為（消歧/向後相容）非 smoke。
- **全棧**：後端(A/B/C/F)→API(models/routes)→前端(D/E)→整合測試(G) 鏈完整；config_hash 契約前後端一致（A-1↔D-6、B-1↔E-2）。無空殼 Task。
- **錨點**：§0、§B、每 Task 含驗證/邊界/不可做 ✓。

## 階段 4：handoff
`SPEC=docs/IC_RUN_SELECTOR_SPEC.md TODO=docs/IC_RUN_SELECTOR_TODO.md FOCUS=config_hash 消歧正確性 + load/load_multi 共用路徑相容`
→ 用 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 雙家族（codex+cursor）獨立審查，Blocking 修補後才 Frozen。當前 Internal Frozen。
