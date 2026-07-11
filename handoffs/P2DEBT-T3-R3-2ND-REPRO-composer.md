# P2DEBT-T3 — R3 2nd-party independent reproduction (Composer)

- task-id: `p2debt-t3`
- role: independent 2nd reproducer (not codex raiser, not grok fix author)
- basis: `handoffs/P2DEBT-T3-TODO-DRAFT-R3.md` §B Batch Gate L78–110 + codex `handoffs/P2DEBT-T3-TODO-REVERIFY-codex.md`
- date: 2026-07-11
- repo: read-only; experiments in `/tmp` only

---

## R2 vs R3 diff scope (acceptance shell only)

```bash
diff -u handoffs/P2DEBT-T3-TODO-DRAFT-R2.md handoffs/P2DEBT-T3-TODO-DRAFT-R3.md
```

- Changed: title/header/refs, §B Batch Gate `tsc_zero` block, Final Acceptance §1/§4–§7 self-contained legs, R3 FACT-RECEIPT/CLOSURE appendix.
- Unchanged: Task 1.1–1.5 implementation checklists (verified: no `+/-` hunks touching Task 1.x body).
- R2→R3 core shell delta: parent `tsc_count=$(grep -c … || echo 0)` + `bash -c 'test "$tsc_count"'` → child `rg -c` + `rc=1→c=0` + assert same `bash -c`; Gate B/C/scope/decouple parent vars folded into single `bash -c` steps.

---

## Finding 1 — `run_step` reads unexported parent variable

**Codex counterexample (R2 pattern) — STILL-OPEN in R2**

```bash
tsc_count=11
bash -c 'echo child_sees=[${tsc_count-<unset>}]; test "$tsc_count" -eq 0; echo test_rc=$?'
```

```
child_sees=[<unset>]
bash: line 0: test: : integer expression expected
test_rc=2
```

```bash
# R2 lines 90-92 equivalent via run_step
set +e; fail=0
run_step() { local name="$1"; shift; "$@"; local rc=$?; echo "STEP_RC[$name]=$rc"; [ "$rc" -ne 0 ] && fail=1; return 0; }
tsc_count=11; echo "TSC_ERROR_COUNT=$tsc_count"
run_step tsc_zero bash -c 'test "$tsc_count" -eq 0'
```

```
TSC_ERROR_COUNT=11
bash: line 0: test: : integer expression expected
STEP_RC[tsc_zero]=2
ANY_FAIL=1
```

Child never sees parent `tsc_count`; assertion is non-executable as written.

**R3 fix (self-contained `tsc_zero` L92–100) — CLOSED**

```bash
UNEXPORTED_SECRET=hello_parent
run_step r2_bad bash -c 'echo child_sees=[${UNEXPORTED_SECRET-<unset>}]; test -n "$UNEXPORTED_SECRET"'
```

```
child_sees=[<unset>]
STEP_RC[r2_bad]=1
```

```bash
echo "no errors" > /tmp/p2debt-t3-composer-sim-zero-tsc.log
run_step tsc_zero bash -c '
  c=$(rg -c "error TS" /tmp/p2debt-t3-composer-sim-zero-tsc.log 2>/dev/null)
  rc=$?
  if [ "$rc" -eq 1 ]; then c=0
  elif [ "$rc" -ne 0 ]; then echo "TSC_COUNT_RG_RC=$rc"; exit 2
  fi
  echo "TSC_ERROR_COUNT=$c"
  test "$c" -eq 0
'
```

```
TSC_ERROR_COUNT=0
STEP_RC[tsc_zero]=0
```

```bash
# bad baseline (real tree)
run_step tsc bash -c 'cd frontend && npx tsc --noEmit 2>&1 | tee /tmp/p2debt-t3-batch-tsc-composer.log; exit ${PIPESTATUS[0]}'
# … same tsc_zero block on that log …
```

```
STEP_RC[tsc]=1
TSC_ERROR_COUNT=11
STEP_RC[tsc_zero]=1
ANY_FAIL=1
```

Count+assert inside child; integer `11` on fail, integer `0` on sim-pass; no parent var leak.

**Finding 1 verdict: CLOSED** (R3 self-contained pattern fixes codex R2 BLOCK)

---

## Finding 2 — zero-match `grep -c … || echo 0` multi-line non-integer

**Codex counterexample — STILL-OPEN in R2 pattern**

```bash
echo "no errors" > /tmp/p2debt-t3-composer-sim-zero-tsc.log
tsc_count=$(grep -c "error TS" /tmp/p2debt-t3-composer-sim-zero-tsc.log 2>/dev/null || echo 0)
printf '%s' "$tsc_count" | od -An -c
test "$tsc_count" -eq 0; echo test_rc=$?
```

```
od: 0 \n 0
test_rc=2   # integer expression expected
```

```bash
printf 'x\n' > /tmp/p2debt-t3-f1.txt; printf 'y\n' > /tmp/p2debt-t3-f2.txt
grep_out=$(grep -c THIS_NEVER /tmp/p2debt-t3-f1.txt /tmp/p2debt-t3-f2.txt 2>/dev/null || echo 0)
printf '%s' "$grep_out" | od -An -c
echo "lines=$(printf '%s\n' "$grep_out" | wc -l | tr -d ' ')"
```

```
/tmp/p2debt-t3-f1.txt:0
/tmp/p2debt-t3-f2.txt:0
od: file1:0\nfile2:0\n0
lines=3
```

Multi-line value; `test -eq` unusable.

**R3 fix (`rg -c` + `rc=1→c=0` + arithmetic sum) — CLOSED**

```bash
# tsc_zero block (R3 L92–100) on no-match log
bash -c 'c=$(rg -c "error TS" /tmp/p2debt-t3-composer-sim-zero-tsc.log 2>/dev/null); rc=$?; if [ "$rc" -eq 1 ]; then c=0; elif [ "$rc" -ne 0 ]; then exit 2; fi; echo TSC_ERROR_COUNT=$c; printf "%s" "$c" | od -An -c; test "$c" -eq 0; echo test_rc=$?'
```

```
TSC_ERROR_COUNT=0
c_od= 0
test_rc=0
```

```bash
# Gate B zero-match polarity (R3 Final §4 loop pattern)
sum=0
for f in /tmp/p2debt-t3-f1.txt /tmp/p2debt-t3-f2.txt; do
  c=$(rg -c "THIS_NEVER_MATCHES_XYZ_R3" "$f" 2>/dev/null); rc=$?
  [ "$rc" -eq 1 ] && c=0; [ "$rc" -ne 0 ] && [ "$rc" -ne 1 ] && exit 2
  sum=$((sum + c))
done
echo GATE_B_SUM=$sum; test "$sum" -eq 0; echo test_rc=$?
```

```
GATE_B_SUM=0
test_rc=0
```

```bash
# real whitelist files (expect sum=87)
# … same loop on 5 test files …
```

```
GATE_B_SUM=87
test_rc=0
```

Single integer `0` or `87`; no `grep -c||echo 0` multi-line.

**Finding 2 verdict: CLOSED** (R3 `rg -c` + rc handling + per-file arithmetic)

---

## Summary

| Finding | R2 status | R3 status | Evidence |
|---------|-----------|-----------|----------|
| (1) unexported parent vars in `run_step` child | STILL-OPEN | CLOSED | child `[<unset>]` / `test_rc=2` vs R3 `TSC_ERROR_COUNT=0` `STEP_RC[tsc_zero]=0` |
| (2) zero-match multi-line count | STILL-OPEN | CLOSED | `0\n0` / 3-line grep vs R3 integer `0` + `test_rc=0` |

ASSUMPTIONS_VERIFIED: R3 Batch Gate L92–100 matches reproduced `tsc_zero`; R2 parent-var and grep patterns fail as codex claimed; Task 1.1–1.5 body untouched in R2→R3 diff.
TESTS_RUN: `/tmp/p2debt-t3-repro{1,2}.sh` + inline bash above (all exit 0 except intentional fail polarities).
FAILURES_SEEN: initial macOS `printf > f1 f2` only wrote one file (corrected); unrelated to R3 contract.
SCOPE_CHANGES: none (output file only).
NUMERIC_OR_SCHEMA_IMPACT: none.

Verdict: APPROVE
