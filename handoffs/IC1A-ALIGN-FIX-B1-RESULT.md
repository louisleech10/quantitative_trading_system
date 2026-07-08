# IC1A ALIGN FIX B1 Result
task-id: ic1a-align-fix-b1
date: 2026-07-09

## changed
- `momentum/core/contracts.py`: Tier-1 label coverage gate added as `valid_ratio >= (len-lag)/len*(1-0.01)`; 0.01 mirrors existing IC label coverage tolerance default without changing `AlignmentSpec`.
- `momentum/core/contracts.py`: Tier-2 sampling changed from seeded random to deterministic head/tail + equidistant strata + forced sensitive rows from `abs(diff(label))` jumps and timestamp gap boundaries.
- `momentum/core/contracts.py`: close-axis missing positions now skip oracle comparison; coverage gate handles missing-label impact, true oracle mismatches still raise `AlignmentViolationError`.
- `momentum/Analysis/ic_filter_orchestrator.py`: successful label-column horizon parsing logs metadata `horizon_source=column_parse`, selected column, effective horizon, and parsed horizons.
- Tests added for low coverage, gap-boundary mismatch, single-point M1 mismatch, missing close-axis skip, M7 mutation receipt docstring, and `horizon_source` metadata.

## blocking mapping
- ADV-B1-01: closed by Tier-1 coverage threshold and `test_validate_alignment_low_label_coverage_raises`.
- ADV-B1-02: closed by deterministic stratified sampling; no `rng(0)` remains.
- ADV-B1-03: closed by forced sensitive rows for label jumps and gap boundaries; covered by single-point and gap-boundary mismatch tests.
- ADV-B1-04: closed by skipping NaN `positions` in Tier-2 oracle; covered by `test_validate_alignment_missing_close_positions_skip_oracle`.
- ADV-B1-05: closed by `test_validate_alignment_m1_single_point_misalignment_raises`.
- ADV-B1-06: M7 mutation receipt documented in test docstring.
- ADV-B1-09: `horizon_source: column_parse` metadata logged and asserted via `caplog`.

## commands
- `pytest tests/momentum/core/test_alignment_contract.py tests/momentum/Analysis/test_ic_1a_cut1_split.py -q` -> 29 passed in 0.52s.
- `pytest tests/momentum/ -k horizon_resolver -q` -> 2 passed, 977 deselected in 1.58s.
- `grep -r "from api\\." momentum/ || true` -> no output.
- `git diff -- data_cache` -> no output.

## impact
- NUMERIC_OR_SCHEMA_IMPACT: no output schema or HDF5 schema change; validation now fail-closes low label coverage and additional sampled mismatches.
