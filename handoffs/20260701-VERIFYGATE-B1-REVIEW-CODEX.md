# VERIFY_GATE B1 code review — Codex

## VERDICT
CHANGES-REQUESTED

## Scope Reviewed
- `scripts/run_with_receipt.py`
- `tests/governance/test_verify_gate.py`
- `.gitignore`
- `handoffs/run_receipts/.gitkeep`
- Against `docs/VERIFY_GATE_SPEC.md` P1-1/P1-2/P1-3 and `docs/VERIFY_GATE_TODO.md` Task 1.1/1.2.

## Findings
1. BLOCKING — node-id mutation runs are misclassified and node scope is lost.
   - Evidence: `scripts/run_with_receipt.py:184-204` only checks `-k test_mutation_`; `scripts/run_with_receipt.py:381` always writes `selected_node_ids=[]`.
   - Manual probe: `pytest tests/governance/test_verify_gate.py::test_mutation_receipt_missing_field_fails -q` produced `runtime_class=helper_smoke`, `selected_node_ids=[]`.
   - Spec impact: P1-1 says runtime_class is derived from argv/node-ids/markers/exit and node-id `test_mutation_*` is mutation_runtime. P2 checker will need selected node IDs for scope intersection.

2. BLOCKING — nonexistent child command does not produce a receipt.
   - Evidence: `scripts/run_with_receipt.py:225-229` lets `subprocess.Popen` `FileNotFoundError` escape before receipt/log/audit creation.
   - Manual probe: `run_with_receipt.py --claim-id review-missing-cmd -- definitely-not-a-real-command-verifygate` exited via traceback with no `*-review-missing-cmd.json`.
   - Spec impact: TODO Task 1.1 boundary explicitly requires nonexistent command -> nonzero exit while still producing a receipt.

3. BLOCKING — audit-chain test does not prove the fields B2 checker must trust.
   - Implementation writes `command_sha256`, `receipt_sha256`, and `log_sha256` in `scripts/run_with_receipt.py:282-294`; manual recomputation matched for a sample receipt.
   - Test gap: `tests/governance/test_verify_gate.py:108-113` checks only event, receipt_id, log_sha256, emitter. It does not assert `command_sha256`, `receipt_sha256`, exit_code, runtime_class, or the receipt hash recomputation needed to catch post-run receipt edits.
   - Spec impact: P1-2 requires checker to recompute command/log/receipt trust fields; B1 tests should lock the audit event contract before B2 depends on it.

4. NON-BLOCKING but weak — runtime_class authoritativeness is not directly tested.
   - Implementation stores `requested_class` separately and does not feed it into `derive_runtime_class`, so requested_class does not currently override runtime_class.
   - Test gap: there is no regression case like `--requested-class mutation_runtime -- python -c pass` asserting receipt runtime_class remains `static_only`.

5. NON-BLOCKING — mutation probe is narrow.
   - `test_mutation_receipt_missing_field_fails` is falsifiable for the required-field assertion, but it mutates an in-memory receipt and exercises the test helper, not production `validate_receipt_schema()`.
   - Existing `test_receipt_schema` would catch omitted production fields, so this is not empty `assert True`, but it is not a strong production mutation probe.

## Confirmed
- `--requested-class` is not used to compute `runtime_class` in the current implementation.
- Audit events include `command_sha256`, `receipt_sha256`, and `log_sha256`; manual recomputation matched one generated sample.
- Exit code passthrough works for normal child exits (`sys.exit(3)` -> wrapper exit 3).
- No `momentum` or `api` imports in reviewed Python files; only standard library plus `pytest` in tests.
- `.gitignore` keeps `handoffs/run_receipts/*.log` and `.claude/gate/verify_audit.log` trackable while `scripts/foo.log` and `data_cache/foo.log` remain ignored.
- No fake data, no numeric/schema impact beyond the new governance receipt/audit schema.

## Tests Run
- `source venv/bin/activate && pytest tests/governance/test_verify_gate.py -q` -> 4 passed.
- `run_with_receipt.py` node-id mutation probe -> exposed `helper_smoke` and empty `selected_node_ids`.
- `run_with_receipt.py` nonexistent command probe -> traceback, no receipt.
- Manual sha256 recomputation for sample receipt/audit/log -> matched.
- `git check-ignore` probes for receipt log, verify_audit.log, scripts/foo.log, data_cache/foo.log.
- `git diff --check -- scripts/run_with_receipt.py tests/governance/test_verify_gate.py .gitignore handoffs/run_receipts/.gitkeep` -> pass.
- `python -m py_compile ...` attempted but blocked by sandbox writing macOS pyc cache outside workspace.
