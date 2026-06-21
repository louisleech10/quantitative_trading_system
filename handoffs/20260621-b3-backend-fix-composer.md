# B3 Backend Review Fix — Composer

Date: 2026-06-21  
Scope: Codex review findings #1/#2/#5/#6 only (no #3 crash reconcile, no #4 backpressure).

## Fixes (4)

### #5 flag-off checkpoint schema
- **Was fake-green**: `_build_initial_checkpoint` always wrote `retention_items: []`; test only checked empty list.
- **Change**: `retention_items` key written only when `FFACT_BATCH_RETENTION` enabled.
- **Now real**: `test_retention_state_flag_off_checkpoint_omits_retention_items` asserts key **absent**; spy test asserts `"retention_items" not in checkpoint` after batch.

### #1 retain==今日 equivalence
- **Was fake-green**: ETH flag-off vs SOL flag-on; line-518 self-compare; grade + non-empty registry only.
- **Change**: Same `BTCUSDT/1h/cfg_batch_ret` twice — flag-off baseline then flag-on + retain; compare `registry_entry` + `browse_task_id` + `quality_summary` via `_identity_snapshot`.
- **Now real**: `retention_client_real_browse` + `FeatureFactoryBrowseAdapter`; three fields asserted `==` (not cross-symbol, not tautology).

### #2 discard browse downstream
- **Was fake-green**: `MockBrowseRegistrar`; only manifest missing + `list_runs()`.
- **Change**: Real browse path; patch router `feature_factory_service` to isolated `ff_service`; assert `browse_task_id not in ff_service._tasks` and `/browse/available` empty after discard.
- **Now real**: Pre/post HTTP on browse endpoint + in-memory `_tasks` eviction.

### #6 concurrency matrix
- **Was fake-green**: Only retain vs discard pair.
- **Change**: Added `test_retention_concurrent_retain_retain_single_terminal`, `test_retention_concurrent_discard_discard_single_delete`; retain/discard spy counts `delete_run` ≤1.
- **Now real**: Terminal count ==1; discard/discard `delete_run` calls ==1; retain/retain `delete_run` ==0.

## Verification

```
pytest tests/api/ -k "retention_state or retention_decision or retention_retain or retention_discard or retention_concurrent or retention_flag_off or retention_list or retention_nonblock" -v
# 19 passed, 293 deselected

python scripts/build_l65_golden_baseline.py --check
# PASS (6 symbol×tf stable)
```

## Commits

- `fix:` flag-off omits `retention_items` from initial checkpoint
- `test:` B3 retention real downstream + concurrency matrix

## Residual (unchanged, B3c)

- #3 crash reconcile
- #4 free-space backpressure/wakeup
