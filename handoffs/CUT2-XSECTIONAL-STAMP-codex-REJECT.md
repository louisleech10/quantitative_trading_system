# CUT2 XSECTIONAL reconcile stamp review — Codex REJECT

Date: 2026-07-07
Reviewer: Codex
Decision: REJECT

Resolved: 2026-07-07 — superseded by codex APPROVED stamp in `handoffs/CUT2-XSECTIONAL-SPECADV-RECONCILE.md`; the three residual blocking items below were rechecked against revised TODO and found closed.

## Residual Blocking

1. TODO Task 1.1 does not implement RECONCILE R8 / SPEC Task 1.1 fail-closed timestamp contract.
   - Reconcile/SPEC require non-monotonic, duplicated, mixed-unit, negative, or ambiguous kline timestamps to raise rather than guess.
   - TODO line content still says `raw["timestamp"].max() > 1e12` means milliseconds and converts by heuristic.
   - This reintroduces the exact "magic unit guess" risk that R8 accepted as a required closure item, so implementers can follow TODO and bypass SPEC.

2. TODO Batch2 validation contradicts RECONCILE D-2 fail-closed labels_path scope.
   - D-2 explicitly chooses minimal F2: cross_sectional single-axis labels_path raises; no symbol-aware HDF5 loader/schema in this knife.
   - TODO Batch Gate still says Batch2 should verify "帶 symbol 維度逐幣正確".
   - That either asks for deferred symbol-aware labels_path support without schema/loader scope, or encourages a test-only bypass. This is the Codex B-2 fake-green risk not fully closed in TODO.

3. TODO Task 4.1 modification list has a stale config note that can mislead implementers.
   - Task 2.1 says add `ICConfig.min_label_coverage_tol`; Task 4.1 says `ICConfig` add `min_label_coverage` was already in Task 2.1.
   - Reconcile D-3 removed magic coverage floor and chose derived per-symbol floor plus tolerance. The stale field name is not by itself a schema change, but in an implementation prompt it can reintroduce the old floor knob.

## Non-Blocking Notes

- Reconcile itself addresses Codex B-1/B-2/B-3 and M-1/M-3 with concrete D-1 through D-4 decisions.
- SPEC is mostly aligned with those decisions: global synchronized boundary, all report outputs test-only, per-symbol coverage floor, labels_path fail-closed, and mutation red-on-break are present.
- Claude adversarial findings were not treated as privileged; D-1/D-3 cover Claude B-1/B-2 and M-1/M-2.

ASSUMPTIONS_VERIFIED: Read HANDOFF.md, CLAUDE.md, CUT2-XSECTIONAL-STAMP-PROMPT.md, reconcile, revised SPEC/TODO, and all three adversarial legs; compared R1-R10/D-1-D-4 against SPEC/TODO text.
TESTS_RUN: `sed`/`wc`/`rg` read-only review commands only; no pytest because this was a stamp review.
FAILURES_SEEN: none during command execution; review found residual blocking text conflicts in TODO.
SCOPE_CHANGES: none; did not append APPROVED stamp.
NUMERIC_OR_SCHEMA_IMPACT: none from this review; residual items could affect timestamp label correctness and labels_path schema scope if left unresolved.
STATUS: BLOCKED
