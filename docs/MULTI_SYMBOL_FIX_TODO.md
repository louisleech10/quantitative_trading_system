# 多 Symbol 批次修復 — TODO（V13，2026-06-02 由 SPEC 生成）

> 狀態：DRAFT（待 TODO adversarial）　基於 SPEC：`docs/MULTI_SYMBOL_FIX_SPEC.md` + `MULTI_SYMBOL_FIX_MANIFEST.md`
> 每項完成回報：測試指令 + pass/fail + 摘要 + 是否動既有斷言。順序 Phase 1→2→3→4（Phase 4 需 §G golden 先凍結）。

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
- **解耦**：`grep -rE "from api\.services|import api\.services" api/services/feature_factory_batch_service.py`→0；batch service 經注入用 service，禁直接 import（Rule 4）。`grep "from api\." momentum/`→0。
- **Logging**：`from api.core.logging import get_logger`；熱迴圈不逐列 log。
- **Error 分類**：可重試(rate_limit/timeout) vs 不可重試(invalid_symbol/logic/format)。
- **不可違反**：不弱化 NaN·inf gate、不擅改輸出大小、多 symbol 不 OOM、跨 tier 可重複、**不寫入 `data_cache/`**（golden 走 `tests/fixtures/golden/`）。
- **防假綠**：不得放寬/刪除既有測試斷言換綠燈；新斷言對應新行為。

## §B 批次執行策略（依賴拓撲 → 最少批次；每批=一次派工 prompt）
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| 1 | [P1-1][P1-2][P1-3][P1-4] | 無 | 真無依賴；P1-2/P1-3 同 batch_service 序列改 | 中 |
| 2a | [P2-1][P2-2] | Batch 1 接回 | id 契約 + 注入 seam（P2-3/2-4 的前置） | 中 |
| 2b | [P2-3][P2-4][P2-5] | 2a | 皆用 P2-2 注入；P2-5 前端 | 中 |
| 3 | [P3-1][P3-2] | **Batch 1/2 完成（同改 batch_service/preprocessor，不可並行）** | C2 worker 預算 | 中 |
| 4 | [P4-1]→[P4-2] | Batch 3 | golden 先凍結再清理 | 大 |
- **硬序列（adversarial 收斂）**：每個 Batch 由**單一 agent 串行完成**，不得逐 Task 並行派工（同檔衝突）。同檔依賴邊：P1-2→P1-3（同 `_process_item_wave`）、P2-2→P2-3→P2-4（注入後才用）、Batch 3 須等 Batch 1/2 完成（同改 batch_service/preprocessor）。
- 批次間 Gate：每批跑該批 Test 全綠 + `./scripts/check_decoupling_phase4.sh`（Batch 2 後）才進下一批。
- 派工 prompt 範本：「讀 HANDOFF/CLAUDE/AGENTS + SPEC §相關 Task。實作 [P*-*]。守 §0。完成跑 <pytest 指令>，輸出 STATUS: DONE/BLOCKED。」

## Phase 1 — 低爭議群（無依賴）
### Task [P1-1] 輪詢統一
- SPEC ref：§P [P1-1]　目標：移除 batch 輪詢 600 次上限，對齊單 symbol。
- 輸入：`featureFactoryStore.ts:pollBatchStatus`(L617-639)　輸出：無上限輪詢（到 terminal 才停）。
- 實作要點：刪 `maxAttempts=600`；改 `while status not in (completed,failed,partial)`；網路 5xx→setError+退避，非逾時誤判。
- 修改檔案：`frontend/src/store/featureFactoryStore.ts` → `pollBatchStatus()`
- 不可做：不刪既有 error 處理。
- 邊界：5xx→surface；failed→停輪詢。
- 驗證：mock fetch >600 次 running 後 completed，斷言不誤報逾時且 `status=='completed'`；`npm run build` pass。

### Task [P1-2] current_symbol 時機
- SPEC ref：§P [P1-2]　目標：item submit 前設 current_symbol。
- 實作要點：在 `_process_item_wave` submit 迴圈(L365-375)內 future 提交前設 `task["current_symbol"]/current_timeframe` + `_notify_progress`；**移除/改 `_record_item_result`(L419) 的 `task["current_symbol"]=symbol`**（否則完成路徑覆寫 → UI 又顯示剛完成）。
- 修改檔案：`feature_factory_batch_service.py` → `_process_item_wave()` + `_record_item_result()`(L419)
- 不可做：不移除完成時 metrics 紀錄；完成路徑不覆寫進行中 current。
- 邊界：concurrent>1→current=最後 submit（單值保型別）；空 wave→不更新。
- 驗證：`pytest tests/api/` 2-symbol 序列，第 2 個 submit 後完成前 `get_status().current_symbol==第2個`；斷言 submit 時 `_notify_progress` 被呼叫。

### Task [P1-3] 子進程 log JSONL
- SPEC ref：§P [P1-3]　目標：子進程指標回收為 JSONL。
- 實作要點：每 symbol 完成寫一行 `{symbol,timeframe,pid,peak_rss_mb,duration_s,status}` 至 `{checkpoint_dir}/{task_id}/child_metrics.jsonl`；QueueListener 或 per-pid 檔避免交錯；列入 cleanup。
- 修改檔案：`feature_factory_batch_service.py` → `_process_item_wave`/`_compute_single*`
- 不可做：熱迴圈不逐列 log。
- 邊界：子進程 crash→status=failed 仍出一筆；並發寫每行可 json.loads。
- 驗證：`pytest` 2-item batch，讀該 jsonl 斷言每 symbol 一筆、欄位齊、status∈{ok,failed}、每行 json.loads 成功。

### Task [P1-4] registry 去重
- SPEC ref：§P [P1-4]　目標：(symbol,timeframe,config_hash) upsert。
- 實作要點：寫入前查同 key 既有條目→更新 feature_count/created_at/path，不 append。
- 修改檔案：`momentum/FeatureEngineering/feature_registry.py`（save/append 方法）
- 不可做：不刪不同 config_hash 歷史條目。
- 邊界：空 registry→新增；不同 config_hash→各留。
- 驗證：`pytest` 同 key register 兩次→`len==1` 最新值；不同 config_hash→`len==2`。

## Phase 2 — 注入 seam + C1 + 品質 loader（依賴 Phase 1）
### Task [P2-1] browse id = B
- SPEC ref：§P [P2-1]　目標：統一 `browse_{sym}_{tf}`（去 restore _hash8）。
- 實作要點：改 `_restore_persisted_tasks`(3718) 去掉 `_{hash8}`，與 `register_hdf5_for_browse`(601) 一致；舊 _hash8 task 映射/忽略。
- 修改檔案：`feature_factory_service.py` → `_restore_persisted_tasks()`、(對齊)`register_hdf5_for_browse()`
- 不可做：不引入 config_hash 進 id（已定 B）。
- 邊界：舊格式殘留不 crash；不同 tf 各 id。
- 驗證：`pytest` register 與 restore 對同 (sym,tf) 產生相同 id（== `browse_{sym}_{tf}`）；重建 service 後 `get` 拿得到；重生成覆蓋為最新。

### Task [P2-2] 注入 seam（Protocol + composition root）
- SPEC ref：§P [P2-2]　目標：batch service 經注入用 service，結構保證 Rule 4。
- 實作要點：`protocols.py` 定 `IBrowseRegistrar.register(symbol,timeframe,manifest_path)->str`、`IQualityComputer.compute(manifest_path)->dict`；`api/services/` 新 adapter 包 service 私有方法；`api/main.py` lifespan 注入 batch service；`get_feature_factory_batch_service()` 無注入→raise(fail-closed)。
- **browse adapter 走 manifest 非 h5py**（收斂）：先查 `register_hdf5_for_browse`(service.py:~596) 是否 h5py.File；batch 傳 manifest path → adapter register 須用 manifest/parquet loader 或新增 `register_manifest_for_browse`，**不得把 manifest 丟 h5py**。
- **既有 caller 同步**（收斂，免打爆啟動/CI）：`get_feature_factory_batch_service()`(L1007)、`api/main.py`(L53)、`tests/api/test_feature_factory_batch_*.py` 直接 construct 處→改注入；conftest fixture 提供 mock；禁裸 construct。
- 修改檔案：`momentum/core/protocols.py`、`api/services/feature_factory_*adapter.py`(新)、`api/main.py`、`feature_factory_batch_service.py`、`tests/api/conftest.py`
- 不可做：batch service 不 import 任何 `api.services.*`；不得把 manifest 丟 h5py。
- 邊界：注入缺失→raise；adapter 在 api 層 import service 合法。
- 驗證：`grep -rE "from api\.services|import api\.services|get_feature_factory_service" api/services/feature_factory_batch_service.py`→0；`./scripts/check_decoupling_phase4.sh` PASS；**`pytest tests/api/` 全綠(caller 同步後)**；注入 None→raise、mock→正常；browse adapter 用真實 parquet+manifest fixture 註冊成功。

### Task [P2-3] 後端 per-item browse 註冊
- SPEC ref：§P [P2-3]　目標：每 symbol 完成即經注入 registrar 註冊。
- 實作要點：`_record_item_result` 成功分支呼叫 `registrar.register(sym,tf,manifest_path)`；`browse_task_id` 寫 checkpoint `completed_items[]`；concurrent>1 同 wave 去重。
- **response schema（收斂，免破舊 caller）**：`get_status()` **保留 `results: Record<str,str>` 不動形狀**，**新增 `browse_task_ids: Record<str,str>`**；同步 `api/models/feature_factory_models.py` + 前端 TS types。
- 修改檔案：`feature_factory_batch_service.py` → `_record_item_result()`、`get_status()`；`api/models/feature_factory_models.py`
- 不可做：不依賴前端事後註冊；不改 `results` 形狀。
- 邊界：失敗 symbol 不註冊；同 wave 不重複註冊。
- 驗證：`pytest` 2-symbol batch（mock 回 fixture manifest），斷言 registrar 呼叫數==成功數、checkpoint browse_task_id 非空、`get_status().browse_task_ids[sym]` 非空且 `results` 形狀不變；清 `self._tasks` 後 `_restore_persisted_tasks` 仍可 browse。

### Task [P2-4] 品質 loader（parquet/manifest）
- SPEC ref：§P [P2-4]　目標：`_compute_symbol_quality` 改讀 parquet/manifest。
- 實作要點：經注入 `IQualityComputer`（adapter 包 `_build_data_quality_cgsa` L2045/`_fast_quality_alerts` L2930）；回傳欄位與前端契約不變。
- 修改檔案：`feature_factory_batch_service.py` → `_compute_symbol_quality()`
- 不可做：不用 h5py 開 parquet/manifest；不重寫平行品質邏輯。
- 邊界：失敗 symbol 不當 pass；空目錄→None 不 crash。
- 驗證：`pytest` fixture 目錄回 grade∈{pass,watch,reject}、feature_count 與 manifest 一致；**G2 golden**：與單 symbol `_build_data_quality_cgsa` 對同目錄 nan_ratio_mean/constant_count/grade 一致（abs<=1e-9）。

### Task [P2-5] 前端讀後端 browse id
- SPEC ref：§P [P2-5]　目標：優先讀後端 browse_task_id。
- 實作要點：`handleSelectBatchSymbol` 先用 `batchTask.results[sym].browse_task_id`，缺才 fallback register；更新 TS response type。
- 修改檔案：`frontend/src/app/feature-factory/page.tsx` → `handleSelectBatchSymbol()`、`lib/types.ts`
- 不可做：不移除 fallback 路徑。
- 邊界：舊 batchTask 無新欄位→fallback。
- 驗證：store/page unit test——有 browse_task_id 不 call register（斷言未呼叫 register endpoint）；缺則 fallback；`npm run build` pass。

## Phase 3 — C2 worker 預算（**與 Phase 1/2 同改檔，序列接回不並行**；包 `FFACT_PARALLEL_BUDGET` 預設 off）
### Task [P3-1] get_slowpath_n_jobs 並行感知
- SPEC ref：§P [P3-1]　目標：簽名加 concurrent_symbols。
- 實作要點：`def get_slowpath_n_jobs(tier_gb, concurrent_symbols: int = 1)`；`return max(1, tier_cap // concurrent_symbols)`，先受 `get_slowpath_parallel_enabled()`(<12GB→1)、Windows→1。
- 修改檔案：`momentum/core/config.py` → `get_slowpath_n_jobs()`
- 不可做：不移除 <12GB gate。
- 邊界：concurrent=0→當 1；非整數→既有 fallback。
- 驗證：`pytest` `(16,1)==4`、`(16,2)==2`、`(32,4)==2`、`(8,1)==1`、下限>=1；無參數呼叫端不變。

### Task [P3-2] concurrency env + peak RSS 守門
- SPEC ref：§P [P3-2]　目標：子進程拿 concurrency divisor + RSS gate。
- 實作要點：父進程 submit 前設 `FFACT_BATCH_SYMBOL_CONCURRENCY`；`_resolve_slowpath_n_jobs` 讀並傳入；`FFACT_BATCH_NESTED` 改運維強制安全模式；整體受 `FFACT_PARALLEL_BUDGET`(off==現狀 1)；封頂 `OMP_NUM_THREADS`/`POLARS_MAX_THREADS`；記 per-child+父總 RSS，超 `tier_gb*0.6` 軟上限→降載 concurrency→1。truth-table 見 SPEC §P Phase 3。
- 修改檔案：`feature_factory_batch_service.py` `_process_item_wave`、`feature_preprocessor.py` `_resolve_slowpath_n_jobs`(L2859)
- 不可做：不移除 RAM gate/memory_sanity/IC-First force 1。
- 邊界：RAM gate→拒新任務；memory_sanity_failed→降 concurrent。
- 驗證：`pytest` concurrency=1@16GB→4、=2→2、8GB→1；`FFACT_BATCH_NESTED=1`→1；flag off→全程 1；peak RSS 測試：16GB concurrency=2 總 RSS<=tier*0.6 否則降載。

## Phase 4 — C3 IC-First 清理（依賴 §G golden 先凍結）
### Task [P4-1] 凍結 G1 golden
- SPEC ref：§G + §P [P4-1]　目標：可重現 baseline。
- **前置（收斂，免自我參照）**：先取真實可審計 config——從 0530/0601 run artifact 或 registry config_hash 還原 `config.json`；**取不到→STATUS: BLOCKED 要使用者提供,不准自造 freeze**。
- 實作要點：新增 `scripts/golden_multi_symbol_c3.py`（freeze/compare）；config `tests/fixtures/golden/multi_symbol_c3/config.json`；freeze 產 baseline.parquet（名稱 sha256+數量+schema+每 feature mean/std/nan_ratio+**全量 chunk hash**+NaN mask hash）+ env_snapshot.json（FFACT_* + compute_fn + config_hash）；float64 canonicalize、index 排序固定；+三 symbol(ETH/BTC/DOGE)名稱集+schema smoke。
- 修改檔案：`scripts/golden_multi_symbol_c3.py`(新)、`tests/fixtures/golden/multi_symbol_c3/`(新)
- 不可做：不寫 `data_cache/`；不在 [P4-2] 後才建。
- 邊界：baseline 缺→compare raise；env 不符→警告。
- 驗證：freeze 產出檔（`ls` 確認）；compare 對未改 code→PASS；人工注入 1e-3 漂移→FAIL 並列該 feature。

### Task [P4-2] 移除重複 IC-First 機制
- SPEC ref：§P [P4-2]　目標：multi 統一走 `_compute_single` + config。
- 實作要點：移除 compute_fn 分支(L358-362)與 `_compute_single_ic_first`；`_resolve_concurrent_symbols` 改「config IC-First 時 force concurrent=1」(讀 config)；`create_feature_factory_for_ic_batch` 無 caller 則移除(先 grep)。
- **測試同步（收斂，免假綠）**：`tests/feature_engineering/test_multi_symbol_ic_first.py` 用到 `_compute_single_ic_first`/`create_feature_factory_for_ic_batch` → 改寫為 config-driven 新路徑或刪除+補等價測試,不放寬斷言。
- 修改檔案：`feature_factory_batch_service.py`、`momentum/factories.py`、`tests/feature_engineering/test_multi_symbol_ic_first.py`
- 不可做：不改 IC-First L6.5 數值語義（G1 守）；不放寬/刪既有斷言交差。
- 邊界：config 未開 IC-First→legacy 不受影響；ICEngine 他處仍用則保留。
- 驗證：`pytest` multi 帶 `ic_first_pipeline=true` 走 `_layer6_5_pre_ic`；concurrent==1；`grep _compute_single_ic_first` 無 caller；**§G G1 golden 全項通過（改前==改後、單==多）= 不過不 merge**。
