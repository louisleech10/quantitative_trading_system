# P0-FF-3 align mutation 探針修牙 — Codex code review

## Scope

- Reviewed `handoffs/20260702-FF-P0FF3-ALIGN-PROBE-FIX-composer.md`.
- Reviewed git diff for:
  - `tests/feature_engineering/test_ff_multitf_truncation_mr.py`
  - `tests/feature_engineering/ff_truncation_mr_helpers.py`
- Did not run slow `requires_kline` mutation tests; used code reasoning + static/collect only.

## BLOCKING

1. `test_mutation_align_lookahead_fails` and `test_mutation_align_lookahead_with_tail_perturb_fails` still accept the "no teeth" path as success.
   - Evidence: both tests wrap `_build_truncation_pair(...)`, `_assert_align_coarse_boundary_lookahead_detected(...)`, and `_assert_truncation_invariants(...)` inside one broad `with pytest.raises(AssertionError)` block (`test_ff_multitf_truncation_mr.py:156-176`, `191-212`).
   - The new oracle raises `AssertionError` when no coarse-column mismatch is found (`ff_truncation_mr_helpers.py:1259-1263`).
   - Therefore, if `align_lookahead_side="trunc"` is accidentally removed, ignored, or the monkeypatch fails to affect the real align path, the generated pair can be baseline-equivalent, the oracle raises "no coarse column mismatch", and the mutation test passes anyway.
   - This directly violates the intended tooth check: the test should prove the injected look-ahead produces a detectable mismatch, not treat failure to detect the mismatch as a killed mutant.
   - Required shape: build the mutated pair first, run `_assert_align_coarse_boundary_lookahead_detected(pair, ...)` outside any `pytest.raises`, then wrap only `_assert_truncation_invariants(...)` in `pytest.raises(...)` or otherwise assert a specific MR failure.

## NON-BLOCKING

1. The asymmetry mechanism itself is directionally correct: `_build_truncation_pair` restores original align for full and enables `_lookahead_build_asof_index_map` only for trunc when `align_lookahead_side="trunc"` (`ff_truncation_mr_helpers.py:1323-1349`). This removes the old full/trunc symmetric cancellation path if the patch reaches the real align call.
2. Existing no-injection baseline tests were not weakened in this diff. `test_c3_multitf_truncation_invariant` and `test_c3_multitf_tail_perturbation_prefix_invariant` still call `_assert_truncation_invariants` without `align_lookahead_side`, so this patch does not introduce an obvious false-red into the baseline path.
3. The oracle has useful setup-failure messages for missing timestamps, missing boundary rows, missing coarse probes, and no mismatch. The collected mismatch detail is currently only used as a pass condition, so the most actionable mismatch details may still come from the later MR failure rather than the oracle.
4. I did not see evidence of loosened existing assertions, relaxed tolerances, skipped cases, fake data, schema/output-size changes, or production changes in the reviewed diff.

## VERDICT

BLOCKING. The implementation fixes the old symmetry mechanism, but the new test structure still lets a toothless align injection pass via the oracle's own "no mismatch" AssertionError. The align probes should not be accepted until that broad `pytest.raises` block is narrowed.

## Review Receipt

ASSUMPTIONS_VERIFIED: Read required handoff/context; diff reviewed against HEAD; confirmed oracle failure path is inside broad `pytest.raises`; confirmed existing baseline tests are unchanged by this diff.
TESTS_RUN: `PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache_ff_review python -m py_compile tests/feature_engineering/ff_truncation_mr_helpers.py tests/feature_engineering/test_ff_multitf_truncation_mr.py` → pass; `pytest tests/feature_engineering/test_ff_multitf_truncation_mr.py --collect-only -q` → 9 tests collected; `python scripts/mutation_probe_static.py tests/feature_engineering/test_ff_multitf_truncation_mr.py` → exit 0.
FAILURES_SEEN: Initial `python -m py_compile ...` without `PYTHONPYCACHEPREFIX` failed with sandbox PermissionError writing `~/Library/Caches/com.apple.python`; rerun with `/private/tmp` pycache prefix passed.
SCOPE_CHANGES: none; review-only, added this handoff report.
NUMERIC_OR_SCHEMA_IMPACT: none.

STATUS: DONE
