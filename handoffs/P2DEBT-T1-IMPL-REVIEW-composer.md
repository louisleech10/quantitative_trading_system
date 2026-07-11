# P2DEBT-T1 Implementation Review — Composer (adversarial)

**task-id**: p2debt-t1  
**reviewer**: Composer  
**date**: 2026-07-11  
**scope reviewed**: `tests/governance/test_verify_gate_b4.py`, `test_verify_gate_b5.py`, `test_verify_gate_redteam.py`, `docs/VERIFY_GATE_SPEC.md`  
**impl author**: Codex (per prompt)

---

## 1. Diff scope & scripts/ boundary

**Command**: `git diff --stat tests/governance/ docs/VERIFY_GATE_SPEC.md`  
**Result**: 4 files, +56 / −9 lines (exact whitelist).

| File | Nature of change |
|------|------------------|
| `test_verify_gate_b4.py` | 3 fixture migrations + 1 new negative (`uppercase_verdict`) |
| `test_verify_gate_b5.py` | 4 fixture migrations + 1 new negative (`missing_risk_hit`) |
| `test_verify_gate_redteam.py` | 1 fixture migration (`VERDICT` → `Verdict`) |
| `docs/VERIFY_GATE_SPEC.md` | `RISK-HIT: b` + 2× `FACT-RECEIPT` |

**Command**: `git diff scripts/`  
**Result**: empty (no `scripts/` changes). **PASS**

**Note**: `git diff --name-only` also lists `.claude/*`, `golden/*`, `settings.json` — outside p2debt-t1 impl delta; not part of this review verdict.

---

## 2. 防假綠 / assertion integrity (vs SPEC §C + §V)

Checked for: deleted/weakened assertions, `pytest.skip`, `returncode in (0,1)`, removal of `"FACT-RECEIPT" in stdout`.

| Check | Result |
|-------|--------|
| `pytest.skip` / `@pytest.mark.skip` in `tests/governance/` | **none** |
| Fuzzy `returncode in (0,1)` | **none** |
| Deleted `assert proc.returncode == 1` on migrated negatives | **none** — all 5 b5 spec negatives still `== 1` |
| Deleted `"FACT-RECEIPT" in proc.stdout` | **none** — `test_b5_spec_command_output_fact_receipt_missing_fails` + `test_b5_spec_fact_receipt_missing_fails` retain |
| Deleted b4 path oracles (`reconcile`/`ADV`/`provenance`/`committee_dispatch`/`GATE PASS`) | **none** |
| `test_b5_existing_verify_gate_spec_still_passes` still targets real `docs/VERIFY_GATE_SPEC.md` | **yes** (unchanged test body) |

**Migrated contract assessment** (fixture-only alignment to current checker semantics):

- **B4×3**: Fixtures gain `Verdict: REJECTED` / `Verdict: APPROVED` so D-1 passes and tests reach intended downstream gates (reconcile / provenance / GATE PASS). Original `returncode` polarity and message oracles **unchanged**.
- **B5×5**: Plain `- 已確認:` → canonical `- **已確認**:` + `RISK-HIT: none` (+ `待確認：無` where needed) so fact-scope actually exercises FACT-RECEIPT / C3 paths per `template_check.sh` f5850c6. Negative tests still assert `rc==1` + `"FACT-RECEIPT" in stdout`; positives still `rc==0`. **Not weakening** — fixes stale fixtures that no longer matched checker contract.
- **R7×1**: Only `VERDICT:` → `Verdict:` in pass fixture; committee_dispatch / hash assertions untouched.

**PASS** — no 防假綠 violations detected.

---

## 3. §V falsifiability negatives (rc≠0 + message oracle)

| §V id | Test | rc assert | Message oracle | Composer re-run |
|-------|------|-----------|----------------|-----------------|
| ① missing RISK-HIT | `test_b5_spec_missing_risk_hit_fails` | `== 1` | `"RISK-HIT" in stdout` | PASSED; manual: `rc=1`, stdout `§RISK 缺 RISK-HIT:` |
| ② uppercase VERDICT | `test_gate_adversarial_rejects_uppercase_verdict` | `== 1` | `"缺 Verdict 行" in combined or "D-1" in combined` | PASSED; manual: `rc=1`, `缺 Verdict 行` + `D-1 拒發` |
| ③ canonical w/o receipt | `test_b5_spec_fact_receipt_missing_fails` | `== 1` | `"FACT-RECEIPT" in stdout` | PASSED; manual: `rc=1`, `§A fact-scope 缺 FACT-RECEIPT` |
| ③ (cmd variant) | `test_b5_spec_command_output_fact_receipt_missing_fails` | `== 1` | `"FACT-RECEIPT" in stdout` | PASSED |

`grep -c 'VERDICT:' test_verify_gate_b4.py` → **1** (only negative test line 280). Pass fixtures use `Verdict:`.

**PASS** — three §V negative classes present; each asserts failure with oracle.

---

## 4. Acceptance re-run

**Command**: `venv/bin/python -m pytest tests/governance -q`  
**Result**: **151 passed**, 0 failed, 48.50s

**Command**: `bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md`  
**Result**: `TEMPLATE PASS (spec): docs/VERIFY_GATE_SPEC.md 含全部必填錨點` — **rc=0**

---

## 5. FACT-RECEIPT truthfulness (read-only replay)

| SPEC line claim | Command replayed | Actual stdout | Match |
|-----------------|------------------|---------------|-------|
| `37:  Task)` | `grep -n 'Task)' scripts/gate_check.sh` | `37:  Task)` | **yes** |
| `74:echo "→ 跑 mutation 探針: pytest -k test_mutation_ $*"` | `grep -n '^echo "→ 跑 mutation 探針: pytest -k test_mutation_' scripts/mutation_probe_check.sh` | `74:echo "→ 跑 mutation 探針: pytest -k test_mutation_ $*"` | **yes** |
| `RISK-HIT: b` | `grep -q 'RISK-HIT: b' docs/VERIFY_GATE_SPEC.md` | exit 0 | **yes** |

FACT-RECEIPT annotations truthfully describe replayable commands; line numbers match live scripts.

---

## 6. Findings

| Severity | Finding |
|----------|---------|
| — | **No blockers.** Implementation matches `P2DEBT_T1_GOVFIX_TODO.md` Tasks 1.1–1.3 + 1.2b. |
| info | Residual risk (SPEC §V): D-1 checks `Verdict` anchor only, not APPROVED/REJECTED value — unchanged, documented, not in scope. |
| info | Working tree has unrelated dirty files (golden, `.claude/`); impl delta itself is clean 4-file whitelist. |

---

## Receipts summary

```
git diff scripts/                          → (empty)
pytest tests/governance -q                 → 151 passed
template_check spec VERIFY_GATE_SPEC.md    → TEMPLATE PASS rc=0
grep Task) gate_check.sh                   → 37:  Task)
grep ^echo mutation_probe_check.sh         → 74:echo "→ 跑 mutation 探針: ..."
negative oracles (manual subprocess)       → all rc=1 + expected substrings
```

Verdict: APPROVE
