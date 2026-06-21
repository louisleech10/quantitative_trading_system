# B3 Backend Rereview — Codex
Date: 2026-06-21
Scope: read-only rereview of `dbe5409` + `916d857` against prior fake-green findings.

Verdict: FAIL (narrow): #1/#2/#5 closed; #6 mostly improved but matrix is incomplete as requested.

Findings:
1. CLOSED #1 retain==today: test now uses same symbol/identity BTCUSDT/1h/cfg_batch_ret for flag-off baseline vs flag-on retain, and asserts registry_entry + browse_task_id + quality_summary equality.
2. CLOSED #2 discard browse: `retention_client_real_browse` wires `FeatureFactoryBrowseAdapter(ff_service)` and asserts `ff_service._tasks` plus `/browse/available` before/after removal.
3. CLOSED #5 flag-off schema: `dbe5409` gates checkpoint `retention_items` on `_is_batch_retention_enabled()`, and tests assert field absence.
4. PARTIAL #6 concurrency: added retain/retain, retain+discard, discard/discard; asserts single terminal for same-decision cases and no duplicate delete for discard/discard.
5. REMAINING #6 gap: no explicit discard+retain test/case; retain+discard uses scheduler race and only asserts one winner + <=1 delete, not both ordered mixed-decision cases as a deterministic matrix.

Residuals agreed:
- #3 crash reconcile remains B3c/pending; no `retention_crash` implementation/tests found.
- #4 real free-space backpressure/wakeup remains B3c/pending; no `shutil.disk_usage`/retention_backpressure path found.

Tests run:
- `source venv/bin/activate && pytest tests/api/test_batch_retention.py -q` => 19 passed.

Notes:
- No product code changed in this rereview.
