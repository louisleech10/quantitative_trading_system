# 批次發現（從 checkpoint 列舊批次）— SPEC（V13，2026-06-03）

> 來源：使用者重啟後仍看不到舊批次彙整(dda0000d 在 disk 卻無前端線索)。R2 僅往後存、救不到舊批次 → 需發現 path。對應 TODO：N/A(中型)。

## §RISK 風險分級
- 大小：**中**。命中原則：無 (a)-(d)(唯讀列 disk checkpoint + 前端下拉,不改資料/計算)。動 `feature_factory_batch_service`(讀)+ 新 route + 前端。→ cursor。

## §A 假設與待使用者確認
- 已驗證事實:① disk 有 `data_cache/feature_preprocessing/batch_state_*.json`,含 `completed_items[]`(symbol/output_paths/browse_task_id)+ `request_payload.timeframe` + `last_updated_at`;**dda0000d=BTCUSDT/ETHUSDT/DOGEUSDT 1h completed=3** 可恢復;② R1(已實作)`get_batch_quality_summary` 可由 batch_id 從 checkpoint 重建;③ R2(已實作)只在修復後啟動的批次存 `ff:lastBatchTaskId` → **救不到舊批次**;④ 既有「最近瀏覽」下拉(`ff:explorerRecentTasks`)為可複用模式。
- 待確認:無。
- 已確認結果:使用者 2026-06-03 回報重啟後舊批次彙整不見、問是否要重跑(答:不必,需發現 path)。

## §C 約束
- 解耦 7 條;**唯讀**(只列 checkpoint,不寫/不改品質計算/特徵資料)。後端 `feature_factory_batch_service.py` + `api/routes/feature_factory.py` 新 route + 前端 `BatchQualityOverview`/`page.tsx`/store。

## §G Golden / Baseline
- N/A(發現/列表/UX,無數值不變性)→ 見 §N。以單元測試(tmp checkpoints → 列表正確)替代。

## §P Phase 與依賴
### Phase 1 — 後端列舉 + 前端下拉（依賴：R1 已在工作樹）
**Task D1 — 後端列出可恢復批次**
- 檔案:`api/services/feature_factory_batch_service.py` 新增 `list_recoverable_batches() -> list[dict]`;`api/routes/feature_factory.py` 新增 `GET /batch/list`(或 `/batches`)。
- 改法:掃 `self._checkpoint_dir` 的 `batch_state_*.json`,對 **completed_items 非空** 者回 `{batch_id, symbols:[...], timeframe, completed_count, updated_at}`;依 `updated_at` 新→舊排序;completed=0 排除;壞檔跳過不報錯。
- 驗證:`pytest tests/api/` 在 tmp checkpoint_dir 放 3 個 checkpoint(2 有 completed_items、1 completed=0)→ 斷言列表含 2 個、含正確 symbols/timeframe、completed=0 被排除、新→舊排序。
- 邊界:無 checkpoint→空 list;壞 JSON→跳過;completed_items 空→排除。
- 不可做:不寫 disk;不改品質計算。

**Task D2 — 前端「最近批次」下拉 + 選取載入彙整**
- 檔案:`frontend/src/components/feature-factory/BatchQualityOverview.tsx`(+ `page.tsx`/store/type)。
- 改法:無 live `batchTask` 時,呼叫 `GET /batch/list` 填「最近批次」下拉(比照既有「最近瀏覽」模式);選一個 → `fetch /batch/{id}/quality`(R1 從 checkpoint 重建)→ 顯示彙整。可選:預設自動選最新一筆。
- 驗證:前端 unit——mock `/batch/list` 回 2 批次 → 下拉渲染 2 項;選取 → 發 `/batch/{id}/quality` 請求並渲染彙整;空 list → 顯示「無歷史批次」空狀態(不報錯);`npm run build` pass。
- 邊界:空 list / 單一批次 / 選取的 id 後端回 None(checkpoint 失效)→「批次已失效」不崩潰。
- 不可做:不得移除既有「最近瀏覽」;不得無限重抓。

## §V 驗證策略與邊界測試目錄
- 層級:後端單元(tmp checkpoints → 列表)、前端 unit(下拉渲染+選取載入)。可獨立 `pytest tests/api/` + `npm run test`。
- 防假綠:不得放寬既有斷言;新斷言對應「列表排除 completed=0、新→舊、選取載入彙整」。
- 邊界:無/單一/多 checkpoint、completed=0、壞 JSON、選取 id 失效。

## §R 回退
- 單 commit 可 revert;唯讀列舉 + 前端下拉,零資料/數值風險。

## §N N/A 登記
- §G Golden:N/A — 發現/列表/UX 無數值不變性,以單元測試替代。
- §0.A 反幻覺:N/A(執行端合約覆蓋)。§1.1 C-OPT 表:N/A(無新效能硬約束)。
