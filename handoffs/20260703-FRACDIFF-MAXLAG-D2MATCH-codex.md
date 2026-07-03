# 20260703 FRACDIFF-MAXLAG D2MATCH — Codex

## Scope
- Task-id: fracdiff-maxlag-d2match-codex-20260703
- Files changed: `tests/feature_engineering/test_ff_fullchain_truncation_mr.py`
- Handoff file: `handoffs/20260703-FRACDIFF-MAXLAG-D2MATCH-codex.md`

## Decision
- Accept two legal failure paths for `test_mutation_fracdiff_calibration_perturb_fails`.
- Match changed from `d_star` to `columns gate failed \(strict\)|d_star`.
- Reason: calibration-window perturbation can change ADF/d* search results, which can change the eligible fracdiff column set before the d* value gate runs.

## Evidence
- Receipt `handoffs/run_receipts/20260703T124142Z-fracdiff-maxlag-d1d2-slow.log` shows the mutation exercised calibration and failed first at strict columns gate.
- Observed failure input: `columns gate failed (strict): only_in_full=428 only_in_trunc=437`, with samples dominated by `*_fracdiff` columns.
- Helper order confirms strict columns gate runs before d* gate in `_assert_fracdiff_truncation_invariants`.

## Verification
- Ran: `source venv/bin/activate && pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py --collect-only -q`
- Result: pass, 13 tests collected.

## Notes
- This does not allow generic values-gate failures and does not weaken numeric tolerances.
- No schema, output-size, or data-cache changes.
