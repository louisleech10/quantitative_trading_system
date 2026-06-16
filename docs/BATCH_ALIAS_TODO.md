# 批次別名 Phase 1+2 — TODO V4（基於 SPEC V4｜2026-06-17）

> 追溯：manifest [BA-1]~[BA-10]；SPEC Task 1.1/1.2/2.1 共 3 Task。Codex 設計為本。

## §0 全域規則與約束
- **不覆寫 per-run `alias`**：batch_alias 為獨立 registry 欄；顯示優先序 `alias > batch_alias:{symbol} > symbol/tf/hash`。
- **auto-cleanup 保護擴大**：候選由 `not entry.get("alias")` → `not (alias or batch_alias)`（命名批次 run 不被清；只擴大保護不弱化）。
- registry key (symbol,tf,config_hash) 不變；唯一性:per-run alias 同 (s,tf) 唯一不變,batch_alias 以 batch_id 一致不參與 per-run alias 唯一檢查。
- 純 metadata：禁碰數值/CGSA/特徵計算/delete reconciliation；向後相容(舊 entry 無欄 .get 不炸)。
- 解耦:registry 邏輯 momentum、API api/、DTO api/models;前端經 store。
- 防假綠:不放寬既有 test_run_lifecycle_api / run_lifecycle vitest 斷言;回歸維持綠。
- 紀律:後端 pytest+前端 build/vitest;測試 tmp_path;**不負責 git commit**(協調者按 Phase 接手);BLOCKED 即停。

## §B 批次執行策略
| Batch | Task | 依賴 | 規模 |
|---|---|---|---|
| P1 | 1.1、1.2 | 無 | 中 |
| P2 | 2.1 | P1 | 中 |

- 每 Phase 記 handoffs/20260616-batch-alias-impl.md;總 Gate:後端 pytest 新檔+既有 test_run_lifecycle_api 綠 + 前端 build+vitest 綠 + grep `from api\.` momentum/=0。

## Phase 1 — 後端 [BA-1..5]
### Task 1.1 — registry batch_id/batch_alias + 寫入
- SPEC ref：Task 1.1。
- 實作要點：
  1. add overwrite 三態(r4):**同 batch_id 再生→保留 batch_alias;換 batch_id(!=)→overwrite+reset batch_alias;傳入 batch_id=None(單 run 再生同 key)→不 overwrite,merge-preserve 既有 batch_id/batch_alias**(r2-MAJOR#1 不偷剝批次歸屬)。
  2. 新 `set_batch_alias(batch_id, batch_alias) -> int`:registry transaction(_locked_mutate)更新所有該 batch_id entry 的 batch_alias(strip 空=清除),回 affected 數;**不動 per-run alias**;**任一 target deleting→raise RunBusyError 整筆 fail(對齊 set_alias, r2-MAJOR#2)**。
  3. **batch_id 顯式參數穿透(禁 self._current_batch_id mutable, r2-B1)+兩條路徑都穿(r3-B1)**:generate_features 加 batch_id→**①單 TF**:三 helper(`_layer7_raw_from_cgsa_pipeline`@367→`_layer7_validate_and_persist_cgsa`@3373、`_layer7_validate_and_persist`@400)加 batch_id 參數;**②multi-TF**:generate_features(@306)`generate_multi_tf(...,batch_id)` 加參數→multi_tf_generator.py 內 `self._factory._layer7_raw_from_cgsa_pipeline`(:309/:600)、`_layer7_validate_and_persist`(:1364)都傳 batch_id→registry.add 三處用區域參數;`_compute_single` 加 batch_id(ProcessPool),`_process_item_wave`/executor 由 checkpoint["batch_id"](非 task_id)傳入。單 run None。
- 修改檔案:feature_registry.py(add/set_batch_alias)、feature_factory.py(generate_features+三 helper 簽名+add 三處+傳 generate_multi_tf)、**timeframe/multi_tf_generator.py(generate_multi_tf 簽名+三 _layer7 呼叫傳 batch_id)**、feature_factory_batch_service.py(_compute_single+傳 batch_id)。
- 不可做:禁覆寫 alias;禁改 add upsert key;禁動 set_alias 唯一性;**禁用 self mutable batch_id state**。
- 邊界:batch_id None(merge-preserve);具體 batch_id overwrite;舊 entry 無欄;batch_alias 空清除;deleting→RunBusyError;**multi-TF 路徑也寫 batch_id**。
- 驗證:`pytest tests/api/test_batch_alias.py -k registry -q`——批次 add 後 entries 有 batch_id;**multi-TF 生成路徑同樣寫 batch_id(r3-B1 不可只測單 TF)**;同 batch_id 再生保留 batch_alias;換 batch_id overwrite+reset;batch_id=None 再生 merge-preserve;set_batch_alias 更新整批且 per-run alias 不變;**deleting target→RunBusyError 無 entry 更新**;**per-run alias 跨 batch_id reset 保留(組合測試 r2-MAJOR#3)**;affected 數正確;舊 entry load 不炸。

### Task 1.2 — PATCH 端點 + auto-cleanup 保護 + RunInfo
- SPEC ref：Task 1.2。
- 實作要點：
  1. `api/models` BatchAliasRequest{batch_alias:Optional[str]};`api/routes/feature_factory.py` `PATCH /api/v1/features/batch/{batch_id}/alias`→service.set_batch_alias;**batch_id 無對應 entry→404 `batch_not_found`(定死,非 affected-0)**;**RunBusyError→409(deleting target, r2-MAJOR#2)**。
  2. RunInfo + list_runs 加 batch_id/batch_alias(從 registry entry)。
  3. **候選 filter + mark_deleting() transaction 都改 `not (alias or batch_alias)`**(Codex r1-B2 race);PATCH batch_id 查無→404 batch_not_found 定死。
- 修改檔案:api/models、api/routes/feature_factory.py、feature_factory_service.py(set_batch_alias service+list_runs 欄)、run_lifecycle.py(候選)。
- 不可做:禁改 max_nan/數值;禁動 delete reconciliation;禁弱化既有 cleanup「命名不清」。
- 邊界:batch_id 查無→404;deleting target→409 RunBusyError;batch_alias 空清除後該 run 無 alias 則回 cleanup 候選。
- 驗證:`-k "api or cleanup" -q`——PATCH 更新整批回 affected;404 batch_not_found;deleting target→409 RunBusyError 無更新;list_runs RunInfo 含 batch_id/batch_alias;**auto_cleanup 不清 batch_alias run**(tmp:5 未命名+1 batch_alias,keep_latest=0→batch_alias run 倖存,未命名清)。

## Phase 2 — 前端 [BA-6][BA-7]
### Task 2.1 — Explorer 顯示/搜尋 + Run 管理分組/整批 rename
- SPEC ref：Task 2.1。
- 實作要點：
  1. `lib/types.ts` RunInfo 加 `batch_id?:string|null`/`batch_alias?:string|null`。
  2. `runExplorer.ts` formatRunLabel 優先序 `alias?.trim() || (batch_alias ? batch_alias+':'+symbol : symbol/tf/hash)`;**`FeatureExplorer.tsx` 的 filteredRuns 搜尋 haystack 加 batch_alias(filteredRuns 在 FeatureExplorer.tsx 非 runExplorer.ts)**。
  3. `store` 加 `setBatchAlias(batchId, batchAlias)` action(PATCH /batch/{id}/alias+成功 refresh runs+錯誤回傳)。
  4. `RunManagerPanel.tsx` 按 batch_id 分組:有 batch_id 的 runs 收進 group(header 顯示 batch_alias 或 batch_id 短碼 + 「重命名整批」按鈕→setBatchAlias);無 batch_id 的 run 維持單列;per-run rename 保留作 override。
- 修改檔案:types.ts、runExplorer.ts、**FeatureExplorer.tsx(filteredRuns 搜尋)**、featureFactoryStore.ts、RunManagerPanel.tsx。
- 不可做:繞 store;改 selection key;放寬既有斷言。
- 邊界:run 無 batch_id(單列);同 symbol 多 batch;batch_alias 空。
- 驗證:`npm run test -- batchAlias RunManagerPanel runExplorer`——formatRunLabel 優先序(alias>batch_alias:{symbol}>fallback);搜尋 batch_alias 命中;分組顯示+整批 rename 呼叫端點+refresh;無 batch 單列;**同 symbol 多 batch 時 group header 用 batch_id 短碼/時間 disambiguation(Codex r1-MINOR,斷言兩 group header 可辨)**;`npm run build` 過。

## 派工 Prompt
> 前置:repo 根、main、venv、frontend 可 build。讀 SPEC V4+本 TODO。P1→P2,各自 commit(協調者接手)。每 Phase 記交接。**不負責 commit**。禁碰數值/CGSA;不覆寫 alias;cleanup 只擴大保護。BLOCKED 即停。

## 階段 3 自檢
1. 追溯:[BA-1]→1.1;[BA-2]→1.1/2.1;[BA-3]→1.2;[BA-4]→1.1/§C;[BA-5]→1.2;[BA-6]→2.1;[BA-7]→2.1;[BA-8]→§V;[BA-9]→§N;[BA-10]→§B。10/10 ✓
2. 深度:3 Task ≥3 要點+函式級+≥2 邊界+可證偽驗證 ✓
3. 語義:batch_alias 不覆寫 alias 貫穿;cleanup 保護擴大;registry key 不變 ✓
4. 全棧:後端(registry/API)→前端(label/分組)鏈完整 ✓
5. 錨點:§0/§B/3 Task 驗證·邊界·不可做 ✓
