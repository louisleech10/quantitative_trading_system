# B4 backend fix — Composer — 2026-06-22

## Scope
Codex review 3 residual defects (`handoffs/20260622-b4-backend-review-codex.md`). Orchestration / force mark / orphan logic untouched.

## Fixes

### #1 CGSA delete fake-green (BLOCKING)
- **Problem**: `b4_client` set `FFACT_CGSA_WORK_DIR` → `run_lifecycle._delete_run_locked` skipped CGSA deletion (`work_dir_override`); tests never asserted CGSA leaf removal.
- **Fix**: Removed env override from `b4_client`; isolation via `RunLifecycleManager(cgsa_root=tmp/...)` only (same pattern as `test_batch_retention.py`).
- **Tests**: `test_bulk_delete_removes_cgsa_leaf` asserts CGSA leaf gone; `test_bulk_delete_equiv_*` also checks CGSA paths.

### #2 B3 DISCARDED too early (BLOCKING)
- **Problem**: `bulk_delete_runs` called `retention_reconcile` (→ `mark_retention_discarded_for_run`) before `delete_run`; checkpoint could show DISCARDED while delete failed.
- **Fix**: Capture `batch_id` pre-delete; call `retention_reconcile` only in the success (`deleted`) branch after `delete_run` completes without errors.
- **Test**: `test_bulk_delete_failed_retention_stays_pending_B3CONC` — simulated `rmtree` failure → `failed` report + retention stays `PENDING`.

### #3 Reader hiding incomplete (MAJOR)
- **Problem**: `list_runs` hid `deleting`, but `FeatureRegistry.get` and `ensure_browse_task_for_run` still exposed deleting entries.
- **Fix**: Public `get()` returns `None` for `deleting`; new `get_internal()` for orphan scan / internal callers. `run_lifecycle.scan_orphans` leaf path uses `get_internal`. `ensure_browse` uses public `get` → 404 during delete.
- **Test**: `test_ensure_browse_hidden_during_deleting` — 404 `run_not_found` while `_delete_run_locked` paused.

## Validation
```
pytest tests/api/ -k "bulk_delete or orphan_cleanup or B3CONC" -v   # 17 passed
pytest tests/feature_engineering/test_run_lifecycle.py -v             # 16 passed
```
Hermetic: `test_b4_hermetic_data_cache_diff_empty` — before/after `data_cache` file-set identical.

## Commits
- `fix:` production (registry get split, bulk_delete reconcile order, orphan get_internal)
- `test:` B4 hermetic CGSA + retention-fail + browse-hide tests

ASSUMPTIONS_VERIFIED: CGSA delete runs when manager.cgsa_root isolated without FFACT_CGSA_WORK_DIR; retention DISCARDED only after delete success; public get hides deleting while list_all/get_internal preserve orphan protection.
TESTS_RUN: pytest tests/api/ -k "bulk_delete or orphan_cleanup or B3CONC" (17 pass); test_run_lifecycle (16 pass)
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
