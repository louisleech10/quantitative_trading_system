Round1 — 流式分層家族 獨立版

## 1. 記憶體/OOM 架構

核心主張：IC-analysis 不應再以 `pd.DataFrame` 作為主流程資料載體。現況 `momentum/Analysis/ic_filter_orchestrator.py:986-1014` 在 stage0 讀入整個 `features_df`，`1092-1152`/`1154-1202`/`1204-1230` 又把全矩陣傳進 stage4/5/6；這在 430,000 欄 × 20,000 列下不可救。新架構要改成：

- `FeatureMatrixSource`：只持有 `symbol/timeframe/config_hash/artifact_path/index/features_catalog/metadata/fingerprint`，不持有全矩陣。
- `ColumnChunkIterator`：以 `FeatureReader.load_columns_v2()` 做欄投影，按 feature columns 分塊讀取。
- `RowMaskPlan`：event filter、train/val/test split、valid-label mask 全部轉成 index/mask，不複製 feature matrix。
- `MetricSink`：IC/rolling/decay/quality 結果 append-only 寫入 Parquet/SQLite/Arrow IPC，支援 resume/retry。
- `CandidateSet`：stage4/5 後只保留通過閾值或 top-K feature 名單，stage6/deep modules 僅允許對候選集讀矩陣。

記憶體模型：

- 原始矩陣：430k × 20k float32 ≈ 34.4GB；float64 ≈ 68.8GB。
- pandas 實務開銷 2-3x，含 index/block manager/中間 rank/copy 後，float32 全量會落在 70-120GB，float64 可到 140-220GB。
- rolling IC 現況 `ic_engine.py:268-302` 會產生 ranked matrix + numpy copy + corr matrix + Python dict/list，實際比原矩陣更糟。
- grouped IC 現況 `ic_engine.py:365-390` 對每 group 做 `.loc` 副本，會再放大全矩陣壓力。
- cross-sectional 現況 `api/services/ic_analysis_service.py:135-154` 對多 symbol `pd.concat(frames)`，再交給 `analyze_cross_sectional()`；100 symbol 等於把災難乘上 100。

建議 per-tier chunk：

| Tier | 欄 chunk | raw float32 | pandas+rank+rolling 安全預估 | 並行 |
|---|---:|---:|---:|---:|
| 8GB | 512 欄 | 41MB | 0.4-0.9GB | 1 worker |
| 16GB | 1,024 欄 | 82MB | 0.8-1.8GB | 1-2 workers |
| 24GB | 2,048 欄 | 164MB | 1.6-3.6GB | 2 workers |
| 32GB | 4,096 欄 | 328MB | 3.2-7.2GB | 2-3 workers |

保守上限：單 worker 峰值不得超 tier RAM 的 35%；多 worker 總峰值不得超 60%。8GB tier 跑 430k 欄約 840 個 512-column chunks；這慢，但穩定、可 resume。resume key 必含 `symbol/timeframe/config_hash/stage/chunk_id/feature_names/input_fingerprint/config_hash`，禁止 stale cache。

## 2. 逐 stage/模組改法

Stage0 ingestion：改 `ic_filter_orchestrator.py:986-1014`。不回傳 `features_df`，改回傳 `FeatureMatrixSource`、`labels_source`、`metadata`、`feature_catalog`。`_validate_input()` 拆成 chunk validator：每 chunk 檢查 NaN/inf/all-null/constant/index alignment，結果寫 `stage0_validation.parquet`。不得 drop 後物化新 DataFrame，只輸出 `valid_features`.

Stage1 preprocessing：`_stage1_preprocessing()` 現在整表呼叫 preprocessor。改為 chunk streaming；若 preprocessing 需要全欄獨立統計，逐欄計算即可；若需要跨欄統計，必須標記為 `requires_candidate_set`，延後到 stage6 後。任何 rank/zscore rolling 必須 PIT，只用當下及過去窗口。

Stage2 label：保持單序列，20k rows 很小。強制 label index 與 feature index byte-faithful 對齊；生成 future return 時確認 feature timestamp t 對應 label t+h，不可把 label shift 回填到未來。輸出 `label_fingerprint`.

Stage3 event_filter：`ic_filter_orchestrator.py:1057-1090` 改為只產生 `row_mask/index_selector`。若 raw kline 可用，繼續基於 raw_data；若 query 需要 feature 欄位，僅讀 query 所需欄，不讀全矩陣。

Stage4 IC：`1092-1152` 改成 chunk engine。每 chunk 讀 `X_chunk`，套 row mask，對每 feature 計算 exact Spearman/Pearson IC、rolling IC summary、ICIR、autocorr。Spearman 可對 chunk 內每欄全 20k rows exact rank，不需要全 430k 欄同時在記憶體。rolling 結果不要以現況 dict/list 全量保存；只保存 per-feature summary，加 `retain_rolling_series_for_top_n`，預設僅 top 500 或候選集保留序列供 centrality/trend。

Stage4 decay：`ic_engine.py:331-363` 現在 horizon × full matrix + per-feature loop。改為 horizon label 先生成小矩陣，chunk 內一次算所有 horizons；`_fit_exponential_decay` warning 聚合成 `{reason: count, examples: [first 20]}`，禁止 14k hot-loop warnings。

Stage4 grouped：`ic_filter_orchestrator.py:1134-1139` 先修 pydantic GroupedConfig 傳 dict 的 crash：`model_dump()`。`ic_engine.py:1018-1045` timestamp unit 不能固定 `ms`，要用實測判斷：數值 < 10^11 視為 seconds，>= 10^11 視為 ms，並把 source/unit 寫入 report。`by_volatility` schema 若預設 true，compute 必須實作或 fail-closed 說 unsupported，不可靜默忽略。grouped IC 改為 group row masks × column chunks，不 `.loc` 全矩陣。

Stage5 statistical_validation：`1154-1202` 拆成兩層。FDR/p-value/ICIR/coverage/turnover/monotonicity 全部可 per-feature streaming；結果表 append-only。monotonicity 需要 quantile buckets，但每 feature 獨立，chunk 可做。FDR 需要所有 p-values，但只需 430k rows 的 metric table，不需 feature matrix。

Stage6 redundancy：`1204-1230` 是第一個明確需要跨 feature 關係的 stage。硬規則：不得對 430k 做 corr/VIF。必須先以 stage5 產生 candidate set，例如 `max_candidates_for_redundancy`: 8GB=500、16GB=1,000、24GB=2,000、32GB=3,000；超過就按 ICIR/FDR/coverage/metadata diversity 排序截斷，並在 report 標記 `redundancy_input_truncated=true`。corr 是 O(k²)，VIF/orthogonalization 近 O(k³)，k 必須被配置上限保護。

Stage7 report：只讀 metric tables 和 candidate metadata。完整 430k summary 可落盤成 Parquet/CSV artifact；API response 預設只回 `top_n_features`、threshold counts、artifact paths、fingerprints、quality summary。不要把全量 summary JSON 塞 WebSocket。

Deep 10 模組：

- factor_return `ic_filter_orchestrator.py:750-756`：僅對 selected/candidate features 讀 chunk；long-short 分位可 per-feature streaming。
- factor_centrality `758-783`：只能基於 retained rolling IC matrix；O(k²)/PCA，k 上限 500-2,000。不可對 430k。
- trend_analysis `785-798`：基於 rolling IC series，候選集可跑；全量只允許 summary trend，不保留全部序列。
- parameter_sensitivity `800-807`：需要 metadata family grouping，可 streaming，但只對 candidate families；全量僅做聚合統計。
- rolling_oos `809-815`：時間切片 × feature 獨立，可 chunk；但輸出只保留候選。
- factor_orthogonalization `817-835`：PCA/Gram-Schmidt 是 O(k²~k³)，必須 candidate-only，8GB 建議 k<=300，32GB k<=1,000。
- factor_exposure `837-890`：目前 `positions = 1.0 / len(factor_values)` 邏輯疑似把 row count 當 feature count，需先審；只允許 candidate matrix。
- long_short `892-898`：per-feature 可 chunk；輸出 top/bottom summary。
- quality_diagnostics `900-911`：ADF 等 per-feature 可 chunk；rolling_ic dict 只讀 retained set。
- net_ic `913-927`：只用 summary + turnover，天然輕量。

Cross-sectional：`api/services/ic_analysis_service.py:135-154` 不能 concat 多 symbol。改為 timestamp-major 或 feature-chunk-major：

- 每個 symbol 獨立 reader，按同一 feature chunk 讀該 symbol 的 20k rows。
- 對每 timestamp 聚合同 feature across symbols 計 rank corr。
- 記憶體約 `symbols × rows × chunk_cols`，100 × 20k × 512 float32 = 4.1GB raw，不適合 8GB。
- 8GB 改用 feature subchunk 64-128 欄，或 timestamp blocks 1,000 rows：100 × 1,000 × 512 = 205MB raw。
- cross-sectional 必須保證 symbol 來源隔離：每個 symbol/config_hash 獨立 fingerprint，不可 merge cache key 只靠 timeframe。

## 3. 數據品質/無洩漏

PIT 保護：

- feature timestamp、label horizon、raw kline timestamp 三者必須在 stage0 寫入 `time_axis_audit`。
- `_get_time_index()` 修正 seconds/ms 判斷，並對 sample min/max 做 sanity check；若轉出 1970 或未來異常日期，fail-closed。
- label generation 僅允許 `future_return(t,t+h)` 作為 label，feature preprocessing 不得使用 t+h 後資料。
- rolling zscore/rank/neutralization 必須 left-closed/right-current，禁止 centered windows。

Train/val/test：

- stage4 可在 train split 上選因子，val 用於 threshold calibration，test 只報一次 holdout IC，不參與 feature selection。
- FDR 閾值與 redundancy ranking 不得用 test 結果。
- rolling_oos 必須 purged/embargo，horizon h 對應至少 h bars purge。

跨 symbol 隔離：

- 所有 artifact key：`symbol/timeframe/config_hash/artifact_kind/input_fingerprint/code_version/config`。
- cross-sectional run key 另含 sorted `(symbol, config_hash, fingerprint)` list hash。
- 禁止把單 symbol feature_filter/cache 套到另一 symbol；resume chunk 必須核對 symbol-level fingerprint。

NaN/inf gate：

- 不弱化現有 gate。chunk validator 必須產生全量 feature 的 NaN/inf/constant 統計。
- early-skip 只能 skip 已證明 invalid 的 feature；任何因記憶體/時間跳過的 feature 必須標 `not_evaluated`，不能算 failed 或 passed。

## 4. 算時/輸出

算時：

- IC 主計算用 numpy/numba chunk kernel，避免 feature-by-feature Python loop。
- Spearman：chunk 內 `rank(axis=0)` 後矩陣化 corr；Pearson 直接中心化矩陣乘 label。
- rolling corr 用 prefix sums / rolling window sums，避免每窗口 pandas corr。
- 多 worker 以 process pool 或 thread pool 視 HDF5 reader thread-safety 決定；每 worker 持有獨立 reader。
- decay horizons 合併計算，不做 horizon × full DataFrame。
- logs 改成每 chunk 一條 INFO、每 warning reason 聚合一條。

輸出：

- API response 預設：top 30、counts、threshold log、artifact paths。
- full 430k metric table：Parquet + optional compressed CSV，不進 WebSocket JSON。
- rolling series：只對 top retained set 輸出；全量輸出 rolling summary。
- corr heatmap：只對 redundancy candidate 或 final selected，不對全量。
- deep report：module-level summary + per-feature top-N，完整表落盤。

幽靈 `feature_filter`：

- 前端 `frontend/src/store/icAnalysisStore.ts:182-187` 和 hook `frontend/src/hooks/useICAnalysis.ts:156-159` 送 `max_features=30`。
- API model 有 `api/models/ic_models.py:8-15`，service 只塞 override `api/services/ic_analysis_service.py:967-970`。
- 核心 `momentum/Analysis/ic_config_schema.py:319+` 沒 `feature_filter`。
- 修法：新增核心 schema `FeatureFilterConfig`，stage0 catalog 層先做 metadata/pattern/include/exclude 過濾；`max_features` 只能是「使用者明確要求只分析 top catalog order N」或「UI preview limit」，不能靜默當品質篩選。若要完整語義，預設應分析全部，`max_features=30` 應改名 `preview_limit` 或 fail-closed 要求確認。

## 5. 正確性代價

無語義改變：

- column chunk exact IC、exact Spearman rank、exact FDR、exact per-feature coverage/turnover/monotonicity，在數值上應與現況一致。
- stage0 不物化全矩陣不應改結果，只改執行形態。
- grouped IC 改 row mask × chunk 也應保持一致，前提 timestamp unit 修正後 golden 要更新為正確值。

有代價/需明示：

- stage6 candidate truncation 會改 redundancy/VIF/corr 語義，因為它不再在所有通過 stage5 的 features 上找冗餘。這是必要保護，必須在 report 標記。
- centrality/orthogonalization/PCA candidate-only 會漏掉未入候選的 crowding/共線關係；可接受但要文件化。
- rolling series 只保留 top-N 會限制 deep trend/centrality 的全量分析；全量 summary 不受影響。
- 若採用 approximate correlation screening，例如 sketch/random projection，只能作 optional exploratory mode，不能作 default gate。
- `max_features` 若提前截斷會漏因子，不能預設用於正式 IC gate。

Golden 測試：

- 小矩陣 golden：現有 pandas full path vs streaming path byte/rtol 一致。
- 430k synthetic metadata-only stress：不 fake market values，但可用 deterministic numeric matrix 測 OOM 行為；資料正確性 golden 必須用真實 kline/feature artifact。
- timestamp golden：seconds/ms/open_time/DatetimeIndex 四種真實路徑。
- resume golden：中斷 chunk N 後重跑，不重算已完成 chunk，結果 hash 一致。
- no-stale-cache golden：改 config/input fingerprint 後舊 chunk 不可命中。
- cross-symbol isolation golden：兩 symbol 同欄名不同 fingerprint 不可混用。

## 6. 落地 epic 切分 + 優先序

Epic A：止血與正確性 crash，對應準則 1/2/3  
修 `GroupedConfig.model_dump()`、timestamp unit、`by_volatility` fail-closed/實作、decay warning 聚合、主 API 統一 `asyncio.to_thread`。這些是低風險且立即降低崩潰與 WS 假死。

Epic B：feature_filter 合約修正，對應準則 3  
核心 schema 加 `feature_filter` 或把 UI 的 `max_features` 改名 preview。正式分析不得讓使用者以為只跑 30 實際跑全量。

Epic C：Stage0 catalog source + chunk reader，對應準則 1/2  
建立 `FeatureMatrixSource`、feature catalog、fingerprint、chunk manifest。`analyze()` 先走 streaming skeleton，但可保留小資料 fallback。

Epic D：Stage4 streaming IC engine，對應準則 1/2/4  
實作 chunk exact IC、rolling summary sink、decay grouped chunk 化。這是最大收益點。

Epic E：Stage5 streaming validation + report artifacts，對應準則 1/3/5  
把 summary table 從 in-memory dict/list 改為 artifact-backed metric table，API 只回 top-N。

Epic F：Stage6/deep candidate-only contract，對應準則 1/4/6  
對 corr/VIF/PCA/centrality/orthogonalization 加硬上限、report truncation disclosure、golden 覆蓋。

Epic G：Cross-sectional streaming redesign，對應準則 2/3  
移除 `pd.concat(frames)`，改 symbol readers + timestamp/feature block aggregator，多 symbol fingerprint 隔離。

Epic H：Perf tuning，對應準則 4/5  
Numba/prefix sums/worker pool/compressed Parquet。只在 A-G 保護後做。

## 7. 風險與不確定點

- `FeatureReader.load_columns_v2()` 的 HDF5 thread/process safety 未驗證；並行策略需實測。
- 現有 `_load_features_hdf5()`、FeatureLibrary artifact layout 未完整讀完；catalog 是否能免讀全矩陣需確認。
- stage1 preprocessor 是否含跨欄操作未知；若有，需逐一分類為 streaming-safe 或 candidate-only。
- quantile monotonicity/turnover 的現有實作細節未逐檔審，可能有隱藏全矩陣 copy。
- centrality/orthogonalization candidate truncation 是必要但會改 deep semantics，需產品層接受。
- cross-sectional 在 100 symbols × 430k features 下即使 streaming 也很慢；可能需要先做 per-symbol IC 粗篩再找共通性，但這會引入漏因子風險，不能當唯一正式 gate。
- pandas exact rank 與 scipy tie handling 必須 golden 鎖住；改 numba 後 tie/NaN 行為很容易偏。
- 输出最小化若改 API response schema，前端與既有使用者可能受影響，需版本化或兼容欄位。
- READ-ONLY：未更新 `HANDOFF.md` 或 `handoffs/*`。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md，抽查 ic_filter_orchestrator.py、ic_engine.py、ic_config_schema.py、ic_analysis_service.py、icAnalysisStore.ts、useICAnalysis.ts、ic_models.py 關鍵行；未執行測試或載入 data_cache。  
TESTS_RUN: none，read-only 架構審查。  
FAILURES_SEEN: none。  
SCOPE_CHANGES: none。  
NUMERIC_OR_SCHEMA_IMPACT: 方案建議未改檔；若落地會涉及核心 schema、API response artifact 化、timestamp 行為修正，需 golden 驗證。  
HANDOFF_NOT_UPDATED: 使用者明示 READ-ONLY 且要求直接輸出方案，不改 repo 檔。  
STATUS: DONE