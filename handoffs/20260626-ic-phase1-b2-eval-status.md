# 20260626 IC Phase1 B2 eval_status

## Scope
- Implemented TODO Task 2.2 only: `EvaluationStatus`, `ICResult.eval_status`, `filter_evaluated`, and v1 serialization exclusion.

## Changed
- `momentum/core/contracts.py`: added `EvaluationStatus(str, Enum)` and `filter_evaluated(results)`.
- `api/services/ic_analysis_service.py`: `_to_json_compatible(..., ic_response_v2=False)` removes `eval_status` for `ICResult` on v1 serialization.
- `tests/momentum/core/test_eval_status.py`: explicit evaluated filtering and legacy exclusion coverage.
- `tests/api/test_ic_response_v2.py`: service `get_result()` path compares B0 baseline after stripping only `generated_at`.

## Validation
- `pytest tests/momentum/core/test_eval_status.py tests/api/test_ic_response_v2.py -q` → 3 passed.
- `grep -rE 'from api\.' momentum/` → 0 matches.

## Decisions
- `UNKNOWN_LEGACY` remains the default to avoid counting legacy results as evaluated.
- v1 exclusion is scoped to `ICResult`; other dataclass serialization is unchanged.

## Notes
- Existing workspace already contained uncommitted/untracked Phase 1/B0/B1 files and a modified root `HANDOFF.md`; those were not reverted.
