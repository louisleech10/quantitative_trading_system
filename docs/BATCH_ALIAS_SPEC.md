# 批次別名（batch_alias）Phase 1+2 — SPEC V4 (Codex adversarial r1+r2+r3 reconciled)

> 來源：使用者「Phase 1+2」+ Codex 設計（handoffs/20260616-batch-alias-design-codex.md）。manifest：docs/BATCH_ALIAS_MANIFEST.md（[BA-1]~[BA-10]）| TODO：docs/BATCH_ALIAS_TODO.md

## §RISK 風險分級 [BA-10]
- **大小**：中-大。命中 **(b)** registry 共用路徑（add/set_alias/auto_cleanup 多消費者）+ auto-cleanup lifecycle 正確性（命名 run 不被清）。(a)(d) 不命中（純 metadata，不碰數值/特徵計算/CGSA）。
- 流程：Composer 實作 + Codex review；本 SPEC 經 Codex adversarial（跨家族）→ 過 gate 派工。

## §A 假設與待使用者確認
- **已驗證事實**（2026-06-16 Claude rg/讀檔）：
  - registry.add 三處（feature_factory.py:3197/3342/3474）；set_alias（feature_registry.py:139）；add key=(symbol,timeframe,config_hash) upsert merge-preserve。
  - auto_cleanup 候選=`not entry.get("alias")`（run_lifecycle.py:145 一帶），命名 run 不清。
  - batch service per-symbol 生成；batch_id 流經 batch service checkpoint（feature_factory_batch_service.py:202/229/288 checkpoint["batch_id"]）**但未進入生成路徑**——`_compute_single`（ProcessPool，:1052）僅收 symbol/timeframe/config_override，`generate_features`（feature_factory.py:226）無 batch_id 參數 → 故 B1 需顯式加參數穿鏈（Task 1.1）。completed_items 有 browse_task_id 無獨立 config_hash。
  - `mark_deleting()`（run_lifecycle.py）transaction 目前只檢 alias（B2 race 來源）。
  - registry.add 三處在三個 helper 內（非 generate_features 本體）：`_layer7_raw_from_cgsa_pipeline`(:3014,呼叫 @367)、`_layer7_validate_and_persist_cgsa`(:3243,@3373 由前者呼叫)、`_layer7_validate_and_persist`(:3360,@400)→故 batch_id 須顯式參數穿透三 helper，區域變數不可達（r2-B1）。
  - **multi-TF 路徑（r3-B1）**：generate_features multi-TF config 分支到 `MultiTFGenerator.generate_multi_tf()`（feature_factory.py:301 建立、@306 呼叫）；其內持 `self._factory` 並呼叫 `self._factory._layer7_raw_from_cgsa_pipeline`（multi_tf_generator.py:309/:600）、`_layer7_validate_and_persist`（:1364）。真實 kline 每 symbol {1h,4h,12h}→批次主走 multi-TF，故此路徑必須穿透 batch_id。generate_multi_tf 簽名（:42）目前無 batch_id。
  - `set_alias`（feature_registry.py:139）對 deleting target raise `RunBusyError`→set_batch_alias 須對齊（r2-MAJOR#2）。
  - RunInfo（api/models）有 alias/browse_task_id/browse_ready；前端 RunInfo 同步；formatRunLabel（runExplorer.ts）label=alias||symbol/tf/hash。
- **待使用者確認：無**（Phase 1+2 已定；顯示優先序/不覆寫 alias 為委員會設計）。
- **已確認結果**：Phase 1+2（使用者 2026-06-16）；設計 Codex + Claude 認可。

## §C 約束
- 不覆寫 per-run `alias`（[BA-2]）：batch_alias 為獨立欄；顯示優先序 alias>batch_alias:{symbol}>fallback。
- registry key 不變（symbol,timeframe,config_hash）——browse/delete/lease/Explorer selection 穩定身份。
- 唯一性 [BA-4]：per-run alias 同 (s,tf) 唯一不變；batch_alias 以 batch_id 一致，不參與 per-run alias 唯一性檢查。
- auto-cleanup [BA-5]：候選改 `not (alias or batch_alias)`——不弱化既有「命名 run 不清」，擴及 batch_alias。
- 不碰數值/CGSA/特徵計算（純 metadata）；解耦：registry 邏輯在 momentum，API 在 api/，DTO 在 api/models。
- 向後相容：舊 registry entry 無 batch_id/batch_alias 以 .get 讀不炸。

## §G Golden / Baseline
- N/A — 移 §N（純 metadata，無數值輸出；正確性由 pytest/vitest + auto-cleanup 保護測試保證）。

## §P Phase 與依賴
> P1 後端（registry+API+cleanup）→ P2 前端（Explorer 顯示/搜尋 + Run 管理分組/整批 rename）。各自 commit。

### Phase 1 — 後端（依賴：無）[BA-1][BA-2][BA-3][BA-4][BA-5]
**Task 1.1 — registry batch_id/batch_alias + 寫入**
- 檔案：`feature_registry.py` add 接受選填 batch_id/batch_alias；**overwrite 語義(r1+r2-MAJOR#1,r4 釐清三態):① incoming 具體 batch_id 且 `== existing.batch_id`→保留 batch_alias(同批再生不洗掉名);② incoming 具體 batch_id 且 `!= existing.batch_id`→overwrite batch_id+reset batch_alias(換批需重命名);③ `incoming batch_id=None`(單 run 再生同 key)→不 overwrite,merge-preserve 既有 batch_id/batch_alias(不偷剝批次歸屬)**；新 `set_batch_alias(batch_id, batch_alias)`（registry transaction `_locked_mutate`，更新所有該 batch_id 的 entry，回 affected 數）。
- **batch_id 顯式參數穿透（Codex r1-B1+r2-B1+r3-B1：禁用 `self._current_batch_id` mutable state，隱式 context 會跨呼叫污染且不可審）**：`feature_factory.py` `generate_features` 加 `batch_id:Optional[str]=None`。**兩條生成路徑都要穿透（r3-B1：真實 kline 每 symbol 1h/4h/12h，multi-TF 是批次主路徑，漏了 batch_id 不寫）**：
  - ① 單 TF：generate_features→(@367)`_layer7_raw_from_cgsa_pipeline(...,batch_id)`→(@3373)`_layer7_validate_and_persist_cgsa(...,batch_id)`、(@400)`_layer7_validate_and_persist(...,batch_id)`。
  - ② multi-TF：generate_features(@306)`generate_multi_tf(...,batch_id)`（`timeframe/multi_tf_generator.py` generate_multi_tf 加 batch_id 參數）→其內 `self._factory._layer7_raw_from_cgsa_pipeline`（:309/:600）、`_layer7_validate_and_persist`（:1364）都傳 batch_id。
  - 三 helper 簽名（feature_factory.py）加 `batch_id:Optional[str]=None`→registry.add 三處（:3197/3342/3474）以區域參數寫入。`feature_factory_batch_service.py` `_compute_single` 加 batch_id 參數（ProcessPool picklable str），`_process_item_wave`/executor 由 `checkpoint["batch_id"]`（非 task_id）傳入→generate_features(batch_id=)。單 run path batch_id=None 不寫。
- 驗證：`pytest tests/api/test_batch_alias.py -k registry -q`——batch 生成後 entries 有 batch_id；**multi-TF 生成路徑同樣寫入 batch_id（r3-B1，不可只測單 TF）**；set_batch_alias 更新整批 batch_alias 不動 per-run alias；同 run 第二批(具體 batch_id)overwrite；**同 run 以 batch_id=None 再生→既有 batch_id/batch_alias 保留(merge-preserve)**；舊 entry（無欄）load 不炸；affected 數正確。
- 邊界：batch_id 查無→404（見 1.2）；batch_alias 空字串=清除；單 run batch_id=None merge-preserve。不可做：禁覆寫 per-run alias；禁改 add upsert key（symbol,tf,config_hash）；禁用 self mutable batch_id state。

**Task 1.2 — PATCH /batch/{batch_id}/alias 端點 + auto-cleanup 保護**
- 檔案：`api/routes/feature_factory.py` 新 `PATCH /api/v1/features/batch/{batch_id}/alias`（body BatchAliasRequest{batch_alias}）→ service set_batch_alias；**batch_id 無對應 entry→404 `batch_not_found`（定死，非 affected-0，Codex r1-MAJOR）**。**set_batch_alias 對 deleting entry 對齊 set_alias：任一 target entry `deleting`→raise `RunBusyError`→API 409，整筆 transaction fail 不部分更新（r2-MAJOR#2）**。`run_lifecycle.py` **候選 filter 與 `mark_deleting()` transaction 都改 `not (alias or batch_alias)`**（Codex r1-B2：僅改候選不夠，mark_deleting 仍只檢 alias 會與 set_batch_alias race 後誤清命名批次 run，兩處須一致）。RunInfo + list_runs 加 batch_id/batch_alias。
- 驗證：`-k api or cleanup`——PATCH 更新整批回 affected；404；**target 含 deleting→409 RunBusyError 且無 entry 被更新（r2-MAJOR#2）**；list_runs RunInfo 含 batch_id/batch_alias；**auto_cleanup 不清有 batch_alias 的 run**（tmp registry：5 未命名+1 batch_alias，cleanup keep 0 → batch_alias run 倖存）。
- 邊界：batch_alias strip 空=清除（清除後該 run 若無 alias 則回到 cleanup 候選）；deleting entry→409。不可做：禁改 max_nan/數值;禁動 delete reconciliation。

### Phase 2 — 前端（依賴：P1）[BA-6][BA-7]
**Task 2.1 — Explorer 顯示/搜尋 + Run 管理分組/整批 rename**
- 檔案：`frontend/src/lib/types.ts` RunInfo 加 batch_id?/batch_alias?；`runExplorer.ts` formatRunLabel 優先序 `alias||batch_alias+':'+symbol||fallback`；**`FeatureExplorer.tsx` 的 filteredRuns 搜尋 haystack 加 batch_alias（filteredRuns 在 FeatureExplorer.tsx 非 runExplorer.ts，Codex r1-MAJOR）**；`RunManagerPanel.tsx` 按 batch_id/batch_alias 分組（有 batch 的 group header 顯示 batch_alias + 「重命名整批」按鈕呼叫 PATCH batch alias；per-run rename 保留）；store 加 setBatchAlias action。
- 驗證：`npm run test -- batchAlias RunManagerPanel runExplorer`——formatRunLabel 優先序（alias>batch_alias:{symbol}>fallback）；搜尋 batch_alias 命中；分組顯示 + 整批 rename 呼叫端點 + 成功 refresh；無 batch 的 run 單列。`npm run build` 過。
- 邊界：同 symbol 多 batch；run 無 batch_id（單列）；batch_alias 空。不可做：繞 store；改 selection key。

## §V 驗證策略 [BA-8]
- 層級：後端 pytest（registry/API/cleanup）+ 前端 vitest（label/搜尋/分組/rename）。
- 防假綠：不放寬既有 test_run_lifecycle_api / run_lifecycle vitest 斷言；新斷言具體（affected 數、batch_alias 倖存、優先序字串）。
- 回歸：既有 tests/api/test_run_lifecycle_api.py 維持綠（auto_cleanup 改動不破壞既有命名保護）；前端既有 vitest 綠。
- 邊界目錄：舊 entry 無欄 / batch_id 查無 / batch_alias 空清除 / 同 symbol 多 batch / run 無 batch / **batch_id=None 再生 merge-preserve / deleting entry 409 / per-run alias 跨 batch_id reset 保留**。
- **組合測試（r2-MAJOR#3）**：run 同時有 per-run alias + batch_id/batch_alias，第二批 overwrite batch_id（batch_alias reset）後 **per-run alias 必須原樣保留**（斷言 alias 不被 reset 連帶清除）。

## §R 回退
- P1/P2 各自 commit；batch_id/batch_alias 為新增選填欄（向後相容）；auto_cleanup 改動為「擴大保護」（更保守，不會誤清）；前端為新增顯示/分組。

## §N N/A 登記
- §G Golden：N/A — 純 metadata，無數值輸出；正確性由 pytest/vitest + cleanup 保護測試。
- 多 symbol OOM/tier：N/A。CGSA/數值：N/A（不碰）。
- Phase 3 batch entity：N/A（[BA-9] 另議）。
