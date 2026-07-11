# p2debt-t3 TODO R2 — Codex re-verification

- Reviewed R1 vs R2 and current tree read-only; only this receipt was written.
- Masking replay: native shell probe produced no output for 60s and was terminated.
- DELEGATED: no native replay rc is claimed due the documented Codex shell hang.
- Static receipt: `sed -n '76,108p' ...R2.md` shows `run_step` retains a failed step via `fail=1` and final `exit "$fail"`.
- BLOCK: the same block sets `tsc_count` only in the parent shell, then runs `bash -c 'test "$tsc_count" -eq 0'`; the variable is not exported/passed, so the child assertion has no reliable value.
- BLOCK: `tsc_count=$(grep -c ... || echo 0)` emits grep's `0` and then echo's `0` on the desired no-match case, yielding a multi-line value rather than integer `0`.
- The same unexported-child pattern affects Final Acceptance variables including `gate_b_rg_rc`, `gate_b_sum`, `gate_c_rg_rc`, `gate_c_diff_rc`, `scope_git_rc`, `scope_diff_rc`, and `decouple_n`.
- Vitest receipt: R2 contains separate `run_step vitest`, `grep -q "Test Files  5 passed (5)"`, and `grep -q "Tests  31 passed (31)"` legs.
- Contract receipt: `frontend/package.json` currently has `"test": "vitest run"`; the five explicit paths therefore cannot silently become watch mode.
- Target receipt: `nl -ba frontend/src/hooks/useFeatureFactory.batchDate.test.ts | sed -n '37,45p'` shows the first mock at L39–41 and L43 blank; R2 now says L39–41.
- Diff receipt: `diff -u ...R1.md ...R2.md` changes only the title/references, Batch/Final acceptance closure, Task 1.5.1 line correction, and their R2 receipts; no unrelated implementation task changed.
- Closed findings: vitest skippability; unreal target line.
- Open finding: fail-closed masking/aggregate exit contract remains non-executable as written.
- RECONCILE-STAMP: WITHHELD.

Verdict: BLOCK — run_step assertions read unexported parent variables, and zero-match tsc counting produces a non-integer multi-line value
