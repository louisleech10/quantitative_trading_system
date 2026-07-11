# IMPL REVIEW — p2debt-t3 (Composer adversarial)

**Reviewer**: Composer | **Date**: 2026-07-11 | **Input**: codex `handoffs/P2DEBT-T3-IMPL-RESULT-codex.md` + frozen `docs/P2DEBT_T3_TSCFIX_TODO.md`

## Scope (item 2)

`git diff --name-only -- frontend/src/` → **exactly 5 whitelisted test files** (no `types.ts`, no non-test `src/`):

- `run_lifecycle.test.tsx`
- `RunManagerPanel.batchDeleteWhole.test.tsx`
- `useFeatureFactory.batchDate.test.ts`
- `runExplorer.test.ts`
- `featureFactoryStore.test.ts`

Diff stat: `5 files changed, 9 insertions(+), 7 deletions(-)`.

## Diff audit (item 1) — no masking, no weakened asserts

| Check | Result |
|-------|--------|
| Gate A (`@ts-ignore` / `@ts-expect-error` / `as any` / `as unknown as`) | `GATE_A_RG_RC=1` → **0 hits** |
| `expect(` lines in unified diff | **0 modified** (only unchanged context adjacent to `runExplorer` cast removal) |
| Gate B sum | **87** (per-file: 20+10+4+9+44) |
| Gate C bodies (`rg -N expect` wc) | **87** lines |

### Per-error alignment vs production types

| # | Change | Production anchor | Masking? |
|---|--------|-------------------|----------|
| 1 | `error: null` on `FeatureTask` fixture | `types.ts:576` `error: string \| null` | No — required field |
| 2 | `completionQueue: [{ ...run, source: 'single' as const }]` | `types.ts:592-595` `CompletionQueueItem.source`; store `enqueueCompletion` default `'single'` (`featureFactoryStore.ts:706`) | No — matches existing expects L71/L84 |
| 3–4 | `response(..., payload: unknown)` | `Response.json()` accepts arbitrary JSON; call sites pass `RunInfo[]` / objects | No — widens helper, not bypass |
| 5–8 | `vi.fn(async (_url: string, init?: RequestInit) => …)` | Standard `fetch(url, init?)` | No — fixes `never` on `mock.calls[0][1]` |
| 9 | `const currentTask: FeatureTask = { …, error: null }`; **removed** `as FeatureTask` | Same `FeatureTask.error` | No — structural fix, stricter than cast |
| 10–11 | store `response` helper `payload: unknown` | same as #3–4 | No |

**Note (non-blocking):** `runExplorer.test.ts` retains pre-existing `as BatchTaskStatus` (L78/L97); out of ticket scope, no tsc errors.

## Independent re-run receipts (item 3)

```text
# tsc
cd frontend && npx tsc --noEmit 2>&1 | tee /tmp/p2debt-t3-review-tsc.log; echo TSC_EXIT=$?
→ TSC_EXIT=0; log wc -l=0; TSC_ERROR_COUNT=0 (rg -c "error TS" → rc=1 → 0)

# vitest (5 files)
cd frontend && npm test -- <五檔>
→ Test Files  5 passed (5); Tests  31 passed (31); VITEST_EXIT=0; duration 5.74s

# Gate B
rg -c '\bexpect\(' <五檔> | awk sum → GATE_B_SUM=87
```

Codex BLOCKED on delegated tsc — **orchestrator receipt now closes** `OPEN_PENDING=["p2debt-t3-orchestrator-tsc"]`.

## Findings

- **F1 (PASS):** All 11 errors addressed per TODO Task 1.1–1.5; zero forbidden tokens.
- **F2 (PASS):** No assertion deletion/weakening; fixture `source: 'single'` aligns store semantics with pre-existing expects.
- **F3 (PASS):** Scope confined to 5 test files; production types unchanged.
- **F4 (PASS):** Full-project `tsc --noEmit` clean; vitest 31/31 green.

**Residual:** None blocking commit for p2debt-t3 test-only scope.

Verdict: APPROVE
