# BATCH_ALIAS code review r2 — Codex

## Scope
- Read `HANDOFF.md`, `CLAUDE.md`, `docs/BATCH_ALIAS_SPEC.md`, `docs/BATCH_ALIAS_TODO.md`.
- Reviewed staged test diff with `git diff --cached -- tests/`.
- Rechecked `_layer7` fake/caller coverage with `git grep -n "_layer7_validate_and_persist\|_layer7_raw_from_cgsa_pipeline" tests/` and `rg`.

## Findings
- none blocking.

## Review Result
- APPROVE.
- Prior r1 blocking issue is resolved: `multi_tf_generator.py` now passes `batch_id`, and staged strict fake factories accept the new optional kwarg.
- Existing test-file changes for `_layer7` fakes are signature-only:
  - `tests/test_multi_tf_generator.py`
  - `tests/test_multi_tf_golden_equivalence.py`
  - `tests/test_primary_self_align_skip.py`
  - `tests/feature_engineering/test_mtf_align_golden.py`
  - `tests/performance/test_searchsorted_perf.py`
  - `tests/feature_engineering/test_failopen_producer.py`
- No existing assertions or logic were removed/relaxed in those existing fake-factory test files.
- `tests/api/test_batch_alias.py` is newly added coverage, not a fake-green relaxation.

## Coverage Check
- All test fake definitions found by grep have `batch_id=None`.
- Remaining grep hits are direct calls to real helpers in `test_l7_raw_streaming.py` and `test_feature_factory_batch2d.py`; they are not strict fake signatures and remain compatible because `batch_id` is optional.

## Verification
- Commands run:
  - `git diff --cached -- tests/`
  - `git diff --cached --unified=0 -- <six existing fake-factory test files>`
  - `git grep -n "_layer7_validate_and_persist\|_layer7_raw_from_cgsa_pipeline" tests/`
  - `rg -n "def _layer7_validate_and_persist|def _layer7_raw_from_cgsa_pipeline" tests`
  - `git diff --cached -- momentum/FeatureEngineering/timeframe/multi_tf_generator.py`
- Tests not rerun by this reviewer; coordinator reported the relevant 100 tests passed.

## Structured Closeout
ASSUMPTIONS_VERIFIED: staged fake-factory diff is signature-only; all test fake `_layer7` definitions include optional `batch_id=None`; remaining grep hits are direct real-helper calls.
TESTS_RUN: no pytest/vitest rerun by reviewer; read-only diff/grep commands above passed.
FAILURES_SEEN: none.
SCOPE_CHANGES: none.
NUMERIC_OR_SCHEMA_IMPACT: none from reviewed fake signature change; broader feature adds metadata fields per SPEC.
STATUS: DONE
