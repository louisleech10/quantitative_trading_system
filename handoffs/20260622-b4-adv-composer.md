# B4 adversarial review — Composer — 2026-06-22

## Verdict
需修補後派工。reuse `delete_run` 方向正確，但 SPEC/TODO 對「交易式」、下游失效、B3 互動、HTTP/前端契約的描述與實碼落差大，照現稿實作會留下半刪狀態與 stale UI。

## Findings
1. [BLOCKING|High] §A「registry get 刪除中拋 RunBusyError」為假：`feature_registry.py:139-142` get 不查 deleting；`delete_run` 不 `mark_deleting`（僅 `auto_cleanup` 用）。刪檔窗口內 `list_runs`/`ensure_browse_task_for_run` 仍見 entry。修法：lease-only 語意寫死+reader 行為，或 bulk 前 mark_deleting/失敗 clear。
2. [BLOCKING|High] 「逐 run 原子」不誠實：`_delete_run_locked` 可先刪 features 再 cgsa/registry 失敗；`delete_run` 僅 `not result.errors` 才清 `_tasks`（`:885-896`），partial 失敗留 browse/cache。bulk report 需 `partial`/`skipped` 態+list 隱藏或 second-chance cleanup。
3. [BLOCKING|High] 下游失效清單不全：`_invalidate_task_cache` 未清 `_data_quality_warming_tasks`、disk `data_quality.json`/`feature_stats_cache.parquet`；前端 `selectedRunKey`/`explorer*ByTask`/`validationSummaryByTask`(localStorage)/`batchTask.browse_task_ids` 未列。刪後 Explorer/Quality 仍可點舊 task。
4. [MAJOR|High] Task1.2 checkpoint「標失效」不可執行：`_results_from_completed`/`list_recoverable_batches`/`resume` 不過濾 flag；且 `api/services` 互不重 import，bulk 如何觸發 batch checkpoint 未設計（route 編排？protocol？）。需 schema+所有 readers+接線圖。
5. [MAJOR|High] B3/B4 互動缺規：retention discard reuse `delete_run`（`batch_service.py:1785`）遇 `RunBusyError`→`retention_error`；bulk 刪 pending retention run 不更新 `retention_items` FSM→BatchRetentionPanel 仍顯 pending。需矩陣：bulk+discard、bulk+生成中(active lease)、bulk 後 reconcile。
6. [MAJOR|High] HTTP 207 未定：全成功/全失敗/全 busy/空清單/validation；單刪 partial 回 500（`feature_factory.py:117-118`）bulk 卻 207→同 run 語意分裂。建議 200+per-run status 或完整 status matrix+TS 型別+store 處理。
7. [MAJOR|Medium] 防誤刪不足：RunManager 有 batch 分組+`active` 徽章（`:331-338`）但單刪僅 `confirm`、無禁選 active；bulk 確認未要求 alias/full hash/去重後明細。易誤刪生成中或同 batch 子集。
8. [MINOR|High] Hermetic 偏窄：§V 只提 tmp `data_cache_path`；未涵蓋 batch singleton checkpoint、`feature_factory_service._tasks` 種子、前端 store cache。參考 `test_batch_retention.py` fixture 模式擴充。
9. [MINOR|Medium] d_star 不應清（symbol/tf fingerprint 跨 run）；建議 §N 登記「不清 shared d_star」防 scope creep。RunManager 多選 vs BatchRetentionPanel 不 UI 衝突但可同 run 雙入口，需在 B4/B3 矩陣說明。

## 被當成事實的未驗證假設
- registry deleting tombstone 已存在（實為 lease+alias mutation guard）。
- reuse delete_run ⇒ 下游已失效（checkpoint/batch live/磁碟 quality 未覆蓋）。
- RunBusyError 足夠覆蓋 bulk+single+retention+生成（缺 FSM/retention lock 協調）。
- 207+vitest 三案例可驗收端到端一致性。

STATUS: DONE
