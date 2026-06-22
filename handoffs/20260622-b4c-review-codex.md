# B4c Frontend Review — Codex
Date: 2026-06-22
Scope: read-only review of commit 3425989 vs docs/B4_BULK_DELETE_SPEC.md v2.1 Task3.1.

Verdict: CHANGES REQUESTED.

Findings:
1. Active transition gap: RunManagerPanel keeps selectedKeys when a selected run later becomes active; selectedRuns/executeBulkDelete can still send that active run. Evidence: RunManagerPanel.tsx:268-291 filters only existing keys, not `!run.active`; payload built at :335-340.
2. Anti-fake-green gap: B4c tests mock `useFeatureFactoryStore`, so bulk delete does not exercise the real `fetch` endpoint/body, store de-dupe, `fetchRuns`, or `fetchBatchRetentionPending`. Evidence: RunManagerPanel.bulkDelete.test.tsx:23-35, :79-122; store real behavior is at featureFactoryStore.ts:635-660.
3. Dedup claim not proven: test name says deduped payload, but fixture has no duplicate run and the real de-dupe lives in store, which is mocked. Evidence: RunManagerPanel.bulkDelete.test.tsx:79-122.
4. Orphan endpoint test mostly verifies test-local mock implementation, not production store wiring. Evidence: store mocked at :23-35; endpoint fetch is manually reimplemented in test at :244-257.

Spec checklist notes:
- Current UI has checkbox/select-all and disables currently-active rows; stale active after refresh remains a gap.
- Confirm dialog shows symbol/tf/alias/full hash/bytes/batch and totals for selected rows.
- Per-run deleted/failed/skipped rendering exists; backend/store endpoint wiring exists but B4c tests do not prove it.
- Orphan scan -> display -> confirm clean exists; endpoint proof is weak for same mock-store reason.
- Single deleteRun path remains separate; B4c does not modify it.

Tests run:
- `cd frontend && npm run test -- RunManagerPanel.bulkDelete.test.tsx RunManagerPanel.batchAlias.test.tsx --run` PASS, 2 files / 6 tests.
- Full vitest not run; known strategy-components.test failure treated as pre-existing per prompt.

Numeric/schema/data impact: none reviewed; no data_cache touched.
