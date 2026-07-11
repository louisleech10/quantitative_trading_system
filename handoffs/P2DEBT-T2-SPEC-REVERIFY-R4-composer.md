# P2DEBT-T2 SPEC R4 re-verify — composer — 2026-07-11

Task-id: `p2debt-t2` | Role: non-author adversarial re-verify | Input: `handoffs/P2DEBT-T2-SPEC-DRAFT-R4.md` (Codex breaker handover from Composer R3) | Grok R4 re-verify: **not read**

---

## 1) Prototype receipts (independent rerun)

### P0 — full suite (expect 8 passed incl. `asyncio.to_thread`)

```text
命令: cd /tmp/p2debt-t2-proto && python -m pytest -q
結果: ........  [100%]
      8 passed in 0.06s
EXIT=0
```

Verbose rerun confirms `test_opt_in_to_thread.py::test_to_thread_polluter_writes_under_redirect PASSED` and `ab_hash=45be569c8791f83cc63fbe45f43e1032f5e6d07f6a98808e2a4cc725de9ccf58` (matches R4 FACT-RECEIPT P3).

### P1 — targeted to_thread + non-opt-in (R4 P1)

```text
命令: cd /tmp/p2debt-t2-proto && python -m pytest tests/test_opt_in_to_thread.py tests/test_non_opt_in.py -v -s
結果: 2 passed in 0.02s
EXIT=0
```

### P2 — mutation / redirect disabled canary (R4 P2)

```text
命令: cd /tmp/p2debt-t2-proto && P2DEBT_PROTO_DISABLE_REDIRECT=1 python -m pytest tests/test_opt_in_to_thread.py::test_to_thread_polluter_writes_under_redirect -q
結果: 1 failed — PosixPath('data_cache/features/THREAD_1h_filtered.h5').is_relative_to(redirect_root) → False
EXIT=1
```

Expected red: feature lands under production-relative `data_cache/features/`, not redirect root.

### P3 — in-prototype mutation three-state (hermetic file)

```text
命令: cd /tmp/p2debt-t2-proto && python -m pytest tests/test_hermetic_mutation.py -v -s
結果: test_hermetic_digest_empty_diff DIGEST_DIFF_EMPTY=1 before=0 after=0 PASSED
      test_mutation_redirect_disabled_caught MUTATION_CANARY=1 PASSED
EXIT=0
```

---

## 2) R3 → R4 preservation / drift audit

Method: line-by-line compare of R3 draft vs R4 on coverage tables, golden A/B/C, isolation, §V oracles, and R3-CLOSURE items. R2 used as backfill where R3 referenced “同 R2 §COVERAGE”.

### Coverage — no dropped rows; enumeration clarified

| Area | R3 | R4 | Drift? |
|------|----|----|--------|
| 16-caller `rg` set | 16 files + RS-01 GUARD row | Exact 16-row table (§COVERAGE L192–211) + separate API polluter table B | **Improved** — fixes codex B1 “19 ≠ 16” ambiguity |
| IC-01..12 | Referenced via R2 / summary | Full table §COVERAGE A | **Preserved** (expanded from R2) |
| API-01..07 | In R2; R3 summary only | Full table §COVERAGE B | **Preserved** |
| ML-01..06 | R3 V7 six-file list | Table C + V7 six-file list | **Preserved** |
| FF-01..02, GEN-01..04 | R3 §GEN + R2 refs | Tables D–E | **Preserved** |
| GUARD/STUB/N/A | R3 16-caller mini-table | Table F incl. `test_ic_1eb_b{2,4,5}_*` | **Preserved** |
| `test_ic_run_selector` | RS-01 GUARD, no REDIRECT | GUARD in 16-caller + table F | **Preserved** |

Repo receipt: `rg -l '\.(analyze|start_analysis|refilter)\(' tests --glob '*.py' | sort | wc -l` → **16** (list matches R4 table order).

### Golden A/B/C — preserved; Run C strengthened (not weakened)

| Run | R3 | R4 | Assessment |
|-----|----|----|------------|
| A/B | ON at `tmp_a`/`tmp_b`; normalized hash equal | Same | Preserved |
| C | OFF必跑；`hash_off == hash_a` | OFF + **`monkeypatch.chdir(tmp_path/work)`**; sacrificial `work/data_cache`; **repo digest before/after must match** | **Stronger** (closes codex B4 / grok NEW-R3-2) |
| normalize / EXEMPT | sorted keys; path/mtime exempt only | Same + explicit ban on exempting numeric/schema fields | **Stronger** |
| skip | `pytest.fail()` | Same | Preserved |
| stdout | `ab_hash=` + V5 `-s` | Same | Preserved |

Prototype `test_golden_ab.py` still runs OFF under `work/` chdir (partially aligned); R4 implementation contract exceeds prototype on repo-root digest — acceptable SPEC tightening, not oracle weakening.

### Isolation I1–I3 — preserved; made executable

| Case | R3 | R4 | Assessment |
|------|----|----|------------|
| I1 | subprocess + 3 nodeids (unnamed) | **Fixed nodeids** + `IC_PERSIST_ASSERT_NO_ACTIVATION=1` + probe JSON `activation_count=0` | **Stronger** (closes codex B5) |
| I2 | S1–S11 parametrize | Same + tied to manifest completeness | Preserved + linked to NEW-R3-1 |
| I3 | inventory vs marker | Same + S9/S11 helper wiring | Preserved |

I1 nodeids exist in repo: `test_disambig_same_tf_different_hash`, `test_refilter_without_cache_raises`, `test_insufficient_ls_samples` (Analysis path; phase25 duplicate noted below).

### §V oracles — preserved or strengthened

| Item | R3 | R4 | Assessment |
|------|----|----|------------|
| V1 | `9 passed, 1 skipped` (perf only) | Same + harness digest label | Preserved |
| V2/V5/V6/V7 | Bare pytest commands | **`run_guard` per-set SHA-256 digest**; bare runs forbidden for hermetic acceptance | **Stronger** (closes codex NEW-2) |
| V3 | Single harness subset | `--set all` → five `DIGEST_DIFF_EMPTY[Vn]=1` labels | **Stronger** |
| V4 | `≥3 passed` isolation | `≥4 passed` (+ inventory file) | **Stronger** |
| V7 skip rule | `passed == collected - data_missing_skips` | **nodeid/reason whitelist** (FF missing kline only) | **Stronger** |
| Digest function | `json.dumps(digest_data_cache())` | per-file **SHA-256** map | **Stronger** (not silent weakening) |
| V1/V7 collect | 10 / 141 | Same — collect-only rerun **10** / **141** (composer 2026-07-11) | Preserved |

### Intentional architecture change (not silent drift)

R3 §PROTO used **thread-local** `get_active_redirect_root()`; codex R3 re-verify P4 proved `asyncio.to_thread` **fails** under TLS. R4 replaces with **process-global `_active_redirect_root` + `RLock`**, nested-activation reject, ownership-checked deactivate. Prototype `fakepkg/redirect.py` L13–82 implements this; P0/P2 confirm cross-thread visibility. This is the documented fix for codex N1/B2, not dropped R3 content.

### R3 open findings → R4 closure spot-check

| R3 blocker (codex R3) | R4 addresses? |
|-----------------------|---------------|
| TLS / `to_thread` (N1, B2) | Yes — process-global gate + P1/P2 receipts |
| Session spy wrong context (NEW-1) | Yes — own-spy teardown; prototype conftest pattern |
| V2/V5/V6/V7 outside digest (NEW-2) | Yes — `run_guard` per set |
| Run C can write repo (B4) | Yes — tmp/work + dual digest |
| I1 not executable (B5) | Yes — fixed nodeids + env probe |
| 16 vs 19 caller table (B1) | Yes — split tables |

**No dropped coverage rows or weakened acceptance oracles identified.**

---

## 3) Process-global gate + RLock vs parallel/xdist (TLS motivation)

### Concern that motivated R3 TLS

R3 chose TLS for “parallel safety” (isolated active root per thread). Codex R3 P4 showed this **breaks** real API path: `api/services/ic_analysis_service.py` L165+ uses `await asyncio.to_thread(analyzer.analyze_…)` — worker thread cannot see TLS active root.

### R4 design + stated justification

R4 explicitly documents (L10–12, L127–128, L217–237, L266–268, L479):

1. **Why global**: patch visibility + active gate must be visible in `asyncio.to_thread` workers in the **same process**.
2. **Why serial**: single active root per process; `activate()` raises if already active (`RuntimeError: redirect already active; pytest execution must remain serial` — prototype L67–68).
3. **RLock role**: protects gate read/write only; lookups are short, no I/O under lock.
4. **xdist**: workers are separate processes → separate gates; R4 states acceptance commands **do not use xdist**.
5. **NOT in scope**: parallel pytest / per-worker ownership deferred to future work (L479).

### Soundness assessment

| Claim | Evidence | Verdict |
|-------|----------|---------|
| Serial default pytest | Repo `rg xdist` → **0** matches | Sound for current CI |
| to_thread fixed | P0/P1/P2 independent pass/fail | **Verified** |
| Nested overlap rejected | Prototype `RedirectContext.activate` | Sound fail-closed |
| xdist isolation | Process boundary argument + no xdist in repo | Sound **given** R4 prohibition |
| Residual risk | Future `-n auto` or concurrent async tests in one process would violate assumption | **Documented** in NOT in scope; not a silent gap |

**Conclusion**: Serial-execution justification is **stated and sound** for this ticket’s acceptance matrix. The TLS→global pivot correctly trades thread-isolation for worker-thread visibility; RLock + nested reject is adequate for serial pytest.

---

## 4) NEW problems (composer hunt)

### NEW-R4-1 — NON-BLOCKING: prototype proves gate, not full `RedirectPatchSet` manifest

R4 §SEAM mandates `resolve_all()` / `install_once()` / `REQUIRED_SEAM_IDS` fail-closed for S1–S11. Prototype still uses simplified `Path.write_bytes`/`mkdir` spy + `data_cache_root()` getter — it does **not** exercise manifest completeness, per-seam wrappers, or `RedirectCompletenessError`. Real repo has **no** `data_cache_root()`; production redirect must be seam wraps per R4 table.

**Impact**: SPEC-implementation gap acceptable at draft stage **if** Phase 1 unit tests (`test_ic_persist_redirect_unit.py`) enforce manifest as written. Not a regression from R3 (R3 had same prototype/simplicity; R4 makes manifest explicit).

### NEW-R4-2 — NON-BLOCKING: I1 long-short nodeid duplicate

Both `tests/momentum/Analysis/test_long_short_analyzer.py` and `tests/phase25/test_long_short_analyzer.py` define `test_insufficient_ls_samples`. R4 I1 pins Analysis path only — correct for non-opt-in canary, but implementers should not accidentally subprocess the phase25 copy.

### NEW-R4-3 — NON-BLOCKING: prototype golden OFF lacks repo-root digest assertion

R4 §G requires Run C to record repo `data_cache` digest before/after; prototype `test_golden_ab.py` only compares normalized in-test hashes under `tmp_path/work`. Implementation must follow §G, not prototype alone.

### NEW-R4-4 — PROCESS NOTE: collect-only touches inventory hook

V1/V7 collect-only (no test body) still loads root pytest plugins; consistent with codex R3 NEW-3 observation. No repo `data_cache/` writes performed in this audit.

**None of NEW-R4-* weaken R4 vs R3 or invalidate P0/P2 evidence.**

---

## 5) Supporting repo facts (read-only)

- `asyncio.to_thread` in IC analyze: `api/services/ic_analysis_service.py` L165, L228, L661, L787, L806, L890.
- API fixture scopes: `ic_analysis_task` / `export_task` **session**; `completed_ic_task` **module** (rg receipt matches R4 §A).
- `test_ic_run_selector.py` stub at L215–227 (R3/R4 GUARD) — not re-read in full; R3 receipt still valid.

---

## Summary

| Check | Result |
|-------|--------|
| Prototype 8/8 + to_thread | **PASS** (independent) |
| Mutation canary exit 1 | **PASS** (independent) |
| R3 coverage/golden/isolation/V preserved | **PASS** — expanded/strengthened, no dropped rows |
| Serial + RLock justification | **PASS** — stated, sound for no-xdist serial pytest |
| NEW blocking issues | **None** |

RECONCILE-STAMP APPROVED (p2debt-t2 SPEC R4, composer, 2026-07-11)

Verdict: APPROVE

---

ASSUMPTIONS_VERIFIED: prototype 8/8; mutation P2DEBT_PROTO_DISABLE_REDIRECT exit 1; 16-caller rg=16; V1 collect=10; V7 collect=141; API session/module scopes; asyncio.to_thread in ic_analysis_service; no xdist in repo; ab_hash matches R4 P3
TESTS_RUN: `/tmp/p2debt-t2-proto` P0/P1/P2/P3; repo `rg` + collect-only V1/V7 (0 polluting pytest body)
FAILURES_SEEN: expected P2 mutation failure only
SCOPE_CHANGES: none; output `handoffs/P2DEBT-T2-SPEC-REVERIFY-R4-composer.md`
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
