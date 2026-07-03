# fracdiff max_lag 三方值守恆簽核 — Codex adversarial 腿

> 2026-07-03 | task-id: fracdiff-maxlag-signoff-codex-20260703 | scope: read-only audit + this file

## 結論

**PASS（限縮範圍：raw feature values / dtype / index / schema order 的 canonical digest 等價；不簽整個 artifact 目錄 byte-identical）。**

## 我親自核對的 receipt

- `20260703T042407Z-fracdiff-maxlag-golden-{G1,G2}.json/.log`
  - G1 two-run stability PASS；BTC/ETH frame digest repeat identical。
  - G1 resolved `max_lag=208`，G2 resolved `max_lag=50`；`fracdiff_hash` 由 `84c11...` 變 `dcc154...`。
  - G1 vs G2 陽性對照有效：非 fracdiff 欄 0 diff；fracdiff diff BTC=4546、ETH=3435。
  - G2 pin 方法明確是 `preprocessor_instance_fracdiff_config_injection`，且 wrapper 作用域有還原邏輯。
- `20260703T085226Z-fracdiff-maxlag-postfix-compare.json/.log`
  - `passed=true, failures=[]`。
  - R vs G2：BTC/ETH 全欄 0 diff，row/index 相等。
  - R vs G1：非 fracdiff 0 diff，fracdiff diff BTC=4546、ETH=3435，G1 actual max_lag=208。
  - G2P vs R：全欄 0 diff；真 config path pin=50 已通。
- `20260703T094044Z-fracdiff-maxlag-convfix-slow.log`
  - max_lag mutation probes passed；tail MR failure is storage codec family, not max_lag equivalence.
- `20260703T132059Z-fracdiff-maxlag-d2-control-final.log`
  - D2 redesigned control receipt shows `1 passed in 1061.68s`。
- `20260703T053419Z-mutation-test_dstar_cache_key_mutation.{json,log}`
  - 7 mutation probes passed; includes max_lag/calibration_bars hash, row_count/time_range, path symbol/timeframe, strong value fingerprint.

## 方法論獵漏

- Digest oracle：`tests/feature_engineering/ff_maxlag_golden_helpers.py` uses full-column value bytes + full NaN mask + dtype + index hash + schema hash; `canonical_raw_dir_digests()` streams every parquet file, not sampled rows. PASS。
- Compare script weak spot：`_digest_columns_equal()` does not directly check `schema_hash`; however the receipts include `frame_digest_sha256`, and I independently checked R/G2/G2P frame digests match for BTC and ETH. Since frame digest includes schema hash, actual receipt closes the column-order gap. PASS with note。
- Cache freshness：freeze/compare scripts require per-run `d_star_cache` dir empty before generation and use unique artifact paths. Receipt `cache_stats` showing `hits=1, misses=0` should not be cited as "fresh miss" proof; those counters reflect in-run cache reuse/aliasing, not old-cache reuse. Freshness is supported by empty-dir assertion + unique paths. PASS。
- G2 pin chain：G2PIN Codex/Composer both verified production config path originally dropped `max_lag`; freeze used instance `fracdiff_config` injection, then postfix G2P verified true schema/config path equals G2. PASS。
- R3 pre-existing statement：R3 reconcile has codex+composer APPROVED stamps on same sha; source/log evidence confirms per-column parquet codec selection depends on full-window values. Claude's §3 is honest and includes the MRFAIL prediction correction. PASS。

## Active Counterexamples Tried

- Symbol swap: BTC and ETH both satisfy R==G2 and G2P==R; not a single-symbol coincidence.
- Window sensitivity positive control: G1 max_lag=208 differs from pin50 and produces fracdiff diffs while non-fracdiff remains equal; oracle can detect real fracdiff changes.
- Dtype/index/schema order: canonical helper covers dtype/index/schema; receipt frame digests equal for R/G2/G2P on both symbols.
- Metadata/artifact surface: `feature_manifest.json` SHA and config_hash differ across G2/R/G2P. This would break a stronger "whole artifact byte-identical" claim, but not SPEC §G value conservation. Timestamps parquet SHA matched.
- Cache contamination: no shared d_star path across G1/G2/R/G2P; unique paths and empty-dir assertions prevent old-cache replay. The hit/miss summary is ambiguous but not evidence of contamination.
- Control-path weakness: original D2 control was invalid after conv fix; R3+D2MATCH narrowed accepted failure paths to strict columns gate or d_star, and final receipt passed.

## Claude 腿漏洞/修正

- Claude PASS is acceptable, but its wording "cache hit/miss" is slightly overconfident if read as final counters proving first-run misses. The stronger evidence is directory isolation.
- Claude should not imply full artifact equality. Manifests/config_hash differ; the valid signed claim is raw feature values/dtypes/index/schema order conservation under the canonical oracle.

ASSUMPTIONS_VERIFIED: receipts opened and cross-checked; helper oracle read; compare/freeze scripts read; G2PIN/R3/D2 evidence read; metadata counterexample probed by SHA.
TESTS_RUN: no new pytest; read-only receipt/source audit plus local Python JSON/parquet metadata inspection.
FAILURES_SEEN: none in this audit; referenced historical failures are 094044Z tail codec fail and invalid D2 DID NOT RAISE.
SCOPE_CHANGES: none; only wrote this handoff file.
NUMERIC_OR_SCHEMA_IMPACT: none from this task.
STATUS: DONE
