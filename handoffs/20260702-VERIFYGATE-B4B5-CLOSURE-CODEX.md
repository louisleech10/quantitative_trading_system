# VERIFYGATE B4+B5 closure recheck — Codex

Scope: reran the six original Codex counterexamples from `20260702-VERIFYGATE-B4B5-REVIEW-CODEX.md` against Composer fixes in `20260702-VERIFYGATE-B4B5-FIX-composer.md`. No implementation edits; only this handoff was added. Gate/audit side effects from this recheck were restored.

## Per-finding status

| Finding | Status | Rerun output summary |
|---|---|---|
| B4-1 non-ADV adversarial path | CLOSED | Original `/tmp/not-adv.md` gate probe now fails closed: `RECONCILE-STAMP FAIL ... 缺『## 戳記』`; `ERROR: --adversarial 既非 ADV 命名亦未獲 reconcile 戳記核可`; `rc=1`. |
| B4-2 backdated old-date stamp | CLOSED | New reconcile with `APPROVED 2026-07-01 ... task:fakestamp1` and correct body hash now fails: `provenance 不符 — ERROR: 戳記 task:fakestamp1 無 committee_dispatch 審計事件（非 legacy allowlist 須有派工留痕）`; `rc=1`. |
| B5-1 `RUNTIME_CHECK=ok` RESULT | CLOSED | `verification_claim_check.py --files bad-RESULT.md` now fails directly: `RESULT RUNTIME_CHECK 枚舉外值: ok`; `checker rc=1`. `template_check result` also fails; no longer template-only. |
| B5-2 real markdown green/red fingerprint | CLOSED | Parser-derived green/red fingerprints now collide: both `cff5a7a5e2288b2d`; checker fails green+red with `claim_fingerprint 衝突...未標 SUPERSEDED`, `rc=1`; superseded green + red passes, `rc=0`. |
| B5-3 command-output FACT-RECEIPT | CLOSED | SPEC line `已確認: pytest ... 輸出 49 passed` without `FACT-RECEIPT` now fails: `§A 已確認+資料結構事實缺 FACT-RECEIPT`; `rc=1`. |
| B4-3 receipt/audit residue | STILL-OPEN | `find handoffs/run_receipts -name '*mutation-test_b4*'` returns none and `.claude/gate/verify_audit.log` has 0 lines, but real `.claude/gate/audit.log` still contains synthetic trust entries: lines 6721-6724 `mutation_receipt=...mutation-test_b4_green/red.json`. It also contains prior B4 test gate entries at lines 6694/6699, 6709/6714, 6728/6733, 6743/6748, 6788/6793, 6803/6808, 6818/6823. |

## New-bypass spot check

- `pytest tests/governance/ -q` passes, but `test_gate_adversarial_passes_with_dispatch` writes a test dispatch entry and `dispatch.token` into real `.claude/gate/` because `gate.sh` hardcodes `AUDIT=.claude/gate/audit.log` instead of honoring a test override. I restored my run's appended entry and token, but this is a real trust-artifact hygiene gap.
- This means B4 tests are not fully isolated from real gate audit state. Even though receipts are isolated, gate pass tests can keep adding synthetic `B4 test adversarial provenance` entries to `.claude/gate/audit.log`.

## Tests run

```text
pytest tests/governance/test_verify_gate_b4.py::test_gate_adversarial_rejects_non_adv_non_reconcile tests/governance/test_verify_gate_b4.py::test_reconcile_rejects_backdated_stamp_not_on_allowlist tests/governance/test_verify_gate_b5.py::test_b5_result_invalid_enum_fails_checker tests/governance/test_verify_gate_b5.py::test_b5_fingerprint_conflict_real_markdown_green_then_red_fails tests/governance/test_verify_gate_b5.py::test_b5_fingerprint_conflict_real_markdown_superseded_passes tests/governance/test_verify_gate_b5.py::test_b5_spec_command_output_fact_receipt_missing_fails -q
# 6 passed in 0.46s

pytest tests/governance/ -q
# 55 passed in 11.06s

bash scripts/reconcile_stamps_check.sh handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md
# RECONCILE-STAMP PASS ... sha256:86fe39f51ea28fadde135b0c0fd2f75feeb09b4adffaba8bbcde4fd590140044

bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md
bash scripts/template_check.sh todo docs/VERIFY_GATE_TODO.md
# TEMPLATE PASS for both
```

## Structured closeout

ASSUMPTIONS_VERIFIED: Five code-path counterexamples now fail closed; B5-2 is verified through real parsed markdown files, not only hand-built ClaimObject; B4-3 cleanup is incomplete in `.claude/gate/audit.log`.
TESTS_RUN: six targeted pytest nodes pass; full `pytest tests/governance/ -q` pass; DELIB reconcile pass; VERIFY_GATE spec/todo template checks pass.
FAILURES_SEEN: B4-3 still has real audit-log synthetic entries; full governance test run added a real `.claude/gate/audit.log` entry and test `dispatch.token`, then restored to pre-test state.
SCOPE_CHANGES: none; no implementation files edited by this closure pass.
NUMERIC_OR_SCHEMA_IMPACT: none from this review.

VERDICT: CHANGES_REQUIRED
STATUS: DONE

---

## B4-3 round2 recheck — Codex

Scope: rechecked only Claude's B4-3 closure fix: `scripts/gate.sh` `GATE_DIR_OVERRIDE`, B4 pytest tmp isolation, and cleanup of synthetic B4 test trust artifacts from `.claude/gate/audit.log`. No implementation edits by Codex in this pass; this section is append-only.

### Rerun results

- Original residue counterexample now closes:
  - `find handoffs/run_receipts -name '*mutation-test_b4*'` prints no paths.
  - `wc -l .claude/gate/verify_audit.log` remains `0`.
  - `rg -n "intent=B4 test|B4 test adversarial provenance|mutation-test_b4|test_b4_green|test_b4_red|mutation_receipt=.*test_b4" .claude/gate/audit.log` prints no matches.
- Full governance test pollution check:
  - Before: `.claude/gate/audit.log` line count `6750`.
  - Command: `venv/bin/python -m pytest tests/governance/ -q`.
  - Result: `55 passed in 10.27s`.
  - After: `.claude/gate/audit.log` line count `6750`; delta `0`.
  - Post-test grep only matched this real orchestration line: `intent=派 Codex 閉合再驗 B4-3 round2(...)`; no synthetic `B4 test adversarial provenance` entry was appended.

### Gate override review

- `scripts/gate.sh` default behavior is unchanged when `GATE_DIR_OVERRIDE` is unset: token and audit still go to `.claude/gate`.
- B4 tests set `GATE_DIR_OVERRIDE` only inside `_run_gate_adversarial`, and the autouse fixture also redirects `VERIFY_GATE_RECEIPTS_DIR`, `VERIFY_GATE_AUDIT_LOG`, and `VERIFY_GATE_COMMITTEE_AUDIT_LOG` to pytest tmp paths.
- `scripts/gate_check.sh` still hardcodes `GATE_DIR=".claude/gate"` and reads `.claude/gate/${kind}.token`; it does not honor `GATE_DIR_OVERRIDE`. Therefore a tmp override token cannot satisfy the real PreToolUse hook.
- Honest boundary: a user who deliberately invokes `GATE_DIR_OVERRIDE=.claude/gate` gets the default path, and a user with shell/file write authority can always copy or forge local trust artifacts. This fix is test-hygiene isolation, not malicious-user containment, which matches the gate's stated careless-proof / auditability boundary.

### Audit cleanup spot check

- Current audit line count is `6750`. Claude's stated cleanup `6859 -> 6735` is consistent with removing `124` synthetic lines, followed by one legitimate round2 dispatch block of `15` lines (`6735 + 15 = 6750`).
- Legal B4 orchestration entries were not blanket-deleted:
  - earlier real B4 planning/dispatch intents still exist (`intent=B4 bulk-delete...`, `intent=B4 v2...`);
  - real B4/B5 implementation, review, fix, closure, and round2 dispatch blocks remain present at the tail.
- The removed patterns were the specific synthetic test artifacts from the prior STILL-OPEN finding: B4 test gate entries plus `mutation-test_b4_*` receipt references. I found no dangling partial block in the tail sample.

### Structured closeout

ASSUMPTIONS_VERIFIED: B4 pytest isolation now prevents writes to real `.claude/gate/audit.log`; original synthetic B4 test audit/receipt residue patterns are absent; `GATE_DIR_OVERRIDE` does not satisfy the real `gate_check.sh` hook because the hook reads only `.claude/gate`.
TESTS_RUN: `venv/bin/python -m pytest tests/governance/ -q` → 55 passed, audit line count 6750 before and 6750 after; residue `rg`/`find` probes → no synthetic B4 test residue; `wc -l .claude/gate/verify_audit.log` → 0.
FAILURES_SEEN: none in round2.
SCOPE_CHANGES: none; no implementation files edited by Codex in this pass; appended this closure section only.
NUMERIC_OR_SCHEMA_IMPACT: none.

VERDICT: APPROVED — B4-3 CLOSED
STATUS: DONE
