# B1 Codex Code Review + Data Sign-off

**Reviewer**: Codex | **Date**: 2026-06-28  
**Scope**: B1 diff for `docs/FF_DEEPAUDIT_P0_SPEC.md` / `docs/FF_DEEPAUDIT_P0_TODO.md` Task 1.0-1.4.  
**Verdict**: CODE REVIEW HOLD. BUG-1 L1 data semantics PASS; BUG-2 data correctness HOLD.

## A. Code Review

### A1 防假綠 / correctness mode
- **PASS with caveat**: I did not find weakened/deleted existing assertions. `tests/feature_engineering/test_adf_safe_skip.py` migrated old BETA/CORREL names to the new hl + CloseVolume names, not a threshold relaxation.
- **PASS**: correctness mode is wired through `FactoryConfig.fail_open_indicators`, `FeatureFactory._inject_fail_open()`, and atomic engines via `compute_guard.py`; production default remains fail-open.
- **Caveat**: only the MFI/momentum path has a direct correctness-mode regression test. The other engine wiring is code-inspected, not independently fault-injected.

### A2 mutation 真 FAIL
- **FAIL / HOLD**: C1-2 true source mutation is fake-green.
  - I temporarily removed `"ATR"` from `TALibWrapper._INPUT_TYPE_MAP["hlc"]` and ran:
    `pytest tests/feature_engineering/atomic/test_prepare_inputs_equivalence.py::test_prepare_inputs_byte_equal_to_semantics_table --tb=short -q`
  - Result: **15 passed**, including `ATR`.
  - Root cause: `build_talib_input_semantics()` derives the oracle semantics from `TALibWrapper.list_indicators()`, so the source mutation contaminates both system-under-test and oracle. The in-test mutation probe only proves a cached/constructed mismatch can be detected; it does not prove the real registry mapping mutation fails.
- **PARTIAL**: C1-1 RSI close→open and BUG-2 EOM `*`→`/` probes are implemented as test-local monkeypatches and pass as probes. I did not treat them as full source-mutation evidence.

### A3 BUG-1 completeness
- **PASS**: `BETA`/`CORREL` now resolve to `hl`; `Beta_CloseVolume`/`Correl_CloseVolume` alias to TA-Lib `BETA`/`CORREL` over close+volume.
- **PASS**: metadata marks CloseVolume aliases as `variant=non_standard_close_volume`.
- **PASS**: `adf_safe_skip.py` keeps hl `CORREL` safe-skip, adds `Correl-CloseVolume`, and keeps `BETA` / `Beta-CloseVolume` out of ADF skip.
- **PASS**: UI display names distinguish high/low canonical and close/volume non-standard variants.
- **HOLD for §G closure**: Consumer checklist only documents old golden/provenance impact; it does not perform v1 re-freeze or prove unaffected L2-L7 value hashes exact. That may be intentionally deferred to Claude, but it means I cannot sign full Affected Column Closure yet.

### A4 解耦 / logging
- **PASS**: `grep -r "from api\\." momentum/` returned 0 results.
- **PASS**: new momentum code uses `momentum.core.logging`; API file uses `api.core.logging` only inside `api/`.

### A5 price_transform / cycle / statistics / custom coverage
- **PASS**: cycle/statistics have direct TA-Lib samples (`HT_DCPERIOD`, `STDDEV`).
- **PASS with caveat**: price_transform is explicitly tested as adapter-owned empty wrapper policy for `AVGPRICE/MEDPRICE/TYPPRICE/WCLPRICE`, not value oracle.
- **WEAK / HOLD**: custom coverage is only `CustomIndicatorEngine` empty-definition smoke; no custom function oracle or failure-path coverage.

## B. 三方數據簽核腿

### BUG-1
- **SIGN-OFF: BUG-1 PASS at L1 atomic semantics**
- Evidence:
  - `test_beta_correl_dual_oracle`: standard `BETA/CORREL == talib(high, low)`.
  - CloseVolume aliases preserve old semantics: `Beta_CloseVolume/Correl_CloseVolume == talib(close, volume)`.
  - Diff table shows old vs new semantic change and old vs alias `max_abs_diff=0.0`.
- Limitation:
  - **SIGN-OFF does not include full L2-L7 closure** because v1 golden/provenance re-freeze and unaffected-column hash proof are not present in B1.

### BUG-2
- **SIGN-OFF: BUG-2 HOLD**
- Reason:
  - Current implementation keeps simplified Klinger/ForceIndex/EOM and documents `variant=simplified`; it does not correct Klinger to canonical.
  - `tests/_golden/ff_deepaudit/handcoded_variant_diff.json` reports Klinger corr `0.17617928579954434` vs canonical and ForceIndex corr `0.5163413653158025`. That is a large semantic divergence, not merely a harmless naming/doc issue.
  - The tests verify production simplified formulas against simplified references. That is useful golden-locking, but it is not evidence that the simplified data is "correct" for quant use.
- Required decision:
  - Committee/user should explicitly decide whether to retain simplified variants as intentionally non-canonical features, rename them to make the simplification first-class, or replace them with canonical implementations.

## Commands Run
- `pytest tests/feature_engineering/atomic/ tests/feature_engineering/test_adf_safe_skip.py -v --tb=short` → **176 passed**
- `grep -r "from api\\." momentum/` → **0 results** (exit 1, no matches)
- True mutation check: remove `ATR` from `_INPUT_TYPE_MAP["hlc"]`, run C1-2 positive test → **15 passed** (unexpected fake-green); source restored.

## Structured Close
ASSUMPTIONS_VERIFIED: Read HANDOFF.md, CLAUDE.md, B1 review prompt, SPEC/TODO, B1 RESULT, Consumer Sync, diff, tests, and golden diff tables. Verified BUG-1 L1 oracle behavior and C1-2 true mutation fake-green.  
TESTS_RUN: `pytest tests/feature_engineering/atomic/ tests/feature_engineering/test_adf_safe_skip.py -v --tb=short` pass 176; `grep -r "from api\\." momentum/` 0 matches; temporary ATR source mutation C1-2 positive test unexpectedly pass 15.  
FAILURES_SEEN: C1-2 true source mutation did not fail, so mutation evidence is insufficient.  
SCOPE_CHANGES: none; only this review handoff file added.  
NUMERIC_OR_SCHEMA_IMPACT: BUG-1 changes BETA/CORREL L1 schema/semantics and adds CloseVolume aliases; BUG-2 remains simplified with metadata only; full L2-L7 closure not signed.  
STATUS: DONE
