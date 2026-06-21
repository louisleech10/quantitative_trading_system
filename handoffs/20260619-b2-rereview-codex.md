# B2 progress unify rereview — Codex

Scope: read-only rereview of fixes `1c236eb` and tests `98b78e7` against prior 3 BLOCKING findings in `handoffs/20260619-b2-review-codex.md`.

Verdict: PASS for the 3 original blockers; 1 new non-blocking regression risk found.

Findings:
1. Original #1 fixed. `normalize_progress_event()` now defaults absent/invalid `schema_version` to `0`; new single/batch emitters pass `schema_version=1`; legacy jsonl without schema_version maps task schema_version to `0`.
2. Original #2 fixed. `BatchProgressPanel` Vitest now expects the new `· (批)worker RSS 768MB` label; this aligns with UI semantics rather than weakening the assertion.
3. Original #3 fixed in field shape. Single completed/failed callback payloads now route through `normalize_progress_event()` and include `schema_version`, `process_rss_mb`, and `current_rss_mb`.
4. New issue: successful terminal payload uses `stage="completed"`, but `_STAGE_PATTERN` only allows `complete`; actual callback payload is normalized with `error_class="invalid_stage"`. Failed terminal payload is clean. No direct UI break observed, but this is a schema/noise regression risk and lacks a terminal-success regression test.

Tests run:
- `pytest tests/api/test_ff_progress_normalize.py tests/api/test_batch_progress_normalize.py tests/api/test_progress_rss_fields.py -q` → 19 passed.
- `cd frontend && npm test -- src/components/feature-factory/__tests__/BatchProgressPanel.test.tsx src/store/featureFactoryStore.test.ts` → 2 files / 11 tests passed.
- Ad-hoc `_run_task` callback script: success terminal payload contains schema/RSS but `error_class=invalid_stage`; failure terminal payload contains schema/RSS and `error_class=none`.

Scope changes: none; no product/test files changed.
Numeric/schema impact: review only; observed schema regression risk on `completed` terminal progress event error_class.

STATUS: DONE
