# 批次品質彙整 重啟/Refresh 持久化 — SPEC（V13，2026-06-03）

> 來源：使用者回報「重啟前後端 + refresh 頁面 → 批次品質彙整全沒了」。根因實測確認(下)。對應 TODO：N/A(中型)。

## §RISK 風險分級
- 大小：**中**。命中原則：無 (a)-(d)(recovery/持久化,不改品質計算/特徵數值)。動 `feature_factory_batch_service`(讀 checkpoint)+ 前端 store/page。→ cursor。

## §A 假設與待使用者確認
- 已驗證事實:① 前端 `batchTask`(含 batch_task_id)是記憶體 Zustand,**未持久化 localStorage**(featureFactoryStore.ts:334 初始 null,持久化的只有 `ff:explorerRecentTasks`/`ff:validationSummaryByTask`)→ refresh 即丟;② `get_batch_quality_summary`(batch_service)**純記憶體**:`task=self._tasks.get(id); if not task: return None` → API 重啟即 None;③ checkpoint **有持久化** `batch_state_<id>.json`,`completed_items[]` 含 `output_paths`(manifest 路徑)+ `browse_task_id`(實機存在 `batch_state_dda0000d-...json` 61KB);④ 品質計算(_compute_symbol_quality / 注入 adapter)只需 results(symbol→manifest 路徑)即可重算。
- 待確認:無。
- 已確認結果:使用者 2026-06-03 回報即此(前後端重啟 + refresh → 空)。

## §C 約束
- 解耦 7 條;**不改品質計算邏輯/特徵數值**(此為「重啟後從 disk 重建 + 前端持久化 id」)。後端 `feature_factory_batch_service.py`,前端 `featureFactoryStore.ts`/`page.tsx`/`BatchQualityOverview`。

## §G Golden / Baseline
- N/A(recovery/持久化,無數值不變性)→ 見 §N。以整合測試(重啟模擬後彙整非空且 symbol/grade 正確)替代。

## §P Phase 與依賴
### Phase 1 — 後端 checkpoint fallback + 前端持久化（依賴：無）
**Task R1 — get_batch_quality_summary checkpoint fallback（後端,撐過 API 重啟）**
- 檔案:`api/services/feature_factory_batch_service.py` → `get_batch_quality_summary()`。
- 改法:`self._tasks` 無此 id 時,**載 checkpoint(`_load_checkpoint(batch_id)`)**,從 `completed_items[]` 重建 `results = {symbol: output_paths[0]}`(沿用 `_results_from_completed`),再走既有品質計算回傳彙整;checkpoint 也無 → 回 None(維持現狀)。
- 驗證:`pytest` 跑完一個 mock batch 後**清空 `self._tasks`**(模擬重啟),呼叫 `get_batch_quality_summary(id)` 斷言**回傳非 None、summaries 含全部成功 symbol、grade 與清空前一致**。
- 邊界:checkpoint 不存在→None;completed_items 空→空 summaries(非報錯);manifest 路徑已不存在→該 symbol 跳過(現有 _compute_symbol_quality 容錯)。
- 不可做:不改品質計算數值;不靠記憶體。

**Task R2 — 前端持久化 batch id + refresh 後重抓（前端）**
- 檔案:`frontend/src/store/featureFactoryStore.ts`(+ `page.tsx` 掛載邏輯)。
- 改法:batch 啟動/完成時把 `batch_task_id` 存 localStorage(如 `ff:lastBatchTaskId`,比照既有 `ff:explorerRecentTasks` 模式);頁面掛載時若無 live `batchTask`,讀持久化 id 並 `fetch /batch/{id}/quality` 還原彙整(後端有 R1 fallback 撐住)。
- 驗證:前端 unit/整合——模擬 reload(store 重置 + localStorage 有 id)→ 掛載後發出 `/batch/{id}/quality` 請求;無持久化 id → 不請求、顯示空狀態(不報錯);`npm run build` pass。
- 邊界:localStorage 無 id(從未跑批次)→ 空狀態;id 對應 checkpoint 已不存在→後端回 None,前端顯示「批次已失效」而非崩潰。
- 不可做:不得移除既有「最近瀏覽」邏輯;不得無限重抓(失敗一次即停)。

## §V 驗證策略與邊界測試目錄
- 層級:後端整合(清 self._tasks 模擬重啟 → 彙整從 checkpoint 重建)、前端 unit(reload 後用持久化 id 重抓)。可獨立 `pytest tests/api/` + `npm run test`。
- 防假綠:不得放寬既有斷言;新斷言對應「重啟後彙整非空且正確」「前端 reload 重抓」。
- 邊界:checkpoint 在/不在、completed_items 空、manifest 缺、localStorage 有/無 id。

## §R 回退
- 單 commit 可 revert;純 recovery/持久化,不動品質計算與特徵資料,零數值風險。

## §N N/A 登記
- §G Golden:N/A — recovery/持久化無數值不變性,以整合測試(重啟後彙整非空+symbol/grade 正確)替代。
- §0.A 反幻覺:N/A(執行端合約覆蓋)。§1.1 C-OPT 表:N/A(無新效能硬約束)。
