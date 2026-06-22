# B8 review — Codex read-only
Date: 2026-06-22
Scope: docs/B8_BATCH_SCALE_UX_SPEC.md v1.1 + commits 0ae47b0,e437b59,ecd2f1c,ccf3df8,a991cac,8f7d5b7

Verdict: PASS

Findings:
- BLOCKING: none
- MAJOR: none
- MINOR: none

Checks:
- bulk retention loops through apply_retention_decision at api/services/feature_factory_batch_service.py:1818-1846.
- opposite terminal is failed + retention_conflict, not skipped, via RetentionConflictError handling at :1866-1882.
- BatchRetentionBulkResponse schema includes per-item identity/status/state/error/code in api/models/feature_factory_models.py.
- B8 tests cover retain==individual, discard real delete/browse absence, opposite terminal, same-terminal idempotent, not-found skipped, one failure continues, and bulk×single concurrency.
- RunManager uses independent bulkDeleteTarget(mode selection|batch) and execute reads targetRuns, not selectedRuns.
- real-store batch-delete test selects batch A, deletes batch B, asserts dialog/payload only B and A selection remains.
- BatchRetentionPanel retain-all has no confirmation; selected/all discard uses confirm dialog.
- Store tests use real Zustand store + mock fetch for bulk retention and bulk delete endpoint/body/refresh.
- Existing RunManager tests for selection bulk delete, active exclusion, single delete lifecycle, and batch alias/grouping still pass.

Tests run:
- source venv/bin/activate && pytest tests/api/test_batch_retention.py -k 'bulk_retention' -v --tb=short → 8 passed
- cd frontend && npm run test -- BatchRetentionPanel RunManagerPanel.batchDeleteWhole featureFactoryStore --run → 23 passed
- cd frontend && npm run test -- RunManagerPanel.bulkDelete RunManagerPanel.batchAlias run_lifecycle --run → 14 passed

Residual:
- Full frontend suite not run because known pre-existing strategy-components.test failure remains outside B8.
- Concurrent bulk×single test asserts final single-terminal safety; exact winner-branch response is supported by code + non-concurrent conflict/idempotency tests but not exhaustively split by scheduler branch.

STATUS: DONE
