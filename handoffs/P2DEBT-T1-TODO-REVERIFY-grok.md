# P2DEBT-T1 TODO R2 re-verify (grok)

- **task-id**: p2debt-t1  
- **reviewer**: grok  
- **date**: 2026-07-11  
- **inputs**: `handoffs/P2DEBT-T1-TODO-DRAFT-R1.md` (prior APPROVE) vs `handoffs/P2DEBT-T1-TODO-DRAFT-R2.md`  
- **mode**: repo read-only except this file; tmp only; no git checkout/restore; no data_cache; did not read codex re-verify output  

## Diff summary (R1 → R2)

| Finding | Location | Change | Impact on prior APPROVE |
|---------|----------|--------|-------------------------|
| **B1** | Task 1.2b.1 verify cmd | R1: `template_check … \| grep -q 'RISK-HIT'` (matches FAIL text) → R2: `grep -q 'RISK-HIT: b' docs/VERIFY_GATE_SPEC.md` (file-content oracle) | **Strengthens** only; no coverage loss |
| **B2** | 1.2b.4 + Final §4 | R1: `…; echo $?` (compound shell rc=0 after fail) → R2: `rc=$?; echo $rc; exit $rc` | **Strengthens** only |
| **B3** | §0 L46, Phase Gate scope, Final §2 | Narrative “snapshot vs allowlist” → executable `git rev-parse HEAD` pre-head + `diff` whitelist(4) vs `git diff --name-only "$PRE_HEAD"` | **Strengthens** mechanics; same 4-file scope |
| **M1** | Phase Gate L193–195 | bare `pytest` → `venv/bin/python -m pytest` | Env consistency only; same tests/oracles |
| Meta | title + R2-CLOSURE footer | R1→R2 label + 4 closure lines | Doc only |

**Unchanged (spot-checked via unified diff):**  
Task 1.1/1.2/1.2b/1.3 implementation tables; §V ①②③ oracles; `returncode == 1` polarity; `"FACT-RECEIPT" in stdout`; forbid scripts/ / skip / assertion softening; allowlist still exactly 4 paths; Batch Gate still full `tests/governance` → 0 failed.

**Coverage / assertion / scope creep:** none. R2 is verification-command mechanics only (as claimed). Prior R1 APPROVE **not invalidated**.

**Residual (NON-BLOCKING):**  
1. B1 dispatch prompt + footer still cite `TODO-DRAFT-R1.md` (cosmetic; executor should use R2 path).  
2. Final §2 compares full post-diff to whitelist without subtracting pre-diff; on polluted tree (6 pre-existing dirties) gate stays red until dirt cleared or dispatch uses clean tree — fail-closed, not a weakening.

## Spot-run receipts (≥2 corrected commands; 2026-07-11 grok)

### B1 — `grep -q 'RISK-HIT: b' docs/VERIFY_GATE_SPEC.md`
```
B1_rc=1
```
Matches R2 bad-baseline claim (file lacks line).

### R1 B1 false-green repro (control)
```
bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md 2>&1 | grep -q 'RISK-HIT'
R1_B1_pipe_rc=0   # FAIL message contains "RISK-HIT" → false green
```

### B2 — `bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md; rc=$?; echo $rc; exit $rc`
```
TEMPLATE FAIL (spec): docs/VERIFY_GATE_SPEC.md
【缺必填錨點】
  · §RISK 缺 RISK-HIT: 宣告行 …
  · §A fact-scope 缺 FACT-RECEIPT: … gate_check.sh …
  · §A fact-scope 缺 FACT-RECEIPT: … mutation_probe_check.sh …
B2_rc=1
```
R2 compound preserves fail: `R2_B2_script_rc=1`.  
R1 control: `…; echo $?` → overall `R1_B2_script_rc=0` (false green).

### B3 — pre-head + whitelist vs post-diff
```
PRE_HEAD=f0f89c1c0bb751f6fb2b75ab68e973c677f5b6e9
post-diff (6): .claude/gate/audit.log, .claude/settings.json, tests/golden/ic_phase1_1a_cut1/*×4
whitelist (4): docs/VERIFY_GATE_SPEC.md + 3 governance test files
B3_diff_rc=1
```
Matches R2 bad-baseline (6 outsiders, rc=1).

### M1 style (optional)
```
venv/bin/python -m pytest tests/governance/test_verify_gate_b4.py -q --tb=no
→ 3 failed, 8 passed, 1 warning in 4.66s   # pre-migration baseline; runner path OK
```

## Verdict

RECONCILE-STAMP APPROVED (p2debt-t1 TODO R2, grok, 2026-07-11)

Verdict: APPROVE
