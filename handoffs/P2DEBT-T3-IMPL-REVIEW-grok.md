# IMPL REVIEW — p2debt-t3 (Grok adversarial)

**Reviewer**: Grok | **Date**: 2026-07-11 | **Mode**: read-only repo (output-only this file)
**Impl claim**: handoffs/P2DEBT-T3-IMPL-RESULT-codex.md (vitest/gates PASS; tsc DELEGATED)
**Chair claim**: tsc=0 independently confirmed (re-verified below)
**Did not read**: composer review (per brief)

---

## (1) Diff adversarial — Gate A / expect / type alignment

### Diff scope (test files only)

```text
cmd: git diff --stat -- 'frontend/src/**/*.test.ts' 'frontend/src/**/*.test.tsx'
result:
  RunManagerPanel.batchDeleteWhole.test.tsx | 2 +-
  run_lifecycle.test.tsx                    | 3 ++-
  useFeatureFactory.batchDate.test.ts       | 4 ++--
  runExplorer.test.ts                       | 5 +++--
  featureFactoryStore.test.ts               | 2 +-
  5 files changed, 9 insertions(+), 7 deletions(-)
```

### Per-error fix vs production types (not masking)

| # | File / change | Production type (types.ts / store) | Verdict |
|---|---------------|------------------------------------|---------|
| 1 | `run_lifecycle`: `error: null` on `FeatureTask` | `FeatureTask.error: string \| null` (types.ts:576, required) | ALIGN |
| 2 | `completionQueue: [{ ...run, source: 'single' as const }]` | `CompletionQueueItem.source: CompletionSource`; `enqueueCompletion` default `'single'` | ALIGN |
| 3–4 | `response(..., payload: unknown)` batchDelete | Mock only; arrays (`RunInfo[]`) were illegal under `Record<string, unknown>` | ALIGN |
| 5–8 | `vi.fn(async (_url: string, init?: RequestInit) => …)` | Real `fetch(input, init?)`; unblocks `mock.calls[0][1].body` without cast | ALIGN |
| 9 | `const currentTask: FeatureTask = { … error: null }`; remove `as FeatureTask` | Structural complete task; cast removal strengthens check | ALIGN |
| 10–11 | store `response` payload → `unknown` | Same as 3–4; empty `[]` mock legal | ALIGN |

**Note (non-blocking)**: `as const` on `'single'` is a literal-narrowing assertion, **not** Gate A banned (`@ts-ignore` / `@ts-expect-error` / `as any` / `as unknown as`). Matches TODO Task 1.1.2.

### Gate A — forbidden silence tokens → 0

```text
cmd: rg -n '@ts-ignore|@ts-expect-error|\bas any\b|as unknown as' <5 whitelist files>
result: (no matches)
rg_rc=1  → PASS (polarity: 1=no hit)
```

### Expect integrity (Gate B + C + skip)

```text
Gate B per-file (worktree):
  run_lifecycle.test.tsx:20
  RunManagerPanel.batchDeleteWhole.test.tsx:10
  useFeatureFactory.batchDate.test.ts:4
  runExplorer.test.ts:9
  featureFactoryStore.test.ts:44
GATE_B_SUM=87  (baseline 87)

Gate C Leg1 (HEAD counts vs worktree):
  diff -u pre-expect-counts post-expect-counts → GATE_C_LEG1_RC=0

Gate C Leg2 (normalized expect bodies, path/indent stripped):
  pre=87 post=87; GATE_C_LEG2_NORM_RC=0

git diff expect lines:
  git diff -U0 -- <5 files> | rg '^[+-].*expect\(' → NO_EXPECT_LINES_IN_DIFF

skip/todo:
  rg '\.skip\(|it\.todo|describe\.skip|test\.skip|xit\(|xdescribe\(' → skip_rg_rc=1 (none)
```

**Finding**: no `expect(...)` added/removed/weakened; assertion bodies byte-stable vs HEAD; no skip/todo masking.

---

## (2) Scope — only 5 whitelist tests; no production src

```text
cmd: git diff --name-only -- frontend/src/
result (all under frontend/src):
  frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx
  frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx
  frontend/src/hooks/useFeatureFactory.batchDate.test.ts
  frontend/src/lib/runExplorer.test.ts
  frontend/src/store/featureFactoryStore.test.ts

cmd: git diff --name-only -- frontend/src/ | rg -v '\.test\.(ts|tsx)$'
result: (empty) — zero non-test frontend/src changes

cmd: git status --porcelain -- frontend/src/lib/types.ts
result: (clean / no types.ts in diff)
```

**Note (context, not T3 defect)**: worktree has other dirty paths (T2 hermetic, golden, HANDOFF, etc.). **T3 frontend implementation surface** is exactly the five whitelist tests. No `types.ts` / non-test `src/` in T3 diff.

---

## (3) Acceptance re-run (independent receipts)

### tsc → 0

```text
cmd: cd frontend && npx tsc --noEmit; echo TSC_EXIT=$?
result: TSC_EXIT=0

cmd: cd frontend && npx tsc --noEmit 2>&1 | grep -c "error TS"
result: 0
(GREP_C_EXIT=1 is grep no-match; count printed is 0)

log: /tmp/p2debt-t3-review-tsc-grok.log (warnings only; no error TS lines)
TSC_ERROR_COUNT=0
```

Chair claim of tsc=0 **reproduced** by this review.

### vitest 5 files / 31 tests

```text
cmd: cd frontend && npm test -- \
  src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
  src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
  src/hooks/useFeatureFactory.batchDate.test.ts \
  src/lib/runExplorer.test.ts \
  src/store/featureFactoryStore.test.ts
result:
  Test Files  5 passed (5)
  Tests  31 passed (31)
  Duration  6.03s
  vitest_rc=0
log: /tmp/p2debt-t3-review-vitest-grok.log
```

---

## Findings summary

| ID | Severity | Finding | Disposition |
|----|----------|---------|-------------|
| F1 | none | Gate A clean; no silence casts | PASS |
| F2 | none | expect count 87; bodies unchanged; no skip | PASS |
| F3 | none | All 11 fixes align to real production types / fetch signatures | PASS |
| F4 | none | Frontend src delta = 5 whitelist tests only; types.ts untouched | PASS |
| F5 | none | tsc=0 + vitest 5/31 re-run PASS | PASS |
| F6 | info | Impl RESULT marked tsc DELEGATED; chair + this review close the gap | non-blocking |
| F7 | info | `as const` present (allowed; not Gate A) | non-blocking |

**Blocking findings**: none

---

## Structured close

```
ASSUMPTIONS_VERIFIED: FeatureTask.error required null; CompletionQueueItem.source; response unknown for arrays; fetch mock arity; no expect/assertion body drift vs HEAD
TESTS_RUN: npx tsc --noEmit → TSC_EXIT=0 / error TS count 0; npm test -- <5 files> → 5 passed / 31 passed
FAILURES_SEEN: none
SCOPE_CHANGES: none for T3 surface (repo has unrelated dirty T2/docs; not in frontend/src non-test)
NUMERIC_OR_SCHEMA_IMPACT: none (test fixture/helper typing only)
```

Verdict: APPROVE
