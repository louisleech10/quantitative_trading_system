# P1-FF-5/7 IMPL codex report

SCOPE:
- Changed only test delivery files: `tests/feature_engineering/ff_artifact_compare_helpers.py`, `tests/feature_engineering/test_ff_cross_symbol_value_isolation.py`, `tests/feature_engineering/test_ff_wrapper_path_correctness.py`.
- No production code edits. Root `HANDOFF.md` left unchanged per task-specific handoff target.

ASSUMPTIONS_VERIFIED:
- Existing kline fixture data contains BTCUSDT and ETHUSDT windows for the fast-tier value-isolation checks.
- `FeatureFactory.run()` can generate compact deterministic frames with L1 trend-only settings and `FFACT_USE_CGSA=0`.
- Wrapper input semantics are available through `TA_INPUT_SPECS` and can be compared against direct TA-Lib calls for representative functions.

V_MAPPING:
- V5.1 cross-symbol order permutation: `test_v5_1_fast_order_permutation_keeps_hash_and_sampled_values`.
- V5.2 D* path/payload isolation: `test_v5_2_dstar_path_payload_and_alias_are_symbol_isolated`.
- V5.4 run and CGSA path scoping: `test_v5_4_run_and_cgsa_paths_are_symbol_scoped`.
- V5.5 L5 reference cache tuple key: `test_v5_5_l5_reference_cache_uses_reference_symbol_timeframe_key`, `test_v5_reference_cache_source_uses_tuple_key_and_effective_ref_symbol`.
- V5 slow artifact comparison hook: `test_v5_slow_solo_a_equals_batch_b_then_a_artifacts`, marked slow and not executed locally.
- V7.1 wrapper semantics: `test_v7_1_full_registry_prepare_inputs_match_semantics`, `test_v7_1_wrapper_matches_talib_direct_for_representatives`, `test_v7_1_price_transform_policy_and_mavp_params`.
- V7.2 L2 polars/pandas path parity: `test_v7_2_l2_polars_and_pandas_paths_match_with_sentinel`.
- V7.3 L3 and L6.5 accelerated/fallback parity: `test_v7_3_l3_numba_multi_single_and_pandas_paths_match`, `test_v7_3_l65_polars_optimized_and_fracdiff_serial_paths`.
- V7.4 float16 error-bound contract: `test_v7_4_float16_error_bound_contract_is_explicit`.

M_MAPPING:
- M5.1 shared D* path sentinel: `test_mutation_m5_1_shared_dstar_path_fails_isolation`.
- M5.2 reference cache static-key sentinel: `test_mutation_m5_2_reference_cache_static_key_drop_is_detected`.
- M5.3 D* wrong-symbol payload sentinel: `test_mutation_m5_3_dstar_payload_wrong_symbol_fails_alias_guard`.
- M7.1 RSI input swap sentinel: `test_mutation_m7_1_rsi_input_swap_fails_semantics`.
- M7.2 claimed-polars-but-pandas fallback sentinel: `test_mutation_m7_2_polars_claim_but_pandas_fallback_fails_sentinel`.

TESTS_RUN:
- fast py_compile: `source venv/bin/activate && PYTHONPYCACHEPREFIX=/tmp/codex_pycache_p1ff57 python -m py_compile tests/feature_engineering/ff_artifact_compare_helpers.py tests/feature_engineering/test_ff_cross_symbol_value_isolation.py tests/feature_engineering/test_ff_wrapper_path_correctness.py` => pass.
- fast collect-only: `source venv/bin/activate && PYTHONPYCACHEPREFIX=/tmp/codex_pycache_p1ff57 pytest --collect-only tests/feature_engineering/test_ff_cross_symbol_value_isolation.py tests/feature_engineering/test_ff_wrapper_path_correctness.py -q` => pass, 26 tests collected.
- fast pytest: `source venv/bin/activate && PYTHONPYCACHEPREFIX=/tmp/codex_pycache_p1ff57 pytest tests/feature_engineering/test_ff_cross_symbol_value_isolation.py tests/feature_engineering/test_ff_wrapper_path_correctness.py -m "not slow" -q --tb=short` => pass, 25 passed, 1 deselected.
- fast mutation_probe_static: `source venv/bin/activate && PYTHONPYCACHEPREFIX=/tmp/codex_pycache_p1ff57 python scripts/mutation_probe_static.py tests/feature_engineering/test_ff_cross_symbol_value_isolation.py tests/feature_engineering/test_ff_wrapper_path_correctness.py` => pass by exit code 0, no stdout.
- skipped-slow: `test_v5_slow_solo_a_equals_batch_b_then_a_artifacts` is marked `@pytest.mark.slow`; local run skipped per assignment.

FAILURES_SEEN:
- Initial py_compile attempted to write bytecode under the user cache path and failed under sandbox restrictions; rerun used `PYTHONPYCACHEPREFIX=/tmp/codex_pycache_p1ff57`.
- Initial fast pytest had four failures from TA-Lib direct-call arity, direct FeatureFactory constructor use, broad fast config, and CGSA-backed empty in-memory frame assumptions; fixes stayed inside the three allowed test delivery files.

SCOPE_CHANGES:
- none.

NUMERIC_OR_SCHEMA_IMPACT:
- Tests only. No production numeric behavior, output schema, or artifact size changes.

STATUS: DONE

## FIX ROUND 1 — Composer BLOCKING closure

BLOCKING-1:
- Fixed V5.1 order semantics: solo `[A]`, same-factory `[A,B]`, and same-factory `[B,A]` are now distinct endpoints.
- Counterexample now blocked: pollution that appears only after B runs before A is covered by `b_then_a_factory` before the A assertion.

BLOCKING-2:
- Added runtime output manifest semantic summaries and V5.3 assertions for row/feature/schema/column-set invariants.
- Counterexample now blocked: A value equality with drifted metadata/schema fails `assert_manifest_semantics_equal`.

BLOCKING-3:
- Slow test now compares values plus manifest semantics and materialized d* artifacts under a real L6.5 fracdiff config.
- Counterexample now blocked: B-before-A disk metadata/d* drift for A fails manifest or symbol-scoped d* checks.

BLOCKING-4:
- Replaced M5.2 string-only proof with runtime monkeypatch of `_layer0_data_ingestion` so A receives wrong reference data through L5.
- Counterexample now blocked: poisoned reference values fail sampled equality on real `cs_*relative_price` output.

BLOCKING-5:
- Added cross-context d* miss, shared d* cache scoped path, runtime CGSA path coverage, and V7 storage manifest coverage.
- Deferred only batch checkpoint/RunLease and L7 artifact path-map deep coverage; not enough runtime surface inside the three-file scope without expanding test cost.

BLOCKING-6:
- Added `test_v5_4_runtime_cgsa_paths_are_symbol_scoped`, which runs `generate_features` with `FFACT_USE_CGSA=1` and checks real manifest/source registry paths.
- Counterexample now blocked: A runtime manifest or CGSA registry path containing B fails token checks.

BLOCKING-7:
- V7.4 now uses `FeatureStorage.write_processed`, `FeatureReader.load_columns_v2`, parquet schema metadata, and `feature_manifest.json`.
- Counterexample now blocked: missing `l7_encoding_registry`, missing encoded count, or storage roundtrip error beyond contract fails.

NON_BLOCKING:
- NB1 fixed: L6.5 sentinel now patches `_apply_fractional_differencing_serial` and keeps optimized/polars mutual-exclusion counters.
- NB2 partially fixed: L3 matrix now includes rank/skew/kurt; persist callback and numba-fallback probe not added in this three-file fast-tier round.
- NB3 partially fixed: L2 now has a pandas fallback raise sentinel; pathological numeric columns not added.
- NB4 not fixed via marker because `medium` is not registered and adding it would require editing `pytest.ini` outside scope; docstring labels V5.5 as medium.
- NB5 fixed: redundant second B run removed by explicit `[A,B]`/`[B,A]` factories.

TESTS_RUN_FIX_ROUND_1:
- `python -m py_compile tests/feature_engineering/ff_artifact_compare_helpers.py tests/feature_engineering/test_ff_cross_symbol_value_isolation.py tests/feature_engineering/test_ff_wrapper_path_correctness.py` => pass.
- `pytest --collect-only tests/feature_engineering/test_ff_cross_symbol_value_isolation.py tests/feature_engineering/test_ff_wrapper_path_correctness.py -q` => pass, 29 collected.
- `pytest tests/feature_engineering/test_ff_cross_symbol_value_isolation.py tests/feature_engineering/test_ff_wrapper_path_correctness.py -m "not slow" -q --tb=short` => pass, 28 passed / 1 deselected.
- `python scripts/mutation_probe_static.py tests/feature_engineering/test_ff_cross_symbol_value_isolation.py tests/feature_engineering/test_ff_wrapper_path_correctness.py` => pass, exit 0.

## FIX ROUND 2 — Composer CLOSURE ROUND 1 REOPEN items

BLOCKING-1 REOPEN:
- Fixed `test_v5_1_fast_order_permutation_keeps_hash_and_sampled_values`: `[A,B]` now runs A, then B, then runs A again on the same factory and compares the post-B A endpoint with solo A.
- Counterexample now blocked: a defect where A first succeeds, B mutates shared factory state, and the second A returns polluted values now fails hash/sample/manifest assertions.

BLOCKING-3 REOPEN:
- Added `symbol` to `manifest_semantic_summary` for both artifact manifests and runtime metadata fallback manifests.
- Added `dstar_payload_summary` / `assert_dstar_payloads_equal`, using `read_d_star_json` to compare solo(A) vs batch[B,A] A d-star payload semantics.
- Updated slow test to use separate solo and batch d-star cache dirs, then compare only the baseline symbol payloads; path-only checks remain as secondary symbol-scope checks.
- Counterexamples now blocked: `{symbol: BTC}` vs `{symbol: ETH}` manifests differ in helper summaries, and a correct A path with wrong A d-star payload fails payload equality.

TESTS_RUN_FIX_ROUND_2:
- `PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python -m py_compile tests/feature_engineering/ff_artifact_compare_helpers.py tests/feature_engineering/test_ff_cross_symbol_value_isolation.py` => pass.
- `pytest --collect-only tests/feature_engineering/test_ff_cross_symbol_value_isolation.py::test_v5_slow_solo_a_equals_batch_b_then_a_artifacts -q` => pass, 1 collected.
- `pytest tests/feature_engineering/test_ff_cross_symbol_value_isolation.py -m 'not slow' -q` => pass, 11 passed / 1 deselected.
- Slow full-chain test intentionally not run per assignment.

FAILURES_SEEN_FIX_ROUND_2:
- First py_compile attempted to write bytecode under `/Users/louis/Library/Caches` and failed under sandbox permissions; rerun used `PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache`.

SCOPE_CHANGES_FIX_ROUND_2:
- none; changed only `tests/feature_engineering/ff_artifact_compare_helpers.py`, `tests/feature_engineering/test_ff_cross_symbol_value_isolation.py`, and this append-only handoff.

NUMERIC_OR_SCHEMA_IMPACT_FIX_ROUND_2:
- Tests only. No production numeric behavior, schema, or output-size impact.

## FIX ROUND 3 — slow tier full-chain config repair

CHANGE:
- Replaced slow V5 config source from compact `fast_config_payload(...)` to `slow_full_chain_config_payload(reference_symbol=ETHUSDT)`.
- Slow V5 now uses the full common BTCUSDT/ETHUSDT 12h kline window from `data_cache/feature_klines/kline_cache.h5` instead of a 120-day slice; local data probe showed 1696 rows each, 2024-01-01 to 2026-04-27 UTC.
- Added config guard `assert_slow_full_chain_config(...)` and runtime guard `assert_full_chain_runtime(...)` so the slow test fails if L1-L6 are empty/disabled or L6.5 fracdiff/d* is not applied.

WHY_CONFIG_IS_FULL_CHAIN:
- Feature set: `preset=professional_full`, not compact; enabled atomic categories include trend/momentum/volatility/volume/statistics/cycle/pattern/tail_risk/microstructure/entropy.
- Data sources: close/open/high/low/volume/quote_volume/trades/taker_buy_volume/taker_ratio plus synthetic avg/med/typ/wcl price sources.
- Layers: L1 atomic, L2 operators, L3 rolling, L4 lag, L5 cross-sectional with `reference_symbol=ETHUSDT`, L6 meta, L6.5 preprocessing, and L7 persist are all configured on.
- L6.5: preprocessing enabled, causal, replace mode, winsor/rank/zscore/gaussian/ADF configured on, fractional_differencing enabled with d* cache enabled.
- Slow comparison remains solo(BTCUSDT) vs same-factory batch-like ETHUSDT→BTCUSDT to keep d* cache dir and BTC artifacts directly comparable inside the three-file test scope.

TESTS_RUN_FIX_ROUND_3:
- `PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python -m py_compile tests/feature_engineering/ff_artifact_compare_helpers.py tests/feature_engineering/test_ff_cross_symbol_value_isolation.py tests/feature_engineering/test_ff_wrapper_path_correctness.py` => pass.
- `pytest --collect-only tests/feature_engineering/test_ff_cross_symbol_value_isolation.py::test_v5_slow_solo_a_equals_batch_b_then_a_artifacts -q` => pass, 1 collected.
- `pytest tests/feature_engineering/test_ff_cross_symbol_value_isolation.py tests/feature_engineering/test_ff_wrapper_path_correctness.py -m "not slow" -q --tb=short` => pass, 28 passed / 1 deselected.
- `python scripts/mutation_probe_static.py tests/feature_engineering/test_ff_cross_symbol_value_isolation.py tests/feature_engineering/test_ff_wrapper_path_correctness.py` => pass, exit 0.
- Config probe only, no feature generation: `assert_slow_full_chain_config(make_factory(...), slow_full_chain_config_payload(ETHUSDT))` => pass; printed full data_sources and rolling/lag/cross/meta/fracdiff all enabled.

FAILURES_SEEN_FIX_ROUND_3:
- none.

SCOPE_CHANGES_FIX_ROUND_3:
- none; changed only `tests/feature_engineering/ff_artifact_compare_helpers.py`, `tests/feature_engineering/test_ff_cross_symbol_value_isolation.py`, and this append-only handoff.

NUMERIC_OR_SCHEMA_IMPACT_FIX_ROUND_3:
- Tests only. No production numeric behavior, schema, or output-size impact.

## FIX ROUND 4 — slow tier dimension repair + runtime full-chain gate

CHANGE:
- Repaired `slow_full_chain_config_payload` after real slow run evidence showed Round 3 generated 416,283 L3 columns and made L6.5 run 289 chunks x 2000 cols.
- Kept no-preset principle: slow config still explicitly enables all atomic categories via `_atomic_indicators_all_enabled()`, not `preset`.
- Reduced multiplicative factors: data sources now OHLCV + `quote_volume` + `taker_ratio`; synthetic sources now only `typ-price`; L3 windows `[13, 55]`; L3 aggregators `[mean, std, rank, zscore, min, max, range, slope]`; L4 custom lags `[1, 3]`; L6.5 keeps causal winsor + ADF + fracdiff/d* cache and disables generation-time rank/zscore/gaussian transforms.
- Upgraded `assert_slow_full_chain_config` to assert reduced dimensions explicitly, and upgraded `assert_full_chain_runtime` to require each L1-L6 `LayerExecutionResult.status == ok`, `present_engines > 0`, and `cols > 0`; L6.5 applied+fracdiff+d* evidence; L7 manifest/run output `feature_count > 0` and complete/ok status.
- Slow test now passes persisted runtime manifests into `assert_full_chain_runtime` before comparing solo(A) vs batch B->A.

SLOW_SIZE_PROBE_FIX_ROUND_4:
- Config-only probe passed: 10 atomic categories enabled; sources=`close/open/high/low/volume/quote_volume/taker_ratio`; synthetic=`typ-price`; L3 windows=`[13,55]`; L3 aggregators=8; custom lags=`[1,3]`.
- Layer count probe on real BTCUSDT/ETHUSDT 12h full common window 2024-01-01..2026-04-27, no L6.5/full generate: L1=3427 cols in 6.55s; L3=53,632 generated / 53,408 surviving cols in 14.42s, peak RSS log 834MB.
- Basis for runtime estimate: Round 3 L3=416,283 vs Round 4 L3=53,408 surviving => ~7.8x smaller L6.5 input by column count; expected to fit the single-generate ~20min target order instead of >70min L6.5.

TESTS_RUN_FIX_ROUND_4:
- `PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache_p1ff57_r4 python -m py_compile tests/feature_engineering/ff_artifact_compare_helpers.py tests/feature_engineering/test_ff_cross_symbol_value_isolation.py tests/feature_engineering/test_ff_wrapper_path_correctness.py` => pass.
- `pytest --collect-only tests/feature_engineering/test_ff_cross_symbol_value_isolation.py tests/feature_engineering/test_ff_wrapper_path_correctness.py -q` => pass, 29 collected.
- `pytest tests/feature_engineering/test_ff_cross_symbol_value_isolation.py tests/feature_engineering/test_ff_wrapper_path_correctness.py -m "not slow" -q --tb=short` => pass, 28 passed / 1 deselected.
- `python scripts/mutation_probe_static.py tests/feature_engineering/test_ff_cross_symbol_value_isolation.py tests/feature_engineering/test_ff_wrapper_path_correctness.py` => pass, exit 0.
- Slow full-chain test intentionally not run per assignment.

FAILURES_SEEN_FIX_ROUND_4:
- First count probe used nonexistent `KlineStorageManager.load_klines`; corrected probe to match `requires_kline_data` fixture path using `read_klines`.
- First reduced config was too small: measured L1=136 and L3=1,016 surviving cols. Repaired to full-open atomic plus shrunk source/L3/L4/L6.5 multipliers; final measured L3=53,408 surviving cols.

SCOPE_CHANGES_FIX_ROUND_4:
- none; changed only `tests/feature_engineering/ff_artifact_compare_helpers.py`, `tests/feature_engineering/test_ff_cross_symbol_value_isolation.py`, and this append-only handoff.

NUMERIC_OR_SCHEMA_IMPACT_FIX_ROUND_4:
- Tests only. No production numeric behavior, schema, or output-size impact.
