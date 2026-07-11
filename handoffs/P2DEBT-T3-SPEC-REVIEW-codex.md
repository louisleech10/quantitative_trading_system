# P2DEBT-T3 SPEC adversarial review — Codex

- task-id: `p2debt-t3`; reviewed only `handoffs/P2DEBT-T3-SPEC-DRAFT-R1.md`; Grok review content was not read.
- FACT-RECEIPT: `cd frontend && npx tsc --noEmit` → exit 1 in 2.63s; exactly 11 diagnostics in 5 files.
- Enumeration: `run_lifecycle.test.tsx:42,88`; `RunManagerPanel.batchDeleteWhole.test.tsx:102,170`; `useFeatureFactory.batchDate.test.ts:55` (2), `:75` (2); `runExplorer.test.ts:51`; `featureFactoryStore.test.ts:429,539`.
- Draft enumeration matches the independent compiler output exactly; no command exceeded 60s and no ticket-4 delegation occurred.
- ROOT-CAUSE 1: `run_lifecycle:42` and `runExplorer:51` are stale fixtures. `types.ts:570-587` requires nullable `error`; backend model `feature_factory_models.py:85-100` and service `feature_factory_service.py:675-688` always emit the field. Production type is correct.
- ROOT-CAUSE 2: `run_lifecycle:88` bypasses `enqueueCompletion`. `types.ts:591-596`, store `:706-713`, and `RunRetentionDialog.tsx:18-20` prove `source` is the required single/batch discriminator. Adding `source: 'single'` preserves the tested modal path.
- ROOT-CAUSE 3: the two `batchDeleteWhole` and two store errors are over-narrow local helpers. API route `feature_factory.py:60-62` declares `response_model=list[RunInfo]`; store `:564-570` consumes `RunInfo[]`. `payload: unknown` is the correct test-helper widening.
- ROOT-CAUSE 4: `batchDate:55,75` result from zero-argument `vi.fn` tuple inference. Production `requestJson` calls `fetch(url, RequestInit)` (`useFeatureFactory.ts:29-36`) and batch passes a POST body (`:409-415`); typing mock parameters fixes inference without changing assertions.
- RISK-HIT audit: no evidence that a production type is wrong; `RISK-HIT: none` remains supported if implementation stays within the five tests.
- FACT-RECEIPT: targeted command from §V ran in 2.73s → `Test Files 5 passed (5)`, `Tests 31 passed (31)`; `package.json` confirms `test = vitest run`, so the command is real (duplicate `--run` is accepted by Vitest).
- BLOCKER 1 (anti-fake-green): §V says “31 assertions,” but independent `rg -c '\bexpect\('` totals 87 (20+10+4+9+44); 31 is the test count. The spec has no executable assertion-preservation gate.
- Required correction: distinguish `31 tests` from `87 current expect() sites` and add a diff-based gate proving no `expect` line/expected value changed; test-count equality alone cannot detect weakened assertions.
- BLOCKER 2 (scope acceptance): §V requires global `git diff --name-only` to contain only the five tests plus artifacts, but the pre-existing worktree currently has 7 unrelated tracked changes. That acceptance cannot pass even with a perfectly scoped implementation.
- Required correction: bind scope verification to the orchestrator preflight snapshot, or at minimum inspect `git diff --name-only -- frontend/src` against the five-file allowlist; retain the global delta as an attributed pre/post snapshot, not an absolute-clean-worktree assertion.
- Defense gate should be an explicit executable negative scan over the five files for `@ts-ignore`, `@ts-expect-error`, `as any`, and `as unknown as`; current independent scan found none of those patterns.
- NUMERIC_OR_SCHEMA_IMPACT: none; review was read-only except this required artifact; `data_cache/` untouched.
- TESTS_RUN: `npx tsc --noEmit` = expected FAIL, 11/11 enumerated; targeted Vitest = PASS, 31/31.
- FAILURES_SEEN: only the 11 baseline TypeScript errors under review.
- SCOPE_CHANGES: none proposed beyond correcting the SPEC acceptance text.

Verdict: BLOCK — anti-fake-green assertion receipt is false/incomplete, and the global dirty-worktree scope command is not executable as an acceptance gate
