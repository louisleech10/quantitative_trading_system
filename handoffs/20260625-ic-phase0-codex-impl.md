# IC Phase 0 Codex implementation handoff

## Done
- B1 Task 1.1/1.2 implemented locally: orchestrator now passes `grouped_analysis.model_dump()` into `compute_grouped_ic`.
- B2 Task 2.1/2.2/2.3 implemented locally: numeric timestamps return `DatetimeIndex`, second/ms unit inferred, implausible years fail closed, `by_volatility` defaults False and explicit True raises.
- Added red-then-green regression tests for real Pydantic grouped config and RangeIndex + second timestamp kline shape.
- Replaced existing Stage4 test `SimpleNamespace` grouped config with real `ICConfig`.

## Blocked
- Cannot proceed to B3 because required gate `pytest tests/momentum/ -q` failed.
- Failing outside current IC scope:
  - `tests/momentum/test_feature_factory_optimization_e2e.py::test_pipeline_with_preprocessing`: expected `_rank` column, actual L6.5 config logged `rank=False`.
  - `tests/momentum/test_feature_factory_optimization_perf.py::test_full_pipeline_overhead`: expected `ms_` column, actual run produced no such new columns.
- Commit creation failed: sandbox cannot write `.git/index.lock` (`Operation not permitted`).

## Tests
- Red proof before fix: `pytest tests/momentum/test_ic_crash_real_config.py tests/momentum/test_ic_timeaxis.py -q` failed with `GroupedConfig` `.get`, Series `.to_series`, missing by_volatility fail-closed.
- Targeted after fix: `pytest tests/momentum/test_ic_crash_real_config.py tests/momentum/test_ic_timeaxis.py tests/momentum/test_ic_engine.py::test_time_index_parsing_and_alignment tests/momentum/test_ic_filter_orchestrator.py::test_stage4_ic_calculation_with_kline_reader -q` passed 7.
- Full gate: `pytest tests/momentum/ -q` failed 3 initially; after IC fixture fix, remaining blockers are the two feature factory tests above.

## Notes
- Running full momentum tests emitted writes under `data_cache/cgsa_work/...` from existing feature factory tests.
- `grep -rn preview_limit api/ momentum/ frontend/src` returned 0.
