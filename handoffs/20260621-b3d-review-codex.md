# B3d frontend review — Codex
Date: 2026-06-21
Scope: read-only review of de12e2b (impl) + af0c467 (vitest) against docs/B3_BATCH_RETENTION_SPEC.md Task 4.1.

Verdict: PASS with one non-blocking hardening note.

Checked:
- completionQueue now stores `{...run, source}`; `enqueueCompletion(run)` defaults to `single`.
- Current single-symbol producer `GenerationProgress` still calls `enqueueCompletion(payload.run_identity)` and queues `source: single`.
- Batch retention does not use completionQueue in current producers; WS/REST update `batchTask.retention_pending`.
- RunRetentionDialog opens only when queue head is not `source: batch`.
- BatchRetentionPanel is one CollapsibleSection containing multiple pending items, not per-item modals.
- Retain/discard calls `POST /api/v1/features/batch/{batch_id}/retention/{symbol}/{timeframe}/{config_hash}` with `{decision}`.
- No frontend batch discard path calls store `deleteRun` or `DELETE /runs/...`.
- REST list补偿 exists on mount and when batchConnectionStatus becomes `lost`; WS pending merges through `applyBatchEvent`.
- Vitest added 5+ meaningful cases: render, retain URL/body, discard URL not DELETE /runs, empty hide, multi-item single panel + no modal, default source, retention_pending clear.

Findings:
- Non-blocking hardening: if a future bug enqueues a `source: batch` item at completionQueue[0], RunRetentionDialog returns `run=null` and does not shift/skip it, so later single items behind it would be starved. Current code has no batch enqueue producer, so this is not an active regression.

Tests run:
- `cd frontend && npm run test -- --run src/components/feature-factory/__tests__/BatchRetentionPanel.test.tsx src/store/featureFactoryStore.test.ts src/components/feature-factory/__tests__/run_lifecycle.test.tsx`
- Result: PASS, 3 files / 21 tests.

Residual:
- Did not run `npm run build` because this was requested as read-only review and build writes `.next`.
