# batch2d freeze fix handoff — 2026-06-16

## Scope
- Touched only `scripts/freeze_batch2d_baseline.py` plus generated `tests/_golden/batch2d/{control,cgsa_baseline,provenance}.json`.
- Did not edit production numerical logic, `data_cache/`, or `tests/golden/l65/test_inventory.txt`.

## Root Cause Verified
- Full orchestrator reproduced the silent stall in the control subprocess, not CGSA: non-CGSA control reached L6.5 after `dropping 15 ratio-unsafe columns` with classic frame path.
- Direct `--phase cgsa` and `python -c _run_cgsa(tempdir)` both completed; CGSA production/storage path stayed healthy.
- Control with fracdiff disabled took Polars before pandas chunking (`FFACT_USE_POLARS=1` default), bypassing `FFACT_L65_CHUNK_SIZE` and wedging/killing on the wide frame.

## Fix
- Freeze script now lazy-imports momentum modules so the parent orchestrator is light before spawning phases.
- Freeze phase subprocess env now defaults to `FFACT_USE_POLARS=0`, `FFACT_L65_CHUNK_SIZE=500`, `FFACT_L65_SLOWPATH_PARALLEL=0`, `FFACT_BATCH_NESTED=1`.
- Phase env explicitly sets `FFACT_USE_CGSA` and clears inherited `FFACT_CGSA_WORK_DIR` for control.

## P0 Result
- `python scripts/freeze_batch2d_baseline.py` completed exit 0.
- Generated: control `367 x 165268`, cgsa_baseline `367 x 165309`, provenance `202517` frame / `202517` CGSA / `202517` common, same-layer=true.

## Tests
- `PYTHONPYCACHEPREFIX=/tmp/codex_pycache python -m py_compile scripts/freeze_batch2d_baseline.py` passed.
- `pytest tests/feature_engineering/test_batch2d_dstar_align.py -q` passed: 7 passed.
- `pytest -k batch2d_golden -q` failed during unrelated API collection because sandbox network cannot resolve `api.binance.com`; no batch2d test failure observed.

## P4 Blocker
- Current `tests/feature_engineering/test_batch2d_dstar_align.py` has no P4 slow d*/value parity/control/CGSA regression tests; only 7 golden/map/filter/read-d* tests are collected.
- Direct frozen value inventory: expected L1/L2=46438; control present=37524 missing=8914; CGSA present=37557 missing=8881; common=37524; value_hash_mismatch=37524; nan_mask_mismatch=0; row_index_equal=false.
- Per exact-only rule, T4 is not exact; no tolerance or production change was attempted. T3 d* parity was not available from the current P4 test surface.

## Status
- BLOCKED for P4 split: implement/run actual T3 d* oracle and investigate T4 row-index/value mismatch as a separate approved scope.
