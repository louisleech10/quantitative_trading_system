# FF d* gate committee note — Codex

## Scope read
- Read `HANDOFF.md`, `CLAUDE.md`, `handoffs/20260702-FF-DSTAR-GATE-CLAUDE.md`.
- Read `tests/feature_engineering/ff_truncation_mr_helpers.py` around `_assert_d_star_gate` / `_assert_fracdiff_truncation_invariants`.
- Read fracdiff/d* production path: `feature_preprocessor.py`, `_slow_path_parallel.py`, `_d_star_cache.py`, `_hurst_prior.py`, and factory context construction.
- No slow tests run; this is read-code reasoning only.

## Challenge to Claude analysis
Claude is right that d* is a stateful parameter and must eventually be persisted/fixed for production reproducibility. But I do **not** fully accept the stronger claim that the current 600→590 fracdiff MR "almost inevitably fails because truncation changes the window".

Evidence:
- Production `_calibration_series` / `_calibration_values` use `series.iloc[:calibration_bars]` / `values[:calibration_bars]`, with minimum 500 bars.
- The fracdiff MR config sets `calibration_bars=500`; helper window is `max(600, required_window)`, so 600→590 should preserve the first 500 row calibration prefix.
- Prior B2 design explicitly said fracdiff dedicated MR is 600→590 with same d-star, strict value tolerance, exact mask. That was not an accidental helper assertion; it was the intended object under test.
- The d_star cache does not share across full/trunc because payload validation includes `row_count` and `time_range`, but recomputation from identical first-500 calibration inputs should still converge to the same rounded d*.

So the observed mismatch (`0.4844` vs `0.4688`) is not explained by "tail removed, therefore d* may drift" alone. It means at least one of these is true:
- the target column's first 500 values differ between full and trunc before fracdiff d* search;
- the eligible-column / preprocessing path is not truly prefix-causal for that source column;
- the serial vs parallel or Hurst-prior/full-search path has a numerical boundary sensitivity despite nominally identical input;
- the helper is reading the wrong/latest d_star artifact when multiple files exist in a dir.

## Q1
The two tests should not be deleted as "invalid". They encode a valid causal invariant under the current first-500 calibration design. However, because they are currently failing in an expensive B2 suite and the root cause has not been isolated, marking only these two as temporary `xfail(strict=True)` is acceptable if linked to a new d* MR epic/task. The xfail reason should not say "d* drift is expected under truncation"; it should say "fracdiff d* MR currently fails; needs prefix-input diagnosis or fixed-reference d* injection".

## Q2
For current production code, d* selection is **not whole-window fit** in the normal path: it uses calibration prefix only. Therefore Q2 is not "benign whole-window non-determinism" versus "true whole-window look-ahead"; the code says whole-window fitting would be a mutant, and there is already a negative control that monkeypatches `_calibration_series` to full series.

Current read-code verdict:
- There is no direct evidence that production d* search uses future tail bars beyond the first 500.
- There is evidence that the failing MR may reveal some other prefix instability before d* search, because identical first-500 inputs should produce identical d*.
- So do **not** classify this failure as benign non-determinism yet. Classify as unresolved d* MR failure with no proved look-ahead, but enough signal to require a targeted diagnostic.

## Q3
The 8 non-fracdiff passes are enough to keep P0-FF-3 / non-fracdiff helper extraction moving, because main MR deliberately disables fracdiff/adf and covers winsor/rank/zscore/gaussian plus align paths. They are not enough to sign off fracdiff causality. Keep the fracdiff issue separate so P0-FF-3 does not block on d* productionization, but record that fracdiff remains unsignoffed for B2.

## Q4 recommended repair direction
Recommended immediate path: **C + narrow diagnostic, then B if feasible**.

1. Temporarily exclude/xfail only fracdiff d*-dependent MR tests from the current P0-FF-3 acceptance path, with an explicit d* epic reference.
2. Add a cheap diagnostic/helper for the failing column class: before fracdiff, compare full vs trunc first 500 calibration values for common eligible columns, and report first mismatch. This directly distinguishes "prefix input differs" from "search nondeterminism".
3. For a real stable MR, implement fixed-reference d* injection for test only: compute/load d* from the full/reference calibration prefix and force both full/trunc transforms to use the same d*. Then compare fracdiff output prefix. This tests transform causality without conflating d* selection.
4. Long-term production fix remains the documented fixed-reference / persisted d* epic in `docs/FEATURE_STATEFUL_PARAM_AUDIT_FINAL.md` and `docs/ROADMAP.md`.

I would avoid pure option A as final wording, because it can accidentally bless the current failure as expected. I would avoid pure option C if it means losing all fracdiff coverage. The right split is: main truncation MR excludes fracdiff; fracdiff has a dedicated diagnostic + fixed-d* MR; production d* persistence is its own high-risk epic.

## Closure report
ASSUMPTIONS_VERIFIED: d* selection uses first calibration prefix in serial and parallel paths; cache payload isolates by row_count/time_range; helper compares exact d* then fracdiff values; prior B2 docs intended same d* for 600→590.
TESTS_RUN: not run by request; read-code only.
FAILURES_SEEN: none during this consultation; underlying slow regression failure is documented in Claude handoff/receipt.
SCOPE_CHANGES: none; added this handoff only.
NUMERIC_OR_SCHEMA_IMPACT: none; no production/test code changed.

STATUS: DONE
