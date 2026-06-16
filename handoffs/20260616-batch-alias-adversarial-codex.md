# Batch Alias SPEC/TODO Adversarial Review V13

## Verdict：需修補後派工

本審查只讀文件與程式碼，未改 `docs/`、`momentum/`、`api/`、`frontend/`。依 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0+§1，結論是方向可行，但 SPEC/TODO 目前不可直接派工：有 2 個 BLOCKING、4 個 MAJOR、2 個 MINOR。

## Findings

### [BLOCKING][High] batch_id「透傳」不是既有生成 context，SPEC/TODO 未指定必改的函式簽名與 ProcessPool 參數鏈
- 證據：
  - SPEC Task 1.1：「`feature_factory.py` registry.add 三處透傳 batch_id（從生成 context）；batch service per-symbol 生成傳 batch_id。」`docs/BATCH_ALIAS_SPEC.md:34`
  - TODO Task 1.1：「registry.add 三處(:3197/3342/3474)透傳 batch_id(從生成 context/參數,無則 None)」「batch service per-symbol 生成把 batch_id 傳入生成→registry.add。」`docs/BATCH_ALIAS_TODO.md:28-29`
  - 真實程式：`FeatureFactory.generate_features(...)` 形參到 `lease_sink` 為止，沒有 `batch_id`；它呼叫 `_generate_features_impl(...)` 也沒有 `batch_id`。`momentum/FeatureEngineering/feature_factory.py:226-244`, `:253-263`
  - 真實 batch 路徑：`_process_item_wave()` 用 `ProcessPoolExecutor`，`run_in_executor(executor, compute_fn, symbol, timeframe, request.config_override, request.force_regenerate, batch_cache_dir)`，沒有 task_id/batch_id。`api/services/feature_factory_batch_service.py:442-458`
  - 子進程 `_compute_single(symbol,timeframe,config_override,force_regenerate,cache_dir)` 重新 `create_feature_factory()` 後呼叫 `factory.generate_features(...)`，也沒有 batch_id。`api/services/feature_factory_batch_service.py:1052-1081`
  - registry.add 三處確實存在，但 add payload 只有 symbol/timeframe/config_hash/feature_count/row_count/path。`momentum/FeatureEngineering/feature_factory.py:3197-3206`, `:3342-3351`, `:3474-3483`
- 會怎麼失敗：實作者若照「從生成 context」找，會發現三個 add 呼叫處沒有 context 變數；batch service 的 batch_id 在父進程 task/checkpoint 中，沒有穿過 executor boundary。最可能產物是只改 registry.add schema/test mock，真實 batch 生成 registry entry 仍無 batch_id。
- 修法：
  - SPEC/TODO 明確列出簽名鏈：`FeatureFactory.generate_features(..., batch_id: Optional[str] = None)`、`_generate_features_impl(..., batch_id=None)`、三個 `_registry.add` payload 加 `batch_id` when truthy。
  - `FeatureFactoryBatchService._compute_single(..., batch_id: Optional[str], ...)` 加參數；`_process_item_wave()` 的 `run_in_executor` 傳 `task_id`。
  - 非 batch API/service 呼叫不傳或傳 None；必要時 `_run_with_env_overrides`/Phase D wrapper 也要保留可選 batch_id，避免非 CGSA/CGSA/old path 漏路徑。

### [BLOCKING][High] auto-cleanup 只改候選不夠；`mark_deleting()` transaction 仍只檢 alias，會與 set_batch_alias race 後誤清命名批次 run
- 證據：
  - SPEC/TODO 只要求候選由 `not entry.get("alias")` 改 `not (alias or batch_alias)`。`docs/BATCH_ALIAS_SPEC.md:22`, `:39-41`; `docs/BATCH_ALIAS_TODO.md:7`, `:40`, `:43-44`
  - 真實 cleanup 先 snapshot/filter entries，再逐一呼叫 `registry.mark_deleting(...)`。`momentum/FeatureEngineering/run_lifecycle.py:141-164`
  - 真實 `mark_deleting()` transaction 內只檢 `target.get("alias")`，不檢 batch_alias。`momentum/FeatureEngineering/feature_registry.py:184-197`
  - per-run alias 透過 `RunLifecycleManager.set_run_alias()` 先拿 run lease，再 registry.set_alias。`momentum/FeatureEngineering/run_lifecycle.py:117-130`
  - SPEC 新 `set_batch_alias` 只說 registry transaction，沒有 run lease 或 mark_deleting 二次防線。`docs/BATCH_ALIAS_SPEC.md:34`
- 會怎麼失敗：cleanup 取得候選 snapshot 時 run 尚無 batch_alias；PATCH batch alias 在 cleanup 進行中寫入 batch_alias；cleanup 接著 `mark_deleting()`，因只檢 alias 仍標 deleting 並刪除。相反順序下，set_batch_alias 也可能更新已 deleting/待刪 entry，最後仍被刪。
- 修法：
  - `FeatureRegistry.mark_deleting()` 必須同時保護 `alias` 和 `batch_alias`，有任一則 return False。
  - `set_batch_alias()` transaction 內應跳過/拒絕 `deleting` entries，並將 affected semantics 寫清。
  - 測試不能只測靜態候選；需加 race/transaction 級測試：候選 snapshot 後加 batch_alias，再 mark_deleting 應回 False 且 cleanup 不刪。

### [MAJOR][High] API contract 矛盾：SPEC/manifest 固定查無 404，TODO 允許 404 或 affected 0
- 證據：
  - Manifest [BA-3]：「batch_id 查無→404。」`docs/BATCH_ALIAS_MANIFEST.md:8`
  - SPEC Task 1.2：「batch_id 查無→404 `batch_not_found`。」`docs/BATCH_ALIAS_SPEC.md:39`
  - TODO Task 1.2：「batch_id 無對應 entry→404 `batch_not_found`(回 affected 0 亦可,擇一寫死測試)」「batch_id 查無→404/affected 0(寫死)」。`docs/BATCH_ALIAS_TODO.md:38`, `:43`
- 會怎麼失敗：前後端與測試可選不同 contract；實作者可能回 200/affected=0，前端以成功 refresh 呈現，違反 manifest/API 可觀測錯誤語義。
- 修法：TODO 與 SPEC 統一為 404 `batch_not_found`。`FeatureRegistry.set_batch_alias()` 可回 0，但 service/route 必須把 0 轉 404，且測試固定此行為。

### [MAJOR][Medium] `add()` 的 merge-preserve 擴到 batch_id/batch_alias 會造成 stale batch membership；不擴則會覆蓋既有 batch alias，SPEC 未定同一 run 多批次語義
- 證據：
  - TODO 要求 `add(entry)` 對 `batch_id`/`batch_alias` 做 merge-preserve「同 key 保留既有非空,與現有 alias/created_at 同模式」。`docs/BATCH_ALIAS_TODO.md:26`
  - 真實 add upsert key 是 `(symbol,timeframe,config_hash)`，既有 preserve 欄位只有 `alias,size_bytes,created_at`。`momentum/FeatureEngineering/feature_registry.py:86-107`, `:242-248`
  - Manifest 說批次完成時把 `batch_id` 寫進每個 run，不靠 checkpoint 反推。`docs/BATCH_ALIAS_MANIFEST.md:6`
- 會怎麼失敗：
  - 若保留既有 `batch_id`，同一 symbol/timeframe/config_hash 被新 batch 重新生成時仍掛在舊 batch，新的 `/batch/{new_id}/alias` affected 可能少於完成數，整批 rename 漏 run。
  - 若覆蓋 `batch_id`，舊 batch alias 關聯被奪走，舊 batch rename/listing 語義消失。
  - 只用單一 `batch_id` 欄位無法表示「同一 run identity 曾由多個 batch 產生」。這可以接受為 Phase 1 限制，但必須明確選擇 latest-batch-wins 或 first-batch-wins，並測試。
- 修法：SPEC 補「同 key 再生成」決策。保守建議：`batch_id` latest-generation wins；`batch_alias` 清空或只在同 batch_id 時 preserve，避免新 batch 繼承舊 batch 名。若要保留歷史批次語義，需 Phase 3 batch entity，不應在本批假裝解決。

### [MAJOR][High] batch_alias 清除語義只寫欄位清除，未寫 affected/entry 保護與 cleanup 回候選的 transaction gate
- 證據：
  - SPEC：「batch_alias 空字串=清除」「清除後該 run 若無 alias 則回到 cleanup 候選」。`docs/BATCH_ALIAS_SPEC.md:36`, `:41`
  - TODO：「strip 空=清除」「batch_alias 空清除後該 run 無 alias 則回 cleanup 候選」。`docs/BATCH_ALIAS_TODO.md:27`, `:43`
  - 真實 registry 有 `deleting` 狀態與 transaction mutation。`momentum/FeatureEngineering/feature_registry.py:184-211`
- 會怎麼失敗：清除若只是 `target.pop("batch_alias")`，但 target 正在 deleting 或 cleanup 進行中，API 可能回 affected 成功，下一瞬間 run 被刪；或測試只驗 list_runs 不驗 auto_cleanup 清除後可刪，導致語義未落地。
- 修法：定義 `set_batch_alias` 對 `deleting` entry 的行為（建議不更新且不計 affected，service 可視情況 409/partial 不做 partial 更好）；加兩個測試：清除後 `keep_latest=0` 會刪未命名 run；清除時 deleting entry 不回成功。

### [MAJOR][Medium] 前端搜尋修改位置寫錯，`filteredRuns` 不在 `runExplorer.ts`
- 證據：
  - SPEC/TODO 都把搜尋 haystack 加 batch_alias 放在 `runExplorer.ts`。`docs/BATCH_ALIAS_SPEC.md:45`; `docs/BATCH_ALIAS_TODO.md:51`
  - 真實 `runExplorer.ts` 只有 `formatRunLabel/pickDefaultRun/sortRunsByRecency`。`frontend/src/lib/runExplorer.ts:77-123`
  - 真實 `filteredRuns` 與 haystack 在 `FeatureExplorer.tsx`。`frontend/src/components/feature-factory/FeatureExplorer.tsx:89-107`
- 會怎麼失敗：實作者若只改 `runExplorer.ts`，Feature Explorer 搜尋 batch_alias 不會生效；vitest 若只測 formatRunLabel 會假綠。
- 修法：TODO 修改檔案清單加 `FeatureExplorer.tsx`；驗證應包含實際 search input 行為或直接測 filtered haystack 的 component test。

### [MINOR][High] §A 事實行號多數正確，但「batch_id 流經 batch service」行號只證 checkpoint/status，不證生成 path 拿得到 batch_id
- 證據：
  - SPEC §A：「batch_id 流經 batch service（feature_factory_batch_service.py:202/229/288 checkpoint["batch_id"]）」`docs/BATCH_ALIAS_SPEC.md:13`
  - 真實 `:202/:229/:288` 是 resume/status/task state，`:766` 是初始 checkpoint 寫入 batch_id；這些都不在 `_compute_single` 生成參數鏈。`api/services/feature_factory_batch_service.py:202`, `:229`, `:288`, `:766`
- 會怎麼失敗：把 checkpoint/status 有 batch_id 誤當作子進程生成 path 可用 batch_id，導致 BLOCKING #1。
- 修法：§A 拆成 fact-verified：「batch checkpoint/status 有 batch_id」與 assumption/resolution：「生成子進程目前沒有 batch_id，需新增參數鏈」。

### [MINOR][Medium] 前端分組/優先序可實作，但 group header disambiguation 未落到 SPEC/TODO 測試
- 證據：
  - Manifest [BA-4] 說不同 batch 可重名，需用 batch_id/時間 disambiguation。`docs/BATCH_ALIAS_MANIFEST.md:9`
  - SPEC/TODO Task 2.1 只說 header 顯示 batch_alias + rename，邊界列「同 symbol 多 batch」，未明確同 batch_alias 多 batch header 如何區分。`docs/BATCH_ALIAS_SPEC.md:45-47`; `docs/BATCH_ALIAS_TODO.md:53`, `:56-57`
- 會怎麼失敗：兩個 batch 都叫 `prod-candidate` 時 UI 可能顯示兩個同名 group header，使用者無法分辨 rename 目標。
- 修法：指定 header 格式如 `batch_alias · short(batch_id)` 或 hover/full title，測試同名 batch_alias 兩組都可區分且 rename 呼叫各自 batch_id。

## §1 十類必查摘要

1. 矛盾/互斥：有。API 查無 404 vs affected 0；add merge-preserve vs 新 batch membership 未定。
2. 漏項/端到端：有。batch_id 沒有明確穿過 ProcessPool `_compute_single` 與 factory signatures；cleanup mark_deleting 二次防線漏。
3. 不可測驗收：有。cleanup race 只測靜態候選不足；搜尋測試若不碰 FeatureExplorer 會假綠。
4. 可疑 quant 假設：無。此批純 metadata，不碰數值/CGSA/特徵計算；但不得因此跳過 lifecycle correctness。
5. 過度工程：無。未引入一等 batch entity是合理 Phase 1/2，但須明確單一 batch_id 欄位限制。
6. OOM/並行：無新增 OOM 風險；但 ProcessPool 參數鏈是功能正確性風險。
7. Cache 正確性：有 metadata stale 風險。同 key upsert 的 batch_id/batch_alias preserve/overwrite 語義未定。
8. API/型別/相容：有。查無 contract 分歧；RunInfo 加 optional 欄位相容可行。
9. 測試品質：需補 race、same-run-multiple-batch、real FeatureExplorer search、same alias different batch disambiguation。
10. Agent 可執行性：不足。Task 有檔案名與方向，但 BLOCKING #1/#2 需要函式級精確補強。

## 被當成事實的未驗證假設

- 「batch_id 從生成 context 可透傳到 registry.add」是 assumption，不是 fact。已驗證 fact 是 checkpoint/status 有 batch_id；真實生成子進程與 factory signature 目前沒有 batch_id。
- 「auto-cleanup 候選改 `not (alias or batch_alias)` 就是不弱化」是 incomplete assumption。已驗證 fact 是 cleanup 還有 `mark_deleting()` transaction 二次檢查，且目前只看 alias。
- 「add 對 batch_id/batch_alias merge-preserve 與現有 alias/created_at 同模式」是 design assumption。現有 fact 只 preserve alias/size_bytes/created_at，batch_id 的 upsert 語義會影響批次 membership。

## §A 事實行號抽查

- registry.add 三處：PASS。`feature_factory.py:3197`, `:3342`, `:3474` 均為 `_registry.add(...)`。
- `FeatureRegistry.add` merge-preserve：PARTIAL。`feature_registry.py:101-105` 只 preserve `alias,size_bytes,created_at`，SPEC/TODO 要新增欄位語義但未處理同 key 新 batch 衝突。
- `set_alias`：PASS。`feature_registry.py:139-167` 單 run alias，唯一性同 symbol/timeframe。
- auto_cleanup 候選：PASS。`run_lifecycle.py:141-146` 現為 `if not entry.get("alias")`。
- batch checkpoint batch_id：PASS but insufficient。`feature_factory_batch_service.py:766` 初始 checkpoint 有 `batch_id`；`:202/:229/:288` 是 resume/status references，不代表生成子進程能拿到 batch_id。
- frontend label/search：PARTIAL。`formatRunLabel` 在 `runExplorer.ts:77-82`；搜尋 haystack 在 `FeatureExplorer.tsx:89-107`，不是 TODO 所寫 `runExplorer.ts`。

## 建議修補清單

1. 補 batch_id 參數鏈的具體函式簽名、executor 傳參、wrapper 路徑。
2. 補 cleanup transaction 防線：`mark_deleting` 檢 batch_alias；`set_batch_alias` 處理 deleting/race；加 race 測試。
3. 統一 PATCH 查無行為為 404 `batch_not_found`。
4. 明確同 key 再生成的 batch_id/batch_alias 語義，避免 stale membership。
5. 前端搜尋檔案改為 `FeatureExplorer.tsx`，同名 batch_alias group header 加 batch_id disambiguation。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、AGENTS.md、SPEC/TODO/manifest、設計 handoff；已用 rg/nl 抽查 registry.add 三處、FeatureFactory signatures、batch ProcessPool path、registry transactions、auto_cleanup/mark_deleting、API RunInfo/routes/service、前端 label/search/RunManager。
TESTS_RUN: 未跑測試；本任務是 adversarial review，僅做靜態文件與程式碼抽查。
FAILURES_SEEN: none
SCOPE_CHANGES: none；只新增本 handoff 報告，未改 docs/momentum/api/frontend/data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 本次無；審查指出未來會新增 metadata/API schema `batch_id`/`batch_alias`，不影響數值輸出。
HANDOFF_NOT_UPDATED: 根 AGENTS 第一段要求更新 HANDOFF.md，但同檔執行合約第 7 條與本次使用者指定要求寫 handoffs/<task>.md 且禁改 docs/momentum/api/frontend；本次未改根 HANDOFF.md。
STATUS: FAIL — SPEC/TODO 需先修補 batch_id 生成參數鏈、cleanup transaction race、API 查無 contract、同 key 再生成 batch 語義後才可派工。
