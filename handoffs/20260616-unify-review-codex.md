# Unify Run Explorer Review — Codex

## Scope
- Reviewed Composer #4/#6 implementation against `handoffs/20260616-unify-run-explorer-design-codex.md`.
- Inspected backend bridge, frontend single Explorer, store/types/lib helpers, and new tests.
- No `api/` or `frontend/` files were modified.

## Findings

### MAJOR
- `frontend/src/lib/runExplorer.ts:41-52` and `frontend/src/components/feature-factory/FeatureExplorer.tsx:125-129`: default run selection is not faithful for completed batch/current run priority. `pickDefaultRun()` maps a completed batch to the first `browse_ready` run with matching `symbol + timeframe`, ignoring `batchTask.browse_task_ids`, output path/config hash, and any concrete run identity. If several runs exist for the same symbol/timeframe, registry order can select an older run. Also, the default-selection effect exits whenever `selectedRunKey` is already set, so a newly completed current/batch run does not take priority once the Explorer has auto-selected a previous registry run. This violates the P2 contract that the run selector defaults to current completed run / current batch first completed symbol and that selection should use the run's `browse_task_id` or ensure path for that run.

### MINOR
- None found.

### BLOCKING
- None found.

## Contract Checks
- P1 backend mostly faithful: `RunInfo` includes `browse_task_id = browse_{symbol}_{timeframe}_{config_hash}` and `browse_ready`; ensure is idempotent and reuses `register_hdf5_for_browse`; old browse routes and `/browse/register` were not changed; delete reconciliation contract remains.
- P2 frontend partially faithful: page now renders one `FeatureExplorer`, batch second block and page-level `selectedBatchSymbol`/`browseTaskIds` were removed, selector has flat search and symbol/timeframe filters. Default selection has the MAJOR issue above.
- Anti-fake-green: no skip/xfail/only found in touched tests; existing backend lifecycle assertions remain present; `_restore_persisted_tasks` pass2 and `_run_identity` fallback remain intact.
- Correctness: lazy ensure does not invoke browse loaders for every run; `SymbolCoverageMatrix` still receives adapted run entries.

## Validation
- `pytest tests/api/test_run_lifecycle_api.py -q` — 18 passed.
- `cd frontend && npm run test -- FeatureExplorer runExplorer run_lifecycle` — 3 files passed, 10 tests passed.
- `cd frontend && npm run build` — passed; existing hook dependency warnings reported in `FeatureTable.tsx`, `GenerationProgress.tsx`, and `RegimeClusterChart.tsx`.
- Real-path smoke: `ensure_browse_task_for_run()` plus `browse_summary()` on an existing BTCUSDT/12h registry run returned `browse_BTCUSDT_12h_87102c0d57c22538eeb07d27aed059cc` and summary `209122` features / `1696` rows.

STATUS: REQUEST_CHANGES
