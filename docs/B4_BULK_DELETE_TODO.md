# B4 批次刪除 + 孤兒清理 (Q2-B) TODO v2
> 版本：v2(選項1+防累積安全網,雙家族 adversarial reconcile)｜基於 SPEC：docs/B4_BULK_DELETE_SPEC.md｜日期：2026-06-22

## 階段 1：SPEC ID 覆蓋
| 類別 | ID | 節錄 | 落點 |
|---|---|---|---|
| Task | 1.1 | bulk-delete endpoint + mark-deleting + report | Phase1 |
| Task | 2.1 | 孤兒掃描 + 清理 endpoint | Phase2 |
| Task | 3.1 | RunManagerPanel 多選 + 確認 + 孤兒按鈕 | Phase3 |
| 不變量 | EQUIV | bulk == 逐單 delete_run 等價 | §V |
| 不變量 | PARTIAL | partial 失敗報告不靜默不中斷 | §V |
| 不變量 | ORPHAN | 孤兒掃出+清掉(防累積) | §V |
| 不變量 | B3CONC | bulk vs B3 retention discard 並發安全 | §V |
| 風險 | (b)(c) | 共用刪除+partial+並發 | §RISK |
- 合計：Task=3、不變量=4、風險=1。

## §0 全域規則
- **逐 run 原子**:reuse 既有 `delete_run`(per-run RunLease),不重寫刪除邏輯。
- **完整 per-run report**:deleted/failed/skipped+bytes;partial **不靜默不中斷**。HTTP **200+per-run status**(非 207,避免與單刪 500 分裂)。
- **mark-deleting**:delete 路徑開始設 registry `deleting` flag(用既有欄),reader(list/get)期間隱藏/標,完成 remove 或失敗 clear。
- **孤兒清理(安全網)**:掃 registry↔artifact 不一致(registry 有/dir 無、dir 有/registry 無)→ dry-run 報 → 清,防 partial-delete error 累積。
- **B3 並發**:bulk 刪 B3 pending-retention run → 更新 retention FSM 或 RunBusyError 擋+報;同 run 冪等。
- **防誤刪**:確認對話顯 symbol/tf/alias/full-hash/bytes/batch,active 禁選,payload 去重。
- **不清 d_star**(共享 fingerprint);記憶體/前端 stale 非本批(重啟/重整清);正常刪除已清整 run 目錄(實證,不留磁碟垃圾)。
- 不改特徵值;hermetic 測試(tmp+FFACT_CGSA_WORK_DIR)。

## §B 批次
| Batch | Task | 依賴 | 規模 |
|---|---|---|---|
| B4a | 1.1 | 無 | 中-大(bulk+mark-deleting+report+B3並發) |
| B4b | 2.1 | 無 | 中(孤兒掃描+清理) |
| B4c | 3.1 | B4a+B4b | 中(前端多選+確認+孤兒按鈕) |
- Gate:B4a bulk==逐單+partial報+mark-deleting+B3並發;B4b 孤兒兩類掃清;B4c npm build+vitest+確認active禁選+不破單deleteRun。

## Phase 1
### Task 1.1 — bulk endpoint + mark-deleting + report
- SPEC ref：1.1　目標:POST runs[];逐 run 設deleting→delete_run→remove/clear;aggregate report;200+per-run status。
- 實作要點:loop reuse delete_run;mark_deleting(registry 既有欄,reader 隱藏);一失敗續刪;RunBusyError→skipped;active run→拒+報。
- 修改檔案:api/routes/feature_factory.py、feature_factory_service.py、run_lifecycle.py/registry(mark_deleting+get/list filter)、api/models。
- 不可做:不中斷整批;不靜默;不重寫刪除;不清 d_star。
- 邊界:空 no-op;重複冪等;不存在→failed;active 拒。
- 驗證:多 run deleted/failed;一失敗其餘照刪;mark-deleting 期間 list 隱藏;`pytest tests/api/ -k bulk_delete`。

## Phase 2
### Task 2.1 — 孤兒掃描 + 清理
- SPEC ref：2.1　目標:掃 list_all vs features_run_dir → 兩類孤兒;dry-run 報+清(a→registry.remove、b→刪dir);冪等。
- 實作要點:feature_factory_service+run_lifecycle orphan scan/clean;清走 per-run lease;dry-run 預設。
- 修改檔案:feature_factory_service.py、run_lifecycle.py、api/routes、api/models。
- 不可做:active run 不算孤兒;清理失敗不靜默。
- 邊界:無孤兒空報;清理失敗報。
- 驗證:製造兩類孤兒(刪dir留registry/留dir刪registry)→掃出+清;`pytest tests/api/ -k orphan_cleanup`。

## Phase 3
### Task 3.1 — 前端多選+確認+孤兒按鈕
- SPEC ref：3.1　目標:checkbox+全選+bulk按鈕+確認對話(alias/full-hash/bytes/batch,active禁選)+per-run結果+孤兒清理按鈕(掃→顯→清)。
- 實作要點:selected Set;確認 dialog;呼 Phase1/2;deleted移出/failed顯錯;不破單deleteRun。
- 修改檔案:frontend RunManagerPanel.tsx、store(bulkDeleteRuns/scanOrphans/cleanOrphans)、types.ts。
- 不可做:無確認直接刪;不破單deleteRun(B3 retention)。
- 邊界:未選不可刪;刪除中disable;active禁選。
- 驗證:`npm run build`+**vitest 4案例**(多選刪呼對endpoint/部分失敗顯錯/確認顯清單+active禁選/孤兒掃清);`pytest tests/api/ -k "bulk or orphan"` 綠。

### Phase 測試 + Gate
- bulk==逐單+partial報+mark-deleting+孤兒掃清+B3並發+防誤刪+HTTP per-run status。
- 單 deleteRun(B3)不破;hermetic(data_cache diff空);不清 d_star。

## 階段 4：Frozen 前 handoff
`SPEC=docs/B4_BULK_DELETE_SPEC.md TODO=docs/B4_BULK_DELETE_TODO.md FOCUS=bulk==逐單/partial報/mark-deleting/孤兒掃清/B3並發/防誤刪/不清d_star/hermetic`
→ **雙家族確認 v2(大,Codex+Composer)** reconcile → Composer 實作(Phase1→3) + Codex review。
