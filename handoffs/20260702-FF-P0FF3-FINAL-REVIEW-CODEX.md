# P0-FF-3 final code review — Codex

## Scope Reviewed

- Current `git diff HEAD` for:
  - `tests/feature_engineering/ff_truncation_mr_helpers.py`
  - `tests/feature_engineering/test_ff_multitf_truncation_mr.py`
- Committed fracdiff xfail change in `9d87d68`.
- Design/closure context:
  - `handoffs/20260702-FF-ALIGN-ORACLE-DESIGN-CODEX.md`
  - `handoffs/20260702-FF-P0FF3-PROBE-REVIEW-CODEX.md`
  - `handoffs/20260702-FF-P0FF3-PROBE-CLOSURE-CODEX.md`
  - Composer fix handoffs for align oracle/probe shape.
- Receipts checked:
  - `20260702T125150Z-mutation-test_ff_multitf_truncation_mr`: 5 passed, 4 deselected, 2:30:31.
  - `20260702T042627Z-ff-b2-regression`: 8 passed + 2 known fracdiff failures before strict-xfail handling.

## BLOCKING

None found.

## NON-BLOCKING

1. `test_mutation_align_lookahead_fails` and `test_mutation_align_lookahead_with_tail_perturb_fails` now use the correct anti-fake-green shape: build mutated pair outside `pytest.raises`, run `_assert_align_coarse_boundary_lookahead_detected(...)` outside `pytest.raises`, and wrap only `_assert_truncation_invariants(...)`.
2. Oracle implementation is faithful to `DESIGN-CODEX`: timestamps come from `pair.trunc.manifest["row_index"]["path"]` under `pair.trunc.run_dir`, require `unit == "s"`, validate count/row_count, compute 12h boundary row positions from the timestamp sidecar, and compare full/trunc coarse TF raw columns by shared parquet filename/column.
3. The align mutation is no longer symmetric: `_build_truncation_pair(..., align_lookahead_side="trunc")` restores original mapping for full generation, enables `_lookahead_build_asof_index_map` for trunc generation, and restores original mapping afterward when a monkeypatch fixture is supplied.
4. I did not find loosened tolerances, removed assertions, skipped existing cases, fake data, production code changes, output schema changes, or residual debug/dead code in the reviewed diff.
5. Helper extraction appears behavior-preserving for B2/default callers: `align_lookahead_side` defaults to `None`, so existing `_build_truncation_pair(...)` calls keep original full/trunc generation behavior. The B2 fracdiff tests are strict-xfail in `9d87d68`; their assertion bodies remain intact and should XPASS once max_lag is fixed.
6. Commit hygiene note: current worktree also contains out-of-scope `tests/golden/l65/test_inventory.txt` changes plus receipt/audit artifacts. Do not include `tests/golden/l65/test_inventory.txt` in the P0-FF-3 final code commit unless separately approved.

## VERDICT

APPROVED for formal commit of the scoped P0-FF-3 code/test changes. Include the final review handoff and intended receipts if that is the project convention; exclude unrelated/out-of-scope working-tree changes.

ASSUMPTIONS_VERIFIED: Read required repo handoffs/context; reviewed current diff and 9d87d68; checked oracle against DESIGN-CODEX; checked probe shape against prior Codex blocking; checked receipt metadata for full 5-probe PASS; confirmed helper default preserves non-align callers by static review.
TESTS_RUN: `PYTHONPYCACHEPREFIX=/private/tmp/pycache_final_review python -m py_compile tests/feature_engineering/ff_truncation_mr_helpers.py tests/feature_engineering/test_ff_multitf_truncation_mr.py tests/feature_engineering/test_ff_fullchain_truncation_mr.py` -> pass; `pytest tests/feature_engineering/test_ff_multitf_truncation_mr.py --collect-only -q` -> 9 collected; `pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py --collect-only -q` -> 10 collected; `python scripts/mutation_probe_static.py tests/feature_engineering/test_ff_multitf_truncation_mr.py` -> pass; `git diff --check -- tests/feature_engineering/ff_truncation_mr_helpers.py tests/feature_engineering/test_ff_multitf_truncation_mr.py` -> pass.
FAILURES_SEEN: none during this review; historical failures are the prior broad-raises fake-green shape and pre-xfail fracdiff max_lag failures.
SCOPE_CHANGES: none; review-only plus this handoff file.
NUMERIC_OR_SCHEMA_IMPACT: none from reviewed changes; fracdiff max_lag remains a documented future numeric-impact epic.

STATUS: DONE
