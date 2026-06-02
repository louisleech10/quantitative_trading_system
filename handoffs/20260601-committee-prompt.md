# 規劃委員會諮詢（READ-ONLY，不得寫檔）

你是規劃顧問。**只讀程式碼、只給設計建議，禁止修改任何檔案。**

請先讀 `docs/MULTI_SYMBOL_DIAGNOSIS_20260601.md`（完整事實與行號）與下列檔案：
- `api/services/feature_factory_batch_service.py`
- `momentum/core/config.py`（`get_slowpath_n_jobs` / `batch_nested_environment` / `_SLOWPATH_NJOBS_BY_TIER_GB`）
- `frontend/src/store/featureFactoryStore.ts`（`pollBatchStatus`）
- `frontend/src/components/feature-factory/GenerationProgress.tsx`
- `frontend/src/app/feature-factory/page.tsx`（`handleSelectBatchSymbol`）

背景：本機 8GB tier。目標是讓多 symbol 批次「per-symbol 行為與單 symbol 一致」，同時為未來
`concurrent_symbols>1` 並行預留正確設計。

針對以下三個爭議點，各給「建議方案 + 理由 + 風險 + 你不同意現有判斷的地方」。**簡潔，重點是判斷不是長篇。**

**C1 — browse 註冊改後端自動化**
目前 browse 註冊靠前端在 batch 完成後呼叫，依賴記憶體中的 `batchTask.results`，API 重啟或輪詢中斷就丟失。
問：應在何處讓後端於「每個 symbol 完成時」自動註冊 browse？落在 `_record_item_result`？還是完成 hook？
checkpoint 是否該持久化 browse id 以撐過 API 重啟？有無 race／重複註冊風險？

**C2 — worker 預算並行感知化（取代 FFACT_BATCH_NESTED 一刀切）**
現況：`concurrent_symbols=1` 仍透過 FFACT_BATCH_NESTED 把 joblib n_jobs 強制為 1，在 ≥16GB tier 屬過度保守。
提議：總 worker 預算 = f(tier, concurrent_symbols)，concurrent=1 拿完整單 symbol 預算，concurrent=N 除以 N。
問：這公式的正確落點（`_resolve_concurrent_symbols` / `get_slowpath_n_jobs` 簽名是否要帶 concurrency）？
是否會破壞既有單 symbol 路徑？OOM 安全邊界怎麼定？是否仍需保留 FFACT_BATCH_NESTED 作為並行旗標？

**C3 — IC-First vs 標準路徑是否統一**
多 symbol 走 `_compute_single_ic_first`（設 FFACT_IC_FIRST_PIPELINE=1，輸出 L7_raw），
單 symbol 走 `_compute_single`（標準）。問：此分岔是否就是輸出格式（manifest+raw 無 .h5）、
品質檢查 h5py 失敗、瀏覽路徑分岔的根源？兩者該統一嗎？若統一，往哪個方向（都走 IC-First？都走標準？）
對 ML 正確性（防 leakage / IC Gatekeeper 下游）有何影響？

輸出格式（每點）：
```
## C{n}
建議：<一句>
理由：<2-3 點>
風險／反對：<你看到但報告沒提的>
```
