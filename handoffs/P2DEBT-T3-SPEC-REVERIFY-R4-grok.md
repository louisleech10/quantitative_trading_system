# p2debt-t3 SPEC R4 — Grok re-confirm (post R1 APPROVE)

> Prior stamp: `handoffs/P2DEBT-T3-SPEC-REVIEW-grok.md` — **Verdict: APPROVE** on SPEC DRAFT **R1**  
> Re-reviewed draft: `handoffs/P2DEBT-T3-SPEC-DRAFT-R4.md`  
> Reviewer: Grok | Date: 2026-07-11 | Mode: **repo read-only** (only this file written)  
> task-id: `p2debt-t3`

---

## 1) Conceptual R1 → R4 delta (what changed vs what I approved)

| Layer | R1 (APPROVED) | R2 | R3 | R4 | Coverage / assertion impact |
|-------|---------------|----|----|----|-----------------------------|
| §RISK / 11 tsc / 5-file allowlist / Tasks 1.1–1.3 fix recipes | Present | Unchanged | Unchanged | Unchanged | **No loss** — same `error: null`, `source: 'single'`, `payload: unknown`, `RequestInit` mock arity |
| §C 防假綠 bans (`@ts-ignore` / `@ts-expect-error` / `as any` / double cast; no delete expects; behavior-only type fills) | Present (prose) | Same + executable gates | Same | Same | **Strengthened** (was prose-only in R1) |
| Scope gate | `git diff --name-only` only 5 test files | **pre-dirty + `comm -13` delta vs whitelist** (dirty-tree safe) | Same | Same | **No loss** — stricter, closes bad-baseline false fail (7 extra dirty paths) |
| Assertion baseline wording | R1 §V said「既有 **31 條斷言**」 | Corrected: **31 = vitest tests**; **87 = `expect()` sites** | Same + per-file baseline | Same | **No loss** — R1 mislabel fixed; actual assert surface **raised** to measurable 87 |
| Gate A (ban silent TS bypass) | Implicit post-diff grep | `rg … \| wc -l` expect 0 | Same pipe form | **`test -f` ×5 + direct `rg_rc` tri-state (1=PASS, 0/2=FAIL)** | **No loss** — closes fail-open on rg rc=2 |
| Gate B (expect count) | Implicit “keep 31 asserts” | Total **87** | Same | Same | **No loss** |
| Gate C (assertion behavior) | Prose only | Raw `rg -n expect` pre/post diff | **Leg1 per-file `rg -c` counts + Leg2 `rg -N` body diff**; amendment note required for count changes | Same | **No loss** — R3 avoids line-shift false FAIL on legal type-fill inserts |

**Stable under R1→R4 (spot-checked markers identical):** Task 1.1/1.2/1.3 tables; 11-row error inventory; allowlist of 5 files; ban on `types.ts` / non-test `src/`; vitest 31 + tsc→0 acceptance; RISK-HIT: none.

**Net judgment:** R2–R4 are **gate hardening only**. Nothing I approved in R1 was dropped or weakened. The only R1 “assertion” claim that changed was the **false equivalence** of “31 asserts” → correctly split into 31 tests / 87 expect sites — that is a **coverage gain**, not a loss.

---

## 2) Spot-run receipts (Grok 2026-07-11)

### Gate A — current tree (expect `rg_rc=1`, gate PASS)

```text
FACT-RECEIPT: for f in <5 whitelist>; do test -f "$f" || exit 2; done
→ existence: OK (5 files)

FACT-RECEIPT: rg -n '@ts-ignore|@ts-expect-error|\bas any\b|as unknown as' <5 whitelist files>
→ (no stdout)
→ rg_rc=1
→ test "$rg_rc" -eq 1 → gate_test_rc=0 (PASS)
```

Matches R4 embedded Polarity 1 and R4 design: no-match is **rc=1**, not “wc -l = 0”.

### Polarity 2 — synthetic hit (expect `rg_rc=0` = FAIL path)

```text
FACT-RECEIPT: echo '// @ts-ignore' > /tmp/p2debt-t3-gate-a-synth-grok.ts
rg -n '@ts-ignore|@ts-expect-error|\bas any\b|as unknown as' /tmp/p2debt-t3-gate-a-synth-grok.ts
→ 1:// @ts-ignore
→ synth_rg_rc=0 (FAIL/hit as designed)
```

### Polarity 3 — bogus path (expect `rg_rc=2` = FAIL path; tri-state not fail-open)

```text
FACT-RECEIPT: rg -n '…' /nonexistent/p2debt-t3-bogus.ts
→ rg: … No such file or directory
→ bogus_rg_rc=2
```

R4 `test "$rg_rc" -eq 1` correctly rejects both 0 and 2. (Existence pre-gate would also `exit 2` if a whitelist file vanished.)

### Gate B — expect site baseline (spot-check vs R4 claim 87)

```text
FACT-RECEIPT: rg -c '\bexpect\(' <5 whitelist> | python sum
→ run_lifecycle.test.tsx:20
→ RunManagerPanel.batchDeleteWhole.test.tsx:10
→ useFeatureFactory.batchDate.test.ts:4
→ runExplorer.test.ts:9
→ featureFactoryStore.test.ts:44
→ total 87
```

Per-file counts match R4 §V Gate C Leg1 baseline exactly.

---

## 3) Coverage / assertion-behavior vs R1 APPROVE

| R1 APPROVE pillar | Still in R4? | Evidence |
|-------------------|--------------|----------|
| Fix all 11 tsc errors test-side only | Yes | §A table + Tasks 1.1–1.3 unchanged |
| No production type / `types.ts` change | Yes | §C 禁止改 + RISK upgrade→BLOCK |
| No `@ts-ignore` / `@ts-expect-error` / `as any` / double cast | Yes + **executable Gate A tri-state** | Spot-run rc=1; polarity hit/bogus |
| No delete/weaken expects; behavior unchanged | Yes + **Gate B=87 + Gate C Leg1/Leg2** | Spot-run 87; R3 body-diff leg |
| Scope = only 5 test files | Yes + **pre-dirty delta** (stronger than R1) | §C/§V item 3 |
| tsc exit 0 + vitest 31 green | Yes | §V items 1–2; 31 clarified as tests not expects |

**No coverage loss. No assertion-behavior loss.** R2–R4 only close codex-found **false green / false red** holes in acceptance machinery.

---

## 4) Structured close

```
ASSUMPTIONS_VERIFIED: R1→R4 task/fix recipes stable; Gate A tri-state (rc 1/0/2) behaves as specified; Gate B total 87 + per-file 20/10/4/9/44; R1 "31 asserts" was mislabel corrected without dropping assert surface
TESTS_RUN: Gate A on 5 whitelist → rg_rc=1 gate PASS; polarity synth hit → rg_rc=0; polarity bogus → rg_rc=2; Gate B rg -c expect → total 87
FAILURES_SEEN: none (gates behaved as designed)
SCOPE_CHANGES: none (read-only reverify; wrote only this handoff)
NUMERIC_OR_SCHEMA_IMPACT: none
```

RECONCILE-STAMP APPROVED (p2debt-t3 SPEC R4, grok, 2026-07-11)

Verdict: APPROVE
