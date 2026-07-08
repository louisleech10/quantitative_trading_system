# IC1A ALIGN SPEC/TODO v2 R2 close verification — Codex

TASK_ID: ic1a-align-specadv-r2
MODE: read-only close verification; production code/tests unchanged.
R1_INPUT: handoffs/IC1A-ALIGN-SPECADV-codex.md
SPEC: docs/IC_PHASE1_1A_ALIGN_SPEC.md v2
TODO: docs/IC_PHASE1_1A_ALIGN_TODO.md v2

## Receipts Re-run
- Read required context: HANDOFF.md, CLAUDE.md, handoffs/IC1A-ALIGN-SPECADV-R2-PROMPT.md, handoffs/IC1A-ALIGN-SPECADV-codex.md, SPEC v2, TODO v2.
- Re-ran R1 kline gap script read-only: data_cache/kline_cache.h5 ETHUSDT/1h n=322, infer_freq=None, median=3600s, max=44179200s, gaps=1; data_cache/feature_klines/kline_cache.h5 sampled 1h/4h/12h groups continuous.
- Re-ran event_filter minimal反例: DatetimeIndex features.loc[RangeIndex] raises KeyError; v2 timestamp-intersection adaptation keeps matching timestamps.
- Re-ran bar-ordinal反例: gappy close axis has missing calendar t+1h, but ordinal i+1 target exists; v2 forbids calendar lookup and selects positional target.
- Re-read HDF5 loader reality: _load_features_hdf5/_load_labels_hdf5 return int64 timestamp Index when timestamps exist; data_cache/features/BTCUSDT_1h_filtered.h5 timestamps are int64 seconds.

## R1 Findings Close Table

R1-ID: ADV-CODEX-1 / CLOSED
Basis: v2 SPEC §C expands consumer map to Stage2, Stage0, _slice_by_mask, _slice_raw_data_by_mask, _stage3_event_filter, ICEngine._align_label_to_group, analyze_cross_sectional:756, horizon resolver/purge_gap. IC-first raw and ML label-column consumers are explicitly moved to §N as separate epics, so the task no longer falsely claims full-platform coverage. TODO Tasks 2.1-2.6 map to the formerly missing consumers.

R1-ID: ADV-CODEX-2 / CLOSED
Basis: v2 D-2 defines oracle semantics as bar-ordinal, "第 i 列 vs 第 i+lag 列", aligned with shift(-h), and explicitly bans t+lag*freq calendar lookup. Re-run gappy-axis receipt confirms this closes the missing-bar ambiguity.

R1-ID: ADV-CODEX-3 / CLOSED
Basis: v2 D-3 defines two-stage cadence/gap policy: non-gap adjacent deltas must match spec.freq within tolerance, gaps >1.5x cadence are allowed but reported as gap_count/gap_rate, and split _validate_expected_frequency remains a separate strict responsibility. Re-run ETHUSDT/1h gap receipt matches the covered case.

R1-ID: ADV-CODEX-4 / CLOSED
Basis: v2 D-1 accepts DatetimeIndex or monotonic unique int64 epoch seconds and converts inside the gate; milliseconds/mixed units/non-monotonic/duplicates raise; double RangeIndex raises. TODO keeps loader schema unchanged, requires materialize->_load_features_hdf5 true-path Golden coverage, and records RangeIndex fixture migration duties. Re-read HDF5 receipt confirms this addresses existing int64-second paths.

R1-ID: ADV-CODEX-5 / CLOSED
Basis: v2 SPEC §G and TODO §0 require Golden harness to treat data_cache as read-only, redirect ingest/report output to pytest tmp via monkeypatch/config, and require postflight data_cache snapshot zero change. This directly closes the ic_ingest_cache write-contamination issue.

R1-ID: ADV-CODEX-6 / CLOSED
Basis: v2 SPEC §V M5 is now an explicit two-leg mutation procedure: leg A gate ON + M1 data must pass by catching AlignmentViolationError; leg B monkeypatch validate_alignment to no-op with the same data must make the same test fail. M6 is separately defined as gate ON vs no-op output sha256 equality on correct data.

R1-ID: ADV-CODEX-7 / CLOSED
Basis: v2 Task 1.2 creates a shared label horizon resolver, aligns return_(n) parsing with the existing cross-sectional resolver, requires unit-bearing label_return_{n}d to be converted to bar count or raise, and makes purge_gap and gate spec.lag share the resolver. External labels without resolvable horizon metadata/name fail closed.

R1-ID: ADV-CODEX-8 / CLOSED
Basis: v2 §N defers Phase 3 cut2 oracle convergence and says a later epic must preserve direct-vs-reindexed probes plus drift tests. The current 1-align scope no longer expands validate_alignment into cross-sectional value-oracle semantics.

R1-ID: ADV-CODEX-9 / CLOSED
Basis: SPEC source line now names the actual Claude receipt handoffs/IC1A-REMAINING-CUTS-ORDER-claude.md plus the Codex and Composer receipts.

## New v2 Decisions Check

R2-D-1 int64 compatibility / CLOSED
Basis: current loaders do return int64 timestamp indexes, and v2 accepts only epoch seconds with monotonic/unique checks while raising milliseconds/mixed/invalid axes. No new blocking hole found.

R2-D-2 bar-ordinal / CLOSED
Basis: label_generator.generate_log_return uses close.shift(-horizon), and the gappy-axis receipt shows ordinal semantics are the only unambiguous match. No new blocking hole found.

R2-D-3 two-stage freq/gap / CLOSED
Basis: v2 separates cadence validation from continuity and records gap metadata. This prevents both false calendar lookup failure and median-only silent acceptance. No new blocking hole found.

R2-Task1.2 horizon resolver / CLOSED
Basis: v2 requires resolver use for purge_gap and gate lag and fail-closed handling for ambiguous external labels. No new blocking hole found.

R2-Task2.4 event_filter adaptation / CLOSED
Basis: minimal反例 reproduces current RangeIndex-vs-DatetimeIndex KeyError, and v2 requires kline int64-to-datetime conversion plus timestamp intersection and empty-intersection raise. No new blocking hole found.

R2-M5 dual leg / CLOSED
Basis: v2 requires both command receipts and defines the no-op leg as expected test failure, removing the cheap-green normal pytest ambiguity. No new blocking hole found.

Implementation note / NEW-ISSUE NON-BLOCKING
Basis: Task 1.1 mentions tail NaN==lag. Implementer should apply this against the full target/close axis or an explicitly documented aligned target axis, not blindly against a truncated feature subset, or valid filtered subsets could be mis-killed. SPEC/TODO already have enough close-axis and coverage language to implement this correctly, so this is not a blocking spec hole.

## Verdict

VERDICT: APPROVE
RECONCILE-STAMP APPROVED Codex 2026-07-08

ASSUMPTIONS_VERIFIED: R1 findings re-read; SPEC/TODO v2 resolution table traced to tasks; R1 kline gap, bar-ordinal, HDF5 index, and event_filter axis反例 re-run read-only.
TESTS_RUN: no pytest; review-only close verification. Commands: sed/nl/rg static reads; read-only Python scripts over data_cache/kline_cache.h5, data_cache/feature_klines/kline_cache.h5, data_cache/features/*.h5; minimal pandas event_filter and bar-ordinal snippets. All receipts support APPROVE.
FAILURES_SEEN: current event_filter minimal反例 raises KeyError as expected before v2 adaptation; no task execution failures.
SCOPE_CHANGES: none; wrote only handoffs/IC1A-ALIGN-SPECADV-R2-codex.md.
NUMERIC_OR_SCHEMA_IMPACT: none from this review; approved spec would change validation behavior fail-closed without changing loader schema.
STATUS: DONE
