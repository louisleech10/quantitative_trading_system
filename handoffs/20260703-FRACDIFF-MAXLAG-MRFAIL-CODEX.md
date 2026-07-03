# fracdiff max_lag MR failure diagnosis — Codex

task-id: fracdiff-maxlag-mrfail-codex-20260703

## Q4 test bug fixed

- Changed only the three `test_mutation_fracdiff_maxlag_len_coupling_*` window-length assertions in `tests/feature_engineering/test_ff_fullchain_truncation_mr.py`.
- Old assertion expected hardcoded `{590, 600}`.
- New assertion derives `window_bars = _fracdiff_window_bars(_fracdiff_mr_config_payload())` and expects `{window_bars - TRUNC_K, window_bars}`.
- Cheap verification printed `{'W': 2081, 'W_minus_TRUNC_K': 2071, 'TRUNC_K': 10}`.
- Helper assertions, tolerances, NaN-mask exactness, and mutation bodies were not weakened.

## Q1 / B1 diagnosis

Observed failure: `warmup 1h_L2_Momentum_chunk4.parquet::volume_1h_momentum_MACDEXT-Hist_13-55-13_Momentum_L144 NaN mask mismatch` in receipt `20260703T054245Z-fracdiff-maxlag-mr-green.log:8543`.

Line evidence:
- Fracdiff MR helper checks all columns after fracdiff value gate: `_assert_fracdiff_truncation_invariants()` calls `_assert_warmup_nan_masks_equal()` at `tests/feature_engineering/ff_truncation_mr_helpers.py:1142-1147`.
- Warmup mask check uses exact NaN-mask equality through `_assert_arrays_values_close()` at `tests/feature_engineering/ff_truncation_mr_helpers.py:717-728`.
- Fracdiff config runs append mode in `_fracdiff_mr_config_payload()` at `tests/feature_engineering/ff_truncation_mr_helpers.py:217-231`; fracdiff appends `f"{column}_fracdiff"` in `FeaturePreprocessor._assign_fracdiff_result()` at `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:3001-3010`.
- ADF also appends a new `f"{column}_diff{chosen_diff}"` column in append mode, not replacing the original column, at `feature_preprocessor.py:3361-3365`.
- The original MACDEXT momentum feature is produced by L2 momentum as `(selected - selected.shift(lag)) / safe_denominator(shifted)` at `momentum/FeatureEngineering/operators/derived_operators.py:576-586`; this is a causal prefix operation.
- Raw stream persistence coerces arrays to float32 before writing at `feature_preprocessor.py:413-427` and `feature_storage.py:876-904`; sanitize only nulls non-finite or `|v| > finite_cap`, per `numeric_guards.py:61-87`.

Conclusion:
- The specific failed column is an original non-`_fracdiff` L2 column. In append mode, neither fracdiff nor ADF should mutate that original column directly.
- Therefore B1 is not explained by the new max_lag resolver and not explained by direct ADF replacement of that column.
- Most likely remaining mechanism is a pre-existing residual length dependency in the original feature/materialization path exposed by the stricter all-column warmup mask gate. The code path to inspect next is full vs trunc raw artifacts around that exact column to locate the first differing NaN index, then trace whether it is born before L6.5, during raw-sink float32/sanitize, or during parquet codec selection.
- I did not run a second full chain, so B1 is narrowed but not single-line root-caused.

## Q2 / B2 diagnosis

Observed failure: `volume_1h_statistics_VAR_144_fracdiff`, 1/20 prefix elements differ, max abs diff `4.7683716e-07`, receipt lines `12040-12044`.

Line evidence:
- Strict fracdiff value gate is `np.testing.assert_allclose(..., atol=FRACDIFF_ATOL, rtol=0.0)` at `ff_truncation_mr_helpers.py:1009-1020`.
- Fracdiff uses `fractional_difference_values()` in the parallel worker at `_slow_path_parallel.py:140-175`.
- `fractional_difference_values()` uses `_convolve_1d()` at `_hurst_prior.py:96-130`.
- `_convolve_1d()` dispatches to SciPy `fftconvolve` when `signal.size * weights.size > 4096` at `_hurst_prior.py:20-28`.
- Raw-sink and parquet persistence coerce to float32 at `feature_preprocessor.py:413-427`, `feature_storage.py:46-49`, and select float16/float32 storage at `feature_storage.py:2564-2588`.

Cheap experiment:
- I ran two synthetic arrays with identical prefix and perturbed final 10 rows through `fractional_difference_values()`.
- FFT path produced nonzero prefix differences (`max_prefix_diff` around `1.5e-10` in float64); direct `np.convolve` on the same finite window produced exact zero prefix difference.

Conclusion:
- B2 is consistent with FFT convolution roundoff leaking tiny numerical differences into mathematically unaffected prefix bins, then being observed at float32/persistence precision.
- It is less consistent with parallel reduction: joblib maps columns independently and preserves returned output order (`_slow_path_parallel.py:67-98`), and each column calculation is single-column convolution, not a cross-column reduction.
- It is also less consistent with true causal data leakage: the mathematical direct convolution has exact zero prefix drift under the same tail perturbation.

Repair recommendation for B2:
- For MR-strict causality tests, force fracdiff convolution to a local direct convolution when testing tail perturbation, or make `_convolve_1d()` causality-stable for the prefix by avoiding full-series FFT in strict deterministic mode.
- Do not relax `FRACDIFF_ATOL` silently. If production keeps FFT for speed, document that FFT introduces sub-float32-prefix roundoff and put the tolerance decision through explicit committee/user approval.

## Q3 introduction status

Evidence:
- `test_fracdiff_truncation_invariant` and `test_fracdiff_tail_perturbation_invariant` were introduced as strict xfail in commit `9d87d68`; the xfail comments say the previous blocker was `max_lag = len(df)//10`.
- Facts file says the warmup/value assertions were unreachable before the max_lag fix and the fracdiff-off main MR was green.
- ADF differencing core lines are old by blame (`feature_preprocessor.py:3306-3365` mostly Feb-Apr-Jun 2026); parallel fracdiff worker core is old (`_slow_path_parallel.py:123-176` mostly Apr-Jun 2026).
- The current max_lag resolver is uncommitted in this worktree and only changes the value-path width derivation at `feature_preprocessor.py:3020-3025` / `3201-3205`.

Conclusion:
- B1 and B2 are best classified as pre-existing behavior first exposed after the xfail/max_lag blocker was removed, not as directly introduced by the max_lag resolver.
- The epic still changes all fracdiff values by design, so these surfaced failures must be declared in the epic signoff scope before regenerating FF for IC.

## Verification

ASSUMPTIONS_VERIFIED:
- `_fracdiff_window_bars(_fracdiff_mr_config_payload())` returns 2081 and `TRUNC_K` is 10.
- The three mutation tests collect after the assertion edit.
- FFT fracdiff can produce nonzero prefix drift from tail-only perturbation; direct convolution did not in the cheap reproduction.

TESTS_RUN:
- `python - <<'PY' ... _fracdiff_window_bars ...` PASS; printed `W=2081`, `W_minus_TRUNC_K=2071`, `TRUNC_K=10`.
- `python -m pytest --collect-only -q tests/feature_engineering/test_ff_fullchain_truncation_mr.py::{three mutation tests}` PASS; 3 tests collected.
- `python - <<'PY' ... fractional_difference_values tail perturb experiment ...` PASS; FFT prefix drift reproduced, direct convolution prefix drift zero.
- `git diff --check -- tests/feature_engineering/test_ff_fullchain_truncation_mr.py` PASS.

FAILURES_SEEN:
- none during my edits; prior slow receipt failures are the input facts.

SCOPE_CHANGES:
- none. My direct edits were the three requested assertion lines in `tests/feature_engineering/test_ff_fullchain_truncation_mr.py` and this requested handoff file. The worktree already contained broader uncommitted fracdiff/max_lag changes before this task.

NUMERIC_OR_SCHEMA_IMPACT:
- none from this task. No production numeric code, schemas, output size, helper thresholds, or `data_cache/` were changed.

STATUS: DONE
