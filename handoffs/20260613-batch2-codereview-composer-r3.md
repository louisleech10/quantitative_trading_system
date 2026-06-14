# Batch2 Run Lifecycle — Composer Code Review R3（終確認）

- **Reviewer**: Composer 2.5（R3 終確認；協調者修復 `1d453c4`）
- **Range**: `git diff f6762bd..1d453c4`
- **對照**: R2 `handoffs/20260613-batch2-codereview-composer-r2.md`（2 PARTIAL MAJOR → REQUEST_CHANGES）

## 變更摘要（1d453c4）

| 檔案 | 變更 |
|------|------|
| `tests/api/test_run_lifecycle_api.py` | +`test_resume_batch_retains_completed_item_with_present_manifest`；DELETE 重複測試加 SPEC [B2-6] 註解 |
| `docs/BATCH2_RUN_LIFECYCLE_TODO.md` | L95「冪等→200」澄清為 SPEC [B2-6] 完整語義 |
| `handoffs/20260613-batch2-codereview-composer-r2.md` | R2 報告入庫 |

**程式行為**：`api/services/feature_factory_service.py` 本輪無 diff；DELETE / resume 邏輯與 `f6762bd` 相同。

---

## MAJOR #3 — manifest-exists 分支 resume_batch 整合測

**R2 缺口**：僅 `test_resume_hash_resolver_three_branches` 靜態測 `_completed_manifest_exists`；無 `resume_batch` 端到端。

**R3 核對**：`test_resume_batch_retains_completed_item_with_present_manifest`（L467-497）

| 驗收點 | 覆蓋 |
|--------|------|
| 碟上 manifest 存在 | ✅ `run_dir/feature_manifest.json` 實體寫入 |
| 不 requeue | ✅ `queued_items == 0`；`completed_items` 保留（`skipped_items == 1`） |
| status completed | ✅ `response["status"] == "completed"` |
| execute 不呼叫 | ✅ `execute_mock.assert_not_called()` |

與 `resume_batch` 路徑（`feature_factory_batch_service.py:183-207`）一致：hash 可解析 + manifest 存在 → `retained_completed` → `queued_items==0` → 早退 completed，不進 `execute_resume`。

**三分支整合測現況**（對齊 TODO Task 2.3 §驗證）：

| 分支 | 測試 |
|------|------|
| manifest 缺失 → requeue | `test_resume_batch_requeues_missing_resolved_run` |
| legacy 無 hash → warning 保留 | `test_resume_batch_keeps_legacy_completed_item` |
| manifest 存在 → 保留 completed | `test_resume_batch_retains_completed_item_with_present_manifest` ✅ 新增 |

**判定: RESOLVED**

---

## MAJOR #1 — DELETE 重複 404 vs 冪等語義

**R2 判定**：重複 DELETE（registry+artifact 皆無）→404，與 TODO 簡寫「冪等→200」衝突。

**協調者裁定（1d453c4）**：
- SPEC [B2-6] / TODO L95 澄清：**冪等**指「磁碟孤兒 + registry 有 → 200 清 entry」；**registry 與 artifact 皆無 → 404 `run_not_found`**（含已成功刪除後重複 DELETE、從未存在）。
- 測試 `test_delete_idempotent_artifact_and_browse_reconciliation` L379-382 加註解，明確將第二次 DELETE→404 標為 SPEC 合意行為，非偏差。

**實作交叉驗證**（`feature_factory_service.py:672-685`，未改）：

| 情境 | 行為 | 對齊澄清後契約 |
|------|------|----------------|
| 僅 artifact、無 registry | 200 | ✅ |
| 首次 DELETE（有資源） | 200 + reconciliation | ✅ |
| 重複 DELETE（皆已清） | 404 `run_not_found` | ✅（澄清後契約） |
| 從未存在 | 404 | ✅ |
| manager 層第二次 `delete_run` | 無 errors（`test_run_lifecycle.py:174`） | ✅ 引擎層仍冪等；API 層用 pre-check 區分「有可刪對象」vs「皆無」 |

**REST 語義評估（404-on-repeat-delete）**：

- HTTP DELETE 的冪等性指**最終狀態**一致（資源不存在），非必須每次回相同 status code。
- 重複 DELETE 回 404 `run_not_found` 與「從未存在」共用語義，客戶端可統一處理為「此 triple 無可管理 run」——與 list/delete 契約一致，且避免對空 triple 回 200 造成「假成功」監控噪音。
- R1 真實缺陷（**有 artifact 無 registry 卻 404**）已在 `f6762bd` 修復；R2 殘留項本質是 TODO 簡寫歧義，非實作錯誤。
- **裁定可接受**：澄清後 SPEC/TODO/測試/實作四方一致；404 重複刪除屬合理 REST 設計，不構成驗收阻塞。

**判定: RESOLVED（契約澄清，非程式回歸）**

---

## R2 殘留非阻塞項

| 項 | 狀態 | 備註 |
|----|------|------|
| MINOR #2 `_write_run_size` 私有 registry API | UNRESOLVED | 本輪未觸及；不影響 Batch2 MAJOR 驗收 |

---

## 防假綠

- `git diff f6762bd..1d453c4 -- tests/`：**僅新增** manifest-exists 整合測 + 註解；無刪除/放寬既有 assert
- 第二次 DELETE→404 斷言保留，現有 SPEC 註解標明為合意契約（非 R2 所稱「固化偏差」）

---

## 測試

```
pytest tests/api/test_run_lifecycle_api.py -k resume -v → 5 passed
pytest tests/api/test_run_lifecycle_api.py -v → 15 passed
```

```
ASSUMPTIONS_VERIFIED: git diff f6762bd..1d453c4 全檔閱讀；新測試與 resume_batch:168-207、delete_run:672-685 交叉驗證；TODO L95 澄清已讀
TESTS_RUN: pytest tests/api/test_run_lifecycle_api.py -k resume -v → 5 passed; pytest tests/api/test_run_lifecycle_api.py -v → 15 passed
FAILURES_SEEN: none
SCOPE_CHANGES: none（review-only，未改程式）
NUMERIC_OR_SCHEMA_IMPACT: none（審查範圍內；DELETE 語義為文件澄清，行為與 f6762bd 相同）
HANDOFF_NOT_UPDATED: 執行合約 — review 寫 append-only handoffs，不重寫根 HANDOFF.md
```

STATUS: APPROVE — MAJOR #3 manifest-exists 整合測已補齊；MAJOR #1 協調者 SPEC [B2-6] 裁定可接受（TODO/測試/實作一致，404-on-repeat-delete 合理）
