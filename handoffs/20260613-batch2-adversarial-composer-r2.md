# Batch2 Run Lifecycle SPEC/TODO — Composer 確認輪（R2 vs V3）

- Reviewer: Composer 2.5（adversarial 確認輪；對照 R1 `handoffs/20260613-batch2-adversarial-composer.md`）
- Date: 2026-06-13
- Inputs: `docs/BATCH2_RUN_LIFECYCLE_{SPEC,TODO,MANIFEST,DECISION}.md` **V3**
- Method: 逐條核對 R1 #1–#16；§N 已知限制評可接受性；只對 V3 **新引入**設計查新 BLOCKING（不重開 DECISION 已決項）
- Code spot-check: `grep`/`Read` 錨點（`run_ic_first_pipeline`、`register_hdf5_for_browse:609`、`GET /task/{task_id}` :252）；未跑 pytest/npm

## Verdict 摘要

| 類別 | R1 數量 | V3 收斂 |
|---|---|---|
| BLOCKING (#1–#3) | 3 | **3/3 RESOLVED** |
| MAJOR (#4–#5,#7–#13,#15) | 10 | **9 RESOLVED + 1 ACCEPTED（§N）** |
| MINOR (#6,#14,#16) | 3 | **1 RESOLVED + 2 ACCEPTED（§N）** |

R1 三項 BLOCKING 均已收斂；§N 四項已知限制在 V3 威脅模型/補償路徑下**可接受**；未發現 V3 新設計引入之實質新 BLOCKING。

---

## 逐條核對（R1 #1–#16）

### BLOCKING

#### #1 — 虛構 `generate_and_persist` / 錯誤行號錨點

| 狀態 | **RESOLVED** |
|---|---|
| V3 證據 | SPEC §A 勘誤：「lease 第二掛點真實函式=**`run_ic_first_pipeline`**（~:1860；V2 `generate_and_persist(:1890)` 為虛構名）」；Task 2.1 明列 `generate_features`（:209，hash ~:236-243）與 `run_ic_first_pipeline`（~:1860）；TODO Task 2.1(1) 同文；MANIFEST [B2-5] 同勘誤。 |
| 程式碼抽查 | `grep def generate_and_persist` → 0；`run_ic_first_pipeline` 於 `feature_factory.py:1883`。 |

#### #2 — warmup 與 factory lease 生命週期結構性矛盾

| 狀態 | **RESOLVED** |
|---|---|
| V3 證據 | SPEC Task 2.1：**`lease_sink: Optional[list]`**——成功且 sink 非 None → 不 release、`sink.append(lease)`；service 傳 sink，**warmup daemon thread 接手 lease**，thread `finally` release；驗收「**lockdir owner token 不變（無空窗）**」；明禁「release-後-reacquire」。DECISION #23：「factory 經 lease_sink 把鎖交給 service，warmup 完才釋放」。MANIFEST [B2-5] 凍結介面。 |
| 備註 | 模型由 R1 建議的 (A)/(B) 擇一，凍結為 **caller-holds via lease_sink**（Codex N3 合併），可實作且可測。 |

#### #3 — `register_hdf5_for_browse` 未納入 stable_id 遷移

| 狀態 | **RESOLVED** |
|---|---|
| V3 證據 | SPEC Task 2.1：「pass2 … 與 **`register_hdf5_for_browse`（:609）** 與 batch adapter 一律 `browse_{s}_{tf}_{full_config_hash}`」；刪除 reconciliation「按 full hash 清兩種來源 task」；TODO Task 2.1(3) 含 `feature_factory_batch_adapters.py`；MANIFEST [B2-9]；DECISION #25 全鏈。 |
| 程式碼現狀 | `service:609` 仍為 `browse_{symbol}_{timeframe}`（待實作，SPEC 已覆蓋）。 |

---

### MAJOR

#### #4 — API path `GET /tasks/{id}` vs 實際 route

| 狀態 | **RESOLVED** |
|---|---|
| V3 證據 | SPEC Task 2.2：「path=**`GET /task/{task_id}`**（:252）」；TODO Task 2.2(1)、Task 3.1 types 對齊同 path；MANIFEST [B2-6] 勘誤 Composer #4。 |
| 程式碼抽查 | `api/routes/feature_factory.py:252` `@router.get("/task/{task_id}")`。 |

#### #5 — `auto_cleanup` re-check 與無鎖 `get()` TOCTOU

| 狀態 | **RESOLVED** |
|---|---|
| V3 證據 | SPEC Task 1.1：`auto_cleanup` → acquire → **`_locked_mutate` 內 re-check alias 為空且標記 `deleting:true`** → `_delete_run_locked`；Task 0.3：`set_alias` 對 `deleting:true` → `RunBusyError`；`mark_deleting`/`clear_deleting`（TODO 0.3）；驗收 barrier「mark_deleting 後 rmtree 前 set_alias → RunBusyError」。DECISION #22：set_alias 亦需 run lease。 |
| 備註 | 超越 R1「re-check 須在 _locked_mutate 內」——增 **deleting 標記 + lease 雙防**。 |

#### #6 — RunLease 檔名 SPEC 自相矛盾（`.lock` vs 三元組）

| 狀態 | **RESOLVED**（設計替換） |
|---|---|
| V3 證據 | V3 重設計為 **lockdir**：`{safe_token(s)}_{safe_token(tf)}_{full_hash}.lockdir/`（Task 0.2、MANIFEST [B2-2]、`safe_token` 與 cgsa 共用）；不再混用 `.lock` 檔名表述。 |

#### #7 — `RunInfo.active: bool` 語義未定義

| 狀態 | **RESOLVED** |
|---|---|
| V3 證據 | Task 0.2：`is_run_active` = **lockdir 存在**（註明 [B2-6] active 定義，Composer #7）；Task 2.2：`RunInfo.active := is_run_active(triple)` + list/DELETE 409 一致性測試；MANIFEST [B2-6]。 |

#### #8 — 刪除後 batch checkpoint / `_tasks` 可見性

| 狀態 | **ACCEPTED（§N 已知限制 + 補償）** |
|---|---|
| V3 證據 | SPEC Task 2.2：「batch `_tasks`/checkpoint 可見性=**out-of-scope 已知限制**（§N，Composer #8——**resume 端由 Task 2.3 收斂**）」；§N：「面板不隨刪除即時更新（resume 正確性由 Task 2.3 保證）」；Task 2.3 / Codex N4：resume 驗 completed manifest，缺→requeue；DECISION #24。 |
| 可接受性 | **可接受**。即時面板與刪除 reconciliation 脫鉤屬明確產品邊界；**下次 resume 重排隊**保證 batch 語義正確，較即時掃 `_tasks` 更低耦合。使用者若見 stale 面板，resume 後自癒。 |

#### #9 — completion WS/polling 等價 vs `get_task_status` 形狀

| 狀態 | **RESOLVED** |
|---|---|
| V3 證據 | Task 2.2：`get_task_status` 擴充 **`retention_prompt`+`run_identity`** + `FeatureTaskStatusResponse.result` 填值；驗收「WS 與 polling 用**同一 fixture payload**」；MANIFEST [B2-6]/[B2-7]；TODO Task 2.2、3.1。 |

#### #10 — registry lock 5s 逾時與 batch 並行混淆

| 狀態 | **RESOLVED** |
|---|---|
| V3 證據 | Task 0.3 / MANIFEST [B2-3]：指數退避 10ms×2 上限 500ms、**總 30s**、逾時 **`RegistryLockTimeout`**（≠ `RunBusyError`）；TODO 0.3 驗證「殘留鎖 → RegistryLockTimeout」。 |

#### #11 — factory 內 registry 實例記憶體陳舊

| 狀態 | **ACCEPTED（§N 已知限制）** |
|---|---|
| V3 證據 | §N：「factory 內 registry 實例記憶體陳舊（**磁碟一致由 _locked_mutate reload 保證；factory 僅 add**，Composer #11）」；MANIFEST [B2-10] 同登記。 |
| 可接受性 | **可接受**。R1 風險在「跨實例讀 list_all/find」；V3 限定 factory 路徑 primarily `add`、lifecycle 用注入 registry + 磁碟 reload。若日後 factory 擴讀路徑需另開項，非本批 BLOCKING。 |

#### #12 — `created_at` ISO 轉換未覆蓋 float/混用

| 狀態 | **RESOLVED** |
|---|---|
| V3 證據 | Task 2.2：「numeric epoch 秒→ISO UTC、ISO 字串 passthrough、其他→null」+ float 與 `cfg_batch2d` 樣本測試；MANIFEST [B2-6]；TODO Task 2.2 驗證 ISO regex。 |

#### #13 — vitest 可行但 polling dialog 依賴後端契約

| 狀態 | **RESOLVED**（依 #9） |
|---|---|
| V3 證據 | MANIFEST [B2-7]：「依 [B2-6] 後端契約落地後 vitest 可實作」；Task 3.1 對齊 `GET /task/{task_id}` + 兩路同 fixture；TODO Task 3.1 驗證 polling 路。 |

#### #15 — stale 雙條件 24h 阻斷過長

| 狀態 | **RESOLVED**（產品決策落地） |
|---|---|
| V3 證據 | MANIFEST [B2-2]：**age>1h（3600s）**（Composer #15 縮短）+ break-glass 手刪 lockdir；Task 0.2 stale 規則同；DECISION #21：「崩潰後最多等 1h 或手刪 .locks」。 |
| 備註 | 與 DECISION #21 綁定；使用者仍可否決 1h 門檻，但文件已寫死，非規格缺口。 |

---

### MINOR

#### #14 — symlink path-swap TOCTOU 未測

| 狀態 | **ACCEPTED（§N 已知限制）** |
|---|---|
| V3 證據 | §N：「symlink parent-swap TOCTOU（內部進程皆守 lease，**無不可信本地行為者威脅模型**，Composer #14）」。 |
| 可接受性 | **可接受**。R1 自身標「非本批 BLOCKING」；V3 四層 lstat + lease 互斥已覆蓋主要路徑；殘餘 TOCTOU 已文件化。 |

#### #16 — pid 重用 stale 誤判

| 狀態 | **ACCEPTED（§N + 設計緩解）** |
|---|---|
| V3 證據 | lockdir `owner.json` 含 **uuid token+pid+iso_ts**（Task 0.2、MANIFEST [B2-2]）；§N：「pid 重用極端誤判（**token+age 緩解**，Composer #16）」；release 比對 token 非僅 pid。 |
| 可接受性 | **可接受**。R1 建議的 host/uuid 已部分落地（uuid token）；殘餘極低機率已 §N 登記。 |

---

## R1 #17（鎖序）— 超出本輪 #1–#16 範圍

R1 #17 要求「全域鎖序：先 run lease，後 registry lock」。V3 實作敘述（delete/cleanup/set_alias 皆先 acquire lease 再 `_locked_mutate`）**隱含**一致順序，但未單獨成章。**未列為本輪 FAIL 理由**（不在使用者指定 #1–#16；且現設計路徑未見反向持鎖）。建議實作時於 `run_lifecycle.py` docstring 一行記錄，非派工阻擋。

---

## V3 新引入設計 — 新 BLOCKING 掃描

| 新設計 | 評估 |
|---|---|
| lockdir + rename graveyard 接管（替 O_EXCL 檔鎖） | 有雙 breaker barrier 驗收；解 N1 誤刪鎖；**非 BLOCKING** |
| `lease_sink: list` 介面 | 凍結於 SPEC/TODO/MANIFEST/DECISION #23；warmup token 連續性可測；**非 BLOCKING** |
| `deleting:true` registry 標記 | 崩潰殘留→下次 cleanup 重走（Task 1.1 邊界）；**非 BLOCKING** |
| stale 1h（DECISION #21） | 已產品決策；#15 收斂；**不重開** |
| Task 2.3 resume requeue | 補 #8 限制；**非 BLOCKING** |
| corrupt 時 add 不落盤（DECISION #26） | 明確 fail-closed；**非 BLOCKING** |

**結論：無新實質 BLOCKING。**

---

## §N 已知限制總表（可接受性）

| §N 項 | 對應 R1 | 可接受？ | 理由 |
|---|---|---|---|
| symlink parent-swap TOCTOU | #14 | ✅ | 威脅模型限定 + 四層 lstat |
| pid 重用極端誤判 | #16 | ✅ | uuid token + age |
| factory registry 記憶體陳舊 | #11 | ✅ | 磁碟 _locked_mutate + factory 僅 add |
| batch `_tasks` 不即時更新 | #8 | ✅ | Task 2.3 resume 重排隊補償 |

---

## 修補後 Gate（R1 六項）對照

| R1 Gate | V3 |
|---|---|
| 1. 刪除 `generate_and_persist`、寫死 lease 掛點 | ✅ Task 2.1 / §A |
| 2. 凍結 warmup lease 模型 + 順序 | ✅ lease_sink + DECISION #23 |
| 3. `register_hdf5_for_browse` 全鏈 | ✅ Task 2.1 + DECISION #25 |
| 4. polling path + retention schema | ✅ Task 2.2 `GET /task/{task_id}` |
| 5. `active` 定義 + alias re-check 在 lock 內 | ✅ is_run_active + mark_deleting |
| 6. registry 逾時 + stale 運維政策 | ✅ RegistryLockTimeout 30s + DECISION #21 1h |

---

ASSUMPTIONS_VERIFIED: V3 四檔已讀；錨點 grep 確認 `run_ic_first_pipeline`/`register_hdf5_for_browse:609`/`GET /task/{task_id}`:252；未執行 pytest/npm
TESTS_RUN: read-only confirmation review only
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅新增本 handoff；未改 docs/momentum/api/frontend）
NUMERIC_OR_SCHEMA_IMPACT: none（確認輪；V3 已記載之 schema 變更為待實作項）

STATUS: PASS — 可派工
