# B4 — 交易式批次刪除 (Q2-B) — SPEC

> 來源：handoffs/20260619-ffconsist-FINAL.md(Q2-B,P2.5,大)。日期：2026-06-22｜對應 TODO：docs/B4_BULK_DELETE_TODO.md
>
> **目標**：RunManager 多選 N 個 run → 一次交易式批次刪除;每 run 原子(reuse 既有 delete_run)+ 完整 per-run report(不靜默)+ 失效下游(browse task/checkpoint 參照/quality cache/磁碟)。B3 已備單 run delete;B4 做多選/批量/報告/下游失效。

## §RISK 風險分級
- **大小**：**大**。**命中 (b)** 共用刪除路徑多下游(registry/browse/checkpoint/quality) + **(c)** 部分失敗難回退/並發。**不命中 (d)**——刪除管理,不碰特徵值/計算正確性。
- → §G 數值 N/A;以「bulk == 逐個 delete_run 等價 + 完整 report + 下游失效 + 並發安全」驗證。**dry-run/確認** 防誤刪護欄。

## §A 假設與待使用者確認
- **已驗證事實**(grep/Read,附行號):
  - 單 run 刪除 `feature_factory_service.delete_run`→`RunLifecycleManager.delete_run`(run_lifecycle.py:70):**per-run RunLease 鎖**(:73)→`_delete_run_locked` 刪 features leaf+cgsa leaf+manifest→`registry.remove`(:114);回 `DeleteResult`(registry_removed/errors/total_bytes,:20-35)。
  - registry `get`(:139)在刪除中拋 `RunBusyError("Run is being deleted")`(:157/190)——**已有 in-flight 保護**(近似 tombstone);`remove`(:202)。
  - 下游參照:browse_task_id(checkpoint completed_items:333、register:705)、quality cache、磁碟。
  - 前端 **RunManagerPanel.tsx** 是 run 管理 UI(單 deleteRun:293);**無多選**(checkbox/selected 不存在)。
  - **無既有 FF bulk-delete**(僅 pattern_management 有 batch/delete-all,不相關)。
- **待確認**：無。**已確認**(委員會 FINAL Q2-B;B3 已備 delete_run 供 reuse)。

## §C 約束
- 解耦:reuse `delete_run`(不重寫刪除邏輯);新 endpoint 在 api/routes;不新增跨域依賴。
- **不可違反**:① **每 run 原子**(reuse 既有 per-run RunLease delete_run);② **完整 per-run report**(成功/失敗/bytes 逐筆,**部分失敗不靜默**;非全-or-nothing,filesystem 無法真 rollback→誠實 best-effort+報);③ **失效下游**(成功刪的 run:移除其 browse task、checkpoint completed_items 參照標失效、quality cache 清);④ **並發安全**(RunBusyError in-flight 保護;同 run 並發刪冪等);⑤ **防誤刪**(endpoint 需明確 run 清單;前端刪除需確認對話 + 顯示將刪清單/bytes);⑥ 不改特徵值/不碰生成。
- 注意:true ACID 跨 N filesystem 刪不可行→「交易式」定義=**逐 run 原子 + 完整報告 + 下游一致失效**,非全-or-nothing。

## §G Golden / Baseline
- N/A(移 §N)。bulk-delete 不碰特徵生成;`build_l65_golden_baseline.py --check` 不受影響(不在刪除路徑)。

## §P Phase 與依賴

### Phase 1 — backend bulk endpoint + 下游失效(依賴:無)
**Task 1.1 — bulk-delete endpoint + 逐 run + aggregate report**
- 目標:POST bulk-delete 收 `runs:[{symbol,timeframe,config_hash}]`;逐 run reuse `delete_run`(per-run 原子);aggregate `{deleted:[], failed:[{run,error}], total_bytes_freed}`;部分失敗回 207/明確報告。
- 檔案:api/routes/feature_factory.py(新 endpoint)+ api/services/feature_factory_service.py(bulk 方法)+ api/models。
- 改法:loop delete_run;收集 DeleteResult per run;不中斷(一個失敗續刪其餘);RunBusyError→該 run 標 busy/skip 報。
- 驗證:多 run 刪除 deleted/failed 正確;一個失敗其餘照刪;`pytest tests/api/ -k bulk_delete`。
- 邊界:空清單→no-op;重複 run 冪等;不存在 run→failed 報非 500。不可做:不中斷整批;不靜默吞失敗。
**Task 1.2 — 下游失效(browse/checkpoint/quality)**
- 目標:成功刪的 run 移除其 browse task(`_tasks`)、標 checkpoint completed_items 參照失效、清 quality cache。
- 檔案:feature_factory_service.py(沿用 delete_run 既有 _tasks 清理:延伸)+ batch_service(checkpoint 參照)。
- 驗證:刪後 browse 查不到、checkpoint 參照標失效、quality cache 清;`pytest tests/api/ -k bulk_delete_downstream`。
- 邊界:無 checkpoint 參照→跳過;quality cache 無項→no-op。

### Phase 2 — 前端多選 + 確認(依賴:Phase 1)
**Task 2.1 — RunManagerPanel 多選 + bulk-delete + 確認**
- 目標:RunManagerPanel 加 per-run checkbox + 全選 + bulk-delete 按鈕;**刪除前確認對話**(顯示將刪 N 個 run + 總 bytes);呼 Phase1 endpoint;顯示 per-run 結果。
- 檔案:frontend RunManagerPanel.tsx、store(bulkDeleteRuns)、types.ts。
- 改法:selected Set<runKey>;確認 dialog;呼 bulk endpoint;deleted 移出列表、failed 顯錯;不破單 deleteRun。
- 驗證:`cd frontend && npm run build` + **vitest 3 案例**(多選刪除呼對 endpoint、部分失敗顯錯、確認對話顯清單);多選 UI。
- 邊界:未選不可刪;刪除中 disable;單 deleteRun 仍可用。不可做:無確認直接刪。

## §V 驗證策略與邊界測試目錄
- 測試層級:單元(bulk loop/report)/整合(真實多 run 刪除+下游失效)/前端(vitest 多選+確認)/並發。
- **防假綠**:不放寬既有測試;新斷言 bulk==逐單 delete_run 等價 + 部分失敗真報 + 下游真失效(碰真實 browse/checkpoint)。
- **核心不變量(可證偽)**:
  ① **逐 run 原子等價**:bulk 刪 N run 結果 == 逐個 delete_run(artifact/registry 同消失);`-k bulk_delete_equiv`。
  ② **部分失敗報告**:N 中 1 失敗(mock delete_run raise)→其餘照刪 + failed 明列該 run(不靜默/不中斷)。
  ③ **下游失效**:刪後 browse `_tasks` 查不到、checkpoint completed_items 參照標失效、quality cache 清。
  ④ **並發安全**:同 run 並發 bulk+single delete→RunBusyError 保護,無雙刪 race。
  ⑤ **防誤刪**:前端刪除前確認對話顯將刪清單;空選不可刪。
- **行為不變**:bulk-delete 不碰生成;單 deleteRun(B3 retention discard)仍正常。
- **邊界目錄**:空清單 no-op/重複 run 冪等/不存在 run→failed 非 500/部分失敗續刪/並發 RunBusyError/前端確認+空選防護/hermetic(測試重導 tmp data_cache_path+FFACT_CGSA_WORK_DIR,跑前後 diff 空)。

## §R 回退
- 新 endpoint + 前端,獨立可 revert。reuse delete_run(無新刪除邏輯)降風險。dry-run/確認對話防誤刪。每 Phase 獨立 commit。

## §N N/A 登記
- §G Golden:**N/A — 刪除管理不碰特徵值/生成**;改以 bulk==逐單 delete_run 等價 + 部分失敗 report + 下游失效 + 並發 RunBusyError 安全 + 前端確認防誤刪 驗證。
