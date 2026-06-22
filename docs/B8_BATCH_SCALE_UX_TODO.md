# B8 批次規模化 UX (A 批次保留批量 + B 刪除整批) TODO
> 版本：DRAFT｜基於 SPEC：docs/B8_BATCH_SCALE_UX_SPEC.md｜日期：2026-06-22

## 階段 1：SPEC ID 覆蓋
| 類別 | ID | 節錄 | 落點 |
|---|---|---|---|
| Task | 1.1 | bulk retention decision endpoint(loop per-item) | Phase1 |
| Task | 2.1 | BatchRetentionPanel 全部保留+多選丟棄 | Phase2 |
| Task | 2.2 | RunManager 刪除整批(reuse bulkDeleteRuns) | Phase2 |
| 不變量 | RETAINEQ | 全部保留==逐個 retain | §V |
| 不變量 | DELBATCHEQ | 刪除整批==選該batch bulk-delete+active排除 | §V |
| 不變量 | NOBREAK | 不破單項/單刪/批次刪除/重命名整批 | §V |
| 風險 | (b) | retention FSM+刪除(重用reviewed) | §RISK |
- 合計：Task=3、不變量=3、風險=1。
- **Codex adversarial reconcile**:#1 刪除整批用獨立 `bulkDeleteTarget`(mode selection|batch)不污染 selectedKeys(測先勾A再刪B只刪B);#2 bulk retention terminal 語意:same→succeeded/**opposite→failed+conflict(非skipped)**/無pending→skipped(+bulk×single並發測);#3 store **real store+mock fetch**(非mock store,B4c教訓);#4 凍結 `BatchRetentionBulkResponse{results:[{id,status,state,error?,code?}]}`+HTTP200 per-item。詳 SPEC。

## §0 全域規則
- **A reuse `apply_retention_decision`**(per-item lock/FSM/冪等),loop 成 bulk,不重寫。
- **全部保留=一鍵**(所有 pending→retain,no-op 清 mark,無需確認);**多選/全部丟棄=確認對話**(會刪檔)。
- **B reuse `bulkDeleteRuns`**(B4 reviewed,含 active 排除+確認+report);刪除整批=group.runs 過濾 active→呼它。
- **不破既有**:單項 retain/discard、單 deleteRun、批次刪除(全選)、重命名整批。
- **store 真測**(mock fetch 非 mock store,B4c 教訓);**確認防誤刪+active 排除**;不改數值。

## §B 批次
| Batch | Task | 依賴 | 規模 |
|---|---|---|---|
| B8a | 1.1 | 無 | 中(bulk retention endpoint loop per-item) |
| B8b | 2.1 | B8a | 中(面板全部保留+多選丟棄+store真測) |
| B8c | 2.2 | 無(reuse B4) | 小(刪除整批前端) |
- Gate:B8a bulk retain==逐個;B8b 全部保留清空+丟棄確認+store真測;B8c 刪除整批==batch bulk-delete+active排除+不破既有。

## Phase 1
### Task 1.1 — bulk retention endpoint
- SPEC ref：1.1　目標:POST /batch/{id}/retention/bulk {decision,runs[]};loop apply_retention_decision;aggregate {succeeded,failed,skipped};200。
- 實作要點:loop reuse apply_retention_decision(per-item lock/FSM 不變);一失敗續做;already-terminal→skipped。
- 修改檔案:api/routes/feature_factory.py、feature_factory_batch_service.py、api/models。
- 不可做:不重寫 FSM;不靜默。
- 邊界:空 no-op;重複冪等;already-terminal→skipped。
- 驗證:bulk retain N==逐個;bulk discard 真刪+browse不見;一失敗其餘照做;`pytest tests/api/ -k bulk_retention`。

## Phase 2
### Task 2.1 — BatchRetentionPanel 全部保留+多選丟棄
- SPEC ref：2.1　目標:「全部保留」一鍵(所有pending→retain)+checkbox+全選+「丟棄選取」(+全部丟棄)確認;呼 Phase1。
- 實作要點:selectedKeys Set;全部保留=送所有pending retain(無確認);丟棄=送selected discard(確認對話);per-item 既有按鈕保留;store bulkRetentionDecision。
- 修改檔案:frontend BatchRetentionPanel.tsx、store、types.ts。
- 不可做:不破既有逐項按鈕;丟棄無確認直接刪。
- 邊界:無pending不顯;deciding disable。
- 驗證:`npm run build`+**vitest 4案例**(全部保留呼對+清空/多選丟棄確認+呼對/全選/確認對話);**store 真測(mock fetch)** bulk endpoint+body。
### Task 2.2 — RunManager 刪除整批
- SPEC ref：2.2　目標:batch header 加「刪除整批」(平行重命名整批);group.runs 過濾 !active→確認對話→reuse bulkDeleteRuns。
- 實作要點:reuse bulkDeleteRuns+確認對話(B4模式);刪後 fetchRuns。
- 修改檔案:frontend RunManagerPanel.tsx。
- 不可做:不破單deleteRun/批次刪除(全選)/重命名整批;無確認不刪。
- 邊界:批內全active→無可刪+提示。
- 驗證:`npm run build`+**vitest 2案例**(刪除整批送該batch runs+active排除/確認顯清單);不破既有。

### Phase 測試 + Gate
- 全部保留==逐個retain+丟棄選取真刪+刪除整批==batch bulk-delete+active排除+不破既有。
- store 真測;hermetic(整合測 data_cache diff空)。

## 階段 4：Frozen 前 handoff
`SPEC=docs/B8_BATCH_SCALE_UX_SPEC.md TODO=docs/B8_BATCH_SCALE_UX_TODO.md FOCUS=全部保留==逐個retain/刪除整批==bulk-delete/active排除/不破既有/store真測/reuse reviewed`
→ 一家 adversarial(Codex,中;重用 reviewed 模式)reconcile → Composer 實作(Phase1→2) + Codex review。
