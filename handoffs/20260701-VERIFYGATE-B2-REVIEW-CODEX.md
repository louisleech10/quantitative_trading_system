# VERIFYGATE B2 adversarial code review — Codex

VERDICT: CHANGES-REQUESTED

## Scope
- Reviewed `scripts/verification_claim_check.py`, `tests/governance/test_verify_gate.py`, `handoffs/pending_verifications.jsonl`.
- Compared against `docs/VERIFY_GATE_SPEC.md` Phase 2 and `docs/VERIFY_GATE_TODO.md` Task 2.1/2.2.
- Ran the required pytest and constructed adversarial checker fixtures.

## Required Baseline
- `venv/bin/python -m pytest tests/governance/test_verify_gate.py -q` → PASS, 20 passed in 6.33s.
- `venv/bin/python scripts/verification_claim_check.py --files docs/VERIFY_GATE_SPEC.md handoffs/*FORENSICS*.md handoffs/*DELIB*.md docs/VERIFY_GATE_SPEC_PLAIN*.md` → exit 0, with WARNs for `正確紅`, `探針紅`, `驗證通過`.

## BLOCKING Findings

### B2-CODEX-1 — Operational synonyms still bypass the gate
- File/lines: `scripts/verification_claim_check.py:31-39`, `scripts/verification_claim_check.py:761-773`.
- Repro fixtures:
  - `## 現役任務\n\n- align 探針紅\n` → checker exit 0 with only WARN.
  - `## 現役任務\n\n- align 正確紅\n` → checker exit 0 with only WARN.
  - `## 現役任務\n\n- align 搞定\n` → checker exit 0 with no WARN.
- Counter-checks:
  - `align 驗證通過` exits 1 because weak `通過` matches.
  - `align 全綠` exits 1.
- Impact: review prompt explicitly listed `正確紅` / `探針紅` / `搞定` as bypass attempts. The current code would allow operational status claims with no VERIFY.

### B2-CODEX-2 — Inline `claim-context: discussion` suppresses an operational claim
- File/lines: `scripts/verification_claim_check.py:44-47`, `scripts/verification_claim_check.py:705-706`.
- Repro fixture: `## 現役任務\n\n- <!-- claim-context: discussion --> align mutation 已驗真紅\n`
- Actual: checker exit 0.
- Expected: exit 1. SPEC says the HTML discussion marker only covers fenced/quoted discussion, not arbitrary operational text.
- Impact: a single inline comment can turn a HANDOFF operational result into fail-open.

### B2-CODEX-3 — Any `FORENSICS` / `DELIB` filename is treated as discussion, even under `## 已完成`
- File/lines: `scripts/verification_claim_check.py:72-75`, `scripts/verification_claim_check.py:306-307`.
- Repro fixture path: `/tmp/20260701-FF-FORENSICS-FAKE.md`
- Repro content: `## 已完成\n\n- align mutation 已驗真紅\n`
- Actual: checker exit 0.
- Expected: exit 1 for operational result blocks. TODO V8 says whitelist/discussion files must not allow operational new claims.
- Impact: any handoff-like file with `FORENSICS`, `DELIB`, `RECONCILE`, or `ADV-` in the name becomes a blanket bypass.

### B2-CODEX-4 — Scope intersection is too broad; one receipt can support the wrong node claim
- File/lines: `scripts/verification_claim_check.py:315-326`, `scripts/verification_claim_check.py:520-532`.
- Repro setup: failing `mutation_runtime` receipt `r-align` with `selected_node_ids=["tests/x.py::test_mutation_align"]`.
- Repro fixture:
  `- center mutation 真紅 VERIFY:r-align tests/x.py::test_mutation_center; align mutation 真紅 VERIFY:r-align tests/x.py::test_mutation_align`
- Actual: checker exit 0.
- Expected: exit 1 for the center claim. The receipt only covers `test_mutation_align`.
- Root cause: `_extract_scope()` also adds `tests/x.py`, and `_scope_intersects()` accepts substring overlap, so shared file path is enough to satisfy a different node id.
- Test gap: `test_v10_same_paragraph_partial_scope_blocked` only covers a second claim with no VERIFY. It does not cover a reused VERIFY with mismatched scope.

### B2-CODEX-5 — Pending ledger close accepts arbitrary fake close events
- File/lines: `scripts/verification_claim_check.py:616-628`, `scripts/verification_claim_check.py:662-668`.
- Repro ledger:
  - open `pending_id=p1`, `task_id=P0-FF-3`, `claim_fingerprint=abc`, `required_runtime_class=mutation_runtime`, node `tests/x.py::test_mutation_align`
  - close `pending_id=p1`, `claim_fingerprint=wrong`, `required_runtime_class=static_only`, `receipt_id=fake-no-receipt`
- Repro claim: `STATUS: DONE — P0-FF-3`
- Actual: checker exit 0 and `list-open` prints nothing.
- Expected: pending remains open unless close matches exact pending id plus fingerprint/scope/runtime/receipt provenance.
- Test issue: `tests/governance/test_verify_gate.py:560-573` codifies a close with fake receipt id and no provenance as allowed.

## Confirmed Checks That Hold
- Handwritten receipt without audit is blocked: test V6 and manual review both confirmed.
- Receipt tamper after audit is blocked: changing `selected_node_ids` after audit produced `receipt_sha256 不符`.
- Worktree-only untracked receipt/log is blocked: checker returned `receipt/log 未 tracked 或 staged`.
- `static_only` / `helper_smoke` cannot support mutation runtime claims in the covered cases.
- Split claim and VERIFY in different blocks is blocked.
- Zero-width inside `已驗` is normalized and blocked.
- `VERIFY-EXEMPT` in `HANDOFF.md` operational status is blocked.

## Test Quality Notes
- The mutation probes for audit removal and runtime-class relaxation are meaningful for those two checks.
- Missing regression tests for:
  - operational `探針紅`, `正確紅`, `搞定`;
  - inline `claim-context: discussion` inside an operational bullet;
  - operational blocks inside discussion-named handoff files;
  - reused VERIFY with mismatched node id but shared file path;
  - fake pending close with wrong fingerprint/receipt/runtime/scope.

## Review Matrix
- Synonyms /改詞: BLOCKING, partial coverage only.
- Split claim vs VERIFY different block: CONFIRM, blocked.
- Unicode / zero-width: CONFIRM for zero-width polarity; fullwidth VERIFY not separately accepted.
- HTML comment discussion marker: BLOCKING.
- VERIFY-EXEMPT abuse in HANDOFF/commit/RESULT: CONFIRM for HANDOFF fixture; discussion-file operational bypass remains BLOCKING.
- Handwritten receipt without audit: CONFIRM, blocked.
- Receipt JSON tamper after audit: CONFIRM, blocked by sha256.
- Worktree-only backing: CONFIRM, blocked.
- Fast test backing slow mutation claim: CONFIRM for helper/static class checks.
- Same paragraph multi-claim: BLOCKING for reused VERIFY wrong node scope.
- `claim_fingerprint`: MAJOR residual because pending close does not validate fingerprint.
- Pending ledger exact close: BLOCKING, fake close accepted.
- V7 false-positive-zero command: CONFIRM exit 0, but WARNs reveal unpromoted operational vocabulary.
- Standard library / no momentum-api imports: CONFIRM by code inspection.

ASSUMPTIONS_VERIFIED: Read HANDOFF.md, CLAUDE.md, B2 review prompt, VERIFY_GATE_SPEC/TODO; verified B2 checker behavior via pytest plus adversarial temp fixtures.
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_verify_gate.py -q` PASS 20/20; V7 command PASS exit 0 with WARNs; manual checker fixtures found 5 blocking bypasses.
FAILURES_SEEN: none in baseline tests; adversarial repros above are expected review failures.
SCOPE_CHANGES: none; review file only.
NUMERIC_OR_SCHEMA_IMPACT: none.
STATUS: BLOCKED — B2 code review CHANGES-REQUESTED
