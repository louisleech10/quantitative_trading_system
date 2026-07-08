# IC1A ALIGN SPEC/TODO adversarial review — Codex

TASK_ID: ic1a-align-specadv
MODE: read-only adversarial review; production code/tests unchanged.

## Scope receipts
- Read: `HANDOFF.md`, `CLAUDE.md`, `handoffs/IC1A-ALIGN-SPECADV-PROMPT.md`, `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`, `docs/IC_PHASE1_1A_ALIGN_SPEC.md`, `docs/IC_PHASE1_1A_ALIGN_TODO.md`.
- Read background receipts: `handoffs/IC1A-REMAINING-CUTS-ORDER-claude.md`, `handoffs/IC1A-CUTS-ORDER-codex.md`, `handoffs/IC1A-CUTS-ORDER-composer.md`. Note: SPEC line 3 names `handoffs/IC1A-CUTS-ORDER-claude.md`, but actual file is `handoffs/IC1A-REMAINING-CUTS-ORDER-claude.md`.
- VERIFY commands run: focused `rg` over IC/ML label consumers; `nl -ba` on `ic_filter_orchestrator.py`, `ic_engine.py`, `ic_analysis_service.py`, `cross_symbol_training_service.py`, `feature_library.py`, `feature_factory.py`, `feature_storage.py`, `contracts.py`; read-only Python scripts against `data_cache/features/registry.json` and kline HDF5 timestamp arrays.

## Findings

ID: ADV-CODEX-1 / BLOCKING / consumer-map incomplete
Receipt: SPEC §C lists 5 consumers at `docs/IC_PHASE1_1A_ALIGN_SPEC.md:27-32`. Actual extra consumers include `_stage3_event_filter`, which returns `features_df.loc[idx], label_series.loc[idx]` using `filtered_df.index` from either features or raw kline base (`momentum/Analysis/ic_filter_orchestrator.py:1671-1704`); IC-first raw path passes labels into `FeatureFactory.run_ic_first` then `ic_engine.compute_ic_from_l7_raw` (`momentum/FeatureEngineering/feature_factory.py:2158-2214`); `ICEngine._align_label_to_group` silently positional-aligns when lengths match but indexes differ (`momentum/Analysis/ic_engine.py:594-602`); ML training consumes label columns directly (`api/services/cross_symbol_training_service.py:51-73`, `api/services/xgboost_task_service.py:195-200` from rg output).
Impact: first-cut incident pattern repeats: gate can pass the orchestrator path while IC-first/ML or event-filtered paths still silently consume misaligned labels.
RECHECK: `rg -n "label_series\\.reindex|labels_df\\.reindex|_align_label_to_group|label_column|train_model\\(|_stage3_event_filter|compute_ic_from_l7_raw" momentum api -g '*.py'`.
Suggested fix: expand SPEC §C/TODO with a complete consumer map. Either wire `validate_alignment` into IC-first and ML label-column consumers, or explicitly move them to §N with a blocking rationale and red-on-break coverage proving they cannot be reached by this task.

ID: ADV-CODEX-2 / BLOCKING / Tier-2 oracle chooses wall-clock offset without deciding bar-ordinal semantics
Receipt: TODO says `expected=log(close[t+lag_offset]/close[t])` where `lag_offset=spec.lag×to_offset(spec.freq)` (`docs/IC_PHASE1_1A_ALIGN_TODO.md:31`). SPEC goal is `Target_{t+lag}` and prompt asks whether this means the next lag-th K bar or the timestamp `t + lag*freq`. Real cache check: `data_cache/kline_cache.h5` `ETHUSDT/1h` has `pd.infer_freq=None`, median diff 3600s, max diff 44179200s, one gap >1.5 median; `data_cache/feature_klines/kline_cache.h5` sampled groups are continuous.
Impact: with missing bars, `t + lag*freq` may be absent while the next valid bar exists. The current TODO would either false-raise or compare to the wrong semantic target depending on reindex behavior.
RECHECK: read-only script over `data_cache/*kline_cache.h5` extracting structured `data["timestamp"]`, then compare `pd.infer_freq(pd.to_datetime(ts, unit="s"))` and `np.diff(ts)`.
Suggested fix: explicitly choose semantics. For trading bars, prefer ordinal next valid K bar on the verified kline axis, plus a separate timestamp-gap policy. If wall-clock semantics are intended, declare that missing expected timestamps are hard failures and document the quant consequence.

ID: ADV-CODEX-3 / BLOCKING / freq/gap policy is internally contradictory and can mis-kill real research data
Receipt: SPEC says fail-closed on `freq 不符 spec` (`docs/IC_PHASE1_1A_ALIGN_SPEC.md:43`) and Tier-1 checks freq via expected freq (`:49`), but also says NaN holes should be skipped and not mis-kill research gaps (`:51`). TODO uses "`pd.infer_freq` or adjacent-delta median" (`docs/IC_PHASE1_1A_ALIGN_TODO.md:30`) and says feature timestamps with kline holes can be legal (`:49`). On a real local cache, `ETHUSDT/1h` has one large gap and `infer_freq=None`; median remains 3600s.
Impact: implementers can pass a gappy series by median only, or reject it by infer_freq/fail-closed. Both are defensible from the current text, so the same data can pass/fail depending on agent interpretation.
RECHECK: same kline timestamp script as ADV-CODEX-2; inspect TODO lines 30 and 49.
Suggested fix: define a two-part policy: base cadence must equal spec on non-gap adjacent deltas, gaps above cadence are allowed only if coverage/oracle can still prove labels, and report gap count/rate with a threshold approved in SPEC.

ID: ADV-CODEX-4 / BLOCKING / Task 2.3 will block existing HDF5/RangeIndex paths without a migration or acceptance command
Receipt: `_load_features_hdf5` creates `pd.Index(timestamps[:], name="timestamp")`, not `DatetimeIndex`; missing timestamps fall back to `RangeIndex` (`momentum/Analysis/ic_filter_orchestrator.py:2469-2479`). `_load_labels_hdf5` likewise uses integer `pd.Index` (`:2508-2511`). TODO Task 2.3 says double RangeIndex/no comparable timestamp must raise and claims V2 load has true axis (`docs/IC_PHASE1_1A_ALIGN_TODO.md:62-69`), while flat existing files exist: `data_cache/features/BTCUSDT_1h_filtered.h5`, `data_cache/features/TESTUSDT_12h_filtered.h5`.
Impact: a currently usable HDF5 analyze path can become fail-closed even when timestamps are epoch seconds and recoverable. SPEC does not state whether this breakage is acceptable, nor how to migrate/convert.
RECHECK: `nl -ba momentum/Analysis/ic_filter_orchestrator.py | sed -n '2455,2511p'`; `find data_cache/features -maxdepth 1 -name '*.h5'`.
Suggested fix: either convert integer epoch timestamp indexes to `DatetimeIndex` in loaders before gate, or make the backward-incompatibility explicit with a validation command proving no accepted workflow depends on flat HDF5/RangeIndex.

ID: ADV-CODEX-5 / BLOCKING / Golden and byte-equal plan can write under data_cache, violating execution red lines
Receipt: TODO requires true end-to-end analyze and byte-equal on registry runs (`docs/IC_PHASE1_1A_ALIGN_TODO.md:51,71`). The API materialization path writes HDF5/meta to `data_cache/reports/ic_ingest_cache` if FeatureLibrary is used (`api/services/ic_analysis_service.py:1248-1280`). AGENTS red line says never delete/modify `data_cache/`.
Impact: an implementation agent following the TODO may create or overwrite files in `data_cache/reports/ic_ingest_cache` just to run Golden, failing postflight or contaminating cache state.
RECHECK: `nl -ba api/services/ic_analysis_service.py | sed -n '1248,1280p'`; run grep for `data_cache/reports/ic_ingest_cache`.
Suggested fix: SPEC/TODO must define a read-only Golden harness or direct all generated replay artifacts to `/tmp`/test temp dirs. If existing registry artifacts are used, require commands that only read manifests/parquet and never materialize into `data_cache`.

ID: ADV-CODEX-6 / BLOCKING / M5 mutation is not self-consistent and invites cheap green
Receipt: SPEC M5 says monkeypatch gate off + M1 means end-to-end test "must leak" (`docs/IC_PHASE1_1A_ALIGN_SPEC.md:71`). TODO says the same: "monkeypatch 關 gate+錯位資料→現行測試須因此漏" (`docs/IC_PHASE1_1A_ALIGN_TODO.md:71`).
Impact: normal pytest suites cannot assert "must leak" without asserting the broken behavior. A weak implementation can mark M5 as manual or write a test that passes when downstream fails for unrelated reasons.
RECHECK: inspect SPEC/TODO M5 lines above.
Suggested fix: define M5 as mutation-test procedure, not a normal passing test: run the same "M1 wrong data must raise `AlignmentViolationError`" test once normally (passes), then with `validate_alignment` monkeypatched to no-op (the test must fail because no raise occurs). Require command/output receipt for both legs.

ID: ADV-CODEX-7 / BLOCKING / horizon extraction is under-specified for external labels
Receipt: SPEC says horizon must be parsed from label names like `return_1` (`docs/IC_PHASE1_1A_ALIGN_SPEC.md:21`), TODO repeats "`return_1`→1" (`docs/IC_PHASE1_1A_ALIGN_TODO.md:9`). Current `_select_label_series` falls back by substring of `default_horizon` or first column (`momentum/Analysis/ic_filter_orchestrator.py:2164-2178`). Feature Factory labels use names like `label_return_{horizon}d` (`momentum/FeatureEngineering/labels/label_generator.py` from rg output), where `1d` is duration, not necessarily one bar.
Impact: gate may validate with the wrong lag for external labels or day-based labels. That is exactly the silent off-by-horizon class this task is supposed to kill.
RECHECK: `rg -n "label_return_|return_1|default_horizon|_select_label_series" momentum docs -g '*.py' -g '*.md'`.
Suggested fix: require explicit label horizon metadata for labels_path; parsing is allowed only for a documented regex with units. If metadata is absent or ambiguous, fail closed with a targeted error.

ID: ADV-CODEX-8 / NON-BLOCKING / Phase 3 cut2 oracle convergence should be deferred
Receipt: SPEC marks Phase 3 optional/deferred (`docs/IC_PHASE1_1A_ALIGN_SPEC.md:62-63,82`). Current cross-sectional service has per-symbol MultiIndex logic and a bespoke matched timestamp oracle (`api/services/ic_analysis_service.py:1380-1455`). `validate_alignment` signature currently accepts generic feature/target/spec but no symbol dimension semantics (`momentum/core/contracts.py:745-765`).
Impact: forcing Phase 3 now expands the gate API into MultiIndex/per-symbol semantics and risks regressing a path that cut2 already signed off.
RECHECK: inspect `api/services/ic_analysis_service.py:1380-1455` and `contracts.py:745-765`.
Suggested fix: move Phase 3 to §N deferred for this knife. Add a drift test that compares the existing cut2 oracle to the new gate later, after single-axis semantics are stable.

ID: ADV-CODEX-9 / NON-BLOCKING / SPEC source receipt filename is wrong
Receipt: SPEC line 3 cites `handoffs/IC1A-CUTS-ORDER-{claude,codex,composer}.md`; `rg --files handoffs | rg 'IC1A.*CUTS.*ORDER'` shows `handoffs/IC1A-REMAINING-CUTS-ORDER-claude.md`, `handoffs/IC1A-CUTS-ORDER-codex.md`, `handoffs/IC1A-CUTS-ORDER-composer.md`.
Impact: future agents trying to verify the Claude receipt will get a missing file and may either block or skip evidence.
RECHECK: command above.
Suggested fix: correct the SPEC receipt path.

## Verdict
VERDICT: REJECT

Blocking findings: ADV-CODEX-1 through ADV-CODEX-7.

ASSUMPTIONS_VERIFIED: SPEC/TODO read; background receipts read using actual available filenames; consumer-map gaps verified by static reads; real kline gap behavior verified by read-only HDF5 timestamp script; no production files edited.
TESTS_RUN: no pytest; review-only task. Verification commands were `rg`/`nl -ba` static reads plus read-only Python scripts over `data_cache/features/registry.json` and kline HDF5 timestamp arrays.
FAILURES_SEEN: missing referenced file `handoffs/IC1A-CUTS-ORDER-claude.md`; actual Claude receipt is `handoffs/IC1A-REMAINING-CUTS-ORDER-claude.md`.
SCOPE_CHANGES: none; wrote only this review output file.
NUMERIC_OR_SCHEMA_IMPACT: none from this review; findings warn that proposed gate semantics can affect label validation, Golden execution, and legacy HDF5 acceptance.
STATUS: DONE
