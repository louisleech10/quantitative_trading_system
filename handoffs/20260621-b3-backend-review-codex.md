# B3 Backend Core Review — Codex

Date: 2026-06-21
Scope: read-only review of `f1d904a` impl + `ef46757` tests against `docs/B3_BATCH_RETENTION_SPEC.md` v2.1 and Codex adversarial handoffs.

Verdict: CONDITIONAL FAIL for full B3 backend readiness. B3a/B3b direction is mostly right, but tests leave fake-green holes and B3c/crash reconcile remain explicit residuals.

Findings:
1. MAJOR: `retain==今日` test is not equivalent. `tests/api/test_batch_retention.py:480-522` compares ETH flag-off to SOL flag-on, has self-comparison at line 518, only checks grade + non-empty registry. It does not prove same identity registry entry + browse_task_id + quality summary.
2. MAJOR: discard "browse gone" test does not touch real browse downstream. `retention_client` injects `MockBrowseRegistrar` (`tests/api/test_batch_retention.py:73-77`), then test only asserts file missing + `list_runs()` absence (`:318-349`), not `FeatureFactoryService._tasks`/browse endpoint removal.
3. MAJOR: crash reconcile is not implemented. No `retention_crash` tests; `resume_batch` only requeues missing manifests from `completed_items` (`api/services/feature_factory_batch_service.py:212-234`) and never reconciles registered-but-not-pending or deleted-before-discarded retention states.
4. MAJOR: B3c free-space backpressure/wakeup is not implemented in these commits. No `shutil.disk_usage`, no `retention_backpressure`, no hard-pause/wakeup path; Composer handoff also marks B3c pending.
5. MEDIUM: flag-off is not "today schema" exact. `_build_initial_checkpoint` always writes `retention_items: []` (`api/services/feature_factory_batch_service.py:966-972`); test only checks empty value (`tests/api/test_batch_retention.py:279-282`), not field absence.
6. MEDIUM: atomicity is process-local lock, not checkpoint/file CAS. `_retention_locks` is in-memory (`api/services/feature_factory_batch_service.py:131-132`); test covers only retain/discard once (`tests/api/test_batch_retention.py:423-462`), not retain/retain, discard/discard, restart, or multi-process.

Confirmed OK:
- Post-hoc mark is not delayed: browse register stays before pending mark (`api/services/feature_factory_batch_service.py:647` then `:677-691`); `FeatureRegistry.add` path not touched.
- Discard wrapper keeps public `delete_run`/route semantics: decision layer catches `KeyError` only in batch path (`:1706-1708`); public DELETE still maps KeyError to 404.
- `run_deleter` is injected into `FeatureFactoryBatchService`; no direct import from batch service to feature factory service.

Residuals:
- B3c: real free-space backpressure + wakeup + hard-pause.
- Crash matrix/reconcile needs either B3c scope or explicit B3b follow-up before full B3 signoff.
- Frontend B3d not reviewed here; only TS types changed.
