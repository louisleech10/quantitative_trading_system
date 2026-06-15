# Batch 3 Committee Technical Investigation (Codex)

- Date: 2026-06-15
- Scope: read-only investigation; no production/test edits
- Background: `docs/BATCH3_TEST_TRIAGE.md`

## Q1 Retention correctness

**Conclusion: choose B, add `last_generated_at`; keep `created_at` as first creation time.**

Evidence:
- `FeatureRegistry.add()` creates an incoming timestamp, then preserves the old `created_at` on same-key upsert: `momentum/FeatureEngineering/feature_registry.py:86-106`.
- Normal generation calls registry `add()` without an explicit timestamp, so every completed regeneration has a fresh time available before merge: `momentum/FeatureEngineering/feature_factory.py:3320-3329`.
- Retention sorts unnamed runs only by `created_at`, newest first, then deletes after `keep_latest`: `momentum/FeatureEngineering/run_lifecycle.py:132-165`.
- `created_at` is exposed as creation/display metadata and converted to an API timestamp: `tests/api/test_run_lifecycle_api.py:320-334`. Changing its meaning to "last generated" would silently rewrite user-visible history.

Why:
- C is incorrect for the stated policy: a just-regenerated old config remains old in retention order and can be deleted immediately after use.
- A fixes deletion order but overloads `created_at`, destroys first-created history, and changes `find_latest()` semantics (`feature_registry.py:124-128`).
- B separates immutable identity history from retention recency and supports future auditing without ambiguity.

Recommended fix:
- On every successful same-key `add`, preserve `created_at` and alias, but set `last_generated_at` from the incoming generation timestamp.
- Sort retention by `last_generated_at`, with `created_at` fallback for legacy entries; do not perform a destructive migration.
- Add tests proving a regenerated old unnamed run moves into the retained five, while alias and original `created_at` remain unchanged.

Confidence: **High (0.95)**.

## Q3 Winsorization numerical divergence

**Conclusion: production causal rolling winsorization is correct; this failing test is stale. It is not evidence that `_winsorize_2d_inplace` is numerically broken.**

Evidence:
- `FeaturePreprocessor` defaults `causal_preprocessing=True`: `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:130-142`.
- `_winsorize_2d_legacy_equivalent()` now uses rolling quantile bounds when causal mode is enabled, and only calls global `_winsorize_2d_inplace()` when causal mode is disabled: `feature_preprocessor.py:2331-2356`.
- `_winsorize_2d_inplace()` computes one full-sample pair of bounds and clips the whole matrix: `feature_preprocessor.py:2863-2881`. That is a valid legacy/non-causal primitive, but is not a valid PIT oracle for default production behavior.
- The failing helper omits `causal_preprocessing`, so it receives the new default `True`: `tests/test_winsorize_partition_opt.py:31-51`. The test then incorrectly compares rolling causal output against global full-sample output: `tests/test_winsorize_partition_opt.py:295-324`.
- Dedicated causal tests compare rolling output to a pandas rolling oracle and prove future perturbations do not alter earlier rows: `tests/feature_engineering/preprocessing/test_causal_winsor.py:29-77`.
- Git history identifies the intentional change: commit `fff522b` (2026-06-08), `fix(feature-factory): L1-L4 preprocessing causalization, eliminate full-sample look-ahead`.
- Reproduction: targeted pytest reported 61/2250 mismatches (2.71%), max abs 0.82011563. This magnitude is expected from different algorithms/windows, not float32 rounding.

Recommended fix:
- Update this test into two explicit contracts: causal mode compares against the rolling PIT oracle; `causal_preprocessing=False` compares `_winsorize_2d_legacy_equivalent` against `_winsorize_2d_inplace`/`np.nanquantile`.
- Keep the existing future-perturbation invariant. Do not change production back to full-sample bounds and do not loosen tolerances.
- Separately retain direct partition-vs-`np.nanquantile` tests for the non-causal primitive (`test_winsorize_2d_inplace_same_result` and `_large`).

Confidence: **Very high (0.99)**.

## Q4 V2 timestamp golden drift

**Conclusion: intentional schema-version change, not feature-set regression. Update only the committed schema hash baseline.**

Evidence:
- The golden fixture still contains `d04e1ae0...`: `tests/_golden/v2_ts/g1_baseline_fingerprint.json:21-44`.
- The test fixture feature set remains exactly group `g`, columns `a,b`: `tests/feature_engineering/test_v2_timestamp_golden.py:117-136`.
- Current hash payload includes schema version plus group/column names: `momentum/FeatureEngineering/feature_storage.py:1417-1429`.
- Current raw schema version is `raw_v2`: `feature_storage.py:681-684`. Hashing `{schema_version: raw_v2, groups: {g: [a,b]}}` yields the observed `93ef6756...`.
- The committed `d04e1ae0...` is exactly the same columns under `raw_v1`.
- Commit `7427c72` (2026-06-11), fail-open Batch 3, intentionally changed `L7_RAW_SCHEMA_VERSION` from `raw_v1` to `raw_v2` to add completeness/failure semantics. The baseline originated earlier in commit `fd3ce6a` (2026-06-08) and was not refreshed.
- Reproduction differed only in `feature_schema_hash`; feature parquet fingerprints, groups, row count, dtype, and total feature count matched.

Recommended fix:
- Refresh only `manifest_allowlist.feature_schema_hash` to `93ef6756efafdba58023f6c09f9ac872c11f19ccf1c754952b7cfc4153016468`.
- Add a short baseline note tying the value to `raw_v2`/commit `7427c72`; do not regenerate unrelated parquet fingerprints or file-size fields.

Confidence: **Very high (0.99)**.

## Q5 Missing `tr_` columns under partial engine failure

**Conclusion: tail-risk is generated and still named `tr_`; the failure is a stale/incorrect result-inspection contract in streaming CGSA, not a tail-risk engine defect.**

Evidence:
- Tail-risk remains explicitly enabled by the test and scheduled independently from microstructure: `tests/momentum/test_feature_factory_optimization_e2e.py:177-190`; `momentum/FeatureEngineering/feature_factory.py:794-811`.
- Optional engine failures are isolated; a failed microstructure engine appends an empty frame while successful engine frames continue: `feature_factory.py:836-895`.
- Tail-risk implementation still emits `tr_*` columns: `momentum/FeatureEngineering/atomic/tail_risk_indicators.py:68-85,117-188`.
- Reproduction logged Layer 1 `engine_partial` with 26 features. The generated CGSA manifest contained 26 `tr_` columns, including `tr_cvar_*`, `tr_gpr_*`, and `tr_mdd_*`.
- The test helper falls back to `result.metadata["feature_names"]` when `features_df` is empty: `tests/momentum/test_feature_factory_optimization_e2e.py:80-84`.
- Streaming CGSA intentionally returns an empty `features_df`, but also hardcodes metadata `feature_names` to `[]`: `momentum/FeatureEngineering/feature_factory.py:3096-3114,3163-3173`. Therefore every prefix assertion fails, including tail-risk-only and all-new-features tests, despite persisted registry columns being present.
- This empty-name behavior entered with streaming/sharded Phase-B commit `816b3f8` (2026-05-11); it is not a rename or disabled-default change. Tail-risk default is disabled but the test explicitly enables it: `momentum/FeatureEngineering/feature_config.py:148-154`.

Recommended fix:
- Prefer updating these E2E assertions to inspect the canonical CGSA registry/manifest schema (or a bounded schema-summary API), because the streaming result deliberately avoids materializing the full frame.
- Do not add the full feature-name list to every production response without an explicit output-size decision; real runs may contain thousands of columns.
- Add one partial-failure assertion for `failed_engines == ("microstructure",)`/`engine_partial`, plus a manifest assertion that `tr_` columns remain and `ms_` columns are absent.

Confidence: **High (0.97)**.

## Verification summary

ASSUMPTIONS_VERIFIED: retention sort key and upsert semantics inspected; causal default and PIT oracle confirmed; raw_v1/raw_v2 hashes recomputed; real-kline CGSA run confirmed 26 persisted `tr_` columns.
TESTS_RUN: targeted 3-test reproduction = 3 failed as reported; tail-risk-only + all-new-features reproduction = 2 failed due empty result metadata, while generation logs/manifests showed expected columns.
FAILURES_SEEN: Q3 61/2250 mismatch; Q4 only schema hash mismatch; Q5 prefix assertions fail because streaming metadata names are empty.
SCOPE_CHANGES: none; only this report added.
NUMERIC_OR_SCHEMA_IMPACT: none from this investigation. Recommended Q3 test correction preserves causal production numerics; recommended Q4 baseline update records intentional raw_v2 schema only.

STATUS: DONE
