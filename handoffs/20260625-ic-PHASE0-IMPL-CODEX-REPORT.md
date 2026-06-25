B1/B2 implementation is in place, but I stopped before B3 because the required `pytest tests/momentum/ -q` gate is not green.

ASSUMPTIONS_VERIFIED: B1/B2 bugs reproduced before fix; IC targeted tests pass after fix; `preview_limit` grep returns 0.
TESTS_RUN: targeted IC tests passed 7/7. Full `pytest tests/momentum/ -q` failed due two feature factory tests outside IC Phase 0 scope.
FAILURES_SEEN: fixed `GroupedConfig` `.get`, `Series.to_series`, by_volatility silent ignore, and 1970 toy timestamp test fixture. Remaining failures: `test_pipeline_with_preprocessing` expects `_rank`; `test_full_pipeline_overhead` expects `ms_`.
SCOPE_CHANGES: none; did not edit feature factory scope. Wrote append-only handoff: `handoffs/20260625-ic-phase0-codex-impl.md`.
NUMERIC_OR_SCHEMA_IMPACT: `GroupedConfig.by_volatility` default changed `True -> False`; explicit True now raises `NotImplementedError`; timestamp parsing now fail-closes implausible years.
COMMIT_STATUS: blocked by sandbox, `.git/index.lock` write denied.

STATUS: BLOCKED — B3 cannot start until `pytest tests/momentum/ -q` gate is resolved or scope is expanded for the two feature factory failures.