# Batch2 Run Lifecycle 實作交接

## Phase 0 完成
- 檔案：`momentum/FeatureEngineering/run_paths.py`、`run_locks.py`、`feature_registry.py`、`feature_factory.py`、`tests/feature_engineering/test_run_lifecycle.py`。
- 函式級：新增 `validate_config_hash`/`safe_token`/兩種 run path；新增 flock `RunLease`/`is_run_active`；registry 新增 `_locked_mutate`、merge-preserve、corrupt fail-closed、alias/remove/deleting；CGSA default path 委派。
- browse ID 斷言更新：本 Phase 無。
- size 寫入函式名：尚未進入 Phase 2。
- tests/api 基線：`123 items / 14 errors`，collection 因 sandbox 無網路時 Binance ping 失敗。

### Phase 0 測試輸出原文
```text
pytest tests/feature_engineering/test_run_lifecycle.py -k paths -q
1 passed, 7 deselected in 0.05s
pytest tests/feature_engineering/test_run_lifecycle.py -k locks -q
3 passed, 5 deselected in 1.50s
pytest tests/feature_engineering/test_run_lifecycle.py -k registry -q
4 passed, 4 deselected in 0.07s
pytest tests/feature_engineering/test_run_lifecycle.py -q
8 passed in 1.59s
```
- 過程失敗：locks 首輪 subprocess readiness busy-spin 未讓子程序排程；改 blocking stdout handshake 後通過，未使用 sleep。

## Phase 1 完成
- 檔案：`momentum/FeatureEngineering/run_lifecycle.py`、`momentum/factories.py`、`tests/feature_engineering/test_run_lifecycle.py`。
- 函式級：新增 `RunLifecycleManager.delete_run/_delete_run_locked/set_run_alias/auto_cleanup`、逐 component symlink/白名單驗證、ownership/override gate、per-(symbol,timeframe) singleflight；新增 `create_run_lifecycle_manager`。

### Phase 1 測試輸出原文
```text
pytest tests/feature_engineering/test_run_lifecycle.py -k 'delete or cleanup' -q
6 passed, 8 deselected in 0.08s
pytest tests/feature_engineering/test_run_lifecycle.py -q
14 passed in 1.58s
```
- 過程失敗：首輪 3 failed，原因為測試環境既有 `FFACT_CGSA_WORK_DIR` 與測試 mkdir 未 `exist_ok`；測試隔離修正後通過，production 未改。

## Phase 2 完成
- 檔案：`feature_factory.py`、`feature_factory_service.py`、`feature_factory_batch_service.py`、`feature_factory_models.py`、route、兩個 backend 測試檔及 2 個既有 browse assertion 檔。
- 函式級：generation/IC-first `lease_sink`；`_run_warmups_then_release`；`list_runs/set_run_alias/delete_run/_write_run_size`；runs routes；resume `_resolve_completed_run_hash/_completed_manifest_exists`。
- size 寫入函式名：`FeatureFactoryService._write_run_size`。
- browse ID 斷言更新：`test_feature_factory_batch_resume.py` 3 條（full hash 正向、legacy ID 無、get_result full hash）；`test_failopen_producer.py` 1 條（deadbeef full hash）。
```text
pytest tests/feature_engineering/test_run_lifecycle.py tests/api/test_run_lifecycle_api.py -q
19 passed in 2.30s
pytest tests/api/test_feature_factory_batch_resume.py tests/feature_engineering/test_failopen_producer.py -q
34 passed, 1 warning in 4.75s
```
- 過程失敗：batch helper 首次插入切斷 async method，compile() 發現後移至 method 尾端；既有 browse 舊格式 2 tests failed，依唯一例外更新 4 條斷言後通過。

## Phase 3 完成
- 檔案：`types.ts`、`featureFactoryStore.ts`、`GenerationProgress.tsx`、`RunRetentionDialog.tsx`、`RunManagerPanel.tsx`、page、`run_lifecycle.test.tsx`。
- 函式級：runs loading/empty/error state/actions、completion queue、WS/polling completion payload、三選 retention dialog、active/409/partial-aware manager。
```text
npm run test -- run_lifecycle
Test Files 1 passed (1); Tests 3 passed (3)
npm run build
Compiled successfully; static pages 20/20; exit 0
```
- 過程失敗：vitest 首輪 1 failed，測試 DOM 未 cleanup；加 afterEach cleanup 後 3 passed。

## Phase 4 完成
- tests/api 基線：`123 items / 14 errors`；收尾：`128 items / 14 errors`，紅數未增加，皆為 sandbox 無網路 Binance ping collection error。
- curl smoke：sandbox 禁止 localhost bind，原文 `[Errno 1] error while attempting to bind on address ('127.0.0.1', 8765): operation not permitted`；未執行真資料 mutation。

### 總 Gate 結果原文
```text
pytest tests/feature_engineering/test_run_lifecycle.py tests/api/test_run_lifecycle_api.py -q
19 passed in 3.18s
npm run test -- run_lifecycle
Test Files 1 passed (1); Tests 3 passed (3)
npm run build
Compiled successfully; Generating static pages (20/20); exit 0
pytest <第1批 7-file bundle> -q
78 passed in 205.92s (0:03:25)
pytest tests/api/ -q --tb=no
128 items / 14 errors; baseline 14 errors
grep -r 'from api\.' momentum/
0 results
```
- 補充回歸：`test_feature_factory_batch_resume.py + test_failopen_producer.py` 34 passed；`test_failopen_api_flags.py + lifecycle API` 9 passed；最終 lifecycle+API flags 23 passed。
- Golden inventory：工作樹與 HEAD SHA256 均 `94c08dda06f7aac81b434ef616e2d4b4ee56005e3d54aa2dd34c7c34336`。
- 數值/schema：不改數值、特徵輸出、checkpoint 寫入格式；新增 API DTO/欄位與 full-hash browse ID，registry 新增 alias/size_bytes/deleting 欄位。

## Code review 修復輪（2026-06-15）
- MAJOR 1：DELETE 不再於 registry miss 提前 404；有 features/CGSA artifact 時仍走 manager 冪等刪除回 200，原先 registry+磁碟全無才 404。
- MAJOR 2：`test_run_lifecycle_api.py` 新增真 ASGI async client，覆蓋 409 `run_busy`、404 `run_not_found`、422 `alias_conflict`、500 `delete_partial`、active DELETE 409→release→200、created_at 兩樣本 ISO regex、browse reconciliation。
- MAJOR 3：新增 tmp checkpoint 的 resume 三分支整合測試；path hash / browse full-hash 缺 manifest 均 assert `execute_resume` called，legacy 保留 completed 且 warning。
- MAJOR 4：新增真 `FeatureFactory.generate_features`+flock+barrier+HTTP DELETE 全鏈；同 hash 第二 generate busy、warmup 中 409、結束後 200；pass2 兩 full-hash browse task 並存。
- MAJOR 5：legacy HDF5 完成路徑改為 release 後 `auto_cleanup(..., 5)`；新增事件順序單測。
- MINOR 1：vitest 新增同 fixture 的 WS / polling completion queue 與 500 delete_partial errors 顯示。
- MINOR 2：registry 私有 API 耦合未列為本輪必修，未修改。
- MINOR 3：created_at numeric/ISO 兩樣本已由 HTTP list_runs 測試覆蓋。
- MINOR 4：pass2 註解改為 full config hash 並明記雙 run 共存。
- 額外修復：browse reconciliation 測試發現 `delete_run` 鎖內呼叫 `_invalidate_task_cache` 的非重入死鎖；改為鎖內移除 tasks、鎖外 invalidate。
- Debug 第 1 輪：完整 backend suite 停於 reconciliation；假設=鎖重入，證據=`_invalidate_task_cache` 再取 `self._lock`；上述鎖範圍修正後聚焦 8 tests passed。

### 修復輪最終驗收原文
```text
pytest tests/feature_engineering/test_run_lifecycle.py tests/api/test_run_lifecycle_api.py -q
28 passed in 2.24s

cd frontend && npm run test -- run_lifecycle
Test Files  1 passed (1)
Tests  5 passed (5)
Duration  1.15s

pytest <第1批 7-file bundle> -q
78 passed in 198.50s (0:03:18)
```
- `git diff --check`：0 errors；`rg "from api\." momentum`：0 results。
- Golden inventory：工作樹與 HEAD SHA256 均 `94c08dda06f7aac81b434ef616e2d4b4ee56005e3d54aa2dd34c7a43c7c34336`；未跑 collect-only，無 golden diff。
- `git diff --name-only -- data_cache/`：0 results；本輪未寫真 `data_cache/`。
- 防假綠：舊 warmup coordinator 與 resume resolver 斷言原樣保留；新增整合斷言，未降門檻。
- 本輪未 commit；根 `HANDOFF.md` 的既有修改未觸碰。
