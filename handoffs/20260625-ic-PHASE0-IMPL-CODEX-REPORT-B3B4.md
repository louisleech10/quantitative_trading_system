ASSUMPTIONS_VERIFIED: B1+B2 accepted by Claude; `preview_limit` absent; feature_filter exact 7 fields added; default filter does not truncate; explicit `max_features` uses sorted column names only.

TESTS_RUN:
- `pytest tests/momentum/test_ic_phase0_golden.py tests/momentum/test_ic_feature_filter.py tests/momentum/test_ic_decay_log.py -q` → 9 passed
- `pytest tests/api/test_ic_analysis_service.py::test_run_analysis_does_not_block_event_loop -q` → 1 passed
- `cd frontend && npm test -- src/hooks/useICAnalysis.test.ts` → 4 passed
- Requested gate `pytest tests/momentum/ tests/api/ -q --deselect ... --deselect ...` → failed during collection, 14 errors from `api.main` import constructing `BinanceProvider` and pinging `api.binance.com` under restricted network

FAILURES_SEEN: One API unit test fixture issue fixed by explicit `labels_path`; full requested gate blocked by external Binance network call during test collection.

SCOPE_CHANGES: none. Did not touch the two pre-existing feature factory failures, provider startup behavior, or `preview_limit`.

NUMERIC_OR_SCHEMA_IMPACT: IC schema changed by adding `FeatureFilterSchema` and `ICConfig.feature_filter`; report metadata now includes feature filter counts/truncation fields. Decay numeric output unchanged; logging changed from per-fit warning to one summary INFO.

FILES_CHANGED: `momentum/Analysis/ic_config_schema.py`, `momentum/Analysis/ic_filter_orchestrator.py`, `momentum/Analysis/ic_engine.py`, `api/services/ic_analysis_service.py`, `frontend/src/hooks/useICAnalysis.ts`, `frontend/src/store/icAnalysisStore.ts`, tests and `tests/fixtures/ic_phase0/*`, plus handoff `handoffs/20260625-ic-phase0-b3-b4-codex.md`.

GOLDEN: grouped baseline passed; feature_filter baseline passed; decay baseline passed.

HANDOFF: wrote append-only `handoffs/20260625-ic-phase0-b3-b4-codex.md`.

STATUS: BLOCKED — requested full pytest gate cannot collect in restricted network because unrelated API route imports instantiate BinanceProvider and call api.binance.com; in-scope B3/B4 targeted tests pass.