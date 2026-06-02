# Phase 3 — C2 parallel budget (Cursor)

## ASSUMPTIONS_VERIFIED
- `get_slowpath_n_jobs` tier caps from `_SLOWPATH_NJOBS_BY_TIER_GB` (8→2 but <12GB gate→1; 16→4; 32→8).
- Batch flag-off path preserved via `batch_nested_environment` still setting `FFACT_BATCH_NESTED=1` when `FFACT_PARALLEL_BUDGET` unset/off.
- Single-symbol path: no `FFACT_BATCH_SYMBOL_CONCURRENCY` → concurrent=1 → unchanged n_jobs at 16GB.

## TESTS_RUN
- `pytest tests/feature_engineering/preprocessing/test_slow_path_parallel.py tests/api/test_feature_factory_batch_resume.py -q` → 25 passed
- `./scripts/check_decoupling_phase4.sh` → PASS

## FAILURES_SEEN
- none

## SCOPE_CHANGES
- none

## NUMERIC_OR_SCHEMA_IMPACT
- Batch-only: `FFACT_PARALLEL_BUDGET` (default off), `FFACT_BATCH_SYMBOL_CONCURRENCY` env, RSS soft downgrade checkpoint field `rss_soft_limit_exceeded`. No output schema/size change.
