# B4 交易式批次刪除 (Q2-B) TODO
> 版本：DRAFT｜基於 SPEC：docs/B4_BULK_DELETE_SPEC.md｜日期：2026-06-22

## 階段 1：SPEC ID 覆蓋
| 類別 | ID | 節錄 | 落點 |
|---|---|---|---|
| Task | 1.1 | bulk-delete endpoint + 逐 run + aggregate report | Phase1 |
| Task | 1.2 | 下游失效(browse/checkpoint/quality) | Phase1 |
| Task | 2.1 | RunManagerPanel 多選 + bulk-delete + 確認 | Phase2 |
| 不變量 | EQUIV | bulk == 逐單 delete_run 等價 | §V |
| 不變量 | PARTIAL | 部分失敗報告不靜默不中斷 | §V |
| 不變量 | DOWNSTREAM | 下游(browse/checkpoint/quality)失效 | §V |
| 風險 | (b)(c) | 多下游刪除+部分失敗並發 | §RISK |

- 合計：Task=3、不變量=3、風險=1。

## §0 全域規則
- **逐 run 原子**:reuse 既有 `delete_run`(per-run RunLease 鎖),不重寫刪除邏輯。
- **完整 per-run report**:成功/失敗/bytes 逐筆;**部分失敗不靜默、不中斷整批**(filesystem 無法真 rollback→best-effort+報,非全-or-nothing)。
- **失效下游**:成功刪的 run 移除 browse `_tasks`、標 checkpoint completed_items 參照失效、清 quality cache。
- **並發安全**:registry RunBusyError(刪除中)保護;同 run 並發冪等。
- **防誤刪**:前端刪除前確認對話(顯將刪清單+總 bytes);空選不可刪。
- **不改特徵值/不碰生成**;hermetic 測試(B5 教訓)。

## §B 批次
| Batch | Task | 依賴 | 規模 |
|---|---|---|---|
| B4a | 1.1 + 1.2 | 無 | 中-大(endpoint+逐run+report+下游失效) |
| B4b | 2.1 | B4a | 中(前端多選+確認) |
- Gate:B4a bulk==逐單等價+部分失敗報+下游失效+並發;B4b npm build+vitest+確認對話+不破單 deleteRun。

## Phase 1 — backend
### Task 1.1 — bulk endpoint + 逐 run + report
- SPEC ref：1.1　目標:POST bulk 收 runs[];逐 run reuse delete_run;aggregate {deleted,failed,total_bytes_freed};部分失敗 207/明報。
- 實作要點:新 endpoint(api/routes/feature_factory.py)+service bulk 方法 loop delete_run;收 DeleteResult per run;一失敗續刪;RunBusyError→標 busy/skip 報。
- 修改檔案:api/routes/feature_factory.py、feature_factory_service.py、api/models。
- 不可做:不中斷整批;不靜默吞失敗;不重寫刪除邏輯。
- 邊界:空清單 no-op;重複冪等;不存在→failed 非 500。
- 驗證:多 run deleted/failed 正確;一失敗其餘照刪;`pytest tests/api/ -k bulk_delete`。
### Task 1.2 — 下游失效
- SPEC ref：1.2　目標:成功刪 run 移除 browse `_tasks`/標 checkpoint 參照失效/清 quality cache。
- 實作要點:沿用 delete_run 既有 _tasks 清理延伸;checkpoint completed_items 對應 browse_task_id 標失效。
- 修改檔案:feature_factory_service.py、batch_service.py。
- 不可做:不破既有 _tasks 清理。
- 邊界:無 checkpoint 參照跳過;quality cache 無項 no-op。
- 驗證:刪後 browse 查不到+checkpoint 參照失效+quality 清;`pytest tests/api/ -k bulk_delete_downstream`。

## Phase 2 — frontend
### Task 2.1 — RunManagerPanel 多選+確認
- SPEC ref：2.1　目標:per-run checkbox+全選+bulk 按鈕+確認對話(顯N個+總bytes)+per-run 結果。
- 實作要點:selected Set<runKey>;確認 dialog;呼 bulk endpoint;deleted 移出/failed 顯錯;不破單 deleteRun。
- 修改檔案:frontend RunManagerPanel.tsx、store(bulkDeleteRuns)、types.ts。
- 不可做:無確認直接刪;不破單 deleteRun(B3 retention)。
- 邊界:未選不可刪;刪除中 disable。
- 驗證:`npm run build`+**vitest 3 案例**(多選刪呼對endpoint/部分失敗顯錯/確認對話顯清單);`pytest tests/api/ -k bulk` 全綠。

### Phase 測試 + Gate
- bulk==逐單等價+部分失敗報+下游失效+並發 RunBusyError+前端確認。
- 單 deleteRun(B3 retention discard)不破。hermetic(data_cache diff 空)。

## 階段 4：Frozen 前 handoff
`SPEC=docs/B4_BULK_DELETE_SPEC.md TODO=docs/B4_BULK_DELETE_TODO.md FOCUS=逐run原子reuse delete_run/完整report不靜默/下游失效/並發RunBusyError/防誤刪確認/hermetic`
→ **雙家族 adversarial(大,(b)(c),Codex+Composer)** reconcile → Composer 實作(Phase1→2) + Codex review。
