# Batch2 Run Lifecycle — Composer Code Review R2（複驗）

- **Reviewer**: Composer 2.5（R2 複驗；實作者=Codex `f6762bd`）
- **Range**: `git diff 2e0cef3..f6762bd`
- **對照**: R1 `handoffs/20260613-batch2-codereview-composer.md`（5 MAJOR + 4 MINOR → REQUEST_CHANGES）
- **抽驗**: `pytest tests/api/test_run_lifecycle_api.py -v` → **14/14 passed**（0.51s）；`npm run test -- run_lifecycle` → **5/5 passed**

## R1 → R2 變更摘要

| 檔案 | 變更 |
|------|------|
| `api/services/feature_factory_service.py` | DELETE 前置存在性檢查；HDF5 路徑 release 後 `auto_cleanup`；browse 註解；`_invalidate_task_cache` 移出 lock |
| `tests/api/test_run_lifecycle_api.py` | +9 用例（HTTP async_client、lease 鏈、HDF5 cleanup、resume 整合、created_at） |
| `frontend/.../run_lifecycle.test.tsx` | +WS/polling 同 payload、+delete_partial 500 顯示 |

## MAJOR 逐條核對

### MAJOR #1 — DELETE 冪等 200

**R1**: `delete_run` 在 registry 缺失時先 `KeyError`→404，與 TODO「冪等→200」及 manager 層冪等不一致。

**R2 實作**（`feature_factory_service.py:672-685`）：
- 刪除前記錄 `registry_exists` / `artifact_exists`（含 features + cgsa leaf）
- 先呼叫 `manager.delete_run`，僅當**兩者皆不存在**時才 `KeyError`→404

**判定: PARTIALLY RESOLVED**

| 情境 | R1 | R2 | SPEC/TODO |
|------|----|----|-----------|
| 僅 artifact、無 registry | 404 | **200** ✅ | 應可刪 |
| 首次 DELETE（有 artifact） | 200 | 200 ✅ | — |
| **重複 DELETE（皆已清）** | 404 | **仍 404** ❌ | TODO L95「冪等→200」 |
| 從未存在 | 404 | 404 ✅ | `run_not_found` |

**證據**：
- `test_delete_idempotent_artifact_and_browse_reconciliation` L379-381 明確斷言第二次 DELETE→404 `run_not_found`
- manager 層第二次 `delete_run` 仍無錯（`test_run_lifecycle.py:174`），但 API 在 pre-check 雙 false 時阻斷
- commit message 稱「冪等 200」，與上述重複 DELETE 行為及測試斷言不一致

---

### MAJOR #2 — Task 2.2 HTTP 層四碼測試

**R1**: 全程 `__new__` 直連 service，未經 `async_client`。

**R2**: 新增 `app` / `async_client` fixture + 多個 HTTP 整合測試。

**判定: RESOLVED**

| 要求 | 測試 | 證據 |
|------|------|------|
| 409 `run_busy` | `test_runs_http_error_contracts` | mock `RunBusyError`→409+code |
| 404 `run_not_found` | 同上 | mock `KeyError`→404 |
| 500 `delete_partial` | 同上 | errors 非空→500+errors 陣列 |
| 422 `alias_conflict` | 同上 | PATCH alias→422 |
| warmup 期 DELETE 409 / release 後 200 | `test_generate_warmup_delete_lease_chain` | HTTP DELETE 409→barrier 結束→200 |
| `created_at` ISO | `test_list_runs_created_at_iso_samples` | epoch float + ISO 字串 regex |
| 刪後 browse reconciliation | `test_delete_idempotent_artifact_and_browse_reconciliation` | `/browse/available` 2→0 |

---

### MAJOR #3 — resume 三分支整合測試

**R1**: 僅靜態 resolver；`resume_batch` 零整合。

**R2**:

**判定: PARTIALLY RESOLVED**

| 分支 | R2 覆蓋 | 證據 |
|------|---------|------|
| manifest **缺失**→requeue | ✅ 整合 | `test_resume_batch_requeues_missing_resolved_run`（output_path / browse_task_id 參數化）；`execute_mock.assert_called_once()` |
| **legacy** 無 hash→warning 保留 | ✅ 整合 | `test_resume_batch_keeps_legacy_completed_item`；caplog + `execute_mock.assert_not_called()` |
| manifest **存在**→保留 completed | ⚠️ 僅靜態 | `test_resume_hash_resolver_three_branches` L229 `_completed_manifest_exists`；**無** `resume_batch` 整合（manifest 在碟、不 requeue、status completed） |

---

### MAJOR #4 — lease 全鏈

**R1**: 缺 busy 第二 generate、warmup 期 HTTP DELETE、pass2 雙 hash。

**R2**:

**判定: RESOLVED**

| 要求 | 測試 | 證據 |
|------|------|------|
| 同 hash 第二 generate→busy | `test_lease_sink_holds_until_release` + `test_generate_warmup_delete_lease_chain` L133-134 | `RunBusyError` match `"busy"` |
| warmup barrier 期 `is_run_active` 連續 | `test_generate_warmup_delete_lease_chain` L157-162 | barrier 中 assert True；409 後仍 True |
| warmup 期 HTTP DELETE→409 | 同上 L159-161 | async_client DELETE→409 `run_busy` |
| warmup 畢 DELETE→200 | 同上 L167-168 | release 後 200 |
| pass2 兩 full-hash browse 並存 | `test_pass2_restores_two_full_hash_browse_tasks` | `set(_tasks)` 含兩 hash ID |

---

### MAJOR #5 — HDF5 路徑 release 後 `auto_cleanup`

**R1**: else（HDF5）分支僅 `release()`，無 cleanup。

**R2**（`feature_factory_service.py:282-293`）：HDF5 路徑 pop lease→release→`_lifecycle().auto_cleanup(...)`，異常 warning。

**判定: RESOLVED** — `test_hdf5_completion_releases_then_auto_cleans` 斷言 `events == ["release", "cleanup"]`。

---

## MINOR 逐條核對

| # | R1 議題 | R2 判定 | 證據 |
|---|---------|---------|------|
| 1 | Frontend WS/polling、delete_partial、500 | **RESOLVED** | vitest 5/5；新增 WS+polling 同 `completionQueue`；`delete_partial` alert 含 errors |
| 2 | `_write_run_size` 私有 registry API | **UNRESOLVED** | `feature_factory_service.py:726-729` 仍用 `_find_entry`/`_locked_mutate`；本輪未改 |
| 3 | `list_runs` created_at 無單測 | **RESOLVED** | `test_list_runs_created_at_iso_samples` |
| 4 | pass2 註解 hash8 legacy | **RESOLVED** | L4040-4041 改為 full-hash 敘述 |

---

## 防假綠（diff 既有斷言）

- `git diff 2e0cef3..f6762bd -- tests/`：**僅新增**斷言，無刪除/放寬既有 `assert` 門檻
- R1 已登記的 browse full-hash fixture 更新未回退
- 新增 `test_delete_idempotent` 第二次 DELETE→404 **強化**了與 SPEC「冪等→200」的偏差（測試與契約不一致，非放寬舊測）

---

## 總結

| 類別 | RESOLVED | PARTIAL | UNRESOLVED |
|------|----------|---------|------------|
| MAJOR (5) | 3 (#2,#4,#5) | 2 (#1,#3) | 0 |
| MINOR (4) | 3 | 0 | 1 (#2) |

**殘留阻塞（MAJOR）**：
1. **#1**：重複 DELETE（已成功刪除後）仍 404；TODO `冪等→200` 未滿足；測試固化 404
2. **#3**：manifest 存在分支缺 `resume_batch` 整合測（三分支驗收未齊）

```
ASSUMPTIONS_VERIFIED: git diff 2e0cef3..f6762bd 全檔閱讀；delete_run 邏輯與測試 L373-381 交叉驗證
TESTS_RUN: pytest tests/api/test_run_lifecycle_api.py -v → 14 passed; npm run test -- run_lifecycle → 5 passed
FAILURES_SEEN: none
SCOPE_CHANGES: none（review-only，未改程式）
NUMERIC_OR_SCHEMA_IMPACT: none（審查範圍內）
HANDOFF_NOT_UPDATED: 執行合約 — 複驗 review 寫 append-only handoffs，不重寫根 HANDOFF.md
```

STATUS: REQUEST_CHANGES — MAJOR #1 重複 DELETE 仍 404（違 TODO 冪等→200，測試亦固化）；MAJOR #3 manifest-exists 分支缺 resume_batch 整合測
