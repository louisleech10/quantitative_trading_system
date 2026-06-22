# B6 Backend Fix — Composer (Codex review #1–#4)

Date: 2026-06-22 | Task: B6 review defect remediation

## Fixes applied

### #1 BLOCKING — flag-on/off cache collision
- **Change**: `_compute_config_hash` now adds `_warmup_trim_enabled: true` **only when** `FFACT_WARMUP_TRIM` is on (`is_warmup_trim_enabled()`).
- **Flag off**: payload unchanged → hash identical to pre-B6 strict (verified `test_warmup_flag_off_preserves_config_hash`: off==off, on≠off).
- **Flag on**: distinct cache entry → strict/warmup runs cannot `_try_load_cache` cross-hit.

### #2 BLOCKING — IC-first warmup leak
- `_run_ic_first_impl`: label/raw/pre_ic all pass `_trim_for_public_output` before IC window + persist; `selection_window` sized on trimmed label.
- Return `features_df` index = trimmed raw; `labels_df` trimmed; `data_range` + `_apply_warmup_metadata` from ingest axis.
- `_run_l1_l6_for_ic_first`: respects `_current_output_window` ingest_start/end for layer0 load.
- Partial factories (no `__init__`): warmup helpers use `getattr(..., "_current_output_window", None)` — no AttributeError when warmup off.

### #3 MAJOR — 5-path trim integration tests (hermetic)
New tests in `test_b6_warmup_trim.py` (tmp features + `FFACT_CGSA_WORK_DIR`, production `data_cache/features` snapshot diff):
| Path | Test | Env |
|------|------|-----|
| Non-CGSA L7 validate | `test_warmup_trim_non_cgsa_l7_validate` | CGSA=0 |
| CGSA raw | `test_warmup_trim_cgsa_raw` | CGSA=1 |
| CGSA validate/V7 | `test_warmup_trim_cgsa_validate` | CGSA=1 + `_layer7_validate_and_persist` |
| Multi-TF | `test_warmup_trim_multi_tf` | training 1h+12h, CGSA=0 |
| IC-first | `test_warmup_trim_ic_first` | `run_ic_first` + real L1-L6 |

Each asserts: first row ≥ output_start, `len(features_df)` == ingest-axis expected, L7 v2 manifest row_count when present.

### #4 MAJOR — row_count non-tautological
- `test_warmup_trim_no_leak_row_count_matches_window` + shared helper `_expected_output_row_count_from_ingest`: expected from `_layer0_data_ingestion(ingest_start..end)` + `output_row_count(raw.index, window)` — **not** from trimmed `result.features_df`.

## Verification (executed)
```
pytest tests/feature_engineering/test_b6_warmup_trim.py -v          → 15 passed
pytest tests/ -k warmup -q                                        → 32 passed
pytest tests/api/ -k batch -q                                     → 121 passed
pytest tests/feature_engineering/test_ic_first_pipeline.py -q     → 15 passed
FFACT_WARMUP_TRIM=0 python scripts/build_l65_golden_baseline.py --check → PASS
```
Hermetic: all integration tests call `_assert_data_cache_unchanged` (production features root snapshot).

## Commits (local, not pushed)
1. `fix:` feature_factory — cache key + IC-first trim + getattr guards
2. `test:` test_b6_warmup_trim — 5-path + hash + ingest-axis row_count

## Unchanged per user
- `estimate_max_warmup_bars` / quality-gain logic untouched.
- Flag off numerical behavior unchanged (golden --check PASS).

STATUS: DONE
