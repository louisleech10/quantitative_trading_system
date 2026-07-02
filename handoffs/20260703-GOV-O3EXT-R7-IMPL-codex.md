# GOV O3EXT R7 B1+B2 Implementation — Codex

DATE: 2026-07-03
TASK: docs/GOV_O3EXT_R7_SPEC.md + docs/GOV_O3EXT_R7_TODO.md §B, B1+B2 plus Task 2.2 script

TASK_MAPPING:
- Task 1.1: `scripts/gate.sh` now supports `--output`, emits JSON-safe `committee_dispatch` for successful `--task-id` dispatches, and adds `register-output <task-id> <handoffs/path>`.
- Task 1.2: `scripts/verify_task_provenance.py` now consumes `committee_output` and pending/nonpending semantics for stamp provenance used by `scripts/reconcile_stamps_check.sh`.
- Task 2.1: `scripts/verification_claim_check.py` adds `VERIFY_GATE_COMMITTEE_AUDIT_LOG` file-class exemption for registered `handoffs/` files with matching raw bytes sha256; `VERIFY_GATE_O3_FILECLASS=0` disables it.
- Task 2.2: `scripts/register_legacy_committee_files.sh` added with the eight SPEC §A.4 paths and current raw sha256 allowlist; tests cover rejection paths only.
- Tests: added `tests/governance/test_verify_gate_r7ext.py` and `tests/governance/test_verify_gate_o3ext.py`; existing redteam expectations unchanged.

ASSUMPTIONS_VERIFIED:
- `gate.sh` previously emitted committee provenance only on high-risk real adversarial paths.
- `verification_claim_check.py` receipt audit log and committee audit log are separate; the implementation reads committee audit via `VERIFY_GATE_COMMITTEE_AUDIT_LOG`.
- `register-output` uses raw file bytes sha256, while reconcile stamps retain existing body_hash validation.

TESTS_RUN:
- `pytest tests/governance/test_verify_gate_r7ext.py tests/governance/test_verify_gate_o3ext.py tests/governance/test_verify_gate_redteam.py -q` => 31 passed.
- `pytest tests/governance/ -q` => 124 passed.
- `PYTHONPYCACHEPREFIX=/tmp/codex_pycache python -m py_compile scripts/verification_claim_check.py scripts/verify_task_provenance.py tests/governance/test_verify_gate_r7ext.py tests/governance/test_verify_gate_o3ext.py` => pass.
- `bash -n scripts/gate.sh scripts/reconcile_stamps_check.sh scripts/register_legacy_committee_files.sh` => pass.
- `git diff -- existing governance test files` => empty; no existing redteam/governance assertions changed.

FAILURES_SEEN:
- First new-test run: pending-dispatch test created the reconcile file before dispatch, producing non-pending hash; fixture order corrected.
- First full governance run: B4 legacy provenance test expected dispatch output-file hash compatibility; restored that compatibility while keeping pending fail-closed.
- Initial `python -m py_compile` wrote pycache under `~/Library/Caches` and hit sandbox permission; rerun used `PYTHONPYCACHEPREFIX=/tmp/codex_pycache`.

SCOPE_CHANGES:
- Added `scripts/verify_task_provenance.py` as a supporting consumer because `reconcile_stamps_check.sh` delegates W2 provenance validation there.
- Did not modify root `HANDOFF.md`; per execution contract, this task handoff is append-only in `handoffs/`.

NUMERIC_OR_SCHEMA_IMPACT:
- No quant numeric/schema/output-size impact.
- Governance audit schema extended by `committee_output`; existing `committee_dispatch` fields remain `task_id/family/output_path/output_sha256/ts`.

RESIDUAL:
- Pre-existing worktree changes remain outside this implementation scope: `.claude/gate/verify_audit.log`, `tests/golden/l65/test_inventory.txt`, frozen SPEC/TODO and legacy committee handoff/receipt files already present before implementation.
