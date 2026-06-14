# Batch2 Run Lifecycle SPEC/TODO Adversarial Review (Composer — V2 獨立全輪)

- Reviewer: Composer 2.5（adversarial，V13；與 Codex round1 平行，非附和）
- Date: 2026-06-13
- Inputs: `docs/BATCH2_RUN_LIFECYCLE_MANIFEST.md` V2、`docs/BATCH2_RUN_LIFECYCLE_SPEC.md` V2、`docs/BATCH2_RUN_LIFECYCLE_TODO.md` V2
- Background read: `handoffs/20260613-batch2-adversarial-codex.md`（V1 FAIL 19 findings；本輪驗證 V2 收斂度 + 新漏洞）
- Focus: O_EXCL lease 崩潰/stale、registry 檔鎖死鎖/逾時、刪除 TOCTOU、pass2 stable_id 消費者、completion 兩路等價、vitest 可行性
- Strictness: MAXIMUM

## Verdict：需修補後派工

V2 已收斂 Codex V1 多數 BLOCKING（merge-preserve、per-run lease、registry transaction、API 契約寫死、lstat 順序、vitest 真測試、interleaving barrier）。但仍有 **3 項 BLOCKING**（warmup 跨層 lease 不可實作、虛構入口函式名、batch browse 穩定 ID 遷移不完整）與數項 MAJOR；在 MAXIMUM 門檻下尚不可派工。

---

## §0 挑戰前提 — §A 已驗證事實抽查

獨立驗證方式：`Read`/`Grep` 對照下列檔案（未跑 pytest/npm；本任務僅 review）。

| §A 聲稱 | 獨立結果 | 判定 |
|---|---|---|
| run 目錄 `feature_storage.py:698-703` | `feature_run_dir` 使用 `_safe_path_segment` 拒 `/` `\` `.` `..` | **fact verified** |
| features vs cgsa segment 不可互換 | features reject vs cgsa `re.sub`（`feature_factory.py:903-905`） | **fact verified** |
| registry 無鎖 upsert（`:47-99`） | `add` 整筆替換 + temp rename，無 lock/reload | **fact verified** |
| 多 registry 實例（`:194`, `factories.py:280-290,648-652`） | `FeatureFactory.__init__` 自建；`create_feature_library`/`create_feature_registry` 另建 | **fact verified** |
| 三處 `_registry.add` 不帶 alias/size | `:3103-3113`, `:3248-3258`, 第三處同型（grep 確認） | **fact verified** |
| CGSA `FFACT_CGSA_WORK_DIR` override（`:899-912`） | env 非空則完全 override work_dir | **fact verified** |
| CGSA resume gate 依賴 L7 manifest（`:923-960`） | `l7_manifest_path.exists()` 否則 skip resume | **fact verified** |
| 單筆 task 建立無三元組（`service:153-169`） | `start_generation` 僅 task_id/status/progress | **fact verified** |
| batch worker 自建 factory（`batch:1001-1034`） | `_compute_single` → `create_feature_factory()` → `generate_features` | **fact verified** |
| 完成後背景 warmup（`service:251-278`） | persist 後 daemon thread 啟動 catalog/dq/stats warmup | **fact verified** |
| pass2 `browse_{s}_{tf}` 無 hash（`:3861-3906`） | `stable_id = f"browse_{symbol}_{timeframe}"` + 同組只留首個 | **fact verified** |
| `GenerationProgress.tsx:48-74` 只取 stage/progress/message/status | `applyPayload` 型別與 spread 皆無 retention/run_identity | **fact verified** |
| vitest 已配置 | `frontend/package.json` `"test": "vitest run"`；既有 `featureFactoryStore.test.ts` 等 | **fact verified** |
| **入口錨點 `feature_factory.py:218/1890`** | **:218 為 `persist: bool` 參數；:1890 為 `layers` 參數；`config_hash` 在 :236-243 才算出；repo 內 **無 `generate_and_persist` 函式**（第二入口實為 `run_ic_first_pipeline` :1883） | **§A/SPEC/TODO 錨點錯誤 — assumption 當 fact** |

---

## Findings

### 前提 / 被當成事實的錯誤錨點

1. **[BLOCKING][High] SPEC/TODO 第二 lease 掛點引用不存在的 `generate_and_persist`（:1890）。**
   - 證據：SPEC Task 2.1「`:224` 後與 `:1910` 後」；TODO Task 2.1「`:218` 與 `generate_and_persist`（:1890 起）」；`grep def generate_and_persist` → 0；`:1890` 實為 `run_ic_first_pipeline` 的 `layers` 參數。
   - 會怎麼失敗：實作者搜不到函式、漏掛 IC-first 路徑，或誤改 `run_ic_first_pipeline` 簽名；lease 覆蓋面不可驗收。
   - 修法：刪除虛構名；明列**實際**需掛 lease 的函式（至少 `generate_features`；若 IC-first 在產品路徑則含 `run_ic_first_pipeline`）；行號改為 `config_hash` 確定後（現碼 ~:236-243）。

2. **[BLOCKING][High] warmup「同 lease 持有」與 factory 內 lease 生命週期結構性矛盾。**
   - 證據：SPEC Task 2.1「warmup 整段在同一 lease…warmup 完才 release」；現碼 `generate_features` 在 executor 線程內同步返回（`service:223-235`），warmup 在返回**之後**以 daemon thread 啟動（`:259-271`, `_start_cgsa_catalog_warmup` :1416-1430）；TODO 寫「lease 由 task 執行緒傳遞或重新 acquire——擇前者」但無傳遞機制/API。
   - 會怎麼失敗：factory `finally` 一 release，warmup 讀檔與 DELETE 競態仍成立；「warmup barrier 期間 DELETE→409」測試無法依設計通過（假綠或被迫 mock lease）。
   - 修法：在 SPEC 凍結一種可實作模型（擇一寫死）：(A) lease 上提到 service/`RunSession` 跨 generate+warmup+cleanup；或 (B) warmup 線程內 `RunLease.acquire` 同一三元組且 generation 延遲 release（需跨線程 lease handle + join 語義）；並定義 completed event 與 warmup join 的順序。

3. **[BLOCKING][High] pass2 stable_id 遷移未覆蓋 `register_hdf5_for_browse`，多 hash 同 (s,tf) 仍互踩。**
   - 證據：V2 只改 `_restore_persisted_tasks` pass2（SPEC Task 2.1 `:3861-3906`）；現碼 `register_hdf5_for_browse` 仍 `task_id = f"browse_{symbol}_{timeframe}"`（`service:608-609`），batch adapter 呼叫此路徑（`feature_factory_batch_adapters.py`）；與新 `browse_{s}_{tf}_{hash8}` 不一致。
   - 會怎麼失敗：batch 完成註冊覆蓋舊 browse task；刪除 reconciliation 依 hash8 前綴清 task 時漏清或誤清；pass2 測試綠但 batch 路徑仍錯。
   - 修法：Task 2.1 scope 明列同步改 `register_hdf5_for_browse` + batch adapter + 既有測試（如 `test_failopen_producer.py` 的 `browse_BTCUSDT_12h`）；刪除 reconciliation 規則覆蓋兩種建立路徑。

### 1. 矛盾 / 互斥

4. **[MAJOR][High] API 路徑與驗收敘述不一致。**
   - 證據：TODO Task 2.2 驗證「`GET /tasks/{id}`」；現有 route 為 `GET /task/{task_id}`（`api/routes/feature_factory.py:252`）。
   - 會怎麼失敗：實作新欄位掛錯端點或測試 404 假紅。
   - 修法：契約寫死實際 path（或新增 alias 並標 deprecated）；測試與 SPEC 同步。

5. **[MAJOR][High] `auto_cleanup`「registry transaction 內 re-check alias」與 `get()` 無鎖讀矛盾。**
   - 證據：SPEC Task 1.1「lease 內經 registry transaction re-check alias」；TODO Task 0.3「`get` 讀方法不加鎖」；Task 1.1 auto_cleanup 用 `registry.get` re-check 後才 `delete_run`。
   - 會怎麼失敗：re-check 與 `set_alias` 之間 TOCTOU；barrier 測試若只鎖 lease 不鎖 registry 仍可能刪到已命名 run。
   - 修法：re-check 必須在 `_locked_mutate` 內（讀+判定+刪除 intent）或 `set_alias` 與 cleanup 共用同一 locked section。

6. **[MINOR][Medium] RunLease 檔名在 SPEC 內自相矛盾。**
   - 證據：Task 0.2「`.locks/{safe}_{full_hash}.lock`」vs Manifest/TODO「`{safe_s}_{safe_tf}_{full_hash}`」。
   - 修法：統一為三元組檔名（與「同 hash 不同 (s,tf) 不互斥」一致）。

### 2. 漏項 / 端到端

7. **[MAJOR][High] `RunInfo.active: bool` 語義未定義。**
   - 證據：SPEC [B2-6] 列 `active:bool`；無「= lease 存在 / service task running / batch worker」任一明確定義或查詢 API。
   - 會怎麼失敗：UI「使用中禁刪」與 409 不一致；list 顯示 active=false 但 DELETE 仍 409。
   - 修法：寫死 `active := exists RunLease lock file for triple` 或 `generation/warmup lease held` 並附查詢實作與測試。

8. **[MAJOR][High] 刪除後 batch checkpoint / `register_hdf5_for_browse` 可見性未納入 reconciliation。**
   - 證據：V2 僅 Task 4.1(4) 測 CGSA resume manifest gate；batch `_tasks`/checkpoint 仍可能顯示 completed 項指向已刪 run（`batch_service` 獨立狀態）。
   - 會怎麼失敗：UI/批次品質面板仍列已刪 run；resume 語義與使用者認知分裂。
   - 修法：明確 out-of-scope 並文件化 UX 限制，或 Task 2.2 加「刪除時掃描 batch completed_items 標記 stale」。

### 3. 不可測驗收

9. **[MAJOR][High] completion「WS/polling 等價」與現有 `get_task_status` 形狀不符。**
   - 證據：SPEC 要求 `GET task status` 含 `retention_prompt`+`run_identity`；現 `get_task_status` 不回 `result`/metadata（`service:554-567`）；`FeatureTaskStatusResponse` 有 `result` 但 service 未填；WS payload 經 `_notify_callbacks` 送 `result: summary`（`:273-278`），`GenerationProgress` 丟棄。
   - 會怎麼失敗：polling-only 用戶永遠看不到 retention dialog；vitest「polling 路徑開 dialog」無法對齊真實 API。
   - 修法：擴充 `get_task_status`（或 document 必須 `GET /result/{id}` 合併）；Pydantic+`types.ts` 同型別；兩路測試用同一 fixture payload。

### 4. 可疑 quant 假設

- **無**（本批不改計算語義）。刪除生成中 artifact 風險見 #2、#3。

### 5. 過度工程

- **無**。O_EXCL + 單檔 registry lock 合理；問題在邊界語義未凍結。

### 6. OOM / 並行

10. **[MAJOR][Medium] 全域 `registry.json.lock` 5s 自旋在 batch 多 worker 同時收尾時可能逾時。**
    - 證據：Task 0.3「≤5s 逾時 raise」；batch `_compute_single` 多進程同時 `generate_features` 結尾皆 `_registry.add`。
    - 會怎麼失敗：合法並行生成尾端隨機 `TimeoutError`，與「busy」語義混淆；測試 flaky。
    - 修法：區分 `RegistryLockTimeout` vs `RunBusyError`；或 batch 尾端序列化 registry 寫入；或提高逾時+指數退避並寫入 SPEC 數值。

### 7. Cache / Registry 正確性

11. **[MAJOR][Medium] Factory 內 `self._registry._entries` 在 lifecycle 外部 mutation 後可能長期陳舊。**
    - 證據：lifecycle 用注入 registry；factory 持有獨立實例（`:194`）；`_locked_mutate` 只保證磁碟一致，不保證其他實例記憶體 reload。
    - 會怎麼失敗：factory 內部若日後讀 `list_all`/`find`（或除錯路徑）看到過期 alias/size。
    - 修法：`create_run_lifecycle_manager` 與 `create_feature_factory` 共用單一 registry 實例，或 factory 在每次 `add` 前強制 reload（已在 mutate 內，但跨實例仍舊）。

### 8. API / 型別 / 相容

12. **[MAJOR][Medium] `created_at` ISO 轉換規則未覆蓋 registry 既有 float seconds 與 pass2 manifest 字串混用。**
    - 證據：§A 稱 epoch seconds；pass2 restore `created_at` 取自 manifest 欄位（`:3902`）未必為 ISO。
    - 修法：API 層統一 `datetime.fromtimestamp`（秒）+ 明確 UTC；單元測試含 `cfg_batch2d` 與 float 樣本。

### 9. 測試品質

13. **[MAJOR][High] vitest 可行，但「polling 開 dialog」需後端契約先落地（見 #9）。**
    - 證據：vitest 存在且 store 測試慣例已有；現前端無 `retention_prompt` 型別欄位（`types.ts:497-506`）。
    - 判定：基礎設施工具鏈 **可行**；驗收案例在 #2/#9 修復前為**不可實作**。

14. **[MINOR][High] symlink 測試未要求 path-swap TOCTOU（僅 lstat 四層）。**
    - 證據：§V 列 leaf/symbol/tf/root symlink；未要求 check 後替換 parent 的競態（NFS/本地極端）。
    - 修法：列為已知殘餘風險或加「刪除全程持有 run lease + 不跟隨 symlink 的 openat 風格」後續項；非本批 BLOCKING。

### 10. Agent 可執行性 — O_EXCL lease 專項

15. **[MAJOR][High] stale 破鎖雙條件（pid 死 **且** age>24h）在崩潰後長時間阻斷同 hash 刪除與重生。**
    - 證據：Task 0.2 stale 規則；空 lock 檔仍要 age>24h。
    - 會怎麼失敗：kill -9 後 24h 內 DELETE/同 config 生成皆 busy；dev/staging 需手動清 `.locks`。
    - 修法：產品決策寫死（接受 24h）或縮短 stale+admin break-glass；文檔化運維步驟；測試覆蓋「空檔+短 age 仍 busy」。

16. **[MINOR][Medium] stale 檢測用 `os.kill(pid,0)` 在 pid 重用邊界可能誤判鎖仍存活。**
    - 證據：lock 檔寫 pid+ts；Linux pid 重用。
    - 失敗：極低機率長時間誤 block；或誤破鎖（若只信 pid 不死）。
    - 修法：lock 檔加 host+start_time+uuid；stale 判定以 ts 為主、pid 為輔。

17. **[MAJOR][Medium] registry lock 與 run lease 鎖序未寫死，存在未來死鎖擴展風險。**
    - 證據：delete 順序 lease→fs→registry；若日後在 `_locked_mutate` 內再 acquire run lease 會 invert。
    - 修法：SPEC 增「全域鎖序：先 run lease，後 registry lock；禁止反向」。

### pass2 stable_id 既有消費者（獨立 grep）

| 消費者 | 現狀 | V2 覆蓋 |
|---|---|---|
| `_restore_persisted_tasks` pass2 | `browse_{s}_{tf}` | ✅ 計劃改 hash8 |
| `register_hdf5_for_browse` | `browse_{s}_{tf}` | ❌ 未列 |
| `test_failopen_producer` | `browse_BTCUSDT_12h` | ❌ 需更新 |
| browse_* API | 以 task_id 字串為 key | 依賴上述註冊 |

---

## 與 Codex V1 對照（獨立判斷）

| Codex V1 主題 | V2 狀態 | Composer 補充 |
|---|---|---|
| 風險低估 (b)(c) | ✅ 已升大 | 同意 |
| registry merge-preserve | ✅ Task 0.3 | 同意 |
| per-run lease + batch path | ✅ 設計有；⚠️ warmup 跨層仍未解 (#2) | **不同意「已可派工」** |
| registry transaction | ✅ | 同意；注意 #10 逾時 |
| task/browse reconciliation | ⚠️ 部分 | pass2 有；batch register 漏 (#3) |
| API 契約寫死 | ✅ 大幅改善 | GET path 仍錯 (#4) |
| symlink lstat 順序 | ✅ | 同意 |
| vitest 假 gate | ✅ 改 vitest | 可行但依賴 #9 |
| FFACT_CGSA_WORK_DIR | ✅ skip+reason | 同意 |
| hash8 ownership | ✅ manifest 全 hash | 同意 |

---

## 被當成事實的未驗證假設（§0）

1. **[High]** 「`generate_and_persist` @ :1890 為生成入口」— **false**（虛構函式；§A 行號錯）。
2. **[High]** 「factory 內 lease + service warmup 可自然共用」— **未證實**；現架構 **false**（#2）。
3. **[High]** 「pass2 stable_id 變更即可區分多 hash browse」— **partial**；batch `register_hdf5_for_browse` 未納入（#3）。
4. **[Medium]** 「`GET /tasks/{id}` 為 polling 契約」— **false**；現為 `/task/{task_id}`（#4）。
5. **[Medium]** 「registry get 無鎖足夠做 cleanup re-check」— **false**（#5）。
6. **[Low]** 「§A 行號可作實作錨點」— **部分 false**（:218/:1890 非 config_hash 入口）。

其餘 §A 核心行為陳述（registry 無鎖、batch worker、warmup 背景線程、pass2 無 hash、GenerationProgress 欄位、vitest 存在）— **獨立複核為 fact**。

---

## 修補後最低重審 Gate

1. 刪除 `generate_and_persist`；寫死 lease 掛點函式與正確行號。
2. 凍結 warmup lease 模型（service 層或跨線程 handle）+ completed/warmup/cleanup 順序圖。
3. `register_hdf5_for_browse` + batch adapter 納入 stable_id 遷移與刪除 reconciliation。
4. 固定 polling 端點 path 與 response schema（含 retention 欄位）。
5. `active` 定義 + alias re-check 在 registry lock 內。
6. （建議）registry lock 逾時與 stale lease 運維政策寫入 DECISION。

---

ASSUMPTIONS_VERIFIED: 獨立 Read/Grep 核實 §A 15 項中 12 項 fact、3 項錨點/架構假設錯誤；未執行 pytest/npm
TESTS_RUN: read-only adversarial review only
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅新增本 handoff；未改 docs/momentum/api/frontend）
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: FAIL — warmup 跨層 lease 不可實作、虛構 generate_and_persist 掛點、batch browse stable_id 遷移缺口；修補後重審
