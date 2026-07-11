# P2DEBT-T1 TODO R2 Codex closure re-verify
Task-id: p2debt-t1 | Date: 2026-07-11 | Reviewer: codex
Compared: `P2DEBT-T1-TODO-DRAFT-R1.md` → `P2DEBT-T1-TODO-DRAFT-R2.md`; SPEC prerequisite R3 has codex APPROVED stamp.

## Original findings
- **B1 CLOSED** — ran `grep -q 'RISK-HIT: b' docs/VERIFY_GATE_SPEC.md`; bad baseline `rc=1`. Correct polarity now fails before the line exists and will pass only on file content.
- **B2 CLOSED** — ran `bash -c 'bash -c "exit 1"; rc=$?; echo mock_checker_rc=$rc; exit $rc'`; printed `mock_checker_rc=1`, outer `rc=1`. R2 preserves checker exit in 1.2b.4 and Final §4. Real checker replay was terminated after two >30s hangs; shell-polarity counterexample itself is verified.
- **B3 STILL-OPEN** — tmp git repo: baseline had dirty `preexisting.txt`; captured R2 pre-head/pre-diff; then changed exactly the four whitelist files. R2 post command listed five paths and `/usr/bin/diff -u whitelist post` returned `rc=1`, with `+preexisting.txt`.
- B3 cause: `/tmp/p2debt-t1-pre-diff.txt` is written but never consumed; `git diff --name-only "$PRE_HEAD"` is the unadjusted dirty-tree diff that §0 says not to use. A legitimate four-file implementation cannot pass in the documented dirty baseline.
- **M1 CLOSED** — Phase Gate L193–195 all use `venv/bin/python -m pytest`; `venv/bin/python -m pytest --version` returned `pytest 8.4.2`, `rc=0`; no bare pytest remains in that gate.

## R2-vs-R1 scope and new finding
- `diff -u R1 R2` touched only: title; B1/B2/B3/M1 command text; Final/Phase scope receipts; and R2-CLOSURE lines. No implementation task/oracle/scope semantics changed otherwise.
- **NEW-B4 STILL-OPEN** — R2 L72 execution prompt and footer L262 both still reference `TODO-DRAFT-R1.md`. This is not harmless: a cold-start executor/reviewer can be routed back to R1, which contains the B1/B2/B3 defects. Both references need R2.

ASSUMPTIONS_VERIFIED: dirty baseline exists; B1 bad-baseline polarity; B2 shell exit preservation; B3 exact-four whitelist behavior; M1 venv availability.
TESTS_RUN: commands above; B1/B2/M1 pass; B3 counterexample fails as described; R1/R2 diff inspected.
FAILURES_SEEN: real `template_check.sh` replay hung twice; no repo mutation used to bypass it.
SCOPE_CHANGES: none; only this output file written; experiments under `/tmp`; no `data_cache/` writes.
NUMERIC_OR_SCHEMA_IMPACT: none.
Verdict: BLOCK — B3 does not subtract the dirty baseline, and two stale R1 references misroute execution/review
