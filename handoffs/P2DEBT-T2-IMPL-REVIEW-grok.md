# P2DEBT-T2 IMPL REVIEW — grok (adversarial)

- task-id: `p2debt-t2-impl-review-grok`
- role: independent dual-family code review (author=codex; no self-review)
- date: 2026-07-12
- scope: ticket-2 redirect only; **read-only** (only this file written)
- brief: `handoffs/P2DEBT-T2-IMPL-REVIEW-BRIEF.md`
- receipt anchor: `handoffs/run_receipts/20260712T003131Z-p2debt-t2-impl-final6.json` (exit 0)

## VERDICT: **BLOCK**

Not because final6 hermetic body currently leaks (digest empty on V1/V2/V5/V6/V7), but because **SPEC/TODO completeness + subtarget mutation claims are false-green**. A missing S2/S1/S10 subtarget installer still activates; unit “refuses_activate” never calls `activate()`. That is the same class of seam hole that shipped C-5 past unit gates until V7 digest caught it.

---

## Counterexamples attempted (falsifiable)

### CE8 — PRIMARY BLOCKING: subtarget mutation does not refuse activate

**Claim under test** (TODO 1.3.3 / test name `test_missing_subtarget_refuses_activate`): dropping an S2/S1/S10 subtarget installer must refuse activate.

**Actual test body** (`tests/momentum/Analysis/test_ic_persist_redirect_unit.py`):

1. pops one installer from the seam
2. calls `resolve_all()` only
3. asserts reduced installer count + `get_activation_count()==0`
4. **never calls `activate()`**

`activation_count==0` is vacuously true.

**Runtime counterexample** (this review, repo cwd, venv python):

```text
# pop S2.save_report (index 0), then activate
CE8_ACTIVATE_SUCCEEDED_WITH_S2_MISSING_SUBTARGET True
installed_ids ['S1','S10','S11','S2','S3','S4','S5','S6','S7','S8','S9']
```

`RedirectPatchSet` only enforces `installers` non-empty and ID set == S1..S11. **Partial S2 (2/3 methods) still installs and activates.** Same pattern covers S1 (`_resolve_filtered_path` / `_persist_outputs`) and S10 (lgb/xgb).

**Why BLOCK**: C-5 was exactly “one sub-write path unpatched”. Current unit matrix cannot fail that regression class. Digest remains the only effective net; unit completeness is cosmetic.

**Fix bar (for author, not done here)**:

- enforce per-seam minimum installer arity (S1≥2, S2≥3, S10≥2) in `_validate` / `activate`
- rewrite subtarget tests to: pop → `activate()` raises `RedirectCompletenessError` → `activation_count==0` → no residual patch if install failed mid-way

---

### CE3 — seam `probe` is tautological (non-blocking alone, aggravates CE8)

`_build_manifest` defines:

```python
def probe(root: Path) -> tuple[Path, ...]:
    return (root / bucket / f"{seam_id.lower()}_probe",)
```

`test_seam_probe_redirect_only[S*]` never calls production write paths or installers. Probes always lie under `root` by construction.

SPEC §SEAM positive probe (“probe 觸發後只寫 redirect root”) is **not implemented**. Only real positive write tests found: `test_s1_orchestrator_report_literals_redirect`, `test_to_thread_polluter_writes_under_redirect`, plus body suites under hermetic digest.

---

### CE1 — C-5-class residual: direct FS write bypasses spy; digest catches

Under active redirect, direct:

```python
Path("data_cache/models/adv_ce1_leak.pkl").write_bytes(b"LEAK")
```

| layer | result |
|---|---|
| `ctx.spy.violations` | `[]` (spy only records wrapper rewrites) |
| file under production | **True** |
| `digest_data_cache()` key present | **True** (`models/adv_ce1_leak.pkl`) |

**Interpretation**: production spy is not a FS fence; hermetic digest **is** the real canary (C-5 finding already proved DIGEST_DIFF_EMPTY=0 on leak). CE1 does **not** reopen a live V7 leak if tests only write via resolvers/helpers — but any future direct `open("data_cache/...")` will be invisible to spy until digest.

C-5 concrete fix verified in tree:

- bad payload writes `get_active_redirect_root()/models/...` (test-side)
- S1 adds `_persist_outputs` + `_RedirectingReporter`
- S10 accepts already-redirected models root

CE6 (phase3-style `Path("data_cache/models")` + patched `_resolve_model_path` write): prod_exists=False, DIGEST_UNCHANGED=True.

---

### CE-cwd — relative path + non-repo cwd skips redirect

```text
# active redirect, chdir to /tmp/othercwd
_redirect_path(Path("data_cache/features/adv_probe.h5"))
→ equals_input True  (NOT rewritten)
→ resolves under othercwd/data_cache/...
```

`Path.resolve()` is cwd-relative; if not under `production_prefix`, rewrite is skipped. Current hermetic V* run from repo root → not live. Latent hazard for any future chdir+active combo (C-2/C-3 family). Non-blocking for present V suites; document / harden if generators chdir.

---

### CE5 — golden A/B/C sha256

`normalize()` drops `filtered_features_path` / `report_paths` / mtime keys (intentional path-independence).

| case | result |
|---|---|
| path-only A vs B | same hash (by design) |
| value field change | hash differs |

final6 log: `ab_hash=1a30560e...` + `DIGEST_DIFF_EMPTY[V5]=1`. Locks **payload** conservation A=B=C (OFF under sacrificial chdir work root), not path identity. **Accept for ticket-2 goal.**

---

### CE-S9/S11 unit mutation — string tautology (inventory saves it)

```python
def test_s9_helper_bypass_mutation() -> None:
    source = "with h5py.File(Path('data_cache/features/x.h5'), 'w'): pass"
    assert "_export_fixture_filtered_path" not in source
```

Never reads `tests/api/test_export_api.py`. SPEC “不經 helper → probe 必紅” not met by unit file.

**Mitigation present**: `test_ic_persist_redirect_inventory.py::test_s9_s11_helpers_are_not_bypassed` does real counts (`_export_fixture_filtered_path(` ==2; `_create_e2e_factory()` ==8; bare `create_feature_factory()` ==1). Call-site wiring OK; unit mutation names overclaim.

S5/S6/S9/S11 installers are **no-ops** (`lambda: (lambda: None)`). S5/S6 rely on S4 module `Path` patch (CE4: materialize/transforms paths rewrite under active). S9/S11 rely on helpers reading `get_active_redirect_root()`. Manifest “11 seams installed” ≠ 11 real patches.

---

## Review checklist (brief)

| Focus | Result |
|---|---|
| Redirect writes to sacrificial root; R/W same root | **Mostly yes** for wired seams (S1+C5, S2, S3, S4 Path, S7, S8, S10, helpers). CE6/S10 OK. |
| Residual C-5 bypass write points | No live V7-scope leak found after C-5 fix; CE1 class still open for raw FS writes; spy blind. |
| Digest oracle falsifiable | **Yes** — CE1 + C-5 history + hermetic `test_mutation_redirect_disabled_caught`. final6 all `DIGEST_DIFF_EMPTY=1`. |
| Golden A/B/C sha256 locks behavior | **Yes** for normalized payload; path keys stripped by design. |
| V6 nodeid gate | Prior polarity both-pass (`handoffs/P2DEBT-T2-P1-POLARITY-grok.md`); final6 `V6_NO_NEW_RED=1`+DIGEST=1. Script parses `^(FAILED\|ERROR) ` + `tests/` field-2 — OK. |
| S1–S11 seam integrity | **FAIL completeness contract** — CE8 + no-op S5/6/9/11 + tautological probes. |
| process-global / `to_thread` | Unit `test_to_thread_polluter_writes_under_redirect` passes; gate is process `_ACTIVE` + RLock (not TLS). |
| Skip whitelist (C-1) | V1 anchors `^SKIPPED [` + `RUN_IC_E2E_PERF`; V7 e2e data skips. |

---

## Tests run this review

```text
venv/bin/python -m pytest \
  tests/momentum/Analysis/test_ic_persist_redirect_unit.py \
  tests/momentum/Analysis/test_ic_data_cache_hermetic.py \
  tests/momentum/Analysis/test_ic_persist_redirect_inventory.py -q
→ 47 passed

# adversarial scripts (CE1–CE9, cwd, S10): all exit 0; CE8 activate-with-missing-S2-subtarget True
# final6 receipt (not re-run full all): exit_code=0; DIGEST V1/V2/V5/V6/V7=1; V6_NO_NEW_RED=1
```

---

## Commit scoping (mixed freeze scripts)

| File | Ticket-2 hunk | Ticket-5 hunk | Advice |
|---|---|---|---|
| `tests/fixtures/gen_ic_run_selector_baseline.py` | import + `with run_with_manual_redirect()` | none in diff | **include all in T2** |
| `tests/golden/ic_phase1_contract/freeze_baseline.py` | redirect wrapper only | none | **include all in T2** |
| `tests/golden/ic_phase1_1a_cut1/freeze_baseline.py` | redirect import/wrapper | `h5_existing` cache short-circuit; `config_override={"ic_train_test_split": False}`; meta `config_override` | **`git add -p` — only redirect hunks for T2** |
| `tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py` | redirect wrapper | `h5_existing`; meta override True; command path fix to `freeze_baseline_new.py` | **same: -p split; T5 hunks out of T2 commit** |
| `baseline_*.json`, `l65/test_inventory.txt` | — | pure T5 | **exclude from T2** |

Do **not** land T2+T5 freeze behavior in one commit: flag-off golden semantics (854d444) are T5 provenance, not redirect isolation.

---

## What is solid (do not regress)

1. Hermetic digest outer gate — historically caught C-5; still the production fence.
2. C-5 S1 `_persist_outputs` + bad-payload same-root write.
3. S10 model path rewrite + already-under-redirect allowance.
4. V6 baseline nodeid ⊆ gate with dual-polarity receipt.
5. Inventory static wiring for S9/S11 and 16-caller set.
6. Manual generator `run_with_manual_redirect` env/root bracket.

---

## Required before APPROVE

1. **Fix CE8**: arity validation + subtarget tests that actually call `activate()` and expect raise.
2. Prefer: replace tautological `probe` with at least one real write per non-no-op seam (or demote SPEC language so probe is path-shape only and completeness rests on body+digest).
3. Prefer: replace fake S9/S11 unit mutation strings with inventory-style source scan (or delete unit tests that invent source).
4. Re-run unit set + optional V7 digest after fix (author/codex; runner/grok per分工).

Until (1) lands, unit “S1–S11 completeness” is not a trustworthy gate — only outer digest is.

---

ASSUMPTIONS_VERIFIED: CE8 activate-with-missing-S2-subtarget; CE1 spy-blind+digest-catch; CE6 S10 no prod write; CE5 normalize path/value; cwd relative bypass; S5/6/9/11 no-op installers; final6 log digest lines; inventory S9/S11 counts via pytest 47p
TESTS_RUN: unit+hermetic+inventory 47 passed; adversarial CE scripts exit 0; final6 not re-executed (cited receipt)
FAILURES_SEEN: none in pytest; CE8 is design false-green not pytest red
SCOPE_CHANGES: none (review-only)
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
verdict=BLOCK
