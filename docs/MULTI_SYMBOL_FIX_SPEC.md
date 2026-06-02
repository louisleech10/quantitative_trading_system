# 多 Symbol 批次修復 — SPEC（V13 格式，2026-06-02 重生成）

> 來源 PLAN/診斷：`docs/MULTI_SYMBOL_DIAGNOSIS_20260601.md` + `docs/MULTI_SYMBOL_FIX_MANIFEST.md`　|　日期：2026-06-02　|　對應 TODO：`docs/MULTI_SYMBOL_FIX_TODO.md`
> 執行者：執行端（codex / cursor）；驗收：Claude（diff + pytest + 摘要）。已過規劃委員會（C1/C2/C3）。

## §RISK 風險分級
- 大小：**大**。
- 命中高風險原則：**(a)** 動資料品質（[P2-4] 品質計算）；**(b)** 多 symbol 共用路徑（batch service / preprocessor）；**(d)** ML 正確性（[P4-2] 改 L6.5 IC-First 路由）。
- → §G Golden 必填、adversarial review 必跑（雙家族 GPT-5.5 + Composer 2.5）。

## §A 假設與待使用者確認
- 已驗證事實：tier=8GB（psutil 實測）；輸出格式=parquet+manifest 無 .h5（ls 實測）；`FeatureFactory.generate_features` 內 IC-First 由 config `preprocessing.ic_first_pipeline` 路由（feature_factory.py:1700 實測）。
- **誠實校正（adversarial 收斂 #1，C3 類前提誇大）**：**batch 入口尚未共用**——`feature_factory_batch_service.py:358-362` 仍用 `get_multi_symbol_ic_first_enabled()` 在 `_compute_single_ic_first`（另設 `FFACT_IC_FIRST_PIPELINE=1` + `create_feature_factory_for_ic_batch`，L770-805）vs `_compute_single` 間切換。「config 共用」≠「batch/single 入口已共用」。**P4-2 是移除這層平行入口，非低風險、須 §G golden gate**。
- 待確認：無（下列已向使用者確認，但**標 log-unverified**：僅使用者口述，未從 0601 request body / config_hash 交叉驗證）。
- 已確認結果（user-confirmed, log-unverified）：① IC-First=0530 單 與 0601 多 兩次都選（使用者 2026-06-02；待 P4-1 凍結時附兩次 run 的 config JSON/hash 佐證，診斷線索：batch `8440d93` vs 12h `b86fa71`）；② browse id 語義=B latest-overwrite（使用者 2026-06-02）；③ 未來需支援 concurrent>1（使用者要求 C2，2026-06-02）。

## §C 約束
- 解耦 7 條：`grep "from api\." momentum/`→0；**服務不互 import**（[P2-2] batch service 經注入用 feature_factory_service，禁直接 import）。
- 不可違反原則：不弱化 NaN·inf gate、不擅改輸出大小、多 symbol 不 OOM、跨 tier 可重複。
- 本任務共用路徑：`feature_factory_batch_service.py`、`feature_preprocessor.py`、`momentum/core/config.py`、`feature_factory_service.py`、前端 store/page。

## §G Golden / Baseline（[P4-1]，C3 數值不漂移客觀 gate）
- 凍結時機/reference：[P4-2] 動工前。reference 主集=`BTCUSDT 1h` + 本次 config（L1 trend-only、L2-6.5 同 0530、`ic_first_pipeline=true`）；**+ 三 symbol smoke**（ETH/BTC/DOGE 1h 的 feature 名稱集 sha256 + schema 一致，抓 symbol 特異 cache/路徑 bug，adversarial #分歧）。
- **存放位置：`tests/fixtures/golden/multi_symbol_c3/`（非 `data_cache/`，避開 AGENTS 紅線，adversarial 收斂；可 commit/審查）**。
- baseline 內容（須擋局部漂移，非只 aggregate；adversarial 收斂 #3）：
  ① feature 名稱集合 sha256；② 數量/bar/schema；③ 每 feature mean/std/nan_ratio；
  ④ **每 feature 全量 deterministic chunk hash**（按 index 排序、float64 canonicalize 後 sha256；非稀疏抽樣，未抽樣 row 的局部漂移也擋）；⑤ NaN mask hash；
  ⑥ **凍結時記錄環境**：`FFACT_MULTI_SYMBOL_IC_FIRST`/`FFACT_IC_FIRST_PIPELINE` 值 + 實際 `compute_fn` 名 + config_hash（確保改前 baseline 與實際路徑一致，adversarial #1）。
- 通過條件（可證偽，容差分尺度）：nan_ratio exact；mean/std/全量 value `abs<=1e-8 或 rel<=1e-6`（大尺度欄位用 rel-only；float32 路徑 atol=1e-5 並文檔化例外）；超出列該 feature+row+diff = FAIL。**改前==改後、單==多(1 symbol) 對照一致**。

## §P Phase 與依賴
> 自檢：每 Task 輸入來源見下；無「依賴尚未完成的後續 Phase」。Phase 序：1（無依賴）→ 2（注入 seam 接回）→ 3 → 4（最後，需 §G）。

### Phase 1 — 低爭議群（依賴：無）
**`[P1-1]` 多 symbol 輪詢統一**
- 檔案：`frontend/src/store/featureFactoryStore.ts` → `pollBatchStatus()`（L617-639）。既有 caller：GenerationProgress 路徑不變。
- 改法：移除 `maxAttempts=600` 上限，跑到 completed/failed/partial 才停（對齊單 symbol `setInterval`）；網路 5xx 才設 error（退避重試）。
- 驗證：mock fetch 連續 running >600 次後 completed，斷言不提早設逾時 error 且 `batchTask.status=='completed'`；`npm run build` pass。
- 邊界：網路 5xx→surface 不靜默；任務 failed→停輪詢。
- 不可做：不得刪既有 error 處理換取簡化。

**`[P1-2]` current_symbol 賦值時機**
- 檔案：`feature_factory_batch_service.py` → `_process_item_wave()`（L342-402，submit 迴圈 L365-375）。
- 改法：item submit **前**設 `task["current_symbol"]/current_timeframe` + `_notify_progress`；**`_record_item_result`(L419) 必須移除/改 `task["current_symbol"]=symbol` 那行**（adversarial：完成路徑仍覆寫會讓 UI 又顯示「剛完成」），完成時只更新 metrics，不覆寫進行中 current。
- 驗證：`pytest tests/api/` 擴充——2-symbol 序列(concurrent=1)，第 2 個 submit 後完成前讀 `get_status()`，斷言 `current_symbol == 第2個`（!= 第1個）；斷言 submit 時 _notify_progress 被呼叫。
- 邊界：concurrent>1 時 current=wave 內最後 submit（單值，保型別）；wave 空→不更新。
- 不可做：不得移除完成時的 metrics 紀錄。

**`[P1-3]` 子進程 log 回收（JSONL）**
- 檔案：`feature_factory_batch_service.py` → `_process_item_wave`/`_compute_single*`（子進程）。
- 改法：每 symbol 完成輸出一行 JSONL `{symbol,timeframe,pid,peak_rss_mb,duration_s,status}` 至**固定路徑** `{checkpoint_dir}/{task_id}/child_metrics.jsonl`（QueueListener 或 per-pid 檔避免交錯；列入 checkpoint cleanup）。**child hard crash 在寫檔前（adversarial 分歧）→ 由 parent 在 `_wait_one` exception path 補寫 status=failed 一筆**（child 只回傳 pid/rss/duration）。
- 驗證：`pytest` 跑 2-item batch，讀 `{checkpoint_dir}/{task_id}/child_metrics.jsonl`，斷言每 symbol 一筆、欄位齊、status∈{ok,failed}、每行 json.loads 成功（不靠 substring）。
- 邊界：子進程 crash→status=failed 仍出一筆；並發寫不產生損毀行（assert 可 json.loads 每行）。
- 不可做：熱迴圈不得逐列 log。

**`[P1-4]` registry 去重**
- 檔案：`momentum/FeatureEngineering/feature_registry.py`（`DEFAULT_REGISTRY_PATH` L16，save/append 方法）。
- 改法：以 (symbol,timeframe,config_hash) 為 key upsert（更新 feature_count/created_at/path），不 append 重複。
- 驗證：`pytest` 同 key register 兩次後斷言 `len(registry)==1` 且值為最新；不同 config_hash 各保留（斷言 ==2）。
- 邊界：空 registry→正常新增；不同 config_hash 視為合法多版本不刪。
- 不可做：不得刪不同 config_hash 的歷史條目。

### Phase 2 — 注入 seam + C1 + 品質 loader（依賴：Phase 1 接回）
**`[P2-1]` browse id 統一 = B latest-overwrite**
- 檔案：`feature_factory_service.py` `register_hdf5_for_browse`(601) 與 `_restore_persisted_tasks`(3718)。
- 改法：兩處統一 `browse_{symbol}_{timeframe}`（**去掉 3718 的 _hash8**，不含 config_hash）；舊 _hash8 task restore 時映射到無 hash id 或忽略（下次生成覆蓋）。
- 驗證：`pytest` 斷言 register 與 restore 對同 (sym,tf) 產生**相同** id（== `browse_{sym}_{tf}`）；重啟（重建 service）後 `get` 拿得到；同 symbol 重生成覆蓋為最新。
- 邊界：舊格式 _hash8 殘留→不 crash；不同 tf 各自 id。
- 不可做：不得引入 config_hash 進 id（已定 B）。

**`[P2-2]` 注入 seam（Protocol，adversarial 收斂 #4：grep 單檔可繞過，須結構保證）**
- 檔案：`momentum/core/protocols.py`（介面）；`api/services/` 新 adapter（可 import service）；`api/main.py` lifespan 注入；`feature_factory_batch_service.py` 建構子收注入。
- **Protocol 簽名（明定，免假合規）**：
  `class IBrowseRegistrar(Protocol): def register(self, symbol: str, timeframe: str, manifest_path: str) -> str: ...`
  `class IQualityComputer(Protocol): def compute(self, manifest_path: str) -> dict: ...`
- 改法：adapter（如 `FeatureFactoryBrowseAdapter`/`...QualityAdapter`，放 `api/services/`）包 `feature_factory_service` 私有方法；**composition root = `api/main.py` lifespan** `FeatureFactoryBatchService(browse_reg=..., quality=...)`；batch service **不 import 任何 `api.services.*`（settings 除外）**。
- **browse adapter 須處理 manifest 格式（adversarial 收斂，與 P2-4 同根）**：先查 `register_hdf5_for_browse`(service.py:~596) 是否用 `h5py.File`；batch 傳的是 manifest path（`result.hdf5_path` 實為 manifest，batch L763/806）→ 若 register 走 h5py 會 FileNotFoundError/假註冊。adapter `register` 須走 manifest/parquet loader（或新增 `register_manifest_for_browse`），**不得把 manifest 丟進 h5py**。
- **既有 caller 同步（adversarial 收斂，免打爆啟動/CI）**：`get_feature_factory_batch_service()`(L1007)、`api/main.py`(L53)、`tests/api/test_feature_factory_batch_*.py` 多處直接 `FeatureFactoryBatchService()`。改 fail-closed 須同步：main.py lifespan 建 adapter 注入；`conftest`/fixture 提供 mock 注入；禁裸 construct。
- **lazy singleton fail-closed**：`get_feature_factory_batch_service()` 無注入時 `raise`（非靜默空殼預設）；測試經 fixture 注入 mock。
- 驗證：① `grep -rE "from api\.services|import api\.services|get_feature_factory_service" api/services/feature_factory_batch_service.py` → **0 行**；② `./scripts/check_decoupling_phase4.sh` PASS；③ `pytest tests/api/` 全綠（caller 同步後）；注入 None → raise、mock → 正常；④ browse adapter 用真實 parquet+manifest fixture 註冊成功（非 h5py 假註冊）。
- 邊界：注入缺失→fail-closed raise；adapter 在 api 層可 import service（合法）。
- 不可做：batch service 不得 import 任何 `api.services.*`（lazy/別名/runtime singleton 皆禁）；不得把 manifest 丟 h5py。

**`[P2-3]` 後端 per-item browse 註冊**
- 檔案：`feature_factory_batch_service.py` → `_record_item_result()` 成功分支（`error is None and hdf5_path`）。
- 改法：經 [P2-2] 注入 registrar `register(symbol,timeframe,manifest_path)` 註冊（傳的是 manifest path，見 P2-2 契約）；`browse_task_id` 寫 checkpoint `completed_items[]`。
- **response schema（adversarial 收斂，免破舊 caller）**：`get_status()` **保留** `results: Record<str,str>` 不動形狀；**新增** `browse_task_ids: Record<str,str>`；同步 `api/models/feature_factory_models.py` + 前端 TS types。
- 驗證：`pytest` 2-symbol batch（mock compute 回 fixture manifest），斷言 registrar 呼叫數==成功數、checkpoint browse_task_id 非空、`get_status().browse_task_ids[sym]` 非空且 `results` 形狀不變；清 `self._tasks` 後 `_restore_persisted_tasks` 仍可 browse。
- 邊界：失敗 symbol 不註冊；concurrent>1 同 wave 去重同 (sym,tf)。
- 不可做：不得依賴前端事後註冊。

**`[P2-4]` 品質 loader（h5py → parquet/manifest）**
- 檔案：`feature_factory_batch_service.py` → `_compute_symbol_quality()`（L912-965）。
- 改法：經 [P2-2] `IQualityComputer` 複用 `feature_factory_service._build_data_quality_cgsa`（L2045）/`_fast_quality_alerts`（L2930），不重寫不直接 import；回傳欄位與前端 BatchQualityOverview 契約不變。
- 驗證：`pytest` fixture manifest 目錄回 grade∈{pass,watch,reject}、feature_count 與 manifest 一致；**G2 golden**：與單 symbol `_build_data_quality_cgsa` 對同目錄 nan_ratio_mean/constant_count/grade 一致（abs<=1e-9，grade 同）。
- 邊界：失敗 symbol 不得當 pass；空目錄→回 None 不 crash。
- 不可做：不得用 h5py 開 parquet/manifest。

**`[P2-5]` 前端讀後端 browse id**
- 檔案：`frontend/src/app/feature-factory/page.tsx` → `handleSelectBatchSymbol()`（L110-130）。
- 改法：優先用 `batchTask.results[sym].browse_task_id`（後端已註冊），缺才 fallback register。
- 驗證：store/page unit test——有 browse_task_id 時不 call register（斷言 fetch 未呼叫 register endpoint）；缺則 fallback；更新 TS response type；`npm run build` pass。
- 邊界：舊 batchTask 無新欄位→fallback 仍可用。
- 不可做：不得移除 fallback 路徑。

### Phase 3 — C2 worker 預算（**派工依賴：與 Phase 1/2 同改 `batch_service`/`preprocessor`，不得與 Phase 1/2 並行派工,須序列接回避免衝突**，adversarial 分歧；整包包 `FFACT_PARALLEL_BUDGET` flag 預設 off）

> **flag/語義 truth-table（adversarial 分歧，免執行端混淆）**：
> | 情境 | FFACT_PARALLEL_BUDGET | FFACT_BATCH_NESTED | tier | concurrent | 預期 n_jobs |
> |---|---|---|---|---|---|
> | 單 symbol（不經 batch） | n/a | n/a | 16GB | n/a | 4（既有行為不變） |
> | batch, flag off（預設） | off | — | 任意 | 任意 | **1（== 現狀）** |
> | batch, flag on | on | unset | 16GB | 1 | 4 |
> | batch, flag on | on | unset | 16GB | 2 | 2 |
> | batch, flag on, 運維覆寫 | on | 1 | 任意 | 任意 | **1（強制安全）** |
> | batch, flag on | on | unset | 8GB | 任意 | 1（<12GB gate） |
> RSS 上限：per-tier 取 `tier_gb * 0.6` 為總 RSS 軟上限（保守），超過降載 concurrency→1。
**`[P3-1]` get_slowpath_n_jobs 並行感知**
- 檔案：`momentum/core/config.py` → `get_slowpath_n_jobs()`（L259-275）。
- 改法：簽名加 `concurrent_symbols: int = 1`（預設 1 不破壞單 symbol）；`return max(1, tier_cap // concurrent_symbols)`，先受 `get_slowpath_parallel_enabled()`（<12GB→1）、Windows→1。
- 驗證：`pytest` 斷言 `get_slowpath_n_jobs(16,1)==4`、`(16,2)==2`、`(32,4)==2`、`(8,1)==1`、下限>=1；無參數呼叫端行為不變。
- 邊界：concurrent_symbols=0→當 1（max 保護）；非整數→既有 fallback。
- 不可做：不得移除 <12GB gate。

**`[P3-2]` 子進程接收 concurrency + peak RSS 守門**
- 檔案：`feature_factory_batch_service.py` `_process_item_wave`；`momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` `_resolve_slowpath_n_jobs`（L2859）。
- 改法：父進程 submit 前設 `FFACT_BATCH_SYMBOL_CONCURRENCY={len(item_wave)}` env；`_resolve_slowpath_n_jobs` 讀並傳入 `get_slowpath_n_jobs(tier, concurrency)`；`FFACT_BATCH_NESTED` 改「運維強制安全模式」；整體受 `FFACT_PARALLEL_BUDGET`（off==現狀 n_jobs=1）；BLAS/Numba/Polars thread 封頂（OMP_NUM_THREADS/POLARS_MAX_THREADS）。
- **RSS 降載時點（adversarial 分歧，submit-all wave 結構）**：超 RSS 軟上限**只影響下一 wave**（寫 checkpoint `concurrent_symbols=1`），不中止已 submit 的當前 wave（避免不可控 kill）。
- 驗證：`pytest` concurrency=1@16GB→`_resolve_slowpath_n_jobs`==4、=2→2、8GB→1；顯式 `FFACT_BATCH_NESTED=1` 仍 1；flag off→全程 1；**peak RSS 測試**：16GB concurrency=2 記 per-child+父總 RSS，斷言 <= tier 上限，超則降載 concurrency→1。
- 邊界：RAM gate 觸發→拒新任務；memory_sanity_failed→降 concurrent；IC-First config→force concurrent=1。
- 不可做：不得移除 RAM gate / memory_sanity / IC-First force 1。

### Phase 4 — C3 IC-First 清理（依賴：§G golden 必先凍結；最後做）
**`[P4-1]` 凍結 G1 golden**（見 §G；前置於 [P4-2]；adversarial 收斂：須可重現+config 可審計,非自我參照）
- **前置子步驟（adversarial 收斂，免自我參照）**：先取得**真實可審計的 reference config**——從 0530/0601 run artifact 或 registry config_hash 還原 `config.json`（含 config_hash）；**取不到 → BLOCKED，要使用者提供，不准自造 baseline freeze**。
- 檔案：新增 `scripts/golden_multi_symbol_c3.py`（`freeze` / `compare` 兩子命令）。
- **可重現規格（寫死，免空殼）**：
  - config 來源：`tests/fixtures/golden/multi_symbol_c3/config.json`（L1 trend-only、L2-6.5 同 0530、`ic_first_pipeline=true`；含 config_hash）。
  - 生成：`python scripts/golden_multi_symbol_c3.py freeze --symbol BTCUSDT --tf 1h --config tests/fixtures/golden/multi_symbol_c3/config.json`
    → 產 `tests/fixtures/golden/multi_symbol_c3/baseline.parquet`（§G ①-⑤ 指紋）+ `env_snapshot.json`（§G ⑥）。
  - 比對：`python scripts/golden_multi_symbol_c3.py compare --baseline tests/fixtures/golden/multi_symbol_c3/baseline.parquet`
    → 輸出 `PASS` 或 `FAIL` + 漂移 (feature, row, abs_diff, rel_diff) 清單。
  - 抽樣/canonicalize spec：全量 chunk hash（無抽樣盲區）；float64 round 到 rel 精度後 sha256；index 排序固定。
- 驗證：執行 freeze 產出上述檔（`ls` 確認存在）；compare 對未改 code 回 PASS；對人工注入 1e-3 漂移回 FAIL 並列出該 feature。
- 邊界：baseline 缺→compare raise 明確錯誤要求先 freeze；env_snapshot 與當前 env 不符→compare 警告（路徑可能變）。
- 不可做：不得在 [P4-2] 動工後才建 baseline；不得寫入 `data_cache/`。

**`[P4-2]` 移除重複 IC-First 機制，統一走 config**
- 檔案：`feature_factory_batch_service.py`（compute_fn 選擇 L358-362、`_compute_single_ic_first`、`_resolve_concurrent_symbols`）；`momentum/factories.py`（`create_feature_factory_for_ic_batch`）。
- 改法：多 symbol 統一呼叫 `_compute_single`（傳 config_override 含 ic_first_pipeline）；移除 `_compute_single_ic_first` 分支與 `FFACT_MULTI_SYMBOL_IC_FIRST` 換函式語義；`_resolve_concurrent_symbols` 改「config 為 IC-First 時 force concurrent=1」（讀 config 非舊 env）；`create_feature_factory_for_ic_batch` 無 caller 則移除（先 grep）。
- **既有測試同步（adversarial 收斂，免假綠）**：`tests/feature_engineering/test_multi_symbol_ic_first.py` 多處用 `_compute_single_ic_first`/`create_feature_factory_for_ic_batch` → 須改寫為新路徑（config-driven）或刪除並補等價測試，**不得放寬/刪斷言交差**。
- 驗證：`pytest` 多 symbol 帶 `ic_first_pipeline=true` 走 `_layer6_5_pre_ic`（無 rank/zscore/gaussian）；concurrent==1；`grep _compute_single_ic_first` 無 caller；**§G G1 golden 全項通過**（改前==改後、單==多，容差分尺度）= 不過不 merge。
- 邊界：config 未開 IC-First→走 legacy 不受影響；ICEngine 注入若他處仍用則保留。
- 不可做：不得改變 IC-First 的 L6.5 數值語義（G1 守）。

## §V 驗證策略與邊界測試目錄
- 層級：單元（config/registry/工廠）、整合（batch 2-symbol mock）、Golden 對照（§G）、前端 unit（store/page）。可獨立 `pytest tests/...`，不需 run_api.py。
- 防假綠：diff 既有測試斷言，不得放寬/刪除換綠燈；新斷言對應新行為。
- 邊界目錄（本任務適用）：空 batch / 全失敗 wave / API 重啟 re-hydrate / 並發 JSONL 寫 / OOM 降載 concurrency→1 / 舊 browse _hash8 殘留 / float32 大尺度 reduction（§G 容差）。

## §R 回退
- 每 Phase 獨立 commit 可單獨 revert。Phase 3（C2）整包包 `FFACT_PARALLEL_BUDGET`（預設 off）→ 16GB 實測 OOM 一鍵關旗標回舊 `FFACT_BATCH_NESTED` 行為，不需 revert code。Phase 4（C3）若 §G G1 golden FAIL → 不 merge。

## §N N/A 登記
- §0.A 反幻覺/提示注入：N/A — 由 `AGENTS.md`/`.cursorrules` 執行端合約覆蓋，不在本 SPEC 重述。
- §1.1 C-OPT 硬約束表：N/A — §C 已重述不可違反原則；本任務無新增效能硬數值約束。
- **batch `get_status()` 重啟 404（adversarial 分歧，codex #8）：本期 scope 外**。[P2-3] 已讓 **per-symbol browse 重啟後可恢復**（解使用者原始痛點「跑完看不到結果」）；但 batch 編排 task_id 仍記憶體內，重啟後 `GET /batch/{id}` 仍 404。完整 rehydrate batch get_status 屬獨立 UX 改善，延後（理由：per-symbol 可瀏覽已解決核心需求，batch status 復原成本高且非阻塞）。
