# R3 Codex read-only verdict — fracdiff max_lag

Task: `fracdiff-maxlag-r3-codex-20260703`  
Mode: read-only adjudication; only this output file was written.

## Evidence Checked

1. Receipt delta is real.
   - `handoffs/run_receipts/20260703T054245Z-fracdiff-maxlag-mr-green.log:7337` shows `test_mutation_fracdiff_calibration_perturb_fails` `PASSED [85%]`; short summary at `:27048-27073` does not list this test as failed.
   - `handoffs/run_receipts/20260703T094044Z-fracdiff-maxlag-convfix-slow.log:16247-16263` lists the same test failed with `DID NOT RAISE`.
   - Interpretation: after conv direct fix, this control stopped raising. The delta supports "previous raise was not the intended asymmetric calibration/d* path".

2. `_build_truncation_pair` applies `patch_fetch` symmetrically to both runs.
   - `tests/feature_engineering/ff_truncation_mr_helpers.py:1327-1329` computes one `(start, full_end, trunc_end)` from the same source window; `:1358-1367` runs full with `start -> full_end`; `:1371-1380` runs trunc with the same `start -> trunc_end`.
   - `:1333-1347` monkeypatches `AdapterRegistry.fetch_aligned`; for matching `symbol` and `primary_tf`, every fetch passes through `patch_fetch(data.copy())`.
   - Therefore both full and trunc generation calls see the patched primary kline source.

3. `_patch_kline_calibration_ohlcv` perturbs each fetched dataframe relative to that fetched dataframe's own tail window.
   - `tests/feature_engineering/ff_truncation_mr_helpers.py:1393-1411`: `window_start = len(out) - window_bars`, `cal_end = window_start + calibration_bars`, then OHLCV columns are perturbed in `out.iloc[window_start:cal_end]`.
   - Because full/trunc fetches are both patched, and the patch selects the first `calibration_bars` inside each current tail window, it does not force a one-sided full-only or trunc-only calibration difference. That is a design bug for a negative control whose intended oracle is "calibration perturb -> d* asymmetry -> MR fails".

4. Codec flip fact is correct.
   - `momentum/FeatureEngineering/feature_storage.py:2554-2588` chooses float16 only if the whole input column array survives float16 roundtrip: finite roundtrip must hold (`:2572-2575`), and every finite element's abs error must be within `max(FLOAT16_MAX_ABS_ERROR, abs(value)*FLOAT16_MAX_REL_ERROR)` (`:2577-2586`); otherwise float32 is used.
   - `_select_parquet_storage_columns` passes the full persisted column vector `source[:, col_idx]` into that selector at `:2604-2606`.
   - Thus dtype is per-column and value-range dependent over the full persisted window, not prefix-only. Tail perturbation can flip full/trunc storage dtype and change prefix precision.
   - `094044Z` tail failure matches this: `close_1h_trend_BBANDS-Lower_233_fracdiff`, `Max absolute difference: 0.0078125`, with `y` displayed as `dtype=float16` at log `:8540-8565` and summary `:16247-16263`.

## Verdicts

- D1: choose (a), strict xfail tied to B1/storage codec family.
  - Reason: current failure is dominated by persistence precision selection, not necessarily fracdiff tail causality. Treating it as a fracdiff MR failure is misleading.
  - Constraint: label it explicitly as temporary loss of tail value-level protection. Do not count tail value MR as signed off until storage codec determinism is fixed or the test is moved pre-persistence.
  - D1(b) is technically stronger but changes test/helper scope. It should be a follow-up only if explicitly authorized.

- D2: approve and require redesign.
  - The existing calibration perturb control is structurally symmetric because `patch_fetch` hits both runs and the perturbation is relative to each fetched dataframe's own window. Redesign must perturb only one run, or otherwise create a proven d* asymmetry, then assert the d* gate is the failure path.

- D3: approve.
  - The signoff scope must state that confirmed value-range-dependent parquet codec selection affects tail value comparison and B1; storage epic remains outside current max_lag correctness signoff.

- D4: approve.
  - Upgrade storage epic text to confirmed root cause: per-column float16/float32 codec is selected from full-window column values, so length/tail values can leak into persisted prefix precision.

## Challenge To Claude Vote

Claude's D1(a)/D2/D3/D4 vote is mostly correct, but the D1(a) wording must not imply the tail MR is merely noisy. It is disabled on a real protection surface until storage determinism or a pre-persistence oracle exists.

I would add one gate to Claude's plan: after D2 is redesigned, the receipt must show failure through the d* invariant, not only a generic value mismatch. Otherwise the same class of false positive could re-enter under another numerical path.

ASSUMPTIONS_VERIFIED: verified receipt delta 054245Z vs 094044Z; verified patch_fetch is applied to both full/trunc generation calls; verified calibration patch is relative to each fetched dataframe's tail window; verified parquet codec selection uses whole per-column persisted values.
TESTS_RUN: no tests run; read-only adjudication by source/log inspection only.
FAILURES_SEEN: none during this task; referenced receipts show 094044Z tail value failure and calibration DID NOT RAISE.
SCOPE_CHANGES: none; only wrote `handoffs/20260703-FRACDIFF-MAXLAG-R3-CODEX.md`.
NUMERIC_OR_SCHEMA_IMPACT: none from this task; verdict identifies existing storage precision impact.
STATUS: DONE
