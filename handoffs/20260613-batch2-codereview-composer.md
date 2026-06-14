# Batch2 Run Lifecycle — Composer Code Review（跨家族複查）

- **Reviewer**: Composer 2.5（code review；實作者=Codex）
- **Range**: `git diff 0e2e2ca^..2e0cef3`（5 commits：P0–P4）
- **Contract**: `docs/BATCH2_RUN_LIFECYCLE_SPEC.md` V5 + `docs/BATCH2_RUN_LIFECYCLE_TODO.md` V5
- **Adversarial 對照**: `handoffs/20260613-batch2-adversarial-composer.md` + `...-r2.md`
- **抽驗**: `pytest tests/feature_engineering/test_run_lifecycle.py` → **14/14 passed**（1.64s）；`pytest tests/api/test_run_lifecycle_api.py` → **5/5 passed**；`npm run test -- run_lifecycle` → **3/3 passed**

## 總覽

P0–P1 核心（`run_paths` / `fcntl.flock` lease / registry transaction / `run_lifecycle` 安全刪除+cleanup）與 SPEC V5 設計對齊度高；競態測試用真 barrier + 跨進程 `kill -9`，非 sleep 假綠。P2–P3 路由與 service 接線已落地，但 **SPEC §V / TODO Task 2.2·2.3·3.1 要求的 HTTP/E2E 驗證覆蓋明顯不足**，且 **DELETE 冪等契約與 SPEC 不符**。既有測試斷言除已登記的 browse ID 字串外未見放寬。

## SPEC 9 Task 對照（實作忠實度）

| Task | 判定 | 備註 |
|------|------|------|
| 0.1 run_paths | ✅ | `validate_config_hash` / `safe_token` / 路徑委派；測試含病態 hash |
| 0.2 flock lease | ✅ | 無 unlink lock 檔；`kill -9` 子進程測試；8 執行緒 barrier 恰 1 勝 |
| 0.3 registry | ✅ | merge-preserve、corrupt 不落盤+copy、`RegistryLockTimeout` 獨立、`deleting`+`set_alias`→`RunBusyError` |
| 1.1 lifecycle | ✅ | 四步 lstat→resolve→is_relative_to→葉刪除；override/ownership；cleanup+deleting+lease |
| 2.1 lease_sink+browse | ⚠️ | CGSA 路徑 coordinator 唯一 release ✅；HDF5 路徑 release 無 `auto_cleanup`（見 MAJOR #5）；pass2/register 全 hash ✅；缺 pass2 雙 hash 共存測試 |
| 2.2 runs API | ⚠️ | route handler 碼齊（409/404/422/500）✅；`get_task_status` 擴充 ✅；**冪等 DELETE 實作錯**（見 MAJOR #1）；缺 HTTP 層測試 |
| 2.3 resume resolver | ⚠️ | 三級 resolver 靜態單元測試 ✅；`resume_batch` 重分類/requeue **無整合測試** |
| 3.1 frontend | ⚠️ | 三態 render + 409 保留 ✅；缺 WS/polling 雙路 dialog、delete_partial vitest |
| 4.1 整合 | ⚠️ | 新 momentum 測試全綠；未見 bundle 78 / tests/api 基線 / `npm run build` 於本輪 commit 內執行證據 |

## 防假綠（diff 既有斷言）

| 檔案 | 變更 | 判定 |
|------|------|------|
| `tests/api/test_feature_factory_batch_resume.py` | `browse_BTCUSDT_1h` → `browse_BTCUSDT_1h_abcdef1234567890`；舊短 ID 改期望 `None` | ✅ 已登記 browse full-hash |
| `tests/feature_engineering/test_failopen_producer.py` | `browse_BTCUSDT_12h` → `browse_BTCUSDT_12h_deadbeef` | ✅ fixture 對齊 full-hash |
| 其餘 `tests/` diff | 僅新增 `test_run_lifecycle*.py` | ✅ 無門檻放寬 |

## Findings

### BLOCKING

（無 — flock/刪除安全/registry fail-closed 未見可致資料錯誤或繞過 lease 的實作缺陷。）

### MAJOR

1. **DELETE 冪等契約違反 SPEC/TODO（重複刪除回 404 非 200）** — `api/services/feature_factory_service.py:664-665`  
   - `delete_run` 在呼叫 `manager.delete_run` 前若 `registry.get(...) is None` 即 `KeyError` → route `404 run_not_found`。  
   - `RunLifecycleManager.delete_run`（`run_lifecycle.py:70-77`）在 artifacts+registry 皆已清除後第二次呼叫可無錯誤返回（測試 `test_delete_removes_owned_leaves_and_registry` 直接測 manager 層冪等）。  
   - TODO Task 2.2 明列「**冪等→200**」；與現行 API 行為不一致。

2. **Task 2.2 HTTP 契約測試缺失** — `tests/api/test_run_lifecycle_api.py` 全程 `__new__` 直連 service，**未經** `async_client` 打 `/api/v1/features/runs/*`。  
   - 未覆蓋：409 `run_busy`、404 `run_not_found`、422 `alias_conflict`、500 `delete_partial` 字串；`active==true` 時 DELETE 409 / release 後 200；`created_at` ISO 轉換；刪除後 browse task reconciliation。

3. **Task 2.3 resume requeue 僅靜態 resolver，無 `resume_batch` 整合測試** — `tests/api/test_run_lifecycle_api.py:81-94`  
   - 實作於 `feature_factory_batch_service.py:175-190`（缺 manifest→requeue；legacy→warning 保留 completed）。  
   - SPEC 要求三分支各一測含 mock `assert_called` / caplog warning；**目前零整合覆蓋**。

4. **Task 2.1 驗收缺口（lease 全鏈）** — 缺：同 hash 第二趟 generate→failed 含 `"busy"`；生成/warmup 期間 HTTP DELETE→409→warmup 畢→200；pass2 兩 config_hash browse task 並存。  
   - 現有 `test_warmup_coordinator_holds_continuous_lease` 僅隔離測 coordinator + `is_run_active`，未接真實 generate/DELETE route。

5. **HDF5 非 CGSA 路徑 release 後未 `auto_cleanup`** — `api/services/feature_factory_service.py:281-284`  
   - `.json`（CGSA）走 `_run_warmups_then_release` → release 後 cleanup ✅。  
   - else（HDF5）直接 `lease_sink.pop().release()`，**無** `auto_cleanup`；與 TODO Task 2.1「無 warmup 路徑 → release+cleanup」不完全一致（若 HDF5 路徑仍為受支援產物，保留策略可能漏跑）。

### MINOR

1. **Frontend vitest 未達 SPEC 3.1 全文** — `frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx`  
   - 有：loading/empty/error/409、dialog 422。  
   - 缺：completion dialog **WS 路 vs polling 路**（同 fixture payload）；`delete_partial` errors 顯示；`RunManagerPanel` 對 500 的斷言。

2. **`_write_run_size` 直觸 registry 私有 API** — `api/services/feature_factory_service.py:705-709`（`registry._find_entry` / `_locked_mutate`）。行為可接受，但耦合私有欄位，後續 refactor 風險。

3. **`list_runs` created_at 轉換無單測** — 邏輯在 `feature_factory_service.py:648-654`（epoch→ISO、ISO passthrough、其他→null）；SPEC Task 2.2 要求兩樣本 regex 斷言，未見測試。

4. **pass2 註解仍提 hash8 legacy** — `feature_factory_service.py:4023-4024`（註解與 V5 full-hash 敘述略不一致；實作已用 `parts[2]` 全 hash）。

## 專項核對

| 檢查項 | 結果 |
|--------|------|
| flock 無 stale 殘留 / 不 unlink lock 檔 | ✅ `run_locks.py` 僅 `LOCK_UN`+close；無 `unlink` |
| 刪除安全四步順序 | ✅ `run_lifecycle.py:209-222` lstat 逐 component + resolve + is_relative_to |
| registry merge-preserve + corrupt fail-closed | ✅ + 測試 bytes 不變 |
| deleting 標記 + alias lease 互斥 | ✅ barrier 測試 `test_cleanup_alias_race_is_blocked_after_mark` |
| lease_sink + warmup coordinator 唯一 release | ✅ 實作 + 隔離 barrier 測試 |
| browse ID full-hash 全鏈 | ✅ register/pass2/batch adapter 委派；測試已更新 |
| resume 三級 legacy 保守 | ✅ resolver 單元測試；整合待補 |
| `grep -r "from api\." momentum/` | ✅ **0** |
| 競態真 barrier / 跨進程 flock | ✅ 非 sleep |
| 前端三態 render | ⚠️ 部分（見 MINOR #1） |

## 建議修復順序（給 Codex / 驗收）

1. 修正 `FeatureFactoryService.delete_run`：registry 已無 entry 時改走 manager 冪等刪除（或明確回 200 空結果），對齊 TODO「冪等→200」。  
2. 補 `tests/api/test_run_lifecycle_api.py` HTTP 層用例（或獨立 `test_runs_routes.py`）覆蓋四碼 + active/DELETE 一致性。  
3. 補 `resume_batch` 三分支整合測試（tmp checkpoint + 刪 manifest / legacy caplog）。  
4. 補 lease 全鏈：busy 第二 generate、warmup 期 DELETE。  
5. 視產品是否仍支援 HDF5：else 分支補 `auto_cleanup` 或文件化例外。  
6. 前端 vitest 補 WS/polling/delete_partial（可與 store `applyPayload` 共用 fixture）。

```
ASSUMPTIONS_VERIFIED: git diff 0e2e2ca^..2e0cef3 全檔閱讀；pytest run_lifecycle 14/14；decoupling grep=0；run_locks 無 unlink
TESTS_RUN: pytest tests/feature_engineering/test_run_lifecycle.py -v (14 passed); pytest tests/api/test_run_lifecycle_api.py (5 passed); npm run test -- run_lifecycle (3 passed)
FAILURES_SEEN: none in executed suites
SCOPE_CHANGES: none（review-only，未改程式）
NUMERIC_OR_SCHEMA_IMPACT: browse task_id schema 變更為 full-hash（已登記）；API DELETE 冪等語義與 SPEC 不一致（應修）
HANDOFF_NOT_UPDATED: code review 唯讀任務，根 HANDOFF 由 Claude 維護
```

STATUS: REQUEST_CHANGES — DELETE 冪等 404 vs SPEC 200；Task 2.2/2.3/2.1/3.1 驗證覆蓋未達 SPEC §V（實作主幹可用，驗收不足）
