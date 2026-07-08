# IC1A ALIGN SPEC/TODO v3 R3 incremental verification — Codex

TASK_ID: ic1a-align-specadv-r3
MODE: read-only incremental close verification; production code/tests unchanged.
R2_INPUT: handoffs/IC1A-ALIGN-SPECADV-R2-codex.md
SPEC: docs/IC_PHASE1_1A_ALIGN_SPEC.md v3
TODO: docs/IC_PHASE1_1A_ALIGN_TODO.md v3

## Incremental Findings

R3-D-4 index normalization writeback / CLOSED
依據:v3 SPEC §A D-4 requires stage0/stage2 gate PASS to write both features_df and label index back to DatetimeIndex at one normalization point, with value/NaN/column sha256 invariants and unchanged HDF5 persisted schema. This directly closes the R2 ambiguity where D-1 converted only inside comparison while downstream slice/event_filter/IC could still receive split int64 vs datetime axes.

R3-Task2.4 event_filter cross-dtype intersection / CLOSED
依據:v3 Task 2.4 now requires both sides to be D-1/D-4 normalized before intersection, forbids bare cross-dtype `Index.intersection`, treats int64 features at stage3 as upstream bypass, and raises only after same-type intersection is empty. Re-run snippet confirms raw int64 Index ∩ DatetimeIndex size=0, while D-1 coerced DatetimeIndex ∩ DatetimeIndex size=2.

R3-Task2.3 mixed same-length slice rule / CLOSED
依據:v3 Task 2.3 explicitly states mixed int64-vs-datetime same-length axes must be D-1 converted before comparison, and after D-4 such mixed input is an upstream bypass that should raise. This preserves my R2 approval of length-coincidence fail-closed behavior without reintroducing positional repair.

R3-Task2.3/2.4 consistency with Codex R2 approval / CLOSED
依據:Codex R2 approved v2 after verifying D-1 int64 compatibility, D-2 bar-ordinal, D-3 gap policy, horizon resolver, M5/M6, and consumer-map coverage. v3 only tightens the normalization boundary and event_filter intersection semantics; it does not weaken any R2-approved fail-closed rule, Golden condition, mutation receipt, loader schema constraint, or deferred §N scope.

R3-new-hole: caller dependency on int64 index values / CLOSED
依據:grep/read of `ic_filter_orchestrator.py` and `ic_engine.py` found downstream index consumers mainly use `_coerce_timestamp_array`, `.equals`, `.reindex`, `.loc`, `.iloc`, or timestamp group slicing. `_coerce_timestamp_array` returns equal datetime64 arrays for int64 seconds and DatetimeIndex receipts. The old dangerous consumers are already listed in Tasks 2.3/2.4/2.5. No evidence found of a downstream caller after stage0/stage2 that semantically requires the index object itself to remain int64 seconds; persisted HDF5 schema remains int64 by D-4.

## Verdict

VERDICT: APPROVE
RECONCILE-STAMP APPROVED Codex 2026-07-08

ASSUMPTIONS_VERIFIED: Read HANDOFF.md, CLAUDE.md, R3 prompt, Codex R2 output, Composer R2 output, SPEC v3, TODO v3; traced D-4/2.3/2.4 increments to R2 findings; grepped/read orchestrator and IC engine index consumers; verified `_coerce_timestamp_array` gives equal datetime64 values for int64 seconds and DatetimeIndex; verified raw int64∩datetime=0 vs coerced datetime∩datetime=2.
TESTS_RUN: no pytest; review-only verification. Commands: `sed`/`nl`/`rg` static reads; Python snippets for `_coerce_timestamp_array` and pandas intersection behavior. Snippets supported APPROVE.
FAILURES_SEEN: raw int64 Index ∩ DatetimeIndex returns empty as expected from R2 Composer; v3 D-4/2.4 closes it by same-type normalization before intersection.
SCOPE_CHANGES: none; wrote only handoffs/IC1A-ALIGN-SPECADV-R3-codex.md.
NUMERIC_OR_SCHEMA_IMPACT: none from this review; approved spec keeps persisted HDF5 schema unchanged and requires value/NaN/column sha256 invariants for D-4 writeback.
STATUS: DONE
