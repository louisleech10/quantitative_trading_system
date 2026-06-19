# T2 rereview — Codex

Scope: read-only rereview of fixes b533b37/27dd92b/ba046eb/9198963/99a6e10/27518dc against prior CHANGES REQUESTED.

Verdict: PASS. No remaining blocking findings found in the T2 fix set.

Checks:
- Issue A: `_process_item_wave` now calls `_compute_single(..., batch_id)`; batch test stubs in `test_feature_factory_batch_resume.py` and `test_feature_factory_batch_step4.py` accept `_batch_id`.
- #1 stale: `_clear_layer_metrics_on_task` pops `current_stage/stage_progress/current_rss_mb`; `_apply_layer_metrics_to_task` calls it for `concurrent_symbols != 1`, missing symbol/timeframe, missing layer file, and no matching symbol/timeframe row.
- #2 tick: layer tick is created before the wave body and canceled/awaited in `finally`; `CancelledError` is suppressed after await. Covers executor setup/scheduling/result/fallback exceptions and task cancellation after tick creation.
- #3 frontend: `normalizeBatchTask` no longer falls back to prior layer fields; omitted keys clear to null, explicit null clears, non-running or symbol/timeframe handoff clears.
- #4 mapper: mapper was extracted to `map_batch_progress_ws_data`; regression calls it and asserts exact mapped values, not source grep.

Tests run:
- `pytest tests/api/test_batch_status_layer.py tests/api/test_feature_factory_batch_resume.py -q` -> 25 passed, 1 warning.
- `cd frontend && npm run test -- featureFactoryStore.test.ts` -> 1 file / 7 tests passed.
- `git diff --check 83496c6..HEAD` -> pass.

Not fully run:
- `pytest tests/api/test_feature_factory_batch_step4.py -q` and the 3-file batch target both failed during collection because `api.main` imports trigger Binance ping and network/DNS is unavailable.

New issues:
- none found in reviewed T2 changes.

Notes:
- Existing worktree had `D dev_stack` and untracked handoffs before this rereview; left untouched.
