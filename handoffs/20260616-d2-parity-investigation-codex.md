# D2 parity investigation — Codex — 2026-06-16

## Scope
- Read-only diagnostics for #2 d* / T4 parity. No production code edits, no commits.
- Real input: `data_cache/feature_klines/kline_cache.h5`, BTCUSDT/12h, 2024-06-01 to 2024-12-01.
- Isolated outputs only under `/tmp/batch2d_parity_investigation/{frame,cgsa}/{features,d_star,cgsa_work}`.

## Commands / artifacts
- Full live diagnostic: `source venv/bin/activate && REPO_ROOT="$PWD" python - <<'PY' ...`
- Summary: `/tmp/batch2d_parity_investigation/summary.json`.
- d* JSONs:
  - frame: `/tmp/batch2d_parity_investigation/frame/d_star/d_star_BTCUSDT_12h_e7b598019841.json`
  - CGSA: `/tmp/batch2d_parity_investigation/cgsa/d_star/d_star_BTCUSDT_12h_e7b598019841.json`

## T3 d* parity result
- frame d* entries: 3,736.
- CGSA d* entries: 3,737.
- common d* keys: 3,458.
- exact matches on common keys: 3,458.
- mismatches on common keys: 0.
- frame-only d* keys: 278.
- CGSA-only d* keys: 279.
- Asymmetry is mostly naming/stage selection: 276 frame-only keys have a CGSA-only `_Abs`/`_Clip`/`_Log1p` suffix counterpart; example `close_statistics_LINEARREG_10` vs `close_statistics_LINEARREG_10_Abs`.

## T4 live value / index result
- frame features: 165,144; CGSA features: 165,185; delta = 41, same shape delta as P0 baseline control/cgsa (165,268 vs 165,309).
- L1/L2 expected provenance columns: 46,438 on both sides.
- Live L1/L2 present after L7/storage filtering: frame 37,400; CGSA 37,433; common present 37,400; CGSA-only present 33; frame-only present 0.
- Common present value hashes: 62 exact matches, 37,338 mismatches.
- NaN mask hashes: 37,400/37,400 match; 0 mask mismatches.
- Row index hashes differ because frame is `int64` epoch seconds named `timestamp`, CGSA is `datetime64[ns]` unnamed. Converting frame seconds to datetime gives the same full timestamp sequence as CGSA.

## T4 root cause
- Row-index mismatch is representation, not row loss or row shift: frame first/last `1717200000`/`1733011200` converts to CGSA first/last `2024-06-01 00:00:00`/`2024-12-01 00:00:00`, and full converted index equals CGSA.
- Value mismatch is not caused by index misalignment. Sample columns compared by position and normalized time still differ; simple +/-1 shifts do not match.
- Sample value deltas are small and consistent with storage dtype/precision divergence:
  - CGSA `FeatureReader.load_columns_v2(... raw ...)` returned `float16` for sampled L1/L2 columns.
  - frame HDF dataset `/BTCUSDT/12h/features` is `float32`.
  - Examples: `close_12h_trend_EMA_5` max finite abs diff `0.0008919239`; `close-volume_12h_statistics_BETA_13` max finite abs diff `0.0012998581`.
- Column-set gap is storage/L7 survival, not provenance absence. Provenance expects 46,438 L1/L2 columns, but post-L7/dead-drop outputs retain only 37,400/37,433. CGSA log reported `[L7 Dead Drop][CGSA] dropped 37332 cols ... final features=165185`; frame output count remains 41 below CGSA, matching the P0 baseline delta.

## Relationship to #2
- #2 frame-path selection fix is effective at the d* oracle layer: frame no longer fracdiff no-ops, and common d* values are exact-equal to CGSA.
- T4 exact value differences are existing CGSA-vs-frame storage/structure differences: index representation, post-storage survival/dead-drop inventory, and float16-vs-float32 value materialization.
- Evidence this is not introduced by #2: P0 baseline already has the same total column delta of 41 (control 165,268 vs CGSA 165,309), and T4 differences are outside SPEC's named scope of L1/L2 fracdiff selection + d* parity.

## Conclusion
- #2 alignment target is achieved at T3 d* parity for all common d* keys: 3,458/3,458 match, 0 mismatch.
- T4 exact value parity should be classified as existing structural/value-materialization divergence and out-of-scope for #2, unless a future SPEC explicitly targets frame/CGSA storage dtype, index canonicalization, and dead-drop parity.

## Structured closeout
ASSUMPTIONS_VERIFIED: T3 common d* exact equality; frame/CGSA index normalized equality; T4 value mismatch not row-shift; CGSA sampled raw dtype float16 vs frame HDF float32; L1/L2 post-L7 survival differs from provenance.
TESTS_RUN: Full live diagnostic PASS; h5py/FeatureReader sample compare PASS; pandas HDFStore inspection FAIL due missing pytables HDF5 dylib but replaced by h5py read.
FAILURES_SEEN: First diagnostic script used wrong `/tmp`-derived repo root and was blocked by sandbox before repo writes; fixed by passing `REPO_ROOT`. pandas HDFStore unavailable due missing `/opt/homebrew/opt/hdf5/lib/libhdf5.310.dylib`; used h5py.
SCOPE_CHANGES: none; no production files modified.
NUMERIC_OR_SCHEMA_IMPACT: none from this investigation; observed existing CGSA float16 vs frame float32 and index dtype divergence.
STATUS: DONE — T3 d* parity common=3458 match=3458 mismatch=0; conclusion=#2 d* alignment achieved, T4 value parity is existing CGSA/frame structural divergence out-of-scope
