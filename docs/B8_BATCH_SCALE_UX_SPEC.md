# B8 — 批次規模化 UX (A 批次保留批量 + B 刪除整批) — SPEC

> 來源：使用者 2026-06-22 實測 B3/B4 後反映「100 symbol 要按 100 次」。日期：2026-06-22｜對應 TODO：docs/B8_BATCH_SCALE_UX_TODO.md
>
> **A**：BatchRetentionPanel 加「全部保留」一鍵 + 多選丟棄(100 symbol=1 點)。**B**：RunManager 加「刪除整批」(平行於「重命名整批」,一鍵刪某 batch_id 全部 run)。**兩者重用既有 reviewed 模式**(A reuse `apply_retention_decision`、B reuse `bulkDeleteRuns`)。

## §RISK 風險分級
- **大小**：中。**命中 (b)** retention FSM + 刪除路徑(但**重用已 reviewed 的 per-item decision(B3)與 bulk-delete(B4)**,非新邏輯)。**不命中 (d)**。
- → §G N/A;以「全部保留==逐個 retain 等價 + 丟棄選取 + 刪除整批==選該 batch bulk-delete + active 排除 + 不破單操作」驗證。

## §A 假設與待使用者確認
- **已驗證事實**(grep,附行號):
  - A:`apply_retention_decision`(feature_factory_batch_service.py:1741,per-item,有 lock/CAS/冪等)可 **loop 成 bulk**;前端 `BatchRetentionPanel` handleDecision(:48)逐項、`visiblePending.map`(:95)無全選/批量。
  - B:store `bulkDeleteRuns`(RunManagerPanel.tsx:219/339,B4 已 reviewed,含 active 排除+確認+report)**可直接重用**;batch group 有 `group.runs`(:656)+「重命名整批」(:647-652),**無「刪除整批」**。
- **待確認**：無。**已確認**(2026-06-22 使用者:A=全部保留+多選丟棄、B=刪除整批,UX 已定)。

## §C 約束
- 解耦:A 後端 reuse apply_retention_decision;B 前端 reuse bulkDeleteRuns;不重寫 decision/delete 邏輯。
- **不可違反**:① A bulk retention = **loop 既有 per-item apply_retention_decision**(保 lock/FSM/冪等),aggregate report(成功/失敗逐筆);② 「全部保留」一鍵 = 對所有 pending retain(no-op 清 mark,無需確認);③ 「多選丟棄」/「全部丟棄」**需確認對話**(會刪檔);④ B 「刪除整批」= 取該 batch `group.runs` **過濾 active** → reuse `bulkDeleteRuns` + **確認對話**(B4 一致,active 排除);⑤ 不破既有單項 retain/discard、單 deleteRun、批次刪除(全選)、重命名整批;⑥ 不改數值/不碰生成。
- 注意:retain 不設命名→不阻 auto_cleanup(永久保留需命名,既有行為,UI 文案可提示)。

## §G Golden / Baseline
- N/A(移 §N)。純 UX/批量,不碰生成;golden 不受影響。

## §P Phase 與依賴

### Phase 1 — A:後端 bulk retention(依賴:無)
**Task 1.1 — bulk retention decision endpoint**
- 目標:`POST /batch/{id}/retention/bulk` body `{decision:'retain'|'discard', runs:[{symbol,timeframe,config_hash}]}`;loop `apply_retention_decision`;aggregate `{succeeded:[], failed:[{run,error}], skipped:[]}`;HTTP 200。
- 檔案:api/routes/feature_factory.py(新 endpoint)+ feature_factory_batch_service.py(bulk 方法 loop per-item)+ api/models。
- 改法:loop reuse apply_retention_decision(per-item lock/FSM 不變);一失敗續做;already-terminal→skipped。
- 驗證:bulk retain N==逐個 retain;bulk discard 真刪+browse 不見;一失敗其餘照做;`pytest tests/api/ -k bulk_retention`。
- 邊界:空 no-op;重複冪等;already terminal→skipped。不可做:不重寫 FSM。

### Phase 2 — A 前端面板 + B 刪除整批(依賴:Phase 1)
**Task 2.1 — BatchRetentionPanel 全部保留 + 多選丟棄**
- 目標:面板加「全部保留」按鈕(所有 pending→retain bulk,一鍵)+ per-item checkbox + 全選 + 「丟棄選取」(+「全部丟棄」)按鈕,丟棄走確認對話;呼 Phase1 endpoint。
- 檔案:frontend BatchRetentionPanel.tsx、store(bulkRetentionDecision)、types.ts。
- 改法:selectedKeys Set;全部保留=送所有 pending retain;丟棄選取=送 selected discard(確認);per-item 既有按鈕保留;狀態用 B2 normalize/`key in payload`。
- 驗證:`npm run build` + **vitest 4 案例**(全部保留呼對 endpoint+清空 pending/多選丟棄確認+呼對/全選/丟棄確認對話);store 真測(mock fetch)bulk endpoint+body。
- 邊界:無 pending 不顯;deciding 中 disable;不破既有逐項按鈕。
**Task 2.2 — RunManager 刪除整批**
- 目標:batch group header 加「刪除整批」按鈕(平行「重命名整批」);取 `group.runs` 過濾 `!active` → 確認對話(顯該批 runs/active 排除/bytes)→ reuse `bulkDeleteRuns`。
- 檔案:frontend RunManagerPanel.tsx。
- 改法:reuse 既有 bulkDeleteRuns + 確認對話模式(B4);刪後 fetchRuns 刷新。
- 驗證:`npm run build` + **vitest 2 案例**(刪除整批送該 batch runs+active 排除/確認對話顯清單);不破單 deleteRun/批次刪除(全選)/重命名整批。
- 邊界:批內全 active→無可刪+提示;確認才刪。

## §V 驗證策略與邊界測試目錄
- 測試層級:單元(bulk retention loop)/整合(真實)/前端(vitest+store 真測)。
- **防假綠**:store 真測 mock fetch 非 mock store(B4c 教訓);bulk retention 真碰 FSM;不放寬既有。
- **核心不變量(可證偽)**:
  ① **全部保留==逐個 retain**:bulk retain 所有 pending == 逐個 apply_retention_decision retain(FSM 同 RETAINED、pending 清空)。
  ② **多選丟棄**:selected discard 真刪該 run(Path.exists False)+browse 不見;未選不動。
  ③ **刪除整批==選該 batch bulk-delete**:刪除整批 == 手動勾該 batch 全部 run 批次刪除(reuse bulkDeleteRuns,結果等價);**active 排除**。
  ④ **不破既有**:單項 retain/discard、單 deleteRun、批次刪除(全選)、重命名整批 全正常。
  ⑤ **確認防誤刪**:丟棄/刪除整批前確認對話;active 排除。
- **行為不變**:不碰生成;golden 不受影響。
- **邊界目錄**:空 pending/無可刪 active/重複冪等/already-terminal skipped/確認對話/hermetic(整合測 tmp data_cache_path+FFACT_CGSA_WORK_DIR,跑前後 diff 空)。

## §R 回退
- A 新 endpoint + 前端按鈕、B 純前端,獨立 revert。reuse apply_retention_decision/bulkDeleteRuns(無新核心邏輯)。確認對話防誤刪。每 Phase 獨立 commit。

## §N N/A 登記
- §G Golden:**N/A — 批量 UX 不碰特徵值/生成**;改以 全部保留==逐個 retain + 丟棄選取真刪 + 刪除整批==batch bulk-delete + active 排除 + 不破既有 驗證。
