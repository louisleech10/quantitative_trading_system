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
