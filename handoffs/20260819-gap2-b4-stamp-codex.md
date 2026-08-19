# GAP-2 B4 stamp — codex

TASK_ID: 20260819-GAP2-B4-STAMP-R22
FAMILY: codex
VERDICT: BLOCKED
STAMP_TARGET: handoffs/reconcile/20260819-gap2-b4-review-r21/synth.md
BODY_SHA256: 969664ed8f7e400a619974c58d0bf9d949251b76b204b556de9485913d8971a8

CRITERION_1: PASS — `bash scripts/completeness_check.sh --lock .../sources.lock`; all 3 source groups passed, 4/4 IDs covered.
CRITERION_2: PASS — targeted real-fixture pytest for `test_persisted_report_json_mirrors_survivor_output`; 1 passed. Disk report and returned five-key metadata matched.
CRITERION_3: PASS — targeted pytest for `test_provenance_uses_effective_config`; 1 passed. kendall/log were present in survivor provenance.
CRITERION_4: BLOCKED — exact six-file pytest collected 73; after 24 passed it remained in `test_budget_bench_receipt` at `np.linalg.lstsq` for 1773.00s and was interrupted. Non-bench rerun was interrupted after 3 passed/1 deselected in 335.69s.
CRITERION_5: PASS BY EXISTING RECEIPT — `handoffs/run_receipts/20260819T011504Z-gap2-B4-probe.log` records 7 RED/RESTORED GREEN cases and post-restore rc=0; probe was not rerun.
CRITERION_6: BLOCKED — `git diff ab53c24e e4e3bb97 --name-only` included non-hook paths such as `HANDOFF.md`, docs/site files, and 白話 files beyond the brief allowlist.

OTHER_GATES: `ic_wiring_check.sh` rc=0; `gap2_freeze_golden.py --check` rc=0; `mutation_probe_check.sh` rc=0 (4 passed).
SCOPE_CHANGES: Only the BLOCKED stamp line and this handoff were written by codex; existing dirty state was preserved. No source change, commit, or push.
NUMERIC_OR_SCHEMA_IMPACT: none.
TMP_CLEANUP: `/tmp` workdir cleanup was not performed because no exact workdir target was identified; `claude-501` was preserved.
