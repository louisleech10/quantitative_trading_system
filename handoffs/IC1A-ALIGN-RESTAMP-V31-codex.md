# IC1A ALIGN RESTAMP V31 codex
TASK_ID: ic1a-align-restamp-v31-codex
ROLE: reconcile restamp review, read-only analysis plus append stamp

RECEIPT_COMMANDS:
- sed -n '1,240p' HANDOFF.md
- sed -n '1,260p' CLAUDE.md
- sed -n '1,260p' handoffs/IC1A-ALIGN-RECONCILE.md
- sed -n '1,220p' handoffs/IC1A-ALIGN-B1GAP-REVIEW-codex.md
- git diff HEAD -- docs/IC_PHASE1_1A_ALIGN_SPEC.md
- rg -n "ORACLE_RETURN_KINDS|_ORACLE_RETURN_KINDS|def validate_alignment|return_kind|AlignmentViolationError|simple|log" momentum/core/contracts.py
- rg -n "ORACLE_RETURN_KINDS|return_kind|simple|log|unsupported|AlignmentViolationError|validate_alignment" tests/momentum/core/test_alignment_contract.py
- git show 24f36d7 --stat
- sed -n '900,1012p' momentum/core/contracts.py
- sed -n '196,256p' tests/momentum/core/test_alignment_contract.py
- git diff --numstat HEAD -- docs/IC_PHASE1_1A_ALIGN_SPEC.md
- pytest tests/momentum/core/test_alignment_contract.py -q
- bash scripts/reconcile_body_hash.sh handoffs/IC1A-ALIGN-RECONCILE.md

EVIDENCE:
- Diff scope: SPEC diff is 2 insertions only: one v3.1 changelog line and one Task 1.1 D-5 return_kind paragraph. No D-1~D-4, §G, §V, §C, or §N hunks appeared in git diff.
- Landed code fidelity: contracts.py defines `_ORACLE_RETURN_KINDS` with `log: np.log(future / current)` and `simple: future / current - 1.0`, exposes `ORACLE_RETURN_KINDS = frozenset(_ORACLE_RETURN_KINDS)`, adds `validate_alignment(..., return_kind: str = "log")`, and raises `AlignmentViolationError` when close is provided with unsupported return_kind.
- Tests and commit evidence: tests/momentum/core/test_alignment_contract.py contains simple pass, simple shifted raise, cross-kind mismatch raise, and unsupported fail-closed tests; pytest reported 19 passed. `git show 24f36d7 --stat` shows the B-1 implementation touched contracts.py, ic_filter_orchestrator.py, and test_alignment_contract.py, plus the prior review handoff.
- B1GAP consistency: handoffs/IC1A-ALIGN-B1GAP-REVIEW-codex.md reports no findings and Verdict: APPROVE, with receipts for simple formula, 19 alignment tests, cross-kind mutation, fail-closed behavior, golden, and no assertion weakening.

STAMP:
- body_hash_before_stamp: ae9367f903d39b79b633d1e307a95c6ae0f938c85cecc81cbc8ee2e2e65d57af
- appended_to: handoffs/IC1A-ALIGN-RECONCILE.md
- stamp_line: RECONCILE-STAMP: codex APPROVED 2026-07-09 sha256:ae9367f903d39b79b633d1e307a95c6ae0f938c85cecc81cbc8ee2e2e65d57af task:ic1a-align-restamp-v31-codex

Verdict: APPROVE

ASSUMPTIONS_VERIFIED: v3.1 diff limited to changelog+D-5; D-5 matches 24f36d7 landed behavior; B1GAP prior conclusion remains consistent.
TESTS_RUN: pytest tests/momentum/core/test_alignment_contract.py -q -> 19 passed in 0.07s; bash scripts/reconcile_body_hash.sh handoffs/IC1A-ALIGN-RECONCILE.md -> ae9367f903d39b79b633d1e307a95c6ae0f938c85cecc81cbc8ee2e2e65d57af.
FAILURES_SEEN: none
SCOPE_CHANGES: none
STATUS: DONE
