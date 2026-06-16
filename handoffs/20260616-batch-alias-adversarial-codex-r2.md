# Batch Alias SPEC/TODO Adversarial Review r2

## Verdict：FAIL（V2 仍需修補後派工）

本輪只讀 `docs/`、`momentum/`、`api/`、`frontend/` 與 r1 handoff；未改上述目錄。已依 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0+§1 對 V2 SPEC/TODO/manifest 與真實程式錨點複審。

## r1 Findings Reconcile Check

- r1-B1 batch_id 參數鏈：**文件層已補齊但仍不合格**。V2 已明寫 `generate_features(..., batch_id=None)`、`_compute_single(..., batch_id)`、execute loop 傳 `checkpoint["batch_id"]`、registry.add 三處讀入；對照現況 `generate_features` 無 batch_id（`feature_factory.py:226-237`）、`_compute_single` 無 batch_id（`feature_factory_batch_service.py:1052-1058`）、executor 未傳（`:450-458`）、registry.add 三處無 batch_id（`:3197/:3342/:3474`）。但 V2 指定用 `self._current_batch_id` 作隱式 context，引入新 BLOCKING #1。
- r1-B2 mark_deleting transaction：**已修補到文件**。V2 SPEC/TODO/manifest 都要求候選 filter 與 `mark_deleting()` transaction 改 `not (alias or batch_alias)`；真實現況確實仍只看 alias（`run_lifecycle.py:141-146`、`feature_registry.py:184-197`），所以派工方向正確。
- r1-MAJOR 404 定死：**已修補**。V2 統一為 `404 batch_not_found`，不再允許 affected-0。
- r1-MAJOR 同 run 多批：**部分修補**。V2 選 latest overwrite + batch_id 變更時 reset batch_alias；但對「非批次單 run 再生成同 key」的 batch ownership 未定，見 MAJOR #1。
- r1-MAJOR filteredRuns 位置：**已修補**。V2 指定 `FeatureExplorer.tsx` haystack；真實位置為 `frontend/src/components/feature-factory/FeatureExplorer.tsx:89-107`。
- r1-MAJOR batch_alias 清除 transaction gate：**部分修補**。V2 補 `mark_deleting()` gate 與清除後回 cleanup 候選，但未定義 `set_batch_alias()` 遇到 deleting entries 的 affected/skip/409 語義，見 MAJOR #2。
- r1-MINOR §A 行號：**已修補**。V2 明確標「checkpoint 有 batch_id 但未進生成路徑」。
- r1-MINOR group header disambiguation：**已修補**。TODO 驗證要求同 symbol 多 batch header 可辨。

## Findings

### [BLOCKING][High] `self._current_batch_id` 是 mutable 隱式 context；V2 未要求 try/finally 清理或避免長壽命 factory 併發污染
- 證據：
  - V2 SPEC Task 1.1：「`generate_features` 加 `batch_id` 參數→存 `self._current_batch_id`→registry.add 三處讀入」。
  - 真實 `FeatureFactoryService` 建構單一長壽命 `self._factory`（`api/services/feature_factory_service.py:62-65`），normal generation 以 `run_in_executor` 跑同一 factory（`:226-240`、`:357-366`）。
  - `_run_with_env_overrides()` 可直接呼叫 `factory._generate_features_impl`（`:474-488`），繞過 `generate_features` wrapper；而 registry.add 實際在 `_generate_features_impl` 下游三處執行（`feature_factory.py:3197/:3342/:3474`）。
- 會怎麼失敗：
  - 若實作者照 V2 只在 `generate_features` 設 `self._current_batch_id`，但沒有 `try/finally` reset，後續同 factory 的非批次生成或 direct `_generate_features_impl` 可能讀到 stale batch_id。
  - 若兩個 generation 任務併發使用同一 service factory，mutable instance state 可在 registry.add 前被另一任務覆寫，造成 batch_id cross-run 污染。這正是本功能要避免的 metadata 污染。
  - ProcessPool 子進程本身「可拿到 batch_id」只有在 `_compute_single` 顯式傳參並呼叫 `generate_features(batch_id=...)` 時成立；`self._current_batch_id` 不是跨進程 context，不能靠父進程 state。
- 修法：
  - 首選：不要用 `self._current_batch_id`；把 `batch_id: Optional[str]` 顯式傳到 `_generate_features_impl`，registry.add 三處使用 local parameter。
  - 若堅持 instance state，SPEC/TODO 必須要求 `generate_features` 用 `previous = getattr(...); try: set; finally: restore/clear`，並加併發/連續呼叫測試：batch call 後同 factory non-batch call 不保留 batch_id；兩個並行 calls 不互相污染。更保守仍是顯式參數。

### [MAJOR][High] latest overwrite + batch_alias reset 未定義 `batch_id=None` 的同 key 再生成語義
- 證據：
  - V2 SPEC/TODO：「batch_id 不 merge-preserve→latest overwrite」「batch_id 變更時 batch_alias reset」「單 run（非批次）路徑 batch_id=None 不寫」。
  - 真實 `FeatureRegistry.add()` upsert key 是 `(symbol,timeframe,config_hash)`，merge 從 `incoming` 開始，只 preserve `alias,size_bytes,created_at`（`feature_registry.py:96-105`）。
- 會怎麼失敗：
  - 如果 non-batch add 不帶 `batch_id` 且 latest overwrite 以 incoming 為準，同 key 單 run 再生成會清掉原 batch_id/batch_alias；使用者先命名整批，後續單獨重跑其中一個 run，該 run 靜默脫離批次。
  - 如果實作者為避免上述問題而 preserve existing batch_id when incoming missing，則又違反「batch_id latest overwrite」；新舊語義取決於實作者臨場解讀。
- 修法：V2 必須明確三態：incoming batch_id 為新值、incoming batch_id 為同值、incoming batch_id absent/None。建議定死其中一個：A) latest owner 包含 non-batch，None 會清 batch_id/batch_alias；或 B) non-batch 不改 batch ownership。兩者都要有測試，不能只測「第二批 batch overwrite」。

### [MAJOR][High] `set_batch_alias()` 對 deleting entries 的 transaction 語義仍未定
- 證據：
  - V2 已要求 `mark_deleting()` 檢 `alias or batch_alias`，但 `set_batch_alias(batch_id, batch_alias)` 只寫「registry transaction，更新所有該 batch_id entry，回 affected 數」。
  - 真實 registry 有 `deleting` 狀態：`set_alias()` 遇 deleting 會 `RunBusyError`（`feature_registry.py:149-153`）；`mark_deleting()` 會標 `target["deleting"]=True`（`:188-194`）。
- 會怎麼失敗：
  - cleanup 已把某 entry 標 deleting 後，PATCH batch alias 仍可能把 batch_alias 寫入 deleting entry 並計入 affected；API 回成功，但 run 隨後被刪。
  - 清除 batch_alias 時亦同：若 deleting entry 被計入 affected，前端會呈現成功，實際 registry/artifact lifecycle 已不可逆。
- 修法：SPEC/TODO 定義 `set_batch_alias` 對 deleting entries 的行為。建議與 `set_alias()` 一致：遇任何 target deleting 則 fail whole transaction with `RunBusyError`/409；或明確 skip deleting and report `skipped_deleting`，但不能只回 affected 數。測試需覆蓋 deleting entry 不被成功更新。

### [MAJOR][Medium] V2 沒有要求 preserve per-run `alias` 與 batch_id reset 的組合測試
- 證據：
  - V2 強調「不覆寫 per-run alias」與「batch_id 變更時 batch_alias reset」，但驗證只寫 set_batch_alias 不動 per-run alias、同 run 第二批 batch_id overwrite。
  - 真實 `add()` preserve alias 的行為在 `feature_registry.py:101-104`；新 batch reset batch_alias 必須與 preserve alias 同時成立。
- 會怎麼失敗：實作者在 `batch_id` 變更時若粗暴重建 entry，可能同時清掉 per-run alias；或為 preserve alias 把 batch_alias 一起 preserve，違反 reset。兩個方向都會破壞核心 UX。
- 修法：新增不可省測試：existing entry 有 `alias="manual"`、`batch_id="old"`、`batch_alias="old-name"`；incoming `batch_id="new"` 後結果必須 `alias="manual"` preserved、`batch_id="new"`、`batch_alias` cleared。

### [MINOR][Medium] `_compute_single` 傳參說「checkpoint["batch_id"]」但實際 `_process_item_wave` 已有 `task_id`
- 證據：`_process_item_wave()` 內 `task_id = str(task["task_id"])`（`feature_factory_batch_service.py:408-410`），executor 提交點在 `:450-458`；checkpoint 也有 `batch_id`（`:751-767`）。
- 風險：不是功能阻斷，但派工時可能讓實作者在 checkpoint/task 兩個來源間做不必要改動。
- 修法：TODO 寫「傳 `str(checkpoint["batch_id"])`（應等於 `task_id`，可 assert/log 不一致）」或直接指定使用 `task_id` 並保留 checkpoint source-of-truth 測試。

## §1 十類必查摘要

1. 矛盾/互斥：有。`batch_id=None` 同 key 再生成與 latest overwrite 未定。
2. 漏項/端到端：有。`self._current_batch_id` lifecycle/併發與 direct `_generate_features_impl` 路徑未規範。
3. 不可測驗收：有。缺 stale/parallel batch_id 污染測試；缺 deleting entry batch alias transaction 測試。
4. 可疑 quant 假設：無。本批純 metadata；但 metadata 污染會影響 run lifecycle/cleanup。
5. 過度工程：無。Phase 1 不做 batch entity 可接受。
6. OOM/並行：有輕度並行正確性風險；不是 RAM/OOM，而是 shared instance state。
7. Cache 正確性：有。registry upsert metadata ownership 三態未定。
8. API/型別/相容：404 已一致；RunInfo optional 欄位相容。
9. 測試品質：需補併發/stale context、None ownership、alias-preserve+batch-reset、deleting set_batch_alias。
10. Agent 可執行性：V2 比 r1 好很多，但 BLOCKING #1 會讓不同實作者做出不同且不可審的 batch_id plumbing。

## 被當成事實的未驗證假設

- 「用 `self._current_batch_id` 作生成 context」被當成安全實作路徑，但真實 service 有長壽命 factory + executor，且有 direct `_generate_features_impl` caller；未驗證無 stale/併發污染。
- 「latest overwrite + batch_alias reset」被當成已定義語義，但只定義了新 batch 覆蓋舊 batch，未定義 non-batch 同 key 再生成。
- 「set_batch_alias registry transaction」被當成足夠，但未處理現有 deleting lifecycle state；真實 per-run alias 已有 deleting gate。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md §0+§1、docs/BATCH_ALIAS_SPEC.md、docs/BATCH_ALIAS_TODO.md、docs/BATCH_ALIAS_MANIFEST.md、r1 handoff；已抽查指定錨點 generate_features:226、_compute_single:1052、registry.add:3197/3342/3474、run_lifecycle auto_cleanup/mark_deleting、FeatureExplorer filteredRuns。
TESTS_RUN: 未跑測試；本任務為 read-only adversarial review，使用 rg/nl/sed 靜態查證。
FAILURES_SEEN: none
SCOPE_CHANGES: none；只新增 handoffs/20260616-batch-alias-adversarial-codex-r2.md，未改 docs/momentum/api/frontend/data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 本次無；review finding 只涉及 metadata/API schema 設計，無數值輸出變更。
HANDOFF_NOT_UPDATED: 使用者明確要求輸出到 handoffs/20260616-batch-alias-adversarial-codex-r2.md，且本任務限定只讀 docs/momentum/api/frontend；未改根 HANDOFF.md。
STATUS: DONE
