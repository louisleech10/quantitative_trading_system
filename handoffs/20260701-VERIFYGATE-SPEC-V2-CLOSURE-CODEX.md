# VERIFY_GATE_SPEC v2 closure review — Codex

VERDICT: CHANGES-REQUESTED — v2 closes the five original BLOCK-class design holes in direction, but one v1 MAJOR remains materially open: referenced receipt/log/audit artifacts are not required to be staged/tracked with the claim. Do not append reconcile approval stamp yet.

## Scope read
- Read `HANDOFF.md`, `CLAUDE.md`.
- Read v1 adversarial: `handoffs/20260701-VERIFYGATE-SPEC-ADV-CODEX.md`.
- Read reconcile: `handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md`.
- Read SPEC v2: `docs/VERIFY_GATE_SPEC.md`.
- Checked repo ignore/tracking for audit/receipt paths: `.gitignore:124 *.log` ignores `.claude/gate/verify_audit.log` and `handoffs/run_receipts/*.log`; no tracked `.claude/gate` or `handoffs/run_receipts` files currently.

## BLOCK closure

### BLOCK-1 receipt self-attestation
Status: CLOSED for the stated careless-proof threat model; residual explicitly accepted, but implementation needs one tightening below.

Closed by SPEC v2 lines 35-40: receipt is produced by `run_with_receipt.py`, includes command/log/git/runtime fields, and checker requires matching append-only audit event. Lines 5-6, 23-25, and 100-103 correctly downgrade the promise to careless-proof + tamper-evident, not cryptographic anti-forgery.

Residual note: audit event in line 39 does not include `receipt_sha256` or started/ended timestamps, although reconcile line 14 asked started/ended and v1 asked receipt sha. This is not a standalone block if line 39 is implemented as strict receipt/log/command recomputation, but it should be tightened together with the open W12 item below.

### BLOCK-2 hook absence/disablement
Status: CLOSED.

Closed by lines 58-62: PreToolUse for handoff edits, repo-tracked `scripts/git_hooks`, CI over changed files as formal enforcement, and `verify_hooks_health.sh` in preflight/postflight/CI. Verified by V13/V14 lines 89-90.

### BLOCK-3 broad `VERIFY-EXEMPT` / discussion laundering
Status: CLOSED.

Closed by lines 48 and 84: discussion only covers fenced/quoted/local discussion structures, operational claims still require backing, and `VERIFY-EXEMPT` in HANDOFF/commit/RESULT must be rejected. This matches reconcile line 20.

### BLOCK-4 pending ledger race / weak binding
Status: CLOSED.

Closed by lines 53-56: reducer, `pending_id`, `claim_fingerprint`, source location, required runtime/node markers, exact-pending close, and `list-open`. V11 line 87 makes the fail-closed behavior testable.

### BLOCK-5 caller-supplied runtime class
Status: CLOSED.

Closed by lines 37, 40, 50, and 85: authoritative class is derived from argv/node ids/markers/exit, requested class is audit-only, parse failures fail closed for node-scoped claims, helper/static receipts cannot back runtime/mutation claims.

## MAJOR closure

### MAJOR-1 vocabulary evasion
Status: CLOSED enough for v1.

Closed by lines 44-48 and 52: Unicode normalization, paragraph/list/table/commit segmentation, claim-object extraction, strong/weak trigger split, and unknown near-terms WARN path. This follows reconcile line 35's deliberate WARN-then-promote balance.

### MAJOR-2 same paragraph wrong binding
Status: CLOSED.

Closed by lines 46, 49, and V10 line 86: each claim has scope/runtime/backing; receipt only satisfies intersecting scope; unsupported neighboring claims still fail.

### MAJOR-3 `log_sha256` schema mismatch
Status: CLOSED.

Closed by line 38 requiring `log_sha256`, line 39 including it in the audit event, and V1 line 77 asserting computed log hash matches.

### MAJOR-4 untracked receipt/log/audit referenced by permanent claim
Status: OPEN — blocks approval.

v2 does not state that every `VERIFY:<id>` / `REF:<id>` / `SIGNOFF` backing artifact must be staged in the same commit or already tracked at the referenced git object. Lines 60-61 say pre-commit scans staged files and CI scans changed files/range, but they do not require the checker to reject a claim whose supporting receipt/log/audit exists only in the local worktree.

This is also a reconcile miss: reconcile line 32 explicitly added W12, "receipt/log 須與 claim 同 staged+hash 對上", but SPEC v2 has no matching P item or V test. Current repo evidence increases the risk: `.gitignore` ignores `*.log`, which includes `.claude/gate/verify_audit.log` and `handoffs/run_receipts/*.log`; without an explicit force-add/tracked-artifact rule, local verification and CI/history can diverge.

Required closure: add a P2/P3 rule that `VERIFY`/`REF`/`SIGNOFF` resolution only accepts backing artifacts that are either staged in the same commit or already tracked in the checked git object, with hash equality for receipt JSON, receipt log, and audit event. Add a V test: commit/handoff claim references an untracked receipt/log/audit that exists in worktree -> local hook/checker rejects; force-added/tracked artifacts -> passes.

### MAJOR-5 meta-assertion tests not real falsifiers
Status: MOSTLY CLOSED, except the MAJOR-4 falsifier remains missing.

Closed by V6/V8/V9/V10/V13/V14/V15/V16 lines 82-92, which cover forged receipt without audit, broad exemption, runtime mislabel, multi-claim laundering, hook health, P4 behavior, and W2/W3 provenance. Missing concrete falsifier: untracked backing artifact referenced by a permanent claim.

### MAJOR-6 stale root HANDOFF claim resurrection
Status: CLOSED within v1 N/A boundary.

Closed by P5-2 lines 70-72 and N/A lines 100-102: v1 does conflict/supersede checking, explicitly defers full generated render index, and records residual risk. This matches reconcile line 26.

## Residual required changes before APPROVED
1. Add W12 to SPEC v2 as a first-class requirement: backing artifacts for claims must be staged/tracked with hash equality; local-only receipt/log/audit cannot satisfy a committed claim.
2. Add a dedicated verification case for W12. Suggested name: `V17 staged_backing_artifacts`: untracked backing rejects; tracked/force-added backing passes.
3. Tighten audit event schema to include `receipt_sha256` and `started_at`/`ended_at`, or explicitly require the checker to recompute every trust-bearing receipt field from command/log and reject JSON-only scope edits. This prevents post-run receipt JSON edits from broadening scope without changing the audit event.

ASSUMPTIONS_VERIFIED: v2 SPEC contains BLOCK-1..5 closure mechanisms; reconcile contains W12; current `.gitignore` ignores `*.log` including proposed audit/log paths.
TESTS_RUN: read-only review; `git check-ignore -v .claude/gate/verify_audit.log handoffs/run_receipts/example.json handoffs/run_receipts/example.log || true` showed audit/log ignore; `git ls-files .claude/gate handoffs/run_receipts ...` showed no tracked backing dirs.
FAILURES_SEEN: none; this is a SPEC review, not implementation test.
SCOPE_CHANGES: none.
NUMERIC_OR_SCHEMA_IMPACT: none; governance spec only.
STATUS: BLOCKED — SPEC v2 still needs W12 staged/tracked backing artifact rule before approval.
