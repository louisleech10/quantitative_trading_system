# Unify Run + Feature Explorer Design

## Scope
- Read-only architecture design for unifying Feature Factory into one run concept and one Feature Explorer.
- No production code changed; no commit created.

## Verified Facts
- Registry source is `data_cache/features/registry.json` via `FeatureRegistry`; `/api/v1/features/runs` returns registry rows plus `active` and `size_bytes` (`api/services/feature_factory_service.py:654`).
- Browse source is the in-memory `_tasks` map; `/api/v1/features/browse/*` accepts `task_id`, and `/browse/available` lists completed `_tasks` only (`api/services/feature_factory_service.py:755`).
- Batch browsing creates virtual task ids through `register_hdf5_for_browse`; the stable id is `browse_{symbol}_{timeframe}_{config_hash}` (`api/services/feature_factory_service.py:776`).
- Restart restore pass2 scans `features/{symbol}/{timeframe}/{config_hash}/feature_manifest.json` and recreates the same stable browse id (`api/services/feature_factory_service.py:4042`).
- `page.tsx` renders one Explorer for `currentTask` (`frontend/src/app/feature-factory/page.tsx:527`) and a second Explorer inside batch symbol picker (`:581-582`).
- Batch page state keeps its own `selectedBatchSymbol`, `browseTaskIds`, and `/browse/register` fallback (`frontend/src/app/feature-factory/page.tsx:80-82`, `:194-210`).

## Target Model
- Canonical run key: `(symbol, timeframe, config_hash)`.
- Canonical list: registry-backed `/api/v1/features/runs`; old `/feature-registry/entries` can stay as compatibility or be internally backed by the same service.
- Browse id becomes a derived field, not a second run identity: `browse_task_id = browse_{symbol}_{timeframe}_{config_hash}`.
- A run is Explorer-ready when either registry `hdf5_relative_path` points to an existing manifest/artifact or `feature_manifest.json` exists under `features/{symbol}/{timeframe}/{config_hash}`.

## Backend Design
- Extend `RunInfo` and `list_runs()` with browse metadata:
  - `run_id` or `key`: `{symbol,timeframe,config_hash}`
  - `browse_task_id`
  - `browse_ready: boolean`
  - `browse_path` / `artifact_path`
  - `quality_status` if present in manifest
  - existing `feature_count`, `row_count`, `alias`, `size_bytes`, `active`, timestamps
- Add a small service method such as `ensure_browse_task_for_run(symbol,timeframe,config_hash)`.
  - Resolve artifact from registry `hdf5_relative_path` first, then canonical manifest path.
  - Reuse `register_hdf5_for_browse`; do not duplicate browse loaders.
  - Return the stable `browse_task_id`; idempotent if `_tasks` already has it.
- Add one endpoint only if eager registration is undesirable:
  - `POST /api/v1/features/runs/{symbol}/{timeframe}/{config_hash}/browse`
  - returns `{browse_task_id,browse_ready}`.
  - Prefer making `GET /runs` include `browse_task_id` and lazily register only on selection to avoid scanning every run.
- Keep `/browse/{task_id}/...` unchanged in Phase 1. Existing heavy browse/cache/warmup behavior remains isolated.
- Delete reconciliation already removes both canonical browse id and metadata-matched tasks on run delete (`api/services/feature_factory_service.py:702-713`); preserve that contract.

## Frontend Design
- `FeatureExplorer` owns run selection and has a single active `taskId`.
- Replace manual task-first UI with a registry run selector:
  - filters: symbol, timeframe, search/alias, status (`browse_ready`, active/deleting)
  - options show alias or `symbol / timeframe / config_hash`, feature count, created time
  - default selection priority: current completed run, current batch first completed symbol, latest registry run, recent run
- Page renders exactly one `<FeatureExplorer />`.
  - Remove batch `selectedBatchSymbol`, `browseTaskIds`, `registeringSymbol`, and the second Explorer block.
  - Batch quality UI can remain separate; batch browsing is just a filtered view of the same run selector.
- Store changes:
  - Replace `registryEntries`-only shape with typed `runs: RunInfo[]`.
  - Add selected run key + selected browse task id.
  - Keep recent task ids during migration, but store recent run keys going forward.
- `FeatureExplorer` selection flow:
  - Load `/api/v1/features/runs`.
  - When a run is selected, use returned `browse_task_id`; if absent or stale, call the new ensure endpoint.
  - Then use existing `browseSummary`, `browseFeatures`, `browse_*` calls unchanged.

## Compatibility And Risks
- `batchBrowse.ts` and `batchTask.browse_task_ids` are transitional; do not remove until live batch status no longer drives Explorer selection.
- `BatchQualityOverview` depends on batch checkpoints, not registry; keep it separate from Explorer unification.
- `SymbolCoverageMatrix` currently consumes registry entries; either feed it the same `runs` list or keep a thin adapter to avoid duplicate fetches.
- `_restore_persisted_tasks` pass2 remains important for direct `/browse/*` compatibility after API restart; do not remove in the first phase.
- Existing task records may lack `metadata.config_hash`; keep `_run_identity()` path fallback.
- `register_hdf5_for_browse` currently stores metadata without `config_hash`; adding it would improve identity consistency but should be covered by tests.

## Phased Plan
- Phase 0, contract tests: add backend tests for `/runs` browse metadata and idempotent ensure; add frontend tests for one Explorer render and registry-run selection.
- Phase 1, backend bridge: extend `RunInfo`, add `ensure_browse_task_for_run`, keep all old browse endpoints and `/browse/register`.
- Phase 2, frontend single Explorer: move run/symbol selector into `FeatureExplorer`; page renders one Explorer; batch mode filters/selects registry runs instead of owning a second picker.
- Phase 3, cleanup: remove page-level batch browse registration state and retire `batchBrowse.ts` after old batch payload support is no longer needed.
- Phase 4, consolidation: decide whether `/feature-registry/entries` becomes alias of `/features/runs` or is deprecated; keep `SymbolCoverageMatrix` on the unified run data.

## Open Decisions
- Whether `GET /runs` should eagerly register browse tasks or only expose `browse_ready` plus derived id. Recommendation: lazy ensure on selection.
- Whether UI primary grouping is `symbol -> timeframe -> run` or flat searchable run list. Recommendation: flat list with symbol/timeframe filters for single and batch consistency.
- Whether historical manual task id input remains as advanced fallback. Recommendation: keep one collapsed fallback during migration only.

STATUS: DONE - design and phased migration plan complete
