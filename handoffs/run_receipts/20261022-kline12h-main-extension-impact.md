# 12h K 線往前延長：影響盤點（read-only，2026-10-22）

Scope: prepend real Binance 12h bars (~2019/2020) to `data_cache/feature_klines/kline_cache.h5` for 10 symbols; 1h/4h untouched.
Method: code reading + read-only h5py probes (scripts in this scratch dir: inspect_h5.py, compare_longhist.py, famB_d0.py, famC_d0.py, famD_ts.py). No pytest, no freeze, no generation, no network, no repo writes.
Per-family detail with file:line: appendices A–E (fam_A..fam_E) below.

## 0. Current file facts (probe: inspect_h5.py)
- 10 symbols × {1h,4h,12h}; all start 2024-01-01 00:00; 12h end 2026-04-27 12:00 = 1696 bars; 4h 5088; 1h 20352. File mtime 2026-04-28, 9.9 MB.
- Layout: `/<SYMBOL>/<tf>/data` (structured array: timestamp i8, open/high/low/close/volume/taker_buy_volume/taker_ratio/quote_volume f4, number_of_trades i4) + tf-group attrs (time_range_start/end, total_bars, data_checksum, data_source, is_complete, last_updated) + `/_metadata` attrs (cache_index JSON, version, created_at, last_updated). `kline_storage.py:261-290, 742-857`.

## 1. Fetch mechanism
- Provider: `momentum/DataExtraction/providers/binance_provider.py` — python-binance `Client.get_klines` = **Binance SPOT** `/api/v3/klines` (`:373-379`), limit 1000/request, client-side token bucket 1000 req/min (`:52-130, :217`), retry/backoff by error class (`:162-168`). Auth: none needed (public endpoint; key/secret optional from env `BINANCE_API_KEY`/`BINANCE_SECRET_KEY`, `:200-215`). Network required (Client init + requests). 12h × ~5000 bars = ~5–6 requests/symbol, ~60 total — rate limits irrelevant.
- Service: `kline_download_service.py:198-292` `download_klines(source, symbol, start, end, timeframe, save_to_storage)` → `storage.append_klines` (`kline_storage.py:908-962`): reads existing dataset, concat + `drop_duplicates(timestamp, keep='last')` + sort, then `write_klines` rewrites ONLY that `<SYMBOL>/<tf>` dataset (temp dataset + atomic rename, post-write verify, `kline_storage.py:742-905`) and updates that tf-group's attrs + `_metadata.cache_index/last_updated` (`:1485-1530`). Other datasets are not rewritten (their bytes/attrs unchanged), but the whole-file sha256 changes and the file does not shrink.
  - So yes: single symbol×tf, historical range, prepend/merge, other datasets untouched.
- Entry points: (a) API `POST /api/v1/feature-data/kline/download` (`api/routes/feature_data.py:17,82`) → `api/services/feature_kline_service.py:183-288`; (b) the precedent one-off script `handoffs/run_receipts/20260927-ffstat-longhist-download.py` (same factories, writes a separate cache dir; env `LONGHIST_SYMBOLS`, `LONGHIST_START`). No dedicated CLI in `scripts/`.
- 🔴 HAZARDS (must design around):
  1. **API path destroys data if end_date is given**: after download it trims every bar with timestamp > end_date (`feature_kline_service.py:239-256`, `write_klines` overwrite). Calling it with end_date=2023-12-31 would DELETE all 2024–2026 12h bars. With end_date=None it downloads up to *now* and APPENDS ~360 new 12h bars after 2026-04-27 (tail changes too, and 12h would no longer end on the same date as 1h/4h). → Do not use the API; use a script calling `download_klines(..., end_time=2023-12-31 12:00)` directly (no trim step).
  2. **Empty-first-window stop**: `fetch_klines` loops in 1000-bar windows and `break`s on the first empty batch (`binance_provider.py:330-333`). For 12h a window is 500 days; if `[start, start+500d]` is entirely before listing, it returns nothing. Documented in the precedent script (`20260927-ffstat-longhist-download.py:31`: BCH "自 2017 起抓首頁為空、下載服務即停止"). → per-symbol start must be ≥ listing − 500 days (relevant for SOL if start=2019-01-01).
  3. **Zero-tolerance continuity**: `append_klines` validates continuity AFTER writing and returns False (data already written) on any gap (`kline_storage.py:935-946, 968-1046`). Real Binance 12h has a gap at 2018-02-08 12:00 (BTC, ETH in longhist; compare_longhist.py) — irrelevant for a 2019+ start, unknown for others. → fetch with save_to_storage=False, check gaps + exact join to 2024-01-01 00:00, back up the h5, then write.
  4. `keep='last'`: overlapping re-downloaded rows overwrite existing rows. Evidence they are identical: the existing longhist cache (`data_cache/feature_klines_longhist/kline_cache.h5`, downloaded 2026-09-27/28 via the same provider) is **byte-equal on all 10 columns** to kline_cache.h5 12h over 2024-01-01..2026-04-27 for BTC/ETH/ADA/BCH (1696/1696 rows, compare_longhist.py). Safer still: end_time = 2023-12-31 12:00 so there is no overlap.
- Earliest Binance spot 12h bar per symbol:
  - From real data in repo (longhist cache): BTCUSDT 2017-08-17, ETHUSDT 2017-08-17, ADAUSDT 2018-04-17, BCHUSDT 2019-11-28 (bars before 2024-01-01: 4655 / 4655 / 4170 / 2990 → max totals 6351 / 6351 / 5866 / 4686).
  - Not in repo (my recollection, UNVERIFIED — confirm by the fetch itself): BNBUSDT ~2017-11-06, XRPUSDT ~2018-05-04, TRXUSDT ~2018-06-11, LINKUSDT ~2019-01-16, DOGEUSDT ~2019-07-05, SOLUSDT ~2020-08-11 (→ SOL max ≈ 4170 bars; DOGE ≈ 4980; LINK ≈ 5320).
  - Start-date arithmetic (12h, end 2026-04-27 12:00): 2019-01-01 → ~5348 bars; 2019-07-01 → ~4986; 2020-01-01 → ~4618. BCH cannot exceed 4686; SOL cannot exceed ~4170 (below NUMVIEW's A:12h need of ≥4550 and C:12h ≥4284 per fam_C) → SOL 12h stays clipped whatever we do.
- Alternative with zero network for 4 symbols: copy the 2019+ prefix from the longhist cache (already proven byte-identical on the overlap). Other 6 symbols still need a fetch.

## 2. Identity pins (go red purely because 12h bytes / count / file hash change)
| pin | where | effect | fix |
|---|---|---|---|
| per-dataset sha256 + min_row_count for 10× 12h | `tests/fixtures/DATA_MANIFEST.json` (checked by `tests/conftest.py:80-128` `requires_kline_data` → `tests/fixtures/data_manifest.py:200-240`) | every test calling `requires_kline_data(...,"12h")` → `pytest.fail` (≥14 call sites, plus the `la0_real_kline` fixture in test_la0_lookahead.py blocks all 8 of its tests incl. BTC-only ones) | regenerate 10 12h entries (no generator script exists — `data_manifest.py` only verifies; hand/one-off) |
| whole-file `kline_sha256` | `tests/_golden/failopen/baseline.json:18`; `tests/_golden/probewinsor/baseline.json:92710`, `contract.json:509-510` | `test_probewinsor.py:210` requires baseline = contract = failopen authority (not the live file) → red only after failopen is refrozen; `scripts/freeze_probewinsor_baseline.py:70` refuses on live mismatch | edit contract + carry over when failopen refreezes |
| TESTREG ledger `kline_sha256` | `tests/fixtures/testreg_recorder_plugin.py:145-227` | every recorded test fingerprint changes ⇒ prior pass records no longer match (re-run accounting) — not a red test | none (expected) |
| `data_snapshot_digest` (whole 12h table) | `tests/golden/gap3_label/*__12h__*.json` (43 files), `tests/golden/gap3_random_control/{20260905,7}__12h.json` | immediate FAIL (`gap3_label/loader.py:91-110,236-243`) | refreeze (see §3) |
| kline_rows 1696 / kline_sha16 | `tests/golden/la1/gen_baseline.py:82-83`, `la2/gen_baseline.py:84-85`, baselines' `input_contract`; test literals `tests/golden/la1/test_b4_golden_rebaseline.py:524, 944` | red | edit + regen |
| n_rows 1695 | `tests/_golden/ratiounsafe/baseline*.json` (s1 cells) | red | refreeze |
| literal 1695/1692/positional | `tests/momentum/event_samples/test_tables.py:64`, `test_return_table_by_label.py:197,244`, `test_pipeline.py:53-62`, `test_alignment.py:134-137` | red (assume bar n = 2024-01-01 + n·12h) | test edits |
| 1696 not tied to file | `tests/momentum/Analysis/strategy_validation/test_frequency.py:48` (pure arithmetic), `test_native_tf_helpers.py:229-289` (synthetic) | stays green | — |
| docs | `docs/NUMVIEW_SPEC.md:48,130,337`, `docs/RATIOUNSAFE_SPEC.md:14` (12h=1696, 412.6 s full run) | stale facts | doc update |

## 3+4. Goldens whose VALUES change (with re-freeze procedure and runtime)
Why so many: any FF cell that reads 12h (as primary or training TF) is warmup- or calibration-truncated at 2024-01-01 today. The trend-default 12h D0 is ≥2580 bars and a 1h+12h run needs ≥30960 1h-bar span. 12h calibration depth is D0+N (N=1000 for intraday) with doubling. Once more history exists, these cells take a different path: different seeds, different stationarity decisions, partial→complete. Cells that read only 1h/4h, or that use an explicit window with small warmup, stay unchanged. Detail is in the appendices.

| # | golden (cells) | consuming tests | verdict | re-freeze procedure | runtime (receipt) | blockers / extra edits |
|---|---|---|---|---|---|---|
| 1 | `tests/_golden/failopen/baseline.json` BTC/12h, ETH/12h, BTC/multi | test_failopen_correctness.py:397,425; test_failopen_layers.py:242; test_failopen_producer.py:385 | YES | `scripts/freeze_failopen_baseline.py --units <cells>` (:758-797). Don't run full `freeze()`: it rewrites max_nan_ratio.json and breaks batch1 N4 | ~122 s each 12h cell, 2285 s BTC/multi (ffname-refreeze.json:633,715,1017); consumer re-validation 8095 s (:307) | ETH/multi values would also change but are K0-locked, must NOT refreeze (test_ffname_refreeze.py:755-778). Byte-bound to the FF-NAME receipt (`bytes_bound` test_ffname_refreeze.py:631-636) ⇒ new follow-on receipt needed. `environment.kline_sha256` is not auto-updated |
| 2 | `tests/_golden/ffname/baseline.json` (116 12h columns flagged calibration_insufficient_history) | test_ffname_value_invariance.py (live re-run vs golden) | YES → RED | **structurally blocked**: `ffname_helpers.py:218-235` immutability (baseline.sha256 single commit, pre-change code) | reference run 403 s, module 514 s | needs a decision (pin to historical kline snapshot / retire / relax immutability) |
| 3 | `tests/_golden/ff_deepaudit/handcoded_v0_v1_diff.json`, `handcoded_variant_diff.json` (+ beta_correl CONDITIONAL) | written by test_handcoded_reference.py:194,227, test_bug1_beta_correl.py:101 | YES | the tests rewrite them on each run | <1 s | tracked files dirtied; Klinger corr threshold (−0.5; today −0.80) UNKNOWN on longer history |
| 4 | `tests/_golden/fftfmeta/baseline.json` `multi` (1h + [1h,12h]) | test_fftfmeta_golden.py:35-58,83,129 | YES | `handoffs/run_receipts/fftfmeta_probes/freeze_baseline.py --refreeze-baseline` | 89.6 s both refs | already red (pre_existing_drift; `20261020-ffdstar-b4-plan.md:26,214` says don't refreeze) ⇒ decision |
| 5 | `tests/_golden/framepath/cgsa_fingerprint.json` C3, C6 (BTC 1h+[1h,12h], stationarity on, golden records `partial`) | test_framepath_invariance.py:183-238; test_framepath_disposition.py:2055; test_ffname_refreeze.py:1021 | YES | no existing tool rewrites existing cells (`scripts/freeze_framepath_baseline.py` only at commit 6e07e0ad, adds missing cells only); `scripts/ffname_refreeze_framepath.sh`, `scripts/preprov_refreeze.py` are byte re-recorders | C3 216.5 s, C6 224.3 s (12 cells ~1210 s) | edits: lineage check test_framepath_disposition.py:2010,2055; `CALIBRATION_PARTIAL_CELLS` freeze_framepath_baseline.py:65 / :643-650; test_boundary_02 test_framepath_invariance.py:228-234 (partial→likely complete); FF-NAME/PRE-PROV receipt chain |
| 6 | `tests/_golden/icfirstalign/probe_baseline.json` P2 (12h, 2025-07-01, D0 3317 > 1094) | test_icfirstalign_calibration_domain.py:71-89,298-303; test_ffname_refreeze.py:1021 | YES | `ffname_refreeze.py` recipe icfa_probe (freeze script "jia" mode can't run on current code) | 40.3 s (k2 receipt) | receipt chain |
| 7 | `tests/_golden/ratiounsafe/baseline.json` s1_* ×4 (BTC 12h, start 2023-08-01 < data start), `baseline_after.json` s1_off/on, `branch_oracle.json` (`iloc[:1500]`) ; multi_tf_names CONDITIONAL | test_ratiounsafe_registry.py:43,109,265,324-403,426,445 | YES | `scripts/freeze_ratiounsafe_baseline.py --stage before / after / branch-oracle` | 115.7 s / 67.1 s / seconds (ffname_refreeze_maps, _k2 receipts) | n_rows 1695 pin; byte-bound in test_ffname_refreeze.py K1–K3 ⇒ receipt chain; option to switch to tail/explicit windows |
| 8 | `tests/_golden/probewinsor/baseline.json` cell e1h12h_st.on.w1 only (28 others NO) | test_probewinsor.py:100-120,134,175,200-215 | YES | `scripts/freeze_probewinsor_baseline.py` refuses unless HEAD = anchor 820e8f14 and kline sha matches (:39-71) | that cell 23 s; all cells 184.5 s | script cannot run as-is; kline_sha256 contract edit; receipt chain |
| 9 | `tests/_golden/preprov/pre_change_fingerprints.json` cells h12h1_multi, h12h1_replace, multi_symbol (8 1h cells NO) | test_preprov_acceptance.py:264-280; NUMVIEW legacy: test_numview_acceptance.py:906-919, test_numview_identity.py:1631, test_numview_criteria.py:741 | YES | `scripts/freeze_preprov_baseline.py` (regenerates all 11 cells) | 1095.6 s now (sum generation_seconds, output_size.json) → ~20 min after | it is NUMVIEW's legacy baseline ⇒ refreeze before any NUMVIEW product change; `preprov/refreeze_receipt.json` goes stale when failopen/framepath are refrozen |
| 10 | `tests/golden/gap3_label/*__12h__*.json` (43) | test_gap3_analysis_label_producer.py:558-590 (+609-720); CLI `--check` | YES (digest + positional picks) | `scripts/gap3_label_golden.py --freeze "tests/golden/gap3_label/*__12h__*.json" --force` | seconds (gap3 suite 653 tests in 47 s) | `cases.py:46-91` picks bars 95/100/0/len−3 by position ⇒ after refreeze cases sit in 2019/20; design decision if 2024-era coverage matters |
| 11 | `tests/golden/gap3_random_control/{20260905,7}__12h.json` | test_random_control.py:366-430, 471-511 | YES (digest; CLI selector guard) | `gap3_label_golden.py --kind random_control --freeze ... --force` | seconds | universe positions 100..900 move to ~2019-20 |
| 12 | `tests/golden/la1/ETHUSDT_12h_baseline.json` + 3 `_control_*_full.json` (regime masks / xgboost phases on FULL close) | test_b4_golden_rebaseline.py:520-627, 930-1023 | YES (IC report itself unchanged) | `python tests/golden/la1/gen_baseline.py` (+`--controls-only`) | 13.2–13.3 s per control; full unknown | EXPECTED_KLINE gen_baseline.py:82-83; literals :524, :944; FROZEN_ALLOWLIST_ROWS_SHA256 test_attribution_validator.py:717 |
| 13 | `tests/golden/la2/ETHUSDT_12h_baseline.json` regime face | static JSON reads (pytest green); `gen_baseline.py --check` fails | YES (regime face only) | `python tests/golden/la2/gen_baseline.py` | unknown | EXPECTED_KLINE :84-85, EXPECTED_FACE_VALUE_HASHES |
| 14 | `tests/golden/l65/fast_adf_gate_report.json` | written by test_fast_adf_gate.py:277-303 (tail(2000) of 12h: today 1696 < 2000) | content changes; asserts threshold-based (UNKNOWN, likely green) | the test itself | unknown | tracked file dirtied every run |
| 15 | `tests/_golden/batch2d/cgsa_baseline.json` (BTC 12h 2024-06..12) | test_batch2d_dstar_align.py asserts live hash `!=` frozen (:211) | values change, NO test impact | do not run `freeze_batch2d_baseline.py` | — | — |
| C | `tests/golden/splitunify/ic_event_report_baseline.*`, `r5_parity.json` | manual scripts only | CONDITIONAL (only if their FF runs are regenerated; runs already absent) | — | — | — |

NOT affected (verdict NO, evidence in appendices): batch1_followup, batch2d/provenance, ff_causal (orphaned), ffname contract/name_vectors/read_whitelist, ffstat/* (baseline is BTC 1h; baseline_nostart is BTC **1h** full history, not 12h; contract's 12h dual-start reads `feature_klines_longhist`), fftfmeta degraded/allowed_paths, framepath C1/C2/C4/C5/C7–C11 + disposition/compare_domain/v1_layout, icfirstalign calibration_baseline (depth 1078/826 < 1094 bars before 2025-07-01) / l3_default_arm / worker_counts / contract, icpostleak, mtf_align, numview criteria file, prered, v2_ts, preprov output_size/reader_inventory, evtalign, evtlabel, evtwarmup, splitunify golden/report_int_keys, tfwindow, icresult_paging, l65 tier1/tier2, l65_hardening (1h/4h), la0 (frozen feature inputs + forward-return labels that do not change while overlap rows are byte-identical), ic_phase1_*, fixtures/ic_phase0, ic_run_selector_baseline.

### Non-golden tests likely RED (from code reading, not run)
- All `requires_kline_data(...,"12h")` callers until DATA_MANIFEST is regenerated (test_feature_factory_e2e.py ×6, test_la0_lookahead.py (8 tests via fixture), atomic/* ×5, test_ff_wrapper_path_correctness.py, test_ff_cross_symbol_value_isolation.py, …).
- tests/feature_engineering/preprocessing/test_l65_native_tf_real_eth.py:92, :283-296 (native warmup prefix vs native_floor=564).
- tests/momentum/event_samples: test_tables.py:42-68, test_return_table_by_label.py:197-222 + G2_GOLDEN_SHA256 :244, test_pipeline.py:53-62, test_alignment.py:134-137; ~15 more BASE-anchored files need individual checks (list in fam_E.md).
- CONDITIONAL: test_ff_cross_symbol_value_isolation.py:456-462 (`len(BTC12h)==len(ETH12h)` + positional `iloc[1034]`; red if BTC/ETH get different start dates; runtime grows).
- Slower: test_feature_factory_e2e (12h full history ≈3× rows).

### Latent bug surfaced (independent of the golden refreeze)
`momentum/Analysis/ic_engine.py:1475-1497` `_align_with_raw_data`: if len(features)==len(raw) it aligns by POSITION; otherwise it `reindex`es raw (RangeIndex) onto feature timestamps ⇒ all-NaN raw ⇒ regime/by-year grouped IC go empty. Today ETH-12h split-OFF runs work only because 1696 == 1696; after extension they hit the NaN branch. The same mismatch already exists for any run whose lengths differ (e.g. BTC 1h tail2000). Not asserted by any golden (evtwarmup `event_run` is unasserted). Flag as a separate correctness fix.

## 5. User-visible effects outside tests
- Feature Factory UI download panel / `GET /api/v1/feature-data/kline/list` (`feature_kline_service.py:290-360`, frontend `FeatureKlineDownloadPanel.tsx:116`, `feature-factory/page.tsx:147`) will show 12h start dates 2019/2020 that differ per symbol, with row counts ~4200–5350. 1h/4h stay at 2024-01-01. No frontend date picker hard-codes a min date (`DateRangePicker` minDate is unused by callers). `2024-01-01` in `api/models/requests.py:150` and `api/routes/optimization.py:62` are schema examples only.
- 12h FF runs **without start_date** ingest the full history: about 3× rows, so more time and output size. Today's full 12h run is 412.6 s at 1696 rows (`handoffs/run_receipts/20261020-preprov-fullrun-size.md`); a linear guess is ~20 min at ~5000 rows (UNKNOWN). The NUMVIEW C-12h upper bound cites that receipt (`test_numview_criteria.py:94-95,856-859`).
- 12h runs **with start_date** in 2024–2026: `warmup_insufficient` alerts (`WarmupInsufficientAlert.tsx`, `RunManagerPanel.tsx:40`) and `calibration_insufficient_history` / quality `partial` largely disappear. Values of 12h columns change versus previously generated runs. Existing runs in `data_cache/features` remain as they were (config_hash keys on the last kline timestamp only, `feature_factory.py:4140`, so a regenerated run with the same config reuses the same hash/dir).
- IC event-filter query mode counts events over the full raw kline (`ic_filter_orchestrator.py:3841-3856`), so n_events and tier change for 12h.
- NUMVIEW: `handoffs/run_receipts/numview_probes/estimate.py:155-168,310-342` reads 12h bar counts. `_estimate_gate.require` does NOT re-check counts, so an estimate receipt made before the extension would still pass the gate afterwards; regenerate estimates after the extension. A:12h becomes unclipped at ≥4550 bars and C:12h at ≥4284 (SOL cannot reach either). B's training TFs gain 12h where A:12h passes. Nothing NUMVIEW has been frozen yet (`scripts/numview_freeze_baseline.py` is all NotImplementedError), so extend 12h before Task 0.4/0.5 freezes.
- Docs stating 12h=1696: `docs/NUMVIEW_SPEC.md:48,130,337`, `docs/RATIOUNSAFE_SPEC.md:14`.

## Confidence / unknowns
- High: fetch mechanism, hazards 1–3 (code + precedent log), overlap byte-equality (measured for 4 symbols), identity pins, the YES list for FF goldens (D0/depth computed by read-only probes that reproduce recorded values: P1 878, P2 3317, calibration rows 1078/826).
- Medium: non-golden RED list (code reading only; nothing run); "partial→complete" flips; ff_deepaudit threshold.
- Unknown: listing dates of BNB/XRP/TRX/LINK/DOGE/SOL (not in repo); possible 12h gaps for those 6 in 2019–2023; full-run runtimes for la1/la2/l65 report; original ffname/batch2d freeze durations.
- Rough total serial re-freeze compute (excluding blocked ffname): failopen 12h+multi ~42 min + framepath C3/C6 ~7.5 min + icfa P2 ~1 min + ratiounsafe ~3.5 min + probewinsor ~0.5 min + preprov ~20 min + gap3/la1/la2 minutes ≈ **75–80 min**, plus failopen consumer re-validation ~2.25 h if repeated as in FF-NAME. The bigger cost is the governance/receipt-chain edits (FF-NAME K-chain, PRE-PROV refreeze_receipt, framepath lineage, probewinsor anchor), which need SPEC-level decisions.

---
# Appendices (subagent findings, verbatim files)

## Appendix A (fam_A.md)
# fam_A — 12h history extension: golden impact audit (READ-ONLY)

Families: batch1_followup, batch2d, failopen, ff_causal, ff_deepaudit, ffname.
Method: read code/JSON only; no pytest, no freeze, no h5 read. Timings from `.testreg/summary.json` (testreg ledger, max duration_s per node) and `handoffs/run_receipts/*`.

## Shared mechanics used (with evidence)

- 12h bars before a start date S = days(2024-01-01 → S) × 2.
- Lower bound on the 12h public warmup D0: `handoffs/run_receipts/probewinsor_probes/out/s12h_off.current.json` records `max_warmup_bars: 2580` for a 12h single-TF run with ONLY the trend category on (default trend indicators), rolling windows [5,13], preprocessing off (probe config: `probe_depth.py` `_payload` → `fftfmeta_golden_helpers.fast_payload`). Any config with the default trend category on has D0 ≥ ~2580 12h bars, plus L6.5 winsor window + 252 when L6.5 is on (`warmup_window.py:250-265`).
- Multi-TF (1h primary + 12h): `m1h12h_off.current.json` records `max_warmup_bars: 30960` (1h bars), i.e. about 1419 days of load (×1.1 buffer, `warmup_window.py:268-278`).
- `_layer0_data_ingestion(start_date=S)` hard-filters `index >= S` (`feature_factory.py:925-935`), so "direct" calls that pass start_date with no warmup cannot see pre-S history.
- Doubling rule: `feature_factory.py:2595-2668`. It doubles only while some TF has late columns AND `lo > 0` (`:2656`). The 1h and 12h data both start 2024-01-01 and share one ingest_start date (`warmup_window.py:531-539`). So in a 1h+12h run the 1h load is floored at 2024-01-01 before and after the extension: 1h-native columns don't change, and only 12h-derived ones do.
- config_hash includes only the primary TF's LAST kline timestamp (`feature_factory.py:4140-4141`). The extension leaves end dates alone, so config_hash is unchanged.
- Calibration N: `feature_config.py:202,225-240`. Below 1 day → 1000 (this includes 12h).

---

## 1. batch1_followup — `tests/_golden/batch1_followup/baseline.json`

1. Consumers: `tests/feature_engineering/test_batch1_followup.py:35` (BASELINE_PATH). Uses at :119-160 (readable, winsor hashes, `max_nan_ratio_btc_12h`), :163-170 (N4 resource vs `tests/_golden/failopen/max_nan_ratio.json` byte-equality), :207 (nan_stats reference), :445-482 (perf budget).
2. Cells: no real-kline cells. `scripts/freeze_batch1_baseline.py:44-53` uses a seeded RNG winsor fixture, :56-73 synthetic NaN cases and :76-91 a synthetic 20000×2000 perf registry with the tf label "12h" (label only). `max_nan_ratio_btc_12h` = `FeatureFactory._default_max_nan_ratio("BTCUSDT","12h")`, which reads the static resource `momentum/FeatureEngineering/_resources/max_nan_ratio.json` (`feature_factory.py:119,3538`). It is not computed from klines.
3. Identity pins: none (no kline sha, row count or timestamps). `max_nan_ratio_btc_12h=0.16346…` is a static number observed in June on 1696-bar data, but it is stored, not recomputed.
4. **VERDICT: NO.** Every value is synthetic or read from a static resource.
   - Side note, not a golden: `test_real_kline_stream_nan_ratio_matches_written_arrays` (:485-540) runs real BTCUSDT 12h from 2024-06-01 (304 12h bars before start, far below D0) with `preprocessing.enabled=False`. Its values will change, but it only checks internal consistency (recomputed nan_ratio == metadata; status vs reasons). It should stay green.
5. Freeze: `venv/bin/python scripts/freeze_batch1_baseline.py`. It refuses to overwrite a differing baseline (:156-170). No refreeze is needed.
6. Runtime: freeze not recorded. Tests are seconds (ledger: perf smoke 9.1s, real-kline test 78s).

## 2. batch2d — `tests/_golden/batch2d/cgsa_baseline.json` (62MB), `provenance.json` (22MB)

1. Consumers: `tests/feature_engineering/test_batch2d_dstar_align.py:93-122` (structure only, both files) and :193-221 `test_cgsa_baseline_runs_ic_first_not_legacy_frozen`. That second test asserts the live run's `canonical_sha256 != frozen` (:211) plus repeat-run NaN-mask stability (self-comparison).
2. Cell: BTCUSDT, primary 12h, training [12h] (`scripts/freeze_batch2d_baseline.py:21-24,122-126`). Window 2024-06-01..2024-12-01. Default config. L6.5 is on (winsor window 252); fracdiff and ADF are off, so no stationarity (golden `metadata.config.preprocessing`). Env Polars=0 (:25-33).
3. Identity pins: `metadata.kline.sha256 = b1ee5b9a…` (cgsa_baseline.json:1159676), `start_date`/`end_date` (:1159684/:1159665), `rows: 367` (:991870). No consumer asserts the kline sha.
4. **VERDICT: values would change (YES), but there is no test impact.** 12h bars before 2024-06-01 = 152 d × 2 = **304**, and D0 ≥ 2580 (+504 for L6.5), so the run is warmup-truncated today and the values move once the history is extended. The only value assertion is an inequality, though. This golden is a deliberately stale "legacy" snapshot (FF-NAME contract classes it K0: `tests/_golden/ffname/contract.json` refreeze.dispositions["tests/_golden/batch2d/cgsa_baseline.json"]). provenance.json holds a column→layer map with no data values, so it is NO.
5. Freeze: `venv/bin/python scripts/freeze_batch2d_baseline.py` (orchestrates a `--phase cgsa` subprocess). Do NOT refreeze; there is no need and no test edit.
6. Runtime: the original freeze time is unknown. Consumer run with 2 tests (2 full 12h generations) = 514.6s (`handoffs/run_receipts/ffname-refreeze.json:27`); ledger max 578s for the P4 test.

## 3. failopen — `tests/_golden/failopen/baseline.json` (+ `max_nan_ratio.json`)

1. Consumers:
   - `test_failopen_correctness.py:29`. The value compare is in `_assert_single_tf_baseline_matches` (:318-345) and `_assert_multi_tf_baseline_matches` (:348-365). The tests are `test_v3_healthy_full_run_matches_frozen_baseline` (BTC/12h, :397), `test_v3_ethusdt_1h…` (:409) and `test_v3_multi_tf_btc…` (:425).
   - `test_failopen_layers.py:29,226-267` (`test_layer_golden_matches_baseline`, BTC/12h layers L1–L6).
   - `test_failopen_contract.py:27,256-304` (`test_l1_baseline_hash_matches_frozen`, which reads `l1_direct`).
   - `test_failopen_golden.py:10,38-90` (structure only).
   - `test_failopen_producer.py:385-388` (reads multi BTC `config_hash`).
   - `test_ffname_refreeze.py:766-800,915,1128-1186` (K0 bytes of ETHUSDT/multi; receipt byte-binding).
   - `test_ratiounsafe_registry.py:415` (git-range check only).
   - `tests/feature_engineering/test_probewinsor.py:178-210` uses `environment.kline_sha256` as the kline authority.
   - `max_nan_ratio.json` is read by `test_failopen_golden.py:40` and `test_batch1_followup.py:36,168`.
2. Cells (`scripts/freeze_failopen_baseline.py`):
   - Symbols BTCUSDT and ETHUSDT; TFs 1h and 12h; multi primary 1h (:26-28).
   - Window = last BTCUSDT 1h bar − 365 d, which gives **2025-04-27..2026-04-27** (:78,108-119; golden env.window baseline.json:40-42).
   - Config (:81-105): enabled_sources=[close]; winsor on; fracdiff, ADF, rank, zscore and gaussian off, so **no stationarity/calibration**. Everything else is the default (L1–L6 on). Fixed env :29-36.
   - Cells:
     - single_tf {BTC,ETH}×{1h,12h}: training=[tf], with `layers` L1–L6, `final_L7` and `l1_direct`.
     - multi_tf {BTC,ETH}: primary 1h, training [1h,12h], `merged_L7`.
   - `l1_direct` (:565-599) calls `_layer0_data_ingestion(start_date=…)` directly and runs only L1, with no warmup.
3. Identity pins:
   - `environment.kline_sha256 = b1ee5b9a…` (baseline.json:18). It is only length-checked here (`test_failopen_golden.py:52`), but `test_probewinsor.py:210` asserts probewinsor's frozen kline_sha == contract == this value.
   - No 1696 / 2024-01-01 / total_bars literal. `final_L7.rows=731` for 12h is the public window and does not change.
   - `unit_commits` records which units were refrozen.
4. VERDICTS per cell:
   - **BTCUSDT/12h and ETHUSDT/12h (`layers`, `final_L7`, artifacts): YES.** 12h bars before 2025-04-27 = 482 d × 2 = **964**. D0 is at least 2580 (trend-only lower bound) + 504 (L6.5), so the run is warmup-truncated at the 2024-01-01 data start today. With extended history the load starts about 3000+ bars earlier: recursive and rolling seeds move, L6.5 winsor moves, and L3 survivor rules (data-dependent) may change.
   - **`l1_direct` for 12h: NO.** It uses an exact [2025-04-27, end] window with no pre-start rows (`feature_factory.py:925-935`).
   - **BTCUSDT/multi: YES.** D0 is at least 30960 1h bars (~1419 d, so ingest starts around 2021-06, before 2024-01-01), which means the 12h series is truncated today. The 12h-derived columns change; 1h-native columns stay the same because the 1h load is floored at 2024-01-01 both before and after. `merged_L7` canonical hash, `group_set_sha256`/`feature_count` (if the 12h L3 survivor set moves) and artifact hashes all change.
   - **ETHUSDT/multi: YES if regenerated (same reasoning), but it must NOT be regenerated.** It is FF-NAME K0. `test_ffname_refreeze.py:755-778` (`failopen_k0_problems`) fails if its node changes or appears in `unit_commits`. No test compares its values.
   - **BTCUSDT/1h, ETHUSDT/1h: NO.** Training=[1h]; the 1h data is untouched.
   - **`max_nan_ratio.json`: NO** (static). It is only rewritten by a full `freeze()` (:735-756), not by `--units` (:758-763). A full freeze would rewrite it from new 12h runs and break batch1's N4 byte-equality (`test_batch1_followup.py:168`), so do not run full `freeze()`.
   - Non-golden literal: `MTF_12H_L3_SURVIVOR_COUNT = 59962` (`test_failopen_correctness.py:42`, used at :494) comes from a direct exact-window L1–L3 call (:458-466). It is NO, unaffected.
5. Freeze: `PYTHONHASHSEED=0 venv/bin/python scripts/freeze_failopen_baseline.py --units BTCUSDT/12h,ETHUSDT/12h,BTCUSDT/multi` (:758-787,797). `freeze_units` keeps the old `environment` block, so `kline_sha256` stays stale unless it is edited. The FF-NAME K2 wrapper `scripts/ffname_refreeze_failopen.sh` is for FF-NAME old/new parity, not this purpose.
   - Test/governance edits needed: `test_ffname_refreeze.py` byte-binds the file to the FF-NAME receipt `new_sha256` or to a PRE-PROV follow-on (`bytes_bound` :631-636, used at :550-551 and :619-620). A refreeze makes it `bytes_unbound` and red unless a new follow-on receipt/rule is added.
   - The probewinsor kline authority chain (`test_probewinsor.py:210`) must be updated consistently with probewinsor's own refreeze.
6. Runtime (recorded):
   - Golden perf `generation_wall_seconds`: BTC/12h 113.8s (baseline.json:9626), ETH/12h 113.4s (:12830), BTC/multi 2239.6s (:3149); ETH/multi 4880.9s (:8033, old code).
   - FF-NAME refreeze receipt (new code): BTC/12h 122.1s, ETH/12h 121.8s, BTC/multi 2285.3s (`handoffs/run_receipts/ffname-refreeze.json:633,715,1017`).
   - Consumer run of all failopen consumers: 8094.9s (`ffname-refreeze.json:307`).
   - Ledger: v3 BTC/12h 126s, v3 multi 2285s.
   - My estimate, not measured: the 12h cells will be slower than ~2 min after the extension because the warmup load grows from ~1.7k to ~3.5–4k native rows. About 45–60 min total for 3 units, plus ~2h15m to rerun the consumers.

## 4. ff_causal — `tests/_golden/ff_causal/legacy_preprocessing_fingerprint.json`

1. Consumers: **none.** `git log -S legacy_preprocessing_fingerprint -- tests` shows the reference was removed in e8b62c9b (2026-06-18); grep of tests/ and scripts/ gives 0 hits. The sibling test `tests/feature_engineering/preprocessing/test_ff_causal_golden.py` does not read it.
2. Cell: source `tests/golden/l65/tier2_reduced/ETHUSDT_1h_2000rows.parquet`, 320 rows × 3 L1 columns (a 1h parquet fixture, not the h5).
3. Identity pins: none for kline h5.
4. **VERDICT: NO.** It is 1h, comes from a parquet fixture and is orphaned. (`test_real_generate_e2e_*` in that test file run on ETHUSDT 1h with a full history and default training TFs, but they only assert shape/finite, so no golden is involved.)
5. Freeze: no script (written once in fff522b7). No action.
6. Runtime: n/a (tests are ~1s).

## 5. ff_deepaudit — `beta_correl_v0_v1_diff.json`, `handcoded_v0_v1_diff.json`, `handcoded_variant_diff.json`

1. Consumers / producers: the tests write these files; they are never compared against.
   - `tests/feature_engineering/atomic/test_bug1_beta_correl.py:17,44-105` writes beta_correl (:101-102).
   - `tests/feature_engineering/atomic/test_handcoded_reference.py:18-19`: `test_handcoded_v0_v1_diff_table_recorded` (:170-200) writes handcoded_v0_v1 (:194-195), and `test_literature_reference_diff_table_recorded` (:203-235) writes handcoded_variant (:227-228).
2. Cells: BTCUSDT 12h, the full series via fixture `requires_kline_data("BTCUSDT","12h",min_rows=500)` (test_bug1_beta_correl.py:20-22; test_handcoded_reference.py:48-50). That fixture uses `tests/conftest.py:82-127`, which returns the complete `read_klines` with no window and verifies DATA_MANIFEST first (:97-106). Pure indicator computation, no FF.
3. Identity pins: handcoded files embed `n` derived from the 1696-bar length: ForceIndex n=1683 (1696−13), Klinger n=1642 (1696−54), EOM n=1682 (1696−14) (handcoded_v0_v1_diff.json, handcoded_variant_diff.json). beta_correl embeds max_abs_diff over all rows (481.59 / 1.954), plus 0.0 for the legacy-identity pairs.
4. VERDICTS:
   - **handcoded_v0_v1_diff.json and handcoded_variant_diff.json: YES.** `n` grows with bar count, and Klinger/ForceIndex are EMA-recursive over the full series, so corr and max_abs_diff change.
   - **beta_correl_v0_v1_diff.json: CONDITIONAL (likely YES).** BETA/CORREL(5) are windowed, so overlap rows are identical, but max_abs_diff is a max over a superset and changes iff older bars produce a larger diff. The two 0.0 entries stay 0.0.
   - Test pass/fail after the extension:
     - The assertions are thresholds on fresh values: Klinger/ForceIndex v0-v1 corr < 0.99 (:197-200), FI corr > 0.99 (:230-231), Klinger r2→r3 corr < −0.5 (:232-235), beta max diff > 0.01 (:105). Most likely they still hold. The Klinger r2→r3 corr (−0.80 today) on longer history is UNKNOWN.
     - All of these tests `pytest.fail` until the DATA_MANIFEST 12h entry is regenerated.
     - Running them leaves the tracked golden files dirty.
5. Freeze: no script. They are regenerated by running the tests: `pytest tests/feature_engineering/atomic/test_bug1_beta_correl.py tests/feature_engineering/atomic/test_handcoded_reference.py` (after updating DATA_MANIFEST). No literal pins in the tests need editing.
6. Runtime: sub-second per test (ledger max 0.3s).

## 6. ffname — `tests/_golden/ffname/{baseline.json (31MB), baseline.sha256, contract.json, name_vectors.json, read_whitelist.json}`

1. Consumers:
   - baseline.json values:
     - `tests/feature_engineering/test_ffname_value_invariance.py:47-56,154-162,223-230,555-566,593-633`. The `current` fixture re-runs `freeze.run_reference` live and cond2 compares four hashes per column against the baseline.
     - `handoffs/run_receipts/ffname-value-invariance.json` is re-checked at :555-566 and :639-648.
   - baseline.json names/parts: `test_ffname_structural_selection.py:154-160`, `test_feature_name_parser.py`, `test_ffname_consumers.py` (via `ffname_helpers.iter_new_names_from_baseline`), `scripts/export_feature_name_vectors.py:47-57`.
   - Immutability: `ffname_helpers.py:218-235` `baseline_immutability_problems` requires sha == file and `git log -- baseline.sha256` to have exactly 1 commit. It is used by `test_ffname_freeze_baseline.py:174` and `test_ffname_refreeze.py:1302`.
   - contract.json, read_whitelist.json and name_vectors.json are rule/name data (grammar, descriptor, gate, refreeze dispositions); name_vectors derives from baseline parts and contract only (`export_feature_name_vectors.py:8-11`).
2. Cells (baseline.json `reference`, built by `scripts/ffname_freeze_baseline.py:740,837-847`):
   - **main:** BTCUSDT, primary 1h, training [1h,12h], window 2026-01-01..2026-01-31.
     - Rich config: many L1 categories, L2 ops, L4 custom lags [1,3], meta on.
     - Preprocessing on: winsor, rank, zscore, gaussian, **ADF and fracdiff on (stationarity ON)**, apply_to non_stationary, mode append.
     - Calibration N=1000 for both TFs (all `stationarity_decisions[*].n` = 1000 or null).
   - **xsec:** ADA/BCH/BNB (vs BTC), 1h only, 2026-01-01..10, preprocessing off.
   - Column split: 2583 `*_12h_*` and 2487 `*_1h_*` columns.
3. Identity pins: `frozen_at_head = dfd5d7db…` (a pre-change code snapshot). baseline.sha256 = 04ff7faa… There is no kline sha. The decisions embed calibration_start/end/shortfall dates.
4. VERDICT **main 12h-tagged columns: YES**, shown directly by the golden:
   - 12h bars before 2026-01-01 = 731 d × 2 = **1462**, and the calibration depth is roughly D + N with N=1000.
   - `stationarity_decisions` lists **116 12h columns** with events `["adf_untested_insufficient_data","calibration_insufficient_history"]` and `calibration_shortfall` from 10 to 529, e.g. `close_12h_cycle_HT-SINE-LeadSine_Distance` with shortfall 186. 19 more 12h columns have `adf_untested_insufficient_data`.
   - Those calibrations hit the 2024-01-01 data start. With history back to 2019/20 they get full N=1000, are ADF-tested, may be differenced or fracdiff'd, and (append mode) may add `_diff-1`/`_fracdiff` columns.
   - All other 12h calibrations (2227 at calibration_start 2024-08-19 with exactly 1000 bars) were loaded from the data start too (depth > 1462). Recursive and cumulative features inside the calibration window, such as OBV/AD/EMA, shift, so ADF p-values and d* can move.
   - Net effect: cond2 (four-hash equality) fails, and cond1 (column set) and Task 2.5 (stationarity keys) may fail.
   - **main 1h-tagged columns: NO (by argument).** The 1h data is unchanged. 1h calibration (N=1000 1h bars, ~42 days) is far from the data start (1h calibration_start ≥ 2025-08-29). The public ingest date is shared with 12h, and the 1h load is floored at 2024-01-01 in either case; doubling continues only while `lo>0` (`feature_factory.py:2656`). Meta is per-TF (`meta_1h`/`meta_12h`, 12 each).
   - **xsec: NO** (1h only).
   - **contract.json, read_whitelist.json, name_vectors.json, baseline.sha256: NO** (no data dependency).
5. Freeze: `venv/bin/python scripts/ffname_freeze_baseline.py`, by design run at PRE-CHANGE HEAD dfd5d7db / c9737729 (`ffname_freeze_baseline.py:1-30`, `frozen_at_head`). **A refreeze is blocked structurally:** `baseline_immutability_problems` (`ffname_helpers.py:218-235`) fails if baseline.sha256 gets a 2nd commit, and the baseline must be produced at pre-change code. Accommodating the extension requires a test/governance edit, for example:
   - pin `test_ffname_value_invariance` to a historical kline snapshot, or
   - retire/convert that test now that FF-NAME is closed (closed 2026-10-19), or
   - relax the immutability rule.

   The value receipt `handoffs/run_receipts/ffname-value-invariance.json` would also need regenerating (`--value-receipt`).
6. Runtime:
   - The reference run (`ffname_freeze_baseline.py --value-receipt`) took 403.0s (`handoffs/run_receipts/ffname-value-invariance.json:576`).
   - The value-invariance module fixture took 514s (ledger, 2026-10-18).
   - The original Task 0.1 freeze time is UNKNOWN (not found in receipts).
   - Extended 12h calibration and warmup history would add some time; the magnitude is unknown.

---

## Summary table

| golden | consuming tests | cells (12h-related) | verdict | freeze script | runtime estimate | identity-only pins |
|---|---|---|---|---|---|---|
| batch1_followup/baseline.json | test_batch1_followup.py:35,119-170,207,445 | none (synthetic + static resource) | NO | scripts/freeze_batch1_baseline.py | n/a (seconds) | none |
| batch2d/cgsa_baseline.json | test_batch2d_dstar_align.py:93-122,193-221 | BTC 12h/[12h], 2024-06-01..12-01 (304 bars pre-start) | values YES; test impact NONE (asserts `!=`, :211; K0 legacy) | scripts/freeze_batch2d_baseline.py (do not run) | 514.6s consumer run (ffname-refreeze.json:27) | metadata.kline.sha256 :1159676 (unasserted) |
| batch2d/provenance.json | test_batch2d_dstar_align.py:93-122 | col→layer map | NO | same | n/a | none |
| failopen/baseline.json BTC/12h, ETH/12h | test_failopen_correctness.py:397; test_failopen_layers.py:242; test_failopen_golden.py | 12h/[12h], 2025-04-27.. (964 bars pre-start < D0≥2580) | YES | freeze_failopen_baseline.py --units | ~122s each (ffname-refreeze.json:633,715); likely longer after extension | env.kline_sha256 :18 (authority for test_probewinsor.py:210) |
| failopen BTC/multi | test_failopen_correctness.py:425; test_failopen_producer.py:385 (config_hash, unchanged) | 1h primary + 12h training, D0≥30960 1h bars → 12h truncated | YES (12h-derived cols; 1h cols unchanged) | --units BTCUSDT/multi | 2285s (ffname-refreeze.json:1017) | same |
| failopen ETH/multi | test_failopen_golden.py (structure); test_ffname_refreeze.py:755-778 K0 | 1h+12h | YES if regenerated; must NOT refreeze (K0 lock) | — | 4881s (old) | same |
| failopen BTC/1h, ETH/1h | test_failopen_correctness.py:409 | 1h only | NO | — | — | — |
| failopen l1_direct 12h | test_failopen_contract.py:278 | exact window, no warmup | NO | — | — | — |
| failopen/max_nan_ratio.json | test_failopen_golden.py:40; test_batch1_followup.py:168 | static | NO (don't run full freeze()) | — | — | — |
| ff_causal/legacy_preprocessing_fingerprint.json | none (orphaned since e8b62c9b) | 1h parquet fixture | NO | none | n/a | none |
| ff_deepaudit/handcoded_v0_v1_diff.json, handcoded_variant_diff.json | written by test_handcoded_reference.py:170-235 | BTC 12h full series | YES (n=1683/1642/1682 ∝ 1696; corr) | the test itself rewrites them | <1s (needs DATA_MANIFEST fix) | n derived from 1696 rows |
| ff_deepaudit/beta_correl_v0_v1_diff.json | written by test_bug1_beta_correl.py:44-105 | BTC 12h full series | CONDITIONAL (max over superset; likely YES) | the test itself | <1s | none |
| ffname/baseline.json | test_ffname_value_invariance.py (cond2 live re-run); immutability ffname_helpers.py:218-235 | main BTC 1h+12h, 2026-01-01..31, stationarity ON, N=1000 (1462 12h bars pre-start; 116 12h cols calibration_insufficient_history) | YES (12h cols); 1h cols & xsec NO | scripts/ffname_freeze_baseline.py, at pre-change commit only; refreeze blocked by single-commit sha rule → needs test/governance edit | ref run 403s (ffname-value-invariance.json:576); module 514s | frozen_at_head; baseline.sha256 |
| ffname/contract.json, name_vectors.json, read_whitelist.json, baseline.sha256 | grammar/descriptor/refreeze tests | none | NO | export_feature_name_vectors.py (names only) | n/a | none |

## Appendix B (fam_B.md)
# Family B: golden impact of extending the 12h kline history (read-only audit)

The scope is ffstat, fftfmeta, framepath, icfirstalign, icpostleak and mtf_align. Paths are relative to the repo root.

## How the evidence was gathered

I ran one read-only script, `scratchpad/famB_d0.py`. It ran with `PYTHONDONTWRITEBYTECODE=1` and sent the numba cache to the scratchpad. It only loads the YAML config and calls the pure functions `estimate_max_warmup_bars` and `resolve_output_window`. It computed D0 (the public-warmup depth in primary-timeframe bars), `ingest_start`, and the 12h calibration depth for every golden configuration in this family. It did no generation and wrote no files.

Results, with the data start at 2024-01-01:

| config | primary | training | D0 | ingest_start | truncated at 2024-01-01? | 12h calibration depth vs 12h bars before start |
|---|---|---|---|---|---|---|
| fftfmeta multi (`fg.multi_tf_payload`) | 1h | 1h,12h | 31464 | 2022-01-19 | **YES** | stationarity off |
| fftfmeta degraded | 1h | 1h | 3084 | 2025-08-12 | no | – |
| framepath C3/C6/C9 (`stat_payload(["1h","12h"])`) | 1h | 1h,12h | 31056 | 2022-02-07 | **YES** | 4050 (N=1000) vs 1462 → **reaches data start** |
| framepath C1-like (`stat_payload(["1h"])`) | 1h | 1h | 3050 | 2025-08-14 | no | 1h only |
| icfa S2 (`s2_payload()`) | 12h | 12h | 878 | 2024-03-05 | no | – |
| icfa P1 (`s2_payload(["12h","1h"])`) | 12h | 12h,1h | 878 | 2024-12-16 | no | – |
| icfa P2 (trend defaults) | 12h | 12h | 3317 | 2020-07-02 | **YES** | – |
| icfa S3 winsor on | 12h | 12h | 878 | 2024-03-05 | no | 1078 (N=200) vs 1094 → does not reach |
| icfa S3 winsor off | 12h | 12h | 626 | 2024-07-21 | no | 826 vs 1094 → does not reach |
| icfa S2m | 12h | 12h,4h | 878 | 2024-03-05 | no | – |

These values match the recorded goldens and receipts:

- probe_baseline P1: `max_warmup_bars` 878, `ingest_start` 2024-12-16T02:24.
- probe_baseline P2: 3317, 2020-07-02T15:36.
- calibration_baseline: `rows` 1078 / 826.
- `handoffs/run_receipts/probewinsor_probes/out/m1h12h_on.fixed.json` (the fftfmeta-like config): depth 31464, ingest 2022-01-19.

---

## 1. ffstat (`tests/_golden/ffstat/`): VERDICT NO for all six files

**The brief assumed `baseline_nostart.json` is a full-12h-history run. It is not.** It is a **BTCUSDT 1h** run with no start date:

- freeze script `handoffs/run_receipts/ffstat_probes/freeze_baseline_nostart.py:54-55` calls `generate_features("BTCUSDT","1h", …, start_date=None, end_date=None)`;
- its payload is `fast_payload([PRIMARY_TF])` with `PRIMARY_TF="1h"` (lines 25-35);
- the golden itself has `"timeframe":"1h"`, `"rows":20352`, and all 3632 columns are `*_1h_*` (zero `_12h_` or `_4h_` columns).

Because 1h is untouched, the values cannot change.

| file | consumers | cells | 12h? | verdict |
|---|---|---|---|---|
| baseline.json | `tests/feature_engineering/ffstat_helpers.py:29` (BASELINE_PATH) → `test_ffstat_golden.py:44` (fixture; tests at :59,:66,:73,:81,:375,:417), `test_ffstat_layer.py:64`, `test_ffstat_all_tested.py:45,53,68`, `test_ffstat_apply_to.py:58`, `test_ffname_value_invariance.py:30,48` (via ffname_helpers) | main run: BTC 1h, training [1h], window 2026-01-01..01-31, stationarity on (`freeze_baseline.py:100-101`; `ffstat_helpers.stat_payload` :88-110; `fftfmeta_golden_helpers.py:30-31,98`). `auto_off`: BTC 1h, no start, end 2024-02-29, stationarity off (:108-115). `ic_first_supplied_off`: 1h, WINDOW (`ffstat_helpers.py:278-293`) | none (3572 base columns all `_1h_`) | **NO**: training is [1h], so 12h is never read (`feature_factory.py:2611-2613`, 461-478) |
| baseline_nostart.json | `test_ffstat_stable_start.py:588-610` (`test_no_start_stationarity_off_stable_values_unchanged`); `test_ffstat_golden.py:73` (per `tests/_golden/ffname/contract.json:201`) | BTC 1h, full 1h history, stationarity off | none | **NO** |
| baseline_dead_drops.json | `test_ffstat_stable_start.py:1206-1231` (via `stable_start_receipts.DEAD_DROPS_PATH`, :88) | BTC 1h, WINDOW, `stat_payload()`, commit 5a148b8e | none | **NO** |
| contract.json | `ffstat_helpers.py:26`, `cost_probe.py:40`, `test_ffstat_stable_start.py` | Policy only. `dual_start` 12h reads `data_cache/feature_klines_longhist`, not kline_cache.h5 (contract `dual_start.timeframes`; used at `test_ffstat_golden.py:94`) | none | **NO** |
| nan_propagation_classes.json | `test_ffstat_stable_start.py:371` | code-classification only (`class: name_free` in ffname contract) | none | **NO** |
| retired_tests.json | `test_ffstat_stable_start.py:1634-1636` | list of retired test IDs | none | **NO** |

- **Identity-only pins:** none. A grep for kline_sha, 1696, 2024-01-01, total_bars, data_checksum and time_range_start found 0 hits in all six files.
- **Freeze scripts:**
  - `venv/bin/python handoffs/run_receipts/ffstat_probes/freeze_baseline.py --refreeze-baseline` (docstring :9-11).
  - The nostart freeze must run in a pre-FF-STAT worktree (`freeze_baseline_nostart.py:3-6`).
  - dead_drops uses `freeze_dead_drops.py`.
  - The FF-NAME recipes are `ffstat_baseline` and `ffstat_nostart` (`scripts/ffname_refreeze.py:164-198`).
- **Runtime (re-freeze is not needed):** FF-NAME record `ffstat_baseline` took 97.6 s and `ffstat_nostart` took 37.8 s (`handoffs/run_receipts/ffname-refreeze.json`).

---

## 2. fftfmeta (`tests/_golden/fftfmeta/`)

**baseline.json** has two references.

- **multi:**
  - payload timeframes primary 1h, training [1h,12h] (`jq .references.multi.payload`);
  - window 2026-01-01..01-31 (`fftfmeta_golden_helpers.py:98`);
  - stationarity off, winsorization on;
  - it contains 12h group hashes such as `"12h_L1_trend_EMA.parquet"`.
- **degraded:** training [1h] only.

Consumer: `tests/feature_engineering/test_fftfmeta_golden.py:35-36,40-58` (multi), `:61` (degraded), `:83`, `:129` (via `fftfmeta_golden_helpers.load_baseline`, :308-309).

**Verdict for multi: YES.**

- The 1h primary with a 12h training timeframe gives D0 = 31464 1h bars. That puts `ingest_start` at 2022-01-19, before the data start, so it is warmup-truncated.
- The 12h series is currently ingested from 2024-01-01. After the extension it would be ingested from 2022-01-19.
- Recursive 12h columns would change bitwise: EMA, DEMA, TEMA, T3, KAMA, MAMA, HT-TRENDLINE, SAR/SAREXT, and the L3/L4/L6 columns built on them. The `12h_*.parquet` group hashes, `group_files_sha256` and the manifest/task stripped sha would all change.

**Verdict for degraded: NO** (1h only).

**Caveat: this golden is already red before the 12h change.**

- The FF-NAME K2 receipt `handoffs/run_receipts/ffname_refreeze_k2/fftfmeta__baseline.json` records `decision: pre_existing_drift` and `pre_change_reproduced: false`.
- The pre-change code differs from the file on six items: degraded/multi groups, manifest and task.
- `handoffs/run_receipts/20261020-ffdstar-b4-plan.md:26,214` says "已是既有紅…不重凍" (already red, do not re-freeze).
- The 12h change only adds more drift.

Other facts:

- **Identity-only pins:** none.
- **Freeze:** `venv/bin/python handoffs/run_receipts/fftfmeta_probes/freeze_baseline.py --refreeze-baseline` (`handoffs/run_receipts/20260924-fftfmeta-golden-freeze.json` .command).
- **Runtime:**
  - 89.6 s for both references at current code (K2 receipt `new_elapsed_seconds`);
  - about 1.3 min for the test (`20261020-ffdstar-b4-plan.md:53`);
  - the 2026-09-24 pre-warmup era took 9.9 s for multi and 5.2 s for degraded.
- **Test edits needed if re-frozen:** the file is a K2 golden whose bytes are bound to the FF-NAME receipt `new_sha256`. See `tests/feature_engineering/test_ffname_refreeze.py:1020-1021` (`test_k2_sidecar_per_name_equal`) and `bytes_bound` at :630-633. A re-freeze turns that test red unless the receipt chain is extended.

**allowed_paths.json:** policy only, **NO**.

---

## 3. framepath (`tests/_golden/framepath/`)

### cgsa_fingerprint.json (12 cells)

Cell definitions are in `scripts/freeze_framepath_baseline.py:57-65` and `cell_settings` at :204-236.

- symbol = BTCUSDT, primary = 1h, start = 2026-01-01 (end defaults to 2026-01-31 via `ffstat_helpers.run_stat`);
- `multi = cell in (C3, C6, C9)` → training `["1h","12h"]` (`fftfmeta_golden_helpers.MULTI_TFS`, :32); every other cell uses training [1h];
- stationarity is on except C2 and C10; C11 has no start date.

| cell | 12h? | verdict | reason |
|---|---|---|---|
| C1, C2, C4-streaming, C4-hybrid, C5, C7, C8 | no, training [1h] | **NO** | 1h only; D0 3050 → ingest 2025-08-14 |
| C10 | no, training [1h]; L5 reference ETHUSDT at training[0] = 1h (`feature_factory.py:4627-4628`) | **NO** | |
| C11 | no, training [1h], no start → full 1h history | **NO** | 1h untouched |
| **C3** (multi, serial, stationarity on) | yes | **YES** | Public D0 = 31056 → ingest 2022-02-07, truncated to the 2024-01-01 data start for 12h. The 12h calibration depth is `estimate_max_warmup_bars(12h)` + N = 3050 + 1000 = 4050, against only 1462 12h bars before 2026-01-01, so it reaches the data start. The golden records `run_status: partial`, `failure_reasons: ["calibration_insufficient_history:546"]`. After the extension (BTC has about 5000 12h bars before 2026-01-01, more than 4050) most of the 546 columns would get calibration values, so stationarity decisions, values, run_status and manifest would all change. |
| **C6** (= C3 with `FFACT_MULTI_TF_PARALLEL=1`) | yes | **YES** | same as C3 |
| C9 (= C3 + allow_partial; `BTCUSDT/12h` deleted in a kline copy) | 12h deleted | **NO (likely)** | Refused before generation: `CalibrationError … No data returned for BTCUSDT/12h`, 0 rows. The kline copy is now larger, but nothing in the fingerprint depends on 12h content. |

**Identity-only pins:** none in the fingerprint. C9's receipt records `source_kline` as a path only, not a sha. Its test checks only the primary (1h) shape in the copy (`test_framepath_invariance.py:~198-200`).

**Consumers:**

- `tests/feature_engineering/test_framepath_invariance.py:183-206` (`test_cell_matches_frozen_baseline[cell]`).
- `:218-238` (`test_boundary_02_run_status_per_cell`) **statically asserts that C3 and C6 are `partial` with `calibration_insufficient_history`**.
- `tests/feature_engineering/test_framepath_disposition.py:2055-2056` (`test_check_0_baseline_existing_cells_preserved`). Its git-lineage rule (`baseline_lineage_errors`, :2010) **turns red if an existing cell's column values are rewritten**.
- `tests/feature_engineering/test_ffname_refreeze.py:1020-1021`, plus the PRE-PROV follow-on at :1085-1110 (K2 byte binding).

**Freeze and re-freeze path:**

- `scripts/freeze_framepath_baseline.py freeze` runs only at `code_anchor` 6e07e0ad (`code_state_errors`; `test_framepath_invariance.py:40` `test_boundary_09`).
- It only appends missing cells and never re-runs existing ones (docstring :660-667).
- Later rewrites went through the FF-NAME K2 refreeze (`scripts/ffname_refreeze_framepath.sh` with `WT=<c9737729 worktree>`) and `scripts/preprov_refreeze.py framepath` (manifest_sha only).
- **None of the existing tools re-freezes C3/C6 values at the current HEAD for a data change.** It needs:
  - a new procedure or approved-lineage rule;
  - an edit to `CALIBRATION_PARTIAL_CELLS` (`scripts/freeze_framepath_baseline.py:65`) and to the freeze refusal at :643-650 if C3/C6 become `complete`;
  - an edit to `test_boundary_02` (`test_framepath_invariance.py:228-234`);
  - an extension of the lineage and K2 receipt binding.

**Runtime:**

- Per the golden's `memory.seconds`: C3 216.5 s, C6 224.3 s, C9 23.6 s.
- All 12 cells take about 1225.6 s per side (`scripts/ffname_refreeze_framepath.sh:8`) and 1207.5 s at current code (`handoffs/run_receipts/ffname_refreeze_k2/framepath__cgsa_fingerprint.json` `new_elapsed_seconds`).
- `preprov_refreeze.py framepath` takes about 30 min for 12 cells (docstring :21).
- The C3 and C6 re-runs alone would take about 7.5 min, plus whatever the longer 12h ingest adds (unknown).

### The other framepath goldens

| file | content | consumer | verdict |
|---|---|---|---|
| test_disposition.json | test node IDs and AST hashes (2245 node IDs; only test-name strings mention kline_cache) | `test_framepath_disposition.py:37` | **NO** |
| compare_domain.json | manifest-exclusion policy | `test_framepath_disposition.py:38` | **NO** |
| v1_layout/FPV1USDT/cfgv1fixture | synthetic V1 layout fixture | `tests/api/test_framepath_api_h5.py:551,577`; `test_framepath_disposition.py:1740-1742` | **NO** |

---

## 4. icfirstalign (`tests/_golden/icfirstalign/`)

Shared settings:

- `icfirstalign_helpers.py:26-28`: SYMBOL BTCUSDT, PRIMARY **12h**, S2_WINDOW 2025-07-01..2026-03-31.
- 12h bars between 2024-01-01 and 2025-07-01: 547 days × 2 = **1094**.
- Freeze command: `env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python scripts/freeze_icfirstalign_baseline.py <stage>` (docstring :8). The stages are `l3-default`, `probe`, `calibration` and `worker-counts` (:290-294).

| file / cell | definition | verdict | evidence |
|---|---|---|---|
| **probe_baseline.json P2** | 12h primary, training [12h], trend default indicators, S2 window, stationarity off (`freeze_icfirstalign_baseline.py:78-86`) | **YES** | D0 = 3317 > 1094 → ingest 2020-07-02, truncated. The golden shows a 12h domain call with rows 1641 (from the data start), `late_columns` 378, and one round. After the extension `lo` > 0, so the 378 late columns trigger doubling to 6634. `rounds`, `window.ingest_start`, `max_warmup_bars`, `domain_calls.rows`, `first_finite_sha256` and `late_names_sha256` all change, in both `jia.P2` and `yi.P2`. |
| probe_baseline.json P1 | 12h primary, training [12h,1h], EMA8/SMA13, window 2026-04-13..04-27 (:69-75) | **NO** | D0 878 → ingest 2024-12-16, after the data start. One round with 0 late columns. The 12h rows (994) come from a timestamp `searchsorted`, not from positions. |
| calibration_baseline.json S3_winsor_on / S3_winsor_off (jia and yi) | 12h, training [12h], fracdiff on, `calibration_bars` 200 for 12h, S2 window, winsorization on/off (:89-96) | **NO** | The calibration depth is 878+200 = **1078** (on) and 626+200 = **826** (off), both less than the 1094 bars available. The golden's `rows` equal exactly 1078 and 826, so doubling never reached the data start. The 3 shortfall columns are `meta_*` with shortfall 200, meaning 0 finite values, which classifies as `deferred` and does not trigger doubling (`feature_factory.py:2555-2563`). The tail slice (`history.iloc[len-depth:]`, :2486) is unchanged, and `_public_row_count` uses ingest 2024-03-05 or 2024-07-21, which is unchanged. |
| l3_default_arm.json | S2 `s2_payload()` default, 12h only, S2 window (`freeze_icfirstalign_baseline.py:48-65`) | **NO** | D0 878 → ingest 2024-03-05, not truncated. The same indicator set had 0 late columns at depth 878 (P1). |
| worker_counts.json | S2m `s2_payload(["12h","4h"])`; the **4h** worker `_tf_worker_entry(…,"4h",…)` (:273-286) | **NO** | 4h data is untouched. The worker window uses data-independent D0 878 (`multi_tf_generator.py` ~1793-1806, `public_warmup_bars` = None). |
| contract.json | errors, budgets and selector policy | **NO** | no data |

**Consumers:**

- `tests/feature_engineering/test_icfirstalign_calibration_domain.py:32-34`. Probe tests at :71-80 (`test_probe_bytes_equal_head_jia[P1,P2]`) and :83-89 (`…_yi[P1,P2]`); `test_boundary_02` at :298-303 uses the P2 late sha. Calibration tests at :106-108 (`test_calibration_packets_bytes_equal_head_jia`) and :466-467.
- `test_icfirstalign_l3_arms.py:32,125-131`.
- `test_icfirstalign_domain.py:570,600-643`.
- `test_ffname_refreeze.py`: K1 checks at :402-403 for calibration_baseline, l3_default_arm and worker_counts; K2 at :1020-1021 for probe_baseline.

**Identity-only pins:** none.

**Re-freezing probe_baseline.** The `jia` mode of the freeze script cannot run at the current code; the ffname contract notes this ("產生腳本於現行碼不可執行，以消費測試之 run 路徑產生", the generator cannot run on current code, so records come from the consuming test's run path). Recipe `icfa_probe` in `scripts/ffname_refreeze.py:289-323` records via the consuming test's `_generate`. A re-freeze of P2 also breaks the K2 byte binding (`test_ffname_refreeze.py:1021`).

**Runtime:**

- probe stage wall 68.6 s (jia+yi, P1+P2; `handoffs/run_receipts/20261004-icfirstalign-freeze-baselines.json` `.probe.wall_s`);
- FF-NAME `icfa_probe` 40.3 s (`ffname_refreeze_k2/icfirstalign__probe_baseline.json`);
- calibration stage 17.2 s (same 20261004 receipt), which is not needed.

---

## 5. icpostleak (`tests/_golden/icpostleak/contract.json`): VERDICT NO

- The kline is BTCUSDT **1h**, 3000 rows (`contract.kline`).
- It is loaded as `kline_frame(...,"1h").iloc[:3000]` (`tests/feature_engineering/test_icpostleak.py:48-49`). That is a positional head, but on 1h, which is untouched.
- Consumers: `test_icpostleak.py:33`, `tests/api/test_icpostleak_api.py:26`, `tests/api/test_numview_ic_page.py:88`, `test_numview_policy.py:73`, `test_numview_core.py:107`, `test_numview_acceptance.py:93`.
- No identity pins.
- No freeze script (parameter contract).

## 6. mtf_align (`tests/_golden/mtf_align/before.json`): VERDICT NO

- The file holds the literal `{"1h@12:00": 91729}`, a look-ahead fingerprint captured before the fix.
- Its only consumer, `tests/feature_engineering/test_mtf_align_golden.py:161-163`, asserts that literal against itself. Nothing regenerates it.
- The other tests in that file read 12h via h5 with an explicit timestamp window 2026-01-01..01-03 (:28-31, :59-73) and assert raw close values. Those rows are unchanged.

---

## Things outside the golden files that will also need attention (no action taken)

- **The FF-NAME refreeze receipt chain binds current golden bytes.** `test_ffname_refreeze.py:210,550-560,619,630-633` covers the K2 goldens, and `:402-403` (value-equal to pre-change) covers K1. Any 12h re-freeze of a K2 golden in this family (framepath cgsa_fingerprint, icfirstalign probe_baseline, fftfmeta baseline) turns `test_k2_sidecar_per_name_equal` red unless a new follow-on receipt rule like PRE-PROV's is added.
- **Working-tree note.** `git status` during this audit showed ` D tests/_golden/numview/preregistered_criteria.json`. Nothing I ran references that file (I grepped the helper modules I imported). It is most likely another session's work in progress. This audit wrote nothing to the repo.

## Appendix C (fam_C.md)
# Family C — 12h history extension golden impact (READ-ONLY audit, 2026-10-22)

Families: numview, preprov, prered, probewinsor, ratiounsafe, v2_ts.
Method: read code/JSON; one read-only scratch script (`famC_d0.py`, `-B`, `NUMBA_CACHE_DIR`=scratch; `git status --porcelain` md5 identical before/after) computing `estimate_max_warmup_bars` / calibration depth for each config and reading current bar counts (all 10 symbols: 12h=1696, 4h=5088, 1h=20352). Output in `famC_d0.out`.

Key computed numbers (current code, `config/scan_config.yaml` + user config):
| config | primary/training | D0 (primary bars) | stationarity | 12h calib depth (12h bars) |
|---|---|---|---|---|
| preprov h12h1_multi / h12h1_replace | 1h / 1h+12h | 31056 (1h) | on | 4050 |
| preprov h1_stat_on (other h1_* similar) | 1h / 1h | 3050 | on | n/a |
| preprov multi_symbol | 12h / 12h | 878 | off | n/a |
| ratiounsafe s1 | 12h / 12h | 1098 | off | n/a |
| ratiounsafe multi_tf_names | 12h / 12h+4h | 1098 | off | n/a |
| NUMVIEW A 12h (also A 4h/1h) | 12h / 12h | 3050 | on (N=1000) | 4050 |
| NUMVIEW B 1h+4h+12h | 1h | 31056 | on | 4050 |
| NUMVIEW B 1h+4h | 1h | 10688 | on | n/a |
| NUMVIEW C 12h (prod default) | 12h | 3784 | off | n/a |
| probewinsor s2-base 12h pp-on w1 (from baseline output_window) | 12h | 878 (=374+504) | per family | 1878 |

---

## 1. tests/_golden/v2_ts/g1_baseline_fingerprint.json
1. Consumer: `tests/feature_engineering/test_v2_timestamp_golden.py:17` (`_GOLDEN_DIR`), `:86-87` load, asserted `:142-144`. Also FF-NAME K0 byte-binding: `scripts/ffname_freeze_baseline.py:1411`, `tests/_golden/ffname/contract.json` refreeze.baseline_goldens, `handoffs/run_receipts/ffname-refreeze.json` (class K0, new_sha256 94fdfad0…).
2. Cells: synthetic 5-row DataFrame (`test_v2_timestamp_golden.py:127-136`, `pd.date_range("2026-05-01", periods=5)`), symbol label "BTCUSDT"/"1h" only as storage keys. No kline read.
3. Identity pins: none.
4. **VERDICT: NO** — pure synthetic frame; never reads kline_cache.h5.
5. Freeze: no script (committed by hand in fd3ce6ac / 935b24fd). No test edit needed.
6. Runtime: n/a (seconds).

## 2. tests/_golden/prered/allowed_red.json
1. Consumers: `tests/governance/test_prered_allowed_red.py:19` (ALLOWED), tests `:107-125`; `scripts/testreg.py:4586` (ALLOWED_RED_REL); `tests/registry/test_testreg_review.py`; `tests/feature_engineering/test_failopen_correctness.py:40` (comment only).
2. Content: 30 rows `{node, owner_ticket=FFSTORE, reason, trigger, state}` — list of pytest node ids allowed to be red (old feature runs deleted). Compared against a static EXPECTED set (`test_prered_allowed_red.py:~88`, "集合不等").
3. Identity pins: none.
4. **VERDICT: NO** — no data values; static node list. (Caveat: if the 12h extension turns some *other* test red, it is not in this allow-list — that is a general consequence, not a golden change.)
5. Freeze: `handoffs/run_receipts/prered_probes/build_allowed_red.py` (census `20261003-prered-red-census.txt`). No edit needed.
6. Runtime: n/a. (Note `handoffs/run_receipts/20261003-prered-refreeze.json` is about failopen units BTCUSDT/12h, ETHUSDT/12h, ETHUSDT/1h — failopen family, not this one.)

## 3. tests/_golden/ratiounsafe/
Consumers (all four files): `tests/feature_engineering/test_ratiounsafe_registry.py` — contract `:30`, branch_oracle `:43` (via contract `branch_oracle_path`) used `:109`, baseline.json `:265-267` (`before` fixture) used `:324,:344-350,:355-366,:386-393,:427`, baseline_after.json `:398-403,:426,:445-450`; freeze module imported `:35-36`. Contract-only consumers: `tests/api/test_ratiounsafe_ic_page.py:20`, `tests/feature_engineering/test_feature_naming.py:21`, `tests/feature_engineering/test_ratiounsafe_wiring.py:23`, `tests/api/test_numview_ic_page.py:89`, `tests/feature_engineering/preprov_helpers.py` (pattern category). FF-NAME byte binding: `tests/feature_engineering/test_ffname_refreeze.py` (K1 baseline.json `:403`, K2 baseline_after `:1021`, K3 branch_oracle `:516`, K0 contract `:235`; `bytes_bound` `:632-635`), receipt `handoffs/run_receipts/ffname-refreeze.json`.

Cell definitions (`tests/_golden/ratiounsafe/contract.json`; `scripts/freeze_ratiounsafe_baseline.py`):
- `s1`: BTCUSDT, primary=training=12h, `days: 1000`, payload EMA8/SMA13 + pattern, close only; arms off/on (dead-drop off/default), each with preprocessing on/off. Window = `_end_and_start` (`freeze_ratiounsafe_baseline.py:41-48`): end = max 12h timestamp (2026-04-27), start = end − 1000 days = **2023-08-01** (before current data start 2024-01-01). Stationarity: off (payload has no preprocessing ⇒ defaults fracdiff/adf False, `feature_config.py:243-244,261-262`). Recorded `n_rows=1695` in all s1 records (baseline.json and baseline_after.json).
- `multi_tf_names`: BTCUSDT primary 12h, training [12h,4h], days 200 ⇒ start ≈ 2025-10-09, stationarity off, dead-drop default on; only the sorted *names* are frozen.
- `branch_kline`: BTCUSDT 12h `rows: 1500` → `branch_frame` = `ffstat_helpers.kline_frame(...).iloc[:1500]` (`freeze_ratiounsafe_baseline.py:131-132`) — FIRST 1500 bars of the full 12h series; TA-Lib CDLDOJI/CDLENGULFING/EMA8/SMA13 then L6.5 branches; `native_arm` 12h→1h ratio 12.

| file | 12h cells | identity pins | VERDICT | reason |
|---|---|---|---|---|
| baseline.json (stage before) | s1_off, s1_on, s1_off_pp_disabled, s1_on_pp_disabled (all 12h); multi_tf_names (12h+4h) | n_rows 1695 (= every 12h bar from 2024-01-01; start 2023-08-01 is before data) | **YES** (s1_*); **CONDITIONAL** (multi_tf_names) | s1 start 2023-08-01 < data start ⇒ run is clipped at data start; extension adds ~300 output rows (n_rows ~1995) and re-seeds every recursive/rolling value. multi_tf_names: 1294 12h bars before start vs D0=1098 (ingest ≈ 2024-02-13, not truncated in round 1); only if the doubling round triggers (D=2196 → reaches data start) would values change; test compares name sets only (non-unsafe set equality, no deletions, `test_ratiounsafe_registry.py:386-393`), names flip only via dead-drop ⇒ likely unchanged, UNKNOWN whether a doubling round occurs (not recorded) |
| baseline_after.json | s1_off, s1_on | n_rows 1695 | **YES** | same s1 window; `test_after_baseline_regression` (`:396-403`) asserts n_rows + every column digest |
| branch_oracle.json | registry*, append_arm, native_arm (12h, first 1500 bars) | implicitly "first 1500 12h bars = 2024-01-01…" | **YES** | `.iloc[:1500]` positional head ⇒ after prepend the 1500 rows become ~2019–2021 data ⇒ every digest changes (`test_ratiounsafe_registry.py:109` `_assert_matches_oracle`) |
| contract.json | — | none | **NO** | parameters only |

Other 12h head reads without golden: `test_ratiounsafe_wiring.py:36` (`.iloc[:600]` of 12h; within-run checks only — inputs change, assertions self-relative).

5. Freeze: `venv/bin/python scripts/freeze_ratiounsafe_baseline.py --stage before|after|branch-oracle` (`freeze_ratiounsafe_baseline.py:7-10`). No anchor/provenance gate in this script (writes from HEAD). Caveats: (a) `before` is semantically a pre-RATIOUNSAFE snapshot; regenerating it at current HEAD loses that meaning (tests' set relations would still hold — my reading, not run). (b) Any byte change to baseline.json / baseline_after.json / branch_oracle.json breaks `tests/feature_engineering/test_ffname_refreeze.py` (K1/K2/K3 compare against the FF-NAME base blob and `bytes_bound` requires sha == `ffname-refreeze.json` new_sha256 or a PRE-PROV follow-on section) ⇒ **test edit / receipt-chain extension required**. (c) Alternatively edit the test/contract (e.g. branch_kline `.iloc[-1500:]` or explicit dates; s1 `days` ≤ ~840 or explicit end-anchored window inside 2024-01-01..) — still requires re-freeze of the digests that change.
6. Runtime: `handoffs/run_receipts/ffname_refreeze_maps/ratiounsafe__baseline.json` `record_elapsed_seconds: 115.7` (stage-before recipe, 4 s1 runs + multi_tf_names); `handoffs/run_receipts/ffname_refreeze_k2/ratiounsafe__baseline_after.json` `new_elapsed_seconds: 67.1` / `old_elapsed_seconds: 66.9` (2 s1 runs). After extension s1 has ~18% more rows — expect ~2.5 min + ~1.3 min. branch-oracle: unknown (no receipt; TA-Lib on 1500 rows + 5 L6.5 branches, expected seconds).

## 4. tests/_golden/probewinsor/
Files: contract.json (9.9 KB), baseline.json (4.6 MB; 29 cells).
1. Consumers: `tests/feature_engineering/probewinsor_helpers.py:23` (BASELINE_PATH), `:37` baseline(); `tests/feature_engineering/test_probewinsor.py` — `test_boundary_02` `:100-103` (ON cells, keys "all"), `_03` `:105-108`, `_04` `:111-120`, `_06` `:134-137`, `_08` `:175-177` (truth_table), `_10` `:200-215` (provenance incl. `kline_sha256` `:210`); `tests/api/test_probewinsor_batch_resume.py:103-105` (config_hash only); FF-NAME K1 rekey `test_ffname_refreeze.py:332-352, :470-480` + receipt `ffname-refreeze.json` (K1, 1ab703af…).
2. Cells (`contract.json` families; BTCUSDT; all windows 2026-01-01..2026-01-31 except e12h_dd ..2026-03-01 and e1h_nostart [null,2026-01-31]); `stationarity` true only for e1h_st, e1h12h_st. Cell = family × pp(on/off) × winsor(w1/w0).
3. Identity pins: `contract.json` `kline_sha256` = b1ee5b9a… and `kline_sha256_authority` → `tests/_golden/failopen/baseline.json#environment.kline_sha256`; `baseline.json` top-level `kline_sha256` (same). `test_boundary_10` (`test_probewinsor.py:210`) asserts frozen == contract == failopen-authority — it does NOT hash the live file, so it stays green unless the failopen baseline is refrozen with the new sha (then RED until contract+baseline updated). The freeze script write mode and `--check` compare live `ph.kline_sha256()` (`scripts/freeze_probewinsor_baseline.py:70-71, :159-160`) ⇒ refuse/differ after extension. Per-cell `output_window.ingest_start` timestamps recorded (all ≥ 2024-09-05; none at data start).

Per-cell verdicts (from baseline `output_window`/`rounds`, and calibration depth):
| cells | 12h? | VERDICT | evidence |
|---|---|---|---|
| e1h.*, e1h_l45.*, s1h.*, e1h_st.* (all 1h-only, training [1h]) | no | **NO** | training [1h]; 1h data untouched |
| e1h_nostart.off.w1 | no | **NO** | 1h only (start None ⇒ full 1h history, unchanged) |
| e12h.{on,off}.{w1,w0} | 12h | **NO** | max D after doubling 878 12h bars; ingest_start 2024-09-05..2025-06-09 (> data start); no stationarity ⇒ public window bytes identical (assuming overlap rows byte-identical) |
| e12h_dd.{on.w1,off.w1,off.w0} | 12h | **NO** | same, ingest ≥ 2024-09-05 |
| e1h12h.{on,off}.{w1,w0} | 1h+12h | **NO** | max depth 9984 1h bars, ingest ≥ 2024-09-30; no stationarity |
| e1h12h_st.off.w1, e1h12h_st.off.w0 | 1h+12h | **NO** | pp=false ⇒ `l65_enabled` false ⇒ `_stationarity_config_enabled` false (`feature_factory.py:367-372`) ⇒ no calibration; ingest 2024-11-15 |
| **e1h12h_st.on.w1** | 1h+12h | **YES** | stationarity on ⇒ 12h calibrated separately; depth = est(12h)=878 + N 1000 = 1878 12h bars > 1462 bars available before 2026-01-01 ⇒ calibration slice reached data start (`_calibrate_timeframe` `feature_factory.py:2460-2500`); baseline `quality_status: "partial"` (vs `e1h_st.on.w1` "complete") consistent with 12h calibration shortfall; after extension the slice starts later and short columns get N values ⇒ fracdiff/ADF decisions + 242 `_12h_` column fingerprints + quality_status change. Asserted by `test_boundary_02` (keys "all") |
| truth_table (top-level) | — | **NO** | config-resolution only (`probewinsor_helpers.py:464-486`), no generation |

5. Freeze: `venv/bin/python scripts/freeze_probewinsor_baseline.py` — ONE-TIME write at the anchor (pre-PROBEWINSOR) code: refuses if baseline exists, if HEAD contains `anchor_absent_symbols`, if production digest ≠ `anchor_production_py_sha256`, or live kline sha ≠ contract (`freeze_probewinsor_baseline.py:5-8, :39-71`; `docs/PROBEWINSOR_SPEC.md:42`). `--check [--cells …]` compares without writing. Re-freezing after extension therefore needs: an anchor-commit worktree (frozen_at_head 820e8f14) + new kline, contract `kline_sha256` and failopen authority updated, then FF-NAME rekey mapping re-applied (current bytes are the FF-NAME K1 rekey of the anchor freeze) ⇒ **test edits needed** (contract kline_sha256, test_ffname_refreeze K1 binding). Only 1 of 29 cells changes values, so a targeted single-cell update is the cheap path but no tool exists for it.
6. Runtime: per-cell `elapsed_seconds` in baseline.json sum = 184.5 s (e1h12h_st.on.w1 = 23.02 s); FF-NAME recording `handoffs/run_receipts/ffname_refreeze_maps/probewinsor__baseline.json` `record_elapsed_seconds: 195.8`. Affected-tests rerun is the expensive part: `HANDOFF.md:300` (PROBEWINSOR anchor round 9.5 h for affected tests — not the freeze itself).

## 5. tests/_golden/preprov/
Files: pre_change_fingerprints.json (11 MB), output_size.json, reader_inventory.json, refreeze_receipt.json.

### 5a. pre_change_fingerprints.json
1. Consumers: `tests/feature_engineering/preprov_helpers.py:44` (PATH); `tests/feature_engineering/test_preprov_acceptance.py:264-273` (`test_oracle_06_values_unchanged`, all CELL_SYMBOLS), `:275-280` (covers all cells). NUMVIEW legacy baseline: `tests/feature_engineering/numview_helpers.py:39` (LEGACY_BASELINE_PATH), `tests/feature_engineering/test_numview_acceptance.py:906-919` (regenerates all 11 PRE-PROV cells, `legacy=True`; working-tree file), `tests/feature_engineering/test_numview_identity.py:1631` (h1_stat_off only), `tests/feature_engineering/test_numview_criteria.py:741` (reads cell names for `*legacy*` regen coverage).
2. Cells: `preprov_helpers.CELLS` (`preprov_helpers.py:195-224`); WINDOW = ("2026-01-01","2026-01-31") (`fftfmeta_golden_helpers.py:98`), BTCUSDT unless noted; payloads `ffstat_helpers.stat_payload` (`ffstat_helpers.py:92-113`, base `fast_payload` `fftfmeta_golden_helpers.py:44-68`). Header `head` 2264d5c4, `command` recorded in file.
3. Identity pins: none (no kline sha / row count; fingerprints are value hashes).
| cell | primary / training | stationarity | VERDICT | reason |
|---|---|---|---|---|
| h1_stat_on | 1h / [1h] | on | **NO** | 1h only |
| h1_stat_off, h1_pp_off, ratio_unsafe, dead_drop, ic_first, ic_first_default, h1_replace_stat_on | 1h / [1h] | mixed | **NO** | training [1h] (`preprov_helpers.py:196-221`) |
| **h12h1_multi** | 1h / [1h,12h] | on (fracdiff+adf) | **YES** | D0 = 31056 1h bars ⇒ ingest_start = 2026-01-01 − 31056h×1.1 ≈ 2022-02-07 < 2024-01-01 ⇒ already warmup-truncated; 12h is ingested from the same date ⇒ after extension 12h loads from ~2022 (1h still from 2024-01-01) ⇒ 12h public values re-seed; plus 12h calibration depth 4050 > 1462 available ⇒ calibration changes. 4594 of 8323 columns are `_12h_` |
| **h12h1_replace** | 1h / [1h,12h], mode replace | on | **YES** | same; 3552 of 7184 columns `_12h_` |
| **multi_symbol** (BTCUSDT, ETHUSDT) | 12h / [12h] worker | off | **YES** | window (None, None) (`preprov_helpers.py:205-206`) ⇒ `run_multi_symbol` full history from first 12h bar ⇒ row count and all recursive values change (161 cols each) |
5. Freeze: `venv/bin/python scripts/freeze_preprov_baseline.py [--out PATH] [--work DIR]` (`scripts/freeze_preprov_baseline.py:7-9`); only gate = momentum/api clean vs HEAD (`:33-41`), regenerates ALL 11 cells/12 runs (no per-cell option). Sequencing constraint: it is NUMVIEW's legacy baseline, so it must be refrozen on code without NUMVIEW product changes (NUMVIEW b1 is contracts/tests only so far). No test literal edits needed for preprov tests themselves.
6. Runtime: per-cell `generation_seconds` in `tests/_golden/preprov/output_size.json` (post-change code, same cells): total 1095.6 s ≈ 18 min (h12h1_multi 357.5, h12h1_replace 263.0, ic_first_default 196.6, h1_stat_on 89.5, h1_replace_stat_on 61.1, ic_first 30.3, ratio_unsafe 28.1, dead_drop 27.6, h1_stat_off 23.3, multi_symbol 11.7, h1_pp_off 6.9). After extension multi_symbol runs ~3× rows and h12h1 12h part ~2× rows ⇒ estimate ~20 min. No recorded elapsed for the freeze run itself (UNKNOWN).

### 5b. output_size.json
Consumers: `preprov_helpers.py:45` (path constant), `scripts/preprov_output_size.py`; tests only exercise the script on tmp (`test_preprov_reader.py:162-203`) — no value assertion against this file found. Content: size measurements; `full_feature_run` = BTCUSDT 12h production-default full-history run (`handoffs/run_receipts/20261020-preprov-fullrun-size.md`: 1,696 rows, 412.6 s, 1.51 GiB). **VERDICT: NO (no test asserts it)** but it is stale as a measurement after extension (multi_symbol run_bytes, full_feature_run rows ×~3). Also referenced by NUMVIEW (`test_numview_criteria.py:94-95, :856-859`) as Cell-C 12h cost baseline.

### 5c. reader_inventory.json
Consumer: `tests/feature_engineering/test_preprov_helpers.py:35,49,259` (AST scan inventory of directory-scan call sites). **VERDICT: NO** (code inventory, no data).

### 5d. refreeze_receipt.json
Consumers: `tests/feature_engineering/test_ffname_refreeze.py:626, :632-635, :701-731` (`preprov_followon_problems`: sha256_after must equal current bytes of failopen/baseline.json and framepath/cgsa_fingerprint.json), `tests/feature_engineering/test_framepath_disposition.py:1978-2019`. Content: structural refreeze sections for `tests/_golden/failopen/baseline.json` (unit BTCUSDT/multi) and `tests/_golden/framepath/cgsa_fingerprint.json` (12 cells), each with `sha256_before/after`, `base_commit`.
**VERDICT: NO values of its own**, but it pins the BYTES of the failopen and framepath goldens ⇒ if those families are refrozen for the 12h extension, `test_ffname_refreeze` (`bytes_bound`) and `test_framepath_disposition` go RED unless this receipt/chain is extended (test/receipt edit required). Producer `scripts/preprov_refreeze.py` (framepath ≈ 30 min, failopen ≈ 36 min per its docstring `:23-24`).

## 6. tests/_golden/numview/preregistered_criteria_v2.json
State: committed file is `preregistered_criteria.json` (v1, a11c8493); working tree deletes v1 and adds **untracked** v2 (`git status`: ` D …criteria.json`, `?? …criteria_v2.json`).
1. Consumers: `tests/feature_engineering/test_numview_criteria.py:198` (`_criteria_path`, v1/v2 exactly-one), `:1230`; `tests/feature_engineering/numview_helpers.py:35-36`; `handoffs/run_receipts/numview_probes/_estimate_gate.py:66-110` (`resolve_criteria_path`, `criteria_sha256` binding); `estimate.py` (`criteria_sha256` `:1064`).
2. Cells (rules, `cell_rules` + `cell_definitions`): enumerate every symbol×tf from kline_cache.h5; output segment = LAST 500 primary bars; A = each symbol×tf single-TF (trend default, rolling 5/13, cross+ratio ops, lag off, mode replace, winsor+fracdiff+ADF on ⇒ stationarity on), entry `run_ic_first`; B = per symbol, primary = finest TF, training = finest + TFs whose A cell is not history-blocked (`b_membership`); C = production default full config. `window_rule`: generate output + required pre-history (D0 + N_cal), no full history; `insufficient_history` authoritative = run completeness (partial with only `*_insufficient_history` reasons ⇒ blocked), prefilter `min_history_bars` 1500.
3. Identity pins: none (grep: no kline sha, no 1696, no 2024-01-01). `_doc` narrates the estimate observation "A:12h 與 B 之生成皆為 run_status=partial".
4. **VERDICT: NO (file values)**; **CONDITIONAL (outcomes it drives)**. With current data A:12h is clipped: available = 1696−500 = 1196 < required 3050+1000 = 4050 ⇒ partial ⇒ blocked ⇒ B excludes 12h. After extension (total 12h bars T): A:12h not clipped iff T ≥ 4550 (12h history starting ≲ 2020-02-03); C:12h not clipped iff T ≥ 4284 (≲ 2020-06-15). Using approximate Binance listing dates (my assumption, not verified): BTC/ETH/BNB/ADA/XRP/TRX/LINK/DOGE (≥ ~4976 bars if back to 2019) and BCH (~4684) pass A; SOL (~4170 from 2020-08-11) stays clipped for both A (3670 < 4050) and C (3670 < 3784). Not clipped ≠ complete (sparse columns can still be short) ⇒ authoritative judgement only by running. Consequence: B membership would change from [1h,4h] to [1h,4h,12h] for symbols whose A:12h passes (B with 12h has D0 = 31056 1h bars; 12h warmup then loads from ~2022 — feasible only after extension).
5. Freeze: hand-authored, single commit; v2 may replace v1 only before any receipt (`_doc`; `test_numview_criteria.py:1230` asserts 1 commit). No edit required by the extension (rules are bar-count-agnostic).
6. Runtime: n/a.

### NUMVIEW — planned freezes / committed artifacts
- What Phase 0–4 will freeze (not yet produced): `tests/_golden/numview/pre_change_fingerprints.json` (Task 0.5: G1 IC-page output per A cell × reachable arms, G2 A-cell L6.5 raw at FFACT_USE_POLARS 0/1, G3 B-cell raw+processed — `scripts/numview_freeze_baseline.py:1-15`, all functions `NotImplementedError`), `tests/_golden/numview/refreeze_receipt.json` (Task 4.2), `tests/_golden/numview/decisions.json`, receipts `handoffs/run_receipts/<date>-numview-estimate.json` / `-freeze-baseline.json` (none exist yet; `ls handoffs/run_receipts | grep numview` → only `numview_probes/`). 12h cells planned: A:<sym>:12h ×10, B:<sym> (12h if A passes) ×10, C:<sym>:12h ×10 (`docs/NUMVIEW_SPEC.md:130`, `docs/manifests/NUMVIEW.json:156,164`). Phase 2–4 regen kinds `regen_t22/t3_core/t34/section_g` cover all A/AB cells (`test_numview_criteria.py:166-172`); `regen_section_g` also regenerates all PRE-PROV legacy cells incl. h12h1_multi/h12h1_replace/multi_symbol.
- Committed b1 (a11c8493) artifacts pinning kline identity or 12h length: **none pin a kline sha or 1696**. Checked: `tests/_golden/numview/preregistered_criteria.json` (v1: min_history_bars 1500, no 1696/sha), `momentum/FeatureEngineering/contracts/numeric_view.json` (no kline/bars refs), `momentum/FeatureEngineering/numeric_view.py`, `tests/feature_engineering/numview_helpers.py` (only `KLINE_PATH` `:42`), `test_numview_criteria.py` (enumerates tf keys from h5 `:268-271`; `FULLRUN_SIZE_TF="12h"` + `FULLRUN_SIZE_RECEIPT` `:94-95,:856-859` lets C-12h cite the 1,696-row/412.6 s full-history receipt — after extension that receipt is no longer an upper bound for a C-12h sufficient-window run, ~4284 rows), `_estimate_gate.py`, `estimate.py`. Docs pin 12h length: `docs/NUMVIEW_SPEC.md:48` FACT-RECEIPT "12h:1696 1h:20352 4h:5088"; `docs/NUMVIEW_SPEC.md:130,337` cite 412.6 s BTC 12h full run; `docs/RATIOUNSAFE_SPEC.md:14` "近 1000 天＝1695 根".
- Does the estimate / pre-gate read 12h bar counts? **estimate.py: YES** — `kline_inventory` reads every symbol×tf row count via h5py (`estimate.py:155-168` committed / `:162-175` working tree), `output_window` reads timestamps of the last output_bars (`:203-215`), `history_blocked` prefilter on counts vs min_history_bars (committed `:218-229`), and the working-tree `pre_history_requirement` (`estimate.py:310-342`, uncommitted) reads `stamps.shape[0]` to compute available/clipped/ingest_floor and records `bar_counts` per cell (`:559, :816-837`). **_estimate_gate.require: NO** — it checks only receipt existence, `reported_at`, `criteria_sha256` == current criteria bytes, and cell-id membership (`_estimate_gate.py:81-110`); it does not bind kline identity or bar counts ⇒ an estimate receipt produced before the extension would remain "valid" to the gate while its cell outcomes/costs are stale.
- Recommendation implied by evidence: do the 12h extension BEFORE NUMVIEW Task 0.4 estimate receipt and Task 0.5 freeze (neither exists yet), and refreeze PRE-PROV `pre_change_fingerprints.json` (NUMVIEW's legacy baseline) before NUMVIEW product-code changes.

## Cross-family coupling found
- FF-NAME byte binding (`test_ffname_refreeze.py`, receipt `handoffs/run_receipts/ffname-refreeze.json`) covers ratiounsafe/{baseline,baseline_after,branch_oracle,contract}.json, probewinsor/baseline.json, v2_ts — any refreeze here turns it red without a receipt/chain update.
- preprov/refreeze_receipt.json pins failopen + framepath golden bytes (other families).
- probewinsor `kline_sha256_authority` → failopen baseline `environment.kline_sha256`.
- `test_numview_acceptance` `test_l2_matrix_btc_12h_reproduces_freeze_baselines` (manifest `NUMVIEW.json:156`) ties BTCUSDT 12h to the ICFIRSTALIGN freeze-baselines receipt (icfirstalign family).

## Appendix D (fam_D.md)
# Family D — event-sample / label / split goldens vs. 12h kline history extension (READ-ONLY audit)

Scope: tests/golden/{evtalign, evtlabel, evtwarmup, gap3_label, gap3_random_control, splitunify, tfwindow, icresult_paging}.
Method: read code/JSON only; one read-only h5py timestamp probe on the two la0 feature fixtures (script: scratchpad/famD_ts.py). No pytest, no freeze scripts run.

## Mechanisms established (shared by several goldens)

M1. Event bar table (gap3 family). `tests/momentum/event_samples/helpers.py:23-40` `load_bars()` and `momentum/Analysis/event_samples/bars_source.py:20-48` both read the FULL `{SYM}/{tf}/data` dataset from kline_cache.h5, no window. So any position-based index (`ot[95]`, `ot[100]`, `ot[0]`) moves to ~2019/2020 after the 12h prepend, and any digest taken over the whole table changes.

M2. IC analyze runs on the la0 fixture (`tests/momentum/helpers/ichc_run.py:17-19,30-78`). The features are a STATIC h5 fixture:
- `tests/golden/la0/inputs/ETHUSDT_12h_e53e2290..._a0_tail2000.h5`: probe shows ETHUSDT/12h/timestamps has 1696 rows, 2024-01-01T00:00Z..2026-04-27T12:00Z.
- `BTCUSDT_1h_4a8a0b37..._a0_tail2000.h5`: 2000 rows, 2026-02-03T16:00Z..2026-04-27T23:00Z.

Only the labels/close come from the live kline via `create_kline_storage_manager(cache_dir="data_cache/feature_klines")` (ichc_run.py:71). `read_klines` returns a RangeIndex frame with a `timestamp` column (`momentum/DataExtraction/kline_storage.py:1049`, `reset_index(drop=True)` at ~1109).
- stage0 `_intersect_features_with_kline_period` (`momentum/Analysis/ic_filter_orchestrator.py:441-497`): head trim is computed as `feature_index >= k_start`. Features start 2024-01-01 and the new 12h kline starts earlier, so head stays 0 and tail is unchanged. `metadata.period_alignment` (which carries kline start/bars) is written only when head or tail is non-zero (orchestrator.py:1348-1352), so it is NOT newly emitted.
- stage2 labels (orchestrator.py:3598-3631): `close` is coterminalized at the tail, forward returns come from `generate_returns_by_type`, and the result is reindexed to the feature timestamps. A forward return does not depend on the prefix, so the values are identical. The `validate_alignment` close oracle positions by timestamp (`momentum/core/contracts.py` ~1145-1166), so it is also head-safe.
- stage4 with a split mask (the normal path): `_slice_raw_data_by_mask` (orchestrator.py:1132-1159) today takes the positional branch, because len(raw)=1696 equals len(features)=1696 and the index-equality check passes. After the prepend it takes the reindex-by-timestamp branch. Both branches select the same rows, so decay, grouped and regime results are identical.
- 🔴 LATENT, no golden in my families pins it: stage4 WITHOUT a mask (no split, or a full-sample fallback) passes the full raw kline into `compute_grouped_ic` → `ic_engine._align_with_raw_data` (`momentum/Analysis/ic_engine.py:1475-1498`).
  - Today the lengths match (1696 == 1696), so features and labels are re-indexed positionally onto raw's RangeIndex and grouped_ic gets real values.
  - After the prepend the lengths differ, so it falls to `raw_data.reindex(features_df.index)`. raw has a RangeIndex and the features have a DatetimeIndex, so every row comes back NaN, and `by_year`/`by_quarter`/`by_regime` change (most likely to empty or NaN).
  - Exposure: any 12h-la0 run whose split is not applied. I checked: evtwarmup `event_run` (degraded_full_sample) is NOT asserted by any test. All the asserted runs below have `ic_train_test_split.applied == true`.
  - This positional/RangeIndex coincidence is arguably a pre-existing latent bug that the extension would expose. Flag it to the lead.

---

## 1. gap3_label (46 JSON; 43 x 12h + 3 x 1h)

- Consumers:
  - `tests/momentum/event_samples/test_gap3_analysis_label_producer.py:558-590`: `_golden_paths()` globs `tests/golden/gap3_label/*.json`, the `golden_bars` fixture is `load_bars(cases.SYMBOL, cases.TFS)` at :573-574, and `check_golden` runs at :583-586.
  - :609-720: `_load_golden_json` plus the D1.4 h-invariance tests compare the h1 file against the h3 file.
  - CLI `scripts/gap3_label_golden.py --check` (:147-200). It adds a registry selector guard at :160 and `_label_selector_guard` at :64-71.
  - `test_gap3_label_rawbar_oracle.py` only names the goldens in its docstring (line 5) and does not read them.
- Cell definition (`tests/golden/gap3_label/cases.py`):
  - SYMBOL=ETHUSDT (:16), TF=12h (:18), TFS=("1h","12h") (:20). No start_date: the full bar table.
  - t0 comes from POSITIONAL selectors, `select_t0` at cases.py:46-91:
    - `gap_bars:n` scans `range(95, min(400, len(ot)-20))` (:58).
    - `plain:n` takes `ot[95+10*i]` (:66-67).
    - `tail_mixed` takes `(ot[100], ot[len-3])` (:80).
    - `warmup_mixed` takes `(ot[0], ot[100])` (:86).
  - Today index 95 is 1708171200000 = 2024-02-17 12:00Z (see `trigger_close__close_to_close__k0__long__12h__h3.json`, t0_ms[0]), and `warmup_mixed` ot[0] is 1704067200000 (`decision_bar_open__open_to_horizon_close__k2__long__12h__h1.json`).
- Identity pins:
  - Every file embeds `data_snapshot_digest` = `bar_table_digest()` over the ENTIRE `{n_rows, rows[open_ms, close_ms, open, close]}` table (`loader.py:91-110`, used at :226). All 43 x 12h files share `cf13fb53…`. `check_golden` early-returns FAIL on a digest mismatch (`loader.py:236-243`).
  - The 3 x 1h files share `4cb9c14e…` over the 1h table.
- VERDICT 12h cases (43): YES.
  - (a) The digest covers the whole 12h table, and n_rows goes from 1696 to ~4600-5300, so every 12h case hard-FAILs.
  - (b) A refreeze through the registry re-resolves the positional selectors. Index 95/100/0 then land at ~2019-2020 bars, so t0_ms, events, label_value, analysis_alignment_receipt_hash and purge all change. Only `ot[len-3]` stays the same.
  - (c) The CLI selector guard also flags t0 drift.
  - Label values for a fixed 2024 timestamp would be numerically identical, but the golden is not keyed that way.
- VERDICT 1h cases (3; files `trigger_open__open_to_close__k0__{long,short}__1h__h1.json`, `decision_bar_open__open_to_horizon_close__k2__long__1h__h3.json`): NO.
  - The digest covers the 1h table only.
  - `prepare_analysis_windows` aligns only the trigger TF (`label_value_from_case.py:1068-1077`, align_tfs = tf_keys).
  - The receipt hash does not include any bar-table digest (`_receipt_hash`, :960-999).
  - 1h data is untouched.
- Freeze: `venv/bin/python scripts/gap3_label_golden.py --freeze "tests/golden/gap3_label/*__12h__*.json" --force` (usage at scripts/gap3_label_golden.py:5-8; `cmd_freeze` :118-145 refuses without `--force`).
  - The docstring in cases.py:24-33 warns: never run a global sed on pending flags, and back up then byte-compare before and after.
  - Test edits: none required for the value refreeze; the test reads JSON.
  - Decision needed: if the lead wants to keep the "2024-era" coverage, cases.py selectors would need a design change. As written, a refreeze moves the cases to 2019/2020 bars, which is still valid coverage because the selectors assert their own preconditions.
- Runtime: no freeze wall-clock recorded. Context: the whole event_samples+gap3 suite ran 653 tests in 46.96 s (`handoffs/run_receipts/20260902T050850Z-gap3-rimpl-backend-gap3-suite-v.log`, last line; json `duration_seconds` 50.64). My estimate for the freeze is seconds-level, because it is in-memory label math over ETH 1h+12h. UNKNOWN as a measured value.

## 2. gap3_random_control (20260905__12h.json, 7__12h.json)

- Consumers:
  - `tests/momentum/event_samples/test_random_control.py:366-430`: `check_golden` with `bars = load_bars(SYMBOL,(TF,))` at :30-31, plus mutation and loader tests.
  - :471-511 `test_d54_golden_cli_detects_registry_drift` runs the CLI `--kind random_control --check` on a CLEAN copy and requires rc==0 at :501-511.
  - CLI `scripts/gap3_label_golden.py --kind random_control` (:43-81).
- Cell definition (`tests/golden/gap3_random_control/cases.py`): ETHUSDT 12h (:15-17).
  - POSITIONAL: `_TRIGGER_IDX=(200,400,700)` (:20) and universe `_UNIVERSE_LO,_HI=100,900` (:22). horizon 2, seeds 20260905 and 7 (:73-76).
  - Frozen spec in the JSON today: universe 1708387200000..1742947200000 (2024-02-20..2025-03-26); triggers 1712707200000/1721347200000/1734307200000; n_drawn 40; candidate_count 768.
- Identity pins: `data_snapshot_digest` = sha over the FULL 12h `open_time_ms` + `close` (`momentum/Analysis/event_samples/random_control.py:414-418`); value `77b1b966…` in both files. `check_golden` returns FAIL immediately on a mismatch (`loader.py:126-131`).
- VERDICT: YES (golden FAIL).
  - The pytest path uses the frozen explicit-ms spec, and the candidates are filtered by timestamp (random_control.py:376-386). `rng.choice` picks the same relative pool elements, so sample ids and labels would actually be the same. The digest still FAILs.
  - The CLI positive-control test (test_random_control.py:501-511) FAILs because `_random_control_selector_guard` sees the positional-derived spec and triggers move to ~2019-2020 (scripts/gap3_label_golden.py:74-88).
  - A refreeze via the registry yields an entirely different universe, sample and labels.
- Freeze: `venv/bin/python scripts/gap3_label_golden.py --kind random_control --freeze "tests/golden/gap3_random_control/*.json" --force`. Test edit: none, beyond the same coverage-intent decision as gap3_label. The month-spanning precondition is asserted at cases.py:52-56.
- Runtime: UNKNOWN (not recorded). Estimate: seconds (2 cases, a loop over ~5k rows).

## 3. evtalign/split_baseline.json

- Consumers:
  - `tests/momentum/test_close_coterminalize.py:170-178` runs `handoffs/20260907-probe-split-baseline.py` and requires the stdout "與既有 golden 相同？ **True**".
  - `tests/api/test_isolation_disclosure.py:133-148` reads case `h5_emb0_n500` purge_gap and compares it to `run_analyze(None)` purge.
- Cells: fully SYNTHETIC. `pd.date_range("2024-01-01", periods=n_rows, freq="1h")` (probe :71), with n_rows 500 or 40 and horizons 2/5/12 x embargo 0/12 (probe :125-133).
  - test_isolation_disclosure's run_analyze uses the la0 12h fixture with a split, and only purge_gap (config default_horizon) is compared.
- Identity pins: none from klines. "2024-01-01" appears only because of the synthetic date_range.
- VERDICT: NO. No kline is read (probe :61-110). purge_gap comes from config.
- Freeze: `venv/bin/python handoffs/20260907-probe-split-baseline.py --write`. Runtime: n/a (not needed).

## 4. evtlabel (survivor_global.json, survivor_event_return_rule.json; README.md is a placeholder)

- Consumers: no pytest. `scripts/freeze_evtlabel_survivor_golden.py` (compare mode) and `scripts/evtlabel_phase_gate.sh:43,81-82` (file count only).
- Cells: SYNTHETIC. `_build` (freeze script :45-56) uses `tests/momentum/Analysis/test_survivor_contract.py` `_build_kwargs`/`_o2`, which generates rng `default_rng(20260803)` with n=5000 (:210-219). Events are synthetic `1704067200000 + i*43200000` (:597-598).
- Identity pins: sha256 and size of the canonical survivor payload only.
- VERDICT: NO (no kline or feature read).
- Freeze: `venv/bin/python scripts/freeze_evtlabel_survivor_golden.py --write`. Runtime: n/a.

## 5. evtwarmup/baseline.json

- Consumer: `tests/api/test_evtwarmup.py:267-284` `test_global_run_unchanged_vs_golden`. It compares ONLY `global_run`; the `event_run` and `facts` sections are not asserted. The `scripts/evtwarmup_phase_gate.sh:23-24` file count is the only other consumer.
- Cell: `run_analyze(None)` on the la0 ETHUSDT 12h static fixture (1696 rows, 2024-01-01..2026-04-27). Labels come from 12h kline close. The split is applied (golden shows `applied: true`, train 1356 / test 335, `index_kind: positional` over FEATURE rows).
- Identity pins:
  - `train_time_bounds[0] = "2024-01-01 00:00:00"` and the row counts come from the static FEATURE fixture index, not the kline.
  - The `event_run` section is the full-sample fallback path (subject to M2 latent), but it is not asserted and its pinned fields do not include grouped_ic.
- VERDICT: NO. Features are static. Labels are forward returns reindexed by timestamp (M2). The masked stage4 slices by timestamp. period_alignment is not emitted, because head trim stays 0.
- Freeze: `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py --write` (probe :1-8,24). Runtime: UNKNOWN (not needed).

## 6. splitunify

a) `splitunify_golden.json` (+ `.v8.json`/`.v8.sha256`)
- Consumer: `tests/momentum/Analysis/test_splitunify_golden.py`.
- Freeze: `scripts/freeze_splitunify_golden.py`. The fixture is SYNTHETIC: `BASE=1_700_000_000_000`, `N_BARS=200`, 1h ints (:52-62, comment "不依賴 data_cache").
- VERDICT: NO.

b) `clusters_oracle.json`
- Consumer: `tests/momentum/Analysis/test_splitunify_derive.py:619-658`. Values are hand-derived synthetic `decision_at_ms` 1700000000000.
- VERDICT: NO.

c) `report_int_keys.json`
- Consumer: `tests/api/test_splitunify_disclosure.py:173-219`, which runs `scripts/freeze_splitunify_report_keys.py` as a subprocess.
- Cells: 3 `run_analyze` runs on the la0 12h fixture (event, degraded with `min_test_events=10000`, global) (:71-96). It pins only the SET of integer-leaf key paths.
- The event and degraded runs keep the holdout (fit_mode train_mask per `test_evtwarmup.py:135-150`), and the global run has a split. stage4 for the event runs works on ~80 event rows, which already go through the reindex branch.
- VERDICT: NO. No new or removed int keys; period_alignment is not emitted.
- Freeze: `venv/bin/python scripts/freeze_splitunify_report_keys.py --write`.

d) `ic_event_report_baseline.{pre_task_10_2,post_task_10_2,prod_task_10_4}.json`
- Consumer: ONLY the manual `scripts/splitunify_ic_event_report_diff.py --mode strict`. No pytest.
- Cells: batch `20260909T130533Z-7f73e4c7` (ETHUSDT 12h events, t0 range 1735776000000..1772020800000 = 2025-01-02..2026-02-25), ff_run `4a8a0b37…`, `ff_run_timeframe` 1h. The conditional IC uses `12h_L1_momentum_BOP`/`RSI` plus 1h L1 (script :55-58). Meta is in each file's `.meta`.
- Pre-existing status: the FF run `4a8a0b37…` is ABSENT from data_cache/features. Only `.locks/*_1h_4a8a0b37….lock` exist (find returned nothing else), so strict mode cannot run today, independent of this change.
- VERDICT: CONDITIONAL.
  - Kline-side event alignment and labels are timestamp-based, with events all in 2025+, so they are unaffected.
  - The 12h-derived feature values (RSI is recursive) would change only if that FF run is REGENERATED after the prepend.
  - pre/post files are declared frozen historical comparisons and are "不再重新捕獲" (script :20-27).
- Runtime: UNKNOWN.

e) `r5_parity.json`
- Consumer: ONLY `scripts/splitunify_r5_parity.py` (manual). It is listed in `tests/_golden/preprov/reader_inventory.json`, but that is inventory, not a value check.
- Cells: batches `20260906T105851Z-8cc44eea` (t0 2025-02-03..2026-05-27) and `20260909T130533Z-7f73e4c7`, x ff_run `5ea07439…` (1h), trigger TF 12h (:57-92).
- Pre-existing status: FF run `5ea07439…` is ABSENT from data_cache/features, so the script exits rc=2 (data missing) today.
- VERDICT: CONDITIONAL. Values: the split boundary comes from the FF-run 1h index, event alignment is by timestamp in 2025+, and `dropped_in_alignment=12` comes from events AFTER the kline end, not before the start. They change only if the FF run is regenerated and its post-trim index moves. The script's own note at :54-56 says feature columns do not affect the compared values.
- Freeze: `venv/bin/python scripts/splitunify_r5_parity.py --update`. Runtime: UNKNOWN.

## 7. tfwindow

- `rolling_keys_1h.json`
  - Consumer: `tests/api/test_tfwindow.py:76-104,125-140` (`GOLDEN_1H` :25, `H5_1H` :26).
  - Cell: `run_analyze(None, h5_glob="BTCUSDT_1h_*_a0_tail2000.h5")`. It is a static 1h feature fixture, although it contains 12h-derived columns (`close_12h_*`) that are frozen in the h5. Labels come from the BTCUSDT **1h** kline (meta timeframe 1h), which is untouched.
  - The run is a full-sample fallback (no mask), so raw is the full 1h kline (20352 rows), already different from 2000 rows, so it is the reindex path both before and after.
  - VERDICT: NO.
- `gap2_pre_disclosure.sha`
  - Consumer: only `handoffs/20260909-probe-tfwindow-refreeze.py:25-44`. It is an immutable historical digest of the la0-12h run report minus `ic_window_disclosure`.
  - The masked path is unaffected and period_alignment is not emitted.
  - VERDICT: NO. Caveat: it is a whole-report canonical sha, so any M2-latent effect would show up only in no-split runs, and this run has a split.
- Freeze: `handoffs/20260909-probe-tfwindow-refreeze.py --write-1h`. Runtime: n/a.

## 8. icresult_paging (fixture_report.json, full_report_projection.json, shape_fixture.json)

- Consumer: `tests/api/test_icresult_paging.py:19,48-53,80-…,403`. The tests load the STATIC `fixture_report.json` and recompute projections from it. No `run_analyze` call (grep confirms none in the test).
- Freeze: `handoffs/20260909-probe-icresult-golden.py --write` re-runs `run_analyze(None)` on la0 12h (:218-225). That run is split-applied (`metadata.ic_train_test_split.applied: true` in the fixture). `shape_fixture` is a hand transcription (`_source`).
- Identity-like fields: `metadata.baseline_subset.tail_bars_actual: 1696` and `index_start "2024-01-01 00:00:00"` are copied from the STATIC la0 fixture meta, not read from the kline.
- VERDICT: NO. The tests are data-independent, and even a re-freeze would take the masked path and reproduce the same values.
- Runtime: n/a.

## 1h/4h-only cells (confirmed unaffected)

- gap3_label 1h x 3: 1h digest; the trigger-TF-only alignment is at label_value_from_case.py:1068-1077.
- tfwindow rolling_keys_1h: meta timeframe 1h, so the 1h kline is read.
- evtalign: synthetic 1h.
- splitunify golden and clusters: synthetic 1h.

## Not in my families but relevant (for the lead)

- If the la0 fixtures (`tests/golden/la0/inputs/*`, config e53e2290 for 12h, 4a8a0b37 for 1h with 12h training TF) were regenerated after the prepend, many of the "NO" verdicts above (evtwarmup, report_int_keys, icresult_paging re-freeze, gap2) would need re-evaluation. Today they are static h5 files.
- M2 latent: no-split 12h runs whose len(features)==len(kline) today lose grouped_ic after the prepend. That is a code defect exposure, not a golden in this family.

## Appendix E (fam_E.md)
# fam_E — golden impact audit: 12h kline history extension (READ-ONLY)

Scope: (a) l65, l65_hardening, la0, la1, la2, ic_phase1_1a_cut1, ic_phase1_contract, fixtures/golden/multi_symbol_c3, fixtures/ic_phase0, fixtures/ic_run_selector_baseline.json; (b) non-golden real-kline tests that read 12h.
Method: code/JSON reading only (no pytest, no h5 reads). "RED" = predicted from code, not executed.

## Key mechanism facts (IC path; used by la0/la1/la2/ichc)
- la0/la1/la2 ETH 12h runs do NOT run Feature Factory: features come from a frozen h5 (`tests/golden/la{0,1,2}/inputs/ETHUSDT_12h_e53e2290…_strat_p2r12_a0_tail2000.h5`, identical sha 55e27b4b… in all three dirs; meta: 1696 rows, index 2024-01-01 00:00 → 2026-04-27 12:00, `cut_method=timestamp_tail_sort_index`). The kline is read live only for labels and for regime/phase side computations.
- Labels: `ic_filter_orchestrator.py:3598-3626` reads full 12h kline, `_coterminalize_close` (tail-trim), `generate_returns_by_type(close, 5, "simple")` (point-wise forward return), then `reindex(feature_index)`. → label values at 2024-01-01..2026-04-27 are unchanged by prepending history (given byte-identical overlap rows).
- `_intersect_features_with_kline_period` (`:440-497`) only writes `metadata.period_alignment` when head/tail trimmed (`:1348-1352`); prepending history causes no head trim → no new key.
- Stage4 raw slicing (`:4300-4306`, `_slice_raw_data_by_mask` `:1132-1159`): split ON → positional branch today (1696==1696, index equality asserted) / reindex branch after → same values. split OFF (mask None) → raw kline (RangeIndex) passed unsliced; `ICEngine._align_with_raw_data` (`ic_engine.py:1475-1497`) today goes positional because len(raw)==len(features)==1696 ONLY for ETH 12h; after extension it does `raw_data.reindex(features datetime index)` on a RangeIndex frame → all-NaN close → `grouped_ic.by_regime` (`ic_engine.py:1282-1291`) changes (to empty/NaN), by_year unchanged. This is a latent mismatch already present for every non-12h run (BTC 1h tail2000 ≠ 20352). Affects any golden that captures `grouped_ic` from an ETH-12h split-OFF analyze (la0 split_off baselines do NOT capture grouped_ic/ic_decay — keys checked; ICHC/GAP-2 goldens are outside my family — flag to their owner).
- Event filter query mode (`:3841-3856`) applies the query to the FULL raw kline; `n_events`/tier (`event_filter.py` ~:144-155) count events before 2024 too → changes for query-mode runs on la0 ETH input (ichc runner) — outside my family; flag.

## (a) Golden families

### 1. tests/golden/la0 (ETHUSDT_12h_baseline.json, _after.json, _after_split_off.json; BTCUSDT_1h_*)
1. Consumers: tests/momentum/test_la0_lookahead.py:37-41,707-711,901-955 (live re-analyze vs after goldens: `test_after_golden_deep_equal`, `test_after_golden_split_off_deep_equal`); tests/momentum/Analysis/test_ic_1a_cut1_golden.py:45-47,96-140,170-215 (live compare; both live tests `xfail(strict=True)` `_LA0_REBASELINE_PENDING` :155-158 for a17b57e7 window change); tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py:18-30 (BTC only); inputs also consumed by tests/momentum/helpers/ichc_run.py:16-17 and tests/momentum/test_ic_golden_inputs_names_opaque.py:71 (GAP-2 golden, not my family).
2. Cells: RUNS gen_baseline.py:79-92 — BTCUSDT/1h cfg 4a8a0b37; ETHUSDT/12h cfg e53e2290; TAIL_BARS=2000 (:57) timestamp tail cut (:374-387) → ETH 12h actual 1696 rows (whole history). IC config: spearman, horizon 5 simple, rolling [21,63,126], split on (after_split_off: split off), winsor on (`config_snapshot`). No FF, no stationarity (features frozen).
3. Identity pins: none kline-derived. `input_contract` has features_h5_sha256/meta_sha256, index_start "2024-01-01 00:00:00", tail_bars_actual 1696 — all FEATURE-derived (frozen h5), not kline. No kline sha/rows.
4. VERDICT: **NO** (ETH 12h values). Metrics captured (rolling_ic, icir, monotonicity, turnover, stage1 winsor, pearson control) depend only on frozen features + forward simple returns at feature timestamps. BTC 1h cells: NO (1h untouched).
5. Freeze: `python tests/golden/la0/gen_baseline.py` (before) and `tests/golden/la0/build_after_and_attribution.py` (after/attribution). Requires feature registry e53e2290 (FRAMEPATH residual: pinned data missing). Not needed for this change.
6. Runtime: ETH 12h after analyze wall 6.6 s (`ETHUSDT_12h_baseline_after.json` after_perf_telemetry.wall_seconds=6.607); full freeze unknown.
- Side note: test_la0_lookahead.py:155-168 fixture `la0_real_kline` calls `requires_kline_data("ETHUSDT","12h",min_rows=200)` (manifest verify on) → all 8 tests using it (incl. BTC-only ones :184,205,323,384,423,544,637) FAIL on DATA_MANIFEST sha mismatch until regenerated. ETH is used positionally (`_build_rolling_ic_inputs` `.iloc[:n_rows]` :91) only in `test_cross_symbol_isolation` (:635-700) which is self-consistent → green after manifest fix.

### 2. tests/golden/la1 (ETHUSDT_12h_baseline.json + 3 control full-tree artifacts ETHUSDT_12h_control_{regime_off,ls_off,non_trigger_fallback}_full.json; attribution_allowlist.json)
1. Consumers: tests/golden/la1/test_b4_golden_rebaseline.py:520-627 (3 parametrized control deep-equal, ETH id), :930-1023 (`test_b4_cross_symbol_eth_independent`), :454-466; tests/golden/la1/test_attribution_validator.py:45 (static); tests/momentum/test_la1_lookahead.py:62 (ETH static only; live = BTC 1h); tests/api/test_ic_la1_degraded_gate.py:690,794 (BTC 1h inputs).
2. Cells: RUNS shared with la0 (same frozen ETH 12h features, la1 inputs = copy, sha 55e27b4b); `run_one` gen_baseline.py:1824-1880: regime rule/kmeans via analyze (close reindexed to features → unaffected) PLUS `_legacy_regime_masks(close)` on FULL kline close (:1834-1855; EMA55 + rolling(55) std + full-period percentiles, :493-) and `detect_phases_for_index(close, volume)` on FULL close (:1870-1872). Controls `run_control_one` :1376-1396 masks from full close.
3. Identity pins: `input_contract.kline_rows: 1696`, `kline_sha16: "00d1ee985ad3f09f"` in ETHUSDT_12h_baseline.json:176-177 and all 3 control files (:14-16); `EXPECTED_KLINE` literal gen_baseline.py:76-85 (rows 1696, sha16 00d1ee98…); test literal `expected_rows=1696` test_b4_golden_rebaseline.py:524 (asserted :536 `len(raw)==expected_rows`); `assert baseline["input_contract"]["kline_rows"] == 1696` :944; mask_membership `len` fields = 1696.
4. VERDICT: **YES** — regime_rule.mask_membership (bull/bear/high/low: len, membership_sha256, true_count), xgboost_phases (len, labels, timestamps), mask_membership_control in all 3 controls, and input_contract kline_rows/sha16 all change; summary_table/report IC values unchanged. Tests going RED: `test_b4_control_regime_off_deep_equal[ETHUSDT/12h]` (len literal + deep-equal), `test_b4_control_ls_off_deep_equal[ETHUSDT/12h]`, `test_b4_control_non_trigger_fallback_deep_equal[ETHUSDT/12h]` (full-tree deep-equal incl. input_contract + mask_membership_control; also bull/bear vs B0), `test_b4_cross_symbol_eth_independent` (bull/bear vs B0 :951-956; five-path xgboost/kmeans diffs vs ETH-scoped allowlist rows with exact old/new → UNEXPECTED). BTC 1h cells unaffected.
5. Freeze: `python tests/golden/la1/gen_baseline.py` (main) and `--controls-only` (control artifacts; hint at test_b4_golden_rebaseline.py:488); `--check` path verifies kline sha (:2078-2120). Test edits needed: EXPECTED_KLINE literal (gen_baseline.py:82-83), test literal 1696 (test_b4_golden_rebaseline.py:524, :944), ETH-scoped rows of attribution_allowlist.json (69 lines mention ETHUSDT/12h) + `FROZEN_ALLOWLIST_ROWS_SHA256` (test_attribution_validator.py:717), control_volatile_receipt.json (content sha).
6. Runtime: per ETH control analyze 13.2–13.3 s (control_volatile_receipt.json discover_matrix); BTC 16.5–16.7 s; la1 gate pytest 32.38 s for 2 tests (handoffs/run_receipts/icresult_la1_fix.log:56). Full gen_baseline wall unknown; regime/phase on ~3x more 12h bars → modestly longer (unknown).

### 3. tests/golden/la2 (ETHUSDT_12h_baseline.json; inputs/*_config.json)
1. Consumers: tests/golden/la2/test_attribution_validator.py:375-430,473-500 (reads frozen JSON; compares to `EXPECTED_FACE_VALUE_HASHES` literals in gen_baseline.py); tests/momentum/test_la2_lookahead.py:1292-1298,1483-1490 (static JSON reads), :1009 imports `_pattern_early_flip_manifest` (pure fn). No pytest re-runs the kline-dependent faces live.
2. Cells: gen_baseline.py `run_one` :1204-1340: features frozen (same h5); `close_feat = close.reindex(features.index)` for model/pattern/factor (unaffected); **regime_fit_global and control.regime_pit use FULL kline close** `_run_regime_face(close, volume)` :1312-1326 (RegimeDetector kmeans lookback 55, PIT refits) → len/labels/timestamps change.
3. Identity pins: `kline_rows: 1696`, `kline_sha16: 00d1ee985ad3f09f` (ETHUSDT_12h_baseline.json:172-173); EXPECTED_KLINE literal gen_baseline.py:78-86; regime face `len`, `timestamps` (start 2024-01-01).
4. VERDICT: **YES** for regime_fit_global / control.regime_pit (+ input_contract); model/pattern/factor/early_flip NO. Pytest stays GREEN (static), but `python tests/golden/la2/gen_baseline.py --check` fails (kline sha16/rows :1568-1578 and regen diff).
5. Freeze: `python tests/golden/la2/gen_baseline.py` (+ `--check`). Edits: EXPECTED_KLINE (:84-85), EXPECTED_FACE_VALUE_HASHES regime face entries, possibly B0_LEGACY diff rows in attribution_allowlist.json + FROZEN_ALLOWLIST_ROWS_SHA256 (attribution_validator.py:388) if regime face hashes are in allowlist rows.
6. Runtime: unknown.

### 4. tests/golden/l65 (tier1_structure, tier2_reduced, fast_adf_gate_report.json)
- tier1_structure/column_inventory.json, schema_hash.txt: built by `scripts/build_l65_golden.py --tier 1` (`build_tier1_structure`), no kline read, no "12h" token (grep count 0). Consumer tests/golden/l65/test_l65_golden.py:18-25 (builds to tmp_path). VERDICT **NO**.
- tier2_reduced/ETHUSDT_1h_2000rows.parquet, d_star_ETHUSDT_1h_2000rows.json, synthetic: `build_l65_golden.py --tier 2b --symbol ETHUSDT --tf 1h --max-rows 2000` (defaults :700-702), single TF `frame.tail(max_rows)` (:471-487). Consumers tests/golden/l65/test_l65_golden.py:90-94 (tmp_path), tests/feature_engineering/preprocessing/test_ff_causal_golden.py:20 (reads 1h only :150,229). VERDICT **NO** (1h only).
- fast_adf_gate_report.json: NOT a compared golden — it is OUTPUT rewritten in place by `test_fast_adf_1000_sample_gate` (tests/feature_engineering/preprocessing/test_fast_adf_gate.py:34,277-303). Cells SYMBOLS ETH/BTC/BNB/SOL × TIMEFRAMES ("1h","12h") (:26-27); `_load_gate_feature_frame` uses `raw_frame.tail(2000)` (:86-92). 12h currently has 1696 < 2000 rows so tail(2000)=whole series; after extension tail(2000) = last 2000 bars (≈2023-08 onward) → frame, global `rank(pct=True)` L3 features, window samples, downsampling all change. VERDICT **YES** (report content; current report generated 2026-06-08, metrics all 1.0). Assertions are threshold-based (agreement >0.99, d* diffs) → expected to stay green but UNKNOWN; the per-sample test (:305-325) also re-samples. Each run dirties this tracked file (already known). Freeze: n/a (test-generated). Runtime unknown.

### 5. tests/golden/l65_hardening (BTC/ETH/ADA × 1h/4h baselines, manifest.json)
- Confirmed 1h/4h only: scripts/build_l65_golden_baseline.py:44-45 `SYMBOLS=("BTCUSDT","ETHUSDT","ADAUSDT")`, `TIMEFRAMES=("1h","4h")`; manifest.json timeframes ["1h","4h"]; single-TF L1/L2 from that TF's OHLCV (:368-373 `raw_frame.tail(max_rows)`); no kline sha pin (only kline_path). Consumers: scripts/build_l65_golden_baseline.py --check; referenced by tests/feature_engineering/test_framepath_disposition.py, scripts/framepath_affected_gate.py. VERDICT **NO**.

### 6. tests/golden/ic_phase1_1a_cut1 and ic_phase1_contract
- Inputs: frozen features h5 `BTCUSDT_1h_a384e6d2…_top50.h5` (freeze_baseline.py:26-28 TIMEFRAME="1h"). "12h" tokens in JSONs are feature NAMES (e.g. `None_12h_tail_risk_…`) frozen in the h5 — not recomputed. Labels from BTC 1h kline. test_split_leakage_golden.py:24-26 reads `handle[symbol]["1h"]["data"][:40]` (1h). Consumers: tests/golden/ic_phase1_contract/test_baseline_frozen.py, test_split_leakage_golden.py, tests/momentum/Analysis/test_ic_1a_cut1_golden.py, test_ic_1a_freeze_reuse_guard.py, tests/api/test_ic_response_v2.py. VERDICT **NO** (would only change if someone re-materialized the a384e6d2 feature run from FF, which the freeze scripts do not do — they read the stored registry).

### 7. tests/fixtures/golden/multi_symbol_c3
- Directory is EMPTY and untracked (git ls-files empty). Retired by FRAMEPATH (tests/_golden/framepath/test_disposition.json:15058-15062: "腳本不被 pytest 收集；其 golden 零讀者"). VERDICT **N/A**.

### 8. tests/fixtures/ic_phase0 (baseline_decay.json, baseline_feature_filter.json, baseline_grouped_post_timeaxis.json, kline_seconds.csv) and tests/fixtures/ic_run_selector_baseline.json
- No `12h`/kline_cache dependency found by this audit's candidate grep (files not in the 97-file kline∧12h list; ic_phase0 ships its own kline_seconds.csv). VERDICT **NO** (not exhaustively traced; low risk).

## (b) Non-golden real-kline 12h tests

Global: every `requires_kline_data(..., "12h")` (verify_manifest default True, tests/conftest.py:97-106 → data_manifest.py:233-237 sha256 compare) FAILS until tests/fixtures/DATA_MANIFEST.json 12h entries (min_row_count 1696 + sha256 per symbol) are regenerated. No generator script found (tests/fixtures/data_manifest.py has only load/verify functions).

| test | read | values change? | outcome after manifest regen |
|---|---|---|---|
| tests/test_feature_factory_e2e.py:118,145,161,215,234 | FF `generate_features` BTC 12h, start_date None (full history) | YES (rows ~1696→~4.6–5.3k) | property asserts only (count>0, rows>100, no inf) → green; runtime ~3x; small risk of inf from older bars (UNKNOWN) |
| tests/test_feature_factory_e2e.py:177-178 (`test_no_future_leak_alignment_check`) | full 12h + full 1h, independent oracle | YES (pre-2024 rows map to -1) | oracle recomputed from same arrays → green |
| tests/momentum/test_la0_lookahead.py:164 | ETH 12h `.iloc[:400]` (cross_symbol only) | YES | self-consistent → green |
| tests/feature_engineering/test_ff_wrapper_path_correctness.py:35 | `.tail(rows≤180)` | NO | green |
| tests/feature_engineering/atomic/test_prepare_inputs_equivalence.py:42 | full series, wrapper vs semantics | YES | self-consistent → green |
| tests/feature_engineering/atomic/test_atomic_differential.py:41 | full series, wrapper vs talib | YES | self-consistent → green |
| tests/feature_engineering/atomic/test_correctness_mode.py:70 | full series, raises-probes | YES | green |
| tests/feature_engineering/atomic/test_handcoded_reference.py:50 | full series; corr thresholds (:197-200 <0.99; :230-235 >0.99, < -0.5); rewrites tracked tests/_golden/ff_deepaudit/handcoded_{v0_v1,variant}_diff.json (n, max_abs_diff, corr) | YES | threshold-based → likely green (UNKNOWN); tracked JSONs dirtied with new values |
| tests/feature_engineering/atomic/test_bug1_beta_correl.py:22 | full series; rewrites tests/_golden/ff_deepaudit/beta_correl_v0_v1_diff.json | YES | oracle equality + `>0.01` → green; JSON dirtied |
| tests/feature_engineering/test_ff_cross_symbol_value_isolation.py (BASELINE_TIMEFRAME="12h" from ff_artifact_compare_helpers.py:26) fast tests :131,224,322,385 | `kline_window_dates` = last 14/7 days (tail) | NO/negligible | order-permutation self-consistency → green |
| same file slow test :456-462 | `iloc[SLOW_PRE_HISTORY_BARS=1034]` positional start; `assert len(BTC12h)==len(ETH12h)` | YES (start moves ~2025-06 → ~2021) | self-consistent; RED only if BTC/ETH 12h prepended to different starts (CONDITIONAL); run range grows from ~662 to ~3.5k+ bars → much slower; partial reasons limited to two allowed codes (status may become complete — allowed) |
| tests/test_kline_data_service.py:76 | TF="1h" (:29) | NO | green |
| **tests/feature_engineering/preprocessing/test_l65_native_tf_real_eth.py:92** (`_load_eth_close("12h", max_rows=0)` = full 12h; primary = first 2400 1h rows) | native 12h grid now starts 2019; idx_map for 2024 rows ≈3000 → native warmup already satisfied | YES | **likely RED**: native warmup prefix assert `native_floor(564) <= native_prefix` (:283-296, measured 588) should collapse toward 0; leading -1 gap in idx_map disappears; docstring pins 1696 (:5) |
| **tests/momentum/event_samples/test_tables.py** :42-57, :60-68 | events at BASE(2024-01-01)+n·12h, oracle `b.iloc[n]` (positional); `last = 1695` | YES | **RED**: hand-example oracle reads 2019-era bar n; `last-3` horizon-omission (`n==3`) no longer happens |
| **tests/momentum/event_samples/test_return_table_by_label.py** :191-222, :225-244 | `tail = 1692` ("共 1696 根"), omission asserts `g["negative"]["7"]["n"]==1`; `G2_GOLDEN_SHA256` (:244) | YES | **RED** (omission asserts; G-2 sha golden) |
| **tests/momentum/event_samples/test_pipeline.py:53-62** | events BASE+[300..940]·12h, `seg = iloc[:1200]` | YES | **RED**: segment no longer contains the 2024 events → `signal_frequency == 6/1198` fails |
| **tests/momentum/event_samples/test_alignment.py:134-137** | event at BASE with decision_offset 1 expects `warmup_insufficient_12h` | YES | **likely RED** (12h now has a prior bar; failure reason shifts to 1h/4h or event succeeds); file docstring :3-5 hard-assumes first bar = 2024-01-01 |
| other event_samples/api files with BASE-anchored events on real ETH 12h (test_counterexample_classifier (timestamp lookup → OK), test_candidate_ledger, test_gap3_* (split_blocked, horizon_curve, two_stage_path, analysis_label_producer, conditional_ic, attached_columns_contract), test_feature_materialization, test_splitunify_wiring, test_mutation_guard (seg iloc[1000:1100] random scores → invariant), test_metrics_glossary / test_all_bars_eval / test_generator_adapters / test_state_counters (positional segments iloc[1000:1100]/[800:1200]/[500:1100]: values change, mostly self-consistent), tests/api/test_gap3_event_analysis_horizon_purge.py, test_cross_timeframe_event_analysis.py, test_period_auto_align.py, test_gap3_feature_coverage_gate.py) | mixed | YES where positional | UNKNOWN per test — systematic assumption "bar index n ↔ 2024-01-01+n·12h"; needs per-test pass. gap3_random_control / gap3_label goldens belong to other families |
| tests/momentum/Analysis/test_evtlabel_e2e_realkline.py:52 | full ETH 12h, planted feature | YES | structural asserts → green |
| tests/fixtures/tmp_feature_runs_plugin.py:41-51 (btc/eth/bch_12h_a/b, window 2024-12-01→2026-04-28; RSI14, BOP, rolling 5/13; L6.5 winsor only) | 670 12h bars before start | CONDITIONAL (only if estimate_max_warmup_bars D0 > 670 → warmup was truncated) | consumers (tests/api/test_ic_analysis_service.py:204, tests/momentum/test_ic_cross_sectional_cut2.py:237) use kline-derived oracles → green |
| tests/feature_engineering/test_b6_warmup_trim.py:78,125,311 | `_date_window` tail 120 days; near-start test uses `ts.min()` | start test start moves to 2019 | relative → green (UNKNOWN for multi-TF variant) |
| tests/api/test_batch_date.py:78 | availability check only | NO | green |

Out-of-family files that read 12h and look golden-ish (not analysed here; for other agents): test_failopen_{contract,correctness,layers,matrix}.py, test_ffstat_{calibration,stable_start (`_close("12h")[:1696]` :1132),warmup_table}.py, test_numview_{acceptance,criteria}.py, test_mtf_align_golden.py, test_framepath_invariance.py, test_ratiounsafe_registry.py, test_ff_multitf_truncation_{mr,small_mr}.py, test_batch1_followup.py, preprov_helpers.py, icfirstalign_helpers.py, tests/golden/gap3_random_control, tests/golden/gap3_label, ICHC/GAP-2 goldens via tests/momentum/helpers/ichc_run.py.
Full candidate list (97 files: kline reader ∧ "12h"): famE_candidates.txt in this scratch dir.
