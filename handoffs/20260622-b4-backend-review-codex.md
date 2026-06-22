# B4 backend review — Codex — 2026-06-22

## Verdict
BLOCKED. Backend direction mostly matches SPEC v2.1, but 3 residual correctness gaps remain before accept.

## Findings
1. [BLOCKING][High] CGSA delete is fake-green under hermetic override. `run_lifecycle.py:137-140` skips CGSA deletion whenever `FFACT_CGSA_WORK_DIR` is set, yet B4 tests set it (`tests/api/test_b4_bulk_delete_orphan.py:112`). Result: normal bulk/single delete removes features+registry but leaves CGSA leaf with no error. Tmp repro: `features_exists=False,cgsa_exists=True,registry=None,skipped=['work_dir_override']`. This violates SPEC §C/§V artifact disappearance and makes bulk equivalence/hermetic tests miss tmp CGSA garbage.
2. [BLOCKING][High] B3 retention is marked `DISCARDED` before delete succeeds. `bulk_delete_runs` calls `retention_reconcile` before `delete_run` (`feature_factory_service.py:931-953`), while `mark_retention_discarded_for_run` persists terminal state immediately (`feature_factory_batch_service.py:1847-1852`). If delete later fails/partial, report says failed but checkpoint says DISCARDED.
3. [MAJOR][Medium] Reader hiding is incomplete. `list_runs` hides deleting (`feature_factory_service.py:811-816`), but `ensure_browse_task_for_run` uses `registry.get` and does not reject `entry['deleting']` (`feature_factory_service.py:837-855`); `FeatureRegistry.get` still returns deleting entries (`feature_registry.py:139-142`). SPEC §C/§V requires public get/list hidden during delete.

## Confirmed OK
- Shared lifecycle delete path exists for single/bulk/B3 discard via `delete_run -> _orchestrated_delete_locked -> mark_deleting_for_delete`.
- Force mark allows alias/batch_alias runs (`feature_registry.py:233-247`) and tests cover named bulk delete.
- Bulk endpoint returns HTTP 200 with per-run deleted/failed/skipped and continues after partial failure.
- Orphan scan includes features + CGSA leaves, validates CGSA manifest ownership, covers CGSA-only orphan, and excludes active/deleting.
- No observed d_star deletion or numeric/schema feature-output changes.

## Tests/Validation
- Reviewed commits `34b91d9` and `a03ca44` against `docs/B4_BULK_DELETE_SPEC.md` + two adversarial handoffs.
- Ran tmp-only repro for CGSA override residual; did not run full pytest.
- Wrote this handoff only; no source edits.

STATUS: BLOCKED — CGSA delete residual, premature B3 DISCARDED, incomplete reader hiding
