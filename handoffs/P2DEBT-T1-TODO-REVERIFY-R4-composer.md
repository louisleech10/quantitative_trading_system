# P2DEBT-T1 TODO R4 Composer re-verify
Task-id: p2debt-t1 | Date: 2026-07-11 | Reviewer: composer
Compared: `handoffs/P2DEBT-T1-TODO-DRAFT-R3.md` → `handoffs/P2DEBT-T1-TODO-DRAFT-R4.md`
Did NOT read: `handoffs/P2DEBT-T1-TODO-REVERIFY-R4-grok.md`

## R3 vs R4 diff summary (composer inspected)
`diff -u R3 R4` → **6 hunks only**; substantive delta = B3 comm-direction fix + diff hygiene; no task/oracle/implementation semantics changed.

| Location | R3 (bug) | R4 (fix) |
|----------|----------|----------|
| §0 L46 | `comm -23 pre post` | `comm -13 pre post \| sort -u` |
| Phase Gate scope L199 | `comm -23 … > delta` + direct `diff` | `comm -13 … \| sort -u > delta` + both sides `sort -u` before `diff` |
| Final §2 L228–232 | `comm -23`; single-file `diff` | `comm -13 \| sort -u`; sorted intermediate files |
| Footer | R3-CLOSURE claimed unobserved pass | R3-CLOSURE annotated honest; **R4-CLOSURE** added |
| New prose | — | R4 synthetic simulation receipt block (Final §2) |

**Unchanged (spot-checked):** Task 1.1–1.3 tables, §V 負例, 派工 prompt L70–76, 附錄修法表, baseline receipts, B1/B2/M1 closures, all pytest oracles.

**Line counts:** R3=271, R4=284 (+13 = comm/sort/receipt/honesty prose only).

## Root cause (R3 comm-direction bug)
R3 text says delta = "post 相對 pre 新增/變更路徑" but used `comm -23` (= lines **only in pre**, i.e. removed paths). Correct = `comm -13` (= lines **only in post**, i.e. added paths).

## EXP1 — comm direction minimal (pre={a,b}, post adds 4 whitelist)
```bash
printf '%s\n' a b | sort -u > /tmp/cmp-pre.txt
printf '%s\n' a b docs/VERIFY_GATE_SPEC.md tests/governance/test_verify_gate_b4.py \
  tests/governance/test_verify_gate_b5.py tests/governance/test_verify_gate_redteam.py | sort -u > /tmp/cmp-post.txt
comm -23 /tmp/cmp-pre.txt /tmp/cmp-post.txt > /tmp/cmp-delta-r3wrong.txt
comm -13 /tmp/cmp-pre.txt /tmp/cmp-post.txt | sort -u > /tmp/cmp-delta-r4correct.txt
```
- R3 `comm -23`: `wc -l` → **0** (empty — would reject correct impl)
- R4 `comm -13`: `wc -l` → **4**; contents = four whitelist paths ✓

## EXP2 — correct-impl counterexample (proves R3 blocker)
Same pre/post as EXP1; whitelist = four paths.
- R3 `comm -23` delta 0 lines → `diff -u whitelist delta` → **rc=1** (correct impl **cannot pass**)
- R4 `comm -13` delta 4 lines → `diff -u whitelist delta` → **rc=0** ✓

## EXP3 — R4 simulation pipeline replay (composer /tmp, matches R4 Final §2)
```bash
printf '%s\n' a b > /tmp/r4-pre4
printf '%s\n' docs/VERIFY_GATE_SPEC.md tests/governance/test_verify_gate_b4.py \
  tests/governance/test_verify_gate_b5.py tests/governance/test_verify_gate_redteam.py > /tmp/r4-white4
# bad baseline (post=pre)
cp /tmp/r4-pre4 /tmp/r4-badpost4
comm -13 /tmp/r4-pre4 /tmp/r4-badpost4 > /tmp/r4-baddelta4
diff -u /tmp/r4-white4 /tmp/r4-baddelta4  # rc=1; wc -l baddelta4 → 0
# good simulation (pre + 4 whitelist)
printf '%s\n' a b docs/VERIFY_GATE_SPEC.md tests/governance/test_verify_gate_b4.py \
  tests/governance/test_verify_gate_b5.py tests/governance/test_verify_gate_redteam.py | sort -u > /tmp/r4-simpost4
comm -13 /tmp/r4-pre4 /tmp/r4-simpost4 | sort -u > /tmp/r4-simdelta4
sort -u /tmp/r4-white4 > /tmp/r4-white4-sorted
diff -u /tmp/r4-white4-sorted /tmp/r4-simdelta4  # rc=0; wc -l simdelta4 → 4
```
| Case | delta lines | diff rc | Matches R4 doc |
|------|-------------|---------|------------------|
| bad (post=pre) | 0 | 1 | ✓ |
| good (pre+4) | 4 | 0 | ✓ |

## EXP4 — real repo bad baseline (no impl change; read-only git status)
```bash
git status --porcelain | awk '{print $NF}' | sort -u > /tmp/p2debt-t1-pre-dirty-composer.txt
cp … /tmp/p2debt-t1-post-dirty-composer.txt
comm -13 pre post | sort -u > delta
diff -u whitelist-sorted delta-sorted
```
- pre-dirty: **28** lines (dirty baseline present)
- delta: **0** lines; diff rc=**1** (honest bad-baseline; no false pass)

## Nothing-else-changed verdict
- Implementation tasks, test oracles, §V 負例, 派工 prompt, 附錄 — **identical**
- Only B3 scope-gate comm/diff mechanics + receipt/honesty prose differ
- No scripts/, momentum/, api/, data_cache/ touched by this review

ASSUMPTIONS_VERIFIED: comm -13 = post∖pre; R3 comm -23 blocks legitimate 4-file impl; R4 simulation rc semantics match documented receipts; non-comm TODO content unchanged.
TESTS_RUN: `diff -u R3 R4`; EXP1–4 commands above (all /tmp + read-only `git status`).
FAILURES_SEEN: none (R3 bug confirmed as design defect, not test flake).
SCOPE_CHANGES: none; only this output file written.
NUMERIC_OR_SCHEMA_IMPACT: none.

RECONCILE-STAMP APPROVED (p2debt-t1 TODO R4, composer, 2026-07-11)
Verdict: APPROVE
