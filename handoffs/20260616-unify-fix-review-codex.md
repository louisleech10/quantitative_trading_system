# Unify Run Explorer Fix Review — Codex Round 2

## Scope
- Reviewed only the prior MAJOR from `handoffs/20260616-unify-review-codex.md`.
- Inspected `runExplorer.ts`, `FeatureExplorer.tsx`, store/type changes, and new/changed tests.
- Did not modify `frontend/`; this file is the only write.

## Verdict
- APPROVE: MAJOR(a) is closed. `pickDefaultRun()` now prefers concrete identity: completed `currentTask.run_identity`, then `batchTask.browse_task_ids` via exact `browse_task_id`/parsed `symbol|timeframe|config_hash`, then output-path fallback. It no longer chooses the first browse-ready run by only `symbol + timeframe`.
- APPROVE: MAJOR(b) is closed. `FeatureExplorer` no longer exits merely because `selectedRunKey` is set; auto selection can replace an older auto-selected run when a completed current/batch run appears. Manual dropdown selection sets `selectionSourceRef` to `manual`, and the auto effect respects it.

## Test Quality
- `runExplorer.test.ts` is non-vacuous for multi-run same symbol: two BTCUSDT/12h runs differ only by `config_hash`; batch `browse_task_ids` points to `cfg_new`; old symbol+timeframe-first behavior would select `cfg_old` and fail.
- `FeatureExplorer.test.tsx` is non-vacuous for auto override: state starts at `selectedRunKey=cfg_old`, then completed batch points to `cfg_batch2d`; old `selectedRunKey` guard would keep `cfg_old` and fail. Manual selection test separately proves user-selected ETH is preserved after batch completion.
- No `.skip`, `.only`, `xfail`, or assertion weakening found in touched tests; diff shows added assertions only for the reviewed area.

## New Risk Check
- No new blocking issue found in the reviewed surface. The selection source is component-local, so persisted selected keys are treated as auto after remount; acceptable for this MAJOR because the required distinction is runtime auto vs user manual interaction.

ASSUMPTIONS_VERIFIED: batch/default selection now uses concrete run identity; selectedRunKey no longer blocks new completed auto default; manual dropdown selection remains respected; tests would fail under the old reviewed bug.
TESTS_RUN: `cd frontend && npm run test -- runExplorer FeatureExplorer run_lifecycle` => 3 files passed, 14 tests passed; `source venv/bin/activate && pytest tests/api/test_run_lifecycle_api.py -q` => 18 passed.
FAILURES_SEEN: none.
SCOPE_CHANGES: none; review-only, wrote only this handoff report.
NUMERIC_OR_SCHEMA_IMPACT: reviewed frontend/API run metadata schema additions only; no numeric computation/output-size change in this review.
STATUS: APPROVE
