# P2DEBT-T3 TODO R1 — Adversarial Review (grok)

> **Against frozen SPEC**: `handoffs/P2DEBT-T3-SPEC-DRAFT-R4.md`  
> **TODO under review**: `handoffs/P2DEBT-T3-TODO-DRAFT-R1.md`  
> **Reviewer**: grok　|　**Date**: 2026-07-11　|　**Mode**: repo read-only except this file  
> **Did not read**: any codex TODO review artifact

---

## Verdict: APPROVE

RECONCILE-STAMP APPROVED (p2debt-t3 TODO R1, grok, 2026-07-11)

---

## (1) Coverage — 11 errors → tasks + gates

| SPEC item | TODO mapping | Exact fix present? | Status |
|-----------|--------------|--------------------|--------|
| #1 `run_lifecycle:42` TS2741 missing `error` | Task 1.1.1 `error: null` | Yes | PASS |
| #2 `run_lifecycle:88` TS2741 missing `source` | Task 1.1.2 `{ ...run, source: 'single' as const }` | Yes | PASS |
| #3–#4 `batchDeleteWhole:102,170` TS2345 | Task 1.3.1 `payload: unknown` | Yes | PASS |
| #5–#8 `batchDate:55,75` TS2493/TS2339 | Task 1.5.1–1.5.2 mock `(_url, init?)` | Yes | PASS |
| #9 `runExplorer:51` TS2352 | Task 1.2.1 `error: null` + remove `as FeatureTask` | Yes | PASS |
| #10–#11 `featureFactoryStore:429,539` TS2345 | Task 1.4.1 `payload: unknown` | Yes | PASS |
| Gate A `rg_rc` tri-state + `test -f` | Task 2.1 full script | Matches SPEC R4 | PASS |
| Gate B sum 87 | Task 2.2 awk sum | Matches | PASS |
| Gate C Leg1 per-file counts pre/post | Task 2.3 Leg1 | Matches | PASS |
| Gate C Leg2 `rg -N` body diff | Task 2.3 Leg2 (+ comment for post) | Present | PASS* |
| scope `comm -13` pre-dirty | Task 3.1 | Matches | PASS |
| Final Acceptance tsc + vitest 31 | Final §1–§2 | Matches | PASS |
| §C forbid `@ts-ignore`/`types.ts`/non-test | §0 + Final 禁止事項 | Matches | PASS |

\*Leg2 post-capture is comment-only (see MINOR-2); mechanics and oracle not weakened.

**Appendix 11-error table** (TODO L449–461) matches SPEC §A inventory and Task IDs 1.1.1–1.5.2.

**SPEC Task renumbering**: SPEC §P 1.1/1.2/1.3 → TODO splits by file into 1.1–1.5; coverage index table documents the bijection. No orphan errors.

---

## (2) Spot-run receipts (read-only; grok 2026-07-11)

### R1 — tsc baseline inventory (11 errors, 5 files)

```text
VERIFY: cd frontend && npx tsc --noEmit 2>&1 | grep -c "error TS"
→ 11

VERIFY: same | rg "error TS" (file:line summary)
→ run_lifecycle.test.tsx(42) TS2741 error missing
→ run_lifecycle.test.tsx(88) TS2741 source missing
→ RunManagerPanel.batchDeleteWhole.test.tsx(102,170) TS2345 RunInfo[] vs Record
→ useFeatureFactory.batchDate.test.ts(55,75) TS2493+TS2339 mock.calls[0][1]
→ runExplorer.test.ts(51) TS2352 as FeatureTask / error missing
→ featureFactoryStore.test.ts(429,539) TS2345 never[] vs Record
```

Per-file error line counts (pipe `tsc` once): `run_lifecycle=2`, `batchDeleteWhole=2`, `batchDate=4`, `runExplorer=1`, `featureFactoryStore.test=2` — matches TODO task-closure baselines.

### R2 — Gate A tri-state polarity

```text
VERIFY: test -f five whitelist files → all exist
VERIFY: rg -n '@ts-ignore|@ts-expect-error|\bas any\b|as unknown as' <five files>
→ rg_rc=1 ; test "$rg_rc" -eq 1 → gate_a_exit=0 PASS (Polarity 1)

VERIFY: echo '// @ts-ignore' > /tmp/p2debt-t3-gate-a-synth-grok.ts
         rg -n '…' /tmp/p2debt-t3-gate-a-synth-grok.ts
→ 1:// @ts-ignore ; polarity2_rg_rc=0 (hit = FAIL) PASS polarity

VERIFY: rg -n '…' /nonexistent/p2debt-t3-bogus.ts
→ stderr No such file… ; polarity3_clean_rc=2 PASS polarity
```

**Note**: piping `rg … 2>&1 | head` masks `rg_rc` (shell sees head’s rc). TODO Task 2.1 correctly forbids pipe/`wc -l` and captures `rg_rc=$?` directly — aligned with SPEC R4 fail-open fix.

### R3 — Gate B / Gate C counts

```text
VERIFY: rg -c '\bexpect\(' <five files> | awk -F: '{s+=$2} END {print s}'
→ TOTAL=87
per-file (sorted):
  RunManagerPanel.batchDeleteWhole.test.tsx:10
  run_lifecycle.test.tsx:20
  useFeatureFactory.batchDate.test.ts:4
  runExplorer.test.ts:9
  featureFactoryStore.test.ts:44
→ matches SPEC + TODO baselines (20+10+4+9+44=87)

VERIFY: rg -N '\bexpect\(' <five> | wc -l
→ 87 (Leg2 body line count)
```

### R4 — scope gate `comm -13` polarity

```text
VERIFY: git status --porcelain | awk '{print $NF}' | sort -u > pre
→ pre_dirty_lines=33 (tree-local; SPEC receipt was 15 — dirty drift OK)
VERIFY: whitelist ∩ pre-dirty → 0 (five test files not pre-dirty → cold-start scope executable)
VERIFY: bad baseline post=pre → delta 0 lines; diff whitelist vs delta → bad_diff_rc=1
VERIFY: sim-post = pre ∪ whitelist → sim_delta_lines=5; diff whitelist vs sim-delta → sim_diff_rc=0
```

### R5 — line-anchor ground truth (fixture vs TODO exact fixes)

| Anchor | On-disk | TODO claim | Match? |
|--------|---------|------------|--------|
| `task: FeatureTask` missing `error` | L42–48 | 1.1.1 L42 | Yes |
| `completionQueue: [run]` | L88 | 1.1.2 L88 | Yes |
| `response(..., Record<string, unknown>)` batchDelete | L22 | 1.3.1 L22 | Yes |
| `response(200, allRuns\|activeOnly)` | L102, L170 | call sites | Yes |
| store `response` helper | L19 | 1.4.1 L19 | Yes |
| store `response(200, [])` | L429, L539 | #10–#11 | Yes |
| `as FeatureTask` runExplorer | L51–58 | 1.2.1 | Yes |
| batchDate `vi.fn(async () =>` | **L39**, **L61** | 1.5.1 claims **L43–45** | **Line off (MINOR-1)** |
| `types.ts` FeatureTask.error / CompletionQueueItem.source | L576 / L595 | §0 / Task inputs | Yes |

---

## (3) Oracle weakening hunt vs SPEC R4

| Oracle | SPEC | TODO | Weakened? |
|--------|------|------|-----------|
| tsc clear | exit 0 + `error TS` count 0 (not hardcoded 11) | Final §1 both | No |
| vitest | 31 tests / 5 files | Batch Gate + Final §2 | No |
| Gate A | `test -f` + `rg_rc` 1/0/2; ban `\| wc -l` | Task 2.1 identical | No |
| Gate B | sum 87 | Task 2.2 | No |
| Gate C Leg1 | per-file `rg -c` pre/post `diff` rc=0 | Task 2.3 | No |
| Gate C Leg2 | `rg -N` body diff / reviewer | Task 2.3 | No (script slightly thinner) |
| Gate C amendment | count change needs SPEC note | Task 2.3 point 3 | No |
| scope | `comm -13` delta == whitelist sorted | Task 3.1 | No |
| anti-bypass | no `@ts-ignore` / `@ts-expect-error` / `as any` / `as unknown as` | §0 + Gate A | No |
| no assert delete | expect count stable | Gate B+C | No |
| production freeze | no `types.ts` / non-test `src/` | §0 + 不可做 | No |

**No oracle weakening found.** Extra Final §5 decoupling `grep -r "from api\." momentum/` is strengthening, not dilution.

---

## (4) Cold-start executability

| Check | Result |
|-------|--------|
| §0 alone states whitelist + forbids + upgrade BLOCK | Yes |
| Each Task: file + exact edit + verify cmd | Yes (B1) |
| Batch topology B1 fix → B2 gates | Yes; five files independent |
| Pre-dirty capture timing | Task 3.1 + §0 say 派工前; Final §4 points Task 3.1 |
| Whitelist currently clean of pre-dirty | Yes (intersection 0) — scope gate can green after real edit |
| Dispatch prompt copy-paste | Present for B1 |
| Claims “不必回讀 SPEC” | Substantively true for B1; Gate Leg2 post relies on comment pattern (MINOR-2) |

---

## Findings

### BLOCKING
**None.**

### MINOR-1 — Task 1.5.1 line anchor off by ~4 lines  
- **Evidence**: TODO claims `L43–45` for dated `vi.fn`; on-disk `vi.fn(async () => {` is **L39–41** (L43 blank, L44 `renderHook`). L61 second mock is correct.  
- **RECHECK**: `rg -n "vi\.fn\(async" frontend/src/hooks/useFeatureFactory.batchDate.test.ts`  
- **Impact**: brief cold-start friction; error lines L55/L75 and signature text still sufficient.  
- **Fail mode**: executor edits wrong lines briefly; not silent wrong fix.  
- **Fix (optional R2)**: retarget 1.5.1 to L39–41; keep multi-line form in pseudo-diff.

### MINOR-2 — Gate C Leg2 post script not fully expanded  
- **Evidence**: Task 2.3 executable block captures only **pre** bodies; post + `diff` is comment (`# 完工後 diff pre vs post bodies`). SPEC §V has full post block.  
- **Impact**: cold-start “不必回讀 SPEC” slightly oversold for Leg2 only. Leg1 full; Final §3 names the contract.  
- **Fail mode**: forget post body snapshot → cannot auto-diff Leg2 (reviewer leg still available).  
- **Fix (optional)**: paste SPEC post-body commands into Task 2.3.

### MINOR-3 — Task-closure `rg -c … → 0` print semantics  
- **Evidence**: TODO expects `rg -c "run_lifecycle" → 0`. Spot-run: `rg -c` with zero matches prints **empty** and exits **1** (not digit `0`). `grep -c` prints `0` with exit 1.  
- **RECHECK**: `printf 'a\n' | rg -c 'nomatch'; echo rc=$?`  
- **Impact**: fail-**closed** (safe); under `set -e` green tsc may look like shell failure. SPEC uses “0 行” (empty) for same checks — slightly clearer.  
- **Fix (optional)**: prefer `rg "run_lifecycle" → empty` or `grep -c` + document exit-1-on-zero.

### NON-FINDING (inherited, not TODO regression)
- Final/`grep -c "error TS"` exit 1 when count is 0 — same pattern in SPEC; Final also checks `tsc_rc=0` first.
- pre-dirty line count drift (SPEC 15 / TODO 30 / now 33) is environment truth, not a false oracle.

### Categories with no issue
1. 矛盾/互斥：無（SPEC 1.1–1.3 ↔ TODO 1.1–1.5 已追溯）  
2. 漏項：無（11/11 + A/B/C + scope + Final）  
3. 不可測驗收：無（命令+預期 rc/計數）  
4–7 quant/OOM/cache：N/A（test-only TS）  
8. API/型別：修法對齊 `types.ts` 必填欄；禁改生產型別  
9. 測試品質：禁刪弱 expect；31 tests 基線保留  
10. Agent 可執行：有序清單+不可做+Phase Gate  

---

## 被當成事實的未驗證假設

| Claim | Fact or assumption? | This review |
|-------|---------------------|-------------|
| 11 tsc errors on five files | Fact (Composer receipt) | **Re-verified** → 11 |
| Gate B = 87 | Fact | **Re-verified** → 87 |
| Gate A clean on tree | Fact | **Re-verified** rg_rc=1 |
| scope bad/synth polarity | Fact in SPEC/TODO | **Re-verified** rc 1 / 0 |
| vitest 31 still green with tsc red | Fact (Composer) | Not re-run this review (cost); TODO+SPEC consistent; not sole stamp basis |
| RISK-HIT none / test-only | Fact after inventory | Confirmed errors are fixture/helper only |

---

## Summary for chair

TODO R1 is a faithful, cold-start-usable decomposition of SPEC R4: all 11 diagnostics have exact fixes, Gate A uses fail-closed `rg_rc` (not `wc -l`), Gate B/C oracles preserve 87 / per-file counts / body review, and scope uses pre-dirty `comm -13` vs five-file whitelist. Spot-runs corroborate baselines and polarities. Three MINOR nits (batchDate line number, Leg2 post script brevity, `rg -c` zero-print) do not block freeze.

**Verdict: APPROVE**  
**RECONCILE-STAMP APPROVED (p2debt-t3 TODO R1, grok, 2026-07-11)**
