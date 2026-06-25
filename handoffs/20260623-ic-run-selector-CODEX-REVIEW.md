STATUS: CONCERNS

**Findings**

BLOCKING: `find_latest` is not read-safe and explicit `config_hash` can silently fall back to unrelated data.
Evidence: [feature_registry.py](/Users/louis/Desktop/quantitative_trading_system/momentum/FeatureEngineering/feature_registry.py:130) chooses max timestamp only. Current registry has latest BTCUSDT/12h entries `5218729…` and `4d26a4…` with empty `hdf5_relative_path` in [registry.json](/Users/louis/Desktop/quantitative_trading_system/data_cache/features/registry.json:111). Then [feature_library.py](/Users/louis/Desktop/quantitative_trading_system/momentum/FeatureEngineering/feature_library.py:160) catches `FileNotFoundError` and falls through to legacy `load_factory_output` at line 163, even when a specific `config_hash` was requested.
Fix: do not “clean registry” as the primary fix. Add read semantics: `find_latest_materialized(symbol, timeframe)` or `find_latest(..., require_materialized=True)` that skips `deleting`, requires a non-empty existing V2 manifest, and validates the requested artifact/raw files. Use that in `FeatureLibrary.load`, IC no-hash fallback, and `ensure_fresh`. For explicit `config_hash`, fail closed if V2/legacy artifacts for that exact hash are missing; do not fallback to symbol/timeframe legacy storage.

BLOCKING: Golden tests are coupled to live mutable registry state.
Evidence: [test_ic_run_selector.py](/Users/louis/Desktop/quantitative_trading_system/tests/api/test_ic_run_selector.py:79) compares no-hash latest to a fixture pinned at `90f586…`, while live registry latest can drift to later orphan entries. This is a real bug in the read path, but the golden should not be hostage to whatever previous tests left in `data_cache/features/registry.json`.
Fix: make the backward-compat golden hermetic. Copy a pinned mini registry into `tmp_path`, set `FFACT_FEATURE_REGISTRY_PATH` to it, include exactly the baseline entries, and point entries at real immutable fixture data or existing real artifact paths. Add a separate live-registry canary that asserts no orphan is selected by the new readable-latest resolver.

BLOCKING: Cross-sectional batch selection can mix timeframes and then read all symbols with the first run’s timeframe.
Evidence: [ICConfigPanel.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/components/ic-analysis/ICConfigPanel.tsx:157) takes `primaryTf = group.items[0]?.timeframe`, then sends every run in the batch as `{symbol, config_hash}` at lines 160-163. Backend then calls `load_multi(symbols_resolved, request.timeframe, config_hashes=...)` in [ic_analysis_service.py](/Users/louis/Desktop/quantitative_trading_system/api/services/ic_analysis_service.py:130).
Fix: group cross-sectional choices by `(batch_id, timeframe)` or include `timeframe` in `CrossRunRef` and load each run by its own `(symbol, timeframe, config_hash)`. Given current backend API, the safer minimal fix is to only offer homogeneous batch/timeframe groups.

BLOCKING: G-3 still does not test the real ML caller.
Evidence: spec requires `CrossSymbolTrainingService.run_cross_symbol_validation`; real caller is [cross_symbol_training_service.py](/Users/louis/Desktop/quantitative_trading_system/api/services/cross_symbol_training_service.py:38). But baseline generation and test call `library.load_multi` directly in [gen_ic_run_selector_baseline.py](/Users/louis/Desktop/quantitative_trading_system/tests/fixtures/gen_ic_run_selector_baseline.py:114) and [test_ic_run_selector.py](/Users/louis/Desktop/quantitative_trading_system/tests/api/test_ic_run_selector.py:90).
Fix: instantiate `CrossSymbolTrainingService`, spy/monkeypatch its `_feature_library.load_multi`, run `run_cross_symbol_validation`, assert kwargs exactly include `for_training=True`, `allow_partial_training`, `feature_columns`, and no `config_hashes`.

BLOCKING: Gate command is too weak for golden coverage.
Evidence: implementation handoff reports only `pytest -k ic_run_selector`; `pytest.ini` does not register `ic_run_selector`, `backward_compat`, or `disambig` markers at [pytest.ini](/Users/louis/Desktop/quantitative_trading_system/pytest.ini:24). I could not run collect-only because the read-only sandbox has no usable temp dir.
Fix: register markers, then use explicit gate:
`PYTHONDONTWRITEBYTECODE=1 pytest tests/api/test_ic_run_selector.py tests/momentum/test_feature_library_config_hash.py tests/api/test_ic_analysis_service.py tests/api/test_ic_list_features.py -m "ic_run_selector or backward_compat or disambig" -v --tb=short`
Also keep `pytest tests/api tests/momentum -k "ic_run_selector or backward_compat or disambig"` only as a secondary smoke, not the golden gate.

NON-BLOCKING: `fetchAvailableFeatures` failure leaves stale features visible.
Evidence: [page.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/app/ic-analysis/page.tsx:256) sets `featuresError` but does not clear `availableFeatures`.
Fix: in `catch`, call `setAvailableFeatures([])` before setting the error.

NON-BLOCKING: `EnsureBrowseResponse` repair looks correct.
Evidence: `RunInfo` ends cleanly and `EnsureBrowseResponse` is restored as a separate class in [feature_factory_models.py](/Users/louis/Desktop/quantitative_trading_system/api/models/feature_factory_models.py:116). Route imports should resolve.

HANDOFF_NOT_UPDATED: read-only review requested; sandbox is read-only.

TESTS_RUN: `pytest --collect-only ... -p no:cacheprovider` attempted, failed before collection because no writable temp directory exists in this sandbox. No code/tests modified.

STATUS: CONCERNS