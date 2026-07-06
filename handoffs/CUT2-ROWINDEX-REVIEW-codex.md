# CUT2 row_index attach adversarial signoff — Codex

Verdict: PASS

Scope reviewed: `momentum/FeatureEngineering/feature_library.py`, row_index tests, `tests/api/test_ic_analysis_service.py`, `docs/IC_PHASE1_1a_CUT2_ROWINDEX_SPEC.md`, `docs/IC_PHASE1_1a_CUT2_ROWINDEX_TODO.md`.

Adversarial hypothesis tested: attaching `timestamps.parquet` could silently shift rows, preserve wrong values under correct labels, or leave IC split using poisoned arange cache.

## Findings

ID: ADV-CODEX-1 [NON-BLOCKING] Row attach implementation is narrow and value-preserving.
Receipt: `source venv/bin/activate && pytest tests/momentum/test_feature_library_row_index.py tests/momentum/test_feature_library_config_hash.py tests/api/test_ic_analysis_service.py -k "not analyze_real_run_with_config_hash_completes" -q` => 13 passed in 89.02s. Real BTCUSDT/12h/e53e2290 loaded as `(1696, 218369)`, `DatetimeIndex(name="timestamp")`, and sampled direct-reader values matched with `equal_nan=True`.

ID: ADV-CODEX-2 [NON-BLOCKING] I could not falsify row-order alignment.
Receipt: independent script checked persisted sidecars across 9 materialized runs: all row_index counts matched manifest, strictly increased, and had expected 1h/12h cadence. For BTCUSDT/12h/e53e2290, `df.index` seconds were byte-equal to `load_row_index_v2`; semantic time oracles `meta_12h_Time_DayOfWeek`, `HourOfDay`, and `IsWeekend` had 0 mismatches against the attached index. I initially tried `MonthOfYear` as a raw oracle; diagnosis showed it has derived/fractional month-boundary behavior, so I did not use it as a counterexample.

ID: ADV-CODEX-3 [NON-BLOCKING] Poisoned IC ingest cache is not automatically invalidated, but current workspace is clean.
Receipt: independent read-only scan of `data_cache/reports/ic_ingest_cache/*.h5` found `poison_arange=False`; BTCUSDT_12h_e53e... timestamps were `[1704067200, 1704110400, 1704153600, 1704196800]`, 43200s diffs, byte-equal to sidecar, and `_validate_expected_frequency(..., 12h)` passed. Code still has the known property that `_materialize_features_for_ic` does not rewrite an already-existing H5; a preexisting poisoned H5 would remain a counterexample until deleted or invalidated. I judge this acceptable for this signoff only because the local derived cache was scanned clean; cache versioning or timestamp validation would be a future hardening item.

ID: ADV-CODEX-4 [NON-BLOCKING] Retargeted API test is faithful to this bug boundary, but no longer proves full analyze completion.
Receipt: the passing test exercises `_materialize_features_for_ic -> H5 timestamps -> _validate_expected_frequency`, which is the observed failure boundary. Mutation claim is credible: if attach is no-op, `_write_features_h5` would write RangeIndex as arange and the timestamp assertions/frequency validation fail. This deviates from SPEC G-3's literal "status completed" endpoint, but does not weaken the data-correctness assertion for the row_index bug.

ID: ADV-CODEX-5 [NON-BLOCKING] 1d frequency gap can be deferred.
Receipt: `EXPECTED_FREQ_BY_TIMEFRAME` currently contains only `1h`, `4h`, `12h`. No 1d materialized run was available in the reviewed fixture set; adding 1d without real validation would be an unverified assumption. This is adjacent IC split support, not a defect in row_index attach.

ID: ADV-CODEX-6 [NON-BLOCKING] Unrelated tracked test inventory diff should not ship with this row_index commit.
Receipt: `git diff -- tests/golden/l65/test_inventory.txt` replaces seven L6.5 nodeids with `BLOCKER: no L6.5/preprocessing tests collected`. This is outside row_index data correctness, but it is a test-gate artifact and should be restored or separated before commit.

## Three Judgment Points

1. Poisoned cache invalidation: PASS for current workspace after read-only H5 scan; recommend future invalidation/validation, not required to sign this attach if cleaned caches are part of release procedure.
2. Test retarget: PASS for row_index data correctness; it closes the materialize/split failure boundary, not the orthogonal 17m full-analyze performance path.
3. 1d gap: PASS to defer; no real 1d artifact was available to validate.

## Receipts

- `pytest ... -q`: 13 passed in 89.02s.
- `grep -r "from api\\." momentum/ | wc -l`: 0.
- Independent sidecar/cache script: sidecar_scan_count=9; all count/monotonic/frequency checks true; target `axis_byte_equal True`; `sample_value_equal_nan True`; `ic_cache_matches_axis True`; `split_frequency_validation pass`; ingest cache scan found no arange poison.
- Semantic row-order script: `DayOfWeek`, `HourOfDay`, `IsWeekend` all true with 0 mismatches.
