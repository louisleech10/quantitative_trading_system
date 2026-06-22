# B4c Re-review — Codex
Date: 2026-06-22
Scope: read-only re-review of cf5a318 + 4cf9762 against prior CHANGES REQUESTED.

Verdict: PASS.

Checks:
1. Active transition fixed: selectedRuns now filters `selectedKeys && !run.active`; excludedActiveRuns tracks stale active selections.
2. executeBulkDelete payload is built only from selectedRuns, so stale active runs are excluded at submit time.
3. Confirm dialog shows an amber excluded-active note with count and per-run identity before deletion.
4. Store test now calls real `bulkDeleteRuns` action and mocks fetch only; fixture contains a true duplicate and asserts deduped body.
5. Store test asserts bulk-delete POST URL/body, then refresh via `/runs` and `fetchBatchRetentionPending`.
6. Store tests call real `scanOrphans`/`cleanOrphans`; assert `/runs/orphans`, `/runs/orphans/clean`, and dry_run true/false bodies.
7. Single `deleteRun` path remains separate and unchanged; component bulk test asserts bulk delete does not call single delete.

Findings:
- No blocking findings.
- Non-blocking residue: component orphan test still has a test-local mocked store implementation, but production wiring is now covered by store-level tests.

Tests run:
- `cd frontend && npm run test -- RunManagerPanel.bulkDelete.test.tsx featureFactoryStore.test.ts --run` PASS, 2 files / 17 tests.

Impact:
- Numeric/schema/data_cache impact: none observed.
