# P2DEBT-T3 SPEC adversarial review (Grok)

> Draft under review: `handoffs/P2DEBT-T3-SPEC-DRAFT-R1.md` (Composer R1)  
> Reviewer: Grok | Date: 2026-07-11 | Mode: **read-only** (only this file written)  
> task-id: `p2debt-t3`

---

## 1) tsc baseline receipt (Grok 實跑)

**FACT-RECEIPT:** `cd frontend && npx tsc --noEmit 2>&1` → exit 1；`grep -c "error TS"` → **11**（Grok 2026-07-11）

| # | file:line (tsc) | TS codes | Draft row match? |
|---|-----------------|----------|------------------|
| 1 | `run_lifecycle.test.tsx:42` | TS2741 | YES |
| 2 | `run_lifecycle.test.tsx:88` | TS2741 | YES |
| 3 | `RunManagerPanel.batchDeleteWhole.test.tsx:102` | TS2345 | YES |
| 4 | `RunManagerPanel.batchDeleteWhole.test.tsx:170` | TS2345 | YES |
| 5–6 | `useFeatureFactory.batchDate.test.ts:55` | TS2493 + TS2339 | YES |
| 7–8 | `useFeatureFactory.batchDate.test.ts:75` | TS2493 + TS2339 | YES |
| 9 | `runExplorer.test.ts:51` | TS2352 | YES |
| 10 | `featureFactoryStore.test.ts:429` | TS2345 | YES |
| 11 | `featureFactoryStore.test.ts:539` | TS2345 | YES |

**Unique error files (5):** exact draft allowlist. No extra `error TS` outside these paths.  
**Draft enumeration accuracy:** count **11** + all **file:line** + codes match. No phantom / missing rows.

---

## 2) Deep dive ≥4 errors (test vs production type)

### Sample A — `#1` `run_lifecycle.test.tsx:42` / `FeatureTask.error`

- **Test:** `const task: FeatureTask = { task_id, status, progress, current_stage, completed_stages }` — omits `error`.
- **Production type:** `types.ts:570-587` — `error: string | null` **required**.
- **Production usage:** `useFeatureFactory.ts:178-184` constructs `FeatureTask` with explicit `error: null` after generate start.
- **Backend wire:** Pydantic `FeatureTaskStatusResponse.error: Optional[str] = None` (may be absent on wire). Frontend domain type still correctly requires the field after client-side object construction; production always fills it.
- **Judgment:** **test incomplete fixture**. Production type is intentional domain contract, not wrong. Fix `error: null` is correct. **Does not invalidate RISK-HIT: none.**

### Sample B — `#2` `run_lifecycle.test.tsx:88` / `CompletionQueueItem.source`

- **Test:** `setState({ completionQueue: [run] })` where `run` has identity + browse fields only — no `source`.
- **Production type:** `CompletionQueueItem extends RunIdentity { source: CompletionSource }` (`types.ts:594-596`); `CompletionSource = 'single' | 'batch'`.
- **Production usage:** `featureFactoryStore.ts:706-714` `enqueueCompletion(run, source = 'single')` always appends `{ ...run, source }`.
- **Same-file assertions (L70/L83)** already expect `{ ...run, source: 'single' }` — fixture at L88 is the inconsistency.
- **Judgment:** **test state illegal under production type**. Fix `{ ...run, source: 'single' as const }` aligns with store default. **Test-only.**

### Sample C — `#3/#4` + `#10/#11` local `response()` helper

- **Test helper:** `payload: Record<string, unknown>` in `RunManagerPanel.batchDeleteWhole.test.tsx:22` and `featureFactoryStore.test.ts:19`.
- **Call sites:** pass `RunInfo[]` / `[]` (never[]) for GET `/runs`.
- **Production:** `fetchRuns` → `await response.json() as RunInfo[]` (`featureFactoryStore.ts:569`) — API JSON is array, not object map.
- **Judgment:** helper signature too narrow for real endpoint shape. Draft fix `payload: unknown` (runtime `json: async () => payload` unchanged) is test-only and preserves behavior. **Not a production type defect.**

### Sample D — `#5–8` `useFeatureFactory.batchDate.test.ts:55/75` vi.fn arity

- **Test:** `vi.fn(async () => response(...))` zero-parameter implementation → `mock.calls[0]` typed as empty tuple → `[1]` is never → `.body` fails.
- **Production:** `fetch(url, init?)` second arg carries `RequestInit.body`; assertions check `start_date`/`end_date` in body.
- **Judgment:** mock signature under-specified. Draft `async (_url: string, init?: RequestInit) => …` restores correct call-tuple inference without changing expects. **Test-only.**

### Sample E (bonus) — `#9` `runExplorer.test.ts:51` `as FeatureTask`

- Object missing `error`; unsafe cast triggers TS2352 (overlap insufficient).
- `pickDefaultRun` only needs `status` + `run_identity` at runtime (`runExplorer.ts:96-99`); type still requires full `FeatureTask`.
- Draft: add `error: null`, use `const currentTask: FeatureTask = {…}`, **remove** `as FeatureTask` — stronger than cast-to-pass; anti-假綠 compliant.

**RISK-HIT hunt result:** No case found where the test is “more correct” and production type should change. **`RISK-HIT: none` stands.** Draft’s hard stop (if impl needs `types.ts` / non-test `src/` → BLOCK, new ticket) is correct.

---

## 3) 防假綠 clauses

| Clause in draft §C | Assessment |
|--------------------|------------|
| Ban `@ts-ignore` / `@ts-expect-error` / `as any` / double `as unknown as T` | Present and enforceable via post-impl `git diff` grep. |
| Ban delete/weaken existing `expect` | Present; proposed edits are fixture/signature only. |
| Behavior unchanged (fill fixtures / mock arity / helper type) | Matches deep-dive fixes; L88 source fill even improves type-faithfulness of existing L70/L83 expects. |
| Diff gate = only 5 test files | Matches tsc error surface. |

**No 假綠 hole** in the proposed fix directions (would fail if impl used ignore/any/assertion stripping — draft forbids that).

---

## 4) Acceptance commands executable

| Claim | Verification |
|-------|----------------|
| `"test": "vitest run"` | **FACT-RECEIPT:** `rg '"test"' frontend/package.json` → `"test": "vitest run"` |
| vitest include | **FACT-RECEIPT:** `frontend/vitest.config.ts` → `include: ['src/**/*.test.{ts,tsx}']` |
| `npm test -- --run <paths…>` | **FACT-RECEIPT (Grok):** `cd frontend && npm test -- --run src/lib/runExplorer.test.ts` → expands to `vitest run --run src/lib/runExplorer.test.ts` → **Test Files 1 passed (1), Tests 7 passed (7)**, exit 0 |
| `npx tsc --noEmit` gate | Confirmed executable; currently 11 errors (pre-fix baseline) |
| Baseline 31 tests | Draft claim; Grok did **not** re-run full 5-file suite (out of scope for SPEC review; command shape validated). Accept as Composer receipt pending impl re-verify. |

**Nit (non-blocking):** extra `--run` after `vitest run` is redundant but **works** under vitest 4.1.5.

---

## 5) Findings summary

| ID | Severity | Finding |
|----|----------|---------|
| F1 | — | tsc 11 / 5 files / all file:line match draft — **PASS** |
| F2 | — | ≥4 root-cause classes verified test-side; no production-type inversion — **PASS** |
| F3 | — | 防假綠 bans + assertion-preservation adequate — **PASS** |
| F4 | — | Acceptance commands executable vs package.json; sample vitest path green — **PASS** |
| N1 | non-blocking | `npm test -- --run …` has redundant `--run`; keep as-is or simplify to path filters only at formalization. |
| N2 | non-blocking | Backend wire `error` Optional vs FE required `error: string \| null` is intentional client domain (prod always sets `error: null`); do **not** open production type change under this ticket. |

**BLOCK-class findings:** none.

---

## 6) Structured close

```
ASSUMPTIONS_VERIFIED: tsc 11 errors + file:line; FeatureTask.error/CompletionQueueItem.source required in types.ts; fetchRuns casts RunInfo[]; enqueueCompletion default source='single'; useFeatureFactory sets error:null; package.json test script; vitest path command runs
TESTS_RUN: cd frontend && npx tsc --noEmit → 11 error TS (exit 1); npm test -- --run src/lib/runExplorer.test.ts → 7 passed
FAILURES_SEEN: none in review
SCOPE_CHANGES: none (read-only review; wrote only this handoff)
NUMERIC_OR_SCHEMA_IMPACT: none
```

Verdict: APPROVE
