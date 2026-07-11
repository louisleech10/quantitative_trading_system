# P2DEBT-T1 TODO R4 re-verify (grok)

- **task-id**: p2debt-t1  
- **reviewer**: grok  
- **date**: 2026-07-11  
- **inputs**: `handoffs/P2DEBT-T1-TODO-DRAFT-R3.md` vs `handoffs/P2DEBT-T1-TODO-DRAFT-R4.md`  
- **mode**: repo read-only except this file; experiments under `/tmp` only; no git checkout/restore; no `data_cache/` writes  
- **context**: circuit-breaker handover after Composer R3 `comm -23` direction bug in scope gate; Codex produced R4

---

## (1) Diff R3 → R4 — scope only?

**Command**: `diff -u handoffs/P2DEBT-T1-TODO-DRAFT-R3.md handoffs/P2DEBT-T1-TODO-DRAFT-R4.md`  
**diffstat**: `1 file changed, 23 insertions(+), 10 deletions(-)`

| Hunk | Location | Change |
|------|----------|--------|
| 1 | §0 L46 (防假綠 scope 第 3 點) | `comm -23` → `comm -13 … \| sort -u`；delta vs whitelist 兩邊皆 `sort -u` 後精確相等 |
| 2 | Phase 1 Gate table `scope` row | 同上 pipeline；標 **預期** 壞基線 rc=1 + **`/tmp` simulation 實跑 rc=0** |
| 3 | Final Acceptance §2 | `comm -13`；whitelist/delta 各自 `sort -u` 再 `diff`；誠實聲明未觀察真實完工；附 R4 synthetic simulation receipt |
| 4 | Footer closures | R3-CLOSURE B3 改寫（撤回未觀察「完工後 rc=0」）；新增 `R4-CLOSURE: B3 → comm direction fixed…` |

**Unchanged (via unified diff):** Task 1.1/1.2/1.2b/1.3 實作表、§V ①②③ oracles、returncode 極性、禁 scripts/skip/弱化斷言、四檔 whitelist、Batch Gate pytest 命令、標題仍寫「草案 R3」、L72/footer 仍指 `TODO-DRAFT-R3.md`（R3 既有殘留，R4 未再動）。

**Verdict (1):** PASS — 僅 scope-gate 機制三處 + closure 行。

**NON-BLOCKING residual:** 檔名 R4 但標題/派工 prompt/footer 仍寫 R3；不影響 scope 語意，冷啟動應讀 `TODO-DRAFT-R4.md`。

---

## (2) `comm` 方向 + R4 pipeline re-run (grok 2026-07-11)

### Semantics (macOS `man comm`)

- col1 = only file1；col2 = only file2；col3 = both  
- **`comm -13` file1 file2** = only file2 → **post − pre 新增**（正確 delta）  
- **`comm -23` file1 file2** = only file1 → pre 獨有（**錯誤**方向，對「pre 是 post 子集」的完工樹會得到空 delta）

### Minimal experiment — pre vs post+additions

```text
pre  = {a, b}
post = {a, b, docs/VERIFY_GATE_SPEC.md,
        tests/governance/test_verify_gate_b4.py,
        tests/governance/test_verify_gate_b5.py,
        tests/governance/test_verify_gate_redteam.py}
```

| Command | Output | Interpretation |
|---------|--------|----------------|
| `comm -13 pre post` | 4 whitelist paths | **correct** post-only delta |
| `comm -23 pre post` | *(empty)* | **wrong** — would fail-green empty delta after legitimate 4-file edit |
| `comm -12 pre post` | `a` `b` | common lines only |

### R4 pipeline simulation (exact recipe from Final §2 comments)

**Empty delta (pre == post = {a,b})** — **real-run (grok):**

```text
wc -l r4-baddelta4 → 0
diff -u r4-white4 r4-baddelta4 → shows 4 missing whitelist lines
EMPTY_DELTA_DIFF_RC=1
```

**pre + 4 whitelist (simpost)** — **real-run (grok):**

```text
comm -13 r4-pre4 r4-simpost4 | sort -u → 4 lines (exact whitelist)
diff -u r4-white4-sorted r4-simdelta4 → (no output)
SIM_PRE4_DIFF_RC=0
wc -l r4-simdelta4 → 4
```

**Control: wrong `-23` on pre+4** — **real-run (grok):**

```text
comm -23 → empty delta; WRONG_DIR_DIFF_RC=1
```

**Verdict (2):** PASS — `-13` is correct; R4 pipeline yields **rc=0** on pre+4-whitelist simulation and **rc=1** on empty delta. R3's `-23` is directionally inverted.

---

## (3) Unobserved-claim audit (every rc in R4)

| rc / exit claim | Label in R4 | Class |
|-----------------|-------------|--------|
| governance baseline `9 failed, 140 passed` | Composer 實跑 | real-run |
| `template_check` 壞基線 exit 1 / rc=1 | Composer 實跑 | real-run |
| 1.2b.1 壞基線 `rc=1` | Composer 實跑 2026-07-11 | real-run |
| 1.2b.4 / Final §4 壞基線 `rc=1` | Composer 實跑 | real-run |
| Final §2 empty-delta sim `rc=1`；pre+4 sim `rc=0` | **R4 synthetic simulation receipt（Codex 實跑）** | simulation |
| Phase Gate scope 壞基線 **rc=1** | 預期 | expected (bad baseline) |
| Phase Gate `pre+4` **rc=0** | `/tmp` simulation 實跑 | simulation |
| Final §2 壞基線 exit 1 | 誠實預期 | expected |
| Final §2 真實完工 exit 0 | **真實完工驗收預期** + L234「**尚未觀察**真實完工…不得宣稱…rc=0」 | expected only; explicitly unobserved |
| Task post-migration `returncode == 0/1` / suite 0 failed | 驗證命令+預期輸出 / 預期完工後 | expected post-impl oracles (not claimed observed now) |
| R3-CLOSURE B3 | 註明「原稱完工後…**未實際觀察**，已由 R4 修正」 | corrects prior overclaim |

**No unobserved “we saw real completion rc=0” claim remains.** R3's overclaim on finished-tree delta=whitelist is withdrawn.

**Verdict (3):** PASS.

---

## Summary

| Check | Result |
|-------|--------|
| (1) Diff only scope-gate×3 + closures | PASS |
| (2) `comm -13` correct; sim rc=0 / empty rc=1 | PASS (grok re-run) |
| (3) All rc labeled real-run / simulation / expected | PASS |

ASSUMPTIONS_VERIFIED: POSIX/macOS `comm -13` = only-file2; R4 three scope sites use `-13`; R3 used `-23`; synthetic pipeline rcs match R4 text.  
TESTS_RUN: `diff -u R3 R4`; `/tmp` comm -13/-23 minimal; empty-delta + pre+4 R4 recipes (EMPTY_DELTA_DIFF_RC=1, SIM_PRE4_DIFF_RC=0); wrong-direction control.  
FAILURES_SEEN: none on re-verify path.  
SCOPE_CHANGES: none; only this output file.  
NUMERIC_OR_SCHEMA_IMPACT: none.

RECONCILE-STAMP APPROVED (p2debt-t1 TODO R4, grok, 2026-07-11)

Verdict: APPROVE
