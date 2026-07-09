# IC1A ALIGN SIGNOFF — codex
task-id: ic1a-align-signoff
date: 2026-07-09
scope: read-only adversarial data-correctness signoff for commits fd5866f/854d444/78c85bb/e47933d
spec: docs/IC_PHASE1_1A_ALIGN_SPEC.md v3; reconcile approved in handoffs/IC1A-ALIGN-RECONCILE.md
method: custom Python signoff script executed from repo; temp artifacts only under /tmp/ic1a-align-signoff
data: true data_cache/features 12h e53e2290 for BTCUSDT/ETHUSDT/BCHUSDT plus data_cache/feature_klines/kline_cache.h5
receipt_file: /tmp/ic1a-align-signoff/receipts.json

receipts:
- true_btc_kernel_pass: PASS rows=1696 checked_samples=93 gaps=0
- adv_wrong_tf_1h_into_12h_spec: RAISED AlignmentViolationError cadence mismatch expected 12h got 1h
- adv_non_monotonic_label_order: RAISED AlignmentViolationError target_data index monotonic
- adv_duplicate_label_timestamp: RAISED AlignmentViolationError target_data index unique
- adv_millisecond_mixed_label_index: RAISED AlignmentViolationError milliseconds expected epoch seconds
- adv_label_values_from_eth_on_btc_axis: RAISED AlignmentViolationError label mismatch at 2024-01-01
- adv_single_point_head_boundary_wrong_value: RAISED AlignmentViolationError label mismatch at 2024-01-01
- adv_external_labels_unparseable_name_stage0: RAISED InvalidInputError label horizon cannot be resolved
- adv_slice_equal_length_shifted_label: RAISED AlignmentViolationError positional slice refused
- adv_grouped_equal_length_shifted_label: RAISED AlignmentViolationError grouped positional alignment refused
- e2e_true_12h_BTCUSDT: PASS summary_rows=3 selected=0 alignment checked_samples=60 gap_count=0
- e2e_true_12h_ETHUSDT: PASS summary_rows=3 selected=0 alignment checked_samples=61 gap_count=0
- e2e_true_12h_BCHUSDT: PASS summary_rows=3 selected=0 alignment checked_samples=61 gap_count=0
- m6_true_btc_gate_on_off_summary_sha: PASS sha_on=sha_off=4602b456dec96962ac3d288df123b872b73a451e38ed962d21c39990ff59ae06 rows=3
decision: SIGNOFF:codex:DATA-CORRECT
blocking: none
data_cache_write: none intended; all generated HDF5/JSON/report artifacts redirected to /tmp
