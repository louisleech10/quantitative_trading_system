# CUT2-XSECTIONAL Codex Code Review

Task: independent code review + adversarial data-correctness check for F1/F2/F3/F4 implementation.
Verdict: DATA_CORRECTNESS FAIL.

## Findings
1. BLOCKING — `momentum/Analysis/ic_filter_orchestrator.py:_enforce_cross_sectional_label_coverage`
   - Counterexample: one timestamp per symbol, `return_1` all NaN, `ic_train_test_split=False`.
   - Observed: `analyze_cross_sectional` does not raise; it returns metadata `per_symbol_coverage={'BTC':0.0,'ETH':0.0}` and NaN summary rows.
   - Cause: `floor_s = (len_s - effective_horizon) / len_s`; when `len_s <= horizon`, threshold is `<=0`, so all-NaN labels pass.
   - Why blocking: violates F4 fail-closed invariant "全 NaN/低覆蓋→raise 非靜默" and can silently emit all-NaN IC.
   - Fix: if `len_s <= effective_horizon` or `labels.notna().sum()==0`, raise `InvalidInputError`; add boundary test with `len_s==horizon` all NaN.

2. MAJOR — `tests/momentum/test_ic_cross_sectional_cut2.py:test_cross_sectional_oos_split_mutation_shrunk_purge_fails`
   - Claude疑點 confirmed: test does not mutate production purge/split logic.
   - It proves `actual_gap >= required_gap + 1h` fails, which is tautological for the existing metadata, not red-on-break for `_build_cross_sectional_global_split`.
   - Existing line 113 test does assert real gap, so production gap is covered; mutation should be replaced with monkeypatch/variant that actually reduces `test_start` or `purge_td` and verifies the real gap assertion catches it.

3. MAJOR — `api/services/ic_analysis_service.py:_append_cross_sectional_labels`
   - Implementation raises when feature timestamps are not a subset of kline timestamps.
   - SPEC Task 1.1 boundary says kline holes should produce NaN labels and let F4 decide coverage.
   - This is safer than silent misalignment, but it diverges from the frozen boundary contract and may turn sparse kline holes into hard failure instead of coverage-gated degradation.

4. MINOR — `api/services/ic_analysis_service.py:_append_cross_sectional_labels`
   - Timestamp contract says int64 epoch seconds; code accepts any integer dtype.
   - Suggested fix: assert `np.issubdtype(ts_raw.dtype, np.integer)` plus int64 or explicitly document narrower/looser contract.

## Checks Run
- `pytest tests/momentum/test_ic_cross_sectional_cut2.py tests/api/test_ic_analysis_service.py -k 'cross_sectional or append_cross_sectional_labels' -q` → 12 passed, 4 deselected.
- Repro script for finding 1 → `NO_RAISE`, all-NaN report returned.
- `pytest tests/momentum/test_ic_cross_sectional_cut2.py::test_cross_sectional_oos_split_mutation_shrunk_purge_fails -q` → 1 passed, confirming test is not red-on-break.
- `pytest tests/momentum/test_ic_filter_orchestrator.py -q` → 2 failed, 32 passed; failures match HEAD defaults/fixtures (`ic_train_test_split=True` + RangeIndex frequency validation), not this CUT2 diff.
- `grep -r "from api\\." momentum/ | wc -l` → 0.

## Scope / Schema / Numeric Impact
- No direct code changes made by this review.
- Reviewed diff touches labels, split selection, report metadata, and tests.
- No feature value/column/row mutation observed in implementation path; F3 uses test row selection only for IC report outputs.

ASSUMPTIONS_VERIFIED: RECONCILE-STAMP codex+composer APPROVED present; HEAD already has `ic_train_test_split=True`; CUT2 focused tests pass; F4 short-series all-NaN counterexample reproduces.
TESTS_RUN: see Checks Run.
FAILURES_SEEN: blocking F4 all-NaN short-series no-raise; pre-existing `test_ic_filter_orchestrator.py` 2 fails.
SCOPE_CHANGES: none.
NUMERIC_OR_SCHEMA_IMPACT: review only; implementation adds metadata `per_symbol_coverage`, `mean_label_coverage`, `ic_train_test_split`.
STATUS: DONE — verdict: 資料正確性 FAIL
