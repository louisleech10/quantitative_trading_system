# B6 Backend Fix #2 — Composer (re-review test fidelity)

Date: 2026-06-22 | Scope: tests only (no product code)

## Re-review defects addressed

### #1 MAJOR — CGSA validate hollow test
**Root cause**: `test_warmup_trim_cgsa_validate` manually ran L3-L6 with wrong args (layer1 passed as layer2), omitted `factory._current_timeframe`, and used 60d window → registry stayed empty (`groups=0 total_features=0`).

**Fix**:
- Added `_run_cgsa_l1_l6_into_registry()` mirroring `generate_features` CGSA L1-L6 (correct layer wiring, `_current_symbol`/`_current_timeframe`, ingest via `_layer0_ingest_start_date_for_tf`, `_persist_single_tf_l3_l6_to_cgsa`).
- Test now asserts `group_count > 0` and `total_features > 0` before validate.
- Uses 90d window (same as `test_warmup_trim_cgsa_raw`).
- After `_layer7_validate_and_persist`: `len(features_df) == ingest-axis expected_rows`, first row at `output_start`, manifest `row_count` when present.

**Measured**: registry **7 groups / 25 features** pre-validate; parquet persist log `groups=1 npy_freed=7 total_features=25` (V7 compaction of 7 npy groups).

### #2 MINOR — IC-first window init via public API
**Root cause**: `test_warmup_trim_ic_first` used `_assert_warmup_trim_artifact(ic_first=True)` which caller-sets `_current_output_window` before `run_ic_first`.

**Fix**: Added `test_warmup_trim_ic_first_public_window_init`:
1. Public `generate_features(...)` → asserts `_current_output_window.warmup_enabled` + trim row_count.
2. Public `run_ic_first(...)` on same factory **without** manually setting window → asserts same `expected_rows` + trimmed first row.

## Hermetic self-proof
- All integration tests use `_isolate_feature_output` (tmp `features` + `FFACT_CGSA_WORK_DIR`) + `_assert_data_cache_unchanged` (production `data_cache/features` snapshot).
- Full suite run before/after: `find data_cache/features -type f | md5` unchanged.

## Verification
```
PYTHONDONTWRITEBYTECODE=1 pytest tests/feature_engineering/test_b6_warmup_trim.py -q → 16 passed
test_warmup_trim_cgsa_validate log: groups=7 pre-validate, total_features=25
```

## Commits (local, not pushed)
- `test:` B6 re-review test fidelity — CGSA validate non-empty + IC-first public window

STATUS: DONE
