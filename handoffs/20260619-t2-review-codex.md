# T2 code review — Codex

Scope: read-only review of commits 83496c6, 0039a3f, ff7a87c against docs/FF_BATCH_OBSERVABILITY_SPEC.md and handoffs/20260619-t2-adv-codex.md.

Verdict: CHANGES REQUESTED. Core numeric path looks observational-only, but layer status lifecycle has a real stale-status bug; tests also miss tick cancellation and mapper behavior.

Findings:
1. HIGH / High confidence — 83496c6:api/services/feature_factory_batch_service.py:813-820 plus :466-470.
   `_apply_layer_metrics_to_task` returns without clearing `current_stage/stage_progress/current_rss_mb` when the current symbol/timeframe has no matching row. On the next queued item, `_process_item_wave` sets `current_symbol/current_timeframe` and immediately notifies before that child writes a row, so the previous symbol's layer can be shown under the new symbol. Fix: clear the three layer fields whenever symbol/timeframe changes, no match exists, file missing, or concurrent_symbols != 1; add a two-symbol sequential test.
2. HIGH / High confidence — 83496c6:api/services/feature_factory_batch_service.py:452-545.
   The periodic tick task is canceled only after the normal path exits the `with` blocks. Exceptions during executor setup, scheduling, result recording, fallback metrics append, or cancellation of `_process_item_wave` skip lines 540-545, leaving the tick task alive and repeatedly notifying. Fix: wrap the whole post-create section in `try/finally`; in finally set stop event, cancel, await/suppress `CancelledError`; add a test that injects an exception after tick creation and asserts no pending tick task.
3. MEDIUM / High confidence — ff7a87c:frontend/src/store/featureFactoryStore.ts:360-366.
   Normalize preserves prior layer fields when payload omits them or explicitly sends null (`?? previous`). This amplifies backend stale data and violates old-task/backward-compatible fallback: a later payload without layer fields can keep rendering an old layer. Fix: for layer fields, treat key presence/null as authoritative clear, or clear when current_symbol/current_timeframe changes/status is not running; add store-level regression.
4. MEDIUM / Medium confidence — 0039a3f:tests/api/test_batch_status_layer.py:140-148.
   WS mapper test is a source-string grep. It can pass if literals exist but the mapper drops/renames fields or sends wrong values. Fix: exercise the callback/mapper behavior with a fake manager or extracted mapper function and assert emitted JSON contains exact `current_stage/stage_progress/current_rss_mb` values.

Confirmed OK:
- 83496c6:momentum/FeatureEngineering/feature_factory.py:3494-3498 now fail-opens at `_report_progress`; callback exceptions should not cross layer boundary.
- 83496c6:_compute_single passes only a progress callback and writes O_APPEND jsonl; no observed diff to feature numeric computation path.
- 0039a3f + ff7a87c add Pydantic, WS whitelist, TS type, and Zustand fields; schema direction is consistent.
- Test diffs add coverage; no evidence of loosened existing assertions or skipped tests.
- Callback frequency reuses existing `_report_progress` layer/stage boundaries; no per-row heartbeat added.

Tests run by reviewer: read-only inspection only; no pytest/npm commands run.

