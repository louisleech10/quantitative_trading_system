# 20260702 O3 Review — Codex

## Scope
- Reviewed `handoffs/O3-composer.md`.
- Reviewed `git diff -- scripts/verification_claim_check.py` against HEAD.
- Ran isolated counterexamples under `/private/tmp`; no repo fixtures or `data_cache/` touched.

## BLOCKING
1. **Allowlisted forensic files can hide real unbacked acceptance claims.**
   - Location: `scripts/verification_claim_check.py:388-413`, `879-888`.
   - Cause: `_forensic_verify_requires_backing()` returns `False` when `VERIFY/REF` is missing or unresolved; `_is_forensic_example_or_discussion()` then treats any `VERIFY:`/`SIGNOFF:` in a forensic path as discussion.
   - Repro result: `handoffs/20260702-REAL-REVIEW.md` containing `align mutation 已驗真紅 VERIFY:no-such-receipt` returned `rc=0`.
   - Same leak reproduced for `docs/VERIFY_GATE_FAKE.md` with the same nonexistent `VERIFY:`.

2. **The whitelist is effectively broader than "discussion only"; operational sections can be bypassed in REVIEW-style files.**
   - Location: `scripts/verification_claim_check.py:455-458` marks operational sections, but `classify_mode()` checks `_is_governance_forensic_path()` first at `884-888`.
   - Repro result: `handoffs/20260702-REAL-REVIEW-OP.md` with `## 已完成` plus `align mutation 已驗真紅 VERIFY:no-such-receipt` returned `rc=0`.
   - This contradicts the O3 stated guarantee that operational sections still fall through to normal backing checks.

3. **Bare strong-polarity claims in allowlisted forensic files are neutralized, not checked.**
   - Location: `scripts/verification_claim_check.py:893-899` after forensic classification.
   - Repro result: `handoffs/20260702-REAL-REVIEW.md` containing only `align mutation 已驗真紅` returned `rc=0`.
   - Because `source_context=forensic_discussion` makes `claim.is_operational=False`, the later operational missing-backing branch never fires.

## NON-BLOCKING
1. **Path normalization overmatches nested paths.**
   - Location: `scripts/verification_claim_check.py:350-363`, `1452-1470`.
   - `_governance_forensic_rel_path()` and `_scannable_rel_path()` search for `handoffs/` or `docs/` anywhere in the path. This is useful for absolute tmp paths, but a repo path like `notes/handoffs/x-REVIEW.md` is normalized to `handoffs/x-REVIEW.md` and receives the whitelist behavior.
   - This is lower priority than the bypass above, but the allowlist should be root-relative for staged/range scans.

## Positive Checks
- HANDOFF root zero-exemption held in direct counterexample: `HANDOFF.md` with nonexistent `VERIFY:` returned `rc=1`.
- Commit message zero-exemption held: commit-msg with nonexistent `VERIFY:` returned `rc=1`.
- RESULT zero-exemption held: `handoffs/20260702-REAL-RESULT.md` with nonexistent `VERIFY:` returned `rc=1` and also failed required RESULT fields.
- R6 fake attribution in HANDOFF remains covered by existing O3 test.
- V7 existing SPEC/DELIB regression remains green in existing O3 and governance tests.

## Tests Run
- `venv/bin/python -m pytest tests/governance/test_verify_gate_o3.py -q` -> 7 passed.
- `venv/bin/python -m pytest tests/governance/ -q` -> 102 passed.
- Isolated `/private/tmp` counterexamples above -> found blocking bypasses; temp files removed with precise `rm`/`rmdir`.

## VERDICT
BLOCKING. O3 fixes the known false-positive pressure, but the current whitelist can let real unbacked acceptance assertions through in REVIEW/REDTEAM/FIX-PROMPT/docs VERIFY_GATE files. The fix should make forensic discussion an explicit content-level exception, not a path-level default, and unresolved `VERIFY/REF` in non-example prose should fail.

## Closure — Composer Redo Content-Level Exemption

### CLOSED
1. REVIEW prose with real unresolved backing still fails:
   - Fixture: `handoffs/20260702-REAL-REVIEW.md`
   - Content: `align mutation 已驗真紅 VERIFY:no-such-receipt`
   - Result: `rc=1`, `receipt 不存在: no-such-receipt`
2. REVIEW operational section still fails:
   - Fixture: `handoffs/20260702-REAL-REVIEW-OP.md`
   - Content: `## 已完成` + unresolved `VERIFY:no-such-receipt`
   - Result: `rc=1`, `receipt 不存在: no-such-receipt`
3. REVIEW bare strong-polarity claim still fails:
   - Fixture: `handoffs/20260702-REAL-REVIEW-BARE.md`
   - Content: `align mutation 已驗真紅`
   - Result: `rc=1`, `operational claim 缺少 VERIFY/REF/SIGNOFF backing`
4. Fenced / inline-code / blockquote attack examples are allowed:
   - Fixture: `handoffs/20260702-ATTACK-EXAMPLE-REVIEW.md`
   - Result: `rc=0`
5. Zero-exemption paths did not regress:
   - `HANDOFF.md` with `VERIFY-EXEMPT` header + unresolved `VERIFY:` -> `rc=1`
   - `handoffs/20260702-O3-RESULT.md` with `VERIFY-EXEMPT` header + unresolved `VERIFY:` -> `rc=1`
   - Existing O3 commit-msg test passed in suite.
6. Path-level default bypass is removed:
   - Code search: `_GOVERNANCE_FORENSIC`, `_is_governance_forensic_path`, `forensic_discussion` absent from checker.
   - Nested path fixture `notes/handoffs/20260702-NESTED-REVIEW.md` with unresolved `VERIFY:` -> `rc=1`.

### STILL-OPEN
- None for the three original BLOCKING findings.
- Residual note: `_scannable_rel_path()` still normalizes nested `notes/handoffs/...` to `handoffs/...`, but with the path-level forensic bypass removed this no longer grants a pass in the reproduced counterexample.

### VERDICT
APPROVED. Original 3 BLOCKING findings are CLOSED under the Composer content-level redo; no regression found in HANDOFF / commit-msg / RESULT zero-exemption checks.

ASSUMPTIONS_VERIFIED: Ran the original three counterexamples plus fenced/inline/blockquote example allowance, HANDOFF/RESULT zero-exemption checks, and nested path bypass shape under isolated `/private/tmp` receipt/audit/ledger paths.
TESTS_RUN: `VERIFY_GATE_RECEIPTS_DIR=/private/tmp/o3-closure-receipts VERIFY_GATE_AUDIT_LOG=/private/tmp/o3-closure-audit/verify_audit.log VERIFY_GATE_PENDING_LEDGER=/private/tmp/o3-closure-pending.jsonl venv/bin/python -m pytest tests/governance/test_verify_gate_o3.py -q` -> 10 passed; manual `/private/tmp` counterexamples -> expected rc results; `VERIFY_GATE_RECEIPTS_DIR=/private/tmp/o3-closure-governance-receipts VERIFY_GATE_AUDIT_LOG=/private/tmp/o3-closure-governance-audit/verify_audit.log VERIFY_GATE_PENDING_LEDGER=/private/tmp/o3-closure-governance-pending.jsonl venv/bin/python -m pytest tests/governance/ -q` -> 105 passed.
FAILURES_SEEN: none during closure verification.
SCOPE_CHANGES: none; only appended this closure section.
NUMERIC_OR_SCHEMA_IMPACT: none.
HANDOFF_NOT_UPDATED: Root `HANDOFF.md` left untouched per append-only execution handoff rule and user-requested target file.
