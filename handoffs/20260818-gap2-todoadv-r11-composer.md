brief-kind: review

# GAP-2a／2b TODO adversarial 審查 R11 — COMPOSER

**task-id**: `20260818-GAP2-X-REVIEW-R11`  
**family**: `composer`  
**brief**: `handoffs/20260818-gap2-todoadv-r11-BRIEF.md`  
**標的**: `docs/GAP2_MARGINAL_IC_TODO.md`（**DRAFT R5**）｜義務：`docs/GAP2_MARGINAL_IC_SPEC.md`（R7 FROZEN）＋`docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（A1-1..A1-6）｜R10 收斂：`handoffs/reconcile/20260818-gap2-x-review-r10/synth.md`（W1／W2）｜本輪 R10 review：`handoffs/20260818-gap2-todoadv-r10-composer.md`  
**date**: 2026-08-18

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | R11 結論 |
|---|---|---|
| `template_check todo` PASS（DRAFT R5） | fact-verified | **成立** — `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → `TEMPLATE PASS` rc=0 |
| `todo_spec_crosscheck` SMOKE PASS | fact-verified | **成立** — `bash scripts/todo_spec_crosscheck.sh …` → `CROSSCHECK SMOKE PASS` rc=0 |
| R10 W1：Phase B4 小節同文 §B L35＋exact grep rc=1 | assumed→verified | **成立** — L247 gate 命令與 §B L35 逐字一致（三個 `test_gap2_*` 路徑）；`grep -n 'mutation_probe_check.sh\`' TODO` → rc=1 |
| R5 相對 R4 僅版本行＋B4 小節＋A1-5 pointer | assumed→verified | **成立** — `git diff ea86a398..8c29bd7a` 僅上述三處 substantive＋`階段 4 handoff` 一行同步；無其他漂移 |
| R10 composer「可 Frozen」在 R5 上維持 | assumed→verified | **維持** — W1 為 R10 codex P2-01 唯一待修；R5 已關閉；R10 sentinel 所核 V1–V3／A1-5／U2／U4 內容未變 |

---

## COMPOSER-R11-P3-00

**斷言**: R11 窄範圍逐項核對後無 finding——R10 W1（Phase B4 小節與 §B「B4→B5」列同文、exact grep gate）於 DRAFT R5 已成立；本家 R10「可 Frozen」判定在 R5 上維持；`git diff` 無夾帶實質漂移。

**碼證**: **W1** — §B L35 與 Phase B4 L247 gate 段（`pytest` 六檔＋`mutation_probe_check.sh` 三新檔路徑＋`ic_wiring_check`＋`gap2_freeze_golden --check`＋`--batch B4`）byte-equal；`grep -n 'mutation_probe_check.sh\`' docs/GAP2_MARGINAL_IC_TODO.md` → rc=1；`grep -n mutation_probe_check.sh docs/GAP2_MARGINAL_IC_TODO.md` → L19／32–35／110／145／178／247 皆帶 test path；`bash scripts/mutation_probe_check.sh` → 用法提示 rc=1。**diff 實核** — `git diff ea86a398..8c29bd7a -- docs/GAP2_MARGINAL_IC_TODO.md docs/GAP2_MARGINAL_IC_AMENDMENTS.md`：TODO ①版本行 DRAFT R4→R5 ②L247 B4 小節同文寫回 ③L308 handoff FOCUS 同步；AMENDMENTS A1-5 決策行加 pointer「（掛載點依下方 A1-5 補正為 basic tab 末段…）」一句；無其他 hunk。**R10 維持** — V1（§0⑥＋Task 5.1 L257–262 basic tab）、V2（B1–B4 Phase 與 §B 同文）、V3（L220 `write_failed` exact＋L226 ⓪）、A1-5 補正、U2／U4 抽核行號與 R10 一致。RECHECK: 重跑上述 grep／template_check／crosscheck／`git diff ea86a398..8c29bd7a`。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#3f6dbfde496b；docs/GAP2_MARGINAL_IC_AMENDMENTS.md#5027be4cbb54；handoffs/reconcile/20260818-gap2-x-review-r10/synth.md#72bf9378c846

[P3] 信心度=High；本輪為 R10 W1 寫回收斂確認，非重開 R8–R10 已閉項。BLOCKING 清單：無。

---

## R11 必答（逐條 verdict）

| # | 問題 | verdict | 依據 |
|---|---|---|---|
| 1 | W1 寫回成立？ | **是** | L247 同文 §B L35；exact grep rc=1（見碼證） |
| 2 | R10 判定在 R5 上維持？ | **維持可 Frozen** | 僅 W1 修補＋版本／pointer；實質 Task 語意未變 |
| 3 | `git diff` 只含宣稱兩處＋A1-5 pointer？ | **是（＋handoff 一行）** | `ea86a398..8c29bd7a` 四 hunk 皆 metadata／W1／pointer；無夾帶 |
| 4 | 可 Frozen 進 B1？ | **可 Frozen** | BLOCKING 清單：無 |

---

## Verdict：可 Frozen

R10 W1 已於 DRAFT R5 正確寫回；本家 R10 sentinel（`COMPOSER-R10-P3-00`）所依據之 V1–V3／A1-5／U2／U4 在 R5 上仍成立。本輪 0 實質 finding（sentinel `COMPOSER-R11-P3-00`）。待三家皆 sentinel ⇒ TODO 版本行改 **FROZEN** → B1 實作。

---

ASSUMPTIONS_VERIFIED: W1 exact grep rc=1；§B L35↔L247 gate 同文；`git diff ea86a398..8c29bd7a` 範圍；template_check PASS；crosscheck SMOKE PASS；`mutation_probe_check.sh` 無參數 rc=1  
TESTS_RUN: `grep -n 'mutation_probe_check.sh\`' docs/GAP2_MARGINAL_IC_TODO.md` → rc=1；`bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → PASS rc=0；`bash scripts/todo_spec_crosscheck.sh docs/GAP2_MARGINAL_IC_SPEC.md docs/GAP2_MARGINAL_IC_TODO.md` → SMOKE PASS rc=0；`bash scripts/mutation_probe_check.sh` → rc=1；`git diff ea86a398..8c29bd7a -- docs/GAP2_MARGINAL_IC_TODO.md docs/GAP2_MARGINAL_IC_AMENDMENTS.md` → 僅宣稱 hunk；`bash scripts/completeness_check.sh --single handoffs/20260818-gap2-todoadv-r11-composer.md --family composer` → PASS rc=0（1 canonical ID）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（審查只讀）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_ARTIFACT: `handoffs/20260818-gap2-todoadv-r11-composer.md`  
TMP_CLEANUP: 嘗清 `/private/tmp` 之 `agent_dc_snapshot.txt`、`b4gate_*.txt`、`gap2_b4_compare.txt`、`mprobe.out`、`sessions/` — shell 權限阻擋未執行；`claude-501` 未動  
HANDOFF_NOT_UPDATED: 根 `HANDOFF.md` 由 Claude 維護；本輪 append → `handoffs/20260818-gap2-todoadv-r11-composer.md`

STATUS: DONE
