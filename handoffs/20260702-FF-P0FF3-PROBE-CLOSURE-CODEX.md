# P0-FF-3 align 探針 BLOCKING 閉合 — Codex

## Scope

- Reviewed prior BLOCKING: `handoffs/20260702-FF-P0FF3-PROBE-REVIEW-CODEX.md`.
- Reviewed Composer fix summary: `handoffs/20260702-FF-P0FF3-PROBE-FIX2-composer.md`.
- Reviewed current git diff for `tests/feature_engineering/test_ff_multitf_truncation_mr.py`.
- Also checked helper injection/oracle structure in `tests/feature_engineering/ff_truncation_mr_helpers.py` for static reasoning.
- Did not run slow `requires_kline` tests, per instruction.

## Closure Checks

1. CLOSED: `_assert_align_coarse_boundary_lookahead_detected(...)` is now outside `pytest.raises` in both align mutation probes.
   - `test_mutation_align_lookahead_fails`: build pair at lines 156-167, oracle at 168-170, only MR invariant assertion under raises at 171-176.
   - `test_mutation_align_lookahead_with_tail_perturb_fails`: build pair at lines 191-202, oracle at 204-206, only MR invariant assertion under raises at 207-212.

2. CLOSED: only `_assert_truncation_invariants(...)` is wrapped in `pytest.raises(AssertionError)` for both align mutation probes.
   - The broad raises shape from the prior review is gone.

3. CLOSED: static no-fake-green reasoning.
   - `_build_truncation_pair(..., align_lookahead_side="trunc", monkeypatch=monkeypatch)` enables `_lookahead_build_asof_index_map` only for the trunc generation path.
   - If `align_lookahead_side` is removed, ignored, or monkeypatch no longer reaches the real align path, the positive oracle should hit its `no coarse column mismatch at 12h boundaries` AssertionError outside `pytest.raises`, making the probe red instead of fake green.
   - If the oracle passes, the subsequent MR invariant failure is the only expected exception swallowed by `pytest.raises`.

4. CLOSED: no new self-referential oracle in the mutation probes.
   - The mutation probes still use generated full/trunc artifacts and compare coarse TF columns at boundary rows.
   - The added synthetic `test_align_lookahead_oracle_smoke` exercises the oracle itself but is not used to certify the mutation path; it does not recreate the broad-raises fake-green issue.

## VERDICT

CLOSED. The specific BLOCKING issue from the prior review is resolved. I did not identify a remaining STILL-OPEN blocker in the requested closure scope.

ASSUMPTIONS_VERIFIED: Read required project context and specified handoffs; inspected current diff/test structure; inspected helper injection/oracle control flow for the fake-green case.
TESTS_RUN: none per instruction; static review only.
FAILURES_SEEN: none during closure review.
SCOPE_CHANGES: none; added this closure handoff only.
NUMERIC_OR_SCHEMA_IMPACT: none.

STATUS: DONE
