# FRACDIFF_MAXLAG SPEC/TODO adversarial review — Codex

Task-id: fracdiff-maxlag-adv-codex-20260703  
Scope: read-only review of `docs/FRACDIFF_MAXLAG_{SPEC,TODO,MANIFEST,EPIC_BRIEF}.md`, background `handoffs/20260702-FF-DSTAR-GATE-{CLAUDE,CODEX,COMPOSER}.md`, and relevant code paths.

## Verdict: 需修補後派工

The repair direction is correct: current production derives fracdiff `max_lag` from `len(df)` (`feature_preprocessor.py:3198-3200`), while d* search uses calibration-prefix values but passes that lag into FFD weights (`feature_preprocessor.py:3699,3733-3739`). However, the SPEC/TODO still has verification holes that can produce false confidence.

## BLOCKING findings

1. **[BLOCKING][High] §G “byte-level” golden is implemented as sampled hashes, so it can miss value drift.**  
   Evidence: SPEC says baseline is “抽樣 value hash + NaN mask hash” (`docs/FRACDIFF_MAXLAG_SPEC.md:32`); TODO repeats “抽樣 value hash” (`docs/FRACDIFF_MAXLAG_TODO.md:45`). But the pass condition claims “byte 級一致” (`SPEC:34-35`). Project test charter requires high-risk data correctness/value conservation to be full, not sampled: “資料正確性…值守恆 100%(非抽樣)” and numeric golden should track exact NaN positions and per-column values (`docs/TEST_DESIGN_CHARTER.md:22,28`).  
   Failure mode: a localized fracdiff or non-fracdiff drift outside the sample passes §G and later IC consumes silently changed features.  
   Fix: change §G/Task 0.1/Task 3.1 to require full per-column `value_sha256`, `nan_mask_sha256`, dtype, row index hash, and feature order/schema hash. Mean/std/nan_ratio can stay as human-readable diagnostics, not the oracle.

2. **[BLOCKING][High] G2 pin=50 vs repaired auto=50 can share the same d* cache key, making §G condition 1 tautological unless caches are isolated.**  
   Evidence: DStarCache path uses symbol, timeframe, and `fracdiff_hash` only (`_d_star_cache.py:327-331`). The hash records resolved `max_lag`, not whether it came from explicit config or auto (`_d_star_cache.py:206-228,302-308`). `FeaturePreprocessor._d_star_cache_dir()` defaults to shared `data_cache/feature_preprocessing` (`feature_preprocessor.py:2949-2951`). G2 before the patch with explicit `max_lag=50` and repaired auto after the patch with resolved `max_lag=50` can therefore address the same cache file.  
   Failure mode: the repaired run can hit d* values written by G2 and pass “修後預設跑 vs G2 byte 級一致” without proving the repaired auto derivation and d* recomputation are correct. This directly weakens the requested “pin max_lag=50 ≡ 修後 auto” proof.  
   Fix: require isolated empty d* cache dirs per run, or run §G with `cache_d_star=False` plus a separate cache-enabled parity check. Record d_star cache hit/miss counts and cache paths in receipts. If comparing cache behavior is desired, make it a distinct test.

3. **[BLOCKING][High] Task 1.4 overstates old-cache invalidation; “old cache must miss” is false for old explicit pin=50 caches.**  
   Evidence: SPEC says old cache file load must miss (`docs/FRACDIFF_MAXLAG_SPEC.md:64`); TODO says test an old cache “含舊 max_lag hash” and expect miss (`docs/FRACDIFF_MAXLAG_TODO.md:87`). But `_compute_fracdiff_hash` includes resolved `max_lag` (`_d_star_cache.py:218-228`), so old auto 600-row cache (`max_lag=60`) should miss after repair, while old explicit pin=50 cache should match repaired auto=50 if other payload fields match. Payload validation also checks `row_count`/`time_range` (`_d_star_cache.py:421-426`) and integer `max_lag` (`_d_star_cache.py:439-447`).  
   Failure mode: implementer may write a too-broad test that expects every pre-patch cache to miss, then either fails valid cache reuse or changes cache semantics unnecessarily.  
   Fix: split into two cases: (a) pre-patch auto len-derived cache with max_lag != 50 must miss; (b) pre-patch explicit pin=50 cache may hit only if payload and per-column strong value fingerprints match. Tie this back to the §G cache isolation requirement above.

4. **[BLOCKING][High] Task 2.2 mutation probe is not executable as written because the derivation point is an inline local expression with no seam to monkeypatch.**  
   Evidence: TODO says “monkeypatch 推導點使 max_lag=len(df)//10” (`docs/FRACDIFF_MAXLAG_TODO.md:112`), but the derivation is inline inside `_apply_fractional_differencing` (`feature_preprocessor.py:3198-3200`), then passed as a local variable to cache, serial, and parallel paths (`feature_preprocessor.py:3207-3221,3232-3273`). There is no resolver method/function to patch.  
   Failure mode: implementer either monkeypatches the whole `_apply_fractional_differencing` method, duplicating production logic in the test, or writes a source-inspection test. Both can pass while the actual production branch is not probed.  
   Fix: make Task 1.1 introduce a small resolver seam, e.g. `_resolve_fracdiff_max_lag(row_count: int) -> int`, used by production and directly monkeypatchable. Then Task 2.2 can patch only that resolver and prove the MR fails.

5. **[BLOCKING][High] Task 2.3’s “fingerprint” mutant targets a field that is not a v3 production cache key/payload guard.**  
   Evidence: TODO requires removing “fingerprint” from key/payload (`docs/FRACDIFF_MAXLAG_TODO.md:121-122`). Current DStarCache path key is symbol/timeframe/fracdiff_hash (`_d_star_cache.py:327-331`); base payload includes symbol, timeframe, fracdiff_hash, row_count, time_range, source_data_version, etc., but not `data_fingerprint` (`_d_star_cache.py:451-473`). Production serial/parallel cache access passes per-column calibration values and validates `strong_value_fp`/`value_fp` (`feature_preprocessor.py:3035-3050,3092-3100`; `_d_star_cache.py:501-527,543-561`). `data_fingerprint` only matters in the backward-compatible no-col-values path (`_d_star_cache.py:493-499,562-564`).  
   Failure mode: the required mutant cannot be written against the stated field, or it tests legacy behavior rather than the production v3 path. This creates a fake “cache isolation probe” for P1-FF-6.  
   Fix: define separate mutants for actual production guards: path symbol, path timeframe, `fracdiff_hash`, payload `row_count`, payload `time_range`, and per-column `strong_value_fp`/value aliasing. If `data_fingerprint` is intentionally legacy-only, document it as N/A rather than a required mutant.

6. **[BLOCKING][Medium] Task 2.2 says the mutant must prove both MR tests fail, but the TODO verification only asserts `_assert_d_star_gate` fails.**  
   Evidence: Manifest requires “[B-1] 兩測試必轉紅” (`docs/FRACDIFF_MAXLAG_MANIFEST.md:39-42`); SPEC says “兩 MR 必 FAIL” (`docs/FRACDIFF_MAXLAG_SPEC.md:72-74`). TODO narrows this to “跑縮小版 fracdiff MR（600→590）→ 斷言 `_assert_d_star_gate` 拋 AssertionError” (`docs/FRACDIFF_MAXLAG_TODO.md:112,117`). Existing two MR tests are truncation and tail perturbation (`test_ff_fullchain_truncation_mr.py:120-155`).  
   Failure mode: one mutation test on one pair proves the d* gate can fail in one scenario, but does not prove both xfail removals are protected. Tail-perturbation could remain unprotected.  
   Fix: either require two mutation checks, one for each MR, or explicitly revise manifest/SPEC to say the mutation probe protects the shared d* gate and explain why that is sufficient.

## NON-BLOCKING findings

1. **[NON-BLOCKING][High] `_native_tf_helpers.py` path is ambiguous/wrong in docs.**  
   Evidence: SPEC/TODO refer to `_native_tf_helpers.py` without path (`docs/FRACDIFF_MAXLAG_SPEC.md:63`; `TODO:87`), while the real file is `momentum/FeatureEngineering/preprocessing/_native_tf_helpers.py`; `rg` finds `_SAMPLE_SIZE_KEYS = ("sample_size", "max_lag")` at lines 96-118.  
   Failure mode: implementer may skip the file during the scan.  
   Fix: use the full path in SPEC/TODO.

2. **[NON-BLOCKING][Medium] Warmup 252 fallback is probably acceptable, but the SPEC should state why it does not affect §G output row count for the default config.**  
   Evidence: warmup appends `calibration_bars` before max_lag (`warmup_window.py:290-295`), and `_calibration_bars()` is at least 500 (`feature_preprocessor.py:175-178`). Therefore default `max_lag=252` does not dominate warmup when calibration_bars is 500.  
   Failure mode: reviewers may think G2 explicit max_lag=50 and repaired auto max_lag=0 produce different trim sizes.  
   Fix: add this reasoning to Task 1.3, and include a row-count/index equality assertion in §G.

3. **[NON-BLOCKING][Medium] Short-df behavior is intentionally changing but under-specified.**  
   Evidence: SPEC says `df=300` still resolves `max_lag=50` (`docs/FRACDIFF_MAXLAG_SPEC.md:46`; `TODO:60`). `_calibration_series` on 300 rows uses 300 rows (`feature_preprocessor.py:180-187`), and `_fracdiff_values` returns all NaN only when filled slice size is smaller than weight width (`feature_preprocessor.py:3736-3739`), not merely when df is below calibration_bars.  
   Failure mode: the edge test may assert only “does not crash” and miss increased leading NaNs or changed d*.  
   Fix: define the expected short-df oracle: resolved max_lag=50, output row count unchanged, no exception, finite/nonfinite behavior recorded, and no weakening of NaN/inf gates.

4. **[NON-BLOCKING][Low] Task 1.2 should name the exact Pydantic idiom.**  
   Evidence: SPEC leaves negative config as “validator 拒或視同 auto” (`docs/FRACDIFF_MAXLAG_SPEC.md:53`); TODO chooses `ge=0` (`docs/FRACDIFF_MAXLAG_TODO.md:67,70`).  
   Failure mode: minor implementation churn.  
   Fix: update SPEC to match TODO: `max_lag: int = Field(default=0, ge=0)`.

## 被當成事實的未驗證假設

- “修後預設跑 vs G2 byte 級一致證明變更純由窗寬造成” is an assumption unless cache isolation and full per-column value hashing are required. Current docs only require sampled hashes and do not prevent G2 d* cache reuse.
- “舊 cache 檔存在時載入必 miss” is only true for old auto len-derived cache entries with a different resolved `max_lag`; it is false for old explicit pin=50 caches.
- “fingerprint mutant” assumes data fingerprint is a current production cache guard. In v3 production access, per-column strong value fingerprints are the real guard; `data_fingerprint` is backward-compat/no-col-values behavior.

## Required spec fixes before implementation

1. Replace sampled golden hashes with full per-column value/mask/index/dtype hashes.
2. Add §G cache isolation or cache-disabled recomputation rules, and record d* cache hit/miss/path.
3. Split old-cache invalidation into old-auto miss vs explicit-pin50 allowed hit.
4. Add a monkeypatchable max_lag resolver seam, then target it in Task 2.2.
5. Redesign B-3 around actual DStarCache v3 guards: path symbol/timeframe, fracdiff_hash, row_count, time_range, strong value fingerprint/value aliases.
6. Decide whether B-2 must mutate both MR tests or only the shared d* gate, and make SPEC/manifest/TODO consistent.

ASSUMPTIONS_VERIFIED: current max_lag is len(df)//10 when config max_lag<=0; d* search uses calibration prefix but FFD weights use passed max_lag; DStarCache hash includes resolved max_lag and path excludes auto-vs-explicit provenance; payload validates row_count/time_range; production cache access uses per-column value fingerprints; warmup default includes calibration_bars>=500 before max_lag.
TESTS_RUN: read-code/document review only; no pytest run.
FAILURES_SEEN: none during review.
SCOPE_CHANGES: none; wrote only this handoff file.
NUMERIC_OR_SCHEMA_IMPACT: none from this review; findings concern planned numeric/schema validation.

STATUS: DONE
