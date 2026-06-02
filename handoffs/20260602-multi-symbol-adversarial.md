# Multi-Symbol SPEC/TODO 雙家族 Adversarial 結論（2026-06-02）

## SPEC — Codex (GPT-5.5)
## Verdict：需修補後派工

## Findings

1. [BLOCKING] High — P4 golden 任務是空殼  
證據：SPEC §G 說「TODO 寫死路徑+生成命令」(SPEC L22)，但 TODO T4.0 寫「config JSON（路徑/hash 填此）；資料快照來源；baseline 存放目錄；comparison script 路徑」(TODO L47-L48)。  
會失敗：執行端沒有可執行 baseline 來源、config hash、生成/比對命令。  
修法：補 exact config file/hash、資料快照來源、生成命令、比對命令、baseline 檔名/schema。

2. [BLOCKING] High — P4 baseline scope 觸碰 `data_cache/`，和執行合約衝突  
證據：SPEC §G baseline 存 `data_cache/golden/multi_symbol_c3/` (SPEC L22)；AGENTS 紅線禁止刪除/修改 `data_cache/`。Manifest scope 也沒有列 data_cache 寫入。  
會失敗：headless 執行端應 BLOCKED，不能自行寫 baseline。  
修法：使用者明確核准此 data_cache 寫入並列入 scope，或改到非 data_cache 的可審查 golden 位置。

3. [MAJOR] High — §A 把 C3 前提說得過強  
證據：SPEC §A：「IC-First 由 config...路由，單/多共用」(SPEC L12)；實際 batch 仍由 `FFACT_MULTI_SYMBOL_IC_FIRST` 選 `_compute_single_ic_first` (batch L357-L362)，該函式用 `create_feature_factory_for_ic_batch` (batch L787-L800)。  
會失敗：作者可能低估 P4 風險，把「FeatureFactory 內部 config 共用」誤當「batch/single entrypoint 已共用」。  
修法：§A 改成「config 路由已驗證；batch 仍有 multi-only wrapper/flag，P4 清理須 golden gate」。

4. [MAJOR] Medium — §A 的「已向使用者確認」不全在指定事實來源中可驗  
證據：診斷只記「0530 單、0601 多都選 IC-First」(診斷 L130-L136)；SPEC §A 又列「browse id=B latest-overwrite」「未來 concurrent>1」(SPEC L14)。  
會失敗：review/派工只按三文件驗證時，會把文件外決策當事實。  
修法：補決策來源連結或 handoff/adversarial artifact 引用；否則標為 user-confirmed external assumption。

5. [MAJOR] High — [P2-2] seam 不能保證守 Rule 4  
證據：SPEC 只驗 `grep "from api.services.feature_factory_service" ...batch_service.py` (SPEC L69)，但同段要求經注入複用 `feature_factory_service._build_data_quality_cgsa` 私有方法 (SPEC L82)。  
會失敗：可用 `from api.services import feature_factory_service`、新 adapter service import、或 runtime singleton 依賴繞過 grep；Rule 4 只被字串檢查，不被架構保證。  
修法：明定 composition root 在 `api/main.py` 注入 adapter；batch service 不 import 任何 `api.services.*`；新增寬 grep：`rg "api\\.services|feature_factory_service|get_feature_factory_service"` 針對 batch 與新增檔。

6. [MAJOR] High — §G 容差/hash 不足以完全擋 C3 局部數值漂移  
證據：§G 只列 mean/std/nan_ratio +「抽樣 value hash（固定種子 row）」+ NaN mask hash，容差 `abs<=1e-8 或 rel<=1e-6` (SPEC L23-L24)。  
會失敗：未抽樣 row 的局部漂移可通過；hash canonicalization、sample size、dtype 處理未定；mean/std 會被重排或抵銷漂移繞過。  
修法：加每 feature 全量 deterministic chunk hash 或全量 tolerant compare；固定 row set 數量、排序、float canonicalization；失敗報 feature/row diff。

7. [MAJOR] High — Phase 3 flag/rollback 自洽性不足  
證據：P3 說整包 `FFACT_PARALLEL_BUDGET` 預設 off (SPEC L94)，P3-2 又驗「flag off→全程 1」(SPEC L105)，但 P3-1 驗 `get_slowpath_n_jobs(16,1)==4` (SPEC L98)。Rollback 說關旗標回舊 `FFACT_BATCH_NESTED` 行為 (SPEC L129)，但 P3-2 又改其語義。  
會失敗：執行端不知道 flag off 時 `get_slowpath_n_jobs`、batch env、single-symbol 行為誰優先。  
修法：補 truth table：single vs batch、flag on/off、nested on/off、tier、expected n_jobs；定義具體 RSS 上限數值與 mock 測試。

8. [MAJOR] Medium — C1 沒明確修掉「batch id refresh 後失效」  
證據：診斷指出 API 重啟 `GET /batch/{id}` 404 (診斷 L51-L52)；SPEC P2-3 只保證 browse 可恢復：「清 self._tasks 後 `_restore_persisted_tasks` 仍可 browse」(SPEC L76)。  
會失敗：使用者刷新 batch status 仍可能看到「已失效」，只是 per-symbol browse 能恢復。  
修法：明確標 N/A 並改 UX，或納入 checkpoint rehydrate batch `get_status()` 的驗收。

9. [MINOR] High — [P1-3] JSONL 缺輸出位置  
證據：SPEC P1-3 只說「每 symbol 完成輸出一行 JSONL」(SPEC L46)，驗證「解析 JSONL」(SPEC L47)，未指定 path/命名/清理。  
會失敗：測試和實作可各選不同位置。  
修法：指定 `checkpoint_dir/{task_id}/child_metrics.jsonl` 或等價固定路徑，並列入 checkpoint/cleanup 規則。

## 無問題類別

- 過度工程：無明顯新增 queue/distributed framework。
- Cache key 決策：browse id latest-overwrite 已明確，但來源需補。
- 前端相容：P2-5 有 fallback，不是 blocking。
- 測試防假綠：§V 有明確禁止放寬既有斷言。

## 被當成事實的未驗證假設（§0）

- 「單/多共用 IC-First 路由」：部分 fact，過度外推；batch entrypoint 仍未共用。
- 「browse id=B latest-overwrite 已確認」：文件內缺可驗來源。
- 「future concurrent>1 已確認」：文件內缺可驗來源。
- 「§G 抽樣 value hash 足以擋 C3 漂移」：assumption，需補全量/分塊比對。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF/CLAUDE/template/SPEC/manifest/diagnosis/TODO，並抽查相關程式片段。  
TESTS_RUN: read-only `nl`/`rg`/`wc` 檢查；未跑 pytest。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: review only，未改檔。  
HANDOFF_NOT_UPDATED: read-only sandbox 且本次為審查輸出，不寫交接檔。  
STATUS: DONE
## SPEC — Cursor (Composer 2.5)
## Verdict：需修補後派工

SPEC 主幹清楚、Manifest 覆蓋完整，但 §A 有未驗證等價前提、§G/P4-1 缺可重現錨點、[P2-2] 注入契約不足以保 Rule 4、C1 未解 batch task 重啟 404。修補後可派工。

---

## Findings

### §0 挑戰前提（優先）

**[MAJOR] High** — §A 把「单/多 共用 config IC-First 路由」當已驗證事實，忽略 env 分叉  
**證據**：§A「IC-First 由 config … 单/多共用」；程式 `feature_factory_batch_service.py:358-362` 仍用 `get_multi_symbol_ic_first_enabled()` 在 `_compute_single_ic_first` vs `_compute_single` 間切換；`_compute_single_ic_first` 另設 `FFACT_IC_FIRST_PIPELINE=1` 且用 `create_feature_factory_for_ic_batch`（L770-805）。  
**失敗**：§A 宣稱等價 → P4-2 以為低風險清理；若 prod `FFACT_MULTI_SYMBOL_IC_FIRST=1`，golden「改前」基線與實際路徑不一致，合併後靜默改 ML 語義。  
**修法**：§A 改為「config 路由已驗（feature_factory.py:1700）；multi 在 flag=1 時仍走平行入口（assumption，待 grep/env 快照）」；§G 凍結 baseline 須記錄 `FFACT_MULTI_SYMBOL_IC_FIRST` 等 env + 實際 `compute_fn`。

**[MAJOR] Medium** — §A「0530 单 / 0601 多 都选 IC-First」僅 user 口述，無 log/config_hash 交叉驗證  
**證據**：§A「已確認结果：① …（使用者 2026-06-02）」；診斷 §C3 更正亦無 0601 request body 的 `ic_first_pipeline` dump。  
**失敗**：若 0601 實際 legacy，P4-2 驗收與 golden 對錯 pipeline。  
**修法**：§A 標 `user-confirmed, log-unverified`；P4-1 凍結時附兩次 run 的 config JSON / config_hash（診斷已有 batch `8440d93` vs 12h `b86fa71` 線索）。

**[MINOR] High** — §A「待確認：无」過度樂觀  
**證據**：§A L13「待确认：无」；委員會仍留 browse 覆蓋風險（診斷 L115）、0601 是否 flag=1 未釘死。  
**修法**：改「待確認：无（使用者 2026-06-02 三項）」並列仍待 code/env 驗證項。

---

### §G golden 容差 vs C3 漂移

**[MAJOR] High** — 容差設計合理但 **抽樣未定義**，局部漂移可過 gate  
**證據**：§G「抽樣 value hash（固定種子 row）」無 row index / 欄位 / 種子算法；審查模板 §2 已警告 aggregate-only 可繞過。  
**失敗**：C3 若只改部分 bar/欄位，mean/std + 稀疏抽樣仍 PASS。  
**修法**：P4-1 寫死：種子、抽樣列數、bar index 集合（如 0/ mid/ -1）、每 feature 全量 NaN-mask hash；超出抽樣列仍 FAIL。

**[MAJOR] Medium** — golden 僅 `BTCUSDT 1h`，未覆蓋事故三元組  
**證據**：§G reference 僅 BTCUSDT 1h；診斷 task 為 ETH/BTC/DOGE。  
**失敗**：symbol 特異 cache/路徑 bug 過 gate。  
**修法**：§G 增「smoke 三 symbol 名稱集 + schema 一致」或 manifest 抽樣至少 1 個非 BTC。

**[MAJOR] High** — P4-1 **空殼**：§G 要求「TODO 写死路径+生成命令」，SPEC/TODO 均未寫  
**證據**：[P4-1] 僅「新增 scripts/golden…」「baseline 存 data_cache/…」；TODO T4.0「路径/hash 填此」仍 placeholder。  
**失敗**：Agent 各寫各的 baseline，CI 不可重現，§G 形同口號。  
**修法**：P4-1 補全：config JSON 路徑、env 快照、`python scripts/golden_multi_symbol_c3.py freeze|compare`、抽樣 spec、baseline 檔名 schema（可 commit 的 `tests/fixtures/golden/` 或 documented 生成步驟）。

**[MINOR] Medium** — float32 `atol=1e-5` 對大尺度特徵可能偏鬆  
**證據**：§G「float32 放寬 atol=1e-5」。  
**修法**：大尺度欄位用 rel-only 或分 quantile 比對；文檔化例外。

---

### [P2-2] 注入 seam vs Rule 4

**[BLOCKING] High** — Protocol 無方法簽名、無 wiring 檔、易假合規  
**證據**：[P2-2] 僅「IBrowseRegistrar/IQualityComputer」「API 啟動時注入」；無 `protocols.py` 方法列表、無 `main.py`/`set_feature_factory_batch_service` 注入範例；P2-4 仍指 private `_build_data_quality_cgsa`。  
**失敗**：Agent 在 batch 內 `from api.services.feature_factory_service import …` 或 lazy import 仍 grep=0 於 batch 檔但 Rule 4 名存實亡。  
**修法**：§P [P2-2] 增：`IBrowseRegistrar.register(sym,tf,output_path)->str`；`IQualityComputer.compute(manifest_path)->dict`；實作類 `FeatureFactoryBrowseAdapter` 放 `api/services/`（可 import service）；`main.py` lifespan 明確 `FeatureFactoryBatchService(browse_reg=..., quality=...)`。

**[MAJOR] High** — 驗收 grep 只查 batch 單檔，不查全 api/services 互 import  
**證據**：[P2-2] 驗證「grep … feature_factory_batch_service.py → 0」。  
**修法**：加 `./scripts/check_decoupling_phase4.sh` 或「batch 不得 import 任何 `api.services.*`（settings 除外）」。

**[MINOR] Medium** — `get_feature_factory_batch_service()` lazy 預設 `FeatureFactoryBatchService()` 無注入（L1007-1008）  
**證據**：batch_service.py singleton fallback。  
**修法**：無注入則 `raise`（fail-closed），測試強制 inject mock。

---

### Phase 依賴 / 回退

**[MAJOR] Medium** — Phase 3 標「依赖：无」與 Phase 2 同改 `batch_service`/`preprocessor`，並行派工易衝突  
**證據**：§P Phase 3「依赖：无」；[P3-2] 與 [P1-2]/[P2-3] 同檔。  
**失敗**：兩 agent 同改 `_process_item_wave`，回退粒度混亂。  
**修法**：Phase 3 改「依赖：Phase 1 接回；與 Phase 2 串行或同 agent」。

**[MAJOR] High** — §R C1 未覆蓋 batch `GET /batch/{id}` 重啟 404  
**證據**：診斷 L51-52「checkpoint 有落地，get_status 只讀記憶體」；[P2-3] 驗證僅「_restore_persisted_tasks 仍可 browse」，非 batch status。  
**失敗**：Refresh 仍「已失效」；browse 單獨修好但 batch UX 半套。  
**修法**：要麼增 Task「batch checkpoint re-hydrate get_status」要麼 §R/§N 明確 **out of scope** 與 UX 預期。

**[MINOR] High** — §R Phase 3「flag off = 現狀」但 [P3-2] 仍改 `FFACT_BATCH_NESTED` 語義  
**證據**：§R vs [P3-2]「FFACT_BATCH_NESTED 改運維強制安全模式」。  
**修法**：§R 列 flag off 時 `batch_nested_environment` 行為 diff 表（concurrent / n_jobs）。

---

### 獵空殼（逐 Task）

| Task | 判定 |
|------|------|
| [P1-1]~[P1-4] | 無空殼（檔案/行號/斷言具體） |
| [P2-1] | 無 |
| **[P2-2]** | **BLOCKING 空殼**（見上：無 Protocol API、無 wiring） |
| [P2-3] | 依賴 P2-2；registrar 簽名有，可派工 |
| [P2-4] | MAJOR：依賴 private 方法，缺 Protocol 契約 |
| [P2-5] | 無 |
| [P3-1] | 無（數值用例對 `_SLOWPATH_NJOBS_BY_TIER_GB`） |
| **[P3-2]** | **MAJOR 半空殼**：「peak RSS <= tier 上限」無 GB 數字/公式 |
| **[P4-1]** | **BLOCKING 空殼**（無生成命令、config、抽樣 spec） |
| [P4-2] | 無 |

**[MAJOR] Medium** — [P3-2] peak RSS 門檻未定義  
**證據**：[P3-2]「斷言 <= tier 上限，超則降載」無 tier→GB 表。  
**修法**：引用 `FFACT_RAM_GATE_MIN_GB` / tier 表或寫死 16GB→例如 14GB cap。

---

### §1 十類快查

1. **矛盾/互斥**：[MAJOR] Phase 3「无依赖」vs 同檔改動（見上）。browse `manifest_path` vs `register_hdf5_for_browse(hdf5_path)` 命名混用（P2-3 vs service:590）→ MINOR，行為若一致可接受。  
2. **漏項/end-to-end**：[MAJOR] batch re-hydrate（見上）；[MINOR] WebSocket batch 通知是否帶 `browse_task_id` 未寫。  
3. **不可測驗收**：P4-1 BLOCKING；P3-2 RSS 缺數值。其餘無。  
4. **可疑 quant**：[MAJOR] §A IC-First 等價（§0）；[MINOR] B latest-overwrite 無 config_hash 已 user 拍板，需在 §R 寫清覆蓋風險。  
5. **過度工程**：無。  
6. **OOM/並行**：[MINOR] P3-2 提 BLAS/Polars 封頂但未列具體 env 值與驗證命令。  
7. **Cache 正確性**：[MINOR] [P2-1] 去 _hash8 後舊 task 僅「映射或忽略」，未指定 migrate 策略。  
8. **API/型別**：[MINOR] [P2-5] 要求更新 TS type 但未列 `types.ts` 路徑。  
9. **測試品質**：[MAJOR] §G 未要求 golden 進 CI（data_cache gitignore）；[MINOR] P1-2「擴充 tests/api/」未指檔名。  
10. **Agent 可執行性**：P2-2、P4-1 BLOCKING；其餘可執行。

### §2 範本錨點
§RISK/§A/§C/§G/§P/§V/§R/§N 齊；§G 有 value/NaN hash 但 P4-1 未落地 → 半落實。

---

## 被當成事實的未驗證假設（§0）

1. **单/多 IC-First 計算完全一致** — 僅在 `FFACT_MULTI_SYMBOL_IC_FIRST=0` 且 config 同時成立；flag=1 時 **assumption false**（不同 compute_fn + factory + env）。  
2. **0530/0601 皆选 IC-First** — user-confirmed，**log-unverified**。  
3. **browse B 语义无副作用** — user-confirmed；不同 config 覆蓋 **accepted risk**，非「无问题」。  
4. **C3 降级低風險** — 依賴 (1)；P4-2 前必須 golden 在**当前** prod 路径上 freeze。  
5. **输出 parquet+manifest 无 .h5** — 診斷+ls **fact-verified** ✓  
6. **tier=8GB** — 診斷 **fact-verified** ✓  
7. **config 路由 feature_factory.py:1700** — code **fact-verified** ✓  

---

STATUS: DONE

## TODO — Codex
## Verdict：需修補後派工

## Findings

[BLOCKING] High  
證據：P2-3「`get_status()` 增列 browse_task_id」；P2-5「`batchTask.results[sym].browse_task_id`」；現有程式是 `results: Record<string,string>`，前端讀 `const hdf5Path = batchResults[sym]`。  
會怎麼失敗：後端可能只加 top-level 或 checkpoint 欄位，前端卻讀 nested object；或改 `results` 形狀後破壞舊 caller。這是未明定的 API/TS schema 變更。  
修法：明定 exact response schema。建議保留 `results: Record<string,string>`，新增 `browse_task_ids: Record<string,string>`；同步 `api/models`、TS types、store/page、舊 batch fallback 測試。

[BLOCKING] High  
證據：P2-2「建構子收注入」「`get_feature_factory_batch_service()` 無注入→raise」；實際 caller 有 `api/main.py: FeatureFactoryBatchService()`、`tests/api/*: FeatureFactoryBatchService(...)`、`tests/performance/...`。  
會怎麼失敗：一改 fail-closed 或 constructor 參數，API 啟動/既有測試/benchmark 直接壞；TODO 沒有 caller 同步 Task。  
修法：P2-2 增列所有 direct constructor/getter caller 的同步改動與測試策略；提供 test adapter/mock fixture，並明確哪些路徑允許測試注入。

[BLOCKING] High  
證據：P4-1「config `tests/fixtures/golden/.../config.json`」「L2-6.5 同 0530」；SPEC §A 又說「log-unverified」「待 P4-1 凍結時附兩次 run 的 config JSON/hash」。  
會怎麼失敗：冷啟動 agent 沒有 0530 config 來源，會自造 baseline；golden 變成不可證偽的自我參照。  
修法：P4-1 前新增 Task：從真實 run artifact/config_hash 取得並提交 config JSON；若取不到，先 BLOCKED 要使用者提供，不准 freeze。

[MAJOR] High  
證據：Manifest P4-1「抽樣 value/NaN-mask hash」 vs SPEC/TODO「全量 deterministic chunk hash」「無抽樣盲區」。  
會怎麼失敗：驗收者按 manifest 接受抽樣 hash，漏掉局部漂移；或執行端按不同文件實作。  
修法：Manifest 改成全量 value chunk hash + NaN mask hash，與 SPEC/TODO 一致。

[MAJOR] High  
證據：P3-2 修改檔案寫「`feature_preprocessor.py` `_resolve_slowpath_n_jobs`」，實際路徑是 `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py`。  
會怎麼失敗：TODO 宣稱「執行端讀完即可遵守，不必回讀 SPEC」，但冷啟動 agent 檔案定位不完整。  
修法：TODO 每個 Task 都寫完整 repo path；P3-2 補全路徑。

[MAJOR] Medium  
證據：§B「每批=一次派工 prompt」但同時是「逐 Task 清單」；Batch 1 內 P1-2/P1-3 都改 `_process_item_wave`，Batch 2b P2-3/P2-4 都改 `feature_factory_batch_service.py`。  
會怎麼失敗：若 Claude 逐 Task 平行派工，同檔/同函式衝突；「序列改」只寫在合併理由，不是硬依賴。  
修法：§B 明定每個 Batch 必須單一 agent 串行完成；若拆 Task 派工，加入同檔依賴邊，例如 P1-2→P1-3、P2-3→P2-4。

[MAJOR] Medium  
證據：P3-2「peak RSS…超則降載 concurrency→1」；現有 `_process_item_wave` 是先 submit 整個 wave，再逐 future 收結果。  
會怎麼失敗：同一 wave 已提交後無法真正降載，只能影響下一 wave；TODO 未定義時點，agent 可能做不可控 cancel/kill。  
修法：明定 RSS 超限只影響後續 wave，寫 checkpoint `concurrent_symbols=1`；若要中止當前 wave，需另定 cancel policy。

[MINOR] Medium  
證據：P1-3「子進程 crash→status=failed 仍出一筆」且「QueueListener 或 per-pid 檔」。  
會怎麼失敗：若 hard crash 發生在 child 寫檔前，child-side JSONL 無法保證一筆 failed。  
修法：指定 parent 在 `_wait_one` exception path 寫 failed metrics；child 只回傳 pid/rss/duration。

## 被當成事實的未驗證假設

- P4-1 的「L2-6.5 同 0530」目前是未提供 artifact 的假設，不是可執行事實。
- P3-2 的「超 RSS 可降載當前 concurrency」在現有 submit-all wave 結構下未驗證，最多是下一 wave 行為。

其他必查類別：無新增問題。

ASSUMPTIONS_VERIFIED: 已用 `sed/rg` 讀 HANDOFF、CLAUDE、review prompt、TODO、SPEC、Manifest，並抽查相關實際 caller/schema/function path。  
TESTS_RUN: 未跑測試；本任務為 read-only adversarial review。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: 發現 P2-3/P2-5 隱含 schema impact 未明定。  
HANDOFF_NOT_UPDATED: read-only sandbox，依 AGENTS 規則不寫交接檔。  
STATUS: DONE
## TODO — Cursor
## Verdict：需修補後派工

整體 Task 有檔名/函式/行號，比常見空殼好；但仍有數條會讓冷啟動 agent 做錯路徑、假綠、或 P4-2 無法安全 merge。

---

## 被當成事實的未驗證假設

| 假設 | 性質 | 證據 |
|------|------|------|
| IC-First 在 0530 單次與 0601 多 symbol「都選」 | user-confirmed，**log-unverified** | SPEC §A：「待 P4-1 凍結時附 config JSON/hash」 |
| `register_hdf5_for_browse` 與 batch 輸出路徑語義一致 | 部分為 assumption | 實測 `generate_features` 常把 `manifest_path` 填進 `hdf5_path`；`register_hdf5_for_browse` 仍 `h5py.File`（`feature_factory_service.py:596-598`） |
| §G「三 symbol smoke」會被做 | SPEC 有、TODO 無 | SPEC §G「ETH/BTC/DOGE…」；P4-1 僅 `freeze --symbol BTCUSDT` |

---

## Findings

### §0 挑戰前提

**[BLOCKING] High** — **P2-3 註冊路徑與現有 browse API 契約衝突**  
- 證據：TODO [P2-3]「`registrar.register(sym,tf,manifest_path)`」；Protocol [P2-2] 第三參數 `manifest_path`；現況 `register_hdf5_for_browse(..., hdf5_path)` + `h5py.File`（`feature_factory_service.py:590-598`）；batch 仍回傳 `result.hdf5_path`（`feature_factory_batch_service.py:763,806`）。  
- 失敗：agent 把 manifest 目錄傳入仍走 h5py → `FileNotFoundError` / 假註冊。  
- 修法：在 [P2-2] 明寫 adapter 契約（manifest 目錄 vs parquet vs 相容 h5）；[P2-3] 寫死傳入欄位來源；必要時擴充 browse 註冊或新增 `register_manifest_for_browse`；驗證用真實 parquet+manifest fixture。

**[MAJOR] High** — **IC-First 對齊仍缺可審計 config 證據**  
- 證據：SPEC §A「log-unverified…待 P4-1 凍結時附兩次 run 的 config JSON/hash」。  
- 失敗：P4-1 baseline 可能凍在錯 config，G1 通過但與使用者場景不一致。  
- 修法：[P4-1] 前置子步驟：提交 `config.json` + `config_hash` + 兩次 run 指紋；compare 寫入 `env_snapshot.json` 並 hard-fail 不符。

**[MAJOR] Medium** — **Manifest 與 SPEC/TODO 對 §G 抽樣描述不一致**  
- 證據：Manifest `[P4-1]`「抽樣 value/NaN-mask hash」；SPEC/TODO「全量 chunk hash（無抽樣盲區）」。  
- 失敗：coverage_check 過、實作按 manifest 做抽樣 → 局部漂移漏檢。  
- 修法：Manifest 與 SPEC 對齊為全量 chunk hash。

---

### §1 必查（10 類）

**1. 矛盾/互斥** — 有  
**[MAJOR] High** — [P1-2] 未處理 `_record_item_result` 事後覆寫 `current_symbol`  
- 證據：診斷根因在「完成後才賦值」；`_record_item_result` L419 仍 `task["current_symbol"] = symbol`；[P1-2] 只改 `_process_item_wave` submit 前。  
- 失敗：跑中 UI 仍可能顯示「剛完成」而非「正在跑」。  
- 修法：[P1-2] 增：完成路徑只更新 metrics、不覆寫進行中 current；或抽 helper 統一語義；驗證保留「第 2 個 submit 後、完成前」斷言。

**[MINOR] Medium** — [P2-3] vs SPEC 成功條件用詞  
- 證據：SPEC「`error is None and hdf5_path`」；欄位語義已是 manifest。  
- 修法：統一為 `output_path` / `manifest_path` 非空。

**2. 漏項/端到端** — 有  
**[BLOCKING] High** — **P4-2 未列既有測試與 caller 同步 Task**  
- 證據：`tests/feature_engineering/test_multi_symbol_ic_first.py` 多處 `_compute_single_ic_first` / `create_feature_factory_for_ic_batch`；[P4-2] 僅「grep 無 caller」+ pytest 敘述。  
- 失敗：刪函式後 CI 紅；agent 為假綠改/刪斷言。  
- 修法：新增子項或併入 [P4-2]：改寫/刪除該檔、更新 mock 路徑；驗證 `pytest tests/feature_engineering/test_multi_symbol_ic_first.py` 明確命令。

**[BLOCKING] High** — **[P2-2] 建構子注入 vs 測試/lifespan 現況未覆蓋**  
- 證據：[P2-2]「注入 None→raise」；`get_feature_factory_batch_service()` L1007-1008 無注入仍 `FeatureFactoryBatchService()`；`api/main.py` L53-54 同；`tests/api/test_feature_factory_batch_*.py` 多處直接 construct。  
- 失敗：實作 fail-closed 後大批測試/啟動 BLOCKED。  
- 修法：[P2-2] 列清單：`main.py` lifespan 建 adapter、`conftest`/`pytest` fixture 注入 mock、禁止裸 `FeatureFactoryBatchService()`；逐檔驗證命令。

**[MAJOR] High** — **§G 三 symbol smoke 無對應 Task**  
- 證據：SPEC §G「+ 三 symbol smoke」；[P4-1] 僅 BTCUSDT freeze。  
- 修法：[P4-1] 增 `compare --smoke-symbols` 或獨立 pytest；寫死 ETH/BTC/DOGE 名稱集 sha256。

**3. 不可測驗收** — 有  
**[MAJOR] Medium** — **[P2-4]「G2 golden」無產出 Task、無 fixture 路徑**  
- 證據：[P2-4] 驗證「**G2 golden**：… abs<=1e-9」；僅 [P4-1] 建 `tests/fixtures/golden/multi_symbol_c3/`。  
- 失敗：品質回歸無可 commit 基線，執行端自訂門檻。  
- 修法：增 `tests/fixtures/golden/multi_symbol_quality/` + 建立 Task（可併 P2-4）；或明訂 inline pytest 用何 manifest fixture 路徑。

**[MAJOR] Medium** — **[P4-1] `config.json` 無建立 Task**  
- 證據：「config 來源：`tests/fixtures/.../config.json`」；修改檔案未含「撰寫 config」。  
- 修法：[P4-1] 第一步：新增 config（含 config_hash、L1/L2-6.5、ic_first_pipeline）；驗證 `sha256(config.json)` 記錄在 env_snapshot。

**[MAJOR] Low** — **[P1-1]/[P2-5] 前端驗證無測試檔路徑**  
- 證據：[P1-1]「mock fetch >600」；[P2-5]「store/page unit test」— 無 `__tests__` 路徑。  
- 修法：指定如 `featureFactoryStore.test.ts` 或 `page.test.tsx` + 最小 mock 骨架。

**[MINOR] High** — **[P3-2] peak RSS 門檻在 CI 易 flaky**  
- 證據：「16GB concurrency=2 總 RSS<=tier*0.6 否則降載」。  
- 修法：mock `psutil`/注入假 RSS，或標 `@pytest.mark.integration` + 僅本地跑；truth-table 單元與 RSS 分離。

**4. 可疑 quant 假設** — 無額外 blocking（§A 已標 batch 入口未共用；P4-2 + §G 方向正確）。

**5. 過度工程** — 無

**6. OOM/並行** — 有（見 [P3-2] flaky）；§B Phase 3 與 1/2 序列依賴正確。

**7. Cache 正確性** — 無新增 blocking

**8. API/型別/相容** — 有（見 P2-3 browse 契約）

**9. 測試品質** — 有（P4-2 測試檔、G2、RSS）

**10. Agent 可執行性** — 有  
**[MAJOR] High** — **§0「不必回讀 SPEC」與多 Task 矛盾**  
- 證據：§0 L6；[P3-2]「truth-table 見 SPEC §P Phase 3」；派工範本「讀 SPEC §相關 Task」。  
- 失敗：冷啟動 agent 漏 FFACT truth-table → 錯 n_jobs。  
- 修法：§0 增「Phase 3 truth-table 內嵌」或 [P3-2] 貼滿表；派工範本改「僅讀 TODO §0+該 Task」。

**[MINOR] Medium** — **[P1-4] 方法名不實**  
- 證據：TODO「save/append」；實際 `FeatureRegistry.add()`（`feature_registry.py:41`）。  
- 修法：改為 `add()` upsert 或新增 `upsert()`。

**[MINOR] Low** — **[P2-1] 舊 _hash8 遷移測試不足**  
- 證據：「舊 _hash8 task 映射/忽略」；驗證僅新 register/restore 同 id。  
- 修法：fixture 含 `browse_BTCUSDT_1h_{hash8}` 重啟不 crash 且可 browse。

---

### §2 範本錨點 + 獵空殼

| 錨點 | 結果 |
|------|------|
| SPEC §RISK/§A/§C/§G/§P/§V/§R/§N | 有；§G 可證偽條款具體 |
| §G 非僅 aggregate | 有全量 chunk + NaN mask hash |
| Task 空殼 | **[P4-1] config 內容**、**[P2-4] G2 fixture**、**[P1-1]/[P2-5] 測試檔** 偏空 |
| 逐 Task 冷啟動 | Batch 1 四合一過重；**P3-2/P2-3** 單讀 TODO 不足 |

**§B 拓撲（同檔不並行）** — **無 blocking**  
- Batch 1：P1-2/P1-3 同 `batch_service`，同批序列改 ✓  
- Batch 3：標「不可與 Phase 1/2 並行」✓  
- Batch 4：P4-1→P4-2 ✓  
- Batch 2a/2b：P2-3/P2-4 同檔同批 ✓  

**改既有函式之 caller 同步** — **有缺口**（見 P2-2 測試、P4-2 `test_multi_symbol_ic_first.py`、P3-1 應點名 `test_slow_path_parallel.py`）

---

## 各 Task 冷啟動快評（不讀 SPEC 能否開寫）

| Task | 可獨立？ | 備註 |
|------|----------|------|
| P1-1 | 是 | 檔案+行為清楚；缺測試檔名 |
| P1-2 | 部分 | 需一併處理 `_record_item_result` |
| P1-3 | 是 | JSONL 路徑明確 |
| P1-4 | 是 | 改 `add()` upsert，非 save/append |
| P2-1 | 是 | 行號略漂，邏輯清楚 |
| P2-2 | 否 | 缺測試/main 遷移清單 |
| P2-3 | 否 | 依 P2-2；manifest vs h5py 未解 |
| P2-4 | 部分 | 缺 G2 fixture 路徑 |
| P2-5 | 部分 | 缺 unit 檔案路徑 |
| P3-1 | 是 | 驗證數值完整 |
| P3-2 | 否 | truth-table 在 SPEC |
| P4-1 | 部分 | 缺 config 撰寫步驟、三 symbol |
| P4-2 | 否 | 依 P4-1；缺測試檔 scope |

---

## 優先修補順序（建議）

1. [P2-2] 補測試/lifespan/注入清單  
2. [P2-3] 解 manifest↔browse 契約  
3. [P1-2] 補 `_record_item_result` 語義  
4. [P4-2] 列 `test_multi_symbol_ic_first.py`  
5. [P4-1] 補 config 建立 + 三 symbol smoke；Manifest 改全量 hash  
6. [P2-4] G2 fixture Task；§0 內嵌 Phase 3 truth-table  

---

STATUS: DONE
