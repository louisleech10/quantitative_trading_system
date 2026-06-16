# unify-run-explorer P1+P2 實作收尾（Composer）

## 範圍
- P1 後端橋接：`RunInfo` + `list_runs()` browse 欄位、`ensure_browse_task_for_run`、POST `/runs/{symbol}/{timeframe}/{config_hash}/browse`
- P2 前端單 Explorer：`FeatureExplorer` run 選擇器、`page.tsx` 單一 `<FeatureExplorer/>`、Coverage Matrix 改餵 `runsToRegistryEntries(runs)`

## ASSUMPTIONS_VERIFIED
- `browse_task_id` 穩定格式 `browse_{symbol}_{timeframe}_{config_hash}`（pytest `test_list_runs_includes_browse_metadata`）
- `browse_ready` = registry `hdf5_relative_path` 存在 **或** canonical `feature_manifest.json` 存在（manifest-only run 可 ensure）
- `ensure_browse_task_for_run` 第二次 POST 冪等、`_tasks` 不重複註冊（`test_ensure_browse_task_for_run_idempotent`）
- 無 artifact 時 ensure 回 404 `browse_not_ready`（`test_ensure_browse_task_not_ready_returns_404`）
- 既有 delete + browse reconciliation 未改動（`test_delete_idempotent_artifact_and_browse_reconciliation` 仍綠）
- `BatchTaskStatus` 批次 timeframe 欄位為 `current_timeframe`（非 `timeframe`），`pickDefaultRun` 已對齊

## TESTS_RUN
- `pytest tests/api/test_run_lifecycle_api.py -v` → **18 passed**
- `npm test -- --run src/lib/runExplorer.test.ts src/components/feature-factory/__tests__/FeatureExplorer.test.tsx src/components/feature-factory/__tests__/run_lifecycle.test.tsx` → **10 passed**
- `npm run build` → **pass**

## FAILURES_SEEN
- FeatureExplorer vitest 初版：`fetchRuns()` 覆寫空 runs、OverviewDashboard 缺 `quality`、Recharts 缺 ResizeObserver → 以 runs fetch mock + 子元件 stub + summary fixture 修正

## SCOPE_CHANGES
- none（未擴大 scope；舊 `/browse/*` 與 `/browse/register`、BatchQualityOverview、pass2 restore、delete reconciliation 均保留）

## NUMERIC_OR_SCHEMA_IMPACT
- API `RunInfo` 新增：`browse_task_id`, `browse_ready`, `browse_path`, `feature_count`, `row_count`, `quality_status`
- 新增 `EnsureBrowseResponse` + POST ensure 端點
- 前端 `RunInfo` / store `selectedRunKey` / `ensureBrowseTaskForRun` 對齊；page 移除批次第二 Explorer 塊

## 主要檔案
- `api/services/feature_factory_service.py` — browse metadata + ensure
- `api/routes/feature_factory.py` — ensure route
- `api/models/feature_factory_models.py` — DTO
- `frontend/src/components/feature-factory/FeatureExplorer.tsx` — 統一 run 選擇器
- `frontend/src/app/feature-factory/page.tsx` — 單 Explorer + coverage adapter
- `frontend/src/lib/runExplorer.ts` — `pickDefaultRun` / `runsToRegistryEntries`
- `tests/api/test_run_lifecycle_api.py` — browse 測試 +3
- `frontend/src/lib/runExplorer.test.ts`, `FeatureExplorer.test.tsx` — 新增

STATUS: DONE
