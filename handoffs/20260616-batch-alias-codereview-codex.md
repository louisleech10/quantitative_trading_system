# Batch Alias Code Review — Codex

RESULT: REQUEST_CHANGES

## Findings
- BLOCKING: `momentum/FeatureEngineering/timeframe/multi_tf_generator.py:1373` now always calls `_layer7_validate_and_persist(..., batch_id=batch_id)` in the legacy multi-TF path. Existing strict fake factories in `tests/test_multi_tf_generator.py` do not accept that new keyword, so the existing multi-TF regression suite fails. This violates the stated compatibility/regression gate even though the new parameter defaults to `None` at public entry points.

## Evidence
- Ran: `source venv/bin/activate && pytest tests/test_multi_tf_generator.py -q`
- Result: 5 failed, 11 passed.
- Failure shape: `TypeError: _layer7_validate_and_persist() got an unexpected keyword argument 'batch_id'` from `multi_tf_generator.py:1373`.
- Failing tests: `test_multi_tf_generator_aligns_and_tags`, `test_multi_tf_generator_skips_primary_self_alignment`, `test_lower_tf_missing_fails_closed_unless_partial_enabled`, `test_short_primary_data_still_generates`, `test_multi_tf_generator_propagates_date_range_to_all_layer0_calls`.

## Checked Clean
- SPEC V4 core registry semantics appear aligned: same concrete batch_id preserves `batch_alias`, different concrete batch_id resets `batch_alias`, `batch_id=None` merge-preserves existing batch metadata.
- `set_batch_alias` checks deleting targets and fails atomically before updates.
- auto-cleanup candidate filter and `mark_deleting()` both check `alias or batch_alias`.
- `grep -r "from api\\." momentum/` returned 0 results.
- No staged weakening found in `tests/api/test_run_lifecycle_api.py`; no staged diff there.

## Notes
- Coordinator-reported fix in `feature_registry.py` for new entry add path is correct: only `incoming_batch_id is None` strips batch fields.
- Frontend jest-dom import fix is present in the new batch alias panel test.
