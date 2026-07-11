# p2debt-t3 SPEC R4 — Codex single-point reverify

- Scope: Gate A fail-open closure only; R3 vs R4 drift audit.
- Exact Gate A rerun: DELEGATED — combined normal/bogus `rg` command produced no output for 60s in Codex sandbox and was terminated; no rc is claimed.
- Independent normal-path receipt: `venv/bin/python` read the five whitelisted files → all exist; forbidden-pattern hits = 0.
- Independent error-path receipt: `venv/bin/python` checked `/nonexistent/p2debt-t3-bogus.ts` → exists=False.
- Logic verification: R4 preassert executes `test -f "$f" || exit 2`; direct `rg` rc is accepted only by `test "$rg_rc" -eq 1`, so rc 0 and rc 2 both fail.
- Embedded delegated runtime receipt: R4 §V records Composer polarity runs: normal `rg_rc=1`/gate 0; bogus `rg_rc=2`/gate fail; missing-file preassert fail.
- Diff receipt: Python `difflib.unified_diff(R3,R4)` showed only R3→R4 header/status metadata, Gate A replacement plus its polarity receipts, and appended `R4-CLOSURE`; no Gate B/C, scope, task, or acceptance drift.
- Finding closure: the R3 `rg ... | wc -l` fail-open counterexample is closed; all ticket-3 SPEC findings are resolved.

RECONCILE-STAMP APPROVED (p2debt-t3 SPEC R4, codex, 2026-07-11)

Verdict: APPROVE
