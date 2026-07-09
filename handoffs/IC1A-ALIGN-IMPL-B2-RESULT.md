TASK: ic1a-align-impl-b2
STATUS: BLOCKED
SCOPE: Implemented Task 2.1/2.2/2.3/2.4 only; did not touch 2.5/2.6 or commit.
CHANGED: momentum/Analysis/ic_filter_orchestrator.py helpers L95/L103 + slice L564 + stage0 L1740 + stage2 L1821 + event_filter L1886.
CHANGED_TESTS: tests/momentum/test_ic_filter_orchestrator.py alignment_gate/slice/event fixtures; cut1 OOS/split fixtures now keep structural tail NaN.
DECISION: D-4 writes features/labels to DatetimeIndex after gate and preserves numeric payload sha256.
DECISION: kline raw_data may carry timestamp column with RangeIndex; Stage2/Stage3 normalize from timestamp column before falling back to index.
DECISION: validate_alignment value oracle is log-return only; non-log configured labels run Tier-1 gate to avoid changing existing return_type semantics.
MUTATION_RECEIPT: M1 PASS via tests/momentum/core/test_alignment_contract.py::test_validate_alignment_m1_shifted_label_raises in core/Analysis run.
MUTATION_RECEIPT: M2 PASS via test_slice_alignment_same_length_misaligned_label_raises and raw_data sibling in selector run.
MUTATION_RECEIPT: M4 PASS via tests/momentum/core/test_alignment_contract.py::test_validate_alignment_m4_wrong_frequency_raises in core/Analysis run.
MUTATION_RECEIPT: M6 PASS via test_alignment_gate_m6_noop_validate_keeps_ic_output_sha; gate on/off summary_table sha equal.
TESTS_RUN: pytest tests/momentum/ -k 'alignment_gate or slice_alignment or event_filter' -q => 25 passed.
TESTS_RUN: pytest tests/momentum/test_ic_filter_orchestrator.py -q => 39 passed.
TESTS_RUN: pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py tests/momentum/Analysis/test_ic_1a_cut1_split.py -q => 27 passed.
TESTS_RUN: pytest tests/momentum/core/ tests/momentum/Analysis/ --ignore=tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q => 388 passed.
TESTS_RUN: grep -r 'from api\.' momentum/ | wc -l => 0.
FAILURES_SEEN: First selector failed on freq string, legacy label column, HDF5 RangeIndex fixture; fixed.
FAILURES_SEEN: Full core/Analysis failed on old cut1 golden deep equality after corrected kline timestamp alignment; not rebaselined.
BLOCKER: tests/momentum/Analysis/test_ic_1a_cut1_golden.py baseline_old/new no longer match; top diffs include summary_table, rolling_ic_series, quantile_returns, grouped_ic, turnover_analysis.
BLOCKER: Golden run and some existing tests wrote data_cache outputs despite redirection work; touched files observed under data_cache/features and data_cache/reports.
ASSUMPTIONS_VERIFIED: B1 kernel imports and raises AlignmentViolationError; reconcile stamps codex+composer APPROVED; decoupling grep is 0.
SCOPE_CHANGES: No production scope beyond orchestrator; test fixture migration touched cut1 OOS/split to satisfy new Stage0 gate.
NUMERIC_OR_SCHEMA_IMPACT: Corrected kline label alignment changes golden IC report payload; requires Claude/user baseline decision.
