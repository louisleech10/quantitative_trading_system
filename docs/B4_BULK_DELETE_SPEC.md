# B4 — 批次刪除 + 孤兒清理 (Q2-B) — SPEC v2（選項1 + 防累積安全網）

> 來源：handoffs/20260619-ffconsist-FINAL.md(Q2-B) + 雙家族 adversarial(handoffs/20260622-b4-adv-*) + 使用者 2026-06-22 選「選項1(批量)+防累積安全網(partial報+孤兒清理)」。日期：2026-06-22｜對應 TODO：docs/B4_BULK_DELETE_TODO.md
>
> **v2 scope**：① 批量刪除(多選 reuse delete_run + 確認 + 完整 report);② **孤兒清理安全網**(掃描 registry↔artifact 不一致 → 清,防 partial-delete 錯誤累積)。**不做 Option 2 全硬化**(實證:正常刪除已清整個 run 目錄、不留磁碟垃圾;真風險僅罕見 partial-delete error)。

## §RISK 風險分級
- **大小**：**大**(跨棧 + 多下游 + B3 並發)。**命中 (b)** 共用刪除路徑 + **(c)** partial-delete/並發。**不命中 (d)**——刪除管理不碰特徵值。
- → §G 數值 N/A;以「bulk==逐單 delete_run 等價 + partial 報告 + 孤兒掃清 + B3 並發安全 + 防誤刪」驗證。

## §A 假設與待使用者確認（v2 實證修正）
- **已驗證事實**(grep/Read/實機,附行號):
  - **正常刪除不留磁碟垃圾**(實機確認):`data_quality.json`/`feature_stats_cache_parts`/`feature_catalog_cache`/`manifest`/`raw/` **全在 run 目錄內**(features_root/symbol/tf/config_hash/);`delete_run`→`_delete_run_locked` 刪**整個** feature_leaf(run_lifecycle.py:90 `_delete_leaf`)→ 連同清掉。委員會「漏清 quality/stats」誤判(那些在 run 目錄內)。
  - `delete_run`(run_lifecycle.py:70)per-run RunLease 鎖;**僅 `not result.errors` 才 `registry.remove`**(:114)→ **partial 失敗(如 cgsa error)會留 registry entry + 半缺 artifact = 孤兒**(這是真累積風險,罕見)。
  - registry 有 `deleting` flag 但**只 alias 守衛/auto_cleanup 用**(set_alias:157/set_batch_alias:190);`delete_run` 不 mark_deleting;`get`(:139)不檢查 → 刪檔窗口內 reader 仍見 entry。**且 `mark_deleting`(:217-225)對有 alias/batch_alias 的 run `return False`**(auto-cleanup 保護命名 run 語義)→ **使用者明確 bulk 刪命名 run 會被拒**(v2.1 BLOCKING,需 delete-path force helper)。
  - **delete_run 刪 features leaf + 獨立 `cgsa_work_dir`(run_paths.py:34)**;partial error 可留 features/registry/cgsa 任一不一致 → **孤兒掃描須涵蓋 features+CGSA 兩 leaf**(v2.1 BLOCKING,只掃 features 會漏 CGSA 孤兒累積大檔)。
  - `registry.list_all`(:120)+ `features_run_dir`(run_paths.py:26)+ `cgsa_work_dir`(:34)→ 掃孤兒;`auto_cleanup(keep_latest=5)`(:132)既有。
  - B3 retention discard **也 reuse delete_run**(batch_service.py:1785)→ bulk 與 discard 同 run 並發需協調(RunBusyError + retention FSM)。
  - 前端 RunManagerPanel(deleteRun:293)無多選;有 batch 分組 + active 徽章。
  - **記憶體快取**(_df/_stats/_adf cache)+ 前端狀態(selectedRunKey/explorer*)= 重啟/重整即清,**非磁碟累積**(proportionate 處理,非全 matrix)。
  - d_star cache 按 symbol/tf/fracdiff fingerprint **跨 run 共享 → 不可刪**(§N 登記)。
- **待確認**：無。**已確認**(2026-06-22 使用者選 選項1+安全網)。

## §C 約束
- 解耦:reuse delete_run;新 endpoint api/routes;不重寫刪除邏輯;不新增跨域依賴。
- **不可違反**:① **per-run lease + best-effort**(reuse delete_run;非全-or-無,filesystem 無法真 rollback;`DeleteResult.errors`→report 的 `failed` 非 skipped);② **完整 per-run report**(deleted/failed/skipped+bytes,**partial 不靜默不中斷**);③ **delete-path mark-deleting(force named)**:統一 lifecycle delete orchestration `lease→mark_deleting(allow_named/force)→delete→remove or 失敗 clear`,**新 helper 允許刪 alias/batch_alias run**(既有 mark_deleting 拒命名,explicit delete 須 override);reader(public get/list)期間隱藏 deleting,**孤兒 scan(internal)看得到 deleting/partial**;單刪+bulk+retention discard **共用此 orchestration**;④ **孤兒清理(含 CGSA)**:掃 registry ↔ **features leaf + cgsa_work_dir** 不一致(registry 有/leaf 無、leaf 有/registry 無,以 manifest config_hash ownership 驗)→ report + 清;**active(lease held)run 不算孤兒**(dir 有 registry 無的生成中不可清);⑤ **B3 FSM reconcile**:bulk 刪 B3 pending-retention run → **route 編排呼 batch_service 標 retention_items DISCARDED**(或 RunBusyError 擋+報);bulk 後前端 `fetchBatchRetentionPending` 刷新;同 run 冪等;⑥ **防誤刪**:確認對話顯 symbol/tf/alias/full-hash/bytes/batch,**active run 禁選**,payload 去重;⑦ **HTTP 200 + per-run status**(避免 207);⑧ **不清 d_star**(共享);不改特徵值。
- 注意:checkpoint completed_items 邏輯失效(resume/quality builders 過濾)= **明確 OUT OF SCOPE**(孤兒網兜底磁碟;完整 checkpoint schema 失效留未來);記憶體/前端 stale 重啟/重整清。
- 注意:記憶體/前端 stale 為次要(重啟/重整清),不納本批 disk-garbage 範圍。

## §G Golden / Baseline
- N/A(移 §N)。bulk-delete/孤兒清理不碰生成;golden 不受影響。

## §P Phase 與依賴

### Phase 1 — backend bulk + mark-deleting + report(依賴:無)
**Task 1.1 — bulk-delete endpoint + mark-deleting + aggregate report**
- 目標:POST 收 `runs:[{symbol,timeframe,config_hash}]`;逐 run:設 `deleting` flag→reuse delete_run→remove/clear flag;aggregate `{deleted:[{run,bytes}], failed:[{run,error}], skipped:[]}`;**HTTP 200 + per-run status**(全空→no-op)。
- 檔案:api/routes/feature_factory.py(新 endpoint)+ feature_factory_service.py(bulk 方法)+ run_lifecycle/registry(mark_deleting)+ api/models。
- 改法:loop;**delete-path mark helper(force named,可刪 alias/batch run)**;一失敗續刪;RunBusyError→skipped 報;public reader 隱藏 deleting;**命中 B3 pending-retention → route 呼 batch_service 標 retention_items DISCARDED**(或 RunBusyError 擋)。
- 驗證:多 run deleted/failed;一失敗其餘照刪;**alias/batch_alias run 能刪**;mark-deleting 期間 list 隱藏;**bulk 刪 B3 pending run→retention FSM 標 DISCARDED**;`pytest tests/api/ -k "bulk_delete or B3CONC"`。
- 邊界:空 no-op;重複冪等;不存在→failed;active(lease held)→拒+報。不可做:不中斷整批;不靜默;不漏 named run。

### Phase 2 — 孤兒清理安全網(依賴:無)
**Task 2.1 — 孤兒掃描 + 清理 endpoint**
- 目標:掃 `registry.list_all` vs **`features_run_dir` + `cgsa_work_dir`** → 孤兒:(a)registry 有但 leaf 無、(b)leaf(features 或 CGSA)有但 registry 無(以 manifest config_hash ownership 驗);report;清(a→registry.remove、b→刪 leaf);冪等。
- 檔案:feature_factory_service.py + run_lifecycle.py(orphan scan/clean,**features+CGSA**)+ api/routes + api/models。
- 改法:dry-run(只報)+ confirm clean;清走 per-run lease;**active(lease held)/deleting 中的 dir 不算孤兒**(內部 scan 看得到 deleting 但不誤清生成中)。
- 驗證:製造孤兒(刪 features leaf 留 registry / 留 features dir 刪 registry / **CGSA-only 孤兒**)→掃出+清;active 不誤清;`pytest tests/api/ -k orphan_cleanup`。
- 邊界:無孤兒→空報;active/deleting 不算孤兒;清理失敗報非靜默。

### Phase 3 — 前端多選 + 確認 + 孤兒按鈕(依賴:Phase 1/2)
**Task 3.1 — RunManagerPanel 多選 + bulk + 確認 + 孤兒清理**
- 目標:per-run checkbox + 全選 + bulk 按鈕 + **確認對話**(顯 symbol/tf/alias/full-hash/bytes/batch,active 禁選)+ per-run 結果;**孤兒清理按鈕**(掃描→顯孤兒→確認清)。
- 檔案:frontend RunManagerPanel.tsx、store(bulkDeleteRuns/scanOrphans/cleanOrphans)、types.ts。
- 改法:selected Set;確認 dialog;呼 Phase1/2 endpoint;deleted 移出、failed 顯錯;不破單 deleteRun(B3 retention)。
- 驗證:`cd frontend && npm run build` + **vitest 4 案例**(多選刪呼對 endpoint/部分失敗顯錯/確認顯清單+active禁選/孤兒掃清);多選 UI。
- 邊界:未選不可刪;刪除中 disable;單 deleteRun 仍可用。不可做:無確認直接刪。

## §V 驗證策略與邊界測試目錄
- 測試層級:單元(bulk loop/report/孤兒掃描)/整合(真實多 run 刪+孤兒)/前端(vitest)/並發。
- **防假綠**:不放寬既有測試;bulk==逐單 delete_run 等價真比對;孤兒真製造真清;B3 並發真測。
- **核心不變量(可證偽)**:
  ① **bulk==逐單等價**:bulk 刪 N run == 逐個 delete_run(artifact/registry 同消失);`-k bulk_delete_equiv`。
  ② **partial 報告**:N 中 1 失敗(mock delete_run raise)→其餘照刪 + failed 明列(不靜默/不中斷)。
  ③ **mark-deleting**:刪檔窗口內 list/get 隱藏該 run;完成 remove/失敗 clear flag。
  ④ **孤兒掃清**:製造兩類孤兒→掃出+清掉;無孤兒空報。
  ⑤ **B3 並發 + FSM reconcile**:bulk 刪 B3 pending-retention run→**retention_items 標 DISCARDED**(route→batch_service)或 RunBusyError 擋;bulk 後前端 fetchBatchRetentionPending 刷新;同 run bulk+single+discard 並發冪等無雙刪 race;`-k B3CONC`。
  ⑥ **named run 可刪**:alias/batch_alias run 經 bulk(force mark)能刪(既有 mark_deleting 拒,delete-path 須 override)。
  ⑦ **CGSA 孤兒**:CGSA-only 孤兒掃出+清(防大檔累積)。
  ⑥ **防誤刪**:確認對話顯 alias/full-hash/bytes;active 禁選;空選不可刪。
  ⑦ **HTTP 200+per-run status**(非 207)。
- **行為不變**:單 deleteRun(B3 retention discard)正常;不清 d_star;golden 不受影響。
- **邊界目錄**:空清單/重複冪等/不存在→failed/active 禁選/partial 續刪/B3 並發/孤兒兩類/HTTP per-run status/hermetic(tmp data_cache_path+FFACT_CGSA_WORK_DIR,跑前後 diff 空)。

## §R 回退
- 新 endpoint + 前端,獨立 revert。reuse delete_run(無新刪除邏輯)。孤兒清理 dry-run 先報再清。確認對話防誤刪。每 Phase 獨立 commit。

## §N N/A 登記
- §G Golden:**N/A — 刪除/清理管理,不碰特徵值/生成**;改以 bulk==逐單等價 + partial report + mark-deleting + 孤兒掃清 + B3 並發安全 + 防誤刪 驗證。
- **不清 d_star cache**:d_star 按 symbol/tf/fracdiff fingerprint **跨 run 共享**,刪單 run 不應清(否則破跨 run reuse);本批明確**不碰 d_star**。
- 記憶體快取/前端 stale:重啟/重整即清,**非磁碟累積**,不納本批 disk-garbage 安全網範圍。
